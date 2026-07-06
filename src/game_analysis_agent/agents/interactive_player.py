"""Interactive player agent: drives the LLM through the Godot game via
``game_analysis_agent.game_tools`` tool calling.

The agent runs an *explicit* weekly loop on the Python side: each week
Python pulls the current state and the available action catalog, asks
the LLM for a single decision (one LLM call per week), forwards it to
``InteractiveProbe.step()``, and records the result. This is a strict
improvement over the v0.2 single-shot tool-loop approach because:

* local Qwen / SGLang models often forget the week counter inside a
  long tool-loop conversation;
* explicit looping makes ``playthrough.jsonl`` deterministic, which
  is necessary for the before/after regression comparison;
* the LLM is only asked to *decide* (1 JSON output per week) instead
  of *navigate* the whole tool protocol — much smaller per-call cost.

Outputs:

* ``playthrough.jsonl`` — one row per week (``state_before``, ``decision``,
  ``result``, ``state_after``, ``anomalies``).
* ``playthrough_summary.md`` — narrative postmortem + per-axis weekly
  table + top anomalies.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent, AgentOutput, AgentRunResult
from game_analysis_agent.game_tools import InteractiveProbe
from game_analysis_agent.llm_client import LocalLLMClient
from game_analysis_agent.schemas import (
    AgentRunReport,
    LLMCall,
    ToolExecutionEvent,
)
from game_analysis_agent.settings import Settings
from game_analysis_agent.tool_loop import parse_model_response_to_tool_calls


# Persona catalogue. The agent picks one and tailors its prompts around
# the persona's play style. Keys map to the *persona* argument on the CLI.
PERSONAS: dict[str, dict[str, str]] = {
    "newbie": {
        "playstyle": "新手玩家，只看 UI 提示随便玩，优先 follow 教程",
        "preferred_groups": "study, food, recovery",
    },
    "study": {
        "playstyle": "学霸玩家，优先学业 / TestDaF / APS，刻意压低社交",
        "preferred_groups": "study, admin, food",
    },
    "money": {
        "playstyle": "打工玩家，优先赚钱，愿意承担工时风险",
        "preferred_groups": "work, food, study",
    },
    "social": {
        "playstyle": "社牛玩家，优先社交 / 派对 / 关系网",
        "preferred_groups": "social, food, recovery",
    },
    "visa": {
        "playstyle": "行政控玩家，优先注册 / 签证 / 保险",
        "preferred_groups": "admin, study, recovery",
    },
    "slacker": {
        "playstyle": "摆烂玩家，优先休息 / 娱乐 / 短视频",
        "preferred_groups": "recovery, escape, social",
    },
}


@dataclass
class PlaythroughStep:
    week: int
    state_before: dict[str, Any]
    decision: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    state_after: dict[str, Any] = field(default_factory=dict)
    triggered_event_id: str = ""
    event_choice_id: str = ""
    available_actions: list[str] = field(default_factory=list)
    chosen_actions: list[str] = field(default_factory=list)
    llm_summary: str = ""
    anomalies: list[dict[str, Any]] = field(default_factory=list)


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
        persona: str = "newbie",
        difficulty: str = "normal",
        seed: int = 42,
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
        self.persona = persona if persona in PERSONAS else "newbie"
        self.difficulty = difficulty
        self.seed = seed

    def run(
        self,
        report_dir: Path,
        context: dict[str, Any] | None = None,
    ) -> AgentRunResult:  # type: ignore[override]
        """Override :meth:`Agent.run` so the weekly loop owns the LLM calls.

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

    # ---- abstract method implementations (carry signatures; unused) ----

    def build_user_prompt(  # noqa: D401
        self, report_dir: Path, context: dict[str, Any]
    ) -> str:
        """Required by the abstract base class; not used by ``play_through``."""
        return ""

    # -- actual gameplay ---------------------------------------------------

    def play_through(
        self,
        report_dir: Path,
        *,
        playthrough_path: Path | None = None,
        probe: InteractiveProbe | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[InteractivePlayerResult, list[Path]]:
        """Run a single playthrough using an explicit Python-side weekly loop.

        ``probe`` may be supplied by tests; in production it is built by
        the CLI via :func:`game_tools.build_probe`.
        """
        context = context or {}
        report_dir.mkdir(parents=True, exist_ok=True)
        playthrough_path = playthrough_path or report_dir / "playthrough.jsonl"

        # The InteractiveProbe is the canonical owner of the Godot
        # connection. Tests inject their own; production code uses the
        # CLI-built probe which shells out to ``RunInteractiveProbe.gd``.
        if probe is None:
            from game_analysis_agent.game_tools import build_probe

            probe = build_probe(self.settings) if self.settings is not None else None
            if probe is None:
                raise RuntimeError(
                    "InteractivePlayerAgent.play_through requires a probe "
                    "or settings configured with game_project_path."
                )

        system_prompt = self._build_system_prompt()
        persona = PERSONAS[self.persona]
        llm_calls: list[LLMCall] = []
        steps: list[PlaythroughStep] = []
        truncated = False

        for week in range(1, self.max_weeks + 1):
            if probe.finished:
                break

            state_before = probe.get_state()
            catalog = probe.list_available_actions()
            available_action_ids = _extract_action_ids(catalog)

            decision, call = self._decide_one_week(
                week=week,
                state=state_before,
                available_action_ids=available_action_ids,
                persona=persona,
                system_prompt=system_prompt,
                probe=probe,
            )
            if call is not None:
                llm_calls.append(call)

            if not decision["actions"]:
                # Model failed to produce a usable action; fall back to a
                # no-op safe pick to keep the loop alive.
                decision["actions"] = [available_action_ids[0]] if available_action_ids else ["rest_at_home"]

            result = probe.step(
                actions=decision["actions"],
                event_choice_id=decision.get("event_choice_id", ""),
            )

            anomalies = [a.model_dump(mode="json") for a in probe.detect_anomalies()]
            state_after = result.get("state", {}) if isinstance(result, dict) else {}

            step = PlaythroughStep(
                week=week,
                state_before=state_before,
                decision=decision,
                result=result,
                state_after=state_after,
                triggered_event_id=result.get("triggered_event_id", ""),
                event_choice_id=decision.get("event_choice_id", "") or "",
                available_actions=available_action_ids,
                chosen_actions=decision["actions"],
                llm_summary=decision.get("rationale", ""),
                anomalies=anomalies,
            )
            steps.append(step)
            self._append_step_jsonl(playthrough_path, step)

            if result.get("finished"):
                break
        else:
            truncated = True

        # Always invoke finish() so the probe writes a final ending. If we
        # already terminated mid-loop this is a no-op for Godot state.
        final = probe.finish()
        final_state = final.get("final_state") or probe.state or {}
        final_ending = final.get("final_ending") or probe.final_ending or "unknown"
        if truncated:
            final_ending = final_ending or "(truncated, max_weeks reached without finish call)"

        run_report = AgentRunReport(
            agent=self.name,
            started_at=datetime.now(tz=UTC),
            completed_at=datetime.now(tz=UTC),
            output_files=["playthrough.jsonl", "playthrough_summary.md"],
            llm_calls=llm_calls,
            tool_events=[],
            budget_usage=None,
        )

        summary_path = report_dir / "playthrough_summary.md"
        summary_path.write_text(
            self._render_summary(steps, final_state, final_ending, truncated),
            encoding="utf-8",
        )

        result = InteractivePlayerResult(
            report=run_report,
            steps=steps,
            final_state=final_state,
            final_ending=final_ending,
        )
        return result, [playthrough_path, summary_path]

    # -- helpers ----------------------------------------------------------

    def _build_system_prompt(self) -> str:
        # The prompt file is named ``player_*.md`` (legacy), not
        # ``interactive_player_*.md``.
        system_template = (self.prompts_root / "player_system.md").read_text(
            encoding="utf-8"
        )
        persona_block = self._persona_block()
        return f"{system_template}\n\n{persona_block}"

    def _persona_block(self) -> str:
        persona = PERSONAS[self.persona]
        return (
            "## Persona\n\n"
            f"- slug: `{self.persona}`\n"
            f"- playstyle: {persona['playstyle']}\n"
            f"- preferred action groups: {persona['preferred_groups']}\n"
            f"- difficulty: {self.difficulty}\n"
            f"- seed: {self.seed}\n"
        )

    def _decide_one_week(
        self,
        *,
        week: int,
        state: dict[str, Any],
        available_action_ids: list[str],
        persona: dict[str, str],
        system_prompt: str,
        probe: InteractiveProbe,
    ) -> tuple[dict[str, Any], LLMCall | None]:
        user_prompt = self._build_user_prompt(week, state, available_action_ids, probe)
        try:
            content, call = self.llm.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                agent=self.name,
                step_name=f"week-{week}",
                temperature=self.temperature,
            )
        except Exception as exc:
            return (
                {"actions": [], "event_choice_id": "", "rationale": f"error: {exc}"},
                None,
            )
        return _parse_decision(content, week, available_action_ids), call

    def _build_user_prompt(
        self,
        week: int,
        state: dict[str, Any],
        available_action_ids: list[str],
        probe: InteractiveProbe,
    ) -> str:
        recent_event = probe.last_event_id or "(none)"
        event_choices = probe.last_event_choices or []
        lines = [
            f"## Week {week} / {self.max_weeks}",
            "",
            "Current state:",
            "```json",
            json.dumps(state.get("state") or {}, ensure_ascii=False, indent=2)[:3500],
            "```",
            "",
            "Available action ids (pick 1–4 from this list, in order):",
            "```json",
            json.dumps(available_action_ids[:80], ensure_ascii=False),
            "```",
            "",
            f"Last triggered event: `{recent_event}`",
        ]
        if event_choices:
            lines.extend(
                [
                    "Event choices:",
                    "```json",
                    json.dumps(
                        [
                            {"index": idx, "choice": c}
                            for idx, c in enumerate(event_choices[:6])
                        ],
                        ensure_ascii=False,
                    ),
                    "```",
                ]
            )
        lines.extend(
            [
                "",
                "Respond with **JSON only**, no prose, in this exact shape:",
                "```json",
                json.dumps(
                    {
                        "actions": [available_action_ids[0]] if available_action_ids else ["rest_at_home"],
                        "event_choice_id": "",
                        "rationale": "short reason in 中文",
                    },
                    ensure_ascii=False,
                ),
                "```",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _append_step_jsonl(path: Path, step: PlaythroughStep) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "step_id": str(uuid.uuid4()),
                        "week": step.week,
                        "state_before": step.state_before,
                        "decision": step.decision,
                        "result": step.result,
                        "state_after": step.state_after,
                        "triggered_event_id": step.triggered_event_id,
                        "event_choice_id": step.event_choice_id,
                        "available_actions": step.available_actions,
                        "chosen_actions": step.chosen_actions,
                        "llm_summary": step.llm_summary,
                        "anomalies": step.anomalies,
                    },
                    ensure_ascii=False,
                )
            )
            handle.write("\n")

    @staticmethod
    def _render_summary(
        steps: list[PlaythroughStep],
        final_state: dict[str, Any],
        final_ending: str,
        truncated: bool,
    ) -> str:
        lines = ["# Interactive Player Summary", ""]
        lines.append("## Overview\n")
        lines.append(f"- weeks played: **{len(steps)}**")
        lines.append(f"- final ending: **{final_ending}**")
        lines.append(f"- truncated at max_weeks: **{truncated}**")
        lines.append("")

        if final_state:
            lines.append("## Final State\n")
            lines.append("```json")
            lines.append(json.dumps(final_state, ensure_ascii=False, indent=2)[:3500])
            lines.append("```")
            lines.append("")

        if steps:
            lines.append("## Weekly Decisions\n")
            lines.append("| week | actions | event | anomalies |")
            lines.append("| --- | --- | --- | --- |")
            for step in steps:
                actions = ", ".join(step.chosen_actions) or "—"
                event = step.triggered_event_id or "—"
                anomaly_count = len(step.anomalies)
                lines.append(
                    f"| {step.week} | {actions} | {event} | {anomaly_count} |"
                )
            lines.append("")

            all_anomalies = [
                (step.week, anomaly)
                for step in steps
                for anomaly in step.anomalies
            ]
            if all_anomalies:
                lines.append("## Anomalies Triggered\n")
                lines.append("| week | kind | severity | message |")
                lines.append("| --- | --- | --- | --- |")
                for week, anomaly in all_anomalies[:30]:
                    lines.append(
                        f"| {week} | `{anomaly.get('kind', '')}` | "
                        f"{anomaly.get('severity', '')} | "
                        f"{anomaly.get('message', '')} |"
                    )
                lines.append("")

        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Pure helpers (kept module-private so the tests can import them directly).
