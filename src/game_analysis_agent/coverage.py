"""Deterministic state, branch, action, and data-quality coverage reports."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any


def analyze_coverage(
    runs: list[dict[str, Any]],
    *,
    event_graph: dict[str, Any] | None = None,
    action_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return coverage evidence for a batch of gameplay runs.

    Observed coverage is deliberately separated from catalog-based coverage.
    A missing catalog must never be mistaken for 100% coverage. Legacy v0.1
    trace keys and current v0.2 keys are both accepted.
    """

    total_runs = len(runs)
    scenario_counts: Counter[str] = Counter()
    policy_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    cell_counts: Counter[tuple[str, str, str]] = Counter()
    crisis_runs: dict[str, set[int]] = defaultdict(set)
    state_week_counts: Counter[str] = Counter()
    regime_pairs: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    choice_counts: Counter[tuple[str, str]] = Counter()
    action_counts: Counter[str] = Counter()
    available_action_ids: set[str] = set()
    state_keys: set[str] = set()
    flags_seen: set[str] = set()
    flag_set_transitions: Counter[str] = Counter()
    flag_unset_transitions: Counter[str] = Counter()
    malformed_runs = 0
    malformed_weeks = 0
    missing_state_weeks = 0
    total_weeks = 0
    no_event_weeks = 0

    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            malformed_runs += 1
            continue
        scenario = str(run.get("scenario") or "default")
        policy = str(run.get("policy") or "unknown")
        difficulty = str(run.get("difficulty") or "unknown")
        scenario_counts[scenario] += 1
        policy_counts[policy] += 1
        difficulty_counts[difficulty] += 1
        cell_counts[(difficulty, policy, scenario)] += 1
        weekly_log = run.get("weekly_log", []) or []
        if not isinstance(weekly_log, list):
            malformed_runs += 1
            continue
        previous_flags: set[str] = set()
        for week in weekly_log:
            total_weeks += 1
            if not isinstance(week, dict):
                malformed_weeks += 1
                continue

            event_id = str(week.get("triggered_event_id") or week.get("event_id") or "")
            choice_id = str(week.get("event_choice_id") or week.get("choice_id") or "")
            if event_id:
                event_counts[event_id] += 1
                if choice_id:
                    choice_counts[(event_id, choice_id)] += 1
            else:
                no_event_weeks += 1

            selected = week.get("selected_action_ids") or week.get("actions") or []
            if isinstance(selected, list):
                action_counts.update(str(item) for item in selected if str(item))
            available = (
                week.get("available_action_ids")
                or week.get("next_available_action_ids")
                or []
            )
            if isinstance(available, list):
                available_action_ids.update(str(item) for item in available if str(item))

            state = week.get("after_state") or week.get("state") or {}
            if not isinstance(state, dict) or not state:
                missing_state_weeks += 1
                continue
            state_keys.update(str(key) for key in state)
            regimes = sorted(_regimes_for_state(state))
            for regime in regimes:
                crisis_runs[regime].add(index)
                state_week_counts[regime] += 1
            for left, right in combinations(regimes, 2):
                regime_pairs[f"{left}+{right}"] += 1

            flags = _true_flags(state.get("flags"))
            flags_seen.update(flags)
            flag_set_transitions.update(flags - previous_flags)
            flag_unset_transitions.update(previous_flags - flags)
            previous_flags = flags

    regimes = []
    for regime in sorted(set(_EXPECTED_REGIMES) | set(crisis_runs)):
        run_count = len(crisis_runs.get(regime, set()))
        regimes.append(
            {
                "regime": regime,
                "run_count": run_count,
                "run_rate": round(run_count / max(1, total_runs), 6),
                "week_count": state_week_counts.get(regime, 0),
            }
        )

    catalog_event_ids, catalog_choice_ids = _event_catalog_ids(event_graph)
    catalog_action_ids = _action_catalog_ids(action_catalog)
    observed_event_ids = set(event_counts)
    observed_choice_ids = {choice for _event, choice in choice_counts}
    observed_action_ids = set(action_counts)
    action_denominator = catalog_action_ids or available_action_ids
    covered_event_ids = observed_event_ids & catalog_event_ids
    covered_choice_ids = observed_choice_ids & catalog_choice_ids
    covered_action_ids = observed_action_ids & action_denominator

    return {
        "schema_version": "coverage-v2",
        "total_runs": total_runs,
        "total_weeks": total_weeks,
        "scenarios": dict(sorted(scenario_counts.items())),
        "policies": dict(sorted(policy_counts.items())),
        "difficulties": dict(sorted(difficulty_counts.items())),
        "cells": [
            {
                "difficulty": difficulty,
                "policy": policy,
                "scenario": scenario,
                "run_count": count,
            }
            for (difficulty, policy, scenario), count in sorted(cell_counts.items())
        ],
        "state_regimes": regimes,
        "regime_pair_coverage": dict(regime_pairs.most_common()),
        "state_coverage": {
            "observed_keys": sorted(state_keys),
            "observed_flags": sorted(flags_seen),
            "flag_set_transitions": dict(flag_set_transitions.most_common()),
            "flag_unset_transitions": dict(flag_unset_transitions.most_common()),
        },
        "event_coverage": {
            "catalog_available": bool(catalog_event_ids),
            "catalog_events": len(catalog_event_ids),
            "distinct_triggered_events": len(observed_event_ids),
            "triggered_event_rate": _ratio(
                len(covered_event_ids), len(catalog_event_ids)
            ),
            "untriggered_event_ids": sorted(catalog_event_ids - observed_event_ids),
            "unknown_observed_event_ids": sorted(observed_event_ids - catalog_event_ids)
            if catalog_event_ids
            else [],
            "top_events": dict(event_counts.most_common(20)),
            "no_event_weeks": no_event_weeks,
        },
        "choice_coverage": {
            "catalog_available": bool(catalog_choice_ids),
            "catalog_choices": len(catalog_choice_ids),
            "distinct_selected_choices": len(observed_choice_ids),
            "selected_choice_rate": _ratio(
                len(covered_choice_ids), len(catalog_choice_ids)
            ),
            "unselected_choice_ids": sorted(catalog_choice_ids - observed_choice_ids),
            "unknown_observed_choice_ids": sorted(observed_choice_ids - catalog_choice_ids)
            if catalog_choice_ids
            else [],
            "selected": [
                {"event_id": event_id, "choice_id": choice_id, "count": count}
                for (event_id, choice_id), count in choice_counts.most_common()
            ],
        },
        "action_coverage": {
            "catalog_available": bool(catalog_action_ids),
            "catalog_actions": len(catalog_action_ids),
            "available_actions_observed": len(available_action_ids),
            "distinct_selected_actions": len(observed_action_ids),
            "selected_action_rate": _ratio(
                len(covered_action_ids), len(action_denominator)
            ),
            "unselected_action_ids": sorted(action_denominator - observed_action_ids),
            "unknown_observed_action_ids": sorted(observed_action_ids - action_denominator)
            if action_denominator
            else [],
            "top_actions": dict(action_counts.most_common(20)),
        },
        "data_quality": {
            "malformed_runs": malformed_runs,
            "malformed_weeks": malformed_weeks,
            "weeks_missing_state": missing_state_weeks,
        },
    }


