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
TraceSink = Callable[[dict[str, Any]], None]


class LocalChatPersonaGateway:
    """Adapt vLLM/SGLang/DeepSeek chat JSON to the shared persona contract."""

    def __init__(
        self,
        llm: LocalLLMClient,
        *,
        audit_sink: AuditSink | None = None,
        decision_max_tokens: int | None = None,
        event_max_tokens: int | None = None,
        temperature: float = 0.3,
        enable_thinking: bool | None = None,
        trace_sink: TraceSink | None = None,
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
        settings = llm.settings
        self.decision_max_tokens = _token_budget(
            decision_max_tokens
            if decision_max_tokens is not None
            else getattr(settings, "persona_decision_max_tokens", 2048),
            field="decision_max_tokens",
        )
        self.event_max_tokens = _token_budget(
            event_max_tokens
            if event_max_tokens is not None
            else getattr(settings, "persona_event_max_tokens", 768),
            field="event_max_tokens",
        )
        self.enable_thinking = (
            bool(enable_thinking)
            if enable_thinking is not None
            else bool(getattr(settings, "persona_enable_thinking", True))
        )
        self.temperature = temperature
        self._audit_sink = audit_sink
        self._trace_sink = trace_sink

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
                    "Act only as this game-testing persona. Think privately, but keep "
                    "reasoning separate from the final answer. Final content must be one "
                    "PlayerDecision JSON object using legal ids. Do not inspect or patch source."
                ),
                prefix=_decision_prefix(),
                prompt=prompt,
                step_name=(f"week-{week}" if attempt == 1 else f"week-{week}-repair-1"),
                max_tokens=self.decision_max_tokens,
                attempt=attempt,
                enable_thinking=self._thinking_for_attempt(attempt),
                trace_context={
                    "request_id": request.request_id,
                    "request_fingerprint": request.fingerprint(),
                    "persona": request.context.persona,
                    "seed": request.context.seed,
                    "week": week,
                    "phase": "decision",
                },
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
                errors = [
                    "final structured output missing after reasoning"
                    if call_metadata.reasoning_attempts
                    else "structured output missing"
                ]
                continue
            saw_model = True
            try:
                decision = PlayerDecision.model_validate(_normalize_decision(parsed, request))
            except ValidationError as exc:
                errors = _validation_errors(exc)
                continue
            errors = validate_player_decision(decision, request.context)
            if errors:
                continue
            metadata.parse_status = (
                PersonaParseStatus.PARSED if attempt == 1 else PersonaParseStatus.REPAIRED
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

    def choose_event(self, request: PersonaEventChoiceRequest) -> PersonaEventChoiceResult:
        week = _request_week(request.request_id, request.context.state.week)
        errors = ["structured output missing"]
        saw_model = False
        metadata: PersonaCallMetadata | None = None
        for attempt in (1, 2):
            prompt = (
                _event_prompt(request) if attempt == 1 else _event_repair_prompt(request, errors)
            )
            content, call_metadata, failure = self._chat(
                system=(
                    "Think privately about the observable event tradeoff. Keep reasoning "
                    "separate; final content must select one legal event_choice_id as JSON."
                ),
                prefix=_event_prefix(),
                prompt=prompt,
                step_name=(f"week-{week}-event" if attempt == 1 else f"week-{week}-event-repair-1"),
                max_tokens=self.event_max_tokens,
                attempt=attempt,
                enable_thinking=self._thinking_for_attempt(attempt),
                trace_context={
                    "request_id": request.request_id,
                    "request_fingerprint": request.fingerprint(),
                    "persona": request.context.persona,
                    "seed": request.context.seed,
                    "week": week,
                    "phase": "event_choice",
                },
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
                errors = [
                    "final structured output missing after reasoning"
                    if call_metadata.reasoning_attempts
                    else "structured output missing"
                ]
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
                PersonaParseStatus.PARSED if attempt == 1 else PersonaParseStatus.REPAIRED
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
        prefix: str,
        prompt: str,
        step_name: str,
        max_tokens: int,
        attempt: int,
        enable_thinking: bool,
        trace_context: dict[str, Any],
    ) -> tuple[str, PersonaCallMetadata, PersonaProviderError | None]:
        started = time.perf_counter()
        try:
            messages = _messages(system=system, prefix=prefix, prompt=prompt)
            if self._trace_sink is not None:
                self._trace_sink(
                    {
                        "schema_version": "persona-chat-trace-v1",
                        **trace_context,
                        "attempt": attempt,
                        "step_name": step_name,
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": max_tokens,
                        "enable_thinking": enable_thinking,
                    }
                )
            content, call = self.llm.chat(
                messages,
                agent="interactive_player",
                step_name=step_name,
                max_tokens=max_tokens,
                temperature=self.temperature,
                enable_thinking=enable_thinking,
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
                    reasoning_enabled=enable_thinking,
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
                    reasoning_enabled=enable_thinking,
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
        return (
            content,
            self._metadata(attempt=attempt, call=call, reasoning_enabled=enable_thinking),
            None,
        )

    def _thinking_for_attempt(self, attempt: int) -> bool:
        return (
            attempt == 1
            and self.enable_thinking
            and self.provider in {PersonaProvider.VLLM, PersonaProvider.SGLANG}
        )

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
        reasoning_enabled: bool = False,
    ) -> PersonaCallMetadata:
        return PersonaCallMetadata(
            provider=self.provider,
            mode=self.mode,
            model=self.model,
            response_id=call.call_id if call else "",
            latency_ms=(call.latency_ms or 0) if latency_ms is None and call else latency_ms or 0,
            attempt_count=attempt,
            parse_status=parse_status,
            reasoning_enabled=reasoning_enabled,
            reasoning_attempts=int(bool(call and call.reasoning_present)),
            reasoning_chars=call.reasoning_chars if call else 0,
            reasoning_sha256=([call.reasoning_sha256] if call and call.reasoning_sha256 else []),
            final_content_chars=len(call.response_text) if call else 0,
            usage=PersonaUsage(
                input_tokens=call.prompt_tokens if call else None,
                output_tokens=call.completion_tokens if call else None,
                total_tokens=call.total_tokens if call else None,
            ),
        )


def _messages(*, system: str, prefix: str, prompt: str) -> list[dict[str, str]]:
    """Keep immutable rules/schema tokens before persona-week state."""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": prefix},
        {"role": "user", "content": prompt},
    ]


