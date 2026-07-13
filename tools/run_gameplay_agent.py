#!/usr/bin/env python3
"""Orchestration CLI for the gameplay agent pipeline.

Sub-commands:

* ``sim``     — run the headless Monte Carlo via study-in-germany's
  ``RunSimulation.gd`` then aggregate via :mod:`game_analysis_agent.analytics`.
* ``analyze`` — re-aggregate an existing ``raw_runs.jsonl`` and emit the
  analytics CSVs + anomaly detection + value analysis.
* ``probe``   — run ``RunBoundaryProbe.gd`` against the configured
  ``game_project_path`` and emit ``boundary_runs.jsonl``.
* ``interactive-probe`` — capture one canonical interactive snapshot with
  versioned risk guidance, without invoking an LLM.
* ``export``  — run ``ExportEventGraph.gd`` to populate
  ``event_graph.json`` + ``action_catalog.json`` in the game project.
* ``play``    — drive the LLM as a player via :class:`InteractivePlayerAgent`.
* ``qa``      — run all the analysis agents against one report directory.
* ``value``   — run :class:`ValueReviewerAgent` only.
* ``graph``   — run :class:`EventGraphAgent` only.
* ``all``     — ``sim`` + ``analyze`` + ``qa`` in one shot.

Usage:

.. code-block:: bash

   # Run a 100-run baseline, analyse it, and emit every agent report.
   python3 tools/run_gameplay_agent.py all --runs 100 --policy balanced

   # Just play through with the LLM.
   python3 tools/run_gameplay_agent.py play --report-dir reports/play/test
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SRC = ROOT / "src"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(SRC))

from analyze_balance import analyze  # noqa: E402
from compare_matrix import (  # noqa: E402
    MatrixCompareError,
    compare_matrix_runs,
)

from game_analysis_agent.agent_eval import evaluate_and_write  # noqa: E402
from game_analysis_agent.agents import AGENT_NAMES, build_agent, write_agent_result  # noqa: E402
from game_analysis_agent.analytics import load_runs  # noqa: E402
from game_analysis_agent.anomaly_detector import detect_and_write  # noqa: E402
from game_analysis_agent.bug_summarizer import write_bug_summary  # noqa: E402
from game_analysis_agent.contracts import (  # noqa: E402
    ContractKind,
    ContractValidationError,
    validate_contract_file,
    validate_trace_catalog_consistency,
)
from game_analysis_agent.env import load_dotenv  # noqa: E402
from game_analysis_agent.llm_client import LocalLLMClient  # noqa: E402
from game_analysis_agent.quality_gates import evaluate_report_dir, write_gate_report  # noqa: E402
from game_analysis_agent.report_manifest import (  # noqa: E402
    write_report_manifest,
    write_reports_index,
)
from game_analysis_agent.settings import get_settings  # noqa: E402
from game_analysis_agent.test_matrix import (  # noqa: E402
    MatrixConfigError,
    build_matrix_plan,
    execute_matrix,
    load_matrix_config,
)
from game_analysis_agent.value_analyzer import analyze_and_write  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

POLICY_ALIASES = {
    "money": "work",
    "visa": "admin",
    "burnout": "slacker",
}

VALIDATOR_SCRIPTS = {
    "content": ("res://scripts/tools/ValidateContent.gd", "content_validation.json"),
    "json-content": ("res://scripts/tools/ValidateJsonContent.gd", "json_content_validation.json"),
    "economy": ("res://scripts/tools/ValidateEconomyRules.gd", "economy_validation.json"),
    "risk": ("res://scripts/tools/ValidateRiskGuidance.gd", "risk_guidance_validation.json"),
    "route": ("res://scripts/tools/ValidateRouteBoundaries.gd", "route_boundary_validation.json"),
    "demo": ("res://scripts/tools/ValidateDemoGates.gd", "demo_gate_validation.json"),
}
PROCESS_ONLY_VALIDATORS = frozenset({"json-content", "economy"})

_REPORT_OUTPUT_PATTERNS = (
    "raw_runs.jsonl",
    "boundary_runs.jsonl",
    "playthrough.jsonl",
    "playthrough_summary.md",
    "interactive_probe.json",
    "summary.json",
    "*.csv",
    "coverage_report.json",
    "anomalies.jsonl",
    "bugs.jsonl",
    "bugs_summary.md",
    "value_report.json",
    "route_report.json",
    "event_graph.json",
    "action_catalog.json",
    "*_validation.json",
    "validation_summary.json",
    "gate_report.json",
    "report_manifest.json",
    "*_agent_report.json",
    "*_agent_report.md",
    "*_findings.jsonl",
    "agent_eval.json",
)


def _canonical_policy(policy: str) -> str:
    return POLICY_ALIASES.get(policy, policy)


def _resolve_godot(settings) -> str:
    godot_bin = settings.godot_bin
    if shutil.which(godot_bin) is None:
        fallback = "godot" if godot_bin == "godot4" else None
        if fallback and shutil.which(fallback):
            return fallback
    return godot_bin


def _resolve_user_path(game_project: Path) -> Path:
    """Return ``${HOME}/.local/share/godot/app_userdata/<project_name>/``."""
    home = Path.home()
    project_name = game_project.name
    user_root = home / ".local" / "share" / "godot" / "app_userdata"
    names = [project_name]
    configured_name = _read_godot_project_name(game_project)
    if configured_name and configured_name not in names:
        names.append(configured_name)
    for name in names:
        for candidate in (user_root / name, user_root / f"{name}_0"):
            if candidate.exists():
                return candidate
    return user_root / project_name


def _read_godot_project_name(game_project: Path) -> str | None:
    project_file = game_project / "project.godot"
    if not project_file.exists():
        return None
    for line in project_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("config/name="):
            return stripped.split("=", 1)[1].strip().strip('"')
    return None


def _find_godot_output(game_project: Path, file_name: str) -> Path | None:
    user_path = _resolve_user_path(game_project) / file_name
    project_path = game_project / file_name
    candidates = [
        candidate
        for candidate in (user_path, project_path)
        if candidate.exists() and candidate.is_file()
    ]
    # Godot can write either to user:// or res://. Selecting the newest
    # artifact prevents a stale user:// file from shadowing a fresh res:// run.
    return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None


def _copy_godot_output(game_project: Path, file_name: str, target: Path) -> Path | None:
    source = _find_godot_output(game_project, file_name)
    if source is None:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, target)
    if source.parent == game_project:
        source.unlink(missing_ok=True)
    return target


def _reset_known_report_outputs(report_dir: Path) -> None:
    """Remove only pipeline-owned root artifacts before a fresh invocation."""

    if not report_dir.exists():
        return
    for pattern in _REPORT_OUTPUT_PATTERNS:
        for path in report_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def _run_godot(
    settings, *, script: str, extra_args: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    cmd = [
        _resolve_godot(settings),
        "--headless",
        "--path",
        str(settings.game_project_path),
        "-s",
        script,
        *extra_args,
    ]
    try:
        return subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=cwd,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(
            cmd,
            124,
            stdout,
            f"{stderr}\nGodot command timed out after 600 seconds".strip(),
        )


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


def cmd_sim(args: argparse.Namespace) -> int:
    settings = get_settings()
    run_id = args.run_id or f"run-{uuid.uuid4().hex[:6]}"
    policy = args.policy or settings.sim_policy
    policy = _canonical_policy(policy)
    runs = args.runs or settings.sim_runs
    seed = args.seed if args.seed is not None else settings.sim_seed
    weeks = args.weeks or settings.sim_weeks
    difficulty = args.difficulty or settings.sim_difficulty
    scenario = args.scenario or settings.sim_scenario

    requested_report_dir = getattr(args, "report_dir", None)
    out_dir = (
        Path(requested_report_dir)
        if requested_report_dir
        else (ROOT / "reports" / "balance" / run_id)
    )
    _reset_known_report_outputs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_report_manifest(
        out_dir,
        report_type="balance",
        run_id=run_id,
        command="sim",
        parameters={
            "runs": runs,
            "policy": policy,
            "seed": seed,
            "weeks": weeks,
            "difficulty": difficulty,
            "scenario": scenario,
        },
        status="started",
    )
    target_out = out_dir / "raw_runs.jsonl"
    legacy_name = "balance_runs.jsonl"
    previous_legacy_signature = _artifact_signature(
        _find_godot_output(settings.game_project_path, legacy_name)
    )
    extra_args = [
        f"--runs={runs}",
        f"--policy={policy}",
        f"--seed={seed}",
        f"--weeks={weeks}",
        f"--difficulty={difficulty}",
        f"--scenario={scenario}",
        f"--out={target_out}",
    ]
    proc = _run_godot(
        settings,
        script="res://scripts/tools/RunSimulation.gd",
        extra_args=extra_args,
    )
    if proc.returncode != 0:
        print("Godot simulation failed:", proc.stdout, proc.stderr, file=sys.stderr)
        return 3
    direct_output = target_out.exists()
    if direct_output:
        copied = target_out
    else:
        try:
            _require_fresh_output(
                settings,
                legacy_name,
                proc,
                previous_signature=previous_legacy_signature,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 4
        copied = _copy_godot_output(
            settings.game_project_path,
            legacy_name,
            target_out,
        )
    if not copied:
        print(f"Could not find Godot output: {target_out}", file=sys.stderr)
        return 4
    try:
        validate_contract_file(target_out, kind=ContractKind.TRACE)
    except ContractValidationError as exc:
        print(f"Godot trace contract failed: {exc}", file=sys.stderr)
        return 7
    catalog_dir = getattr(args, "catalog_dir", None)
    if catalog_dir is not None:
        catalog_root = Path(catalog_dir)
        graph_source = catalog_root / "event_graph.json"
        action_source = catalog_root / "action_catalog.json"
        try:
            validate_contract_file(graph_source, kind=ContractKind.EVENT_GRAPH)
            validate_contract_file(action_source, kind=ContractKind.ACTION_CATALOG)
        except (ContractValidationError, OSError) as exc:
            print(f"Matrix catalog contract failed: {exc}", file=sys.stderr)
            return 7
        shutil.copy(graph_source, out_dir / "event_graph.json")
        shutil.copy(action_source, out_dir / "action_catalog.json")
        try:
            validate_trace_catalog_consistency(
                target_out,
                out_dir / "event_graph.json",
                out_dir / "action_catalog.json",
            )
        except ContractValidationError as exc:
            print(f"Trace/catalog consistency failed: {exc}", file=sys.stderr)
            return 7
    write_report_manifest(
        out_dir,
        report_type="balance",
        run_id=run_id,
        command="sim",
        parameters={
            "runs": runs,
            "policy": policy,
            "seed": seed,
            "weeks": weeks,
            "difficulty": difficulty,
            "scenario": scenario,
        },
        source_files=[target_out],
        generated_files=[target_out],
        status="simulated",
    )
    print(f"Copied raw runs to {target_out}")
    args._report_dir = out_dir
    return cmd_analyze(
        argparse.Namespace(
            report_dir=out_dir,
            raw_runs=target_out,
            run_anomalies=True,
            run_value=True,
        )
    )


def cmd_analyze(args: argparse.Namespace) -> int:
    raw_path = args.raw_runs or (args.report_dir / "raw_runs.jsonl")
    if not raw_path.exists():
        print(f"Missing raw runs: {raw_path}", file=sys.stderr)
        return 1
    runs = load_runs(raw_path)
    out_dir = args.report_dir
    analyze(runs, out_dir, raw_runs_path=raw_path)
    if args.run_anomalies:
        from game_analysis_agent.anomaly_detector import detect_and_write

        anomalies = detect_and_write(runs, out_dir)
        write_bug_summary(anomalies, out_dir)
    if args.run_value:
        analyze_and_write(out_dir)
    write_report_manifest(
        out_dir,
        report_type="balance",
        run_id=out_dir.name,
        command="analyze",
        parameters={
            "run_anomalies": bool(args.run_anomalies),
            "run_value": bool(args.run_value),
        },
        source_files=[raw_path],
        generated_files=[
            "summary.json",
            "ending_distribution.csv",
            "weekly_stats.csv",
            "action_pick_rates.csv",
            "event_trigger_rates.csv",
            "choice_pick_rates.csv",
            "coverage_report.json",
            "anomalies.jsonl",
            "bugs.jsonl",
            "bugs_summary.md",
            "value_report.json",
            "route_report.json",
        ],
        summary={"total_runs": len(runs)},
    )
    print(f"Analysis written to {out_dir}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    settings = get_settings()
    run_id = args.run_id or f"boundary-{uuid.uuid4().hex[:6]}"
    requested_report_dir = getattr(args, "report_dir", None)
    out_dir = (
        Path(requested_report_dir)
        if requested_report_dir
        else (ROOT / "reports" / "boundary" / run_id)
    )
    _reset_known_report_outputs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_report_manifest(
        out_dir,
        report_type="boundary",
        run_id=run_id,
        command="probe",
        parameters={
            "runs": args.runs,
            "policy": _canonical_policy(args.policy),
            "seed": args.seed,
            "weeks": args.weeks,
            "extreme": args.extreme,
        },
        status="started",
    )
    target_out = out_dir / "boundary_runs.jsonl"
    legacy_name = "boundary_runs.jsonl"
    previous_legacy_signature = _artifact_signature(
        _find_godot_output(settings.game_project_path, legacy_name)
    )
    extra_args = [
        f"--runs={args.runs}",
        f"--policy={_canonical_policy(args.policy)}",
        f"--seed={args.seed}",
        f"--weeks={args.weeks}",
        f"--extreme={args.extreme}",
        f"--out={target_out}",
    ]
    proc = _run_godot(
        settings,
        script="res://scripts/tools/RunBoundaryProbe.gd",
        extra_args=extra_args,
    )
    if proc.returncode != 0:
        print("Godot boundary probe failed:", proc.stdout, proc.stderr, file=sys.stderr)
        return 3
    if target_out.exists():
        copied = target_out
    else:
        try:
            _require_fresh_output(
                settings,
                legacy_name,
                proc,
                previous_signature=previous_legacy_signature,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 4
        copied = _copy_godot_output(
            settings.game_project_path,
            legacy_name,
            target_out,
        )
    if not copied:
        print(f"Could not find boundary output: {target_out}", file=sys.stderr)
        return 4
    try:
        validate_contract_file(target_out, kind=ContractKind.BOUNDARY_TRACE)
    except ContractValidationError as exc:
        print(f"Godot boundary trace contract failed: {exc}", file=sys.stderr)
        return 7
    analyze_and_write(out_dir)
    # also feed the aggregate through the bug detector so the agent has
    # immediate numeric context.
    runs = load_runs(target_out)

    anomalies = detect_and_write(runs, out_dir)
    write_bug_summary(anomalies, out_dir)
    write_report_manifest(
        out_dir,
        report_type="boundary",
        run_id=run_id,
        command="probe",
        source_files=[target_out],
        generated_files=[
            target_out,
            "anomalies.jsonl",
            "bugs.jsonl",
            "bugs_summary.md",
            "value_report.json",
            "route_report.json",
        ],
        summary={"total_runs": len(runs), "anomalies": len(anomalies)},
    )
    print(f"Boundary probe complete; {len(runs)} runs -> {target_out}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    settings = get_settings()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    selected = args.checks or list(VALIDATOR_SCRIPTS)
    reuse_inputs = bool(getattr(args, "reuse_inputs", False))
    results: list[dict[str, object]] = []
    prerequisites: list[dict[str, object]] = []
    failed = False
    route_inputs_ready = False

    for check in selected:
        try:
            if check == "route":
                generated = _ensure_route_validation_inputs(
                    settings,
                    reuse_existing=reuse_inputs,
                )
                prerequisites.extend(generated)
                route_inputs_ready = True
            if check == "demo":
                prerequisites.extend(
                    _ensure_demo_validation_inputs(
                        settings,
                        reuse_existing=reuse_inputs,
                        route_inputs_ready=route_inputs_ready,
                    )
                )
            script, file_name = VALIDATOR_SCRIPTS[check]
            target = args.report_dir / file_name
            target.unlink(missing_ok=True)
            previous_signature = _artifact_signature(
                _find_godot_output(settings.game_project_path, file_name)
            )
            out_arg = f"--out={target.resolve()}"
            proc = _run_godot(settings, script=script, extra_args=[out_arg])
            if target.exists():
                copied = target
            elif check in PROCESS_ONLY_VALIDATORS:
                _write_process_validator_report(
                    target,
                    check=check,
                    script=script,
                    proc=proc,
                )
                copied = target
            else:
                _require_fresh_output(
                    settings,
                    file_name,
                    proc,
                    previous_signature=previous_signature,
                )
                copied = _copy_user_file(
                    settings.game_project_path,
                    file_name,
                    target,
                )
            output_error = _validator_output_error(copied)
            check_failed = proc.returncode != 0 or copied is None or bool(output_error)
            result = {
                "check": check,
                "script": script,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
                "output_file": str(copied) if copied else "",
                "output_error": output_error,
            }
        except RuntimeError as exc:
            check_failed = True
            result = {
                "check": check,
                "script": VALIDATOR_SCRIPTS[check][0],
                "returncode": 1,
                "stdout": "",
                "stderr": str(exc),
                "output_file": "",
                "output_error": str(exc),
            }

        results.append(result)
        failed = failed or check_failed
        stream = sys.stderr if check_failed else sys.stdout
        print(f"[validate:{check}] {'failed' if check_failed else 'ok'}", file=stream)

    summary = {
        "schema_version": "validation-summary-v2",
        "passed": not failed,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "reuse_inputs": reuse_inputs,
        "checks": results,
        "prerequisites": prerequisites,
    }
    summary_path = args.report_dir / "validation_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report_manifest(
        args.report_dir,
        report_type="validation",
        run_id=args.report_dir.name,
        command="validate",
        parameters={"checks": selected, "reuse_inputs": reuse_inputs},
        generated_files=["validation_summary.json"]
        + [result["output_file"] for result in results if result.get("output_file")],
        status="failed" if failed else "completed",
        summary={"passed": not failed, "check_count": len(results)},
    )
    return 1 if failed else 0


def _ensure_route_validation_inputs(
    settings,
    *,
    reuse_existing: bool,
) -> list[dict[str, object]]:
    route_specs = [
        ("study", "reports/route_audit_study.jsonl"),
        ("work", "reports/route_audit_work.jsonl"),
        ("admin", "reports/route_audit_admin_after_fix.jsonl"),
        ("social", "reports/route_audit_social.jsonl"),
        ("slacker", "reports/route_audit_slacker.jsonl"),
    ]
    generated: list[dict[str, object]] = []
    for policy, out_path in route_specs:
        generated.append(
            _ensure_simulation_input(
                settings,
                out_path=out_path,
                reuse_existing=reuse_existing,
                runs=6,
                policy=policy,
                difficulty="normal",
                scenario="default_first_semester",
                weeks=20,
                seed=42,
            )
        )
    return generated


def _ensure_demo_validation_inputs(
    settings,
    *,
    reuse_existing: bool,
    route_inputs_ready: bool,
) -> list[dict[str, object]]:
    generated: list[dict[str, object]] = []
    demo_specs = [
        (
            "reports/gates_balanced_normal.jsonl",
            "balanced",
            "normal",
            "default_first_semester",
        ),
        (
            "reports/gates_balanced_realistic.jsonl",
            "balanced",
            "realistic",
            "default_first_semester",
        ),
        (
            "reports/gates_balanced_low_money.jsonl",
            "balanced",
            "normal",
            "low_money_start",
        ),
    ]
    for out_path, policy, difficulty, scenario in demo_specs:
        generated.append(
            _ensure_simulation_input(
                settings,
                out_path=out_path,
                reuse_existing=reuse_existing,
                runs=12,
                policy=policy,
                difficulty=difficulty,
                scenario=scenario,
                weeks=20,
                seed=42,
            )
        )

    for script, out_path in (
        ("res://scripts/tools/ValidateContent.gd", "reports/content_validation.json"),
        (
            "res://scripts/tools/ValidateRiskGuidance.gd",
            "reports/risk_guidance_validation.json",
        ),
    ):
        generated.append(
            _ensure_validator_input(
                settings,
                script=script,
                out_path=out_path,
                reuse_existing=reuse_existing,
            )
        )

    if not route_inputs_ready:
        generated.extend(
            _ensure_route_validation_inputs(
                settings,
                reuse_existing=reuse_existing,
            )
        )
    generated.append(
        _ensure_validator_input(
            settings,
            script="res://scripts/tools/ValidateRouteBoundaries.gd",
            out_path="reports/route_boundary_validation.json",
            reuse_existing=reuse_existing and not route_inputs_ready,
        )
    )
    return generated


def _ensure_simulation_input(
    settings,
    *,
    out_path: str,
    reuse_existing: bool,
    runs: int,
    policy: str,
    difficulty: str,
    scenario: str,
    weeks: int,
    seed: int,
) -> dict[str, object]:
    existing = _find_godot_output(settings.game_project_path, out_path)
    if reuse_existing and existing is not None:
        return _prerequisite_record(out_path, existing, reused=True)
    previous_signature = _artifact_signature(existing)
    proc = _run_godot(
        settings,
        script="res://scripts/tools/RunSimulation.gd",
        extra_args=[
            f"--runs={runs}",
            f"--policy={policy}",
            f"--difficulty={difficulty}",
            f"--scenario={scenario}",
            f"--weeks={weeks}",
            f"--seed={seed}",
            f"--out=res://{out_path}",
        ],
    )
    return _require_fresh_output(
        settings,
        out_path,
        proc,
        previous_signature=previous_signature,
    )


def _ensure_validator_input(
    settings,
    *,
    script: str,
    out_path: str,
    reuse_existing: bool,
) -> dict[str, object]:
    existing = _find_godot_output(settings.game_project_path, out_path)
    if reuse_existing and existing is not None and not _validator_output_error(existing):
        return _prerequisite_record(out_path, existing, reused=True)
    previous_signature = _artifact_signature(existing)
    proc = _run_godot(
        settings,
        script=script,
        extra_args=[f"--out=res://{out_path}"],
    )
    record = _require_fresh_output(
        settings,
        out_path,
        proc,
        previous_signature=previous_signature,
    )
    output = Path(str(record["path"]))
    output_error = _validator_output_error(output)
    if output_error:
        raise RuntimeError(f"{script} produced invalid output: {output_error}")
    return record


def _require_fresh_output(
    settings,
    out_path: str,
    proc: subprocess.CompletedProcess[str],
    *,
    previous_signature: tuple[int, int] | None,
) -> dict[str, object]:
    if proc.returncode != 0:
        raise RuntimeError(
            f"prerequisite generation failed for {out_path}: "
            f"{proc.stderr[-2000:] or proc.stdout[-2000:]}"
        )
    output = _find_godot_output(settings.game_project_path, out_path)
    if output is None:
        raise RuntimeError(f"prerequisite did not produce {out_path}")
    current_signature = _artifact_signature(output)
    if previous_signature is not None and current_signature == previous_signature:
        raise RuntimeError(
            f"prerequisite left stale artifact unchanged: {out_path}; "
            "use --reuse-inputs only when stale reuse is intentional"
        )
    return _prerequisite_record(out_path, output, reused=False)


def _artifact_signature(path: Path | None) -> tuple[int, int] | None:
    if path is None or not path.exists():
        return None
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _prerequisite_record(
    logical_path: str,
    path: Path,
    *,
    reused: bool,
) -> dict[str, object]:
    return {
        "logical_path": logical_path,
        "path": str(path),
        "reused": reused,
        "bytes": path.stat().st_size,
        "modified_at": datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=UTC,
        ).isoformat(),
    }


def _validator_output_error(path: Path | None) -> str:
    if path is None or not path.exists():
        return "validator output is missing"
    try:
        validate_contract_file(
            path,
            kind=ContractKind.VALIDATOR_REPORT,
            require_clean=True,
        )
    except (ContractValidationError, OSError) as exc:
        return str(exc)
    return ""


def _write_process_validator_report(
    path: Path,
    *,
    check: str,
    script: str,
    proc: subprocess.CompletedProcess[str],
) -> None:
    """Wrap legacy stdout-only validators in the common JSON contract."""

    message = (proc.stderr or proc.stdout).strip()
    errors = [] if proc.returncode == 0 else [message or f"validator exited {proc.returncode}"]
    payload = {
        "contract_version": "1.0",
        "errors": errors,
        "warnings": [],
        "summary": {
            "check": check,
            "script": script,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "source": "process_exit_envelope",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_user_file(game_project: Path, file_name: str, target: Path) -> Path | None:
    return _copy_godot_output(game_project, file_name, target)


def cmd_gates(args: argparse.Namespace) -> int:
    gates_path = args.gates or (ROOT / "config" / "gates.yaml")
    report = evaluate_report_dir(args.report_dir, gates_path)
    out = args.out or (args.report_dir / "gate_report.json")
    write_gate_report(report, out)
    write_report_manifest(
        args.report_dir,
        report_type="gate",
        run_id=args.report_dir.name,
        command="gates",
        source_files=[args.gates or (ROOT / "config" / "gates.yaml")],
        generated_files=[out],
        status="completed" if report["passed"] else "failed",
        summary={
            "passed": report["passed"],
            "failure_count": report.get("failure_count", 0),
            "warning_count": report.get("warning_count", 0),
        },
    )
    print(f"Gate report written to {out}")
    if not report["passed"]:
        for failure in report["failures"]:
            print(f"[gate failed] {failure['gate']}: {failure['message']}", file=sys.stderr)
        return 1
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    settings = get_settings()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    graph_target = args.report_dir / "event_graph.json"
    action_target = args.report_dir / "action_catalog.json"
    graph_previous = _artifact_signature(
        _find_godot_output(settings.game_project_path, "event_graph.json")
    )
    action_previous = _artifact_signature(
        _find_godot_output(settings.game_project_path, "action_catalog.json")
    )
    graph_target.unlink(missing_ok=True)
    action_target.unlink(missing_ok=True)
    extra_args = [f"--out={graph_target.resolve()}"]
    proc = _run_godot(
        settings,
        script="res://scripts/tools/ExportEventGraph.gd",
        extra_args=extra_args,
    )
    if proc.returncode != 0:
        print("ExportEventGraph failed:", proc.stdout, proc.stderr, file=sys.stderr)
        return 3
    if graph_target.exists():
        graph_copied = graph_target
    else:
        try:
            _require_fresh_output(
                settings,
                "event_graph.json",
                proc,
                previous_signature=graph_previous,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 4
        graph_copied = _copy_godot_output(
            settings.game_project_path,
            "event_graph.json",
            graph_target,
        )
    if action_target.exists():
        action_copied = action_target
    else:
        try:
            _require_fresh_output(
                settings,
                "action_catalog.json",
                proc,
                previous_signature=action_previous,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 4
        action_copied = _copy_godot_output(
            settings.game_project_path,
            "action_catalog.json",
            action_target,
        )
    if graph_copied is None or action_copied is None:
        print("ExportEventGraph did not produce both catalog artifacts", file=sys.stderr)
        return 4
    try:
        validate_contract_file(graph_target, kind=ContractKind.EVENT_GRAPH)
        validate_contract_file(action_target, kind=ContractKind.ACTION_CATALOG)
    except ContractValidationError as exc:
        print(f"Godot catalog contract failed: {exc}", file=sys.stderr)
        return 7
    write_report_manifest(
        args.report_dir,
        report_type="catalog",
        run_id=args.report_dir.name,
        command="export",
        generated_files=[graph_target, action_target],
    )
    print(f"Event graph copied to {graph_target}")
    return 0


def cmd_qa(args: argparse.Namespace) -> int:
    settings = get_settings()
    llm = LocalLLMClient.from_settings(settings)
    prompts_root = ROOT / "prompts"
    for agent_name in args.agents:
        if agent_name == "interactive_player":
            print("Skipping interactive_player in `qa`; use the `play` subcommand.")
            continue
        agent = build_agent(
            agent_name,
            llm=llm,
            prompts_root=prompts_root,
            settings=settings,
        )
        result = agent.run(args.report_dir)
        written = write_agent_result(args.report_dir, result)
        write_report_manifest(
            args.report_dir,
            report_type="agent_qa",
            run_id=args.report_dir.name,
            command="qa",
            parameters={"agent": agent_name},
            generated_files=written,
            summary={"agent": agent_name, "output_count": len(written)},
        )
        for path in written:
            print(f"[{agent_name}] {path}")
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    settings = get_settings()
    _reset_known_report_outputs(args.report_dir)
    llm = LocalLLMClient.from_settings(settings)
    if not llm.settings.deepseek_configured() and llm.provider == "deepseek":
        print(
            "DeepSeek key not configured; set DEEPSEEK_API_KEY before using `play`.",
            file=sys.stderr,
        )
        return 5
    from game_analysis_agent.agents.interactive_player import (  # noqa: I001
        PERSONAS,
        InteractivePlayerAgent,
    )
    from game_analysis_agent.game_tools import (  # noqa: I001
        TOOL_DEFINITIONS,
        build_probe,
        build_tool_map,
    )

    probe = build_probe(settings)
    tool_map = build_tool_map(probe)
    persona = getattr(args, "persona", None) or "newbie"
    if persona not in PERSONAS:
        print(
            f"Unknown persona {persona!r}; valid: {sorted(PERSONAS)}",
            file=sys.stderr,
        )
        return 6

    agent = InteractivePlayerAgent(
        llm=llm,
        prompts_root=ROOT / "prompts",
        settings=settings,
        tool_definitions=TOOL_DEFINITIONS,
        tool_map=tool_map,
        max_weeks=args.weeks,
        persona=persona,
        difficulty=getattr(args, "difficulty", None) or "normal",
        scenario=getattr(args, "scenario", None) or "default_first_semester",
        seed=int(getattr(args, "seed", 42) or 42),
    )
    result, written = agent.play_through(args.report_dir)
    evaluate_and_write(args.report_dir)
    written = [*written, args.report_dir / "agent_eval.json"]
    write_report_manifest(
        args.report_dir,
        report_type="play",
        run_id=args.report_dir.name,
        command="play",
        parameters={
            "persona": persona,
            "weeks": args.weeks,
            "difficulty": getattr(args, "difficulty", None) or "normal",
            "scenario": getattr(args, "scenario", None) or "default_first_semester",
            "seed": int(getattr(args, "seed", 42) or 42),
            "provider": llm.provider,
            "model": llm.model,
        },
        generated_files=written,
        summary={
            "final_ending": result.final_ending,
            "steps": len(result.steps),
            "llm_calls": len(result.report.llm_calls),
        },
    )
    for path in written:
        print(f"[interactive_player] {path}")
    print(f"[interactive_player] ending={result.final_ending} steps={len(result.steps)}")
    return 0


def cmd_interactive_probe(args: argparse.Namespace) -> int:
    """Capture and persist one real interactive-probe contract snapshot."""

    from game_analysis_agent.game_tools import _run_one_step

    settings = get_settings()
    report_dir = args.report_dir.resolve()
    _reset_known_report_outputs(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    try:
        payload = _run_one_step(
            settings,
            [],
            seed=args.seed,
            difficulty=args.difficulty,
            scenario=args.scenario,
        )
    except (OSError, RuntimeError) as exc:
        print(f"Interactive probe failed: {exc}", file=sys.stderr)
        return 7
    guidance = payload.get("risk_guidance")
    if not isinstance(guidance, dict):
        print(
            "Interactive probe omitted canonical risk_guidance from RiskEvaluator.",
            file=sys.stderr,
        )
        return 8

    output = report_dir / "interactive_probe.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        validate_contract_file(output, kind=ContractKind.INTERACTIVE_PROBE)
    except ContractValidationError as exc:
        print(f"Interactive probe contract failed: {exc}", file=sys.stderr)
        return 8
    write_report_manifest(
        report_dir,
        report_type="interactive_probe",
        run_id=args.run_id or report_dir.name,
        command="interactive-probe",
        parameters={
            "seed": args.seed,
            "difficulty": args.difficulty,
            "scenario": args.scenario,
        },
        generated_files=[output],
        summary={
            "risk_count": len(guidance.get("top_risks") or []),
            "risk_source": guidance.get("source", ""),
        },
    )
    print(f"Interactive probe written to {output}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    report = evaluate_and_write(args.report_dir, output=args.out)
    target = args.out or args.report_dir / "agent_eval.json"
    print(f"Agent eval written to {target}")
    if not report["valid"]:
        for error in report["errors"]:
            print(f"[eval failed] {error}", file=sys.stderr)
        return 1
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    rc = cmd_sim(args)
    if rc != 0:
        return rc
    report_dir = args._report_dir

    rc = cmd_export(argparse.Namespace(report_dir=report_dir))
    if rc != 0:
        return rc

    try:
        validate_trace_catalog_consistency(
            report_dir / "raw_runs.jsonl",
            report_dir / "event_graph.json",
            report_dir / "action_catalog.json",
        )
    except (ContractValidationError, OSError) as exc:
        print(f"Trace/catalog consistency failed: {exc}", file=sys.stderr)
        return 7

    # The initial analysis runs before catalogs exist. Recompute it so event,
    # choice, and action coverage use the fresh exported denominators.
    rc = cmd_analyze(
        argparse.Namespace(
            report_dir=report_dir,
            raw_runs=report_dir / "raw_runs.jsonl",
            run_anomalies=True,
            run_value=True,
        )
    )
    if rc != 0:
        return rc

    rc = cmd_validate(
        argparse.Namespace(
            report_dir=report_dir,
            checks=list(VALIDATOR_SCRIPTS),
            reuse_inputs=bool(getattr(args, "reuse_validation_inputs", False)),
        )
    )
    if rc != 0:
        return rc

    if not bool(getattr(args, "skip_qa", False)):
        rc = cmd_qa(
            argparse.Namespace(
                agent=AGENT_NAMES,
                report_dir=report_dir,
                agents=[name for name in AGENT_NAMES if name != "interactive_player"],
            )
        )
        if rc != 0:
            return rc

    return cmd_gates(
        argparse.Namespace(
            report_dir=report_dir,
            gates=getattr(args, "gates", None),
            out=None,
        )
    )


def cmd_matrix(args: argparse.Namespace) -> int:
    try:
        config = load_matrix_config(args.config)
        initial_plan = build_matrix_plan(
            config,
            project_root=ROOT,
            matrix_dir=args.out,
            simulation_command=args.simulation_command,
        )
        catalog_dir = initial_plan.matrix_dir / "catalog"
        plan = build_matrix_plan(
            config,
            project_root=ROOT,
            matrix_dir=initial_plan.matrix_dir,
            simulation_command=args.simulation_command,
            catalog_dir=catalog_dir if args.simulation_command == "sim" else None,
        )
        if not args.dry_run and args.simulation_command == "sim":
            rc = cmd_export(argparse.Namespace(report_dir=catalog_dir))
            if rc != 0:
                return rc
        result = execute_matrix(
            plan,
            jobs=args.jobs,
            dry_run=args.dry_run,
            resume=args.resume,
        )
    except MatrixConfigError as exc:
        print(f"Invalid matrix config: {exc}", file=sys.stderr)
        return 2
    print(f"Matrix manifest written to {result.manifest_path}")
    print(
        f"matrix={result.matrix_id} status={result.status} "
        f"total={result.summary.get('total', 0)} "
        f"failed={result.summary.get('failed', 0)}"
    )
    return result.exit_code


def cmd_compare_matrix(args: argparse.Namespace) -> int:
    try:
        result = compare_matrix_runs(
            args.before,
            args.after,
            output_dir=args.out,
        )
    except MatrixCompareError as exc:
        print(f"Matrix comparison failed: {exc}", file=sys.stderr)
        return 2
    print(f"Matrix comparison written to {result.summary_path}")
    print(
        f"cells={result.summary['total_cells']} "
        f"comparable={result.summary['comparable_cells']} "
        f"changed_artifacts={result.summary['changed_artifacts']}"
    )
    return result.exit_code


def cmd_index(args: argparse.Namespace) -> int:
    index = write_reports_index(args.reports)
    print(f"Report index written to {args.reports / 'report_index.json'}")
    print(f"Indexed {index['report_count']} reports")
    return 0


# ---------------------------------------------------------------------------
# Argparse plumbing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_gameplay_agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sim_p = sub.add_parser("sim", help="Run Monte Carlo via the Godot runner.")
    sim_p.add_argument("--run-id", default=None)
    sim_p.add_argument("--runs", type=int, default=None)
    sim_p.add_argument("--policy", default=None)
    sim_p.add_argument("--seed", type=int, default=None)
    sim_p.add_argument("--weeks", type=int, default=None)
    sim_p.add_argument("--difficulty", default=None)
    sim_p.add_argument("--scenario", default=None)
    sim_p.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Override the report directory (used by isolated matrix runs).",
    )
    sim_p.add_argument(
        "--catalog-dir",
        type=Path,
        default=None,
        help="Pre-exported event/action catalogs to copy before analysis.",
    )
    sim_p.add_argument("--no-anomalies", dest="run_anomalies", action="store_false")
    sim_p.add_argument("--no-value", dest="run_value", action="store_false")
    sim_p.set_defaults(func=cmd_sim)

    analyze_p = sub.add_parser("analyze", help="Re-analyze an existing raw_runs.jsonl.")
    analyze_p.add_argument(
        "--report-dir", type=Path, required=True, help="Output dir for analytics CSVs."
    )
    analyze_p.add_argument("--raw-runs", type=Path, default=None)
    analyze_p.add_argument("--no-anomalies", dest="run_anomalies", action="store_false")
    analyze_p.add_argument("--no-value", dest="run_value", action="store_false")
    analyze_p.set_defaults(func=cmd_analyze)

    probe_p = sub.add_parser("probe", help="Run extreme-scenario boundary probes via Godot.")
    probe_p.add_argument("--run-id", default=None)
    probe_p.add_argument("--runs", type=int, default=3)
    probe_p.add_argument("--policy", default="balanced")
    probe_p.add_argument("--seed", type=int, default=42)
    probe_p.add_argument("--weeks", type=int, default=12)
    probe_p.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Override the report directory (used by isolated matrix runs).",
    )
    probe_p.add_argument(
        "--extreme",
        default="zero_money,deep_debt,no_energy,all_negative,no_language,flag_chaos,week_zero,already_registered",
    )
    probe_p.set_defaults(func=cmd_probe)

    interactive_probe_p = sub.add_parser(
        "interactive-probe",
        help="Capture a real interactive snapshot and canonical RiskEvaluator guidance.",
    )
    interactive_probe_p.add_argument("--run-id", default=None)
    interactive_probe_p.add_argument("--seed", type=int, default=42)
    interactive_probe_p.add_argument("--difficulty", default="normal")
    interactive_probe_p.add_argument("--scenario", default="default_first_semester")
    interactive_probe_p.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        help="Directory for interactive_probe.json and its trace manifest.",
    )
    interactive_probe_p.set_defaults(func=cmd_interactive_probe)

    export_p = sub.add_parser("export", help="Export the event/action catalog from Godot.")
    export_p.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT / "reports" / "catalog",
        help="Where to put event_graph.json + action_catalog.json.",
    )
    export_p.set_defaults(func=cmd_export)

    validate_p = sub.add_parser(
        "validate", help="Run Godot-side validators and collect their JSON reports."
    )
    validate_p.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT / "reports" / "validation",
        help="Where validator JSON reports should be copied.",
    )
    validate_p.add_argument(
        "--check",
        dest="checks",
        action="append",
        choices=tuple(VALIDATOR_SCRIPTS),
        default=None,
        help="Validator to run. Repeatable. Default: all validators.",
    )
    validate_p.add_argument(
        "--reuse-inputs",
        action="store_true",
        help="Opt in to existing route/demo prerequisite artifacts instead of regenerating them.",
    )
    validate_p.set_defaults(func=cmd_validate)

    matrix_p = sub.add_parser(
        "matrix",
        help="Execute the strict, resumable simulation/boundary/persona matrix.",
    )
    matrix_p.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "matrix.yaml",
    )
    matrix_p.add_argument("--out", type=Path, default=None)
    matrix_p.add_argument("--jobs", type=int, default=1)
    matrix_p.add_argument("--dry-run", action="store_true")
    matrix_p.add_argument("--resume", action="store_true")
    matrix_p.add_argument(
        "--simulation-command",
        choices=("sim", "all"),
        default="sim",
        help=(
            "Use 'sim' for parallel deterministic matrix data; use 'all' "
            "to run validators, model QA, and gates per simulation cell."
        ),
    )
    matrix_p.set_defaults(func=cmd_matrix)

    compare_matrix_p = sub.add_parser(
        "compare-matrix",
        help="Strictly compare fixed-seed outputs from two completed matrices.",
    )
    compare_matrix_p.add_argument(
        "--before",
        type=Path,
        required=True,
        help="Before matrix directory or matrix_manifest.json.",
    )
    compare_matrix_p.add_argument(
        "--after",
        type=Path,
        required=True,
        help="After matrix directory or matrix_manifest.json.",
    )
    compare_matrix_p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "compare" / "matrix",
        help="Directory for matrix_compare_summary.json and per-cell diffs.",
    )
    compare_matrix_p.set_defaults(func=cmd_compare_matrix)

    index_p = sub.add_parser("index", help="Build reports/report_index.json from report manifests.")
    index_p.add_argument(
        "--reports",
        type=Path,
        default=ROOT / "reports",
        help="Reports root to scan.",
    )
    index_p.set_defaults(func=cmd_index)

    gates_p = sub.add_parser("gates", help="Evaluate config/gates.yaml against a report dir.")
    gates_p.add_argument("--report-dir", type=Path, required=True)
    gates_p.add_argument("--gates", type=Path, default=None)
    gates_p.add_argument("--out", type=Path, default=None)
    gates_p.set_defaults(func=cmd_gates)

    eval_p = sub.add_parser(
        "eval",
        help="Evaluate a recorded interactive playthrough without calling an LLM.",
    )
    eval_p.add_argument("--report-dir", type=Path, required=True)
    eval_p.add_argument("--out", type=Path, default=None)
    eval_p.set_defaults(func=cmd_eval)

    qa_p = sub.add_parser("qa", help="Run all (or selected) LLM agents against a report dir.")
    qa_p.add_argument("--report-dir", type=Path, required=True)
    qa_p.add_argument(
        "--agent",
        action="append",
        choices=AGENT_NAMES,
        default=None,
        help=(
            "Run a single agent. Repeatable. Default: balance + content_qa + "
            "event_graph + bug_hunter + boundary_prober + value_reviewer."
        ),
    )
    qa_p.set_defaults(func=cmd_qa)

    play_p = sub.add_parser("play", help="Drive the LLM as a player with the tool loop.")
    play_p.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        help="Where to write playthrough.jsonl + playthrough_summary.md.",
    )
    play_p.add_argument("--weeks", type=int, default=20)
    play_p.add_argument(
        "--persona",
        default="newbie",
        choices=("newbie", "study", "money", "social", "visa", "slacker"),
        help="LLM player persona to drive the playthrough.",
    )
    play_p.add_argument(
        "--difficulty", default="normal", help="Godot difficulty to inject into the probe."
    )
    play_p.add_argument(
        "--scenario",
        default="default_first_semester",
        help="Godot scenario id to inject into the interactive probe.",
    )
    play_p.add_argument("--seed", type=int, default=42, help="Seed passed to the persona block.")
    play_p.set_defaults(func=cmd_play)

    all_p = sub.add_parser(
        "all",
        help="sim -> analyze -> export -> validate -> qa -> gates.",
    )
    all_p.add_argument("--run-id", default=None)
    all_p.add_argument("--runs", type=int, default=None)
    all_p.add_argument("--policy", default=None)
    all_p.add_argument("--seed", type=int, default=None)
    all_p.add_argument("--weeks", type=int, default=None)
    all_p.add_argument("--difficulty", default=None)
    all_p.add_argument("--scenario", default=None)
    all_p.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Override the report directory (used by isolated matrix runs).",
    )
    all_p.add_argument(
        "--catalog-dir",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    all_p.add_argument("--gates", type=Path, default=None)
    all_p.add_argument(
        "--skip-qa",
        action="store_true",
        help="Skip model-backed QA while retaining deterministic validation and gates.",
    )
    all_p.add_argument(
        "--reuse-validation-inputs",
        action="store_true",
        help="Opt in to existing route/demo prerequisites; fresh inputs are the default.",
    )
    all_p.set_defaults(func=cmd_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_dotenv(ROOT / ".env")
    if getattr(args, "agent", None) is None and hasattr(args, "agents") is False:
        if hasattr(args, "agent"):
            args.agents = args.agent
    elif hasattr(args, "agent"):
        # Dual-mode agents list
        args.agents = args.agent or [
            "balance",
            "content_qa",
            "event_graph",
            "bug_hunter",
            "boundary_prober",
            "value_reviewer",
        ]
    if hasattr(args, "agents") and args.agents is None:
        args.agents = [
            "balance",
            "content_qa",
            "event_graph",
            "bug_hunter",
            "boundary_prober",
            "value_reviewer",
        ]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