# ---------------------------------------------------------------------------


def _extract_action_ids(catalog: dict[str, Any]) -> list[str]:
    if not isinstance(catalog, dict):
        return []
    actions = catalog.get("actions")
    if isinstance(actions, list):
        ids: list[str] = []
        for entry in actions:
            if isinstance(entry, dict):
                action_id = entry.get("id")
                if isinstance(action_id, str):
                    ids.append(action_id)
            elif isinstance(entry, str):
                ids.append(entry)
        return ids
    return []


_DECISION_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_DECISION_BRACES = re.compile(r"(\{.*\})", re.DOTALL)


def _parse_decision(
    content: str,
    week: int,
    available_action_ids: list[str],
) -> dict[str, Any]:
    """Extract the JSON decision block from the LLM response.

    Returns ``{"actions": [...], "event_choice_id": ..., "rationale": ...}``.
    Falls back to a safe default when parsing fails so the loop can keep
    advancing.
    """
    fallback = {
        "actions": [available_action_ids[0]] if available_action_ids else ["rest_at_home"],
        "event_choice_id": "",
        "rationale": "fallback default action",
    }

    if not content:
        return fallback

    text = content.strip()
    parsed: dict[str, Any] | None = None
    fence_match = _DECISION_FENCE.search(text)
    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            parsed = None
    if parsed is None:
        # T02 fallback path: the model may already speak the JSON tool-call
        # protocol, in which case `parse_model_response_to_tool_calls` will
        # return ``step(...)`` with the actions list inside arguments.
        fallback_calls = parse_model_response_to_tool_calls(text, round_index=week)
        if fallback_calls:
            for call in fallback_calls:
                if call["function"]["name"] == "step":
                    try:
                        arguments = json.loads(call["function"]["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}
                    return {
                        "actions": list(arguments.get("actions") or []),
                        "event_choice_id": str(arguments.get("event_choice_id") or ""),
                        "rationale": "json-fallback tool_call",
                    }
        # Final attempt: take the first {...} block.
        brace_match = _DECISION_BRACES.search(text)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group(1))
            except json.JSONDecodeError:
                parsed = None
    if parsed is None:
        return fallback

    actions = parsed.get("actions")
    if not isinstance(actions, list):
        return fallback
    cleaned = [str(a) for a in actions if isinstance(a, (str, int))]
    if not cleaned:
        return fallback
    if available_action_ids:
        cleaned = [a for a in cleaned if a in available_action_ids] or [available_action_ids[0]]
    return {
        "actions": cleaned,
        "event_choice_id": str(parsed.get("event_choice_id") or ""),
        "rationale": str(parsed.get("rationale") or ""),
    }


__all__ = [
    "AgentOutput",
    "InteractivePlayerAgent",
    "InteractivePlayerResult",
    "PERSONAS",
    "PlaythroughStep",
    "_extract_action_ids",
    "_parse_decision",
]