"""Pure analytics functions extracted from ``tools/analyze_balance.py``.

The CLI shell still lives in ``tools/analyze_balance.py``; this module
holds the deterministic statistics so they can be unit-tested without
subprocess overhead and reused by other agents (notably
``src/game_analysis_agent/agents/value_reviewer.py``).
"""

from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# Core in-game stats. Mirrors ``study-in-germany/autoload/GameState.gd``
# (the v0.2 contracts use these names); additional fields are kept
# optional so legacy fixtures still parse.
METRICS: tuple[str, ...] = (
    "money",
    "energy",
    "stress",
    "loneliness",
    "hunger",
    "academic_progress",
    "exam_readiness",
    "language",
    "social",
    "visa_progress",
    "career_progress",
    "gpa_score",
    "aps_knowledge",
    "aps_score",
    "current_week_work_hours",
    "annual_work_half_days",
)

NON_NEGATIVE_METRICS: tuple[str, ...] = (
    "money",
    "blocked_account_balance",
    "current_week_work_hours",
    "annual_work_half_days",
    "failed_courses",
    "testdaf_reading",
    "testdaf_listening",
    "testdaf_writing",
    "testdaf_speaking",
)

UPPER_BOUNDED_METRICS: tuple[str, ...] = (
    "energy",
    "stress",
    "loneliness",
    "hunger",
    "academic_progress",
    "exam_readiness",
    "language",
    "social",
    "visa_progress",
    "career_progress",
    "gpa_score",
    "aps_knowledge",
    "aps_score",
)


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return ordered[index]


def load_runs(path: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                runs.append(json_loads(stripped))
            except ValueError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
    return runs


def json_loads(text: str) -> Any:
    import json

    return json.loads(text)


def compute_ending_distribution(
    runs: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """``[{"policy": ..., "ending_id": ..., "count": ..., "rate": ...}, ...]``"""
    by_policy: dict[str, list[str]] = defaultdict(list)
    for run in runs:
        by_policy[str(run.get("policy", "unknown"))].append(
            str(run.get("final_ending_id") or run.get("ending_id") or "unknown")
        )
    rows: list[dict[str, Any]] = []
    for policy, endings in sorted(by_policy.items()):
        counter = Counter(endings)
        total = len(endings)
        for ending_id, count in sorted(counter.items()):
            rows.append(
                {
                    "policy": policy,
                    "ending_id": ending_id,
                    "count": count,
                    "rate": round(count / max(1, total), 6),
                }
            )
    return rows


def compute_action_pick_rates(
    runs: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_policy: dict[str, Counter[str]] = defaultdict(Counter)
    policy_total: Counter[str] = Counter()
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        policy_total[policy] += 1
        for action_id in _iter_action_ids(run):
            by_policy[policy][action_id] += 1
    rows: list[dict[str, Any]] = []
    for policy, actions in sorted(by_policy.items()):
        total = policy_total[policy]
        for action_id, count in sorted(actions.items()):
            rows.append(
                {
                    "policy": policy,
                    "action_id": action_id,
                    "count": count,
                    "rate_per_run": round(count / max(1, total), 6),
                }
            )
    return rows


def compute_event_trigger_rates(
    runs: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_policy: dict[str, Counter[str]] = defaultdict(Counter)
    policy_total: Counter[str] = Counter()
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        policy_total[policy] += 1
        for week in run.get("weekly_log", []) or []:
            event_id = str(week.get("triggered_event_id") or week.get("event_id", "") or "")
            if event_id:
                by_policy[policy][event_id] += 1
    rows: list[dict[str, Any]] = []
    for policy, events in sorted(by_policy.items()):
        total = policy_total[policy]
        for event_id, count in sorted(events.items()):
            rows.append(
                {
                    "policy": policy,
                    "event_id": event_id,
                    "count": count,
                    "rate_per_run": round(count / max(1, total), 6),
                }
            )
    return rows


def compute_choice_pick_rates(
    runs: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    event_totals: dict[tuple[str, str], int] = defaultdict(int)
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        for week in run.get("weekly_log", []) or []:
            event_id = str(week.get("triggered_event_id") or week.get("event_id", "") or "")
            choice_id = str(week.get("event_choice_id") or week.get("choice_id", "") or "")
            if not event_id:
                continue
            event_totals[(policy, event_id)] += 1
            if choice_id:
                counts[(policy, event_id, choice_id)] += 1
    rows: list[dict[str, Any]] = []
    for (policy, event_id, choice_id), count in sorted(counts.items()):
        total = event_totals[(policy, event_id)]
        rows.append(
            {
                "policy": policy,
                "event_id": event_id,
                "choice_id": choice_id,
                "count": count,
                "rate_per_event": round(count / max(1, total), 6),
            }
        )
    return rows


def compute_weekly_stats(
    runs: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    bucket: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        for week in run.get("weekly_log", []) or []:
            state = week.get("after_state") or week.get("state") or {}
            week_no = int(
                week.get("week", state.get("week", 0) if isinstance(state, dict) else 0)
                or 0
            )
            if not isinstance(state, dict):
                continue
            for metric in METRICS:
                value = state.get(metric)
                if isinstance(value, (int, float)):
                    bucket[(policy, week_no, metric)].append(float(value))
    rows: list[dict[str, Any]] = []
    for (policy, week_no, metric), values in sorted(bucket.items()):
        rows.append(
            {
                "policy": policy,
                "week": week_no,
                "metric": metric,
                "mean": round(statistics.fmean(values), 4),
                "median": round(statistics.median(values), 4),
                "p10": round(percentile(values, 0.1), 4),
                "p90": round(percentile(values, 0.9), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
            }
        )
    return rows


def compute_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_policy: dict[str, int] = defaultdict(int)
    top_events: Counter[str] = Counter()
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        by_policy[policy] += 1
        for week in run.get("weekly_log", []) or []:
            event_id = str(week.get("triggered_event_id") or week.get("event_id", "") or "")
            if event_id:
                top_events[event_id] += 1
    return {
        "total_runs": len(runs),
        "policies": dict(sorted(by_policy.items())),
        "top_events": dict(top_events.most_common(20)),
    }


def write_csv(
    path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _iter_action_ids(run: dict[str, Any]) -> Iterable[str]:
    """Yield every action id used across the run.

    Supports both the legacy schema (``weekly_log[].actions``) and the
    v0.2 ``study-in-germany`` schema (``weekly_log[].selected_action_ids``
    and ``action_sequence[].actions``).
    """
    for week in run.get("weekly_log", []) or []:
        for key in ("selected_action_ids", "actions"):
            for action_id in week.get(key, []) or []:
                yield str(action_id)
    for step in run.get("action_sequence", []) or []:
        for action_id in step.get("actions", []) or []:
            yield str(action_id)


__all__ = [
    "METRICS",
    "NON_NEGATIVE_METRICS",
    "UPPER_BOUNDED_METRICS",
    "compute_action_pick_rates",
    "compute_choice_pick_rates",
    "compute_ending_distribution",
    "compute_event_trigger_rates",
    "compute_summary",
    "compute_weekly_stats",
    "load_runs",
    "percentile",
    "write_csv",
]
