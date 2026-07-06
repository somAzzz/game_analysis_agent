"""Balance agent: analyse ending distribution, attribute curves, action
dominance and produce diagnosis + tuning proposal markdown files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent, AgentOutput


class BalanceAgent(Agent):
    """Reads the standard balance bundle and emits diagnosis + proposal."""

    name = "balance"
    default_output_files = ("agent_diagnosis.md", "tuning_proposal.md")
    default_temperature = 0.2

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        return self.read_prompt_template("user")

    def _split_outputs(self, response: str) -> list[AgentOutput]:
        marker = "# Tuning Proposal"
        before, after = response, ""
        if marker in response:
            before, after = response.split(marker, 1)
            before = before.strip() + "\n"
            after = f"{marker}{after.strip()}\n"
        else:
            after = f"{marker}\n\nAgent did not emit a separate section.\n"
            before = response.strip() + "\n"
        return [
            AgentOutput(file_name="agent_diagnosis.md", content=before),
            AgentOutput(file_name="tuning_proposal.md", content=after),
        ]


__all__ = ["BalanceAgent"]
