"""Tests for ``game_analysis_agent.anomaly_semantics`` (T04)."""

from __future__ import annotations

from typing import Any

from game_analysis_agent.anomaly_detector import detect_anomalies
from game_analysis_agent.anomaly_semantics import check_semantic_invariants


def _flags(**flags: Any) -> dict[str, Any]:
    return {key: value for key, value in flags.items()}


def _final_state(**state: Any) -> dict[str, Any]:
    return dict(state)


def _base_run(**overrides: Any) -> dict[str, Any]:
    run: dict[str, Any] = {
        "run_id": 0,
        "policy": "balanced",
        "max_weeks": 20,
        "final_ending_id": "academic_success",
        "final_state": _final_state(
            week=20,
            money=500,
            energy=80,
            stress=30,
            loneliness=20,
            hunger=20,
            academic_progress=80,
            exam_readiness=70,
            language=70,
            social=50,
            visa_progress=80,
            career_progress=10,
            flags=_flags(
                registered=True,
                testdaf_passed=True,
                aps_passed=True,
            ),
        ),
        "weekly_log": [],
    }
    run.update(overrides)
    return run


def test_crisis_success_ending_fires() -> None:
    run = _base_run(
        final_ending_id="academic_success",
        final_state=_final_state(
            money=-1200,
            energy=20,
            stress=80,
            loneliness=50,
            hunger=70,
            academic_progress=60,
            visa_progress=10,
            flags=_flags(registered=True),
        ),
    )
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "crisis_success_ending" in kinds


def test_social_connector_under_survival_crisis_fires() -> None:
    run = _base_run(
        final_ending_id="social_connector",
        final_state=_final_state(
            money=300,
            energy=20,
            stress=90,
            loneliness=15,
            hunger=90,
            social=85,
            visa_progress=40,
        ),
    )
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "social_success_under_survival_crisis" in kinds


def test_academic_success_with_failed_courses_fires() -> None:
    run = _base_run(
        final_ending_id="scholarship_path",
        final_state=_final_state(
            money=2000,
            academic_progress=90,
            failed_courses=2,
            visa_progress=70,
            flags=_flags(registered=True),
        ),
    )
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "academic_success_with_failed_courses" in kinds


def test_visa_success_without_registration_fires() -> None:
    run = _base_run(
        final_ending_id="smooth_first_semester",
        final_state=_final_state(
            money=4000,
            visa_progress=90,
            flags={},  # no registration
        ),
    )
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "visa_success_without_registration" in kinds


def test_testdaf_pass_with_low_language_fires() -> None:
    run = _base_run(
        final_ending_id="academic_success",
        final_state=_final_state(
            money=1500,
            academic_progress=80,
            language=10,  # very low
            visa_progress=70,
            flags=_flags(registered=True, testdaf_passed=True),
        ),
    )
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "testdaf_pass_with_low_language" in kinds


def test_aps_pass_with_low_knowledge_fires() -> None:
    run = _base_run(
        final_ending_id="academic_success",
        final_state=_final_state(
            money=1500,
            academic_progress=80,
            aps_knowledge=10,
            visa_progress=70,
            flags=_flags(registered=True, aps_passed=True),
        ),
    )
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "aps_pass_with_low_aps_knowledge" in kinds


def test_black_work_without_risk_fires() -> None:
    run = _base_run(
        final_ending_id="smooth_first_semester",
        final_state=_final_state(
            money=3000,
            visa_progress=95,
            flags=_flags(registered=True, illegal_work_taken=True),
        ),
    )
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "black_work_without_risk" in kinds


def test_hunger_ignored_too_long_fires() -> None:
    weekly_log = []
    for week in range(1, 11):
        weekly_log.append(
            {
                "week": week,
                "selected_action_ids": ["cook_at_home"],
                "after_state": {"hunger": 95, "stress": 30},
            }
        )
    run = _base_run(weekly_log=weekly_log, final_ending_id="burnout")
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "hunger_ignored_too_long" in kinds


def test_hunger_ignored_uses_review_threshold_85() -> None:
    weekly_log = []
    for week in range(1, 7):
        weekly_log.append(
            {
                "week": week,
                "selected_action_ids": ["cook_at_home"],
                "after_state": {"hunger": 86, "stress": 30},
            }
        )
    run = _base_run(weekly_log=weekly_log, final_ending_id="burnout")
    findings = check_semantic_invariants(run)
    hunger = [a for a in findings if a.kind == "hunger_ignored_too_long"]
    assert hunger
    assert hunger[0].evidence["threshold"] == 85.0


def test_stress_zero_lock_fires() -> None:
    weekly_log = []
    for week in range(1, 6):
        weekly_log.append(
            {
                "week": week,
                "selected_action_ids": ["sleep_recover"],
                "after_state": {"hunger": 20, "stress": 0.5},
            }
        )
    run = _base_run(weekly_log=weekly_log, final_ending_id="social_connector")
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "stress_zero_lock" in kinds


def test_social_overflow_pattern_fires() -> None:
    weekly_log = []
    actions = ["social_chat", "social_party", "social_karaoke", "social_discord"]
    for week in range(1, 11):
        weekly_log.append(
            {
                "week": week,
                "selected_action_ids": actions,
                "after_state": {"hunger": 40, "stress": 50, "social": 90},
            }
        )
    run = _base_run(weekly_log=weekly_log, final_ending_id="social_connector")
    findings = check_semantic_invariants(run)
    kinds = {a.kind for a in findings}
    assert "social_overflow_pattern" in kinds


def test_clean_run_produces_no_semantic_anomalies() -> None:
    run = _base_run(
        final_ending_id="academic_success",
        final_state=_final_state(
            money=1500,
            academic_progress=85,
            language=80,
            aps_knowledge=70,
            visa_progress=80,
            failed_courses=0,
            flags=_flags(
                registered=True,
                testdaf_passed=True,
                aps_passed=True,
            ),
        ),
        weekly_log=[
            {
                "week": 1,
                "selected_action_ids": ["study_library"],
                "after_state": {"hunger": 25, "stress": 30, "social": 30},
            },
            {
                "week": 2,
                "selected_action_ids": ["study_library"],
                "after_state": {"hunger": 25, "stress": 30, "social": 30},
            },
        ],
    )
    findings = check_semantic_invariants(run)
    assert findings == []


def test_detect_anomalies_runs_semantics() -> None:
    run = _base_run(
        final_ending_id="academic_success",
        final_state=_final_state(
            money=-1500,  # triggers crisis_success_ending
            academic_progress=80,
            language=80,
            aps_knowledge=70,
            visa_progress=80,
            flags=_flags(registered=True),
        ),
    )
    anomalies = detect_anomalies([run])
    kinds = {a.kind for a in anomalies}
    assert "crisis_success_ending" in kinds
    # The semantic check should add the anomaly with severity=critical.
    critical = [a for a in anomalies if a.kind == "crisis_success_ending"]
    assert critical and critical[0].severity == "critical"
