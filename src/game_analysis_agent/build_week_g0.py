"""Fail-closed G0 review for the canonical Build Week baseline."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .build_week_baseline import (
    artifact_inventory,
    compare_baselines,
    load_baseline_config,
)
from .build_week_inventory import collect_inventory
from .build_week_toolchain import evaluate_toolchain, load_toolchain
from .contracts import (
    ContractKind,
    validate_contract_file,
    validate_trace_catalog_consistency,
)

G0_SCHEMA = "build-week-g0-review-v1"
VALIDATOR_FILES = {
    "content": "content_validation.json",
    "json-content": "json_content_validation.json",
    "economy": "economy_validation.json",
    "risk": "risk_guidance_validation.json",
    "route": "route_boundary_validation.json",
}


class G0ReviewError(RuntimeError):
    """Raised when a G0 review cannot be evaluated."""


def review_g0(
    *,
    project_root: str | Path,
    game_root: str | Path,
    baseline_dir: str | Path,
    reproduction_dir: str | Path,
    baseline_config_path: str | Path,
    game_pin_path: str | Path,
    toolchain_path: str | Path,
    execute_commands: bool = True,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Evaluate every P0.5 criterion and return a machine-readable review."""

    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    baseline = Path(baseline_dir).resolve()
    reproduction = Path(reproduction_dir).resolve()
    env = dict(os.environ if environ is None else environ)
    env.update(_contract_environment(game, baseline))
    checks: list[dict[str, Any]] = []
    baseline_config = load_baseline_config(baseline_config_path)
    game_pin = _required_json(Path(game_pin_path))
    toolchain = load_toolchain(toolchain_path)

    _capture(checks, "scope_and_inventory", lambda: _inventory_evidence(project, game, env))
    _capture(checks, "toolchain", lambda: _toolchain_evidence(project, game, env, toolchain))
    _capture(checks, "game_bundle_pin", lambda: _game_pin_evidence(game, game_pin))
    _capture(
        checks,
        "baseline_provenance",
        lambda: _baseline_provenance_evidence(baseline, game_pin),
    )
    _capture(
        checks,
        "baseline_artifact_hashes",
        lambda: _baseline_hash_evidence(baseline, baseline_config),
    )
    _capture(
        checks,
        "fixed_seed_reproduction",
        lambda: _comparison_evidence(baseline, reproduction, baseline_config),
    )
    _capture(
        checks,
        "real_game_contract",
        lambda: _contract_evidence(baseline, baseline_config),
    )
    _capture(
        checks,
        "observed_demo_problem",
        lambda: _quality_evidence(baseline, baseline_config),
    )
    _capture(
        checks,
        "portable_private_bundle",
        lambda: _portability_evidence(project, game, game_pin, toolchain),
    )
    _capture(checks, "sanitized_evidence", lambda: _privacy_evidence(baseline))

    if execute_commands:
        npm = env.get("BUILD_WEEK_NPM_BIN", "npm")
        commands = [
            (
                "frontend_public_build",
                [npm, "--prefix", "frontend", "run", "build:public"],
            ),
            ("frontend_tests", [npm, "--prefix", "frontend", "test"]),
            (
                "frontend_dependency_audit",
                [npm, "--prefix", "frontend", "audit", "--audit-level=moderate"],
            ),
            ("ruff", ["uv", "run", "ruff", "check", "."]),
            ("full_pytest", ["uv", "run", "pytest", "-q", "-ra"]),
        ]
        for check_id, command in commands:
            _capture(
                checks,
                check_id,
                lambda command=command: _command_evidence(command, project, env),
            )

    failures = [item for item in checks if item["status"] != "passed"]
    return {
        "schema_version": G0_SCHEMA,
        "gate": "G0",
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "checks": checks,
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": [item["id"] for item in failures],
    }


