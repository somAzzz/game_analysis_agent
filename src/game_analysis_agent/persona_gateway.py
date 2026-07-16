"""Provider-neutral contracts for one interactive persona decision."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schemas import PlayerDecision, WeekContext


class PersonaProvider(StrEnum):
    """Supported decision providers without endpoint-specific details."""

    REPLAY = "replay"
    OPENAI = "openai"
    VLLM = "vllm"
    SGLANG = "sglang"
    DEEPSEEK = "deepseek"


class PersonaProviderMode(StrEnum):
    """Truthful execution mode exposed in reports and UI."""

    REPLAY = "replay"
    LIVE = "live"
    LOCAL = "local"


class PersonaResultStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PersonaParseStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PARSED = "parsed"
    REPAIRED = "repaired"
    FAILED = "failed"


class PersonaErrorCategory(StrEnum):
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    REFUSAL = "refusal"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    TRANSPORT = "transport"
    MALFORMED_RESPONSE = "malformed_response"
    INVALID_DECISION = "invalid_decision"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CANCELLED = "cancelled"
    FIXTURE_MISMATCH = "fixture_mismatch"


class PersonaUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class PersonaProviderError(BaseModel):
    """Sanitized provider failure; never stores an SDK exception or secret."""

    model_config = ConfigDict(extra="forbid")

    category: PersonaErrorCategory
    message: str = Field(min_length=1, max_length=500)
    retryable: bool = False


class PersonaCallMetadata(BaseModel):
    """Common audit metadata emitted by Replay, OpenAI, and local gateways."""

    model_config = ConfigDict(extra="forbid")

    provider: PersonaProvider
    mode: PersonaProviderMode
    model: str = ""
    response_id: str = ""
    latency_ms: int = Field(default=0, ge=0)
    attempt_count: int = Field(default=1, ge=1)
    parse_status: PersonaParseStatus = PersonaParseStatus.NOT_APPLICABLE
    refusal: str = Field(default="", max_length=500)
    usage: PersonaUsage = Field(default_factory=PersonaUsage)


class PersonaDecisionRequest(BaseModel):
    """Exact request identity for one weekly PlayerDecision."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=120)
    context: WeekContext
    state_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _state_hash_matches_context(self) -> PersonaDecisionRequest:
        expected = context_state_hash(self.context)
        if self.state_hash != expected:
            raise ValueError("state_hash does not match WeekContext")
        return self

    @classmethod
    def from_context(cls, context: WeekContext, *, request_id: str) -> PersonaDecisionRequest:
        return cls(
            request_id=request_id,
            context=context,
            state_hash=context_state_hash(context),
        )

    def fingerprint(self) -> str:
        return request_fingerprint(
            kind="decision",
            request_id=self.request_id,
            context=self.context,
            state_hash=self.state_hash,
            selected_actions=[],
        )


