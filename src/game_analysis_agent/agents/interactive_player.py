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

import yaml
from pydantic import ValidationError

from game_analysis_agent.agents.base import Agent, AgentOutput, AgentRunResult
from game_analysis_agent.game_tools import InteractiveProbe
from game_analysis_agent.llm_client import LocalLLMClient
from game_analysis_agent.schemas import (
    AgentRunReport,
    ActionBrief,
    DecisionValidation,
    EventChoiceBrief,
    LLMCall,
    PlayerDecision,
    PlayMemory,
    RiskBrief,
    StateSummary,
    ToolExecutionEvent,
    WeekContext,
    WeekMemory,
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
    week_context: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    delta: dict[str, int] = field(default_factory=dict)
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
    decision_max_tokens = 768

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
        scenario: str = "default_first_semester",
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
        self.scenario = scenario
        self.seed = seed
        self.persona_strategy = load_player_personas(prompts_root.parent).get(
            self.persona, PERSONAS[self.persona]
        )

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
        llm_calls: list[LLMCall] = []
        steps: list[PlaythroughStep] = []
        memory = _initial_memory(self.persona, self.persona_strategy)
        truncated = False

        probe.seed = self.seed
        probe.difficulty = self.difficulty
        probe.scenario = self.scenario

        for week in range(1, self.max_weeks + 1):
            if probe.finished:
                break

            state_before = probe.get_state()
            catalog = probe.list_available_actions()
            context_pack = build_week_context(
                week=week,
                max_weeks=self.max_weeks,
                persona=self.persona,
                persona_strategy=self.persona_strategy,
                state_payload=state_before,
                action_catalog=catalog,
                event_choices=[],
                last_event_id=probe.last_event_id,
                memory=memory,
                difficulty=self.difficulty,
                scenario=self.scenario,
                seed=self.seed,
            )
            available_action_ids = [action.id for action in context_pack.available_actions]

            decision, validation, call = self._decide_one_week(
                week=week,
                context_pack=context_pack,
                system_prompt=system_prompt,
                probe=probe,
            )
            if call is not None:
                llm_calls.append(call)

            if not decision.actions:
                # Model failed to produce a usable action; fall back to a
                # no-op safe pick to keep the loop alive.
                decision.actions = [available_action_ids[0]] if available_action_ids else ["rest_at_home"]

            if hasattr(probe, "preview_step"):
                preview = probe.preview_step(decision.actions)
                preview_choices = preview.get("event_choices", []) if isinstance(preview, dict) else []
                if preview_choices:
                    event_context = build_week_context(
                        week=week,
                        max_weeks=self.max_weeks,
                        persona=self.persona,
                        persona_strategy=self.persona_strategy,
                        state_payload={"state": preview.get("state", {})},
                        action_catalog=catalog,
                        event_choices=preview_choices,
                        last_event_id=str(preview.get("triggered_event_id", "")),
                        memory=memory,
                        difficulty=self.difficulty,
                        scenario=self.scenario,
                        seed=self.seed,
                    )
                    event_decision, event_validation, event_call = self._decide_one_week(
                        week=week,
                        context_pack=event_context,
                        system_prompt=system_prompt,
                        probe=probe,
                    )
                    if event_call is not None:
                        llm_calls.append(event_call)
                    decision.event_choice_id = event_decision.event_choice_id
                    validation = DecisionValidation(
                        valid=validation.valid and event_validation.valid,
                        errors=[*validation.errors, *event_validation.errors],
                        repair_count=validation.repair_count + event_validation.repair_count,
                        fallback_used=validation.fallback_used or event_validation.fallback_used,
                    )

            result = probe.step(
                actions=decision.actions,
                event_choice_id=decision.event_choice_id,
            )

            anomalies = [a.model_dump(mode="json") for a in probe.detect_anomalies()]
            state_after = result.get("state", {}) if isinstance(result, dict) else {}
            delta = _state_delta(state_before.get("state") or {}, state_after)

            step = PlaythroughStep(
                week=week,
                state_before=state_before,
                decision=decision.model_dump(mode="json"),
                result=result,
                state_after=state_after,
                triggered_event_id=result.get("triggered_event_id", ""),
                event_choice_id=decision.event_choice_id or "",
                available_actions=available_action_ids,
                chosen_actions=decision.actions,
                week_context=context_pack.model_dump(mode="json"),
                validation=validation.model_dump(mode="json"),
                delta=delta,
                llm_summary=decision.strategic_goal,
                anomalies=anomalies,
            )
            steps.append(step)
            _append_step_jsonl(playthrough_path, step)
            memory = _update_memory(memory, step)

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
            _render_summary(steps, final_state, final_ending, truncated),
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
        strategy = self.persona_strategy
        return (
            "## Persona\n\n"
            f"- slug: `{self.persona}`\n"
            f"- playstyle: {strategy.get('description', persona['playstyle'])}\n"
            f"- priorities: {', '.join(strategy.get('priorities', []))}\n"
            f"- risk_tolerance: {strategy.get('risk_tolerance', 'unknown')}\n"
            f"- exploration: {strategy.get('exploration', 'unknown')}\n"
            f"- failure_intent: {strategy.get('failure_intent', False)}\n"
            f"- hard_avoid: {', '.join(strategy.get('hard_avoid', []))}\n"
            f"- difficulty: {self.difficulty}\n"
            f"- scenario: {self.scenario}\n"
            f"- seed: {self.seed}\n"
            "\n"
            "You must output JSON matching PlayerDecision. Use only action ids from "
            "WeekContext.available_actions. Explain strategic_goal, risk_awareness, "
            "expected_tradeoff, and confidence every week.\n"
            "For interactive playtests, do not output hidden reasoning, markdown, "
            "or prose. Return exactly one compact JSON object and stop.\n"
        )

    def _decide_one_week(
        self,
        *,
        week: int,
        context_pack: WeekContext,
        system_prompt: str,
        probe: InteractiveProbe,
    ) -> tuple[PlayerDecision, DecisionValidation, LLMCall | None]:
        user_prompt = self._build_user_prompt(context_pack)
        calls: list[LLMCall] = []
        errors: list[str] = []
        attempt_errors: list[str] = []
        for attempt in range(3):
            prompt = user_prompt if attempt == 0 else _repair_prompt(context_pack, errors)
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                content, call = self._chat_decision(
                    messages,
                    agent=self.name,
                    step_name=f"week-{week}" if attempt == 0 else f"week-{week}-repair-{attempt}",
                    temperature=self.temperature,
                )
                calls.append(call)
            except Exception as exc:
                errors = [f"LLM error: {exc}"]
                break
            decision, errors = _parse_player_decision(
                content,
                context_pack,
            )
            if not errors:
                return (
                    decision,
                    DecisionValidation(
                        valid=True,
                        errors=attempt_errors,
                        repair_count=attempt,
                    ),
                    call,
                )
            attempt_errors.extend(errors)
        fallback = _fallback_decision(context_pack, errors)
        return (
            fallback,
            DecisionValidation(
                valid=False,
                errors=errors,
                repair_count=max(0, len(calls) - 1),
                fallback_used=True,
            ),
            calls[-1] if calls else None,
        )

    def _chat_decision(
        self,
        messages: list[dict[str, str]],
        *,
        agent: str,
        step_name: str,
        temperature: float | None,
    ) -> tuple[str, LLMCall]:
        try:
            return self.llm.chat(
                messages,
                agent=agent,
                step_name=step_name,
                max_tokens=self.decision_max_tokens,
                temperature=temperature,
            )
        except TypeError as exc:
            if "max_tokens" not in str(exc):
                raise
            return self.llm.chat(
                messages,
                agent=agent,
                step_name=step_name,
                temperature=temperature,
            )

    def _build_user_prompt(self, context_pack: WeekContext) -> str:
        schema_hint = {
            "week": context_pack.state.week,
            "persona": self.persona,
            "strategic_goal": "本周选择服务于哪个长期目标，最多 160 字",
            "actions": [context_pack.available_actions[0].id]
            if context_pack.available_actions
            else ["rest_at_home"],
            "event_choice_id": "",
            "risk_awareness": ["本周注意到的主要风险"],
            "expected_tradeoff": "收益与代价，最多 240 字",
            "confidence": 0.7,
        }
        return "\n".join(
            [
                "/no_think",
                "",
                f"## Week {context_pack.state.week} / {self.max_weeks}",
                "",
                "WeekContext JSON:",
                "```json",
                context_pack.model_dump_json(indent=2),
                "```",
                "",
                "Respond with one raw JSON object only. Do not use markdown, prose, or code fences. "
                "Do not include analysis before or after the JSON. Keep every string concise. "
                "Match this exact PlayerDecision shape:",
                "```json",
                json.dumps(schema_hint, ensure_ascii=False, indent=2),
                "```",
            ]
        )


def load_player_personas(project_root: Path) -> dict[str, dict[str, Any]]:
    path = project_root / "config" / "player_personas.yaml"
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    personas = payload.get("personas", {}) if isinstance(payload, dict) else {}
    return personas if isinstance(personas, dict) else {}


def build_week_context(
    *,
    week: int,
    max_weeks: int,
    persona: str,
    persona_strategy: dict[str, Any],
    state_payload: dict[str, Any],
    action_catalog: dict[str, Any],
    event_choices: list[dict[str, Any]],
    last_event_id: str,
    memory: PlayMemory,
    difficulty: str,
    scenario: str,
    seed: int,
) -> WeekContext:
    state = _state_summary(state_payload.get("state") or {}, week=week)
    actions = [_action_brief(action) for action in (action_catalog.get("actions") or [])]
    choices = [
        _event_choice_brief(choice, last_event_id, index)
        for index, choice in enumerate(event_choices)
        if isinstance(choice, dict)
    ]
    return WeekContext(
        game_version=str((state_payload.get("state") or {}).get("content_version", "")),
        seed=seed,
        difficulty=difficulty,
        scenario=scenario,
        max_action_slots=4,
        persona=persona,
        persona_strategy=persona_strategy,
        state=state,
        top_risks=_risk_briefs(state, max_weeks=max_weeks),
        available_actions=actions[:80],
        current_event_id=last_event_id or "",
        event_choices=choices[:8],
        memory=memory,
    )


def _state_summary(raw_state: dict[str, Any], *, week: int) -> StateSummary:
    flags = raw_state.get("flags") if isinstance(raw_state.get("flags"), dict) else {}
    return StateSummary(
        week=int(raw_state.get("week", week) or week),
        money=int(raw_state.get("money", 0) or 0),
        blocked_account_balance=_optional_int(raw_state.get("blocked_account_balance")),
        energy=int(raw_state.get("energy", 0) or 0),
        stress=int(raw_state.get("stress", 0) or 0),
        hunger=int(raw_state.get("hunger", 0) or 0),
        loneliness=int(raw_state.get("loneliness", 0) or 0),
        academic_progress=int(raw_state.get("academic_progress", 0) or 0),
        exam_readiness=_optional_int(raw_state.get("exam_readiness")),
        language=int(raw_state.get("language", 0) or 0),
        social=int(raw_state.get("social", 0) or 0),
        visa_progress=int(raw_state.get("visa_progress", 0) or 0),
        career_progress=int(raw_state.get("career_progress", 0) or 0),
        gpa_score=_optional_int(raw_state.get("gpa_score")),
        annual_work_half_days=_optional_int(raw_state.get("annual_work_half_days")),
        university_tier=str(raw_state.get("university_tier", "")) or None,
        flags={str(key): bool(value) for key, value in flags.items()},
    )


def _action_brief(action: Any) -> ActionBrief:
    if not isinstance(action, dict):
        return ActionBrief(id=str(action))
    tags = [str(tag) for tag in action.get("tags", []) or []]
    return ActionBrief(
        id=str(action.get("id", "")),
        name=str(action.get("name", "")),
        description=str(action.get("description", ""))[:220],
        type=tags[0] if tags else "",
        cost={
            "energy": int(action.get("cost_energy", 0) or 0),
            "money": int(action.get("cost_money", 0) or 0),
            "slots": int(action.get("cost_slots", 1) or 1),
        },
        effects=_int_dict(action.get("effects", {})),
        requirements=action.get("requirements", {}) if isinstance(action.get("requirements"), dict) else {},
        tags=tags,
        risk_tags=[str(tag) for tag in action.get("risk_tags", []) or []],
        cooldown_group=str(action.get("cooldown_group", "")) or None,
        max_per_week=_optional_int(action.get("max_per_week")),
    )


def _event_choice_brief(choice: dict[str, Any], event_id: str, index: int) -> EventChoiceBrief:
    choice_id = str(choice.get("choice_id") or "")
    if not choice_id:
        safe_text = str(choice.get("text", "")).strip().lower().replace(" ", "_")
        choice_id = f"{event_id}.choice_{index + 1:02d}_{safe_text}" if event_id else f"choice_{index + 1:02d}"
    return EventChoiceBrief(
        choice_id=choice_id,
        text=str(choice.get("text", "")),
        success_rate=float(choice["success_rate"]) if "success_rate" in choice else None,
        requirements=choice.get("requirements", {}) if isinstance(choice.get("requirements"), dict) else {},
        success_effects=_int_dict(choice.get("success_effects", {})),
        failure_effects=_int_dict(choice.get("failure_effects", {})),
    )


def _risk_briefs(state: StateSummary, *, max_weeks: int) -> list[RiskBrief]:
    risks: list[RiskBrief] = []
    remaining = max_weeks - state.week
    school_registered = state.flags.get("school_registered", False)
    testdaf_passed = state.flags.get("testdaf_passed", False)
    if not school_registered and state.week <= 6:
        risks.append(
            RiskBrief(
                id="school_registration_deadline",
                severity="critical" if state.week >= 4 else "high",
                reason=(
                    "school_registration requires testdaf_passed and must be completed by week 6; "
                    f"testdaf_passed={testdaf_passed}"
                ),
                suggested_action_types=[
                    "testdaf_exam_germany",
                    "testdaf_prep",
                    "school_registration",
                ],
            )
        )
    if state.flags.get("registration_delayed", False) and not school_registered:
        risks.append(
            RiskBrief(
                id="registration_delayed",
                severity="critical",
                reason="registration window was missed; recover with next_semester_registration when available",
                suggested_action_types=["next_semester_registration", "international_office"],
            )
        )
    if state.money < 0:
        severity = "critical" if state.money < -1000 else "high"
        risks.append(
            RiskBrief(
                id="cashflow",
                severity=severity,
                reason=f"money={state.money}; debt can block survival endings",
                suggested_action_types=["work", "budget", "food"],
            )
        )
    if state.hunger >= 75:
        risks.append(
            RiskBrief(
                id="hunger",
                severity="critical" if state.hunger >= 90 else "high",
                reason=f"hunger={state.hunger}; survival state is degrading",
                suggested_action_types=["food", "recovery"],
            )
        )
    if state.stress >= 75:
        risks.append(
            RiskBrief(
                id="stress",
                severity="critical" if state.stress >= 90 else "high",
                reason=f"stress={state.stress}; burnout risk is high",
                suggested_action_types=["recovery", "social"],
            )
        )
    if remaining <= 8 and state.academic_progress < 45:
        risks.append(
            RiskBrief(
                id="academic_deadline",
                severity="high",
                reason=f"week={state.week}, academic_progress={state.academic_progress}",
                suggested_action_types=["study"],
            )
        )
    if state.week >= 8 and state.visa_progress < 45:
        risks.append(
            RiskBrief(
                id="visa_deadline",
                severity="high",
                reason=f"week={state.week}, visa_progress={state.visa_progress}",
                suggested_action_types=["admin"],
            )
        )
    return risks[:5]


def _parse_player_decision(content: str, context_pack: WeekContext) -> tuple[PlayerDecision, list[str]]:
    parsed = _extract_json_object(content)
    if isinstance(parsed, dict) and parsed.get("tool") == "step":
        arguments = parsed.get("arguments") if isinstance(parsed.get("arguments"), dict) else {}
        parsed = {
            "week": context_pack.state.week,
            "persona": context_pack.persona,
            "strategic_goal": "json fallback tool call",
            "actions": arguments.get("actions") or [],
            "event_choice_id": arguments.get("event_choice_id") or "",
            "risk_awareness": [],
            "expected_tradeoff": "model emitted step tool JSON",
            "confidence": 0.5,
        }
    if parsed is None:
        calls = parse_model_response_to_tool_calls(content, round_index=context_pack.state.week)
        for call in calls:
            if call["function"]["name"] == "step":
                try:
                    args = json.loads(call["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                parsed = {
                    "week": context_pack.state.week,
                    "persona": context_pack.persona,
                    "strategic_goal": "json fallback tool call",
                    "actions": args.get("actions") or [],
                    "event_choice_id": args.get("event_choice_id") or "",
                    "risk_awareness": [],
                    "expected_tradeoff": "model emitted step tool JSON",
                    "confidence": 0.5,
                }
                break
    if parsed is None:
        return _fallback_decision(context_pack, ["No JSON object found"]), ["No JSON object found"]
    if "rationale" in parsed and "strategic_goal" not in parsed:
        parsed["strategic_goal"] = str(parsed.get("rationale", ""))
    parsed.pop("rationale", None)
    parsed = _normalize_decision_payload(parsed, context_pack)
    parsed.setdefault("week", context_pack.state.week)
    parsed.setdefault("persona", context_pack.persona)
    parsed.setdefault("risk_awareness", [])
    parsed.setdefault("expected_tradeoff", parsed.get("strategic_goal", ""))
    parsed.setdefault("confidence", 0.5)
    try:
        decision = PlayerDecision.model_validate(parsed)
    except ValidationError as exc:
        return _fallback_decision(context_pack, [str(exc)]), [str(exc)]
    errors = _validate_decision(decision, context_pack)
    return decision, errors


def _validate_decision(decision: PlayerDecision, context_pack: WeekContext) -> list[str]:
    errors: list[str] = []
    valid_actions = {action.id for action in context_pack.available_actions}
    for action_id in decision.actions:
        if action_id not in valid_actions:
            errors.append(f"Unknown action_id: {action_id}")
    if len(decision.actions) > context_pack.max_action_slots:
        errors.append(f"Too many actions: {len(decision.actions)}")
    if context_pack.event_choices and not decision.event_choice_id:
        errors.append("Missing event_choice_id")
    if context_pack.event_choices and decision.event_choice_id:
        valid_choices = {choice.choice_id for choice in context_pack.event_choices}
        if decision.event_choice_id not in valid_choices:
            errors.append(f"Invalid event_choice_id: {decision.event_choice_id}")
    if not decision.strategic_goal.strip():
        errors.append("Missing strategic_goal")
    if not decision.expected_tradeoff.strip():
        errors.append("Missing expected_tradeoff")
    return errors


def _repair_prompt(context_pack: WeekContext, errors: list[str]) -> str:
    valid_choices = [choice.choice_id for choice in context_pack.event_choices]
    return "\n".join(
        [
            "Your previous PlayerDecision JSON was invalid.",
            "Errors:",
            json.dumps(errors, ensure_ascii=False, indent=2),
            "",
            "Repair it using only these action ids:",
            json.dumps([action.id for action in context_pack.available_actions], ensure_ascii=False),
            "",
            "Valid event_choice_id values:",
            json.dumps(valid_choices, ensure_ascii=False),
            "",
            "Return JSON only with week, persona, strategic_goal, actions, event_choice_id, "
            "risk_awareness, expected_tradeoff, confidence.",
        ]
    )


def _fallback_decision(context_pack: WeekContext, errors: list[str]) -> PlayerDecision:
    action_id = _best_fallback_action(context_pack)
    event_choice_id = context_pack.event_choices[0].choice_id if context_pack.event_choices else ""
    return PlayerDecision(
        week=context_pack.state.week,
        persona=context_pack.persona,
        strategic_goal="deterministic fallback after invalid LLM decision",
        actions=[action_id] if action_id else ["rest_at_home"],
        event_choice_id=event_choice_id,
        risk_awareness=errors[:3],
        expected_tradeoff="fallback keeps the playthrough reproducible",
        confidence=0.0,
    )


def _best_fallback_action(context_pack: WeekContext) -> str:
    priorities = context_pack.persona_strategy.get("priorities", [])
    for priority in priorities:
        for action in context_pack.available_actions:
            haystack = " ".join([action.type, *action.tags, *action.risk_tags, action.id])
            if str(priority).split("_")[0] in haystack:
                return action.id
    if context_pack.available_actions:
        return context_pack.available_actions[0].id
    return "rest_at_home"


def _extract_json_object(content: str) -> dict[str, Any] | None:
    if not content:
        return None
    text = content.strip()
    fence_match = _DECISION_FENCE.search(text)
    candidates = [fence_match.group(1)] if fence_match else []
    brace_match = _DECISION_BRACES.search(text)
    if brace_match:
        candidates.append(brace_match.group(1))
    candidates.append(text)
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _normalize_decision_payload(
    parsed: dict[str, Any],
    context_pack: WeekContext,
) -> dict[str, Any]:
    normalized = dict(parsed)
    valid_actions = {action.id for action in context_pack.available_actions}
    if isinstance(normalized.get("event_choice_id"), list):
        values = normalized.get("event_choice_id") or []
        normalized["event_choice_id"] = str(values[0]) if values else ""
    if normalized.get("event_choice_id") is None:
        normalized["event_choice_id"] = ""
    if not context_pack.event_choices:
        normalized["event_choice_id"] = ""
    if not isinstance(normalized.get("risk_awareness"), list):
        value = normalized.get("risk_awareness")
        normalized["risk_awareness"] = [] if value in (None, "") else [str(value)]
    normalized["risk_awareness"] = [str(item)[:120] for item in normalized["risk_awareness"][:5]]
    if not isinstance(normalized.get("actions"), list):
        value = normalized.get("actions")
        normalized["actions"] = [str(value)] if value not in (None, "") else []
    cleaned_actions: list[str] = []
    for item in normalized["actions"]:
        action_id = str(item).strip()
        if action_id and action_id in valid_actions and action_id not in cleaned_actions:
            cleaned_actions.append(action_id)
        if len(cleaned_actions) >= context_pack.max_action_slots:
            break
    normalized["actions"] = cleaned_actions or [_best_fallback_action(context_pack)]
    if not isinstance(normalized.get("confidence"), (int, float)):
        normalized["confidence"] = 0.5
    normalized["confidence"] = max(0.0, min(1.0, float(normalized["confidence"])))
    strategic_goal = str(normalized.get("strategic_goal", "")).strip()
    expected_tradeoff = str(normalized.get("expected_tradeoff", "")).strip()
    normalized["strategic_goal"] = strategic_goal[:160]
    normalized["expected_tradeoff"] = (expected_tradeoff or strategic_goal)[:240]
    normalized["week"] = context_pack.state.week
    normalized["persona"] = context_pack.persona
    return normalized

def _append_step_jsonl(path: Path, step: PlaythroughStep) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "step_id": str(uuid.uuid4()),
                    "week": step.week,
                    "week_context": step.week_context,
                    "state_before": step.state_before,
                    "decision": step.decision,
                    "validation": step.validation,
                    "result": step.result,
                    "state_after": step.state_after,
                    "delta": step.delta,
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
        lines.append("| week | actions | goal | event | valid | anomalies |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for step in steps:
            actions = ", ".join(step.chosen_actions) or "-"
            event = step.triggered_event_id or "-"
            goal = str(step.decision.get("strategic_goal", ""))[:80]
            valid = str(step.validation.get("valid", ""))
            anomaly_count = len(step.anomalies)
            lines.append(
                f"| {step.week} | {actions} | {goal} | {event} | {valid} | {anomaly_count} |"
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


def _initial_memory(persona: str, strategy: dict[str, Any]) -> PlayMemory:
    priorities = strategy.get("priorities", [])
    return PlayMemory(
        persona=persona,
        route_commitment=", ".join(str(item) for item in priorities[:3]),
        long_term_goal=str(strategy.get("description", "")),
    )


def _update_memory(memory: PlayMemory, step: PlaythroughStep) -> PlayMemory:
    repeated = dict(memory.repeated_actions)
    for action_id in step.chosen_actions:
        repeated[action_id] = repeated.get(action_id, 0) + 1
    week_memory = WeekMemory(
        week=step.week,
        actions=step.chosen_actions,
        event=step.triggered_event_id,
        rationale=str(step.decision.get("strategic_goal", "")),
        delta=step.delta,
    )
    state = step.state_after or {}
    flags = state.get("flags") if isinstance(state.get("flags"), dict) else {}
    unresolved = list(memory.unresolved_risks)
    if int(state.get("money", 0) or 0) < 0 and "cashflow" not in unresolved:
        unresolved.append("cashflow")
    if int(state.get("stress", 0) or 0) >= 75 and "stress" not in unresolved:
        unresolved.append("stress")
    if int(state.get("hunger", 0) or 0) >= 75 and "hunger" not in unresolved:
        unresolved.append("hunger")
    return memory.model_copy(
        update={
            "important_flags": {str(key): bool(value) for key, value in flags.items()},
            "repeated_actions": repeated,
            "unresolved_risks": unresolved[-8:],
            "last_5_weeks": [*memory.last_5_weeks, week_memory][-5:],
        }
    )


def _state_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, int]:
    keys = [
        "money",
        "energy",
        "stress",
        "hunger",
        "loneliness",
        "academic_progress",
        "exam_readiness",
        "language",
        "social",
        "visa_progress",
        "career_progress",
    ]
    delta: dict[str, int] = {}
    for key in keys:
        if isinstance(before.get(key), (int, float)) and isinstance(after.get(key), (int, float)):
            value = int(after[key]) - int(before[key])
            if value != 0:
                delta[key] = value
    return delta


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_dict(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, item in value.items():
        if isinstance(item, (int, float)):
            out[str(key)] = int(item)
    return out


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
    """Legacy parser kept for existing tests and compatibility."""
    fallback = {
        "actions": [available_action_ids[0]] if available_action_ids else ["rest_at_home"],
        "event_choice_id": "",
        "rationale": "fallback default action",
    }
    if not content:
        return fallback
    parsed = _extract_json_object(content)
    if parsed is None:
        fallback_calls = parse_model_response_to_tool_calls(content, round_index=week)
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
        "rationale": str(parsed.get("rationale") or parsed.get("strategic_goal") or ""),
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
