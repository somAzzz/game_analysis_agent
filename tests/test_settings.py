"""Tests for ``game_analysis_agent.settings``."""

from __future__ import annotations

import os

import pytest

from game_analysis_agent.settings import Settings, get_settings, reset_settings_cache


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    reset_settings_cache()
    yield
    reset_settings_cache()


def _clear_env() -> None:
    for key in (
        "LLM_PROVIDER",
        "VLLM_BASE_URL",
        "VLLM_API_KEY",
        "VLLM_MODEL",
        "SGLANG_BASE_URL",
        "SGLANG_API_KEY",
        "SGLANG_MODEL",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_API_KEY",
        "AGENT_TEMPERATURE",
        "AGENT_MAX_TOKENS",
        "TOOL_MAX_ROUNDS",
        "GODOT_BIN",
        "GAME_PROJECT_PATH",
        "SIM_RUNS",
        "SIM_POLICY",
        "SIM_WEEKS",
        "SIM_SEED",
        "SIM_DIFFICULTY",
    ):
        os.environ.pop(key, None)


class TestDefaults:
    def test_default_provider_is_vllm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_env()
        s = Settings()
        assert s.llm_provider == "vllm"
        assert s.provider() == "vllm"
        assert s.base_url().startswith("http://localhost:")
        assert s.model() == s.vllm_model

    def test_default_sim_difficulty_is_normal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_env()
        s = Settings()
        assert s.sim_difficulty == "normal"
        assert s.sim_runs == 100
        assert s.sim_weeks == 20

    def test_unknown_provider_falls_back_to_vllm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_env()
        os.environ["LLM_PROVIDER"] = "oss-117"
        s = Settings()
        assert s.provider() == "vllm"


class TestSelectors:
    def test_provider_selects_correct_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_env()
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "real-key")
        s = Settings()
        assert s.provider() == "deepseek"
        assert s.base_url() == s.deepseek_base_url
        assert s.model() == s.deepseek_model
        assert s.deepseek_configured() is True

    def test_deepseek_rejects_placeholder_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_env()
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "REPLACE_ME")
        s = Settings()
        assert s.provider() == "deepseek"
        assert s.deepseek_configured() is False


class TestCache:
    def test_get_settings_is_cached(self) -> None:
        first = get_settings()
        second = get_settings()
        assert first is second

    def test_reset_clears_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s1 = get_settings()
        monkeypatch.setenv("LLM_PROVIDER", "sglang")
        reset_settings_cache()
        s2 = get_settings()
        assert s1 is not s2
        assert s2.provider() == "sglang"
