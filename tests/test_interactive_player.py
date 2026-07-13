"""Tests for the explicit weekly loop in ``InteractivePlayerAgent`` (T05)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from game_analysis_agent.agents.interactive_player import (
    PERSONAS,
    InteractivePlayerAgent,
    _extract_action_ids,
    _parse_decision,
    build_week_context,
)
from game_analysis_agent.game_tools import InteractiveProbe
from game_analysis_agent.schemas import LLMCall, PlayMemory
from game_analysis_agent.settings import Settings


def _fake_settings() -> Settings:
    return Settings()


def _fake_llm_call(content: str = "") -> LLMCall:
    return LLMCall(
        call_id="llm-fake",
        agent="interactive_player",
        step_name="week-1",
        provider="vllm",
        model="fake",
        prompt_text="",
        response_text=content,
        latency_ms=1,
        started_at=datetime.now(tz=timezone.utc),
        completed_at=datetime.now(tz=timezone.utc),
    )


class _FakeLLM:
    def __init__(self, contents: list[str], settings: Settings) -> None:
        self.contents = list(contents)
        self.settings = settings
        self.calls: list[LLMCall] = []

    def chat(self, messages, *, agent, step_name, temperature=None):  # noqa: ANN001
        content = self.contents.pop(0) if self.contents else ""
        call = _fake_llm_call(content)
        self.calls.append(call)
        return content, call


class _FakeProbe:
    """In-memory InteractiveProbe replacement that doesn't shell out to Godot."""

    def __init__(self, max_weeks: int = 5, *, finish_at: int | None = None) -> None:
        self.max_weeks = max_weeks
        self.current_week = 0
        self.state = {
            "money": 1000,
            "stress": 30,
            "academic_progress": 50,
            "visa_progress": 50,
            "social": 30,
            "hunger": 20,
        }
        self.last_event_id = ""
        self.last_event_choices: list[dict[str, Any]] = []
        self.finished = False
        self.final_ending: str | None = None
        self.history: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self._finish_at = finish_at

    # -- tool implementations ---------------------------------------------

    def get_state(self) -> dict[str, Any]:
        return {
            "week": self.current_week,
            "state": self.state,
            "finished": self.finished,
            "last_event_id": self.last_event_id,
        }

    def list_available_actions(self) -> dict[str, Any]:
        return {
            "actions": [
                {"id": "study_library", "name": "Study"},
                {"id": "sleep_recover", "name": "Sleep"},
                {"id": "mini_job", "name": "Mini Job"},
                {"id": "rest_at_home", "name": "Rest"},
            ]
        }

    def step(self, *, actions: list[str], event_choice_id: str = "") -> dict[str, Any]:
        self.current_week += 1
        self.calls.append({"actions": list(actions), "event_choice_id": event_choice_id})
        if actions:
            action = actions[0]
            if action == "study_library":
                self.state["academic_progress"] += 5
            elif action == "sleep_recover":
                self.state["stress"] = max(0.0, self.state["stress"] - 8)
            elif action == "mini_job":
                self.state["money"] += 50
        if self._finish_at is not None and self.current_week >= self._finish_at:
            self.finished = True
            self.final_ending = "academic_success"
        return {
            "week": self.current_week,
            "state": dict(self.state),
            "triggered_event_id": "",
            "event_choices": [],
            "finished": self.finished,
        }

    def finish(self) -> dict[str, Any]:
        self.finished = True
        if self.final_ending is None:
            self.final_ending = "max_weeks_reached"
        return {
            "finished": True,
            "final_state": dict(self.state),
            "final_ending": self.final_ending,
        }

    def detect_anomalies(self):  # noqa: D401
        return []


def _build_agent(llm_contents: list[str], probe: _FakeProbe) -> InteractivePlayerAgent:
    settings = _fake_settings()
    llm = _FakeLLM(llm_contents, settings)
    agent = InteractivePlayerAgent(
        llm=llm,  # type: ignore[arg-type]
        prompts_root=Path(__file__).parent.parent / "prompts",
        settings=settings,
        tool_definitions=[],
        tool_map={},
        max_weeks=5,
        persona="study",
        difficulty="normal",
        seed=42,
    )
    # Inject our probe (bypass build_probe).
    agent._test_probe = probe  # type: ignore[attr-defined]
    return agent


