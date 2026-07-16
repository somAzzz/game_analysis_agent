"""Tests for state-space coverage reports."""

from __future__ import annotations

from game_analysis_agent.coverage import analyze_coverage


def test_analyze_coverage_counts_crisis_regimes() -> None:
    report = analyze_coverage(
        [
            {
                "policy": "work",
                "scenario": "low_money_start",
                "weekly_log": [
                    {
                        "week": 12,
                        "triggered_event_id": "rent_pressure",
                        "after_state": {
                            "week": 12,
                            "money": -1200,
                            "stress": 85,
                            "hunger": 82,
                            "visa_progress": 30,
                            "academic_progress": 20,
                            "exam_readiness": 25,
                            "current_week_work_hours": 24,
                        },
                    }
                ],
            }
        ]
    )

    by_regime = {row["regime"]: row for row in report["state_regimes"]}
    assert report["scenarios"] == {"low_money_start": 1}
    assert by_regime["deep_debt"]["run_count"] == 1
    assert by_regime["high_stress"]["week_count"] == 1
    assert by_regime["work_limit_risk"]["run_count"] == 1
    assert report["event_coverage"]["distinct_triggered_events"] == 1

def test_analyze_coverage_reports_catalog_branch_action_and_flag_gaps() -> None:
    report = analyze_coverage(
        [
            {
                "policy": "balanced",
                "difficulty": "realistic",
                "scenario": "high_stress_start",
                "weekly_log": [
                    {
                        "week": 1,
                        "available_action_ids": ["study", "rest"],
                        "selected_action_ids": ["rest"],
                        "triggered_event_id": "arrival",
                        "event_choice_id": "arrival.ask",
                        "after_state": {
                            "week": 1,
                            "money": 100,
                            "energy": 15,
                            "stress": 90,
                            "flags": {"arrived": True},
                        },
                    },
                    {
                        "week": 2,
                        "available_action_ids": ["study", "rest"],
                        "selected_action_ids": ["study"],
                        "after_state": {
                            "week": 2,
                            "money": 300,
                            "energy": 40,
                            "stress": 50,
                            "flags": {"arrived": True, "registered": True},
                        },
                    },
                ],
            }
        ],
        event_graph={
            "events": [
                {
                    "id": "arrival",
                    "choices": [
                        {"id": "arrival.ask"},
                        {"id": "arrival.wait"},
                    ],
                },
                {"id": "exam", "choices": []},
            ]
        },
        action_catalog={
            "actions": [{"id": "study"}, {"id": "rest"}, {"id": "work"}]
        },
    )

    assert report["schema_version"] == "coverage-v2"
    assert report["cells"] == [
        {
            "difficulty": "realistic",
            "policy": "balanced",
            "scenario": "high_stress_start",
            "run_count": 1,
        }
    ]
    assert report["event_coverage"]["triggered_event_rate"] == 0.5
    assert report["event_coverage"]["untriggered_event_ids"] == ["exam"]
    assert report["choice_coverage"]["selected_choice_rate"] == 0.5
    assert report["action_coverage"]["unselected_action_ids"] == ["work"]
    assert report["state_coverage"]["flag_set_transitions"] == {
        "arrived": 1,
        "registered": 1,
    }
    assert list(report["state_coverage"]["flag_set_transitions"]) == [
        "arrived",
        "registered",
    ]
    assert report["regime_pair_coverage"]["high_stress+low_energy"] == 1


def test_analyze_coverage_does_not_claim_rates_without_catalogs() -> None:
    report = analyze_coverage([{"weekly_log": []}])

    assert report["event_coverage"]["catalog_available"] is False
    assert report["event_coverage"]["triggered_event_rate"] is None
    assert report["action_coverage"]["selected_action_rate"] is None


def test_catalog_coverage_uses_real_choice_ids_and_excludes_unknowns() -> None:
    report = analyze_coverage(
        [
            {
                "weekly_log": [
                    {
                        "triggered_event_id": "arrival",
                        "event_choice_id": "arrival.choice_01_ask_for_help",
                        "selected_action_ids": ["study", "ghost"],
                        "after_state": {"week": 1},
                    },
                    {
                        "triggered_event_id": "ghost_event",
                        "event_choice_id": "ghost.choice_01",
                        "after_state": {"week": 2},
                    },
                ]
            }
        ],
        event_graph={
            "events": [
                {
                    "id": "arrival",
                    "choices": [
                        {"text": "Ask for help"},
                        {"text": "Wait"},
                    ],
                }
            ]
        },
        action_catalog={"actions": [{"id": "study"}, {"id": "rest"}]},
    )

    assert report["event_coverage"]["triggered_event_rate"] == 1.0
    assert report["event_coverage"]["unknown_observed_event_ids"] == ["ghost_event"]
    assert report["choice_coverage"]["selected_choice_rate"] == 0.5
    assert report["choice_coverage"]["unknown_observed_choice_ids"] == [
        "ghost.choice_01"
    ]
    assert report["action_coverage"]["selected_action_rate"] == 0.5
    assert report["action_coverage"]["unknown_observed_action_ids"] == ["ghost"]
