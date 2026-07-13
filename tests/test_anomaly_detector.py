"""Tests for ``game_analysis_agent.anomaly_detector``."""

from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.anomaly_detector import detect_anomalies, write_anomalies_jsonl

FIXTURE = Path(__file__).parent / "fixtures" / "anomaly_runs.jsonl"


def _read_fixture() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_detects_negative_money() -> None:
    runs = _read_fixture()
    anomalies = detect_anomalies(runs)
    kinds = {a.kind for a in anomalies}
    assert "negative_money" in kinds


def test_detects_stress_overflow() -> None:
    runs = _read_fixture()
    anomalies = detect_anomalies(runs)
    overflow = [a for a in anomalies if a.kind == "stat_overflow"]
    assert overflow, "Expected at least one stat_overflow anomaly"
    assert any(a.evidence.get("metric") == "stress" for a in overflow)


def test_detects_non_repeatable_event_repeated() -> None:
    runs = _read_fixture()
    anomalies = detect_anomalies(runs)
    repeated = [a for a in anomalies if a.kind == "non_repeatable_event_repeated"]
    assert repeated, "Expected non_repeatable_event_repeated for library_day"


def test_detects_dead_state() -> None:
    runs = _read_fixture()
    anomalies = detect_anomalies(runs)
    dead = [a for a in anomalies if a.kind == "dead_state"]
    assert dead, "Expected dead_state for the long flat run"


def test_detects_pipeline_stalled() -> None:
    runs = _read_fixture()
    anomalies = detect_anomalies(runs)
    kinds = {a.kind for a in anomalies}
    assert "pipeline_stalled" in kinds


def test_write_anomalies_jsonl_round_trip(tmp_path) -> None:
    runs = _read_fixture()
    anomalies = detect_anomalies(runs)
    out = tmp_path / "anomalies.jsonl"
    count = write_anomalies_jsonl(anomalies, out)
    assert count == len(anomalies)
    assert out.exists()
    raw = [
        json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(raw) == count


def test_detects_no_anomalies_for_clean_run() -> None:
    runs = [
        {
            "run_id": 0,
            "policy": "balanced",
            "max_weeks": 20,
            "final_ending_id": "academic_success",
            "weekly_log": [
                {
                    "week": 1,
                    "selected_action_ids": ["sleep_recover"],
                    "triggered_event_id": "",
                    "after_state": {
                        "week": 1,
                        "money": 1000,
                        "energy": 100,
                        "stress": 20,
                        "loneliness": 30,
                        "hunger": 20,
                        "academic_progress": 30,
                        "exam_readiness": 25,
                        "language": 25,
                        "social": 15,
                        "visa_progress": 30,
                        "career_progress": 5,
                    },
                }
            ],
        }
    ]
    anomalies = detect_anomalies(runs)
    critical = [a for a in anomalies if a.severity in {"critical", "error"}]
    assert critical == []


def test_anomaly_evidence_contains_replay_context() -> None:
    anomalies = detect_anomalies(
        [
            {
                "run_id": 7,
                "seed": 99,
                "policy": "work",
                "difficulty": "realistic",
                "scenario": "low_money_start",
                "max_weeks": 20,
                "final_ending_id": "stable_start",
                "weekly_log": [
                    {
                        "week": 3,
                        "selected_action_ids": ["part_time_job"],
                        "triggered_event_id": "rent_pressure",
                        "event_choice_id": "rent_pressure.choice_01",
                        "after_state": {"week": 3, "money": -5},
                    }
                ],
            }
        ]
    )

    replay = anomalies[0].evidence["replay"]
    assert replay["seed"] == 99
    assert replay["policy"] == "work"
    assert replay["scenario"] == "low_money_start"
    assert replay["actions"] == ["part_time_job"]


def test_cost_check_uses_before_state_instead_of_after_state() -> None:
    run = {
        "run_id": 1,
        "policy": "balanced",
        "max_weeks": 1,
        "final_ending_id": "stable_start",
        "weekly_log": [
            {
                "week": 1,
                "selected_action_ids": ["language_course"],
                "before_state": {"week": 0, "money": 500},
                "after_state": {"week": 1, "money": 197},
                "action_effects": [
                    {"action_id": "language_course", "effects": {"money": -420}}
                ],
            }
        ],
    }

    anomalies = detect_anomalies([run])

    assert not [a for a in anomalies if a.kind == "cost_money_exceeds_balance"]


def test_cost_check_reports_actual_before_state_shortfall() -> None:
    run = {
        "run_id": 2,
        "policy": "balanced",
        "max_weeks": 1,
        "final_ending_id": "stable_start",
        "weekly_log": [
            {
                "week": 1,
                "selected_action_ids": ["expensive_action"],
                "before_state": {"week": 0, "money": 100},
                "after_state": {"week": 1, "money": 0},
                "action_effects": [
                    {
                        "action_id": "expensive_action",
                        "effects": {"money": -150},
                        "executed": True,
                    }
                ],
            }
        ],
    }

    anomalies = detect_anomalies([run])
    shortfalls = [a for a in anomalies if a.kind == "cost_money_exceeds_balance"]

    assert len(shortfalls) == 1
    assert shortfalls[0].evidence["balance_before"] == 100


def test_cost_check_does_not_claim_planned_effect_was_executed() -> None:
    run = {
        "run_id": 3,
        "policy": "balanced",
        "max_weeks": 1,
        "final_ending_id": "stable_start",
        "weekly_log": [
            {
                "week": 1,
                "selected_action_ids": ["expensive_action"],
                "before_state": {"week": 0, "money": 100},
                "after_state": {"week": 1, "money": 100},
                "action_effects": [
                    {"action_id": "expensive_action", "effects": {"money": -150}}
                ],
            }
        ],
    }

    anomalies = detect_anomalies([run])

    assert not [a for a in anomalies if a.kind == "cost_money_exceeds_balance"]
    planned = [a for a in anomalies if a.kind == "planned_cost_exceeds_balance"]
    assert len(planned) == 1
    assert planned[0].severity == "info"
