"""OpenAI-compatible tool-calling loop.

Pattern borrowed from ``fintext_llm/src/llm/tool_loop.py``. This module is
deliberately a *thin* copy that does only what the game analysis agents
need: native tool_calls + a JSON-fallback loop. Budget enforcement, async
bridge, and audit-sink plumbing are kept because the interactive-player
agent relies on them.

The tool loop is consumed by :mod:`game_analysis_agent.agents.interactive_player`
to let the LLM play the game across many turns, calling wrapper functions
in :mod:`game_analysis_agent.game_tools` to read state, pick actions, and submit
event choices.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from game_analysis_agent.schemas import (
    LLMCall,
    ToolBudgetUsage,
    ToolExecutionEvent,
)

ToolFunction = Callable[..., Any]
NoOpSink = Callable[[LLMCall], None]

DEFAULT_MAX_TOOL_RESULT_CHARS = 12000
DEFAULT_MAX_TOTAL_TOOL_RESULT_CHARS = 40000
TOOL_BUDGET_EXHAUSTED_PROMPT = (
    "Tool-call budget is exhausted. Do not call any more tools. "
    "Based only on the evidence already available in this conversation, "
    "provide your final analysis now. Explicitly separate evidence, "
    "inference, and uncertainty."
)


class ToolLoopError(Exception):
    """Raised when the tool loop cannot complete."""


def assistant_message_to_dict(message: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": _field(message, "content", None) or "",
    }
    tool_calls = list(_field(message, "tool_calls", None) or [])
    if tool_calls:
        payload["tool_calls"] = [tool_call_to_dict(tc) for tc in tool_calls]
    return payload


def tool_call_to_dict(tool_call: Any) -> dict[str, Any]:
    function = _field(tool_call, "function", {})
    return {
        "id": _field(tool_call, "id", ""),
        "type": _field(tool_call, "type", "function"),
        "function": {
            "name": _field(function, "name", ""),
            "arguments": _field(function, "arguments", "{}"),
        },
    }


def tool_message(
    tool_call: Any,
    result: Any,
    *,
    max_result_chars: int = DEFAULT_MAX_TOOL_RESULT_CHARS,
) -> dict[str, Any]:
    if isinstance(result, str):
        content = result
    else:
        content = json.dumps(result, ensure_ascii=False, default=str)
    content = _truncate_content(content, max_result_chars)
    return {
        "role": "tool",
        "tool_call_id": _field(tool_call, "id", ""),
        "content": content,
    }


def execute_tool_call(
    tool_call: Any,
    tool_map: Mapping[str, ToolFunction],
) -> dict[str, Any]:
    message, _event = execute_tool_call_with_event(
        tool_call,
        tool_map,
        round_id="round-unknown",
    )
    return message


def execute_tool_call_with_event(
    tool_call: Any,
    tool_map: Mapping[str, ToolFunction],
    *,
    round_id: str,
    max_result_chars: int = DEFAULT_MAX_TOOL_RESULT_CHARS,
) -> tuple[dict[str, Any], ToolExecutionEvent]:
    started = datetime.now(tz=UTC)
    function = _field(tool_call, "function", {})
    name = _field(function, "name", "")
    raw_args = _field(function, "arguments", "{}") or "{}"
    tool_call_id = _field(tool_call, "id", "")
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError as exc:
        result = {"error": f"invalid JSON arguments: {exc.msg}"}
        message = tool_message(tool_call, result, max_result_chars=max_result_chars)
        return message, _tool_event(
            started=started,
            round_id=round_id,
            tool_call_id=tool_call_id,
            tool_name=name,
            arguments={},
            status="failed",
            content=message["content"],
            error=result["error"],
        )
    if not isinstance(args, dict):
        result = {"error": "tool arguments must be an object"}
        message = tool_message(tool_call, result, max_result_chars=max_result_chars)
        return message, _tool_event(
            started=started,
            round_id=round_id,
            tool_call_id=tool_call_id,
            tool_name=name,
            arguments={},
            status="failed",
            content=message["content"],
            error=result["error"],
        )
    tool = tool_map.get(name)
    if tool is None:
        result = {"error": f"unknown tool: {name}"}
        message = tool_message(tool_call, result, max_result_chars=max_result_chars)
        return message, _tool_event(
            started=started,
            round_id=round_id,
            tool_call_id=tool_call_id,
            tool_name=name,
            arguments=args,
            status="failed",
            content=message["content"],
            error=result["error"],
        )
    try:
        result = tool(**args)
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}
        message = tool_message(tool_call, result, max_result_chars=max_result_chars)
        return message, _tool_event(
            started=started,
            round_id=round_id,
            tool_call_id=tool_call_id,
            tool_name=name,
            arguments=args,
            status="failed",
            content=message["content"],
            error=result["error"],
        )
    message = tool_message(tool_call, result, max_result_chars=max_result_chars)
    return message, _tool_event(
        started=started,
        round_id=round_id,
        tool_call_id=tool_call_id,
        tool_name=name,
        arguments=args,
        status="success",
        content=message["content"],
        error=None,
    )


def _tool_event(
    *,
    started: datetime,
    round_id: str,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    status: str,
    content: str,
    error: str | None,
) -> ToolExecutionEvent:
    completed = datetime.now(tz=UTC)
    latency_ms = max(0, int((completed - started).total_seconds() * 1000))
    return ToolExecutionEvent(
        event_id=f"tool-{uuid.uuid4().hex[:12]}",
        round_id=round_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments=arguments,
        status=status,  # type: ignore[arg-type]
        result_summary=content[:4000],
        latency_ms=latency_ms,
        error=error,
        created_at=completed,
    )


def _truncate_content(content: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(content) <= max_chars:
        return content
    empty_envelope = json.dumps(
        {"truncated": True, "truncated_text": "", "original_chars": len(content)},
        ensure_ascii=False,
    )
    if len(empty_envelope) > max_chars:
        minimal_envelope = json.dumps({"truncated": True}, ensure_ascii=False)
        if len(minimal_envelope) <= max_chars:
            return minimal_envelope
        return content[:max_chars]
    low, high = 0, len(content)
    best = empty_envelope
    while low <= high:
        mid = (low + high) // 2
        candidate = json.dumps(
            {
                "truncated": True,
                "truncated_text": content[:mid],
                "original_chars": len(content),
            },
            ensure_ascii=False,
        )
        if len(candidate) <= max_chars:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best


def _parse_json_choice(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _json_final_answer(parsed: dict[str, Any] | None, raw_content: str) -> str | None:
    if parsed is None:
        return raw_content if raw_content.strip() else None
    for key in ("final_answer", "answer"):
        value = parsed.get(key)
        if isinstance(value, str):
            return value
    if parsed.get("tool") or parsed.get("tool_calls"):
        return None
    return raw_content


def _json_choice_to_tool_call(
    parsed: dict[str, Any] | None,
    round_index: int,
    *,
    index_hint: int = 0,
) -> dict[str, Any] | None:
    if parsed is None:
        return None
    name = parsed.get("tool") or parsed.get("name")
    if not isinstance(name, str) or not name:
        return None
    raw_args = parsed.get("arguments", {})
    if not isinstance(raw_args, str):
        raw_args = json.dumps(raw_args or {})
    return {
        "id": f"json-call-{round_index}-{index_hint}",
        "type": "function",
        "function": {"name": name, "arguments": raw_args},
    }


def parse_model_response_to_tool_calls(
    content: str,
    *,
    round_index: int = 0,
) -> list[dict[str, Any]]:
    """Extract tool calls from a raw model message.

    Two on-the-wire JSON shapes are accepted as a *fallback* for
    providers (notably local Qwen) that struggle with native OpenAI
    ``tool_calls``:

    1. ``{"tool": "foo", "arguments": {...}}`` — single-tool shorthand.
    2. ``{"tool_calls": [{"name": "foo", "arguments": {...}}, ...]}`` —
       OpenAI-style array. Each entry may use either ``name`` / ``arguments``
       or the nested ``function.name`` / ``function.arguments`` form.

    Returns an empty list when the content is not JSON, when the JSON
    has no tool indicator, or when the JSON cannot be parsed. Errors
    never raise — the caller treats an empty list as "no fallback
    tool calls available".
    """
    parsed = _parse_json_choice(content)
    if parsed is None:
        return []

    # Shape 1: single-tool shorthand.
    if parsed.get("tool") or parsed.get("name"):
        single = _json_choice_to_tool_call(parsed, round_index, index_hint=0)
        return [single] if single is not None else []

    # Shape 2: array of tool calls.
    raw_calls = parsed.get("tool_calls")
    if isinstance(raw_calls, list) and raw_calls:
        collected: list[dict[str, Any]] = []
        for idx, entry in enumerate(raw_calls):
            if not isinstance(entry, dict):
                continue
            sub = dict(entry)
            if "function" in sub and isinstance(sub["function"], dict):
                sub.setdefault("name", sub["function"].get("name"))
                sub.setdefault("arguments", sub["function"].get("arguments", {}))
            call = _json_choice_to_tool_call(sub, round_index, index_hint=idx)
            if call is not None:
                collected.append(call)
        return collected

    return []


class OpenAICompatibleToolLoop:
    """Execute model-requested tool calls for one OpenAI-compatible client."""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        provider: str,
        temperature: float,
        max_tokens: int,
        llm_call_sink: NoOpSink | None = None,
        step_name: str = "tool_calling",
        max_tool_result_chars: int = DEFAULT_MAX_TOOL_RESULT_CHARS,
        max_total_tool_result_chars: int = DEFAULT_MAX_TOTAL_TOOL_RESULT_CHARS,
        extra_request_body: dict[str, Any] | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm_call_sink: NoOpSink = llm_call_sink or (lambda _c: None)
        self.step_name = step_name
        self.max_tool_result_chars = max_tool_result_chars
        self.max_total_tool_result_chars = max_total_tool_result_chars
        self.extra_request_body = extra_request_body or {}
        self.last_tool_events: list[ToolExecutionEvent] = []
        self.last_budget_usage = ToolBudgetUsage(
            max_tool_result_chars=max_tool_result_chars,
            max_total_tool_result_chars=max_total_tool_result_chars,
        )

    def complete(
        self,
        prompt: str,
        *,
        tools: list[dict[str, Any]],
        tool_map: Mapping[str, ToolFunction],
        system: str | None = None,
        max_tool_rounds: int = 4,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        extra_body: dict[str, Any] | None = None,
    ) -> tuple[str, list[LLMCall], list[ToolExecutionEvent]]:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(
            messages,
            tools=tools,
            tool_map=tool_map,
            max_tool_rounds=max_tool_rounds,
            max_tokens=max_tokens,
            temperature=temperature,
            tool_choice=tool_choice,
            extra_body=extra_body,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]],
        tool_map: Mapping[str, ToolFunction],
        max_tool_rounds: int = 4,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        extra_body: dict[str, Any] | None = None,
    ) -> tuple[str, list[LLMCall], list[ToolExecutionEvent]]:
        if not tools:
            raise ValueError("tools must contain at least one tool schema")
        if not tool_map:
            raise ValueError("tool_map must contain executable functions")

        transcript = [dict(message) for message in messages]
        audit_calls: list[LLMCall] = []
        self.last_tool_events = []
        merged_extra = dict(self.extra_request_body)
        if extra_body:
            merged_extra.update(extra_body)
        budget = ToolBudgetUsage(
            max_tool_result_chars=self.max_tool_result_chars,
            max_total_tool_result_chars=self.max_total_tool_result_chars,
        )
        self.last_budget_usage = budget

        for round_index in range(max_tool_rounds + 1):
            request_tool_choice = tool_choice if round_index == 0 else "auto"
            kwargs: dict[str, Any] = {}
            if merged_extra:
                kwargs["extra_body"] = merged_extra
            response = self.client.chat.completions.create(
                model=self.model,
                messages=deepcopy(transcript),
                tools=tools,
                tool_choice=request_tool_choice,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                **kwargs,
            )
            message = response.choices[0].message
            content = _field(message, "content", None) or ""
            tool_calls = list(_field(message, "tool_calls", None) or [])
            # JSON fallback for local Qwen / providers that don't emit
            # native tool_calls. We only fall back when the model returned
            # zero native tool calls *and* the content actually parses as a
            # JSON tool invocation; otherwise we treat content as the
            # final answer (and prefer the extracted ``final_answer`` if the
            # model wrapped the answer in JSON).
            if not tool_calls:
                fallback_calls = parse_model_response_to_tool_calls(
                    content, round_index=round_index
                )
                if fallback_calls:
                    tool_calls = fallback_calls
                else:
                    parsed = _parse_json_choice(content)
                    final_text = _json_final_answer(parsed, content) or content
                    audit = self._build_audit(
                        transcript,
                        final_text,
                        [],
                        round_index,
                        getattr(response, "usage", None),
                    )
                    audit_calls.append(audit)
                    self._llm_call_sink(audit)
                    assistant_payload = dict(assistant_message_to_dict(message))
                    assistant_payload["content"] = final_text
                    transcript.append(assistant_payload)
                    return final_text, audit_calls, self.last_tool_events
            audit = self._build_audit(
                transcript,
                content,
                tool_calls,
                round_index,
                getattr(response, "usage", None),
            )
            audit_calls.append(audit)
            self._llm_call_sink(audit)
            transcript.append(assistant_message_to_dict(message))

            for tool_call in tool_calls:
                message_row, event = execute_tool_call_with_event(
                    tool_call,
                    tool_map,
                    round_id=f"round-{round_index}",
                    max_result_chars=min(
                        budget.max_tool_result_chars,
                        max(0, budget.max_total_tool_result_chars - budget.used_tool_result_chars),
                    ),
                )
                self.last_tool_events.append(event)
                budget.used_tool_result_chars += len(message_row.get("content", ""))
                if event.status == "failed" and "truncated" in message_row["content"]:
                    budget.truncated_events += 1
                transcript.append(message_row)

        transcript.append({"role": "user", "content": TOOL_BUDGET_EXHAUSTED_PROMPT})
        kwargs = {}
        if merged_extra:
            kwargs["extra_body"] = merged_extra
        response = self.client.chat.completions.create(
            model=self.model,
            messages=deepcopy(transcript),
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            **kwargs,
        )
        message = response.choices[0].message
        content = _field(message, "content", None) or ""
        audit = self._build_audit(
            transcript,
            content,
            [],
            max_tool_rounds + 1,
            getattr(response, "usage", None),
        )
        audit_calls.append(audit)
        self._llm_call_sink(audit)
        self.last_budget_usage = budget
        return content, audit_calls, self.last_tool_events

    def _build_audit(
        self,
        transcript: list[dict[str, Any]],
        content: str,
        tool_calls: list[Any],
        round_index: int,
        usage: Any,
    ) -> LLMCall:
        prompt_text = transcript[-1].get("content", "") if transcript else ""
        return LLMCall(
            call_id=f"tool-{uuid.uuid4().hex[:12]}",
            agent=self.step_name,
            step_name=f"round-{round_index}",
            provider=self.provider,
            model=self.model,
            prompt_text=prompt_text,
            response_text=content,
            prompt_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            completion_tokens=getattr(usage, "completion_tokens", None) if usage else None,
            total_tokens=getattr(usage, "total_tokens", None) if usage else None,
            latency_ms=0,
            started_at=datetime.now(tz=UTC),
            completed_at=datetime.now(tz=UTC),
        )


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


__all__ = [
    "DEFAULT_MAX_TOOL_RESULT_CHARS",
    "DEFAULT_MAX_TOTAL_TOOL_RESULT_CHARS",
    "OpenAICompatibleToolLoop",
    "TOOL_BUDGET_EXHAUSTED_PROMPT",
    "ToolFunction",
    "ToolLoopError",
    "assistant_message_to_dict",
    "execute_tool_call",
    "execute_tool_call_with_event",
    "parse_model_response_to_tool_calls",
    "tool_call_to_dict",
    "tool_message",
]
