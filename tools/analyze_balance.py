#!/usr/bin/env python3
"""CLI: aggregate raw_runs.jsonl into summary CSVs / JSON / anomaly report.

The statistical logic lives in :mod:`game_analysis_agent.analytics`. This
script is intentionally a thin layer so it can stay as a shell-friendly
command for CI scripts while the testing surface stays in Python.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.analytics import (  # noqa: E402
    compute_action_pick_rates,
    compute_choice_pick_rates,
    compute_ending_distribution,
    compute_event_trigger_rates,
    compute_summary,
    compute_weekly_stats,
    load_runs,
    write_csv,
)
from game_analysis_agent.coverage import analyze_and_write_coverage  # noqa: E402
from game_analysis_agent.report_manifest import write_report_manifest  # noqa: E402


def usage() -> None:
    print("Usage: python3 tools/analyze_balance.py <raw_runs.jsonl> <out_dir>")


def analyze(runs: list[dict], out_dir: Path, *, raw_runs_path: Path | None = None) -> dict[str, list]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ending_rows = compute_ending_distribution(runs)
    action_rows = compute_action_pick_rates(runs)
    event_rows = compute_event_trigger_rates(runs)
    choice_rows = compute_choice_pick_rates(runs)
    weekly_rows = compute_weekly_stats(runs)
    write_csv(
        out_dir / "ending_distribution.csv",
        [
            "policy",
            "difficulty",
            "scenario",
            "ending_id",
            "count",
            "sample_size",
            "rate",
            "ci95_low",
            "ci95_high",
        ],
        ending_rows,
    )
    write_csv(
        out_dir / "weekly_stats.csv",
        ["policy", "week", "metric", "mean", "median", "p10", "p90", "min", "max"],
        weekly_rows,
    )
    write_csv(
        out_dir / "action_pick_rates.csv",
        ["policy", "action_id", "count", "rate_per_run"],
        action_rows,
    )
    write_csv(
        out_dir / "event_trigger_rates.csv",
        ["policy", "event_id", "count", "rate_per_run"],
        event_rows,
    )
    write_csv(
        out_dir / "choice_pick_rates.csv",
        ["policy", "event_id", "choice_id", "count", "rate_per_event"],
        choice_rows,
    )
    summary = compute_summary(runs)
    analyze_and_write_coverage(runs, out_dir)
    summary["generated_files"] = [
        "ending_distribution.csv",
        "weekly_stats.csv",
        "action_pick_rates.csv",
        "event_trigger_rates.csv",
        "choice_pick_rates.csv",
        "coverage_report.json",
    ]
    (out_dir / "summary.json").write_text(
        __import__("json").dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report_manifest(
        out_dir,
        report_type="balance",
        command="analyze_balance",
        source_files=[raw_runs_path or (out_dir / "raw_runs.jsonl")],
        generated_files=summary["generated_files"] + ["summary.json"],
        summary={
            "total_runs": summary.get("total_runs", len(runs)),
            "policies": summary.get("policies", {}),
            "run_id_count": len({run.get("run_id") for run in runs}),
        },
    )
    return {
        "ending_rows": ending_rows,
        "action_rows": action_rows,
        "event_rows": event_rows,
        "choice_rows": choice_rows,
        "weekly_rows": weekly_rows,
    }


def main() -> int:
    if len(sys.argv) != 3:
        usage()
        return 2
    raw_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    if not raw_path.exists():
        print(f"Missing raw file: {raw_path}", file=sys.stderr)
        return 1
    runs = load_runs(raw_path)
    analyze(runs, out_dir, raw_runs_path=raw_path)
    print(f"Analysis written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
