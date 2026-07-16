"""OpenAI-compatible local-provider adapter for persona decisions."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from .llm_client import LLMRequestError, LocalLLMClient
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
from .persona_runtime import redact_sensitive_text
from .schemas import LLMCall, PlayerDecision

AuditSink = Callable[[LLMCall], None]


class LocalChatPersonaGateway:
    """Adapt vLLM/SGLang/DeepSeek chat JSON to the shared persona contract."""

    def __init__(
        self,
        llm: LocalLLMClient,
        *,
        audit_sink: AuditSink | None = None,
        decision_max_tokens: int = 768,
        event_max_tokens: int = 192,
        temperature: float = 0.3,
    ) -> None:
        provider_name = getattr(llm, "provider", None) or llm.settings.provider()
        try:
            self.provider = PersonaProvider(provider_name)
        except ValueError as exc:
            raise ValueError(f"Unsupported local persona provider: {provider_name}") from exc
        if self.provider not in {
            PersonaProvider.VLLM,
            PersonaProvider.SGLANG,
            PersonaProvider.DEEPSEEK,
        }:
            raise ValueError(f"Provider is not OpenAI-compatible local chat: {self.provider}")
        self.mode = (
            PersonaProviderMode.LIVE
            if self.provider == PersonaProvider.DEEPSEEK
            else PersonaProviderMode.LOCAL
        )
        self.model = getattr(llm, "model", None) or llm.settings.model()
        self.llm = llm
        self.decision_max_tokens = decision_max_tokens
        self.event_max_tokens = event_max_tokens
        self.temperature = temperature
        self._audit_sink = audit_sink

    def set_audit_sink(self, sink: AuditSink | None) -> None:
        self._audit_sink = sink

    def decide(self, request: PersonaDecisionRequest) -> PersonaDecisionResult:
        week = _request_week(request.request_id, request.context.state.week)
        errors = ["structured output missing"]
        saw_model = False
        metadata: PersonaCallMetadata | None = None
        for attempt in (1, 2):
            prompt = (
                _decision_prompt(request)
                if attempt == 1
                else _decision_repair_prompt(request, errors)
            )
            content, call_metadata, failure = self._chat(
                system=(
                    "Act only as this game-testing persona. Return one PlayerDecision "
                    "JSON object using legal ids. Do not inspect or patch source."
                ),
                prompt=prompt,
                step_name=(
                    f"week-{week}"
                    if attempt == 1
                    else f"week-{week}-repair-1"
                ),
                max_tokens=self.decision_max_tokens,
                attempt=attempt,
            )
            metadata = _accumulate_metadata(metadata, call_metadata)
            if failure is not None:
                return PersonaDecisionResult(
                    status=PersonaResultStatus.FAILED,
                    request_fingerprint=request.fingerprint(),
                    metadata=metadata,
                    error=failure,
                )
            parsed = _extract_json_object(content)
            if parsed is None:
                errors = ["structured output missing"]
                continue
            saw_model = True
            try:
                decision = PlayerDecision.model_validate(
                    _normalize_decision(parsed, request)
                )
            except ValidationError:
                errors = ["structured output failed Pydantic validation"]
                continue
            errors = validate_player_decision(decision, request.context)
            if errors:
                continue
            metadata.parse_status = (
                PersonaParseStatus.PARSED
                if attempt == 1
                else PersonaParseStatus.REPAIRED
            )
            return PersonaDecisionResult(
                status=PersonaResultStatus.COMPLETED,
                request_fingerprint=request.fingerprint(),
                decision=decision,
                metadata=metadata,
            )
        return PersonaDecisionResult(
            status=PersonaResultStatus.FAILED,
            request_fingerprint=request.fingerprint(),
            metadata=metadata or self._metadata(attempt=2),
            error=_invalid_output(errors, saw_model=saw_model),
        )

    def choose_event(
        self, request: PersonaEventChoiceRequest
    ) -> PersonaEventChoiceResult:
        week = _request_week(request.request_id, request.context.state.week)
        errors = ["structured output missing"]
        saw_model = False
        metadata: PersonaCallMetadata | None = None
        for attempt in (1, 2):
            prompt = (
                _event_prompt(request)
                if attempt == 1
                else _event_repair_prompt(request, errors)
            )
            content, call_metadata, failure = self._chat(
                system="Select one legal game event option. Never invent an id.",
                prompt=prompt,
                step_name=(
                    f"week-{week}-event"
                    if attempt == 1
                    else f"week-{week}-event-repair-1"
                ),
                max_tokens=self.event_max_tokens,
                attempt=attempt,
            )
            metadata = _accumulate_metadata(metadata, call_metadata)
            if failure is not None:
                return PersonaEventChoiceResult(
                    status=PersonaResultStatus.FAILED,
                    request_fingerprint=request.fingerprint(),
                    metadata=metadata,
                    error=failure,
                )
            parsed = _extract_json_object(content)
            if parsed is None:
                errors = ["structured output missing"]
                continue
            saw_model = True
            payload = {
                "week": request.context.state.week,
                "persona": request.context.persona,
                "event_id": request.context.current_event_id,
                "event_choice_id": parsed.get("event_choice_id", ""),
            }
            try:
                choice = PersonaEventChoice.model_validate(payload)
            except ValidationError:
                errors = ["structured output failed Pydantic validation"]
                continue
            errors = validate_event_choice(choice, request)
            if errors:
                continue
            metadata.parse_status = (
                PersonaParseStatus.PARSED
                if attempt == 1
                else PersonaParseStatus.REPAIRED
            )
            return PersonaEventChoiceResult(
                status=PersonaResultStatus.COMPLETED,
                request_fingerprint=request.fingerprint(),
                choice=choice,
                metadata=metadata,
            )
        return PersonaEventChoiceResult(
            status=PersonaResultStatus.FAILED,
            request_fingerprint=request.fingerprint(),
            metadata=metadata or self._metadata(attempt=2),
            error=_invalid_output(errors, saw_model=saw_model),
        )

    def _chat(
        self,
        *,
        system: str,
        prompt: str,
        step_name: str,
        max_tokens: int,
        attempt: int,
    ) -> tuple[str, PersonaCallMetadata, PersonaProviderError | None]:
        started = time.perf_counter()
        try:
            content, call = self.llm.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                agent="interactive_player",
                step_name=step_name,
                max_tokens=max_tokens,
                temperature=self.temperature,
            )
        except LLMRequestError as exc:
            self._emit(exc.call)
            return (
                "",
                self._metadata(
                    attempt=attempt,
                    call=exc.call,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    parse_status=PersonaParseStatus.FAILED,
                ),
                PersonaProviderError(
                    category=PersonaErrorCategory.TRANSPORT,
                    message=redact_sensitive_text(exc),
                    retryable=True,
                ),
            )
        except Exception as exc:
            return (
                "",
                self._metadata(
                    attempt=attempt,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    parse_status=PersonaParseStatus.FAILED,
                ),
                PersonaProviderError(
                    category=PersonaErrorCategory.TRANSPORT,
                    message=redact_sensitive_text(
                        f"local provider failed: {exc.__class__.__name__}"
                    ),
                    retryable=False,
                ),
            )
        self._emit(call)
        return content, self._metadata(attempt=attempt, call=call), None

    def _emit(self, call: LLMCall) -> None:
        if self._audit_sink is not None:
            self._audit_sink(call)

    def _metadata(
        self,
        *,
        attempt: int,
        call: LLMCall | None = None,
        latency_ms: int | None = None,
        parse_status: PersonaParseStatus = PersonaParseStatus.FAILED,
    ) -> PersonaCallMetadata:
        return PersonaCallMetadata(
            provider=self.provider,
            mode=self.mode,
            model=self.model,
            response_id=call.call_id if call else "",
            latency_ms=(call.latency_ms or 0) if latency_ms is None and call else latency_ms or 0,
            attempt_count=attempt,
            parse_status=parse_status,
            usage=PersonaUsage(
                input_tokens=call.prompt_tokens if call else None,
                output_tokens=call.completion_tokens if call else None,
                total_tokens=call.total_tokens if call else None,
            ),
        )


def _decision_prompt(request: PersonaDecisionRequest) -> str:
    return (
        "/no_think\nChoose legal weekly actions and return one compact PlayerDecision JSON.\n"
        + request.context.model_dump_json()
    )


def _decision_repair_prompt(
    request: PersonaDecisionRequest, errors: list[str]
) -> str:
    return (
        "Repair the previous PlayerDecision once. Errors: "
        + json.dumps(errors, ensure_ascii=False)
        + "\nLegal context:\n"
        + request.context.model_dump_json()
    )


def _event_prompt(request: PersonaEventChoiceRequest) -> str:
    compact = {
        "week": request.context.state.week,
        "persona": request.context.persona,
        "priorities": request.context.persona_strategy.get("priorities", []),
        "selected_actions": request.selected_actions,
        "state": request.context.state.model_dump(mode="json"),
        "top_risk_ids": [risk.id for risk in request.context.top_risks],
        "event_id": request.context.current_event_id,
        "event_choices": [
            choice.model_dump(mode="json") for choice in request.context.event_choices
        ],
    }
    return "\n".join(
        [
            "/no_think",
            "Choose exactly one event_choice_id from the JSON context.",
            json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
            "Return only compact JSON: {\"event_choice_id\":\"...\"}.",
        ]
    )


def _event_repair_prompt(
    request: PersonaEventChoiceRequest, errors: list[str]
) -> str:
    return (
        _event_prompt(request)
        + "\nPrevious errors: "
        + json.dumps(errors, ensure_ascii=False)
        + ". Return one valid id as JSON only."
    )


def _extract_json_object(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if not text:
        return None
    try:
        direct = json.loads(text)
    except json.JSONDecodeError:
        direct = None
    if isinstance(direct, dict):
        return direct
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


def _normalize_decision(
    parsed: dict[str, Any], request: PersonaDecisionRequest
) -> dict[str, Any]:
    context = request.context
    if parsed.get("tool") == "step" and isinstance(parsed.get("arguments"), dict):
        parsed = {
            "actions": parsed["arguments"].get("actions", []),
            "event_choice_id": parsed["arguments"].get("event_choice_id", ""),
            "strategic_goal": "json fallback tool call",
            "expected_tradeoff": "model emitted step tool JSON",
        }
    normalized = dict(parsed)
    rationale = str(normalized.pop("rationale", "") or "")
    normalized.setdefault("week", context.state.week)
    normalized.setdefault("persona", context.persona)
    normalized.setdefault("strategic_goal", rationale)
    normalized.setdefault("event_choice_id", "")
    normalized.setdefault("risk_awareness", [])
    normalized.setdefault(
        "expected_tradeoff", normalized.get("strategic_goal") or rationale
    )
    normalized.setdefault("confidence", 0.5)
    return normalized


def _invalid_output(errors: list[str], *, saw_model: bool) -> PersonaProviderError:
    return PersonaProviderError(
        category=(
            PersonaErrorCategory.INVALID_DECISION
            if saw_model
            else PersonaErrorCategory.MALFORMED_RESPONSE
        ),
        message=redact_sensitive_text("; ".join(errors)),
        retryable=False,
    )


def _request_week(request_id: str, fallback: int) -> int:
    marker = request_id.rsplit("-w", maxsplit=1)
    if len(marker) == 2:
        candidate = marker[1].split("-", maxsplit=1)[0]
        if candidate.isdigit():
            return int(candidate)
    return fallback


def _accumulate_metadata(
    previous: PersonaCallMetadata | None, current: PersonaCallMetadata
) -> PersonaCallMetadata:
    if previous is None:
        return current
    return current.model_copy(
        update={
            "latency_ms": previous.latency_ms + current.latency_ms,
            "usage": PersonaUsage(
                input_tokens=_sum_optional(
                    previous.usage.input_tokens, current.usage.input_tokens
                ),
                output_tokens=_sum_optional(
                    previous.usage.output_tokens, current.usage.output_tokens
                ),
                total_tokens=_sum_optional(
                    previous.usage.total_tokens, current.usage.total_tokens
                ),
            ),
        }
    )


def _sum_optional(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)


__all__ = ["AuditSink", "LocalChatPersonaGateway"]
