"""Tests for ``game_analysis_agent.tool_loop`` (OpenAICompatibleToolLoop)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from game_analysis_agent.tool_loop import (
    OpenAICompatibleToolLoop,
    execute_tool_call_with_event,
    tool_call_to_dict,
    tool_message,
)


def _tool_call(name: str, arguments: dict | str = "{}") -> SimpleNamespace:
    raw_args = json.dumps(arguments) if isinstance(arguments, dict) else arguments
    return SimpleNamespace(
        id="call-1",
        type="function",
        function=SimpleNamespace(name=name, arguments=raw_args),
    )


def _response(content: str, tool_calls=None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=tool_calls)
            )
        ],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
    )


def test_executes_registered_tool_and_finishes() -> None:
    sdk = MagicMock()
    sdk.chat.completions.create.side_effect = [
        _response("", [_tool_call("lookup", {"key": "a"})]),
        _response("result-a", None),
    ]
    calls: list[dict] = []

    def lookup(key: str) -> dict:
        calls.append({"key": key})
        return {"key": key, "value": 42}

    loop = OpenAICompatibleToolLoop(
        client=sdk,
        model="local",
        provider="vllm",
        temperature=0.1,
        max_tokens=256,
    )
    text, audit, events = loop.complete(
        "Please look up something.",
        tools=[{"type": "function", "function": {"name": "lookup"}}],
        tool_map={"lookup": lookup},
    )
    assert text == "result-a"
    assert calls == [{"key": "a"}]
    assert len(audit) == 2
    assert len(events) == 1
    assert events[0].tool_name == "lookup"


def test_no_tools_emits_validation_error() -> None:
    sdk = MagicMock()
    loop = OpenAICompatibleToolLoop(
        client=sdk,
        model="local",
        provider="vllm",
        temperature=0.1,
        max_tokens=256,
    )
    with pytest.raises(ValueError):
        loop.complete("prompt", tools=[], tool_map={})


def test_unknown_tool_returns_error_message() -> None:
    sdk = MagicMock()
    sdk.chat.completions.create.side_effect = [
        _response("", [_tool_call("ghost", {"x": 1})]),
        _response("done", None),
    ]

    def real_tool() -> str:
        return "ok"

    loop = OpenAICompatibleToolLoop(
        client=sdk,
        model="local",
        provider="vllm",
        temperature=0.1,
        max_tokens=256,
    )
    text, _audit, events = loop.complete(
        "prompt",
        tools=[{"type": "function", "function": {"name": "ghost"}}],
        tool_map={"real_tool": real_tool},
    )
    assert text == "done"
    assert events[0].status == "failed"
    assert "unknown tool" in events[0].error


def test_execute_tool_call_with_event_truncates_long_result() -> None:
    tc = _tool_call("echo", {"v": "y"})
    message, event = execute_tool_call_with_event(
        tc, {"echo": lambda v: "x" * 50000}, round_id="r0", max_result_chars=1024
    )
    assert "truncated" in message["content"]
    assert event.status == "success"
    assert len(message["content"]) <= 1024


def test_tool_message_handles_string_result() -> None:
    msg = tool_message(_tool_call("echo"), "hello", max_result_chars=128)
    assert msg["role"] == "tool"
    assert msg["content"] == "hello"
    assert msg["tool_call_id"] == "call-1"


def test_tool_call_to_dict_uses_function_attrs() -> None:
    tc = _tool_call("foo", {"a": 1})
    payload = tool_call_to_dict(tc)
    assert payload["function"]["name"] == "foo"
    assert payload["function"]["arguments"] == '{"a": 1}'
