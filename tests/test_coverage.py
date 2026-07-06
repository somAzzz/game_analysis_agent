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
