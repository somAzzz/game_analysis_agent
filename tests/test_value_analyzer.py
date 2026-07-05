"""Tests for ``game_analysis_agent.value_analyzer``."""

from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.value_analyzer import analyze_and_write, analyze_values


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(header))
        handle.write("\n")
        for row in rows:
            handle.write(",".join(str(v) for v in row))
            handle.write("\n")


def test_dominant_action_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "action_pick_rates.csv",
        ["policy", "action_id", "count", "rate_per_run"],
        [
            ["balanced", "study_library", 90, 0.90],
            ["balanced", "rest_at_home", 50, 0.50],
        ],
    )
    findings = analyze_values(action_csv=tmp_path / "action_pick_rates.csv")
    dominant = [f for f in findings if f.scope == "action" and "study_library" in f.target_id]
    assert dominant
    assert dominant[0].severity == "warning"


def test_dead_action_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "action_pick_rates.csv",
        ["policy", "action_id", "count", "rate_per_run"],
        [
            ["balanced", "study_library", 50, 0.50],
            ["balanced", "obscure_action", 1, 0.01],
        ],
    )
    findings = analyze_values(action_csv=tmp_path / "action_pick_rates.csv")
    dead = [f for f in findings if f.scope == "action" and "obscure_action" in f.target_id]
    assert dead
    assert dead[0].severity == "info"


def test_dominant_choice_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "choice_pick_rates.csv",
        ["policy", "event_id", "choice_id", "count", "rate_per_event"],
        [
            ["balanced", "first_lecture", "first_lecture.choice_01_ask_question", 100, 0.90],
            ["balanced", "first_lecture", "first_lecture.choice_02_stay_silent", 10, 0.10],
        ],
    )
    findings = analyze_values(choice_csv=tmp_path / "choice_pick_rates.csv")
    dom = [f for f in findings if f.scope == "choice" and "first_lecture" in f.target_id]
    assert dom
    assert dom[0].finding_id.startswith("choice_dominant-")


def test_rare_event_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "event_trigger_rates.csv",
        ["policy", "event_id", "count", "rate_per_run"],
        [
            ["balanced", "first_lecture", 100, 1.00],
            ["balanced", "obscure_event", 1, 0.001],
        ],
    )
    findings = analyze_values(event_csv=tmp_path / "event_trigger_rates.csv")
    rare = [f for f in findings if f.scope == "event" and "obscure_event" in f.target_id]
    assert rare
    assert rare[0].severity == "info"


def test_ending_dominance_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "ending_distribution.csv",
        ["policy", "ending_id", "count", "rate"],
        [
            ["balanced", "academic_success", 95, 0.95],
            ["balanced", "burnout", 5, 0.05],
        ],
    )
    findings = analyze_values(ending_csv=tmp_path / "ending_distribution.csv")
    ending = [f for f in findings if f.scope == "ending"]
    assert ending


def test_analyze_and_write_persists_value_report(tmp_path) -> None:
    _write_csv(
        tmp_path / "action_pick_rates.csv",
        ["policy", "action_id", "count", "rate_per_run"],
        [["balanced", "a", 100, 0.95]],
    )
    _write_csv(
        tmp_path / "event_trigger_rates.csv",
        ["policy", "event_id", "count", "rate_per_run"],
        [["balanced", "x", 100, 1.0]],
    )
    _write_csv(
        tmp_path / "choice_pick_rates.csv",
        ["policy", "event_id", "choice_id", "count", "rate_per_event"],
        [["balanced", "x", "x.choice_01", 100, 1.0]],
    )
    _write_csv(
        tmp_path / "ending_distribution.csv",
        ["policy", "ending_id", "count", "rate"],
        [["balanced", "y", 100, 1.0]],
    )
    findings = analyze_and_write(tmp_path)
    assert isinstance(findings, list)
    assert (tmp_path / "value_report.json").exists()
    payload = json.loads((tmp_path / "value_report.json").read_text(encoding="utf-8"))
    assert payload["finding_count"] == len(findings)
