"""Interactive player agent: drives the LLM through the Godot game via
``game_analysis_agent.game_tools`` tool calling.

Each round the model reads the game state via ``get_state()`` + tool
calls, picks actions, optionally resolves an event choice, and we
forward the call results back as a ``role=tool`` message until the
model emits a final answer.

Outputs:

* ``playthrough.jsonl`` — every step (``{"week": ..., "state": ...,
  "actions": [...], "event_choice_index": ..., "tool_events": [...]}``).
* ``playthrough_summary.md`` — narrative postmortem.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent, AgentOutput, AgentRunResult
from game_analysis_agent.llm_client import LocalLLMClient
from game_analysis_agent.schemas import (
    AgentRunReport,
    LLMCall,
    ToolExecutionEvent,
)
from game_analysis_agent.settings import Settings
from game_analysis_agent.tool_loop import (
    DEFAULT_MAX_TOOL_RESULT_CHARS,
    DEFAULT_MAX_TOTAL_TOOL_RESULT_CHARS,
    OpenAICompatibleToolLoop,
)


@dataclass
class PlaythroughStep:
    week: int
    state_before: dict[str, Any]
    actions: list[str] = field(default_factory=list)
    triggered_event_id: str = ""
    event_choice_index: int = -1
    state_after: dict[str, Any] = field(default_factory=dict)
    llm_summary: str = ""
    tool_events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class InteractivePlayerResult:
    report: AgentRunReport
    steps: list[PlaythroughStep]
    final_state: dict[str, Any]
    final_ending: str


class InteractivePlayerAgent(Agent):
    name = "interactive_player"
    default_output_files = ("playthrough_summary.md",)
    default_temperature = 0.3

    def __init__(
        self,
        *,
        llm: LocalLLMClient,
        prompts_root: Path,
        settings: Settings | None = None,
        tool_definitions: list[dict[str, Any]] | None = None,
        tool_map: dict[str, Callable[..., Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        max_tool_rounds: int | None = None,
        max_weeks: int = 20,
        extra_files: tuple[str, ...] = (),
        output_files: tuple[str, ...] | None = None,
        temperature: float | None = None,
    ) -> None:
        super().__init__(
            llm=llm,
            prompts_root=prompts_root,
            settings=settings,
            output_files=output_files,
            temperature=temperature,
            extra_files=extra_files,
        )
        self.tool_definitions = tool_definitions or []
        self.tool_map = tool_map or {}
        self.tool_choice = tool_choice
        self.max_tool_rounds = max_tool_rounds or (settings.tool_max_rounds if settings else 8)
        self.max_weeks = max_weeks

    def run(
        self,
        report_dir: Path,
        context: dict[str, Any] | None = None,
    ) -> AgentRunResult:  # type: ignore[override]
        """Override :meth:`Agent.run` so the tool loop owns the LLM calls.

        The base implementation is single-shot — the interactive player
        must drive many turns so it sidesteps the template method here
        and calls :meth:`play_through` directly. The actual artifacts
        (``playthrough.jsonl``, ``playthrough_summary.md``) are written
        to ``report_dir`` by :meth:`play_through`; this method just
        re-reads them so the caller can treat all agents uniformly.
        """
        context = context or {}
        result, written_paths = self.play_through(report_dir, context=context)
        outputs: list[AgentOutput] = []
        for path in written_paths:
            outputs.append(
                AgentOutput(file_name=path.name, content=path.read_text(encoding="utf-8"))
            )
        return AgentRunResult(agent=self.name, outputs=outputs)

    # -- actual gameplay ---------------------------------------------------

    def play_through(
        self,
        report_dir: Path,
        *,
        playthrough_path: Path | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[InteractivePlayerResult, list[Path]]:
        context = context or {}
        report_dir.mkdir(parents=True, exist_ok=True)
        playthrough_path = playthrough_path or report_dir / "playthrough.jsonl"

        system_prompt = self.build_system_prompt()
        prompt_text = self._opening_user_prompt(report_dir, context)

        llm_calls: list[LLMCall] = []
        tool_events: list[ToolExecutionEvent] = []
        steps: list[PlaythroughStep] = []
        budget_used = 0

        # Capture LLM calls + tool events into local lists by wrapping
        # the underlying sink. The base :class:`LocalLLMClient` already
        # builds an LLMCall row per chat round inside the loop, so we
        # also need to push those into `llm_calls`.
        loop = OpenAICompatibleToolLoop(
            client=self.llm.client,
            model=self.llm.model,
            provider=self.llm.provider,
            temperature=self.llm.settings.agent_temperature,
            max_tokens=self.llm.settings.agent_max_tokens,
            llm_call_sink=lambda call: llm_calls.append(call),
            step_name="interactive_player",
            max_tool_result_chars=DEFAULT_MAX_TOOL_RESULT_CHARS,
            max_total_tool_result_chars=DEFAULT_MAX_TOTAL_TOOL_RESULT_CHARS,
            extra_request_body=self.llm._extra_body(),
        )
        final_text, calls, events = loop.complete(
            prompt_text,
            tools=self.tool_definitions,
            tool_map=self.tool_map,
            system=system_prompt,
            max_tool_rounds=self.max_tool_rounds,
            tool_choice=self.tool_choice,
        )
        llm_calls.extend(calls)
        tool_events.extend(events)
        budget_used = sum(ev.latency_ms for ev in tool_events)

        steps_path = playthrough_path
        steps_path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "step_id": str(uuid.uuid4()),
                        "week": 0,
                        "final_text": final_text[:2000],
                        "tool_events": [ev.model_dump(mode="json") for ev in tool_events],
                    },
                    ensure_ascii=False,
                )
            )
            + "\n",
            encoding="utf-8",
        )

        # Persist a stub final state so other agents can chain on it.
        final_state_guess = {
            "week": self.max_weeks,
            "final_ending": "(see playthrough.jsonl)",
        }
        run_report = AgentRunReport(
            agent=self.name,
            started_at=datetime.now(tz=UTC),
            completed_at=datetime.now(tz=UTC),
            output_files=["playthrough.jsonl", "playthrough_summary.md"],
            llm_calls=llm_calls,
            tool_events=tool_events,
            budget_usage=loop.last_budget_usage,
        )
        summary_text = (
            "# Interactive Player Summary\n\n"
            "## Decision Log\n\n"
            f"- Tool rounds consumed: **{len(tool_events)}**\n"
            f"- LLM calls emitted: **{len(llm_calls)}**\n"
            f"- Total tool-event latency: **{budget_used} ms**\n\n"
            "## Final Output (truncated)\n\n"
            "```text\n"
            + final_text[:1500]
            + "\n```\n"
        )
        summary_path = report_dir / "playthrough_summary.md"
        summary_path.write_text(summary_text, encoding="utf-8")
        result = InteractivePlayerResult(
            report=run_report,
            steps=steps,
            final_state=final_state_guess,
            final_ending="(interactive play did not terminate cleanly)",
        )
        return result, [steps_path, summary_path]

    def _opening_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        template = (self.prompts_root / f"{self.name}_user.md").read_text(
            encoding="utf-8"
        )
        return template.format(
            max_weeks=self.max_weeks,
            report_dir=str(report_dir),
            **(context or {}),
        )


__all__ = [
    "AgentOutput",
    "InteractivePlayerAgent",
    "InteractivePlayerResult",
    "PlaythroughStep",
]
