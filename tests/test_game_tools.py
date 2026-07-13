"""Tests for ``game_analysis_agent.game_tools``."""

from __future__ import annotations

import subprocess
from pathlib import Path

import game_analysis_agent.game_tools as game_tools
from game_analysis_agent.game_tools import (
    TOOL_DEFINITIONS,
    build_probe,
    build_tool_map,
)
from game_analysis_agent.settings import Settings


def _settings() -> Settings:
    base = Settings()
    return Settings(
        **{
            **base.__dict__,
            # Keep these unit tests independent from a host or Docker Godot runtime.
            "godot_bin": "/definitely/missing/godot-for-unit-test",
            "game_project_path": base.game_project_path.parent,
        }
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


def test_probe_propagates_risk_guidance_from_snapshot(monkeypatch) -> None:
    guidance = {
        "contract_version": "1.0",
        "source": "game_risk_evaluator",
        "evaluator": "RiskEvaluator.get_top_risks",
        "generated_for_week": 0,
        "top_risks": [],
    }

    def fake_run_one_step(*args, **kwargs):
        return {
            "current_state": {"week": 0, "money": 1000},
            "next_available_actions": [],
            "triggered_event_id": "",
            "event_choices": [],
            "risk_guidance": guidance,
        }

    monkeypatch.setattr(game_tools, "_run_one_step", fake_run_one_step)
    probe = build_probe(_settings())

    payload = probe.get_state()

    assert payload["risk_guidance"] == guidance


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


def test_run_one_step_validates_contract_and_cleans_temp_files(
    tmp_path, monkeypatch
) -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "contracts"
        / "interactive_probe_v1.json"
    )

    def invoke(_settings, *, script, extra_args):  # noqa: ANN001
        assert script == "res://scripts/tools/RunInteractiveProbe.gd"
        output = Path(
            next(arg for arg in extra_args if arg.startswith("--out=")).removeprefix(
                "--out="
            )
        )
        output.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
        return subprocess.CompletedProcess([], 0, "", "")

    settings = Settings(
        **{
            **Settings().__dict__,
            "game_project_path": tmp_path,
        }
    )
    monkeypatch.setattr(game_tools, "_invoke_godot", invoke)

    payload = game_tools._run_one_step(settings, [])

    assert payload["risk_guidance"]["source"] == "game_risk_evaluator"
    assert not list((tmp_path / "reports").glob("_plan_*.json"))
    assert not list((tmp_path / "reports").glob("_trace_*.json"))
