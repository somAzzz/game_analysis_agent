"""Provider selection and runtime-governance tests for Judge Mode."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError

from game_analysis_agent.persona_gateway import (
    PersonaCallMetadata,
    PersonaDecisionRequest,
    PersonaDecisionResult,
    PersonaErrorCategory,
    PersonaProvider,
    PersonaProviderError,
    PersonaProviderMode,
    PersonaResultStatus,
)
from game_analysis_agent.persona_runtime import (
    GovernedPersonaGateway,
    PersonaCancellationToken,
    PersonaRuntimeConfigurationError,
    PersonaRuntimeLimits,
    PersonaRuntimeSettings,
    redact_sensitive_text,
)
from game_analysis_agent.recorded_persona_gateway import RecordedPersonaGateway
from game_analysis_agent.schemas import PlayerDecision, WeekContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WeekContext:
    return WeekContext.model_validate(
        {
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "persona": "newbie",
            "state": {"week": 1},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
            },
            "available_actions": [{"id": "rest_at_home"}],
            "memory": {"persona": "newbie"},
        }
    )


def _request(index: int = 0) -> PersonaDecisionRequest:
    return PersonaDecisionRequest.from_context(_context(), request_id=f"newbie-42-w1-{index}")


def _result(
    request: PersonaDecisionRequest,
    *,
    status: PersonaResultStatus = PersonaResultStatus.COMPLETED,
    retryable: bool = False,
) -> PersonaDecisionResult:
    metadata = PersonaCallMetadata(
        provider=PersonaProvider.OPENAI,
        mode=PersonaProviderMode.LIVE,
        model="gpt-test",
        latency_ms=2,
    )
    if status == PersonaResultStatus.COMPLETED:
        return PersonaDecisionResult(
            status=status,
            request_fingerprint=request.fingerprint(),
            decision=PlayerDecision(
                week=1,
                persona="newbie",
                strategic_goal="rest",
                actions=["rest_at_home"],
                expected_tradeoff="time",
                confidence=0.8,
            ),
            metadata=metadata,
        )
    return PersonaDecisionResult(
        status=status,
        request_fingerprint=request.fingerprint(),
        metadata=metadata,
        error=PersonaProviderError(
            category=PersonaErrorCategory.TIMEOUT,
            message="timed out",
            retryable=retryable,
        ),
    )


class _Gateway:
    provider = PersonaProvider.OPENAI
    mode = PersonaProviderMode.LIVE
    model = "gpt-test"

    def __init__(self, outcomes=None, *, delay_s: float = 0) -> None:
        self.outcomes = list(outcomes or [])
        self.delay_s = delay_s
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def decide(self, request: PersonaDecisionRequest) -> PersonaDecisionResult:
        with self._lock:
            self.calls += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.delay_s:
                time.sleep(self.delay_s)
            if self.outcomes:
                status, retryable = self.outcomes.pop(0)
                return _result(request, status=status, retryable=retryable)
            return _result(request)
        finally:
            with self._lock:
                self.active -= 1

    def choose_event(self, request):  # noqa: ANN001
        raise AssertionError("not used in these tests")


def test_auto_selects_replay_before_execution_without_key() -> None:
    settings = PersonaRuntimeSettings.from_env({})
    selection = settings.resolve_provider()

    assert selection.selected == PersonaProvider.REPLAY
    assert selection.mode == PersonaProviderMode.REPLAY
    assert "before execution" in selection.reason
    gateway = RecordedPersonaGateway.from_manifest(
        ROOT / settings.replay_manifest, project_root=ROOT
    )
    assert gateway.provider == PersonaProvider.REPLAY


def test_auto_selects_openai_before_execution_with_key_without_serializing_it() -> None:
    settings = PersonaRuntimeSettings.from_env({"OPENAI_API_KEY": "sk-private-test"})

    selection = settings.resolve_provider()

    assert selection.selected == PersonaProvider.OPENAI
    assert settings.model_dump() == {
        "provider": "auto",
        "openai_model": "gpt-5.6-luna",
        "replay_manifest": "config/build_week_2026_replay.json",
        "limits": settings.limits.model_dump(),
    }
    assert "sk-private-test" not in repr(settings)


def test_explicit_live_provider_without_key_fails_instead_of_replaying() -> None:
    settings = PersonaRuntimeSettings.from_env({"PERSONA_PROVIDER": "openai"})

    with pytest.raises(PersonaRuntimeConfigurationError, match="OPENAI_API_KEY"):
        settings.resolve_provider()


@pytest.mark.parametrize(
    ("provider", "expected_mode"),
    [("vllm", "local"), ("sglang", "local"), ("replay", "replay")],
)
def test_existing_local_and_replay_providers_are_validated(
    provider: str, expected_mode: str
) -> None:
    selection = PersonaRuntimeSettings.from_env({"PERSONA_PROVIDER": provider}).resolve_provider()

    assert selection.selected.value == provider
    assert selection.mode.value == expected_mode


def test_limits_reject_invalid_settings_and_oversized_campaign() -> None:
    with pytest.raises(ValidationError):
        PersonaRuntimeLimits(max_concurrency=0)
    limits = PersonaRuntimeLimits(max_runs=2, max_weeks=3, max_concurrency=1)

    with pytest.raises(PersonaRuntimeConfigurationError, match="runs"):
        limits.validate_campaign(runs=3, weeks=3, concurrency=1)


def test_retry_is_bounded_and_does_not_switch_provider() -> None:
    request = _request()
    gateway = _Gateway(
        outcomes=[
            (PersonaResultStatus.FAILED, True),
            (PersonaResultStatus.COMPLETED, False),
        ]
    )
    governed = GovernedPersonaGateway(
        gateway,
        limits=PersonaRuntimeLimits(max_calls=10, max_retries=1, retry_backoff_s=0),
    )

    result = governed.decide(request)

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.metadata.provider == PersonaProvider.OPENAI
    assert result.metadata.mode == PersonaProviderMode.LIVE
    assert result.metadata.attempt_count == 2
    assert gateway.calls == governed.calls_used == 2


def test_governed_gateway_forwards_audit_sink() -> None:
    class AuditedGateway(_Gateway):
        def set_audit_sink(self, sink) -> None:  # noqa: ANN001
            self.audit_sink = sink

    gateway = AuditedGateway()
    governed = GovernedPersonaGateway(gateway, limits=PersonaRuntimeLimits())
    sink = object()

    governed.set_audit_sink(sink)

    assert gateway.audit_sink is sink


def test_live_failure_stays_live_when_retries_are_exhausted() -> None:
    request = _request()
    gateway = _Gateway(
        outcomes=[
            (PersonaResultStatus.FAILED, True),
            (PersonaResultStatus.FAILED, True),
        ]
    )
    governed = GovernedPersonaGateway(
        gateway,
        limits=PersonaRuntimeLimits(max_calls=10, max_retries=1, retry_backoff_s=0),
    )

    result = governed.decide(request)

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.TIMEOUT
    assert result.metadata.provider == PersonaProvider.OPENAI
    assert gateway.calls == 2


def test_call_budget_and_cancellation_fail_closed_without_provider_calls() -> None:
    gateway = _Gateway()
    governed = GovernedPersonaGateway(
        gateway, limits=PersonaRuntimeLimits(max_calls=1, max_retries=0)
    )
    first = governed.decide(_request(1))
    exhausted = governed.decide(_request(2))

    token = PersonaCancellationToken()
    token.cancel()
    cancelled_gateway = _Gateway()
    cancelled = GovernedPersonaGateway(
        cancelled_gateway,
        limits=PersonaRuntimeLimits(),
        cancellation=token,
    ).decide(_request(3))

    assert first.status == PersonaResultStatus.COMPLETED
    assert exhausted.error is not None
    assert exhausted.error.category == PersonaErrorCategory.BUDGET_EXHAUSTED
    assert gateway.calls == 1
    assert cancelled.status == PersonaResultStatus.CANCELLED
    assert cancelled.error is not None
    assert cancelled.error.category == PersonaErrorCategory.CANCELLED
    assert cancelled_gateway.calls == 0


def test_concurrency_cap_is_enforced() -> None:
    gateway = _Gateway(delay_s=0.03)
    governed = GovernedPersonaGateway(
        gateway,
        limits=PersonaRuntimeLimits(max_concurrency=2, max_calls=10, max_retries=0),
    )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(governed.decide, [_request(i) for i in range(4)]))

    assert all(result.status == PersonaResultStatus.COMPLETED for result in results)
    assert gateway.max_active == 2


def test_redaction_covers_keys_and_authorization_headers() -> None:
    message = (
        "sk-secret-123 Authorization: Bearer live-token api_key=another-secret token: final-secret"
    )

    redacted = redact_sensitive_text(message)

    assert "secret" not in redacted
    assert "live-token" not in redacted
    assert redacted.count("<redacted>") == 4
