"""Game-semantic anomaly invariants for ``study-in-germany``.

The Python anomaly detector in :mod:`game_analysis_agent.anomaly_detector`
covers *generic* invariants (stat bounds, dead state, pipeline stall,
etc). This module adds the *semantic* invariants that pin down gameplay
credibility: a run that ends in ``academic_success`` while the player
is bankrupt is a rule-of-the-game bug, not just a numeric curiosity.

The rules implemented here match the v0.2 review feedback in
``docs/REVIEW_FEEDBACK.md`` §9. They are deterministic, do not require
LLM calls, and are kept in a dedicated module so unit tests can exercise
each rule independently.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Final

from game_analysis_agent.schemas import Anomaly, AnomalyKind, AnomalySeverity


def _mk(
    kind: AnomalyKind,
    run_id: int,
    week: int,
    policy: str,
    *,
    severity: AnomalySeverity = "warning",
    evidence: dict[str, Any] | None = None,
    message: str = "",
) -> Anomaly:
    return Anomaly(
        kind=kind,
        severity=severity,
        run_id=run_id,
        week=week,
        policy=policy,
        evidence=evidence or {},
        message=message,
    )

# ---------------------------------------------------------------------------
# Game-specific constants (T04)
# ---------------------------------------------------------------------------

# Ending-id prefixes / members that represent a "successful" run. Used by
# ``crisis_success_ending`` and ``academic_success_with_failed_courses``.
SUCCESS_ENDING_EXACT: Final[frozenset[str]] = frozenset(
    {
        "academic_success",
        "scholarship_path",
        "smooth_first_semester",
        "schengen_granted",
    }
)

ACADEMIC_SUCCESS_ENDINGS: Final[frozenset[str]] = frozenset(
    {
        "academic_success",
        "scholarship_path",
    }
)

VISA_SUCCESS_ENDINGS: Final[frozenset[str]] = frozenset(
    {
        "smooth_first_semester",
        "schengen_granted",
    }
)

# Defaults that mirror the current demo.
DEFAULT_CRISIS_MONEY_THRESHOLD: Final[float] = -1000.0
DEFAULT_SURVIVAL_HUNGER: Final[float] = 85.0
DEFAULT_SURVIVAL_STRESS: Final[float] = 85.0
DEFAULT_LANGUAGE_THRESHOLD: Final[float] = 25.0
DEFAULT_APS_KNOWLEDGE_THRESHOLD: Final[float] = 25.0
DEFAULT_HUNGER_STREAK_WEEKS: Final[int] = 6
DEFAULT_STRESS_LOCK_WEEKS: Final[int] = 4
DEFAULT_SOCIAL_OVERFLOW_LOOKBACK: Final[int] = 8
DEFAULT_SOCIAL_OVERFLOW_RATIO: Final[float] = 0.7
DEFAULT_BLACK_WORK_VISA_THRESHOLD: Final[float] = 70.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _flags_of(run: dict[str, Any]) -> dict[str, Any]:
    """Locate the run's flag dictionary across the legacy and v0.2 shapes."""
    final_state = run.get("final_state") or run.get("state") or {}
    if isinstance(final_state, dict):
        flags = final_state.get("flags")
        if isinstance(flags, dict):
            return flags
    flags = run.get("flags")
    if isinstance(flags, dict):
        return flags
    return {}


def _ending_id(run: dict[str, Any]) -> str:
    return str(
        run.get("final_ending_id")
        or run.get("last_ending_id")
        or run.get("ending_id")
        or ""
    )


def _weekly_log(run: dict[str, Any]) -> list[dict[str, Any]]:
    log = run.get("weekly_log") or []
    return [week for week in log if isinstance(week, dict)]


def _after_state(week: dict[str, Any]) -> dict[str, Any]:
    state = week.get("after_state")
    if isinstance(state, dict):
        return state
    state = week.get("state")
    if isinstance(state, dict):
        return state
    return {}


def _selected_actions(week: dict[str, Any]) -> list[str]:
    actions = week.get("selected_action_ids") or week.get("actions") or []
    return [str(a) for a in actions if isinstance(a, str)]


def _is_success_ending(ending_id: str) -> bool:
    if ending_id in SUCCESS_ENDING_EXACT:
        return True
    return ending_id.endswith("_success") or ending_id.startswith("scholarship_")


