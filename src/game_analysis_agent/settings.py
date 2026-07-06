"""Process-wide configuration for game_analysis_agent.

Uses ``os.environ`` directly to avoid pulling in ``pydantic-settings`` as a
new dependency. A module-level ``lru_cache`` ensures a single ``Settings``
instance per process. Pattern borrowed from
``fintext_llm/src/config.py`` so a downstream maintainer sees the same shape
across both projects.
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value is not None else default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return int(raw)


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw) if raw else default


_SUPPORTED_PROVIDERS = frozenset({"vllm", "sglang", "deepseek"})
_PLACEHOLDER_TOKENS = frozenset({"", "empty", "dummy", "replace_me"})


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for game_analysis_agent components."""

    # ---- LLM provider selection ----------------------------------------
    llm_provider: str = field(
        default_factory=lambda: _env("LLM_PROVIDER", "vllm")
    )

    # ---- Local vLLM (default local backend) ----------------------------
    vllm_base_url: str = field(
        default_factory=lambda: _env("VLLM_BASE_URL", "http://localhost:8000/v1")
    )
    vllm_api_key: str = field(
        default_factory=lambda: _env("VLLM_API_KEY", "local-dev-token")
    )
    vllm_model: str = field(
        default_factory=lambda: _env("VLLM_MODEL", "/models/qwen3.6-nvfp4")
    )

    # ---- Local SGLang (alternative) ------------------------------------
    sglang_base_url: str = field(
        default_factory=lambda: _env("SGLANG_BASE_URL", "http://localhost:30000/v1")
    )
    sglang_api_key: str = field(
        default_factory=lambda: _env("SGLANG_API_KEY", "dummy")
    )
    sglang_model: str = field(
        default_factory=lambda: _env("SGLANG_MODEL", "Qwen/Qwen3.6-35B-A3B")
    )

    # ---- DeepSeek (cloud fallback) -------------------------------------
    deepseek_base_url: str = field(
        default_factory=lambda: _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    deepseek_model: str = field(
        default_factory=lambda: _env("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )
    deepseek_api_key: str | None = field(
        default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY")
    )

    # ---- Agent generation defaults --------------------------------------
    agent_temperature: float = field(
        default_factory=lambda: _env_float("AGENT_TEMPERATURE", 0.2)
    )
    agent_max_tokens: int = field(
        default_factory=lambda: _env_int("AGENT_MAX_TOKENS", 4096)
    )
    tool_max_rounds: int = field(
        default_factory=lambda: _env_int("TOOL_MAX_ROUNDS", 8)
    )

    # ---- Godot CLI + target game project -------------------------------
    godot_bin: str = field(
        default_factory=lambda: _env("GODOT_BIN", "godot4")
    )
    game_project_path: Path = field(
        default_factory=lambda: _env_path(
            "GAME_PROJECT_PATH", Path("/home/bo/projects/python/study-in-germany")
        )
    )

    # ---- Default Monte Carlo knobs -------------------------------------
    sim_runs: int = field(default_factory=lambda: _env_int("SIM_RUNS", 100))
    sim_policy: str = field(default_factory=lambda: _env("SIM_POLICY", "balanced"))
    sim_weeks: int = field(default_factory=lambda: _env_int("SIM_WEEKS", 20))
    sim_seed: int = field(default_factory=lambda: _env_int("SIM_SEED", 42))
    sim_difficulty: str = field(
        default_factory=lambda: _env("SIM_DIFFICULTY", "normal")
    )
    sim_scenario: str = field(
        default_factory=lambda: _env("SIM_SCENARIO", "default_first_semester")
    )

    # ---- Derived selectors ---------------------------------------------
    def provider(self) -> str:
        """Return the normalized provider name; defaults to ``vllm``."""
        return self.llm_provider if self.llm_provider in _SUPPORTED_PROVIDERS else "vllm"

    def base_url(self) -> str:
        """Return the OpenAI-compatible endpoint for the active provider."""
        return {
            "vllm": self.vllm_base_url,
            "sglang": self.sglang_base_url,
            "deepseek": self.deepseek_base_url,
        }[self.provider()]

    def api_key(self) -> str:
        """Return the bearer token for the active provider."""
        if self.provider() == "deepseek":
            key = self.deepseek_api_key
            return key if key else "missing"
        if self.provider() == "sglang":
            return self.sglang_api_key or "EMPTY"
        return self.vllm_api_key or "local-dev-token"

    def model(self) -> str:
        """Return the configured model id for the active provider."""
        return {
            "vllm": self.vllm_model,
            "sglang": self.sglang_model,
            "deepseek": self.deepseek_model,
        }[self.provider()]

    def deepseek_configured(self) -> bool:
        """Return ``True`` when DEEPSEEK is the active provider *and* a real key is set."""
        if self.provider() != "deepseek":
            return False
        key = self.deepseek_api_key
        if not key:
            return False
        lowered = key.strip().lower()
        if not lowered or lowered in _PLACEHOLDER_TOKENS:
            return False
        return not lowered.startswith("replace-me")


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached ``Settings`` instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the lru_cache around :func:`get_settings`. Tests use this."""
    get_settings.cache_clear()


__all__ = [
    "Settings",
    "get_settings",
    "reset_settings_cache",
]
