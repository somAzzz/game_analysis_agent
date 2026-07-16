"""Mocked Responses API tests for the OpenAI persona gateway."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
from openai import APITimeoutError, RateLimitError

from game_analysis_agent.openai_persona_gateway import (
    DEFAULT_OPENAI_PERSONA_MODEL,
    OpenAIResponsesPersonaGateway,
)
from game_analysis_agent.persona_gateway import (
    PersonaDecisionRequest,
    PersonaErrorCategory,
    PersonaEventChoiceRequest,
    PersonaParseStatus,
    PersonaProvider,
    PersonaProviderMode,
    PersonaResultStatus,
)
from game_analysis_agent.schemas import PlayerDecision, WeekContext


class _Responses:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    def parse(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _Client:
    def __init__(self, outcomes: list[object]) -> None:
        self.responses = _Responses(outcomes)


def _context() -> WeekContext:
    return WeekContext.model_validate(
        {
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "persona": "newbie",
            "state": {"week": 1, "money": 420, "stress": 55},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
            },
            "available_actions": [{"id": "budget_call"}, {"id": "rest_at_home"}],
            "current_event_id": "rent_pressure",
            "event_choices": [
                {"choice_id": "rent_pressure.pay_now"},
                {"choice_id": "rent_pressure.ask_extension"},
            ],
            "memory": {"persona": "newbie"},
        }
    )


def _decision(*, action: str = "budget_call") -> PlayerDecision:
    return PlayerDecision(
        week=1,
        persona="newbie",
        strategic_goal="protect cashflow",
        actions=[action],
        event_choice_id="rent_pressure.ask_extension",
        expected_tradeoff="use one action slot",
        confidence=0.8,
    )


def _response(*, parsed=None, refusal: str = "", response_id: str = "resp_test"):
    if refusal:
        content = [SimpleNamespace(type="refusal", refusal=refusal, parsed=None)]
    else:
        content = [SimpleNamespace(type="output_text", refusal=None, parsed=parsed)]
    return SimpleNamespace(
        id=response_id,
        model="gpt-5.6-luna-2026-06-01",
        output=[SimpleNamespace(type="message", content=content)],
        usage=SimpleNamespace(input_tokens=100, output_tokens=30, total_tokens=130),
    )


def _gateway(outcomes: list[object]) -> OpenAIResponsesPersonaGateway:
    return OpenAIResponsesPersonaGateway(api_key="sk-test", client=_Client(outcomes))


def _request() -> PersonaDecisionRequest:
    return PersonaDecisionRequest.from_context(_context(), request_id="newbie-42-w1")


def test_successful_structured_decision_captures_openai_metadata() -> None:
    gateway = _gateway([_response(parsed=_decision())])

    result = gateway.decide(_request())

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.metadata.provider == PersonaProvider.OPENAI
    assert result.metadata.mode == PersonaProviderMode.LIVE
    assert result.metadata.model == "gpt-5.6-luna-2026-06-01"
    assert result.metadata.response_id == "resp_test"
    assert result.metadata.usage.total_tokens == 130
    assert result.metadata.parse_status == PersonaParseStatus.PARSED
    call = gateway._client.responses.calls[0]
    assert call["model"] == DEFAULT_OPENAI_PERSONA_MODEL
    assert call["text_format"] is PlayerDecision
    assert call["store"] is False


def test_refusal_is_visible_and_never_replayed() -> None:
    result = _gateway([_response(refusal="Cannot make this decision")]).decide(_request())

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.REFUSAL
    assert result.metadata.mode == PersonaProviderMode.LIVE
    assert result.metadata.refusal == "Cannot make this decision"


def test_timeout_and_rate_limit_are_typed_and_retryable() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    timeout = APITimeoutError(request=request)
    rate_response = httpx.Response(429, request=request)
    rate_limit = RateLimitError("rate limit", response=rate_response, body=None)

    timeout_result = _gateway([timeout]).decide(_request())
    rate_result = _gateway([rate_limit]).decide(_request())

    assert timeout_result.error is not None
    assert timeout_result.error.category == PersonaErrorCategory.TIMEOUT
    assert timeout_result.error.retryable is True
    assert rate_result.error is not None
    assert rate_result.error.category == PersonaErrorCategory.RATE_LIMIT
    assert rate_result.error.retryable is True


def test_malformed_response_gets_one_repair_then_fails() -> None:
    gateway = _gateway([_response(parsed=None), _response(parsed=None, response_id="resp_2")])

    result = gateway.decide(_request())

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.MALFORMED_RESPONSE
    assert result.metadata.attempt_count == 2
    assert len(gateway._client.responses.calls) == 2


def test_unknown_action_is_rejected_after_one_repair() -> None:
    gateway = _gateway(
        [_response(parsed=_decision(action="ghost")), _response(parsed=_decision(action="ghost"))]
    )

    result = gateway.decide(_request())

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.INVALID_DECISION
    assert "Unknown action_id" in result.error.message


def test_one_schema_repair_can_produce_a_legal_decision() -> None:
    gateway = _gateway(
        [_response(parsed=_decision(action="ghost")), _response(parsed=_decision())]
    )

    result = gateway.decide(_request())

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.decision is not None
    assert result.decision.actions == ["budget_call"]
    assert result.metadata.attempt_count == 2
    assert result.metadata.parse_status == PersonaParseStatus.REPAIRED
    assert result.metadata.usage.total_tokens == 260


def test_event_choice_uses_shared_structured_contract() -> None:
    choice = {
        "week": 1,
        "persona": "newbie",
        "event_id": "rent_pressure",
        "event_choice_id": "rent_pressure.ask_extension",
    }
    request = PersonaEventChoiceRequest.from_context(
        _context(), request_id="newbie-42-w1-event", selected_actions=["budget_call"]
    )

    result = _gateway([_response(parsed=choice)]).choose_event(request)

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.choice is not None
    assert result.choice.event_choice_id == "rent_pressure.ask_extension"