def _state_float(state: dict[str, Any], key: str) -> float | None:
    value = state.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def check_semantic_invariants(
    run: dict[str, Any],
    *,
    crisis_money_threshold: float = DEFAULT_CRISIS_MONEY_THRESHOLD,
    survival_hunger: float = DEFAULT_SURVIVAL_HUNGER,
    survival_stress: float = DEFAULT_SURVIVAL_STRESS,
    language_threshold: float = DEFAULT_LANGUAGE_THRESHOLD,
    aps_knowledge_threshold: float = DEFAULT_APS_KNOWLEDGE_THRESHOLD,
    hunger_streak_weeks: int = DEFAULT_HUNGER_STREAK_WEEKS,
    stress_lock_weeks: int = DEFAULT_STRESS_LOCK_WEEKS,
    social_overflow_lookback: int = DEFAULT_SOCIAL_OVERFLOW_LOOKBACK,
    social_overflow_ratio: float = DEFAULT_SOCIAL_OVERFLOW_RATIO,
    black_work_visa_threshold: float = DEFAULT_BLACK_WORK_VISA_THRESHOLD,
    action_tags: Iterable[str] | None = None,
) -> list[Anomaly]:
    """Return a list of game-semantic anomalies for one run."""
    anomalies: list[Anomaly] = []
    run_id = int(run.get("run_id", 0))
    policy = str(run.get("policy", "unknown"))
    ending_id = _ending_id(run)
    log = _weekly_log(run)
    final_state = run.get("final_state") or (log[-1].get("after_state", {}) if log else {}) or {}
    flags = _flags_of(run)
    last_week_state = final_state if isinstance(final_state, dict) else {}

    # 1. Crisis success ending.
    if ending_id and _is_success_ending(ending_id):
        money = _state_float(last_week_state, "money")
        if money is not None and money < crisis_money_threshold:
            anomalies.append(
                _mk(
                    "crisis_success_ending",
                    run_id,
                    -1,
                    policy,
                    severity="critical",
                    evidence={
                        "ending_id": ending_id,
                        "money": money,
                        "threshold": crisis_money_threshold,
                    },
                    message=(
                        f"Run ended in `{ending_id}` while money was {money} "
                        f"(threshold={crisis_money_threshold})."
                    ),
                )
            )

    # 2. Social connector under survival crisis.
    if ending_id == "social_connector":
        hunger = _state_float(last_week_state, "hunger")
        stress = _state_float(last_week_state, "stress")
        if (
            hunger is not None
            and stress is not None
            and hunger >= survival_hunger
            and stress >= survival_stress
        ):
            anomalies.append(
                _mk(
                    "social_success_under_survival_crisis",
                    run_id,
                    -1,
                    policy,
                    severity="critical",
                    evidence={
                        "ending_id": ending_id,
                        "hunger": hunger,
                        "stress": stress,
                    },
                    message=(
                        f"`{ending_id}` reached with hunger={hunger}, "
                        f"stress={stress} — survival crisis ignored."
                    ),
                )
            )

    # 3. Academic success with failed courses.
    if ending_id in ACADEMIC_SUCCESS_ENDINGS:
        failed = last_week_state.get("failed_courses")
        if isinstance(failed, (int, float)) and failed > 0:
            anomalies.append(
                _mk(
                    "academic_success_with_failed_courses",
                    run_id,
                    -1,
                    policy,
                    severity="error",
                    evidence={
                        "ending_id": ending_id,
                        "failed_courses": failed,
                    },
                    message=(
                        f"`{ending_id}` reached with {failed} failed courses."
                    ),
                )
            )

    # 4. Visa success without registration.
    if ending_id in VISA_SUCCESS_ENDINGS:
        registered = bool(
            flags.get("registered")
            or flags.get("school_registered")
            or flags.get("registered_at_school")
        )
        if not registered:
            anomalies.append(
                _mk(
                    "visa_success_without_registration",
                    run_id,
                    -1,
                    policy,
                    severity="critical",
                    evidence={
                        "ending_id": ending_id,
                        "registered": False,
                    },
                    message=(
                        f"`{ending_id}` reached without school registration."
                    ),
                )
            )

    # 5/6. TestDaF / APS pass with too-low underlying stat.
    if flags.get("testdaf_passed"):
        language = _state_float(last_week_state, "language")
        if language is not None and language < language_threshold:
            anomalies.append(
                _mk(
                    "testdaf_pass_with_low_language",
                    run_id,
                    -1,
                    policy,
                    severity="error",
                    evidence={
                        "language": language,
                        "threshold": language_threshold,
                    },
                    message=(
                        f"TestDaF passed but language={language} "
                        f"(threshold={language_threshold})."
                    ),
                )
            )
    if flags.get("aps_passed"):
        aps = _state_float(last_week_state, "aps_knowledge")
        if aps is not None and aps < aps_knowledge_threshold:
            anomalies.append(
                _mk(
                    "aps_pass_with_low_aps_knowledge",
                    run_id,
                    -1,
                    policy,
                    severity="error",
                    evidence={
                        "aps_knowledge": aps,
                        "threshold": aps_knowledge_threshold,
                    },
                    message=(
                        f"APS passed but aps_knowledge={aps} "
                        f"(threshold={aps_knowledge_threshold})."
                    ),
                )
            )

    # 7. Black work without consequence.
    if flags.get("illegal_work_taken"):
        visa = _state_float(last_week_state, "visa_progress")
        if visa is not None and visa >= black_work_visa_threshold:
            anomalies.append(
                _mk(
                    "black_work_without_risk",
                    run_id,
                    -1,
                    policy,
                    severity="warning",
                    evidence={
                        "visa_progress": visa,
                        "threshold": black_work_visa_threshold,
                    },
                    message=(
                        f"Illegal work taken; visa_progress={visa} — no "
                        f"consequence applied."
                    ),
                )
            )

    # 8. Hunger ignored too long.
    if log:
        streak = 0
        max_streak_week = -1
        for week in log:
            state = _after_state(week)
            hunger = _state_float(state, "hunger")
            if hunger is not None and hunger >= survival_hunger:
                streak += 1
                if streak >= hunger_streak_weeks:
                    max_streak_week = int(week.get("week", -1))
            else:
                streak = 0
        if max_streak_week >= 0:
            anomalies.append(
                _mk(
                    "hunger_ignored_too_long",
                    run_id,
                    max_streak_week,
                    policy,
                    severity="warning",
                    evidence={
                        "streak_weeks": streak,
                        "threshold": survival_hunger,
                    },
                    message=(
                        f"Hunger ≥ {survival_hunger:g} for {streak} consecutive weeks "
                        f"(week={max_streak_week})."
                    ),
                )
            )

        # 9. Stress zero lock.
        lock_streak = 0
        lock_week = -1
        for week in log:
            state = _after_state(week)
            stress = _state_float(state, "stress")
            if stress is not None and stress <= 1:
                lock_streak += 1
                if lock_streak >= stress_lock_weeks:
                    lock_week = int(week.get("week", -1))
            else:
                lock_streak = 0
        if lock_week >= 0:
            anomalies.append(
                _mk(
                    "stress_zero_lock",
                    run_id,
                    lock_week,
                    policy,
                    severity="info",
                    evidence={"streak_weeks": lock_streak},
                    message=(
                        f"Stress ≤ 1 for {lock_streak} consecutive weeks "
                        f"(week={lock_week})."
                    ),
                )
            )

        # 10. Social overflow pattern.
        lookback = log[-social_overflow_lookback:] if len(log) > social_overflow_lookback else log
        total_actions = 0
        social_actions = 0
        tags = {tag.lower() for tag in (action_tags or {"social"})}
        for week in lookback:
            for action_id in _selected_actions(week):
                total_actions += 1
                if any(tag in action_id.lower() for tag in tags):
                    social_actions += 1
        if total_actions > 0:
            ratio = social_actions / total_actions
            if ratio >= social_overflow_ratio and social_actions >= 8:
                anomalies.append(
                    _mk(
                        "social_overflow_pattern",
                        run_id,
                        int(lookback[-1].get("week", -1)) if lookback else -1,
                        policy,
                        severity="info",
                        evidence={
                            "ratio": round(ratio, 3),
                            "social_actions": social_actions,
                            "total_actions": total_actions,
                        },
                        message=(
                            f"Social actions dominated {ratio:.0%} of the last "
                            f"{len(lookback)} weeks."
                        ),
                    )
                )

    return anomalies


__all__ = [
    "ACADEMIC_SUCCESS_ENDINGS",
    "DEFAULT_BLACK_WORK_VISA_THRESHOLD",
    "DEFAULT_CRISIS_MONEY_THRESHOLD",
    "DEFAULT_HUNGER_STREAK_WEEKS",
    "DEFAULT_LANGUAGE_THRESHOLD",
    "DEFAULT_APS_KNOWLEDGE_THRESHOLD",
    "DEFAULT_SOCIAL_OVERFLOW_LOOKBACK",
    "DEFAULT_SOCIAL_OVERFLOW_RATIO",
    "DEFAULT_STRESS_LOCK_WEEKS",
    "DEFAULT_SURVIVAL_HUNGER",
    "DEFAULT_SURVIVAL_STRESS",
    "SUCCESS_ENDING_EXACT",
    "VISA_SUCCESS_ENDINGS",
    "check_semantic_invariants",
]
