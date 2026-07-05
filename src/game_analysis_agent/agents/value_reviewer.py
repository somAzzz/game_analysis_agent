"""Value reviewer agent: reads ``value_report.json`` + the standard
bundle and emits ``value_review.md`` with narrative explanations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent, render_prompt_text
from game_analysis_agent.report_bundle import DEFAULT_REPORT_FILES, read_report_bundle
from game_analysis_agent.value_analyzer import analyze_and_write


class ValueReviewerAgent(Agent):
    name = "value_reviewer"
    default_output_files = ("value_review.md",)
    default_temperature = 0.15

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        report_json = report_dir / "value_report.json"
        if not report_json.exists():
            analyze_and_write(report_dir)
        bundle = read_report_bundle(
            report_dir,
            files=list(DEFAULT_REPORT_FILES)
            + list(self.extra_files)
            + ["value_report.json"],
        )
        # Emit the structured findings JSON for the LLM too.
        if report_json.exists():
            bundle += "\n\n## Value Findings (structured)\n\n```json\n" + report_json.read_text(
                encoding="utf-8"
            ) + "\n```\n"
        user_template = (self.prompts_root / f"{self.name}_user.md").read_text(
            encoding="utf-8"
        )
        return render_prompt_text(user_template, bundle)


__all__ = ["ValueReviewerAgent"]