class PersonaEventChoiceRequest(BaseModel):
    """Exact request identity for the event-choice phase of a week."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=120)
    context: WeekContext
    state_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_actions: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _state_hash_matches_context(self) -> PersonaEventChoiceRequest:
        expected = context_state_hash(self.context)
        if self.state_hash != expected:
            raise ValueError("state_hash does not match WeekContext")
        return self

    @classmethod
    def from_context(
        cls,
        context: WeekContext,
        *,
        request_id: str,
        selected_actions: list[str],
    ) -> PersonaEventChoiceRequest:
        return cls(
            request_id=request_id,
            context=context,
            state_hash=context_state_hash(context),
            selected_actions=selected_actions,
        )

    def fingerprint(self) -> str:
        return request_fingerprint(
            kind="event_choice",
            request_id=self.request_id,
            context=self.context,
            state_hash=self.state_hash,
            selected_actions=self.selected_actions,
        )


class PersonaEventChoice(BaseModel):
    """Shared event-choice output, independent of provider wire format."""

    model_config = ConfigDict(extra="forbid")

    week: int
    persona: str
    event_id: str
    event_choice_id: str


class PersonaDecisionResult(BaseModel):
    """Provider-neutral envelope around a PlayerDecision."""

    model_config = ConfigDict(extra="forbid")

    status: PersonaResultStatus
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: PlayerDecision | None = None
    metadata: PersonaCallMetadata
    error: PersonaProviderError | None = None

    @model_validator(mode="after")
    def _result_is_consistent(self) -> PersonaDecisionResult:
        _validate_result(self.status, self.decision, self.error)
        return self


class PersonaEventChoiceResult(BaseModel):
    """Provider-neutral envelope around a PersonaEventChoice."""

    model_config = ConfigDict(extra="forbid")

    status: PersonaResultStatus
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    choice: PersonaEventChoice | None = None
    metadata: PersonaCallMetadata
    error: PersonaProviderError | None = None

    @model_validator(mode="after")
    def _result_is_consistent(self) -> PersonaEventChoiceResult:
        _validate_result(self.status, self.choice, self.error)
        return self


@runtime_checkable
class PersonaDecisionGateway(Protocol):
    """Narrow interactive-player seam shared by every provider."""

    provider: PersonaProvider
    mode: PersonaProviderMode

    def decide(self, request: PersonaDecisionRequest) -> PersonaDecisionResult: ...

    def choose_event(
        self, request: PersonaEventChoiceRequest
    ) -> PersonaEventChoiceResult: ...


def context_state_hash(context: WeekContext) -> str:
    """Hash the canonical state snapshot used for exact Replay matching."""

    payload = context.state.model_dump(mode="json")
    return _json_sha256(payload)


def validate_player_decision(
    decision: PlayerDecision, context: WeekContext
) -> list[str]:
    """Apply the one legal-action/event-choice policy shared by all providers."""

    errors: list[str] = []
    valid_actions = {action.id for action in context.available_actions}
    for action_id in decision.actions:
        if action_id not in valid_actions:
            errors.append(f"Unknown action_id: {action_id}")
    if len(decision.actions) > context.max_action_slots:
        errors.append(f"Too many actions: {len(decision.actions)}")
    if decision.week != context.state.week:
        errors.append(f"Decision week mismatch: {decision.week}")
    if decision.persona != context.persona:
        errors.append(f"Decision persona mismatch: {decision.persona}")
    if context.event_choices and not decision.event_choice_id:
        errors.append("Missing event_choice_id")
    if context.event_choices and decision.event_choice_id:
        valid_choices = {choice.choice_id for choice in context.event_choices}
        if decision.event_choice_id not in valid_choices:
            errors.append(f"Invalid event_choice_id: {decision.event_choice_id}")
    if not decision.strategic_goal.strip():
        errors.append("Missing strategic_goal")
    if not decision.expected_tradeoff.strip():
        errors.append("Missing expected_tradeoff")
    return errors


def validate_event_choice(
    choice: PersonaEventChoice, request: PersonaEventChoiceRequest
) -> list[str]:
    """Validate the separate event phase against the same WeekContext."""

    errors = []
    context = request.context
    if choice.week != context.state.week:
        errors.append(f"Event choice week mismatch: {choice.week}")
    if choice.persona != context.persona:
        errors.append(f"Event choice persona mismatch: {choice.persona}")
    if choice.event_id != context.current_event_id:
        errors.append(f"Event id mismatch: {choice.event_id}")
    valid_choices = {item.choice_id for item in context.event_choices}
    if choice.event_choice_id not in valid_choices:
        errors.append(f"Invalid event_choice_id: {choice.event_choice_id}")
    return errors


def request_fingerprint(
    *,
    kind: str,
    request_id: str,
    context: WeekContext,
    state_hash: str,
    selected_actions: list[str],
) -> str:
    """Bind persona, seed, week, state, event context, and selected actions."""

    payload = {
        "kind": kind,
        "request_id": request_id,
        "persona": context.persona,
        "seed": context.seed,
        "week": context.state.week,
        "state_hash": state_hash,
        "event_id": context.current_event_id,
        "event_choices": [choice.choice_id for choice in context.event_choices],
        "selected_actions": selected_actions,
    }
    return _json_sha256(payload)


def _validate_result(status: PersonaResultStatus, value: object, error: object) -> None:
    if status == PersonaResultStatus.COMPLETED and (value is None or error is not None):
        raise ValueError("completed persona result requires a value and no error")
    if status != PersonaResultStatus.COMPLETED and (value is not None or error is None):
        raise ValueError("non-completed persona result requires an error and no value")


def _json_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
