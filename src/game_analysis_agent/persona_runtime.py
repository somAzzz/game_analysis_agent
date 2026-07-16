"""Preflight selection and hard runtime controls for persona providers."""

from __future__ import annotations

import os
import re
import threading
from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from .persona_gateway import (
    PersonaCallMetadata,
    PersonaDecisionGateway,
    PersonaDecisionRequest,
    PersonaDecisionResult,
    PersonaErrorCategory,
    PersonaEventChoiceRequest,
    PersonaEventChoiceResult,
    PersonaProvider,
    PersonaProviderError,
    PersonaProviderMode,
    PersonaResultStatus,
    PersonaUsage,
)


class PersonaRuntimeConfigurationError(ValueError):
    """Raised before a campaign when provider or limit settings are invalid."""


class PersonaProviderChoice(StrEnum):
    AUTO = "auto"
    REPLAY = "replay"
    OPENAI = "openai"
    VLLM = "vllm"
    SGLANG = "sglang"
    DEEPSEEK = "deepseek"


class PersonaRuntimeLimits(BaseModel):
    """Fail-closed caps applied to every Judge Mode campaign."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_runs: int = Field(default=12, ge=1, le=100)
    max_weeks: int = Field(default=20, ge=1, le=52)
    max_concurrency: int = Field(default=4, ge=1, le=16)
    max_calls: int = Field(default=600, ge=1, le=10_000)
    max_retries: int = Field(default=1, ge=0, le=3)
    retry_backoff_s: float = Field(default=0.5, ge=0, le=5)

    def validate_campaign(self, *, runs: int, weeks: int, concurrency: int) -> None:
        violations = []
        if runs < 1 or runs > self.max_runs:
            violations.append(f"runs must be between 1 and {self.max_runs}")
        if weeks < 1 or weeks > self.max_weeks:
            violations.append(f"weeks must be between 1 and {self.max_weeks}")
        if concurrency < 1 or concurrency > self.max_concurrency:
            violations.append(
                f"concurrency must be between 1 and {self.max_concurrency}"
            )
        if violations:
            raise PersonaRuntimeConfigurationError("; ".join(violations))


class PersonaProviderSelection(BaseModel):
    """Secret-free decision made once, before campaign execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested: PersonaProviderChoice
    selected: PersonaProvider
    mode: PersonaProviderMode
    reason: str