def _context_for_risk_payload(state_payload: dict[str, Any]):
    return build_week_context(
        week=3,
        max_weeks=20,
        persona="study",
        persona_strategy={},
        state_payload=state_payload,
        action_catalog={"actions": []},
        event_choices=[],
        last_event_id="",
        memory=PlayMemory(persona="study"),
        difficulty="normal",
        scenario="default_first_semester",
        seed=42,
    )


def _canonical_risk_guidance() -> dict[str, Any]:
    return {
        "contract_version": "1.0",
        "source": "game_risk_evaluator",
        "evaluator": "RiskEvaluator.get_top_risks",
        "generated_for_week": 2,
        "top_risks": [
            {
                "id": "money",
                "title": "现金流",
                "score": 78,
                "body": "当前现金不足。",
                "suggested_actions": ["budget_call", "part_time_job"],
            }
        ],
    }


def test_week_context_prefers_canonical_game_ui_risks() -> None:
    context = _context_for_risk_payload(
        {
            "state": {"week": 2, "money": 100, "hunger": 95},
            "risk_guidance": _canonical_risk_guidance(),
        }
    )

    assert [risk.id for risk in context.top_risks] == ["money"]
    assert context.top_risks[0].severity == "high"
    assert context.top_risks[0].score == 78
    assert context.top_risks[0].suggested_action_ids == [
        "budget_call",
        "part_time_job",
    ]
    assert context.risk_guidance.source == "game_risk_evaluator"
    assert context.risk_guidance.evaluator == "RiskEvaluator.get_top_risks"
    assert context.risk_guidance.fallback_reason == ""


def test_week_context_marks_missing_invalid_and_stale_guidance_as_fallback() -> None:
    missing = _context_for_risk_payload({"state": {"week": 2, "money": 100, "hunger": 95}})
    assert missing.risk_guidance.source == "python_fallback"
    assert missing.risk_guidance.fallback_reason == "probe payload omitted risk_guidance"
    assert "hunger" in {risk.id for risk in missing.top_risks}

    invalid_guidance = _canonical_risk_guidance()
    invalid_guidance["top_risks"][0]["score"] = "78"
    invalid = _context_for_risk_payload(
        {
            "state": {"week": 2, "money": 100, "hunger": 95},
            "risk_guidance": invalid_guidance,
        }
    )
    assert invalid.risk_guidance.source == "python_fallback"
    assert "top_risks.0.score" in invalid.risk_guidance.fallback_reason

    stale_guidance = _canonical_risk_guidance()
    stale_guidance["generated_for_week"] = 1
    stale = _context_for_risk_payload(
        {
            "state": {"week": 2, "money": 100, "hunger": 95},
            "risk_guidance": stale_guidance,
        }
    )
    assert stale.risk_guidance.source == "python_fallback"
    assert "does not match probe state week=2" in stale.risk_guidance.fallback_reason


def test_play_through_runs_explicit_weekly_loop(tmp_path) -> None:
    probe = _FakeProbe()
    decisions = [
        json.dumps({"actions": ["study_library"], "event_choice_id": "", "rationale": "wk1"}),
        json.dumps({"actions": ["sleep_recover"], "event_choice_id": "", "rationale": "wk2"}),
        json.dumps({"actions": ["mini_job"], "event_choice_id": "", "rationale": "wk3"}),
        json.dumps({"actions": ["study_library"], "event_choice_id": "", "rationale": "wk4"}),
        json.dumps({"actions": ["study_library"], "event_choice_id": "", "rationale": "wk5"}),
    ]
    agent = _build_agent(decisions, probe)
    result, written = agent.play_through(tmp_path, probe=probe)  # type: ignore[arg-type]

    assert len(result.steps) == 5
    assert result.final_ending != "unknown"
    assert probe.current_week == 5

    summary_path = tmp_path / "playthrough_summary.md"
    jsonl_path = tmp_path / "playthrough.jsonl"
    agent_report_path = tmp_path / "playthrough_agent_report.json"
    assert summary_path.exists()
    assert jsonl_path.exists()
    assert agent_report_path.exists()
    summary = summary_path.read_text(encoding="utf-8")
    assert "## Weekly Decisions" in summary
    assert "weeks played: **5**" in summary
    assert "run id:" in summary

    rows = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 5
    assert rows[0]["run_id"] == tmp_path.name
    assert rows[0]["chosen_actions"] == ["study_library"]
    assert rows[1]["chosen_actions"] == ["sleep_recover"]


