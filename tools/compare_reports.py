#!/usr/bin/env python3
"""Diff two ``reports/balance/<run-id>/`` directories.

This is the T07 deliverable from ``docs/ACTION_PLAN.md`` — a CLI that
takes the before / after report dirs produced by
``tools/run_gameplay_agent.py`` and emits a human-readable Markdown
summary alongside a machine-readable JSON diff.

Usage:

.. code-block:: bash

   python3 tools/compare_reports.py \\
     --before reports/balance/v01-normal-balanced-r200 \\
     --after  reports/balance/v02-normal-balanced-r200 \\
     --out    reports/compare/v01-v02-balanced.md

Output:

* ``compare_summary.md`` — Markdown with per-dimension Δ tables.
* ``compare_diff.json``   — raw diff payload (one dict per dimension).

Dimensions covered:

1. ``ending_distribution.csv``     — ending-level rate Δ
2. ``action_pick_rates.csv``       — action-level rate Δ
3. ``weekly_stats.csv``            — per-week mean Δ for each metric
4. ``anomalies.jsonl``             — kind-level count Δ
5. ``value_report.json``           — finding_kind Δ
6. ``route_report.json``           — finding_kind Δ
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Loaders (kept tiny + dependency-free so the CLI is easy to invoke)
# ---------------------------------------------------------------------------


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Per-dimension diff functions
# ---------------------------------------------------------------------------


def _diff_endings(before: list[dict[str, str]], after: list[dict[str, str]]) -> dict[str, Any]:
    def _index(rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
        out: dict[tuple[str, str], float] = {}
        for row in rows:
            policy = str(row.get("policy", ""))
            ending = str(row.get("ending_id", ""))
            try:
                rate = float(row.get("rate", 0.0))
            except (TypeError, ValueError):
                continue
            out[(policy, ending)] = rate
        return out

    before_map = _index(before)
    after_map = _index(after)
    keys = sorted(set(before_map) | set(after_map))
    rows: list[dict[str, Any]] = []
    for key in keys:
        b = before_map.get(key, 0.0)
        a = after_map.get(key, 0.0)
        rows.append(
            {
                "policy": key[0],
                "ending_id": key[1],
                "before": b,
                "after": a,
                "delta": round(a - b, 6),
            }
        )
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return {"rows": rows, "top": rows[:10]}


def _diff_actions(before: list[dict[str, str]], after: list[dict[str, str]]) -> dict[str, Any]:
    def _index(rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
        out: dict[tuple[str, str], float] = {}
        for row in rows:
            policy = str(row.get("policy", ""))
            action_id = str(row.get("action_id", ""))
            try:
                rate = float(row.get("rate_per_run", 0.0))
            except (TypeError, ValueError):
                continue
            out[(policy, action_id)] = rate
        return out

    before_map = _index(before)
    after_map = _index(after)
    keys = sorted(set(before_map) | set(after_map))
    rows: list[dict[str, Any]] = []
    for key in keys:
        b = before_map.get(key, 0.0)
        a = after_map.get(key, 0.0)
        rows.append(
            {
                "policy": key[0],
                "action_id": key[1],
                "before": b,
                "after": a,
                "delta": round(a - b, 6),
            }
        )
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return {"rows": rows, "top": rows[:15]}


def _diff_weekly_stats(
    before: list[dict[str, str]], after: list[dict[str, str]]
) -> dict[str, Any]:
    def _index(rows: list[dict[str, str]]) -> dict[tuple[str, int, str], float]:
        out: dict[tuple[str, int, str], float] = {}
        for row in rows:
            policy = str(row.get("policy", ""))
            try:
                week = int(row.get("week", 0))
            except (TypeError, ValueError):
                continue
            metric = str(row.get("metric", ""))
            try:
                mean = float(row.get("mean", 0.0))
            except (TypeError, ValueError):
                continue
            out[(policy, week, metric)] = mean
        return out

    before_map = _index(before)
    after_map = _index(after)
    keys = sorted(set(before_map) | set(after_map))
    rows: list[dict[str, Any]] = []
    for key in keys:
        b = before_map.get(key, 0.0)
        a = after_map.get(key, 0.0)
        rows.append(
            {
                "policy": key[0],
                "week": key[1],
                "metric": key[2],
                "before": b,
                "after": a,
                "delta": round(a - b, 4),
            }
        )
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return {"rows": rows, "top": rows[:20]}


def _diff_anomalies(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, Any]:
    def _count(rows: list[dict[str, Any]]) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for row in rows:
            kind = str(row.get("kind", "unknown"))
            out[kind] += 1
        return dict(sorted(out.items()))

    before_count = _count(before)
    after_count = _count(after)
    kinds = sorted(set(before_count) | set(after_count))
    rows: list[dict[str, Any]] = []
    for kind in kinds:
        b = before_count.get(kind, 0)
        a = after_count.get(kind, 0)
        rows.append(
            {
                "kind": kind,
                "before": b,
                "after": a,
                "delta": a - b,
            }
        )
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return {"rows": rows}


def _diff_finding_report(
    before: dict[str, Any] | None, after: dict[str, Any] | None
) -> dict[str, Any]:
    def _index(payload: dict[str, Any] | None) -> dict[str, int]:
        if not payload:
            return {}
        by_kind = payload.get("by_kind", {})
        return {str(k): int(v) for k, v in by_kind.items()}

    before_map = _index(before)
    after_map = _index(after)
    kinds = sorted(set(before_map) | set(after_map))
    rows: list[dict[str, Any]] = []
    for kind in kinds:
        b = before_map.get(kind, 0)
        a = after_map.get(kind, 0)
        rows.append(
            {
                "kind": kind,
                "before": b,
                "after": a,
                "delta": a - b,
            }
        )
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return {"rows": rows}


# ---------------------------------------------------------------------------
# Public entry point — usable both as a library and via the CLI.
# ---------------------------------------------------------------------------


def compare_reports(before_dir: Path, after_dir: Path) -> dict[str, Any]:
    """Return the structured diff between two report directories."""
    diff: dict[str, Any] = {
        "before": str(before_dir),
        "after": str(after_dir),
        "endings": _diff_endings(
            _load_csv(before_dir / "ending_distribution.csv"),
            _load_csv(after_dir / "ending_distribution.csv"),
        ),
        "actions": _diff_actions(
            _load_csv(before_dir / "action_pick_rates.csv"),
            _load_csv(after_dir / "action_pick_rates.csv"),
        ),
        "weekly_stats": _diff_weekly_stats(
            _load_csv(before_dir / "weekly_stats.csv"),
            _load_csv(after_dir / "weekly_stats.csv"),
        ),
        "anomalies": _diff_anomalies(
            _load_jsonl(before_dir / "anomalies.jsonl"),
            _load_jsonl(after_dir / "anomalies.jsonl"),
        ),
        "value_report": _diff_finding_report(
            _load_json(before_dir / "value_report.json"),
            _load_json(after_dir / "value_report.json"),
        ),
        "route_report": _diff_finding_report(
            _load_json(before_dir / "route_report.json"),
            _load_json(after_dir / "route_report.json"),
        ),
    }
    return diff


def render_markdown(diff: dict[str, Any]) -> str:
    """Render the diff as a Markdown report."""
    lines: list[str] = []
    lines.append("# Report Diff\n")
    lines.append(f"- before: `{diff['before']}`")
    lines.append(f"- after:  `{diff['after']}`")
    lines.append("")

    # Endings
    lines.append("## Endings (rate Δ)\n")
    lines.append("| policy | ending_id | before | after | Δ |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for row in diff["endings"]["top"]:
        lines.append(
            f"| {row['policy']} | {row['ending_id']} | {row['before']:.3f} | "
            f"{row['after']:.3f} | {row['delta']:+.3f} |"
        )
    lines.append("")

    # Actions
    lines.append("## Actions (rate_per_run Δ)\n")
    lines.append("| policy | action_id | before | after | Δ |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for row in diff["actions"]["top"]:
        lines.append(
            f"| {row['policy']} | {row['action_id']} | {row['before']:.3f} | "
            f"{row['after']:.3f} | {row['delta']:+.3f} |"
        )
    lines.append("")

    # Weekly stats
    lines.append("## Weekly stats (mean Δ, top 20)\n")
    lines.append("| policy | week | metric | before | after | Δ |")
    lines.append("| --- | ---: | --- | ---: | ---: | ---: |")
    for row in diff["weekly_stats"]["top"]:
        lines.append(
            f"| {row['policy']} | {row['week']} | {row['metric']} | "
            f"{row['before']:.2f} | {row['after']:.2f} | {row['delta']:+.2f} |"
        )
    lines.append("")

    # Anomalies
    lines.append("## Anomalies (count Δ)\n")
    lines.append("| kind | before | after | Δ |")
    lines.append("| --- | ---: | ---: | ---: |")
    for row in diff["anomalies"]["rows"]:
        lines.append(
            f"| {row['kind']} | {row['before']} | {row['after']} | {row['delta']:+d} |"
        )
    lines.append("")

    # Value report
    lines.append("## value_report.json (finding_kind Δ)\n")
    lines.append("| kind | before | after | Δ |")
    lines.append("| --- | ---: | ---: | ---: |")
    for row in diff["value_report"]["rows"]:
        lines.append(
            f"| {row['kind']} | {row['before']} | {row['after']} | {row['delta']:+d} |"
        )
    lines.append("")

    # Route report
    lines.append("## route_report.json (finding_kind Δ)\n")
    lines.append("| kind | before | after | Δ |")
    lines.append("| --- | ---: | ---: | ---: |")
    for row in diff["route_report"]["rows"]:
        lines.append(
            f"| {row['kind']} | {row['before']} | {row['after']} | {row['delta']:+d} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="compare_reports")
    parser.add_argument("--before", type=Path, required=True, help="Before report dir.")
    parser.add_argument("--after", type=Path, required=True, help="After report dir.")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "compare" / "compare_summary.md",
        help="Path to write the Markdown summary.",
    )
    parser.add_argument(
        "--diff-json",
        type=Path,
        default=None,
        help="Path to write the machine-readable diff JSON (defaults next to --out).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.before.exists():
        print(f"--before does not exist: {args.before}", file=sys.stderr)
        return 2
    if not args.after.exists():
        print(f"--after does not exist: {args.after}", file=sys.stderr)
        return 3

    diff = compare_reports(args.before, args.after)
    out_md = args.out
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(diff), encoding="utf-8")

    out_json = args.diff_json or out_md.with_name("compare_diff.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


__all__ = [
    "build_parser",
    "compare_reports",
    "main",
    "render_markdown",
]


if __name__ == "__main__":
    raise SystemExit(main())