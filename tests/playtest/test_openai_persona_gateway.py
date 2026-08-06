"""Mocked Responses API tests for the OpenAI persona gateway."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
from openai import APITimeoutError, OpenAI, RateLimitError

from game_analysis_agent.openai_persona_gateway import (
    DEFAULT_OPENAI_MAX_OUTPUT_TOKENS,
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


class _RawAPIResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _RawResponses(_Responses):
    @property
    def with_raw_response(self):
        return self

    def parse(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _RawAPIResponse(outcome)


class _RawClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.responses = _RawResponses(outcomes)


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


def _raw_response(
    *,
    text: str,
    response_id: str = "resp_raw",
    status: str = "completed",
    incomplete_reason: str | None = None,
) -> dict:
    return {
        "id": response_id,
        "created_at": 1.0,
        "model": "gpt-5.6-luna-2026-06-01",
        "object": "response",
        "output": [
            {
                "id": f"msg_{response_id}",
                "content": [
                    {
                        "annotations": [],
                        "logprobs": [],
                        "text": text,
                        "type": "output_text",
                    }
                ],
                "role": "assistant",
                "status": "completed",
                "type": "message",
            }
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "status": status,
        "incomplete_details": ({"reason": incomplete_reason} if incomplete_reason else None),
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens": 30,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 130,
        },
    }


def _gateway(outcomes: list[object]) -> OpenAIResponsesPersonaGateway:
    return OpenAIResponsesPersonaGateway(api_key="sk-test", client=_Client(outcomes))


def _raw_gateway(outcomes: list[object]) -> OpenAIResponsesPersonaGateway:
    return OpenAIResponsesPersonaGateway(api_key="sk-test", client=_RawClient(outcomes))


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
    gateway = _gateway([_response(parsed=_decision(action="ghost")), _response(parsed=_decision())])

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


def test_raw_response_validation_retains_usage_and_repairs_once() -> None:
    malformed = _raw_response(text=json.dumps({"week": "wrong"}), response_id="resp_bad")
    repaired = _raw_response(text=_decision().model_dump_json(), response_id="resp_repaired")
    gateway = _raw_gateway([malformed, repaired])

    result = gateway.decide(_request())

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.metadata.response_id == "resp_repaired"
    assert result.metadata.attempt_count == 2
    assert result.metadata.parse_status == PersonaParseStatus.REPAIRED
    assert result.metadata.usage.total_tokens == 260
    assert (
        gateway._client.responses.calls[0]["max_output_tokens"] == DEFAULT_OPENAI_MAX_OUTPUT_TOKENS
    )


def test_raw_malformed_response_is_typed_without_losing_envelope() -> None:
    gateway = _raw_gateway(
        [
            _raw_response(text="not-json", response_id="resp_bad_1"),
            _raw_response(text="still-not-json", response_id="resp_bad_2"),
        ]
    )

    result = gateway.decide(_request())

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.MALFORMED_RESPONSE
    assert "Invalid JSON" in result.error.message
    assert result.metadata.response_id == "resp_bad_2"
    assert result.metadata.usage.total_tokens == 260


def test_incomplete_raw_response_gets_one_bounded_repair() -> None:
    incomplete = _raw_response(
        text="{",
        response_id="resp_incomplete",
        status="incomplete",
        incomplete_reason="max_output_tokens",
    )
    repaired = _raw_response(text=_decision().model_dump_json(), response_id="resp_complete")
    gateway = _raw_gateway([incomplete, repaired])

    result = gateway.decide(_request())

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.metadata.response_id == "resp_complete"
    assert result.metadata.parse_status == PersonaParseStatus.REPAIRED
    assert result.metadata.usage.total_tokens == 260


def test_real_sdk_raw_wrapper_does_not_raise_before_gateway_repair() -> None:
    payloads = iter(
        [
            _raw_response(text=json.dumps({"week": "wrong"}), response_id="resp_sdk_bad"),
            _raw_response(text=_decision().model_dump_json(), response_id="resp_sdk_good"),
        ]
    )

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["text"]["format"]["type"] == "json_schema"
        return httpx.Response(200, json=next(payloads), request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handle))
    client = OpenAI(
        api_key="sk-test",
        base_url="https://openai.test/v1",
        http_client=http_client,
        max_retries=0,
    )
    try:
        result = OpenAIResponsesPersonaGateway(api_key="sk-test", client=client).decide(_request())
    finally:
        client.close()

    assert result.status == PersonaResultStatus.COMPLETED, (result.error, result.metadata)
    assert result.metadata.response_id == "resp_sdk_good"
    assert result.metadata.parse_status == PersonaParseStatus.REPAIRED
    assert result.metadata.usage.total_tokens == 260
