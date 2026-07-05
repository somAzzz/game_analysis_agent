"""Boundary prober agent: read the JSONL produced by
``scripts/tools/RunBoundaryProbe.gd`` and the per-extreme anomaly rollup,
then emit ``boundary_report.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent, render_prompt_text
from game_analysis_agent.report_bundle import DEFAULT_REPORT_FILES, read_report_bundle


class BoundaryProberAgent(Agent):
    name = "boundary_prober"
    default_output_files = ("boundary_report.md",)
    default_temperature = 0.2

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        user_template = (self.prompts_root / f"{self.name}_user.md").read_text(encoding="utf-8")

        boundary_runs_path = report_dir / "boundary_runs.jsonl"
        boundary_text = (
            self._render_boundary_runs(boundary_runs_path)
            if boundary_runs_path.exists()
            else "(no boundary_runs.jsonl — please run `tools/run_gameplay_agent.py probe` first)"
        )

        files = list(DEFAULT_REPORT_FILES) + list(self.extra_files) + ["boundary_runs.jsonl"]
        bundle = read_report_bundle(report_dir, files=files)
        extras = (
            "## Boundary Run Summary (per extreme)\n\n"
            + boundary_text
            + "\n\n## Boundary Raw Runs (head 30)\n\n"
            + self._head_jsonl(boundary_runs_path, limit=30)
        )
        bundle += "\n\n" + extras
        return render_prompt_text(user_template, bundle)

    @staticmethod
    def _render_boundary_runs(path: Path) -> str:
        runs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        by_extreme: dict[str, list[dict]] = {}
        for run in runs:
            by_extreme.setdefault(str(run.get("extreme", "unknown")), []).append(run)
        lines: list[str] = []
        for extreme, items in sorted(by_extreme.items()):
            ending_counts: dict[str, int] = {}
            week_durations: list[int] = []
            anomaly_kinds: list[str] = []
            for run in items:
                ending_id = run.get("final_ending_id") or "unknown"
                ending_counts[ending_id] = ending_counts.get(ending_id, 0) + 1
                week_durations.append(int(run.get("final_week", 0) or 0))
                for anomaly in run.get("anomalies", []) or []:
                    anomaly_kinds.append(str(anomaly.get("kind", "unknown")))
            avg_week = (sum(week_durations) / max(1, len(week_durations))) if week_durations else 0
            lines.append(f"### Extreme: `{extreme}` × {len(items)}")
            lines.append("")
            lines.append(f"- Average final week: `{avg_week:.1f}`")
            if ending_counts:
                ending_str = ", ".join(
                    f"`{k}` = {v}" for k, v in sorted(ending_counts.items())
                )
                lines.append(f"- Ending distribution: {ending_str}")
            if anomaly_kinds:
                from collections import Counter

                top = Counter(anomaly_kinds).most_common(3)
                lines.append("- Top anomalies: " + ", ".join(
                    f"`{k}` × {v}" for k, v in top
                ))
            lines.append("")
        return "\n".join(lines) if lines else "(no boundary runs yet)"

    @staticmethod
    def _head_jsonl(path: Path, limit: int) -> str:
        if not path.exists():
            return "(missing)"
        lines = [
            line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        head = lines[:limit]
        return "```jsonl\n" + "\n".join(head) + "\n```"


__all__ = ["BoundaryProberAgent"]