class PersonaRuntimeSettings(BaseModel):
    """Validated server-side settings for Judge Mode persona execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: PersonaProviderChoice = PersonaProviderChoice.AUTO
    openai_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    deepseek_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    openai_model: str = Field(default="gpt-5.6-luna", min_length=1, max_length=120)
    replay_manifest: str = Field(
        default="config/build_week_2026_replay.json", min_length=1, max_length=500
    )
    limits: PersonaRuntimeLimits = Field(default_factory=PersonaRuntimeLimits)

    @classmethod
    def from_env(
        cls, environ: Mapping[str, str] | None = None
    ) -> PersonaRuntimeSettings:
        source = os.environ if environ is None else environ
        return cls(
            provider=source.get("PERSONA_PROVIDER", "auto"),
            openai_api_key=source.get("OPENAI_API_KEY"),
            deepseek_api_key=source.get("DEEPSEEK_API_KEY"),
            openai_model=source.get("OPENAI_PERSONA_MODEL", "gpt-5.6-luna"),
            replay_manifest=source.get(
                "PERSONA_REPLAY_MANIFEST", "config/build_week_2026_replay.json"
            ),
            limits=PersonaRuntimeLimits(
                max_runs=_env_int(source, "PERSONA_MAX_RUNS", 12),
                max_weeks=_env_int(source, "PERSONA_MAX_WEEKS", 20),
                max_concurrency=_env_int(source, "PERSONA_MAX_CONCURRENCY", 4),
                max_calls=_env_int(source, "PERSONA_MAX_CALLS", 600),
                max_retries=_env_int(source, "PERSONA_MAX_RETRIES", 1),
                retry_backoff_s=_env_float(
                    source, "PERSONA_RETRY_BACKOFF_SECONDS", 0.5
                ),
            ),
        )

    def resolve_provider(self) -> PersonaProviderSelection:
        """Resolve AUTO exactly once; never use this as an error fallback."""

        requested = self.provider
        if requested == PersonaProviderChoice.AUTO:
            if _usable_secret(self.openai_api_key):
                return PersonaProviderSelection(
                    requested=requested,
                    selected=PersonaProvider.OPENAI,
                    mode=PersonaProviderMode.LIVE,
                    reason="OPENAI_API_KEY was configured before execution",
                )
            return PersonaProviderSelection(
                requested=requested,
                selected=PersonaProvider.REPLAY,
                mode=PersonaProviderMode.REPLAY,
                reason="no OpenAI key; Replay selected before execution",
            )
        provider = PersonaProvider(requested.value)
        if provider == PersonaProvider.OPENAI and not _usable_secret(self.openai_api_key):
            raise PersonaRuntimeConfigurationError(
                "PERSONA_PROVIDER=openai requires a non-placeholder OPENAI_API_KEY"
            )
        if provider == PersonaProvider.DEEPSEEK and not _usable_secret(
            self.deepseek_api_key
        ):
            raise PersonaRuntimeConfigurationError(
                "PERSONA_PROVIDER=deepseek requires a non-placeholder DEEPSEEK_API_KEY"
            )
        mode = (
            PersonaProviderMode.REPLAY
            if provider == PersonaProvider.REPLAY
            else PersonaProviderMode.LIVE
            if provider in {PersonaProvider.OPENAI, PersonaProvider.DEEPSEEK}
            else PersonaProviderMode.LOCAL
        )
        return PersonaProviderSelection(
            requested=requested,
            selected=provider,
            mode=mode,
            reason="provider explicitly selected before execution",
        )

    @model_validator(mode="after")
    def _manifest_is_relative(self) -> PersonaRuntimeSettings:
        normalized = self.replay_manifest.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("replay_manifest must be a safe project-relative path")
        return self


class PersonaCancellationToken:
    """Thread-safe cooperative cancellation shared by campaign workers."""

    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    def wait(self, timeout_s: float) -> bool:
        return self._event.wait(timeout_s)


class GovernedPersonaGateway:
    """Apply call, concurrency, retry, and cancellation policy to one provider."""

    def __init__(
        self,
        gateway: PersonaDecisionGateway,
        *,
        limits: PersonaRuntimeLimits,
        cancellation: PersonaCancellationToken | None = None,
    ) -> None:
        self.gateway = gateway
        self.provider = gateway.provider
        self.mode = gateway.mode
        self.limits = limits
        self.cancellation = cancellation or PersonaCancellationToken()
        self._semaphore = threading.BoundedSemaphore(limits.max_concurrency)
        self._budget_lock = threading.Lock()
        self._calls_used = 0

    @property
    def calls_used(self) -> int:
        with self._budget_lock:
            return self._calls_used

    def validate_campaign(self, *, runs: int, weeks: int, concurrency: int) -> None:
        self.limits.validate_campaign(runs=runs, weeks=weeks, concurrency=concurrency)

    def decide(self, request: PersonaDecisionRequest) -> PersonaDecisionResult:
        result = self._run(lambda: self.gateway.decide(request))
        if result is None:
            return PersonaDecisionResult(
                status=PersonaResultStatus.CANCELLED,
                request_fingerprint=request.fingerprint(),
                metadata=self._empty_metadata(),
                error=_runtime_error(PersonaErrorCategory.CANCELLED, "campaign cancelled"),
            )
        if isinstance(result, PersonaDecisionResult):
            return result
        return PersonaDecisionResult(
            status=PersonaResultStatus.FAILED,
            request_fingerprint=request.fingerprint(),
            metadata=self._empty_metadata(),
            error=_runtime_error(
                PersonaErrorCategory.BUDGET_EXHAUSTED, "persona call budget exhausted"
            ),
        )

    def choose_event(
        self, request: PersonaEventChoiceRequest
    ) -> PersonaEventChoiceResult:
        result = self._run(lambda: self.gateway.choose_event(request))
        if result is None:
            return PersonaEventChoiceResult(
                status=PersonaResultStatus.CANCELLED,
                request_fingerprint=request.fingerprint(),
                metadata=self._empty_metadata(),
                error=_runtime_error(PersonaErrorCategory.CANCELLED, "campaign cancelled"),
            )
        if isinstance(result, PersonaEventChoiceResult):
            return result
        return PersonaEventChoiceResult(
            status=PersonaResultStatus.FAILED,
            request_fingerprint=request.fingerprint(),
            metadata=self._empty_metadata(),
            error=_runtime_error(
                PersonaErrorCategory.BUDGET_EXHAUSTED, "persona call budget exhausted"
            ),
        )

    def _run(
        self,
        operation,
    ) -> PersonaDecisionResult | PersonaEventChoiceResult | bool | None:
        if self.cancellation.cancelled:
            return None
        while not self._semaphore.acquire(timeout=0.05):
            if self.cancellation.cancelled:
                return None
        try:
            total_attempts = 0
            total_latency_ms = 0
            total_usage = PersonaUsage(input_tokens=0, output_tokens=0, total_tokens=0)
            for retry_index in range(self.limits.max_retries + 1):
                if self.cancellation.cancelled:
                    return None
                if not self._claim_call():
                    return False
                result = operation()
                total_attempts += result.metadata.attempt_count
                total_latency_ms += result.metadata.latency_ms
                total_usage = _sum_usage(total_usage, result.metadata.usage)
                result = _with_totals(
                    result,
                    attempts=total_attempts,
                    latency_ms=total_latency_ms,
                    usage=total_usage,
                )
                if result.status == PersonaResultStatus.COMPLETED:
                    return result
                if result.error is None or not result.error.retryable:
                    return result
                if retry_index == self.limits.max_retries:
                    return result
                backoff = self.limits.retry_backoff_s * (2**retry_index)
                if self.cancellation.wait(backoff):
                    return None
            raise AssertionError("bounded retry loop returned no result")
        finally:
            self._semaphore.release()

    def _claim_call(self) -> bool:
        with self._budget_lock:
            if self._calls_used >= self.limits.max_calls:
                return False
            self._calls_used += 1
            return True

    def _empty_metadata(self) -> PersonaCallMetadata:
        return PersonaCallMetadata(
            provider=self.provider,
            mode=self.mode,
            model=str(getattr(self.gateway, "model", "")),
        )


def redact_sensitive_text(value: object) -> str:
    """Remove common API-key/header forms before text reaches reports or logs."""

    text = str(value)
    text = re.sub(r"sk-[A-Za-z0-9_-]+", "<redacted>", text)
    text = re.sub(
        r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+",
        r"\1<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)((?:api[_-]?key|token)\s*[:=]\s*)[^\s,;]+",
        r"\1<redacted>",
        text,
    )
    return text[:500]


def _usable_secret(value: SecretStr | None) -> bool:
    if value is None:
        return False
    raw = value.get_secret_value().strip()
    lowered = raw.lower()
    return bool(raw) and lowered not in {
        "empty",
        "dummy",
        "replace_me",
        "replace-me",
        "missing",
    }


def _env_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name)
    return default if raw is None else int(raw)


def _env_float(source: Mapping[str, str], name: str, default: float) -> float:
    raw = source.get(name)
    return default if raw is None else float(raw)


def _runtime_error(
    category: PersonaErrorCategory, message: str
) -> PersonaProviderError:
    return PersonaProviderError(category=category, message=message, retryable=False)


def _sum_usage(left: PersonaUsage, right: PersonaUsage) -> PersonaUsage:
    return PersonaUsage(
        input_tokens=_sum_optional(left.input_tokens, right.input_tokens),
        output_tokens=_sum_optional(left.output_tokens, right.output_tokens),
        total_tokens=_sum_optional(left.total_tokens, right.total_tokens),
    )


def _sum_optional(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)


def _with_totals(
    result: PersonaDecisionResult | PersonaEventChoiceResult,
    *,
    attempts: int,
    latency_ms: int,
    usage: PersonaUsage,
) -> PersonaDecisionResult | PersonaEventChoiceResult:
    metadata = result.metadata.model_copy(
        update={
            "attempt_count": attempts,
            "latency_ms": latency_ms,
            "usage": usage,
        }
    )
    return result.model_copy(update={"metadata": metadata})


__all__ = [
    "GovernedPersonaGateway",
    "PersonaCancellationToken",
    "PersonaProviderChoice",
    "PersonaProviderSelection",
    "PersonaRuntimeConfigurationError",
    "PersonaRuntimeLimits",
    "PersonaRuntimeSettings",
    "redact_sensitive_text",
]
