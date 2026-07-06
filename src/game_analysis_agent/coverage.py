"""State-space coverage reports for raw gameplay runs.

Ending distributions answer "what happened"; coverage answers "which
important regimes were actually exercised?". Real balance testing needs
both. These helpers are deterministic and run as part of ``analyze``.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def analyze_coverage(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return state/event/scenario coverage for a batch of runs."""
    total_runs = len(runs)
    scenario_counts: Counter[str] = Counter()
    policy_counts: Counter[str] = Counter()
    crisis_runs: dict[str, set[int]] = defaultdict(set)
    event_counts: Counter[str] = Counter()
    state_week_counts: Counter[str] = Counter()

    for index, run in enumerate(runs):
        scenario_counts[str(run.get("scenario") or "default")] += 1
        policy_counts[str(run.get("policy") or "unknown")] += 1
        for week in run.get("weekly_log", []) or []:
            if not isinstance(week, dict):
                continue
            event_id = str(week.get("triggered_event_id") or week.get("event_id") or "")
            if event_id:
                event_counts[event_id] += 1
            state = week.get("after_state") or week.get("state") or {}
            if not isinstance(state, dict):
                continue
            for regime in _regimes_for_state(state):
                crisis_runs[regime].add(index)
                state_week_counts[regime] += 1

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

    return {
        "total_runs": total_runs,
        "scenarios": dict(sorted(scenario_counts.items())),
        "policies": dict(sorted(policy_counts.items())),
        "state_regimes": regimes,
        "event_coverage": {
            "distinct_triggered_events": len(event_counts),
            "top_events": dict(event_counts.most_common(20)),
        },
    }


def write_coverage_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_and_write_coverage(runs: list[dict[str, Any]], report_dir: Path) -> dict[str, Any]:
    report = analyze_coverage(runs)
    write_coverage_report(report, report_dir / "coverage_report.json")
    return report


_EXPECTED_REGIMES = (
    "low_money",
    "deep_debt",
    "high_stress",
    "high_hunger",
    "visa_risk",
    "academic_risk",
    "work_limit_risk",
)


def _regimes_for_state(state: dict[str, Any]) -> list[str]:
    regimes: list[str] = []
    money = _num(state, "money")
    stress = _num(state, "stress")
    hunger = _num(state, "hunger")
    visa = _num(state, "visa_progress")
    academic = _num(state, "academic_progress")
    exam = _num(state, "exam_readiness")
    work_hours = _num(state, "current_week_work_hours")
    if money is not None and money < 200:
        regimes.append("low_money")
    if money is not None and money < -1000:
        regimes.append("deep_debt")
    if stress is not None and stress >= 80:
        regimes.append("high_stress")
    if hunger is not None and hunger >= 80:
        regimes.append("high_hunger")
    if visa is not None and visa < 45:
        regimes.append("visa_risk")
    if (
        academic is not None
        and exam is not None
        and min(academic, exam) < 45
        and int(state.get("week", 0) or 0) >= 8
    ):
        regimes.append("academic_risk")
    if work_hours is not None and work_hours > 20:
        regimes.append("work_limit_risk")
    return regimes


def _num(state: dict[str, Any], key: str) -> float | None:
    value = state.get(key)
    return float(value) if isinstance(value, (int, float)) else None


__all__ = [
    "analyze_and_write_coverage",
    "analyze_coverage",
    "write_coverage_report",
]