def test_play_through_terminates_when_probe_finishes(tmp_path) -> None:
    probe = _FakeProbe(finish_at=2)
    decisions = [
        json.dumps({"actions": ["study_library"], "event_choice_id": "", "rationale": "wk1"}),
        json.dumps({"actions": ["mini_job"], "event_choice_id": "", "rationale": "wk2"}),
        json.dumps({"actions": ["study_library"], "event_choice_id": "", "rationale": "unused"}),
    ]
    agent = _build_agent(decisions, probe)
    result, _written = agent.play_through(tmp_path, probe=probe)  # type: ignore[arg-type]
    assert len(result.steps) == 2
    assert probe.finished


def test_play_through_falls_back_to_first_action_when_decision_invalid(tmp_path) -> None:
    probe = _FakeProbe()
    agent = _build_agent(["not-json-at-all"] * 5, probe)
    result, _written = agent.play_through(tmp_path, probe=probe)  # type: ignore[arg-type]
    assert len(result.steps) == 5
    assert probe.calls[0]["actions"] == ["study_library"]
    # Three invalid attempts per week must all remain in the audit report.
    assert len(result.report.llm_calls) == 15


def test_play_through_handles_json_fallback_tool_call(tmp_path) -> None:
    """If the model emits the tool-call JSON instead of a decision block, the parser should pick it up via T02."""
    probe = _FakeProbe()
    fallback = json.dumps(
        {
            "tool": "step",
            "arguments": {"actions": ["mini_job"], "event_choice_id": ""},
        }
    )
    agent = _build_agent([fallback] * 5, probe)
    result, _ = agent.play_through(tmp_path, probe=probe)  # type: ignore[arg-type]
    assert probe.calls[0]["actions"] == ["mini_job"]


def test_parse_decision_filters_unknown_actions() -> None:
    cleaned = _parse_decision(
        json.dumps(
            {
                "actions": ["ghost_action", "study_library"],
                "event_choice_id": "",
                "rationale": "test",
            }
        ),
        week=1,
        available_action_ids=["study_library", "rest_at_home"],
    )
    assert cleaned["actions"] == ["study_library"]


def test_parse_decision_handles_garbage() -> None:
    out = _parse_decision("nothing useful here", week=1, available_action_ids=["study_library"])
    assert out["actions"] == ["study_library"]
    assert out["rationale"]


def test_extract_action_ids_handles_dict_and_string() -> None:
    assert _extract_action_ids({"actions": [{"id": "a"}, {"id": "b"}, "c"]}) == ["a", "b", "c"]
    assert _extract_action_ids({}) == []
    assert _extract_action_ids({"actions": "not a list"}) == []


def test_persona_lookup_is_exhaustive() -> None:
    for slug in ("newbie", "study", "money", "social", "visa", "slacker"):
        assert slug in PERSONAS


def test_real_probe_dataclass_compatibility() -> None:
    """The agent should accept the real InteractiveProbe too (no crash on access)."""
    real = InteractiveProbe(settings=_fake_settings())
    assert real.current_week == 0
    assert real.state is None
    # Just verify the surface area we'd rely on is present.
    for attr in ("get_state", "list_available_actions", "step", "finish", "detect_anomalies"):
        assert hasattr(real, attr)


def test_play_through_reusing_report_dir_replaces_old_trace(tmp_path) -> None:
    first_probe = _FakeProbe(finish_at=2)
    first = _build_agent(
        [
            json.dumps({"actions": ["study_library"], "event_choice_id": "", "rationale": "study"}),
            json.dumps({"actions": ["study_library"], "event_choice_id": "", "rationale": "study"}),
        ],
        first_probe,
    )
    first.play_through(tmp_path, probe=first_probe)  # type: ignore[arg-type]

    second_probe = _FakeProbe(finish_at=2)
    second = _build_agent(
        [
            json.dumps({"actions": ["mini_job"], "event_choice_id": "", "rationale": "work"}),
            json.dumps({"actions": ["mini_job"], "event_choice_id": "", "rationale": "work"}),
        ],
        second_probe,
    )
    second.play_through(tmp_path, probe=second_probe)  # type: ignore[arg-type]

    rows = [
        json.loads(line)
        for line in (tmp_path / "playthrough.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert rows[0]["chosen_actions"] == ["mini_job"]
