"""Cluster :class:`Anomaly` rows into human-readable summaries.

Output:

* ``bugs.jsonl``   — one JSON object per anomaly (raw).
* ``bugs_summary.md`` — Markdown grouped by ``kind`` + severity, with
  frequency counts and a representative evidence line per cluster.

The summarizer is deterministic; the LLM-backed :mod:`agents.bug_hunter`
adds narrative explanation and patch proposals on top.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from game_analysis_agent.schemas import Anomaly


def summarize_anomalies(anomalies: Iterable[Anomaly]) -> dict[str, Any]:
    by_kind: dict[str, list[Anomaly]] = defaultdict(list)
    severity_counter: Counter[str] = Counter()
    runs_affected: set[int] = set()
    for anomaly in anomalies:
        by_kind[anomaly.kind].append(anomaly)
        severity_counter[anomaly.severity] += 1
        runs_affected.add(anomaly.run_id)

    summary = {
        "total_anomalies": sum(len(items) for items in by_kind.values()),
        "runs_affected": len(runs_affected),
        "by_severity": dict(severity_counter),
        "by_kind": {},
    }
    for kind, items in by_kind.items():
        policies = Counter(item.policy for item in items if item.policy)
        representative = items[0]
        summary["by_kind"][kind] = {
            "count": len(items),
            "policies": dict(policies),
            "example_run_id": representative.run_id,
            "example_week": representative.week,
            "example_message": representative.message,
        }
    return summary


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = ["# Bug & Anomaly Summary", ""]
    lines.append(f"- Total anomalies: **{summary['total_anomalies']}**")
    lines.append(f"- Runs affected: **{summary['runs_affected']}**")
    if summary["by_severity"]:
        lines.append("- By severity: " + ", ".join(
            f"`{k}` = {v}" for k, v in sorted(summary["by_severity"].items())
        ))
    lines.append("")
    lines.append("## By Kind")
    lines.append("")
    if not summary["by_kind"]:
        lines.append("- No anomalies detected.")
        return "\n".join(lines) + "\n"
    for kind, info in sorted(summary["by_kind"].items()):
        lines.append(f"### `{kind}` × {info['count']}")
        lines.append("")
        if info["example_message"]:
            lines.append(f"> {info['example_message']}")
            lines.append("")
        if info["policies"]:
            policy_breakdown = ", ".join(
                f"`{k}` ({v})" for k, v in sorted(info["policies"].items())
            )
            lines.append(f"- Affects policies: {policy_breakdown}")
        lines.append(
            f"- Example: run #{info['example_run_id']}, "
            f"week {info['example_week']}"
        )
        lines.append("")
    return "\n".join(lines) + "\n"


def write_bug_summary(
    anomalies: Iterable[Anomaly],
    report_dir: Path,
) -> dict[str, Any]:
    anomalies = list(anomalies)
    summary = summarize_anomalies(anomalies)
    (report_dir / "bugs_summary.md").write_text(
        render_summary_markdown(summary),
        encoding="utf-8",
    )
    with (report_dir / "bugs.jsonl").open("w", encoding="utf-8") as handle:
        for anomaly in anomalies:
            handle.write(anomaly.model_dump_json())
            handle.write("\n")
    return summary


__all__ = [
    "render_summary_markdown",
    "summarize_anomalies",
    "write_bug_summary",
]
