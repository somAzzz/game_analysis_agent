"""OpenAI-compatible LLM client with provider switching and call auditing.

Pattern borrowed from ``fintext_llm/src/llm/client.py``. Differences:

* Three providers are supported (``vllm`` / ``sglang`` / ``deepseek``),
  selected via ``Settings.llm_provider``. Local Qwen backends attach
  ``extra_body.chat_template_kwargs.enable_thinking=False`` so reasoning
  models do not pollute the chat transcript with thinking text.
* The audit row is :class:`game_analysis_agent.schemas.LLMCall` (Pydantic),
  pushed through a sink that downstream consumers can swap.

The legacy :class:`LocalLLMClient` is kept around as a thin wrapper so
existing callers (``tools/run_agent.py`` etc.) continue to compile
during the migration.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from openai import OpenAI

from game_analysis_agent.schemas import LLMCall
from game_analysis_agent.settings import Settings, get_settings

NoOpSink = Callable[[LLMCall], None]


def _no_sink(_call: LLMCall) -> None:
    """Default no-op sink used when no caller-supplied sink is provided."""


def _now_utc() -> datetime:
    return datetime.now(UTC)


class LocalLLMClient:
    """OpenAI-compatible client used by every agent in this project.

    Provider (and the matching ``base_url`` / ``api_key`` / ``model``) is
    resolved from the active :class:`Settings` at construction time.
    Override via the ``provider`` / ``base_url`` / ``api_key`` / ``model``
    keyword arguments when calling :meth:`from_settings`.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        llm_call_sink: NoOpSink | None = None,
        provider: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float = 600.0,
    ) -> None:
        self.settings = settings
        self.provider = provider or settings.provider()
        self.base_url = (base_url or settings.base_url()).rstrip("/")
        self.api_key = api_key or settings.api_key()
        self.model = model or settings.model()
        self.timeout_s = timeout_s
        self._llm_call_sink: NoOpSink = llm_call_sink or _no_sink
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=timeout_s,
        )

    # --- factory helpers --------------------------------------------------

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        llm_call_sink: NoOpSink | None = None,
    ) -> LocalLLMClient:
        return cls(settings or get_settings(), llm_call_sink=llm_call_sink)

    # --- core chat -------------------------------------------------------

    def _extra_body(self) -> dict[str, Any] | None:
        """Return provider-specific request kwargs.

        Locally served Qwen reasoning models otherwise prepend a long thinking
        transcript by default, which is undesirable for tool-calling /
        structured-output flows.
        """
        if self.provider in {"vllm", "sglang"}:
            return {"chat_template_kwargs": {"enable_thinking": False}}
        return None

    def _chat(
        self,
        messages: list[dict[str, str]],
        *,
        agent: str,
        step_name: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        emit_call: bool = True,
    ) -> tuple[str, LLMCall]:
        started = _now_utc()
        call_id = f"llm-{uuid.uuid4().hex[:12]}"
        prompt_text = messages[-1]["content"] if messages else ""
        request_kwargs: dict[str, Any] = {}
        extra = self._extra_body()
        if extra:
            request_kwargs["extra_body"] = extra
        try:
            t0 = time.perf_counter()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.settings.agent_temperature,
                max_tokens=max_tokens if max_tokens is not None else self.settings.agent_max_tokens,
                **request_kwargs,
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
        except Exception as exc:
            completed = _now_utc()
            call = LLMCall(
                call_id=call_id,
                agent=agent,
                step_name=step_name,
                provider=self.provider,
                model=self.model,
                prompt_text=prompt_text,
                response_text="",
                latency_ms=int((completed - started).total_seconds() * 1000),
                error=f"{type(exc).__name__}: {exc}",
                started_at=started,
                completed_at=completed,
            )
            if emit_call:
                self._llm_call_sink(call)
            raise

        try:
            content = response.choices[0].message.content or ""
        except (AttributeError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected LLM response: {response!r}") from exc
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None
        completed = _now_utc()
        call = LLMCall(
            call_id=call_id,
            agent=agent,
            step_name=step_name,
            provider=self.provider,
            model=self.model,
            prompt_text=prompt_text,
            response_text=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            started_at=started,
            completed_at=completed,
        )
        if emit_call:
            self._llm_call_sink(call)
        return content, call

    # --- public API ------------------------------------------------------

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        agent: str = "default",
        step_name: str = "complete",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """One-shot chat completion that returns the raw response string."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        content, _call = self._chat(
            messages,
            agent=agent,
            step_name=step_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return content

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        agent: str = "default",
        step_name: str = "chat",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> tuple[str, LLMCall]:
        """Chat with an already-built message list; returns ``(text, audit)``."""
        return self._chat(
            messages,
            agent=agent,
            step_name=step_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )


# ---------------------------------------------------------------------------
# Legacy compatibility shim
# ---------------------------------------------------------------------------
#
# The original ``LocalLLMClient`` exposed ``LLMConfig`` + a ``chat(system,
# user)`` method that called urllib directly. The new client above is the
# primary implementation; the helpers below keep older callers compiling.


class LLMConfig:
    """Backwards-compatible config dataclass mirroring the pre-v0.2 shape."""

    base_url: str
    api_key: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 4096

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> LLMConfig:
        s = get_settings()
        return cls(
            base_url=s.base_url(),
            api_key=s.api_key(),
            model=s.model(),
            temperature=s.agent_temperature,
            max_tokens=s.agent_max_tokens,
        )


class LegacyLocalLLMClient:
    """Minimal urllib-based client retained for callers that have not migrated.

    Used by :func:`tools.run_agent` only as a safety net; the primary code
    path goes through :class:`LocalLLMClient` (which uses the OpenAI SDK).
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach LLM endpoint {self.config.base_url}. "
                "Start it with tools/run_vllm_qwen.sh or update VLLM_BASE_URL."
            ) from exc
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected LLM response: {data}") from exc


__all__ = [
    "LLMConfig",
    "LegacyLocalLLMClient",
    "LocalLLMClient",
    "NoOpSink",
    "_no_sink",
]