def _decision_prefix() -> str:
    return "\n".join(
        [
            "Choose one or more legal action ids, up to max_action_slots.",
            (
                "Final content must be compact JSON with exactly these fields: "
                '{"strategic_goal":"short goal","actions":["legal_action_id"],'
                '"event_choice_id":"legal_choice_id","risk_awareness":["short risk"],'
                '"expected_tradeoff":"short text","confidence":0.0}. '
                "Confidence must be a number from 0 to 1."
            ),
        ]
    )


def _decision_prompt(request: PersonaDecisionRequest) -> str:
    context = request.context
    memory = context.memory.model_dump(mode="json")
    history = memory.pop("history", [])
    memory.pop("last_5_weeks", None)
    dynamic = {
        "persona": context.persona,
        "persona_strategy": context.persona_strategy,
        "history": history,
        "memory_summary": memory,
        "week": context.state.week,
        "state": context.state.model_dump(mode="json"),
        "top_risks": [risk.model_dump(mode="json") for risk in context.top_risks],
        "current_event_id": context.current_event_id,
        "max_action_slots": context.max_action_slots,
        "available_actions": [
            action.model_dump(mode="json") for action in context.available_actions
        ],
        "event_choices": [choice.model_dump(mode="json") for choice in context.event_choices],
    }
    return "\n".join(
        [
            "Think privately about the complete observable history and current state.",
            json.dumps(dynamic, ensure_ascii=False, separators=(",", ":")),
            "Return only the final JSON object specified in the stable prefix.",
        ]
    )


def _decision_repair_prompt(request: PersonaDecisionRequest, errors: list[str]) -> str:
    return (
        _decision_prompt(request)
        + "\nPrevious errors: "
        + json.dumps(errors, ensure_ascii=False)
        + ". Return one corrected JSON object only."
    )


