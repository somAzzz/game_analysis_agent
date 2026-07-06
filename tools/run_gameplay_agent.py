#!/usr/bin/env python3
"""Orchestration CLI for the gameplay agent pipeline.

Sub-commands:

* ``sim``     — run the headless Monte Carlo via study-in-germany's
  ``RunSimulation.gd`` then aggregate via :mod:`game_analysis_agent.analytics`.
* ``analyze`` — re-aggregate an existing ``raw_runs.jsonl`` and emit the
  analytics CSVs + anomaly detection + value analysis.
* ``probe``   — run ``RunBoundaryProbe.gd`` against the configured
  ``game_project_path`` and emit ``boundary_runs.jsonl``.
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
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SRC = ROOT / "src"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(SRC))

from analyze_balance import analyze  # noqa: E402

from game_analysis_agent.agents import AGENT_NAMES, build_agent, write_agent_result  # noqa: E402
from game_analysis_agent.analytics import load_runs  # noqa: E402
from game_analysis_agent.anomaly_detector import detect_and_write  # noqa: E402
from game_analysis_agent.bug_summarizer import write_bug_summary  # noqa: E402
from game_analysis_agent.env import load_dotenv  # noqa: E402
from game_analysis_agent.llm_client import LocalLLMClient  # noqa: E402
from game_analysis_agent.quality_gates import evaluate_report_dir, write_gate_report  # noqa: E402
from game_analysis_agent.settings import get_settings  # noqa: E402
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
    for candidate in (user_path, project_path):
        if candidate.exists():
            return candidate
    return None


def _copy_godot_output(game_project: Path, file_name: str, target: Path) -> Path | None:
    source = _find_godot_output(game_project, file_name)
    if source is None:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, target)
    if source.parent == game_project:
        source.unlink(missing_ok=True)
    return target


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
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
        cwd=cwd,
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

    out_dir = ROOT / "reports" / "balance" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    target_out = ROOT / "reports" / "balance" / run_id / "raw_runs.jsonl"
    # Simpler: write to res://balance_runs.jsonl then cp.
    extra_args = [
        f"--runs={runs}",
        f"--policy={policy}",
        f"--seed={seed}",
        f"--weeks={weeks}",
        f"--difficulty={difficulty}",
        f"--scenario={scenario}",
        "--out=res://balance_runs.jsonl",
    ]
    proc = _run_godot(
        settings,
        script="res://scripts/tools/RunSimulation.gd",
        extra_args=extra_args,
    )
    if proc.returncode != 0:
        print("Godot simulation failed:", proc.stdout, proc.stderr, file=sys.stderr)
        return 3
    copied = _copy_godot_output(
        settings.game_project_path, "balance_runs.jsonl", target_out
    )
    if not copied:
        print("Could not find Godot output: balance_runs.jsonl", file=sys.stderr)
        return 4
    print(f"Copied raw runs to {target_out}")
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
    analyze(runs, out_dir)
    if args.run_anomalies:
        from game_analysis_agent.anomaly_detector import detect_and_write

        anomalies = detect_and_write(runs, out_dir)
        write_bug_summary(anomalies, out_dir)
    if args.run_value:
        analyze_and_write(out_dir)
    print(f"Analysis written to {out_dir}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    settings = get_settings()
    run_id = args.run_id or f"boundary-{uuid.uuid4().hex[:6]}"
    out_dir = ROOT / "reports" / "boundary" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    target_out = out_dir / "boundary_runs.jsonl"
    extra_args = [
        f"--runs={args.runs}",
        f"--policy={_canonical_policy(args.policy)}",
        f"--seed={args.seed}",
        f"--weeks={args.weeks}",
        f"--extreme={args.extreme}",
        "--out=res://boundary_runs.jsonl",
    ]
    proc = _run_godot(
        settings,
        script="res://scripts/tools/RunBoundaryProbe.gd",
        extra_args=extra_args,
    )
    if proc.returncode != 0:
        print("Godot boundary probe failed:", proc.stdout, proc.stderr, file=sys.stderr)
        return 3
    copied = _copy_godot_output(
        settings.game_project_path, "boundary_runs.jsonl", target_out
    )
    if not copied:
        print("Could not find boundary output: boundary_runs.jsonl", file=sys.stderr)
        return 4
    analyze_and_write(out_dir)
    # also feed the aggregate through the bug detector so the agent has
    # immediate numeric context.
    runs = load_runs(target_out)

    anomalies = detect_and_write(runs, out_dir)
    write_bug_summary(anomalies, out_dir)
    print(f"Boundary probe complete; {len(runs)} runs -> {target_out}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    settings = get_settings()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    selected = args.checks or ["content", "json-content", "economy", "risk"]
    results: list[dict[str, object]] = []
    failed = False
    for check in selected:
        if check == "route":
            _ensure_route_validation_inputs(settings)
        if check == "demo":
            _ensure_demo_validation_inputs(settings)
        script, file_name = VALIDATOR_SCRIPTS[check]
        out_arg = f"--out=res://{file_name}"
        proc = _run_godot(settings, script=script, extra_args=[out_arg])
        copied = _copy_user_file(settings.game_project_path, file_name, args.report_dir / file_name)
        result = {
            "check": check,
            "script": script,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "output_file": str(copied) if copied else "",
        }
        results.append(result)
        if proc.returncode != 0:
            failed = True
            print(f"[validate:{check}] failed", file=sys.stderr)
        else:
            print(f"[validate:{check}] ok")
    summary = {"passed": not failed, "checks": results}
    (args.report_dir / "validation_summary.json").write_text(
        __import__("json").dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 1 if failed else 0


def _ensure_route_validation_inputs(settings) -> None:
    route_specs = [
        ("study", "reports/route_audit_study.jsonl"),
        ("work", "reports/route_audit_work.jsonl"),
        ("admin", "reports/route_audit_admin_after_fix.jsonl"),
        ("social", "reports/route_audit_social.jsonl"),
        ("slacker", "reports/route_audit_slacker.jsonl"),
    ]
    for policy, out_path in route_specs:
        if _find_godot_output(settings.game_project_path, out_path):
            continue
        _run_godot(
            settings,
            script="res://scripts/tools/RunSimulation.gd",
            extra_args=[
                "--runs=6",
                f"--policy={policy}",
                "--difficulty=normal",
                "--scenario=default_first_semester",
                "--weeks=20",
                "--seed=42",
                f"--out=res://{out_path}",
            ],
        )


def _ensure_demo_validation_inputs(settings) -> None:
    demo_specs = [
        ("reports/gates_balanced_normal.jsonl", "balanced", "normal", "default_first_semester"),
        ("reports/gates_balanced_realistic.jsonl", "balanced", "realistic", "default_first_semester"),
        ("reports/gates_balanced_low_money.jsonl", "balanced", "normal", "low_money_start"),
    ]
    for out_path, policy, difficulty, scenario in demo_specs:
        if _find_godot_output(settings.game_project_path, out_path):
            continue
        _run_godot(
            settings,
            script="res://scripts/tools/RunSimulation.gd",
            extra_args=[
                "--runs=12",
                f"--policy={policy}",
                f"--difficulty={difficulty}",
                f"--scenario={scenario}",
                "--weeks=20",
                "--seed=42",
                f"--out=res://{out_path}",
            ],
        )
    if not _find_godot_output(settings.game_project_path, "reports/content_validation.json"):
        _run_godot(
            settings,
            script="res://scripts/tools/ValidateContent.gd",
            extra_args=["--out=res://reports/content_validation.json"],
        )
    if not _find_godot_output(settings.game_project_path, "reports/risk_guidance_validation.json"):
        _run_godot(
            settings,
            script="res://scripts/tools/ValidateRiskGuidance.gd",
            extra_args=["--out=res://reports/risk_guidance_validation.json"],
        )
    if not _find_godot_output(settings.game_project_path, "reports/route_boundary_validation.json"):
        _ensure_route_validation_inputs(settings)
        _run_godot(
            settings,
            script="res://scripts/tools/ValidateRouteBoundaries.gd",
            extra_args=["--out=res://reports/route_boundary_validation.json"],
        )


def _copy_user_file(game_project: Path, file_name: str, target: Path) -> Path | None:
    return _copy_godot_output(game_project, file_name, target)


def cmd_gates(args: argparse.Namespace) -> int:
    gates_path = args.gates or (ROOT / "config" / "gates.yaml")
    report = evaluate_report_dir(args.report_dir, gates_path)
    out = args.out or (args.report_dir / "gate_report.json")
    write_gate_report(report, out)
    print(f"Gate report written to {out}")
    if not report["passed"]:
        for failure in report["failures"]:
            print(f"[gate failed] {failure['gate']}: {failure['message']}", file=sys.stderr)
        return 1
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    settings = get_settings()
    extra_args = [
        "--out=res://event_graph.json",
    ]
    proc = _run_godot(
        settings,
        script="res://scripts/tools/ExportEventGraph.gd",
        extra_args=extra_args,
    )
    if proc.returncode != 0:
        print("ExportEventGraph failed:", proc.stdout, proc.stderr, file=sys.stderr)
        return 3
    target = args.report_dir / "event_graph.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    _copy_godot_output(settings.game_project_path, "event_graph.json", target)
    _copy_godot_output(
        settings.game_project_path,
        "action_catalog.json",
        args.report_dir / "action_catalog.json",
    )
    print(f"Event graph copied to {target}")
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
        for path in written:
            print(f"[{agent_name}] {path}")
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    settings = get_settings()
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
    for path in written:
        print(f"[interactive_player] {path}")
    print(
        f"[interactive_player] ending={result.final_ending} "
        f"steps={len(result.steps)}"
    )
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    rc = cmd_sim(args)
    if rc != 0:
        return rc
    # After `sim`, find the report dir
    latest = sorted((ROOT / "reports" / "balance").iterdir())[-1]
    return cmd_qa(
        argparse.Namespace(
            agent=AGENT_NAMES,
            report_dir=latest,
            agents=[name for name in AGENT_NAMES if name != "interactive_player"],
        )
    )


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

    probe_p = sub.add_parser(
        "probe", help="Run extreme-scenario boundary probes via Godot."
    )
    probe_p.add_argument("--run-id", default=None)
    probe_p.add_argument("--runs", type=int, default=3)
    probe_p.add_argument("--policy", default="balanced")
    probe_p.add_argument("--seed", type=int, default=42)
    probe_p.add_argument("--weeks", type=int, default=12)
    probe_p.add_argument(
        "--extreme",
        default="zero_money,deep_debt,no_energy,all_negative,no_language,flag_chaos,week_zero,already_registered",
    )
    probe_p.set_defaults(func=cmd_probe)

    export_p = sub.add_parser(
        "export", help="Export the event/action catalog from Godot."
    )
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
        help="Validator to run. Repeatable. Default: content + json-content + economy + risk.",
    )
    validate_p.set_defaults(func=cmd_validate)

    gates_p = sub.add_parser("gates", help="Evaluate config/gates.yaml against a report dir.")
    gates_p.add_argument("--report-dir", type=Path, required=True)
    gates_p.add_argument("--gates", type=Path, default=None)
    gates_p.add_argument("--out", type=Path, default=None)
    gates_p.set_defaults(func=cmd_gates)

    qa_p = sub.add_parser(
        "qa", help="Run all (or selected) LLM agents against a report dir."
    )
    qa_p.add_argument(
        "--report-dir", type=Path, required=True
    )
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

    play_p = sub.add_parser(
        "play", help="Drive the LLM as a player with the tool loop."
    )
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
    play_p.add_argument(
        "--seed", type=int, default=42, help="Seed passed to the persona block."
    )
    play_p.set_defaults(func=cmd_play)

    all_p = sub.add_parser("all", help="sim -> analyze -> qa in one command.")
    all_p.add_argument("--run-id", default=None)
    all_p.add_argument("--runs", type=int, default=None)
    all_p.add_argument("--policy", default=None)
    all_p.add_argument("--seed", type=int, default=None)
    all_p.add_argument("--weeks", type=int, default=None)
    all_p.add_argument("--difficulty", default=None)
    all_p.add_argument("--scenario", default=None)
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
            "balance", "content_qa", "event_graph",
            "bug_hunter", "boundary_prober", "value_reviewer",
        ]
    if hasattr(args, "agents") and args.agents is None:
        args.agents = [
            "balance", "content_qa", "event_graph",
            "bug_hunter", "boundary_prober", "value_reviewer",
        ]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
