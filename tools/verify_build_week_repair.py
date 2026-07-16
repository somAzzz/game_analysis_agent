#!/usr/bin/env python3
"""Run focused, fixed, and holdout proof and write an accept/reject record."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.design_contract import load_design_contract  # noqa: E402
from game_analysis_agent.repair_experiment import (  # noqa: E402
    CodexProvenance,
    FocusedTestResult,
    PatchEvidence,
    RepairCohort,
    RepairExperimentPlan,
    write_repair_record_atomic,
)
from game_analysis_agent.repair_verification import (  # noqa: E402
    build_repair_record,
    run_repair_cohort,
)
from game_analysis_agent.settings import Settings  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--patch-evidence", type=Path, required=True)
    parser.add_argument("--baseline-game", type=Path, required=True)
    parser.add_argument("--patched-game", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--task-reference", required=True)
    parser.add_argument("--feedback-session-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--concurrency", type=int, default=4, choices=(1, 2, 3, 4))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = RepairExperimentPlan.model_validate_json(args.plan.read_text(encoding="utf-8"))
    patch = PatchEvidence.model_validate_json(
        args.patch_evidence.read_text(encoding="utf-8")
    )
    design = load_design_contract(
        ROOT / "config/build_week_2026_design_contract.json", project_root=ROOT
    )
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    focused = (_run_focused_test(args.patched_game.resolve(), settings, output),)
    definitions = (
        (
            RepairCohort.BASELINE_FIXED,
            args.baseline_game,
            plan.baseline_game_commit,
            plan.fixed_seeds,
        ),
        (
            RepairCohort.PATCHED_FIXED,
            args.patched_game,
            patch.patched_commit,
            plan.fixed_seeds,
        ),
        (
            RepairCohort.BASELINE_HOLDOUT,
            args.baseline_game,
            plan.baseline_game_commit,
            plan.holdout_seeds,
        ),
        (
            RepairCohort.PATCHED_HOLDOUT,
            args.patched_game,
            patch.patched_commit,
            plan.holdout_seeds,
        ),
    )
    snapshots = []
    for cohort, game, commit, seeds in definitions:
        snapshot = run_repair_cohort(
            project_root=ROOT,
            game_root=game,
            game_commit=commit,
            cohort=cohort,
            seeds=seeds,
            output_dir=output / cohort.value,
            design=design,
            settings=settings,
            concurrency=args.concurrency,
            progress=lambda message: print(message, flush=True),
        )
        snapshots.append(snapshot)
    record = build_repair_record(
        plan=plan,
        patch=patch,
        focused_tests=focused,
        snapshots=tuple(snapshots),
        design=design,
        codex=CodexProvenance(
            task_reference=args.task_reference,
            feedback_session_id=args.feedback_session_id,
            model=args.model,
        ),
        completed_at=datetime.now(tz=UTC),
    )
    write_repair_record_atomic(output / "repair_experiment.json", record)
    (output / "comparison.json").write_text(
        record.comparison.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output / "repair_summary.md").write_text(_summary(record), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": record.decision.value,
                "failed_gates": [
                    item.gate_id for item in record.gates if item.status.value == "failed"
                ],
                "fixed_reduction": record.comparison.fixed_relative_reduction,
                "holdout_reduction": record.comparison.holdout_relative_reduction,
                "record": str(output / "repair_experiment.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if record.decision.value == "accepted" else 1


def _run_focused_test(
    patched_game: Path, settings: Settings, output: Path
) -> FocusedTestResult:
    command = (
        settings.godot_bin,
        "--headless",
        "--path",
        str(patched_game),
        "-s",
        "res://scripts/tools/ValidateEconomyRules.gd",
    )
    started = time.perf_counter()
    completed = subprocess.run(
        command, check=False, capture_output=True, text=True, timeout=300
    )
    duration = time.perf_counter() - started
    text = (completed.stdout + completed.stderr).replace(str(Path.home()), "<home>")
    log = output / "focused-test.log"
    log.write_text(text, encoding="utf-8")
    return FocusedTestResult(
        command=(Path(command[0]).name, *command[1:]),
        exit_code=completed.returncode,
        output_sha256=hashlib.sha256(text.encode()).hexdigest(),
        duration_seconds=round(duration, 3),
    )


def _summary(record) -> str:  # noqa: ANN001
    lines = [
        "# Repair experiment",
        "",
        f"- Decision: **{record.decision.value}**",
        f"- Hypothesis: {record.plan.hypothesis}",
        f"- Mechanism: `{record.plan.mechanism_class}`",
        f"- Fixed relative reduction: {record.comparison.fixed_relative_reduction:.1%}",
        f"- Holdout relative reduction: {record.comparison.holdout_relative_reduction:.1%}",
        f"- Reason: {record.decision_reason}",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- {item.gate_id}: **{item.status.value}** — {item.detail}"
        for item in record.gates
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
