"""Tests for the rewritten :mod:`game_analysis_agent.llm_client`."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from game_analysis_agent.llm_client import LocalLLMClient
from game_analysis_agent.schemas import LLMCall
from game_analysis_agent.settings import Settings


class _FakeCompletions:
    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self.response


def _settings(provider: str = "vllm", **overrides) -> Settings:
    base = Settings()
    overrides_dict = {**base.__dict__, "llm_provider": provider, **overrides}
    return Settings(**overrides_dict)


def test_complete_returns_text_and_emits_audit() -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
        usage=SimpleNamespace(prompt_tokens=2, completion_tokens=3, total_tokens=5),
    )
    sdk = MagicMock()
    sdk.chat.completions.create.return_value = response
    audit_rows: list[LLMCall] = []

    client = LocalLLMClient(
        _settings(),
        llm_call_sink=audit_rows.append,
        provider="vllm",
        base_url="http://localhost:1234/v1",
        api_key="k",
        model="m",
    )
    client.client = sdk  # rebind so the fake SDK is used

    text = client.complete("hi", system="sys", agent="balance", step_name="balance")
    assert text == "hello"
    assert len(audit_rows) == 1
    assert audit_rows[0].prompt_text == "hi"


def test_sglang_provider_attaches_thinking_disable() -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
        usage=None,
    )
    completions = _FakeCompletions(response)

    sdk = MagicMock()
    sdk.chat.completions.create = completions.create
    client = LocalLLMClient(
        _settings(),
        provider="sglang",
        base_url="http://localhost:1234/v1",
        api_key="k",
        model="m",
    )
    client.client = sdk
    client.complete("hi", system="sys", agent="x")
    assert completions.calls, "expected at least one chat completion"
    extra = completions.calls[0].get("extra_body", {})
    assert extra.get("chat_template_kwargs", {}).get("enable_thinking") is False


def test_deepseek_provider_does_not_attach_thinking_disable() -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
        usage=None,
    )
    completions = _FakeCompletions(response)

    sdk = MagicMock()
    sdk.chat.completions.create = completions.create
    client = LocalLLMClient(
        _settings(),
        provider="deepseek",
        base_url="http://localhost:1234/v1",
        api_key="k",
        model="m",
    )
    client.client = sdk
    client.complete("hi", system="sys", agent="x")
    assert completions.calls, "expected at least one chat completion"
    assert "extra_body" not in completions.calls[0]


def test_chat_returns_audit_row() -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="reply"))],
        usage=None,
    )
    sdk = MagicMock()
    sdk.chat.completions.create.return_value = response
    audit_rows: list[LLMCall] = []
    client = LocalLLMClient(
        _settings(),
        llm_call_sink=audit_rows.append,
        provider="vllm",
        base_url="http://x",
        api_key="k",
        model="m",
    )
    client.client = sdk
    text, audit = client.chat(
        [{"role": "user", "content": "ping"}],
        agent="balance",
        step_name="balance",
    )
    assert text == "reply"
    assert audit.provider == "vllm"
