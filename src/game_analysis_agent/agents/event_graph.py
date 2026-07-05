"""Event graph QA agent: emit reachability + broken-chain report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent


class EventGraphAgent(Agent):
    name = "event_graph"
    default_output_files = ("event_graph_report.md",)
    default_temperature = 0.1

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        path = self.prompts_root / f"{self.name}_user.md"
        return path.read_text(encoding="utf-8")


__all__ = ["EventGraphAgent"]