def _event_prefix() -> str:
    return "\n".join(
        [
            "Choose exactly one event_choice_id from the legal choices.",
            'Final content must be compact JSON: {"event_choice_id":"..."}.',
        ]
    )


def _event_prompt(request: PersonaEventChoiceRequest) -> str:
    context = request.context
    dynamic = {
        "persona": context.persona,
        "priorities": context.persona_strategy.get("priorities", []),
        "history": [item.model_dump(mode="json") for item in context.memory.history],
        "week": context.state.week,
        "selected_actions": request.selected_actions,
        "state": context.state.model_dump(mode="json"),
        "top_risk_ids": [risk.id for risk in context.top_risks],
        "event_id": context.current_event_id,
        "event_choices": [
            choice.model_dump(mode="json") for choice in context.event_choices
        ],
    }
    return "\n".join(
        [
            "Think privately about the observable history and current event tradeoff.",
            json.dumps(dynamic, ensure_ascii=False, separators=(",", ":")),
            "Return only the final JSON object specified in the stable prefix.",
        ]
    )


def _event_repair_prompt(request: PersonaEventChoiceRequest, errors: list[str]) -> str:
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


def _normalize_decision(parsed: dict[str, Any], request: PersonaDecisionRequest) -> dict[str, Any]:
    context = request.context
    if parsed.get("tool") == "step" and isinstance(parsed.get("arguments"), dict):
        parsed = {
            "actions": parsed["arguments"].get("actions", []),
            "event_choice_id": parsed["arguments"].get("event_choice_id", ""),
            "strategic_goal": "json fallback tool call",
            "expected_tradeoff": "model emitted step tool JSON",
        }
    rationale = str(parsed.get("rationale", "") or "")
    raw_actions = parsed.get("actions", [])
    if not isinstance(raw_actions, list):
        raw_actions = [] if raw_actions in (None, "") else [raw_actions]
    valid_action_ids = {action.id for action in context.available_actions}
    actions = [str(item).strip() for item in raw_actions if str(item).strip() in valid_action_ids]
    risks = parsed.get("risk_awareness", [])
    if not isinstance(risks, list):
        risks = [] if risks in (None, "") else [risks]
    confidence = parsed.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5
    given_tradeoff = str(parsed.get("expected_tradeoff", "") or "")
    strategic_goal = str(parsed.get("strategic_goal", "") or rationale or given_tradeoff)
    expected_tradeoff = given_tradeoff or strategic_goal or rationale
    event_choice_id = parsed.get("event_choice_id", "")
    if isinstance(event_choice_id, list):
        event_choice_id = event_choice_id[0] if event_choice_id else ""
    return {
        "week": context.state.week,
        "persona": context.persona,
        "strategic_goal": strategic_goal[:160],
        "actions": actions,
        "event_choice_id": str(event_choice_id or ""),
        "risk_awareness": [str(item)[:120] for item in risks[:5]],
        "expected_tradeoff": expected_tradeoff[:240],
        "confidence": confidence,
    }


def _validation_errors(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}"
        for error in exc.errors(include_url=False)[:5]
    ]


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
            "reasoning_enabled": (previous.reasoning_enabled or current.reasoning_enabled),
            "reasoning_attempts": (previous.reasoning_attempts + current.reasoning_attempts),
            "reasoning_chars": previous.reasoning_chars + current.reasoning_chars,
            "reasoning_sha256": [*previous.reasoning_sha256, *current.reasoning_sha256][:4],
            "final_content_chars": (previous.final_content_chars + current.final_content_chars),
            "usage": PersonaUsage(
                input_tokens=_sum_optional(previous.usage.input_tokens, current.usage.input_tokens),
                output_tokens=_sum_optional(
                    previous.usage.output_tokens, current.usage.output_tokens
                ),
                total_tokens=_sum_optional(previous.usage.total_tokens, current.usage.total_tokens),
            ),
        }
    )


def _token_budget(value: int, *, field: str) -> int:
    if value < 128 or value > 4096:
        raise ValueError(f"{field} must be between 128 and 4096")
    return value


def _sum_optional(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)


__all__ = ["AuditSink", "LocalChatPersonaGateway"]
