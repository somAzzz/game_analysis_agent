"""Bug hunter agent: read anomalies + summary and emit a
``bug_diagnosis.md`` with severity-ranked suspect bugs.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent, render_prompt_text
from game_analysis_agent.analytics import load_runs
from game_analysis_agent.anomaly_detector import write_anomalies_jsonl
from game_analysis_agent.schemas import Anomaly


class BugHunterAgent(Agent):
    name = "bug_hunter"
    default_output_files = ("bug_diagnosis.md",)
    default_temperature = 0.2
    max_anomaly_samples = 50

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.anomalies: list[Anomaly] = []
        self.summary_text: str = ""

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        raw_path = report_dir / "raw_runs.jsonl"
        anomalies_path = report_dir / "anomalies.jsonl"
        self.anomalies = self._ensure_anomalies(raw_path, anomalies_path)
        self.summary_text = self._summarize(self.anomalies)

        template_path = self.prompts_root / f"{self.name}_user.md"
        user_template = template_path.read_text(encoding="utf-8")
        # Inject the structured anomalies + summary alongside the report bundle.
        extras = (
            "## Auto-detected Anomalies (machine-readable)\n\n"
            + self._render_anomaly_samples(self.anomalies)
            + "\n\n"
            "## Anomaly Distribution\n\n"
            + self.summary_text
        )
        # We rebuild the bundle so the model sees the canonical files + extras.
        from game_analysis_agent.report_bundle import (
            DEFAULT_REPORT_FILES,
            read_report_bundle,
        )

        files = list(DEFAULT_REPORT_FILES) + list(self.extra_files)
        bundle = read_report_bundle(report_dir, files=files)
        bundle += "\n\n" + extras
        return render_prompt_text(user_template, bundle)

    def _render_anomaly_samples(self, anomalies: list[Anomaly]) -> str:
        if not anomalies:
            return "(no auto-detected anomalies)"
        samples = anomalies[: self.max_anomaly_samples]
        omitted = len(anomalies) - len(samples)
        header = (
            f"Showing {len(samples)} of {len(anomalies)} anomalies; "
            f"{omitted} omitted after deterministic sampling."
        )
        return (
            header
            + "\n\n"
            "```jsonl\n"
            + "\n".join(a.model_dump_json() for a in samples)
            + "\n```"
        )

    def _ensure_anomalies(
        self, raw_path: Path, anomalies_path: Path
    ) -> list[Anomaly]:
        # anomalies.jsonl is derived evidence. Recompute it whenever the raw
        # trace exists so detector fixes cannot leave QA reading stale rows.
        if raw_path.exists():
            runs = load_runs(raw_path)
            from game_analysis_agent.anomaly_detector import detect_anomalies

            anomalies = detect_anomalies(runs)
            write_anomalies_jsonl(anomalies, anomalies_path)
            return anomalies
        if anomalies_path.exists() and anomalies_path.stat().st_size > 0:
            return [
                Anomaly.model_validate_json(line)
                for line in anomalies_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        return []

    @staticmethod
    def _summarize(anomalies: list[Anomaly]) -> str:
        kinds = Counter(a.kind for a in anomalies)
        severities = Counter(a.severity for a in anomalies)
        runs = Counter(a.run_id for a in anomalies)
        lines = ["- Anomaly kinds:"]
        for kind, count in kinds.most_common():
            lines.append(f"  - `{kind}` × {count}")
        lines.append("- Severities:")
        for sev, count in severities.most_common():
            lines.append(f"  - `{sev}` × {count}")
        lines.append(f"- Total runs touched: **{len(runs)}**")
        return "\n".join(lines)


__all__ = ["BugHunterAgent"]
