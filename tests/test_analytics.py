"""Tests for ``game_analysis_agent.analytics`` pure functions."""

from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.analytics import (
    compute_action_pick_rates,
    compute_choice_pick_rates,
    compute_ending_distribution,
    compute_event_trigger_rates,
    compute_summary,
    compute_weekly_stats,
    load_runs,
    write_csv,
)

FIXTURE = Path(__file__).parent / "fixtures" / "raw_runs.sample.jsonl"


def _read_fixture() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_load_runs_returns_list_of_dicts() -> None:
    runs = load_runs(FIXTURE)
    assert isinstance(runs, list)
    assert all(isinstance(r, dict) for r in runs)
    assert len(runs) == 2


def test_compute_ending_distribution_counts_correctly() -> None:
    runs = _read_fixture()
    rows = compute_ending_distribution(runs)
    by_key = {(row["policy"], row["ending_id"]): row for row in rows}
    # The fixture has two balanced runs but with different ending_ids
    # (academic_success, burnout) — each appears once with rate 0.5.
    assert by_key[("balanced", "academic_success")]["count"] == 1
    academic = by_key[("balanced", "academic_success")]
    assert academic["rate"] == 0.5
    assert academic["sample_size"] == 2
    assert academic["difficulty"] == "unknown"
    assert academic["scenario"] == "default"
    assert academic["ci95_low"] < academic["rate"] < academic["ci95_high"]
    assert by_key[("balanced", "burnout")]["count"] == 1


def test_compute_action_pick_rates_handles_v02_keys() -> None:
    runs = _read_fixture()
    rows = compute_action_pick_rates(runs)
    # Legacy fixture uses ``actions`` key inside weekly_log — both are accepted.
    pick_ids = {row["action_id"] for row in rows}
    assert "study_library" in pick_ids
    assert "rest_at_home" in pick_ids


def test_compute_action_pick_rates_does_not_double_count_replay_mirror() -> None:
    runs = [
        {
            "policy": "balanced",
            "weekly_log": [{"selected_action_ids": ["study", "rest"]}],
            "action_sequence": [{"actions": ["study", "rest"]}],
        }
    ]

    rows = compute_action_pick_rates(runs)
    by_action = {row["action_id"]: row for row in rows}

    assert by_action["study"]["count"] == 1
    assert by_action["study"]["rate_per_run"] == 1.0
    assert by_action["study"]["pick_share"] == 0.5
    assert by_action["study"]["run_presence_rate"] == 1.0
    assert by_action["rest"]["count"] == 1


def test_compute_weekly_stats_keys_metrics() -> None:
    runs = _read_fixture()
    weekly = compute_weekly_stats(runs)
    metrics = {row["metric"] for row in weekly}
    assert "money" in metrics
    assert "stress" in metrics
    for row in weekly:
        assert "mean" in row and "median" in row


def test_compute_event_trigger_rates_v02_schema() -> None:
    runs = [
        {
            "run_id": 0,
            "policy": "balanced",
            "weekly_log": [
                {
                    "week": 1,
                    "triggered_event_id": "first_lecture",
                    "after_state": {"week": 1},
                }
            ],
        },
        {
            "run_id": 1,
            "policy": "balanced",
            "weekly_log": [
                {
                    "week": 1,
                    "triggered_event_id": "stress_breakdown",
                    "after_state": {"week": 1},
                }
            ],
        },
    ]
    rows = compute_event_trigger_rates(runs)
    assert {row["event_id"] for row in rows} == {"first_lecture", "stress_breakdown"}


def test_compute_choice_pick_rates_groups_by_event() -> None:
    runs = [
        {
            "run_id": 0,
            "policy": "balanced",
            "weekly_log": [
                {
                    "week": 1,
                    "triggered_event_id": "first_lecture",
                    "event_choice_id": "first_lecture.choice_01",
                }
            ],
        },
        {
            "run_id": 1,
            "policy": "balanced",
            "weekly_log": [
                {
                    "week": 1,
                    "triggered_event_id": "first_lecture",
                    "event_choice_id": "first_lecture.choice_02",
                }
            ],
        },
    ]
    rows = compute_choice_pick_rates(runs)
    total = sum(row["count"] for row in rows)
    assert total == 2


def test_compute_summary_has_top_events() -> None:
    runs = _read_fixture()
    summary = compute_summary(runs)
    assert summary["total_runs"] == 2
    assert "first_lecture" in summary["top_events"]


def test_write_csv_round_trips(tmp_path) -> None:
    out = tmp_path / "sub" / "x.csv"
    write_csv(out, ["a", "b"], [{"a": 1, "b": 2}])
    assert out.exists()
    content = out.read_text(encoding="utf-8").splitlines()
    assert content[0] == "a,b"
    assert content[1] == "1,2"
