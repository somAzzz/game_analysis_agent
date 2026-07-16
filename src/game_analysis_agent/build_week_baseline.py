"""Generate and compare the canonical real-game Build Week baseline."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import validate_trace_catalog_consistency

CONFIG_SCHEMA = "build-week-baseline-config-v1"
REVIEW_SCHEMA = "build-week-baseline-review-v1"
MARKER_FILE = ".playtest-forge-baseline.json"
REVIEW_FILE = "baseline_review.json"


class BaselineError(RuntimeError):
    """Raised when canonical baseline evidence is incomplete or inconsistent."""


@dataclass(frozen=True)
class CommandResult:
    """Minimal subprocess result used by the injectable baseline runner."""

    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], CommandResult]


def load_baseline_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the tracked canonical-baseline declaration."""

    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BaselineError(f"baseline config not found: {source.name}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"baseline config is invalid JSON: {source.name}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != CONFIG_SCHEMA:
        raise BaselineError(f"baseline schema_version must be {CONFIG_SCHEMA!r}")
    if not isinstance(payload.get("run_id"), str) or not payload["run_id"]:
        raise BaselineError("baseline run_id is required")
    parameters = _mapping(payload, "parameters")
    for key in ("runs", "seed", "weeks"):
        if not isinstance(parameters.get(key), int):
            raise BaselineError(f"baseline parameter {key} must be an integer")
    for key in ("policy", "difficulty", "scenario"):
        if not isinstance(parameters.get(key), str) or not parameters[key]:
            raise BaselineError(f"baseline parameter {key} is required")
    validators = payload.get("contract_validators")
    if not isinstance(validators, list) or not all(
        isinstance(item, str) and item for item in validators
    ):
        raise BaselineError("baseline contract_validators must be a non-empty list")
    artifacts = payload.get("canonical_artifacts")
    if not isinstance(artifacts, list) or not all(
        isinstance(item, str) and item and not Path(item).is_absolute() and ".." not in Path(item).parts
        for item in artifacts
    ):
        raise BaselineError("baseline canonical_artifacts contains an unsafe path")
    observation = _mapping(payload, "quality_observation")
    fragments = observation.get("required_error_fragments")
    if not isinstance(fragments, list) or not all(
        isinstance(item, str) and item for item in fragments
    ):
        raise BaselineError("baseline quality observation requires error fragments")
    return payload


def generate_baseline(
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    game_root: str | Path,
    output_dir: str | Path,
    replace: bool = False,
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Run the real Godot pipeline and write a fail-closed baseline review."""

    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    output = Path(output_dir).resolve()
    if not (game / "project.godot").is_file():
        raise BaselineError("canonical game bundle is not a Godot project")
    _prepare_output(output, run_id=str(config["run_id"]), replace=replace)
    command_runner = runner or _run_command
    environment = {**os.environ, "GAME_PROJECT_PATH": str(game)}
    operations: list[dict[str, Any]] = []
    status = "failed"
    error = ""
    try:
        for name, command, expected_codes in build_command_plan(
            config,
            project_root=project,
            output_dir=output,
        ):
            result = command_runner(command, project, environment)
            operation = {
                "name": name,
                "command": _display_command(command, project=project, output=output, game=game),
                "returncode": result.returncode,
                "stdout": _sanitize(result.stdout[-4000:], project, output, game),
                "stderr": _sanitize(result.stderr[-4000:], project, output, game),
            }
            operations.append(operation)
            if result.returncode not in expected_codes:
                raise BaselineError(f"baseline stage {name} exited {result.returncode}")

        validate_trace_catalog_consistency(
            output / "raw_runs.jsonl",
            output / "event_graph.json",
            output / "action_catalog.json",
        )
        observation_path = output / "quality-observation" / "demo_gate_validation.json"
        observation = _read_json(observation_path)
        observed_errors = observation.get("errors")
        if not isinstance(observed_errors, list) or not all(
            isinstance(item, str) for item in observed_errors
        ):
            raise BaselineError("quality observation did not emit string errors")
        _validate_expected_quality_issue(observed_errors, config)
        artifacts = artifact_inventory(output, config["canonical_artifacts"])
        manifest = _read_json(output / "report_manifest.json")
        provenance = manifest.get("provenance")
        if not isinstance(provenance, dict):
            raise BaselineError("baseline report manifest has no provenance")
        status = "ready_with_observed_quality_defect"
        review = {
            "schema_version": REVIEW_SCHEMA,
            "status": status,
            "run_id": config["run_id"],
            "parameters": dict(config["parameters"]),
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "operations": operations,
            "contract_consistency": "passed",
            "invariant_gates": "passed",
            "agent_evaluation": {
                "status": "not_applicable",
                "reason": "canonical Monte Carlo baseline has no recorded persona playthrough",
            },
            "observed_quality_defect": {
                "status": "reproduced",
                "errors": observed_errors,
            },
            "artifacts": artifacts,
            "provenance": provenance,
            "error": "",
        }
    except Exception as exc:
        error = _sanitize(str(exc), project, output, game)
        review = {
            "schema_version": REVIEW_SCHEMA,
            "status": status,
            "run_id": config.get("run_id", "unknown"),
            "parameters": dict(config.get("parameters", {})),
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "operations": operations,
            "error": error,
        }
        _write_json(output / REVIEW_FILE, review)
        raise BaselineError(error) from exc
    _write_json(output / REVIEW_FILE, review)
    _write_json(
        output / MARKER_FILE,
        {
            "schema_version": REVIEW_SCHEMA,
            "run_id": config["run_id"],
            "status": status,
        },
    )
    return review


def build_command_plan(
    config: Mapping[str, Any],
    *,
    project_root: Path,
    output_dir: Path,
) -> list[tuple[str, list[str], set[int]]]:
    """Build the exact existing CLI sequence used by the baseline."""

    tool = project_root / "tools" / "run_gameplay_agent.py"
    python = sys.executable
    parameters = _mapping(config, "parameters")
    common = [python, str(tool)]
    sim = [
        *common,
        "sim",
        "--run-id",
        str(config["run_id"]),
        "--report-dir",
        str(output_dir),
        "--runs",
        str(parameters["runs"]),
        "--policy",
        str(parameters["policy"]),
        "--seed",
        str(parameters["seed"]),
        "--weeks",
        str(parameters["weeks"]),
        "--difficulty",
        str(parameters["difficulty"]),
        "--scenario",
        str(parameters["scenario"]),
    ]
    validate = [*common, "validate", "--report-dir", str(output_dir)]
    for check in config["contract_validators"]:
        validate.extend(["--check", str(check)])
    observation_dir = output_dir / "quality-observation"
    quality_validator = str(_mapping(config, "quality_observation")["validator"])
    gates = project_root / str(config["invariant_gates"])
    return [
        ("simulate_and_analyze", sim, {0}),
        ("export_catalog", [*common, "export", "--report-dir", str(output_dir)], {0}),
        ("reanalyze_with_catalog", [*common, "analyze", "--report-dir", str(output_dir)], {0}),
        ("validate_contracts", validate, {0}),
        (
            "observe_quality_defect",
            [
                *common,
                "validate",
                "--report-dir",
                str(observation_dir),
                "--check",
                quality_validator,
            ],
            {1},
        ),
        (
            "evaluate_invariants",
            [
                *common,
                "gates",
                "--report-dir",
                str(output_dir),
                "--gates",
                str(gates),
                "--out",
                str(output_dir / "invariant_gate_report.json"),
            ],
            {0},
        ),
    ]


def artifact_inventory(root: Path, relative_paths: Sequence[str]) -> list[dict[str, Any]]:
    """Hash every declared deterministic baseline artifact."""

    inventory = []
    for value in relative_paths:
        relative = Path(value)
        path = root / relative
        if not path.is_file():
            raise BaselineError(f"canonical baseline artifact is missing: {relative.as_posix()}")
        inventory.append(
            {
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return inventory


def compare_baselines(
    first: str | Path,
    second: str | Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare canonical artifact bytes from two independent fixed-seed runs."""

    first_items = {item["path"]: item for item in artifact_inventory(Path(first), config["canonical_artifacts"])}
    second_items = {item["path"]: item for item in artifact_inventory(Path(second), config["canonical_artifacts"])}
    mismatches = [
        {
            "path": path,
            "first_sha256": first_items[path]["sha256"],
            "second_sha256": second_items[path]["sha256"],
        }
        for path in sorted(first_items)
        if first_items[path]["sha256"] != second_items[path]["sha256"]
    ]
    return {
        "schema_version": "build-week-baseline-compare-v1",
        "status": "passed" if not mismatches else "failed",
        "artifact_count": len(first_items),
        "mismatches": mismatches,
    }


def _prepare_output(output: Path, *, run_id: str, replace: bool) -> None:
    if output.exists():
        if not replace:
            raise BaselineError("baseline output already exists; use --replace")
        marker = _read_json(output / MARKER_FILE)
        if marker.get("schema_version") != REVIEW_SCHEMA or marker.get("run_id") != run_id:
            raise BaselineError("refusing to replace an unmanaged baseline directory")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    _write_json(
        output / MARKER_FILE,
        {"schema_version": REVIEW_SCHEMA, "run_id": run_id, "status": "started"},
    )


def _validate_expected_quality_issue(errors: Sequence[str], config: Mapping[str, Any]) -> None:
    observation = _mapping(config, "quality_observation")
    expected_count = observation.get("expected_error_count")
    if not isinstance(expected_count, int) or len(errors) != expected_count:
        raise BaselineError(
            f"quality observation error count changed: expected {expected_count}, got {len(errors)}"
        )
    combined = "\n".join(errors)
    missing = [
        fragment
        for fragment in observation["required_error_fragments"]
        if fragment not in combined
    ]
    if missing:
        raise BaselineError(f"expected quality evidence is missing: {', '.join(missing)}")


def _run_command(command: Sequence[str], cwd: Path, env: Mapping[str, str]) -> CommandResult:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
            timeout=1200,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BaselineError(f"unable to run baseline stage: {exc.__class__.__name__}") from exc
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _display_command(command: Sequence[str], *, project: Path, output: Path, game: Path) -> list[str]:
    return [_sanitize(str(item), project, output, game) for item in command]


def _sanitize(value: str, project: Path, output: Path, game: Path) -> str:
    sanitized = value.replace(str(output), "<baseline>")
    sanitized = sanitized.replace(str(game), "<game>")
    sanitized = sanitized.replace(str(project), "<project>")
    sanitized = sanitized.replace(str(Path.home()), "<home>")
    return sanitized


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise BaselineError(f"baseline {key} must be an object")
    return value
