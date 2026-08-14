"""Frozen integration tests for Godot-authoritative persona plan repair."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

import game_analysis_agent.game_tools as game_tools
from game_analysis_agent.agents.interactive_player import (
    InteractivePlayerAgent,
    _authoritative_plan_error,
)
from game_analysis_agent.game_tools import InteractiveProbeStepError, build_probe
from game_analysis_agent.local_persona_gateway import LocalChatPersonaGateway
from game_analysis_agent.persona_gateway import (
    PersonaDecisionRequest,
    PersonaErrorCategory,
    PersonaResultStatus,
)
from game_analysis_agent.schemas import LLMCall, PlayerDecision, WeekContext
from game_analysis_agent.settings import Settings

CONFLICTING = [
    "cook_at_home",
    "cheap_noodle_week",
    "mensa_coupon",
    "go_running",
]
REPAIRED = ["cook_at_home", "go_running", "library_day", "budget_call"]


def _settings(tmp_path: Path | None = None) -> Settings:
    base = Settings()
    values = {
        **base.__dict__,
        "godot_bin": "/definitely/missing/godot-for-unit-test",
    }
    if tmp_path is not None:
        values["game_project_path"] = tmp_path
    return Settings(**values)


def _actions() -> list[dict]:
    return [
        {
            "id": "cook_at_home",
            "name": "Cook",
            "cost_slots": 1,
            "cost_money": 12,
            "cooldown_group": "meal",
            "max_per_week": 2,
        },
        {
            "id": "cheap_noodle_week",
            "name": "Noodles",
            "cost_slots": 1,
            "cost_money": 4,
            "cooldown_group": "meal",
            "max_per_week": 1,
        },
        {
            "id": "mensa_coupon",
            "name": "Mensa",
            "cost_slots": 1,
            "cost_money": 7,
            "cooldown_group": "meal",
            "max_per_week": 1,
        },
        {
            "id": "go_running",
            "name": "Run",
            "cost_slots": 1,
            "cost_money": 0,
            "cooldown_group": "exercise",
            "max_per_week": 1,
        },
        {
            "id": "library_day",
            "name": "Study",
            "cost_slots": 1,
            "cost_money": 0,
            "cooldown_group": "",
            "max_per_week": 0,
        },
        {
            "id": "budget_call",
            "name": "Budget",
            "cost_slots": 1,
            "cost_money": 0,
            "cooldown_group": "family_support",
            "max_per_week": 1,
        },
    ]


def _context() -> WeekContext:
    return WeekContext.model_validate(
        {
            "game_version": "focused",
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "max_action_slots": 4,
            "action_slot_policy": "exact_cost_sum",
            "persona": "money",
            "state": {"week": 1, "money": 1000, "hunger": 60},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
                "contract_version": "1.0",
            },
            "available_actions": [
                {
                    "id": action["id"],
                    "name": action["name"],
                    "cost": {
                        "slots": action["cost_slots"],
                        "money": action["cost_money"],
                    },
                    "cooldown_group": action["cooldown_group"] or None,
                    "max_per_week": action["max_per_week"],
                }
                for action in _actions()
            ],
            "memory": {"persona": "money"},
        }
    )


def _decision(actions: list[str]) -> PlayerDecision:
    return PlayerDecision(
        week=1,
        persona="money",
        strategic_goal="protect cashflow",
        actions=actions,
        expected_tradeoff="use the exact weekly plan budget",
        confidence=0.8,
    )


class _LocalLLM:
    provider = "vllm"
    model = "authoritative-focused-test"

    def __init__(self, contents: list[str]) -> None:
        self.settings = Settings()
        self.contents = list(contents)
        self.calls: list[list[dict]] = []

    def chat(self, messages, *, agent, step_name, max_tokens, temperature):  # noqa: ANN001
        del max_tokens, temperature
        self.calls.append(messages)
        content = self.contents.pop(0)
        return content, LLMCall(
            call_id=f"authoritative-{len(self.calls)}",
            agent=agent,
            step_name=step_name,
            provider=self.provider,
            model=self.model,
            prompt_text="",
            response_text=content,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=1,
        )


def _invalid_preview() -> dict:
    return {
        "valid": False,
        "error_code": "invalid_plan",
        "plan_validation": {
            "valid": False,
            "code": "invalid_plan",
            "used_slots": 2,
            "required_slots": 4,
            "selected_action_ids": ["cook_at_home", "go_running"],
        },
        "finished": False,
    }


def _valid_preview() -> dict:
    return {
        "valid": True,
        "error_code": "",
        "plan_validation": {
            "valid": True,
            "code": "",
            "used_slots": 4,
            "required_slots": 4,
            "selected_action_ids": REPAIRED,
        },
        "state": {"week": 1, "money": 1000, "hunger": 60},
        "triggered_event_id": "",
        "event_choices": [],
        "risk_guidance": {
            "contract_version": "1.0",
            "source": "game_risk_evaluator",
            "evaluator": "RiskEvaluator.get_top_risks",
            "generated_for_week": 1,
            "top_risks": [],
        },
        "finished": False,
    }


def test_local_gateway_uses_one_total_repair_for_authoritative_rejection() -> None:
    llm = _LocalLLM([_decision(CONFLICTING).model_dump_json(), _decision(REPAIRED).model_dump_json()])
    gateway = LocalChatPersonaGateway(llm)  # type: ignore[arg-type]
    request = PersonaDecisionRequest.from_context(_context(), request_id="money-42-w1")
    previews = [_invalid_preview(), _valid_preview()]

    def authoritative(decision: PlayerDecision) -> list[str]:
        preview = previews.pop(0)
        if preview["valid"]:
            return []
        validation = preview["plan_validation"]
        return [
            "Authoritative plan rejected: error_code=invalid_plan; "
            f"accepted_action_ids={validation['selected_action_ids']}; "
            f"used_slots={validation['used_slots']}; "
            f"required_slots={validation['required_slots']}"
        ]

    result = gateway.decide(request, validator=authoritative)

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.decision is not None
    assert result.decision.actions == REPAIRED
    assert result.metadata.attempt_count == 2
    assert len(llm.calls) == 2
    assert "accepted_action_ids" in llm.calls[1][-1]["content"]
    assert previews == []


def test_schema_and_authoritative_failures_share_one_repair_budget() -> None:
    llm = _LocalLLM(["not-json", _decision(CONFLICTING).model_dump_json()])
    gateway = LocalChatPersonaGateway(llm)  # type: ignore[arg-type]
    request = PersonaDecisionRequest.from_context(_context(), request_id="money-42-w1")

    result = gateway.decide(
        request,
        validator=lambda _decision: [
            "Authoritative plan rejected: error_code=invalid_plan; used_slots=2; required_slots=4"
        ],
    )

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.INVALID_DECISION
    assert result.metadata.attempt_count == 2
    assert len(llm.calls) == 2


def test_interactive_probe_validation_is_non_mutating(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        game_tools,
        "_run_one_step",
        lambda *_args, **_kwargs: _invalid_preview(),
    )
    probe = build_probe(_settings(tmp_path))
    before = deepcopy(probe.__dict__)

    result = probe.validate_step(CONFLICTING)

    assert result["valid"] is False
    assert probe.__dict__ == before
    with pytest.raises(InteractiveProbeStepError, match="invalid_plan"):
        probe.preview_step(CONFLICTING)
    assert probe.__dict__ == before


def test_authoritative_error_reads_current_plan_submission_contract() -> None:
    error = _authoritative_plan_error(
        {
            "valid": False,
            "error_code": "invalid_plan",
            "plan_submission": {
                "valid": False,
                "requested_action_ids": CONFLICTING,
                "accepted_action_ids": [],
                "rejections": [
                    {
                        "action_id": "cheap_noodle_week",
                        "code": "cooldown_group_conflict",
                    },
                    {"action_id": "mensa_coupon", "code": "cooldown_group_conflict"},
                ],
                "used_slots": 0,
                "idle_slots": 4,
            },
        }
    )

    assert 'proposed_action_ids=["cook_at_home", "cheap_noodle_week"' in error
    assert 'accepted_action_ids=["cook_at_home", "go_running"]' in error
    assert 'rejected_action_ids=["cheap_noodle_week", "mensa_coupon"]' in error
    assert "maximum_slots=4" in error


class _AuthoritativeProbe:
    def __init__(self) -> None:
        self.seed = 42
        self.difficulty = "normal"
        self.scenario = "default_first_semester"
        self.current_week = 0
        self.state = {"week": 1, "money": 1000, "hunger": 60}
        self.last_event_id = ""
        self.last_event_choices: list[dict] = []
        self.finished = False
        self.final_ending: str | None = None
        self.history: list[dict] = []
        self.validation_calls: list[list[str]] = []
        self.step_calls: list[list[str]] = []

    def get_state(self) -> dict:
        return {
            "week": self.current_week,
            "state": dict(self.state),
            "finished": self.finished,
            "last_event_id": self.last_event_id,
        }

    def list_available_actions(self) -> dict:
        return {"actions": _actions()}

    def validate_step(self, actions: list[str]) -> dict:
        self.validation_calls.append(list(actions))
        return _invalid_preview() if actions == CONFLICTING else _valid_preview()

    def preview_step(self, _actions: list[str]) -> dict:
        raise AssertionError("successful authoritative preview must be cached")

    def step(self, *, actions: list[str], event_choice_id: str = "") -> dict:
        del event_choice_id
        self.step_calls.append(list(actions))
        self.current_week = 1
        self.finished = True
        self.final_ending = "semester_complete"
        self.state["week"] = 20
        return {
            "week": 1,
            "state": dict(self.state),
            "triggered_event_id": "",
            "event_choices": [],
            "finished": True,
            "final_ending": self.final_ending,
        }

    def finish(self) -> dict:
        return {
            "finished": True,
            "final_state": dict(self.state),
            "final_ending": self.final_ending,
        }

    def detect_anomalies(self) -> list:
        return []


class _SubsetNormalizingProbe(_AuthoritativeProbe):
    def validate_step(self, actions: list[str]) -> dict:
        self.validation_calls.append(list(actions))
        if actions != CONFLICTING:
            return _valid_preview()
        return {
            "valid": False,
            "error_code": "invalid_plan",
            "plan_submission": {
                "valid": False,
                "requested_action_ids": CONFLICTING,
                "accepted_action_ids": [],
                "rejections": [
                    {"index": 1, "action_id": "cheap_noodle_week", "code": "meal_conflict"},
                    {"index": 2, "action_id": "mensa_coupon", "code": "meal_conflict"},
                ],
                "used_slots": 0,
                "idle_slots": 4,
            },
        }


def test_interactive_player_repairs_with_authoritative_feedback_and_reuses_preview(
    tmp_path: Path,
) -> None:
    llm = _LocalLLM([_decision(CONFLICTING).model_dump_json(), _decision(REPAIRED).model_dump_json()])
    probe = _AuthoritativeProbe()
    agent = InteractivePlayerAgent(
        llm=llm,  # type: ignore[arg-type]
        prompts_root=Path(__file__).resolve().parents[2] / "prompts",
        settings=_settings(),
        max_weeks=1,
        persona="money",
        seed=42,
    )

    result, _paths = agent.play_through(tmp_path, probe=probe)  # type: ignore[arg-type]

    assert len(result.steps) == 1
    assert result.steps[0].chosen_actions == REPAIRED
    assert result.steps[0].validation == {
        "valid": True,
        "errors": [],
        "repair_count": 1,
        "fallback_used": False,
    }
    assert probe.validation_calls == [CONFLICTING, REPAIRED]
    assert probe.step_calls == [REPAIRED]
    assert len(llm.calls) == 2


def test_interactive_player_drops_only_godot_rejected_actions(tmp_path: Path) -> None:
    llm = _LocalLLM([_decision(CONFLICTING).model_dump_json()])
    probe = _SubsetNormalizingProbe()
    agent = InteractivePlayerAgent(
        llm=llm,  # type: ignore[arg-type]
        prompts_root=Path(__file__).resolve().parents[2] / "prompts",
        settings=_settings(),
        max_weeks=1,
        persona="money",
        seed=42,
    )

    result, _paths = agent.play_through(tmp_path, probe=probe)  # type: ignore[arg-type]

    expected = ["cook_at_home", "go_running"]
    assert result.steps[0].chosen_actions == expected
    assert result.steps[0].decision["normalization_notes"] == [
        "godot_rejected_action:cheap_noodle_week:meal_conflict",
        "godot_rejected_action:mensa_coupon:meal_conflict",
    ]
    assert probe.validation_calls == [CONFLICTING, expected]
    assert probe.step_calls == [expected]
    assert len(llm.calls) == 1
