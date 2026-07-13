"""Strict, resumable execution of the gameplay test matrix.

The module deliberately keeps orchestration separate from the CLI.  It turns
``config/matrix.yaml`` into immutable command plans and accepts an injected
executor, so callers can use the real subprocess runner while tests stay
independent from Godot and an LLM provider.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from collections import Counter
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from game_analysis_agent.agent_eval import evaluate_playthrough
from game_analysis_agent.contracts import (
    ContractKind,
    ContractValidationError,
    validate_contract_file,
    validate_trace_catalog_consistency,
)
from game_analysis_agent.report_manifest import execution_source_fingerprint

MATRIX_MANIFEST_FILE = "matrix_manifest.json"
MATRIX_SUMMARY_FILE = "matrix_summary.json"
CELL_MANIFEST_FILE = "cell_manifest.json"
SCHEMA_VERSION = "test-matrix-v1"
CELL_STATUSES = ("planned", "running", "completed", "failed", "skipped")
_SHARED_GODOT_OUTPUT_LOCK = threading.Lock()

_SUCCESS_ENDINGS = {
    "work_warrior",
    "career_launch",
    "high_pressure_top_student",
    "social_connector",
    "stable_start",
}
_RECOVERY_ENDINGS = {"delayed_enrollment", "survival_struggle"}
_DESIGNED_FAILURE_ENDINGS = {
    "forced_departure",
    "cashflow_collapse",
    "living_imbalance",
    "burnout_pause",
    "registration_failure",
    "academic_failure",
    "work_law_trouble",
    "romance_bankrupt",
    "admin_collapse",
    "mental_crash",
}

CellKind = Literal["simulation", "boundary", "persona"]


class MatrixConfigError(ValueError):
    """Raised when the matrix file does not conform to the strict schema."""


@dataclass(frozen=True)
class BoundaryConfig:
    runs: int
    seed: int
    weeks: int
    policy: str
    extremes: tuple[str, ...]


@dataclass(frozen=True)
class OutcomeCoverageConfig:
    success_is_not_required_per_persona: bool
    designed_failure_is_valid: bool
    expected_categories: tuple[str, ...]
    invalid_endings: tuple[str, ...]


@dataclass(frozen=True)
class PlayConfig:
    default_persona: str
    personas: tuple[str, ...]
    weeks: int
    difficulty: str
    seeds: tuple[int, ...]
    outcome_coverage: OutcomeCoverageConfig


@dataclass(frozen=True)
class CompareConfig:
    output_dir: str
    include: tuple[str, ...]


@dataclass(frozen=True)
class MatrixConfig:
    source_path: Path
    version: str
    weeks: int
    runs_per_cell: int
    seeds: tuple[int, ...]
    difficulties: tuple[str, ...]
    policies: tuple[str, ...]
    policy_aliases: Mapping[str, str]
    scenarios: tuple[str, ...]
    boundary: BoundaryConfig
    play: PlayConfig
    compare: CompareConfig
    config_hash: str
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class MatrixCell:
    kind: CellKind
    cell_id: str
    run_id: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class CommandPlan:
    cell: MatrixCell
    code_fingerprint: str
    argv: tuple[str, ...]
    cwd: Path
    report_dir: Path
    manifest_path: Path


@dataclass(frozen=True)
class MatrixExecutionPlan:
    matrix_id: str
    code_fingerprint: str
    config: MatrixConfig
    matrix_dir: Path
    cells: tuple[CommandPlan, ...]


@dataclass(frozen=True)
class ExecutionOutcome:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Executor = Callable[[CommandPlan], ExecutionOutcome | subprocess.CompletedProcess[str] | int]


@dataclass(frozen=True)
class MatrixRunResult:
    matrix_id: str
    status: str
    manifest_path: Path
    summary_path: Path
    summary: Mapping[str, Any]
    cells: tuple[Mapping[str, Any], ...]

    @property
    def exit_code(self) -> int:
        return 1 if self.status == "failed" else 0


def load_matrix_config(path: str | Path) -> MatrixConfig:
    """Load and strictly validate a matrix YAML file.

    Unknown keys are rejected at every schema level.  Counts, durations, and
    seeds must be positive integers (``bool`` is intentionally not accepted as
    an integer by this schema).
    """

    source_path = Path(path).resolve()
    try:
        payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MatrixConfigError(f"cannot read matrix config {source_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise MatrixConfigError(f"invalid YAML in {source_path}: {exc}") from exc

    root = _mapping(payload, "matrix")
    _keys(
        root,
        path="matrix",
        required={
            "version",
            "weeks",
            "runs_per_cell",
            "seeds",
            "difficulties",
            "policies",
            "policy_aliases",
            "scenarios",
            "boundary",
            "play",
            "compare",
        },
    )

    version = _string(root["version"], "matrix.version")
    weeks = _positive_int(root["weeks"], "matrix.weeks")
    runs_per_cell = _positive_int(root["runs_per_cell"], "matrix.runs_per_cell")
    seeds = _positive_int_list(root["seeds"], "matrix.seeds")
    ordered_seeds = sorted(seeds)
    for left, right in zip(ordered_seeds, ordered_seeds[1:], strict=False):
        if right - left < runs_per_cell:
            raise MatrixConfigError(
                "matrix.seeds batches overlap: base seeds must differ by at least "
                "matrix.runs_per_cell"
            )
    difficulties = _string_list(root["difficulties"], "matrix.difficulties")
    policies = _string_list(root["policies"], "matrix.policies")
    scenarios = _string_list(root["scenarios"], "matrix.scenarios")

    aliases_raw = _mapping(root["policy_aliases"], "matrix.policy_aliases")
    aliases: dict[str, str] = {}
    for alias, target in aliases_raw.items():
        alias_name = _string(alias, "matrix.policy_aliases key")
        target_name = _string(target, f"matrix.policy_aliases.{alias_name}")
        if target_name not in policies:
            raise MatrixConfigError(
                f"matrix.policy_aliases.{alias_name} targets unknown policy {target_name!r}"
            )
        if alias_name in policies:
            raise MatrixConfigError(
                f"matrix.policy_aliases key {alias_name!r} duplicates a canonical policy"
            )
        aliases[alias_name] = target_name

    boundary_raw = _mapping(root["boundary"], "matrix.boundary")
    _keys(
        boundary_raw,
        path="matrix.boundary",
        required={"runs", "seed", "weeks", "policy", "extremes"},
    )
    boundary_policy = _string(boundary_raw["policy"], "matrix.boundary.policy")
    canonical_boundary_policy = aliases.get(boundary_policy, boundary_policy)
    if canonical_boundary_policy not in policies:
        raise MatrixConfigError(
            f"matrix.boundary.policy references unknown policy {boundary_policy!r}"
        )
    boundary = BoundaryConfig(
        runs=_positive_int(boundary_raw["runs"], "matrix.boundary.runs"),
        seed=_positive_int(boundary_raw["seed"], "matrix.boundary.seed"),
        weeks=_positive_int(boundary_raw["weeks"], "matrix.boundary.weeks"),
        policy=canonical_boundary_policy,
        extremes=_string_list(boundary_raw["extremes"], "matrix.boundary.extremes"),
    )

    play_raw = _mapping(root["play"], "matrix.play")
    _keys(
        play_raw,
        path="matrix.play",
        required={
            "default_persona",
            "personas",
            "weeks",
            "difficulty",
            "seeds",
            "outcome_coverage",
        },
    )
    personas = _string_list(play_raw["personas"], "matrix.play.personas")
    default_persona = _string(play_raw["default_persona"], "matrix.play.default_persona")
    if default_persona not in personas:
        raise MatrixConfigError(
            "matrix.play.default_persona must be listed in matrix.play.personas"
        )
    play_difficulty = _string(play_raw["difficulty"], "matrix.play.difficulty")
    if play_difficulty not in difficulties:
        raise MatrixConfigError(
            f"matrix.play.difficulty references unknown difficulty {play_difficulty!r}"
        )
    coverage_raw = _mapping(play_raw["outcome_coverage"], "matrix.play.outcome_coverage")
    _keys(
        coverage_raw,
        path="matrix.play.outcome_coverage",
        required={
            "success_is_not_required_per_persona",
            "designed_failure_is_valid",
            "expected_categories",
            "invalid_endings",
        },
    )
    coverage = OutcomeCoverageConfig(
        success_is_not_required_per_persona=_boolean(
            coverage_raw["success_is_not_required_per_persona"],
            "matrix.play.outcome_coverage.success_is_not_required_per_persona",
        ),
        designed_failure_is_valid=_boolean(
            coverage_raw["designed_failure_is_valid"],
            "matrix.play.outcome_coverage.designed_failure_is_valid",
        ),
        expected_categories=_string_list(
            coverage_raw["expected_categories"],
            "matrix.play.outcome_coverage.expected_categories",
        ),
        invalid_endings=_string_list(
            coverage_raw["invalid_endings"],
            "matrix.play.outcome_coverage.invalid_endings",
        ),
    )
    play = PlayConfig(
        default_persona=default_persona,
        personas=personas,
        weeks=_positive_int(play_raw["weeks"], "matrix.play.weeks"),
        difficulty=play_difficulty,
        seeds=_positive_int_list(play_raw["seeds"], "matrix.play.seeds"),
        outcome_coverage=coverage,
    )

    compare_raw = _mapping(root["compare"], "matrix.compare")
    _keys(compare_raw, path="matrix.compare", required={"output_dir", "include"})
    compare = CompareConfig(
        output_dir=_string(compare_raw["output_dir"], "matrix.compare.output_dir"),
        include=_string_list(compare_raw["include"], "matrix.compare.include"),
    )

    canonical_json = json.dumps(root, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    config_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return MatrixConfig(
        source_path=source_path,
        version=version,
        weeks=weeks,
        runs_per_cell=runs_per_cell,
        seeds=seeds,
        difficulties=difficulties,
        policies=policies,
        policy_aliases=dict(aliases),
        scenarios=scenarios,
        boundary=boundary,
        play=play,
        compare=compare,
        config_hash=config_hash,
        raw=dict(root),
    )


def expand_matrix_cells(config: MatrixConfig) -> tuple[MatrixCell, ...]:
    """Expand simulation, boundary, and interactive-persona matrix cells."""

    cells: list[MatrixCell] = []
    for difficulty in config.difficulties:
        for policy in config.policies:
            for scenario in config.scenarios:
                for seed in config.seeds:
                    parameters = {
                        "runs": config.runs_per_cell,
                        "weeks": config.weeks,
                        "difficulty": difficulty,
                        "policy": policy,
                        "scenario": scenario,
                        "seed": seed,
                    }
                    cells.append(_cell(config, "simulation", parameters))

    for extreme in config.boundary.extremes:
        parameters = {
            "runs": config.boundary.runs,
            "weeks": config.boundary.weeks,
            "policy": config.boundary.policy,
            "seed": config.boundary.seed,
            "extreme": extreme,
        }
        cells.append(_cell(config, "boundary", parameters))

    # The first scenario is the configured baseline for persona coverage.  A
    # future schema version can add an explicit play.scenarios dimension
    # without silently changing v1's number of cells.
    persona_scenario = config.scenarios[0]
    for persona in config.play.personas:
        for seed in config.play.seeds:
            parameters = {
                "persona": persona,
                "weeks": config.play.weeks,
                "difficulty": config.play.difficulty,
                "scenario": persona_scenario,
                "seed": seed,
            }
            cells.append(_cell(config, "persona", parameters))

    cell_ids = [cell.cell_id for cell in cells]
    run_ids = [cell.run_id for cell in cells]
    if len(cell_ids) != len(set(cell_ids)) or len(run_ids) != len(set(run_ids)):
        raise MatrixConfigError("matrix expansion produced duplicate cell or run ids")
    return tuple(cells)


def build_matrix_plan(
    config: MatrixConfig,
    *,
    project_root: str | Path,
    matrix_dir: str | Path | None = None,
    python_executable: str | Path | None = None,
    simulation_command: Literal["all", "sim"] = "all",
    catalog_dir: str | Path | None = None,
) -> MatrixExecutionPlan:
    """Build an immutable command plan suitable for CLI or programmatic use."""

    if simulation_command not in {"all", "sim"}:
        raise ValueError("simulation_command must be 'all' or 'sim'")
    root = Path(project_root).resolve()
    matrix_id = f"matrix-{_slug(config.version)}-{config.config_hash[:12]}"
    output_dir = (
        Path(matrix_dir).resolve()
        if matrix_dir is not None
        else root / "reports" / "matrix" / matrix_id
    )
    python = str(python_executable or sys.executable)
    game_root = Path(os.environ.get("GAME_PROJECT_PATH", str(root.parent / "study-in-germany")))
    code_fingerprint = execution_source_fingerprint(root, game_root)
    runner = root / "tools" / "run_gameplay_agent.py"
    reports_root = output_dir / "reports"
    plans: list[CommandPlan] = []

    for cell in expand_matrix_cells(config):
        params = cell.parameters
        if cell.kind == "simulation":
            report_dir = reports_root / "balance" / cell.run_id
            simulation_args = (
                python,
                str(runner),
                simulation_command,
                "--run-id",
                cell.run_id,
                "--runs",
                str(params["runs"]),
                "--policy",
                str(params["policy"]),
                "--seed",
                str(params["seed"]),
                "--weeks",
                str(params["weeks"]),
                "--difficulty",
                str(params["difficulty"]),
                "--scenario",
                str(params["scenario"]),
                "--report-dir",
                str(report_dir),
            )
            argv = (
                *simulation_args,
                *(("--catalog-dir", str(Path(catalog_dir).resolve())) if catalog_dir else ()),
            )
        elif cell.kind == "boundary":
            report_dir = reports_root / "boundary" / cell.run_id
            argv = (
                python,
                str(runner),
                "probe",
                "--run-id",
                cell.run_id,
                "--runs",
                str(params["runs"]),
                "--policy",
                str(params["policy"]),
                "--seed",
                str(params["seed"]),
                "--weeks",
                str(params["weeks"]),
                "--report-dir",
                str(report_dir),
                "--extreme",
                str(params["extreme"]),
            )
        else:
            report_dir = reports_root / "play" / cell.run_id
            argv = (
                python,
                str(runner),
                "play",
                "--report-dir",
                str(report_dir),
                "--persona",
                str(params["persona"]),
                "--seed",
                str(params["seed"]),
                "--weeks",
                str(params["weeks"]),
                "--difficulty",
                str(params["difficulty"]),
                "--scenario",
                str(params["scenario"]),
            )
        plans.append(
            CommandPlan(
                cell=cell,
                code_fingerprint=code_fingerprint,
                argv=argv,
                cwd=root,
                report_dir=report_dir,
                manifest_path=output_dir / "cells" / cell.cell_id / CELL_MANIFEST_FILE,
            )
        )
    return MatrixExecutionPlan(
        matrix_id=matrix_id,
        code_fingerprint=code_fingerprint,
        config=config,
        matrix_dir=output_dir,
        cells=tuple(plans),
    )


def run_matrix_file(
    config_path: str | Path,
    *,
    project_root: str | Path,
    matrix_dir: str | Path | None = None,
    jobs: int = 1,
    dry_run: bool = False,
    resume: bool = False,
    executor: Executor | None = None,
    simulation_command: Literal["all", "sim"] = "all",
    verify_evidence: bool = True,
    catalog_dir: str | Path | None = None,
) -> MatrixRunResult:
    """Convenience entry point for a CLI: load, plan, execute, and persist."""

    config = load_matrix_config(config_path)
    plan = build_matrix_plan(
        config,
        project_root=project_root,
        matrix_dir=matrix_dir,
        simulation_command=simulation_command,
        catalog_dir=catalog_dir,
    )
    return execute_matrix(
        plan,
        jobs=jobs,
        dry_run=dry_run,
        resume=resume,
        executor=executor,
        verify_evidence=verify_evidence,
    )


def execute_matrix(
    plan: MatrixExecutionPlan,
    *,
    jobs: int = 1,
    dry_run: bool = False,
    resume: bool = False,
    executor: Executor | None = None,
    verify_evidence: bool = True,
) -> MatrixRunResult:
    """Execute a plan with safe per-cell persistence and optional concurrency."""

    jobs = _positive_int(jobs, "jobs")
    active_executor = executor or subprocess_executor
    started_at = _now()
    entries = [_planned_entry(item) for item in plan.cells]

    runnable: list[CommandPlan] = []
    for index, item in enumerate(plan.cells):
        previous = _read_json(item.manifest_path)
        if resume and _completed_for_plan(
            previous,
            plan,
            item,
            verify_evidence=verify_evidence,
        ):
            evidence = _cell_evidence(item, plan.config) if verify_evidence else {}
            entries[index] = {
                **entries[index],
                **evidence,
                "status": "skipped",
                "exit_code": 0,
                "started_at": previous.get("started_at"),
                "finished_at": previous.get("finished_at"),
                "resumed_from": str(item.manifest_path),
            }
        else:
            runnable.append(item)

    status = "planned" if dry_run else "running"
    _write_matrix_state(
        plan,
        entries,
        status=status,
        jobs=jobs,
        dry_run=dry_run,
        resume=resume,
        started_at=started_at,
        finished_at=None,
    )
    if dry_run:
        return _result_from_disk(plan)

    index_by_cell = {entry["cell_id"]: index for index, entry in enumerate(entries)}
    if jobs == 1:
        for item in runnable:
            outcome = _execute_cell(
                plan,
                item,
                active_executor,
                verify_evidence=verify_evidence,
            )
            entries[index_by_cell[item.cell.cell_id]] = outcome
            _write_matrix_state(
                plan,
                entries,
                status="running",
                jobs=jobs,
                dry_run=False,
                resume=resume,
                started_at=started_at,
                finished_at=None,
            )
    else:
        with ThreadPoolExecutor(max_workers=jobs, thread_name_prefix="matrix-cell") as pool:
            futures = {
                pool.submit(
                    _execute_cell,
                    plan,
                    item,
                    active_executor,
                    verify_evidence=verify_evidence,
                ): item
                for item in runnable
            }
            for future in as_completed(futures):
                item = futures[future]
                # _execute_cell catches executor errors.  This guard also makes
                # orchestration bugs observable in the matrix instead of
                # abandoning all remaining futures.
                try:
                    outcome = future.result()
                except Exception as exc:  # pragma: no cover - defensive guard
                    outcome = _failed_entry(item, error=f"orchestration error: {exc}")
                    _write_cell_manifest(plan, item, outcome)
                entries[index_by_cell[item.cell.cell_id]] = outcome
                _write_matrix_state(
                    plan,
                    entries,
                    status="running",
                    jobs=jobs,
                    dry_run=False,
                    resume=resume,
                    started_at=started_at,
                    finished_at=None,
                )

    finished_at = _now()
    outcome_coverage = _persona_outcome_coverage(plan.config, entries) if verify_evidence else None
    final_status = (
        "failed"
        if any(row["status"] == "failed" for row in entries)
        or bool(outcome_coverage and outcome_coverage["missing_categories"])
        else "completed"
    )
    _write_matrix_state(
        plan,
        entries,
        status=final_status,
        jobs=jobs,
        dry_run=False,
        resume=resume,
        started_at=started_at,
        finished_at=finished_at,
        outcome_coverage=outcome_coverage,
    )
    return _result_from_disk(plan)


def subprocess_executor(plan: CommandPlan) -> ExecutionOutcome:
    """Run one cell while protecting only shared validator prerequisites.

    ``sim`` and ``probe`` pass unique absolute outputs and can run in
    parallel. ``all`` also writes shared route/demo inputs in the Godot
    project, so those cells remain serialized.
    """

    uses_shared_validation = (
        plan.cell.kind == "simulation" and len(plan.argv) > 2 and plan.argv[2] == "all"
    )
    if not uses_shared_validation:
        return _run_subprocess(plan)
    with _SHARED_GODOT_OUTPUT_LOCK:
        return _run_subprocess(plan)


def _run_subprocess(plan: CommandPlan) -> ExecutionOutcome:
    """Default executor used by the CLI integration."""

    completed = subprocess.run(
        plan.argv,
        cwd=plan.cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    return ExecutionOutcome(completed.returncode, completed.stdout, completed.stderr)


def _cell(config: MatrixConfig, kind: CellKind, parameters: dict[str, Any]) -> MatrixCell:
    identity = {
        "config_hash": config.config_hash,
        "kind": kind,
        "parameters": parameters,
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:12]
    if kind == "simulation":
        label = (
            f"{parameters['difficulty']}-{parameters['policy']}-"
            f"{parameters['scenario']}-s{parameters['seed']}"
        )
    elif kind == "boundary":
        label = f"{parameters['extreme']}-{parameters['policy']}-s{parameters['seed']}"
    else:
        label = f"{parameters['persona']}-{parameters['difficulty']}-s{parameters['seed']}"
    cell_id = f"{kind}-{_slug(label)}-{digest}"
    return MatrixCell(
        kind=kind,
        cell_id=cell_id,
        run_id=f"{_slug(config.version)}-{cell_id}",
        parameters=dict(parameters),
    )


def _execute_cell(
    matrix_plan: MatrixExecutionPlan,
    command_plan: CommandPlan,
    executor: Executor,
    *,
    verify_evidence: bool,
) -> dict[str, Any]:
    previous = _read_json(command_plan.manifest_path)
    try:
        previous_attempt = int(previous.get("attempt", 0))
    except (TypeError, ValueError):
        previous_attempt = 0
    started_at = _now()
    running = {
        **_planned_entry(command_plan),
        "status": "running",
        "attempt": previous_attempt + 1,
        "started_at": started_at,
        "finished_at": None,
        "exit_code": None,
        "error": "",
    }
    _write_cell_manifest(matrix_plan, command_plan, running)
    try:
        outcome = _normalize_outcome(executor(command_plan))
    except Exception as exc:
        final = {
            **running,
            "status": "failed",
            "finished_at": _now(),
            "error": f"{type(exc).__name__}: {exc}",
        }
        _write_cell_manifest(matrix_plan, command_plan, final)
        return final

    evidence: dict[str, Any] = {}
    evidence_error = ""
    if outcome.returncode == 0 and verify_evidence:
        try:
            evidence = _cell_evidence(command_plan, matrix_plan.config)
        except (OSError, ValueError, ContractValidationError) as exc:
            evidence_error = f"evidence validation failed: {exc}"

    stderr_tail = _tail(outcome.stderr)
    stdout_tail = _tail(outcome.stdout)
    completed = outcome.returncode == 0 and not evidence_error
    final = {
        **running,
        **evidence,
        "status": "completed" if completed else "failed",
        "finished_at": _now(),
        "exit_code": outcome.returncode
        if outcome.returncode != 0
        else (8 if evidence_error else 0),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "error": ""
        if completed
        else (evidence_error or stderr_tail or f"command exited with code {outcome.returncode}"),
    }
    _write_cell_manifest(matrix_plan, command_plan, final)
    return final


def _normalize_outcome(
    outcome: ExecutionOutcome | subprocess.CompletedProcess[str] | int,
) -> ExecutionOutcome:
    if isinstance(outcome, ExecutionOutcome):
        return outcome
    if isinstance(outcome, subprocess.CompletedProcess):
        return ExecutionOutcome(
            returncode=int(outcome.returncode),
            stdout=str(outcome.stdout or ""),
            stderr=str(outcome.stderr or ""),
        )
    if type(outcome) is int:
        return ExecutionOutcome(returncode=outcome)
    raise TypeError("executor must return ExecutionOutcome, CompletedProcess, or int")


def _cell_evidence(plan: CommandPlan, config: MatrixConfig) -> dict[str, Any]:
    required = {
        "simulation": (
            "report_manifest.json",
            "raw_runs.jsonl",
            "summary.json",
            "ending_distribution.csv",
            "action_pick_rates.csv",
            "weekly_stats.csv",
            "coverage_report.json",
            "anomalies.jsonl",
            "value_report.json",
            "route_report.json",
            "event_graph.json",
            "action_catalog.json",
        ),
        "boundary": (
            "report_manifest.json",
            "boundary_runs.jsonl",
            "anomalies.jsonl",
            "value_report.json",
            "route_report.json",
        ),
        "persona": (
            "report_manifest.json",
            "playthrough.jsonl",
            "playthrough_agent_report.json",
            "playthrough_summary.md",
            "agent_eval.json",
        ),
    }[plan.cell.kind]
    missing = [name for name in required if not (plan.report_dir / name).is_file()]
    if missing:
        raise ValueError(f"missing required report artifacts: {missing}")

    manifest = _read_required_object(plan.report_dir / "report_manifest.json")
    if manifest.get("schema_version") != "trace-manifest-v2":
        raise ValueError("report_manifest.json has the wrong schema_version")
    if manifest.get("run_id") != plan.cell.run_id:
        raise ValueError("report_manifest.json run_id does not match the matrix cell")
    if manifest.get("status") != "completed":
        raise ValueError("report_manifest.json status must be completed")
    report_fingerprint = ((manifest.get("provenance") or {}).get("fingerprints") or {}).get(
        "execution_source_sha256"
    )
    expected_fingerprint = plan.code_fingerprint
    if report_fingerprint != expected_fingerprint:
        raise ValueError(
            "report_manifest.json runtime source fingerprint does not match the matrix plan"
        )

    if plan.cell.kind == "simulation":
        validate_contract_file(plan.report_dir / "raw_runs.jsonl", kind=ContractKind.TRACE)
        _require_json_keys(
            plan.report_dir / "summary.json",
            {"total_runs", "policies", "top_events"},
        )
        _validate_csv_columns(
            plan.report_dir / "ending_distribution.csv",
            {
                "policy",
                "difficulty",
                "scenario",
                "ending_id",
                "count",
                "sample_size",
                "rate",
                "ci95_low",
                "ci95_high",
            },
        )
        _validate_csv_columns(
            plan.report_dir / "action_pick_rates.csv",
            {"policy", "action_id", "count", "rate_per_run"},
        )
        _validate_csv_columns(
            plan.report_dir / "weekly_stats.csv",
            {"policy", "week", "metric", "mean", "median", "p10", "p90", "min", "max"},
        )
        _require_json_keys(
            plan.report_dir / "value_report.json",
            {"finding_count", "by_kind", "findings"},
        )
        _require_json_keys(
            plan.report_dir / "route_report.json",
            {
                "finding_count",
                "by_kind",
                "axes",
                "groups",
                "crisis_response",
                "ending_contradictions",
                "route_separation",
            },
        )
        coverage = _read_required_object(plan.report_dir / "coverage_report.json")
        if coverage.get("schema_version") != "coverage-v2":
            raise ValueError("coverage_report.json has the wrong schema_version")
        catalog_errors = (coverage.get("data_quality") or {}).get("catalog_errors", [])
        if catalog_errors:
            raise ValueError(f"coverage catalog errors: {catalog_errors}")
        if not coverage.get("event_coverage", {}).get("catalog_available"):
            raise ValueError("coverage report has no event catalog denominator")
        if not coverage.get("action_coverage", {}).get("catalog_available"):
            raise ValueError("coverage report has no action catalog denominator")
        validate_trace_catalog_consistency(
            plan.report_dir / "raw_runs.jsonl",
            plan.report_dir / "event_graph.json",
            plan.report_dir / "action_catalog.json",
        )
        return {}

    if plan.cell.kind == "boundary":
        validate_contract_file(
            plan.report_dir / "boundary_runs.jsonl",
            kind=ContractKind.BOUNDARY_TRACE,
        )
        _require_json_keys(
            plan.report_dir / "value_report.json",
            {"finding_count", "by_kind", "findings"},
        )
        _require_json_keys(
            plan.report_dir / "route_report.json",
            {"finding_count", "by_kind", "axes", "groups"},
        )
        return {}

    agent_eval = _read_required_object(plan.report_dir / "agent_eval.json")
    if agent_eval.get("schema_version") != "agent-eval-v1":
        raise ValueError("agent_eval.json has the wrong schema_version")
    if agent_eval.get("valid") is not True or agent_eval.get("errors") != []:
        raise ValueError("agent_eval.json is not valid and clean")
    recomputed = evaluate_playthrough(plan.report_dir)
    if recomputed.get("valid") is not True:
        raise ValueError(f"playthrough evidence is invalid: {recomputed.get('errors', [])}")
    if recomputed.get("metrics") != agent_eval.get("metrics"):
        raise ValueError("agent_eval.json metrics do not match the recorded playthrough")
    ending = str(agent_eval.get("final_ending") or "")
    if not ending:
        raise ValueError("agent_eval.json final_ending is empty")
    if recomputed.get("final_ending") != ending:
        raise ValueError("agent_eval.json ending does not match playthrough_summary.md")
    if ending in config.play.outcome_coverage.invalid_endings:
        raise ValueError(f"persona reached invalid ending {ending!r}")
    category = _ending_category(ending)
    if category == "unclassified":
        raise ValueError(f"persona ending {ending!r} has no configured category")
    coverage = config.play.outcome_coverage
    if category == "designed_failure" and not coverage.designed_failure_is_valid:
        raise ValueError("designed failure endings are disabled by matrix config")
    if not coverage.success_is_not_required_per_persona and category != "success":
        raise ValueError("matrix config requires every persona to reach a success ending")
    return {"final_ending": ending, "outcome_category": category}


def _read_required_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} root must be an object")
    return payload


def _require_json_keys(path: Path, keys: set[str]) -> dict[str, Any]:
    payload = _read_required_object(path)
    missing = sorted(keys - set(payload))
    if missing:
        raise ValueError(f"{path.name} is missing required keys: {missing}")
    return payload


def _validate_csv_columns(path: Path, required: set[str]) -> None:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            missing = sorted(required - columns)
            if missing:
                raise ValueError(f"{path.name} is missing required columns: {missing}")
            for row in reader:
                if None in row:
                    raise ValueError(f"{path.name} has a row wider than its header")
    except (OSError, csv.Error) as exc:
        raise ValueError(f"cannot read {path.name}: {exc}") from exc


def _ending_category(ending: str) -> str:
    if ending in _SUCCESS_ENDINGS:
        return "success"
    if ending in _RECOVERY_ENDINGS:
        return "recovery_or_mixed"
    if ending in _DESIGNED_FAILURE_ENDINGS:
        return "designed_failure"
    return "unclassified"


def _persona_outcome_coverage(
    config: MatrixConfig,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    categories = Counter(
        str(entry["outcome_category"])
        for entry in entries
        if entry.get("kind") == "persona" and entry.get("outcome_category")
    )
    expected = set(config.play.outcome_coverage.expected_categories)
    return {
        "expected_categories": sorted(expected),
        "observed_categories": dict(sorted(categories.items())),
        "missing_categories": sorted(expected - set(categories)),
    }


def _planned_entry(plan: CommandPlan) -> dict[str, Any]:
    return {
        "cell_id": plan.cell.cell_id,
        "run_id": plan.cell.run_id,
        "kind": plan.cell.kind,
        "parameters": dict(plan.cell.parameters),
        "command": list(plan.argv),
        "cwd": str(plan.cwd),
        "report_dir": str(plan.report_dir),
        "cell_manifest": str(plan.manifest_path),
        "status": "planned",
        "attempt": 0,
        "exit_code": None,
        "error": "",
        "started_at": None,
        "finished_at": None,
    }


def _failed_entry(plan: CommandPlan, *, error: str) -> dict[str, Any]:
    return {
        **_planned_entry(plan),
        "status": "failed",
        "error": error,
        "finished_at": _now(),
    }


def _completed_for_plan(
    payload: Mapping[str, Any],
    matrix_plan: MatrixExecutionPlan,
    command_plan: CommandPlan,
    *,
    verify_evidence: bool,
) -> bool:
    identity_matches = (
        payload.get("status") == "completed"
        and payload.get("config_hash") == matrix_plan.config.config_hash
        and payload.get("code_fingerprint") == matrix_plan.code_fingerprint
        and payload.get("matrix_id") == matrix_plan.matrix_id
        and payload.get("cell_id") == command_plan.cell.cell_id
        and payload.get("run_id") == command_plan.cell.run_id
    )
    if not identity_matches or not verify_evidence:
        return identity_matches
    try:
        _cell_evidence(command_plan, matrix_plan.config)
    except (OSError, ValueError, ContractValidationError):
        return False
    return True


def _write_cell_manifest(
    matrix_plan: MatrixExecutionPlan,
    command_plan: CommandPlan,
    entry: Mapping[str, Any],
) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "matrix_id": matrix_plan.matrix_id,
        "config_version": matrix_plan.config.version,
        "config_hash": matrix_plan.config.config_hash,
        "code_fingerprint": matrix_plan.code_fingerprint,
        "config_path": str(matrix_plan.config.source_path),
        **entry,
        "updated_at": _now(),
    }
    _atomic_write_json(command_plan.manifest_path, payload)


def _write_matrix_state(
    plan: MatrixExecutionPlan,
    entries: list[dict[str, Any]],
    *,
    status: str,
    jobs: int,
    dry_run: bool,
    resume: bool,
    started_at: str,
    finished_at: str | None,
    outcome_coverage: dict[str, Any] | None = None,
) -> None:
    summary = _summarize(entries, status=status)
    if outcome_coverage is not None:
        summary["persona_outcome_coverage"] = outcome_coverage
    updated_at = _now()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "config_version": plan.config.version,
        "config_hash": plan.config.config_hash,
        "code_fingerprint": plan.code_fingerprint,
        "config_path": str(plan.config.source_path),
        "status": status,
        "dry_run": dry_run,
        "resume": resume,
        "jobs": jobs,
        "started_at": started_at,
        "finished_at": finished_at,
        "updated_at": updated_at,
        "compare": {
            "output_dir": plan.config.compare.output_dir,
            "include": list(plan.config.compare.include),
        },
        "summary": summary,
        "cells": entries,
    }
    summary_payload = {
        "schema_version": SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "config_version": plan.config.version,
        "config_hash": plan.config.config_hash,
        "code_fingerprint": plan.code_fingerprint,
        "status": status,
        "generated_at": updated_at,
        **summary,
    }
    _atomic_write_json(plan.matrix_dir / MATRIX_MANIFEST_FILE, manifest)
    _atomic_write_json(plan.matrix_dir / MATRIX_SUMMARY_FILE, summary_payload)


def _summarize(entries: list[dict[str, Any]], *, status: str) -> dict[str, Any]:
    counts = Counter(str(entry["status"]) for entry in entries)
    summary: dict[str, Any] = {
        "status": status,
        "total": len(entries),
        **{name: counts[name] for name in CELL_STATUSES},
        "failed_cells": [entry["cell_id"] for entry in entries if entry["status"] == "failed"],
        "by_kind": {},
    }
    for kind in ("simulation", "boundary", "persona"):
        kind_entries = [entry for entry in entries if entry["kind"] == kind]
        kind_counts = Counter(str(entry["status"]) for entry in kind_entries)
        summary["by_kind"][kind] = {
            "total": len(kind_entries),
            **{name: kind_counts[name] for name in CELL_STATUSES},
        }
    return summary


def _result_from_disk(plan: MatrixExecutionPlan) -> MatrixRunResult:
    manifest_path = plan.matrix_dir / MATRIX_MANIFEST_FILE
    summary_path = plan.matrix_dir / MATRIX_SUMMARY_FILE
    manifest = _read_json(manifest_path)
    summary = _read_json(summary_path)
    return MatrixRunResult(
        matrix_id=plan.matrix_id,
        status=str(manifest.get("status", "failed")),
        manifest_path=manifest_path,
        summary_path=summary_path,
        summary=summary,
        cells=tuple(manifest.get("cells", [])),
    )


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MatrixConfigError(f"{path} must be a mapping")
    return value


def _keys(value: Mapping[str, Any], *, path: str, required: set[str]) -> None:
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(str(key) for key in actual - required)
    if missing:
        raise MatrixConfigError(f"{path} is missing required keys: {', '.join(missing)}")
    if unknown:
        raise MatrixConfigError(f"{path} has unknown keys: {', '.join(unknown)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MatrixConfigError(f"{path} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise MatrixConfigError(f"{path} must be a non-empty list")
    items = tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len(items) != len(set(items)):
        raise MatrixConfigError(f"{path} must not contain duplicates")
    return items


def _positive_int(value: Any, path: str) -> int:
    if type(value) is not int or value <= 0:
        raise MatrixConfigError(f"{path} must be a positive integer")
    return value


def _positive_int_list(value: Any, path: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise MatrixConfigError(f"{path} must be a non-empty list")
    items = tuple(_positive_int(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len(items) != len(set(items)):
        raise MatrixConfigError(f"{path} must not contain duplicates")
    return items


def _boolean(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise MatrixConfigError(f"{path} must be a boolean")
    return value


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "matrix"
    return slug[:80].rstrip("-")


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _tail(value: str, limit: int = 4000) -> str:
    return value[-limit:] if len(value) > limit else value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "CELL_MANIFEST_FILE",
    "MATRIX_MANIFEST_FILE",
    "MATRIX_SUMMARY_FILE",
    "BoundaryConfig",
    "CommandPlan",
    "CompareConfig",
    "ExecutionOutcome",
    "MatrixCell",
    "MatrixConfig",
    "MatrixConfigError",
    "MatrixExecutionPlan",
    "MatrixRunResult",
    "OutcomeCoverageConfig",
    "PlayConfig",
    "build_matrix_plan",
    "execute_matrix",
    "expand_matrix_cells",
    "load_matrix_config",
    "run_matrix_file",
    "subprocess_executor",
]
