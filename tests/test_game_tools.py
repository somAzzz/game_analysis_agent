"""Tests for ``game_analysis_agent.game_tools``."""

from __future__ import annotations

from game_analysis_agent.game_tools import (
    TOOL_DEFINITIONS,
    build_probe,
    build_tool_map,
)
from game_analysis_agent.settings import Settings


def _settings() -> Settings:
    base = Settings()
    return Settings(
        **{**base.__dict__, "game_project_path": base.game_project_path.parent}
    )


def test_tool_definitions_have_unique_names() -> None:
    names = [d["function"]["name"] for d in TOOL_DEFINITIONS]
    assert len(names) == len(set(names))
    expected = {"get_state", "list_available_actions", "inspect_event", "step", "finish"}
    assert expected.issubset(set(names))


def test_build_probe_starts_at_week_zero() -> None:
    settings = _settings()
    probe = build_probe(settings)
    assert probe.current_week == 0
    assert probe.state is None
    assert probe.finished is False


def test_get_state_returns_initial_shape() -> None:
    settings = _settings()
    probe = build_probe(settings)
    payload = probe.get_state()
    assert payload["week"] == 0
    assert payload["finished"] is False
    assert payload["state"] == {}


def test_build_tool_map_returns_callable_map() -> None:
    probe = build_probe(_settings())
    tool_map = build_tool_map(probe)
    assert set(tool_map.keys()) == {
        "get_state",
        "list_available_actions",
        "inspect_event",
        "inspect_action",
        "step",
        "finish",
    }


def test_step_rejects_empty_actions() -> None:
    probe = build_probe(_settings())
    out = probe.step([])
    assert out.get("error")


def test_finish_marks_finished_and_returns_unknown_when_no_plan() -> None:
    probe = build_probe(_settings())
    out = probe.finish()
    assert out["finished"] is True
    assert "final_state" in out
