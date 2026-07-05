"""Content QA agent: emit a table of content issues per event."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent


class ContentQAAgent(Agent):
    name = "content_qa"
    default_output_files = ("content_issues.md",)
    default_temperature = 0.15

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        path = self.prompts_root / f"{self.name}_user.md"
        return path.read_text(encoding="utf-8")


__all__ = ["ContentQAAgent"]