def write_coverage_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_and_write_coverage(
    runs: list[dict[str, Any]], report_dir: Path
) -> dict[str, Any]:
    event_graph, event_error = _read_optional_json(report_dir / "event_graph.json")
    action_catalog, action_error = _read_optional_json(report_dir / "action_catalog.json")
    report = analyze_coverage(
        runs,
        event_graph=event_graph,
        action_catalog=action_catalog,
    )
    report["data_quality"]["catalog_errors"] = [
        error for error in (event_error, action_error) if error
    ]
    write_coverage_report(report, report_dir / "coverage_report.json")
    return report


_EXPECTED_REGIMES = (
    "low_money",
    "deep_debt",
    "low_energy",
    "high_stress",
    "high_hunger",
    "high_loneliness",
    "visa_risk",
    "academic_risk",
    "work_limit_risk",
    "cashflow_crisis",
)


def _regimes_for_state(state: dict[str, Any]) -> list[str]:
    regimes: list[str] = []
    money = _num(state, "money")
    energy = _num(state, "energy")
    stress = _num(state, "stress")
    hunger = _num(state, "hunger")
    loneliness = _num(state, "loneliness")
    visa = _num(state, "visa_progress")
    academic = _num(state, "academic_progress", "academic")
    exam = _num(state, "exam_readiness")
    work_hours = _num(state, "current_week_work_hours")
    flags = _true_flags(state.get("flags"))
    if money is not None and money < 200:
        regimes.append("low_money")
    if money is not None and money < -1000:
        regimes.append("deep_debt")
    if energy is not None and energy <= 20:
        regimes.append("low_energy")
    if stress is not None and stress >= 80:
        regimes.append("high_stress")
    if hunger is not None and hunger >= 80:
        regimes.append("high_hunger")
    if loneliness is not None and loneliness >= 80:
        regimes.append("high_loneliness")
    if visa is not None and visa < 45:
        regimes.append("visa_risk")
    if (
        academic is not None
        and (exam is None or min(academic, exam) < 45)
        and int(state.get("week", 0) or 0) >= 8
    ):
        regimes.append("academic_risk")
    if work_hours is not None and work_hours > 20:
        regimes.append("work_limit_risk")
    if {"cashflow_crisis", "cash_shortfall"} & flags:
        regimes.append("cashflow_crisis")
    return regimes


def _num(state: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = state.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _true_flags(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key, enabled in value.items() if enabled is True}
    if isinstance(value, list):
        return {str(item) for item in value if str(item)}
    return set()


def _event_catalog_ids(
    payload: dict[str, Any] | None,
) -> tuple[set[str], set[str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        return set(), set()
    events: set[str] = set()
    choices: set[str] = set()
    for event in payload["events"]:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "")
        if not event_id:
            continue
        events.add(event_id)
        raw_choices = event.get("choices") or []
        if not isinstance(raw_choices, list):
            continue
        for index, choice in enumerate(raw_choices, start=1):
            if not isinstance(choice, dict):
                continue
            choice_id = str(choice.get("choice_id") or choice.get("id") or "")
            if not choice_id:
                safe_text = str(choice.get("text") or "").lower().replace(" ", "_")
                choice_id = f"{event_id}.choice_{index:02d}_{safe_text}"
            choices.add(choice_id)
    return events, choices


def _action_catalog_ids(payload: dict[str, Any] | None) -> set[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("actions"), list):
        return set()
    return {
        str(action.get("id"))
        for action in payload["actions"]
        if isinstance(action, dict) and action.get("id")
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _read_optional_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{path.name}: invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, f"{path.name}: root must be an object"
    return payload, None


__all__ = [
    "analyze_and_write_coverage",
    "analyze_coverage",
    "write_coverage_report",
]
