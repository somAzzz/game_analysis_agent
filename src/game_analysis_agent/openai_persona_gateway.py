"""OpenAI Responses API adapter for provider-neutral persona decisions."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from openai import (
    APIConnectionError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from openai import APITimeoutError as OpenAITimeoutError

from .persona_gateway import (
    PersonaCallMetadata,
    PersonaDecisionRequest,
    PersonaDecisionResult,
    PersonaErrorCategory,
    PersonaEventChoice,
    PersonaEventChoiceRequest,
    PersonaEventChoiceResult,
    PersonaParseStatus,
    PersonaProvider,
    PersonaProviderError,
    PersonaProviderMode,
    PersonaResultStatus,
    PersonaUsage,
    validate_event_choice,
    validate_player_decision,
)
from .schemas import PlayerDecision

DEFAULT_OPENAI_PERSONA_MODEL = "gpt-5.6-luna"


@dataclass
class _Outcome:
    value: Any | None
    metadata: PersonaCallMetadata
    error: PersonaProviderError | None


class OpenAIResponsesPersonaGateway:
    """Use Responses Structured Outputs without leaking SDK objects downstream."""

    provider = PersonaProvider.OPENAI
    mode = PersonaProviderMode.LIVE

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_OPENAI_PERSONA_MODEL,
        client: Any | None = None,
        timeout_s: float = 30.0,
        max_output_tokens: int = 700,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key is required for the live persona gateway")
        self.model = model
        self.max_output_tokens = max_output_tokens
        self._client = client or OpenAI(
            api_key=api_key,
            timeout=timeout_s,
            max_retries=0,
        )

    def decide(self, request: PersonaDecisionRequest) -> PersonaDecisionResult:
        outcome = self._structured_request(
            schema=PlayerDecision,
            system=_decision_system_prompt(),
            initial_prompt=_decision_prompt(request),
            repair_prompt=lambda errors: _decision_repair_prompt(request, errors),
            validate=lambda value: validate_player_decision(value, request.context),
        )
        if outcome.error is not None:
            return PersonaDecisionResult(
                status=PersonaResultStatus.FAILED,
                request_fingerprint=request.fingerprint(),
                metadata=outcome.metadata,
                error=outcome.error,
            )
        return PersonaDecisionResult(
            status=PersonaResultStatus.COMPLETED,
            request_fingerprint=request.fingerprint(),
            decision=outcome.value,
            metadata=outcome.metadata,
        )

    def choose_event(
        self, request: PersonaEventChoiceRequest
    ) -> PersonaEventChoiceResult:
        outcome = self._structured_request(
            schema=PersonaEventChoice,
            system=_event_system_prompt(),
            initial_prompt=_event_prompt(request),
            repair_prompt=lambda errors: _event_repair_prompt(request, errors),
            validate=lambda value: validate_event_choice(value, request),
        )
        if outcome.error is not None:
            return PersonaEventChoiceResult(
                status=PersonaResultStatus.FAILED,
                request_fingerprint=request.fingerprint(),
                metadata=outcome.metadata,
                error=outcome.error,
            )
        return PersonaEventChoiceResult(
            status=PersonaResultStatus.COMPLETED,
            request_fingerprint=request.fingerprint(),
            choice=outcome.value,
            metadata=outcome.metadata,
        )

    def _structured_request(
        self,
        *,
        schema: type,
        system: str,
        initial_prompt: str,
        repair_prompt,
        validate,
    ) -> _Outcome:
        total_usage = PersonaUsage(input_tokens=0, output_tokens=0, total_tokens=0)
        last_metadata = self._metadata(attempt=1, usage=total_usage)
        last_errors = ["structured output missing"]
        saw_parsed = False
        for attempt in (1, 2):
            prompt = initial_prompt if attempt == 1 else repair_prompt(last_errors)
            started = time.perf_counter()
            try:
                response = self._client.responses.parse(
                    model=self.model,
                    input=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    text_format=schema,
                    max_output_tokens=self.max_output_tokens,
                    store=False,
                )
            except Exception as exc:
                metadata = self._metadata(
                    attempt=attempt,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    usage=total_usage,
                    parse_status=PersonaParseStatus.FAILED,
                )
                return _Outcome(None, metadata, _provider_error(exc))
            parsed, refusal = _response_content(response)
            usage = _response_usage(response)
            total_usage = _sum_usage(total_usage, usage)
            last_metadata = self._metadata(
                attempt=attempt,
                response=response,
                latency_ms=int((time.perf_counter() - started) * 1000),
                usage=total_usage,
                parse_status=PersonaParseStatus.FAILED,
                refusal=refusal,
            )
            if refusal:
                return _Outcome(
                    None,
                    last_metadata,
                    PersonaProviderError(
                        category=PersonaErrorCategory.REFUSAL,
                        message=_sanitize_message(refusal),
                        retryable=False,
                    ),
                )
            if parsed is None:
                last_errors = ["structured output missing"]
                continue
            saw_parsed = True
            try:
                value = parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
            except Exception:
                last_errors = ["structured output failed Pydantic validation"]
                continue
            last_errors = validate(value)
            if last_errors:
                continue
            last_metadata.parse_status = (
                PersonaParseStatus.PARSED if attempt == 1 else PersonaParseStatus.REPAIRED
            )
            return _Outcome(value, last_metadata, None)
        category = (
            PersonaErrorCategory.INVALID_DECISION
            if saw_parsed
            else PersonaErrorCategory.MALFORMED_RESPONSE
        )
        return _Outcome(
            None,
            last_metadata,
            PersonaProviderError(
                category=category,
                message=_sanitize_message("; ".join(last_errors)),
                retryable=False,
            ),
        )

    def _metadata(
        self,
        *,
        attempt: int,
        usage: PersonaUsage,
        response: Any | None = None,
        latency_ms: int = 0,
        parse_status: PersonaParseStatus = PersonaParseStatus.NOT_APPLICABLE,
        refusal: str = "",
    ) -> PersonaCallMetadata:
        return PersonaCallMetadata(
            provider=self.provider,
            mode=self.mode,
            model=str(getattr(response, "model", None) or self.model),
            response_id=str(getattr(response, "id", "")),
            latency_ms=latency_ms,
            attempt_count=attempt,
            parse_status=parse_status,
            refusal=_sanitize_message(refusal) if refusal else "",
            usage=usage,
        )


def _response_content(response: Any) -> tuple[Any | None, str]:
    parsed = getattr(response, "output_parsed", None)
    refusal = ""
    for output in getattr(response, "output", []) or []:
        if getattr(output, "type", "") != "message":
            continue
        for item in getattr(output, "content", []) or []:
            if getattr(item, "type", "") == "refusal":
                refusal = str(getattr(item, "refusal", "") or "")
            candidate = getattr(item, "parsed", None)
            if candidate is not None:
                parsed = candidate
    return parsed, refusal


def _response_usage(response: Any) -> PersonaUsage:
    usage = getattr(response, "usage", None)
    return PersonaUsage(
        input_tokens=_nonnegative(getattr(usage, "input_tokens", None)),
        output_tokens=_nonnegative(getattr(usage, "output_tokens", None)),
        total_tokens=_nonnegative(getattr(usage, "total_tokens", None)),
    )


def _sum_usage(left: PersonaUsage, right: PersonaUsage) -> PersonaUsage:
    return PersonaUsage(
        input_tokens=(left.input_tokens or 0) + (right.input_tokens or 0),
        output_tokens=(left.output_tokens or 0) + (right.output_tokens or 0),
        total_tokens=(left.total_tokens or 0) + (right.total_tokens or 0),
    )


def _provider_error(exc: Exception) -> PersonaProviderError:
    if isinstance(exc, AuthenticationError):
        category = PersonaErrorCategory.AUTHENTICATION
        message = "OpenAI authentication failed"
        retryable = False
    elif isinstance(exc, RateLimitError):
        category = PersonaErrorCategory.RATE_LIMIT
        message = "OpenAI rate limit exceeded"
        retryable = True
    elif isinstance(exc, OpenAITimeoutError):
        category = PersonaErrorCategory.TIMEOUT
        message = "OpenAI request timed out"
        retryable = True
    elif isinstance(exc, APIConnectionError):
        category = PersonaErrorCategory.TRANSPORT
        message = "OpenAI connection failed"
        retryable = True
    else:
        category = PersonaErrorCategory.TRANSPORT
        message = f"OpenAI request failed: {exc.__class__.__name__}"
        retryable = False
    return PersonaProviderError(category=category, message=message, retryable=retryable)


def _decision_system_prompt() -> str:
    return (
        "Act only as the supplied game-testing persona. Choose legal weekly actions "
        "from WeekContext and return the PlayerDecision schema. Do not inspect code, "
        "suggest patches, use tools, or reveal hidden reasoning."
    )


def _event_system_prompt() -> str:
    return (
        "Act only as the supplied game-testing persona. Choose exactly one legal "
        "event choice and return the PersonaEventChoice schema."
    )


def _decision_prompt(request: PersonaDecisionRequest) -> str:
    return "Choose this week's actions from this JSON context:\n" + _context_json(request.context)


def _decision_repair_prompt(request: PersonaDecisionRequest, errors: list[str]) -> str:
    return (
        "Repair the prior structured decision once. Errors: "
        + json.dumps(errors, ensure_ascii=False)
        + "\nUse only legal ids in this context:\n"
        + _context_json(request.context)
    )


def _event_prompt(request: PersonaEventChoiceRequest) -> str:
    payload = {
        "context": request.context.model_dump(mode="json"),
        "selected_actions": request.selected_actions,
    }
    return "Choose one event choice from this JSON context:\n" + _compact_json(payload)


def _event_repair_prompt(request: PersonaEventChoiceRequest, errors: list[str]) -> str:
    return (
        "Repair the prior event choice once. Errors: "
        + json.dumps(errors, ensure_ascii=False)
        + "\n"
        + _event_prompt(request)
    )


def _context_json(context) -> str:
    return _compact_json(context.model_dump(mode="json"))


def _compact_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sanitize_message(value: str) -> str:
    sanitized = re.sub(r"sk-[A-Za-z0-9_-]+", "<redacted>", str(value))
    return sanitized[:500] or "provider error"


def _nonnegative(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None
