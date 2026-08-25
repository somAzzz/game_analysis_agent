"""Tests for the provider-neutral PersonaDecisionGateway contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from game_analysis_agent.persona_gateway import (
    PersonaCallMetadata,
    PersonaDecisionGateway,
    PersonaDecisionRequest,
    PersonaDecisionResult,
    PersonaErrorCategory,
    PersonaParseStatus,
    PersonaProvider,
    PersonaProviderError,
    PersonaProviderMode,
    PersonaResultStatus,
    context_state_hash,
)
from game_analysis_agent.schemas import PlayerDecision, WeekContext


def _context() -> WeekContext:
    return WeekContext.model_validate(
        {
            "game_version": "test",
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "persona": "newbie",
            "state": {"week": 1, "money": 420, "stress": 55},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
                "contract_version": "1.0",
            },
            "available_actions": [{"id": "budget_call", "name": "Budget call"}],
            "memory": {"persona": "newbie"},
        }
    )


def _decision(context: WeekContext) -> PlayerDecision:
    return PlayerDecision(
        week=context.state.week,
        persona=context.persona,
        strategic_goal="protect registration",
        actions=[context.available_actions[0].id],
        expected_tradeoff="spend one action slot",
        confidence=0.8,
    )


def test_request_hash_and_fingerprint_are_stable_and_context_bound() -> None:
    context = _context()
    first = PersonaDecisionRequest.from_context(context, request_id="newbie-42-w1")
    second = PersonaDecisionRequest.from_context(context, request_id="newbie-42-w1")

    assert first.state_hash == context_state_hash(context)
    assert first.fingerprint() == second.fingerprint()

    changed = context.model_copy(deep=True)
    changed.state.money += 1
    different = PersonaDecisionRequest.from_context(changed, request_id="newbie-42-w1")
    assert different.state_hash != first.state_hash
    assert different.fingerprint() != first.fingerprint()


def test_request_rejects_caller_supplied_mismatched_state_hash() -> None:
    with pytest.raises(ValidationError, match="state_hash does not match"):
        PersonaDecisionRequest(
            request_id="bad",
            context=_context(),
            state_hash="0" * 64,
        )


def test_result_envelope_is_fail_closed() -> None:
    request = PersonaDecisionRequest.from_context(_context(), request_id="request")
    metadata = PersonaCallMetadata(
        provider=PersonaProvider.REPLAY,
        mode=PersonaProviderMode.REPLAY,
        parse_status=PersonaParseStatus.PARSED,
    )
    result = PersonaDecisionResult(
        status=PersonaResultStatus.COMPLETED,
        request_fingerprint=request.fingerprint(),
        decision=_decision(request.context),
        metadata=metadata,
    )
    assert result.decision is not None

    with pytest.raises(ValidationError, match="requires a value"):
        PersonaDecisionResult(
            status=PersonaResultStatus.COMPLETED,
            request_fingerprint=request.fingerprint(),
            metadata=metadata,
        )


def test_failed_result_has_typed_sanitized_error() -> None:
    request = PersonaDecisionRequest.from_context(_context(), request_id="request")
    result = PersonaDecisionResult(
        status=PersonaResultStatus.FAILED,
        request_fingerprint=request.fingerprint(),
        metadata=PersonaCallMetadata(
            provider=PersonaProvider.OPENAI,
            mode=PersonaProviderMode.LIVE,
            parse_status=PersonaParseStatus.FAILED,
        ),
        error=PersonaProviderError(
            category=PersonaErrorCategory.REFUSAL,
            message="persona worker refused the decision",
        ),
    )

    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.REFUSAL


def test_protocol_accepts_provider_neutral_implementation() -> None:
    class Gateway:
        provider = PersonaProvider.REPLAY
        mode = PersonaProviderMode.REPLAY

        def decide(self, request):  # noqa: ANN001
            raise NotImplementedError

        def choose_event(self, request):  # noqa: ANN001
            raise NotImplementedError

    assert isinstance(Gateway(), PersonaDecisionGateway)