def write_g0_review(path: str | Path, review: Mapping[str, Any]) -> Path:
    """Write a G0 review without embedding its host output path."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _capture(checks: list[dict[str, Any]], check_id: str, operation) -> None:
    try:
        evidence = operation()
    except Exception as exc:
        checks.append(
            {
                "id": check_id,
                "status": "failed",
                "evidence": {},
                "error": str(exc),
            }
        )
        return
    checks.append(
        {"id": check_id, "status": "passed", "evidence": evidence, "error": ""}
    )


def _inventory_evidence(project: Path, game: Path, env: Mapping[str, str]) -> dict[str, Any]:
    inventory = collect_inventory(project, game_project_path=game, environ=env)
    readiness = inventory["readiness"]
    if readiness["status"] != "ready":
        raise G0ReviewError(f"inventory has {readiness['blocker_count']} blocker(s)")
    source = inventory["game_repository"]
    return {
        "status": readiness["status"],
        "game_source_type": source.get("source_type", "git"),
        "game_revision": source.get("revision", ""),
        "game_path": source.get("path", ""),
    }


def _toolchain_evidence(
    project: Path,
    game: Path,
    env: Mapping[str, str],
    toolchain: Mapping[str, Any],
) -> dict[str, Any]:
    inventory = collect_inventory(project, game_project_path=game, environ=env)
    result = evaluate_toolchain(inventory, toolchain)
    if result["status"] != "ready":
        raise G0ReviewError(f"toolchain has {result['failure_count']} required failure(s)")
    return {
        "status": result["status"],
        "platform": result["platform"],
        "warning_count": result["warning_count"],
        "warnings": [item["id"] for item in result["checks"] if item["status"] == "warning"],
    }


def _game_pin_evidence(game: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    marker = _required_json(game / ".playtest-forge-source.json")
    pin = _mapping(manifest, "pin")
    for key in ("commit", "tree", "archive_sha256", "file_count"):
        if marker.get(key) != pin.get(key):
            raise G0ReviewError(f"materialized game {key} does not match pin")
    return {key: marker[key] for key in ("commit", "tree", "archive_sha256", "file_count")}


def _baseline_provenance_evidence(
    baseline: Path, game_pin: Mapping[str, Any]
) -> dict[str, Any]:
    review = _required_json(baseline / "baseline_review.json")
    if review.get("status") != "ready_with_observed_quality_defect":
        raise G0ReviewError("baseline review is not ready")
    provenance = _mapping(review, "provenance")
    agent = _mapping(provenance, "agent_repository")
    game = _mapping(provenance, "game_repository")
    if agent.get("dirty") is not False or not agent.get("commit"):
        raise G0ReviewError("baseline was not generated from a clean Agent commit")
    pin = _mapping(game_pin, "pin")
    if game.get("commit") != pin.get("commit") or game.get("tree") != pin.get("tree"):
        raise G0ReviewError("baseline game provenance differs from canonical pin")
    return {
        "agent_commit": agent["commit"],
        "agent_dirty": agent["dirty"],
        "game_commit": game["commit"],
        "game_tree": game["tree"],
        "execution_source_sha256": _mapping(provenance, "fingerprints").get(
            "execution_source_sha256", ""
        ),
    }


def _baseline_hash_evidence(
    baseline: Path, config: Mapping[str, Any]
) -> dict[str, Any]:
    review = _required_json(baseline / "baseline_review.json")
    declared = {
        item["path"]: item["sha256"]
        for item in review.get("artifacts", [])
        if isinstance(item, dict) and item.get("path") and item.get("sha256")
    }
    observed = artifact_inventory(baseline, config["canonical_artifacts"])
    mismatches = [item["path"] for item in observed if declared.get(item["path"]) != item["sha256"]]
    if mismatches:
        raise G0ReviewError(f"baseline artifact hash mismatch: {', '.join(mismatches)}")
    return {"artifact_count": len(observed), "mismatches": []}


def _comparison_evidence(
    baseline: Path, reproduction: Path, config: Mapping[str, Any]
) -> dict[str, Any]:
    comparison = compare_baselines(baseline, reproduction, config)
    if comparison["status"] != "passed":
        raise G0ReviewError(f"{len(comparison['mismatches'])} canonical artifact(s) differ")
    return comparison


def _contract_evidence(baseline: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    trace = baseline / "raw_runs.jsonl"
    graph = baseline / "event_graph.json"
    catalog = baseline / "action_catalog.json"
    validate_contract_file(trace, kind=ContractKind.TRACE)
    validate_contract_file(graph, kind=ContractKind.EVENT_GRAPH)
    validate_contract_file(catalog, kind=ContractKind.ACTION_CATALOG)
    validate_trace_catalog_consistency(trace, graph, catalog)
    validated = []
    for check in config["contract_validators"]:
        file_name = VALIDATOR_FILES.get(str(check))
        if not file_name:
            raise G0ReviewError(f"unknown contract validator: {check}")
        validate_contract_file(
            baseline / file_name,
            kind=ContractKind.VALIDATOR_REPORT,
            require_clean=True,
        )
        validated.append(file_name)
    return {"trace_catalog_consistency": "passed", "clean_validators": validated}


def _quality_evidence(baseline: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    observation = _required_json(
        baseline / "quality-observation" / "demo_gate_validation.json"
    )
    errors = observation.get("errors")
    expected = _mapping(config, "quality_observation")
    if not isinstance(errors, list) or len(errors) != expected.get("expected_error_count"):
        raise G0ReviewError("observed demo problem changed error count")
    combined = "\n".join(str(item) for item in errors)
    missing = [item for item in expected["required_error_fragments"] if item not in combined]
    if missing:
        raise G0ReviewError(f"observed demo evidence is missing: {', '.join(missing)}")
    return {"status": "reproduced", "errors": errors}


def _portability_evidence(
    project: Path,
    game: Path,
    game_pin: Mapping[str, Any],
    toolchain: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        relative_game = game.relative_to(project).as_posix()
    except ValueError as exc:
        raise G0ReviewError("game bundle is not repository-relative") from exc
    packaging = _mapping(game_pin, "packaging")
    if packaging.get("distribution_status") != "approved_by_owner":
        raise G0ReviewError("private bundle distribution is not owner-approved")
    node_assets = set(_mapping(_mapping(toolchain, "node"), "assets"))
    godot_assets = set(_mapping(_mapping(toolchain, "godot"), "assets"))
    if not {"darwin-arm64", "linux-amd64", "linux-arm64"}.issubset(node_assets):
        raise G0ReviewError("Node assets do not cover declared platforms")
    if not {"darwin-arm64", "linux-amd64"}.issubset(godot_assets):
        raise G0ReviewError("Godot assets do not cover macOS and Linux amd64")
    return {
        "bundle_path": relative_game,
        "distribution_status": packaging["distribution_status"],
        "native_runtime_assets": ["darwin-arm64", "linux-amd64"],
        "linux_arm64_mode": "Replay or external Godot runtime",
    }


def _privacy_evidence(baseline: Path) -> dict[str, Any]:
    files = [
        baseline / "baseline_review.json",
        baseline / "validation_summary.json",
        baseline / "report_manifest.json",
        baseline / "quality-observation" / "validation_summary.json",
        baseline / "quality-observation" / "report_manifest.json",
    ]
    pattern = re.compile(r"/(?:Users|home)/[^/\s\"']+")
    leaks = []
    for path in files:
        if path.is_file() and pattern.search(path.read_text(encoding="utf-8")):
            leaks.append(path.name)
    if leaks:
        raise G0ReviewError(f"absolute user path found in: {', '.join(leaks)}")
    return {"files_checked": len(files), "absolute_user_paths": 0}


def _command_evidence(
    command: Sequence[str], project: Path, env: Mapping[str, str]
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=project,
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise G0ReviewError(f"review command unavailable: {exc.__class__.__name__}") from exc
    stdout = _sanitize_output(completed.stdout[-3000:], project)
    stderr = _sanitize_output(completed.stderr[-3000:], project)
    if completed.returncode != 0:
        raise G0ReviewError(
            f"command exited {completed.returncode}: {(stderr or stdout).strip()[:500]}"
        )
    return {
        "command": [Path(command[0]).name, *command[1:]],
        "returncode": completed.returncode,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
    }


def _contract_environment(game: Path, baseline: Path) -> dict[str, str]:
    return {
        "GAME_PROJECT_PATH": str(game),
        "GAME_CONTRACT_TRACE": str(baseline / "raw_runs.jsonl"),
        "GAME_CONTRACT_EVENT_GRAPH": str(baseline / "event_graph.json"),
        "GAME_CONTRACT_ACTION_CATALOG": str(baseline / "action_catalog.json"),
        "GAME_CONTRACT_VALIDATOR": str(baseline / "content_validation.json"),
    }


def _sanitize_output(value: str, project: Path) -> str:
    sanitized = value.replace(str(project), "<project>")
    return sanitized.replace(str(Path.home()), "<home>")


def _required_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise G0ReviewError(f"required JSON is unavailable: {path.name}") from exc
    if not isinstance(payload, dict):
        raise G0ReviewError(f"required JSON is not an object: {path.name}")
    return payload


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise G0ReviewError(f"G0 evidence {key} must be an object")
    return value
