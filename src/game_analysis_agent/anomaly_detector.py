"""Lightweight invariant & anomaly detector for ``raw_runs.jsonl``.

The detector is intentionally deterministic — it produces a list of
:class:`game_analysis_agent.schemas.Anomaly` rows. Output is meant to be:

1. written to ``bugs.jsonl`` for downstream machine readers (incl. the
   ``bug_hunter`` agent and CI gates);
2. passed to :mod:`game_analysis_agent.bug_summarizer` to produce a grouped
   ``bugs_summary.md`` for humans.

It supports both the legacy v0.1 schema (``weekly_log[].actions`` /
``choice_id``) and the v0.2 ``study-in-germany`` schema
(``selected_action_ids`` / ``triggered_event_id`` / ``event_choice_id``
/ ``after_state``).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from game_analysis_agent.analytics import (
    NON_NEGATIVE_METRICS,
    UPPER_BOUNDED_METRICS,
)
from game_analysis_agent.anomaly_semantics import check_semantic_invariants
from game_analysis_agent.schemas import (
    Anomaly,
    AnomalyKind,
    AnomalySeverity,
)

# Default thresholds; tune per-project in tests / profile YAML.
DEFAULT_SPIKE_ABS = 30       # a single-week delta above this fires `single_week_spike`
DEFAULT_DEAD_STATE_WEEKS = 5  # N consecutive weeks with zero deltas fires `dead_state`


def detect_anomalies(
    runs: Iterable[dict[str, Any]],
    *,
    spike_abs: int = DEFAULT_SPIKE_ABS,
    dead_state_weeks: int = DEFAULT_DEAD_STATE_WEEKS,
) -> list[Anomaly]:
    """Return a flat list of anomalies covering every run."""
    anomalies: list[Anomaly] = []
    for run_idx, run in enumerate(runs):
        anomalies.extend(_scan_single_run(run, spike_abs, dead_state_weeks))
    return anomalies


def _scan_single_run(
    run: dict[str, Any],
    spike_abs: int,
    dead_state_weeks: int,
) -> list[Anomaly]:
    anomalies: list[Anomaly] = []
    run_id = int(run.get("run_id", 0))
    policy = str(run.get("policy", "unknown"))
    weekly_log = run.get("weekly_log", []) or []
    seen_events: dict[str, int] = defaultdict(int)
    prev_state: dict[str, float] | None = None
    dead_streak = 0

    for week in weekly_log:
        week_no = int(week.get("week", 0) or 0)
        state = week.get("after_state") or week.get("state") or {}
        if not isinstance(state, dict):
            continue

        # Bounded-stat invariants (stat ∈ [0, 100] for the bounded metrics)
        for metric in UPPER_BOUNDED_METRICS:
            value = state.get(metric)
            if not isinstance(value, (int, float)):
                continue
            fv = float(value)
            if fv < 0:
                anomalies.append(
                    _mk(
                        "stat_underflow",
                        run_id,
                        week_no,
                        policy,
                        severity="error",
                        evidence={"metric": metric, "value": fv},
                        message=f"`{metric}` dropped below 0 ({fv}).",
                    )
                )
            elif fv > 100:
                anomalies.append(
                    _mk(
                        "stat_overflow",
                        run_id,
                        week_no,
                        policy,
                        severity="error",
                        evidence={"metric": metric, "value": fv},
                        message=f"`{metric}` exceeded 100 ({fv}).",
                    )
                )

        # Non-negative invariants (money, work-hours counters, etc.)
        for metric in NON_NEGATIVE_METRICS:
            value = state.get(metric)
            if not isinstance(value, (int, float)):
                continue
            fv = float(value)
            if fv < 0:
                kind: AnomalyKind = (
                    "negative_money"
                    if metric in {"money", "blocked_account_balance"}
                    else "stat_underflow"
                )
                anomalies.append(
                    _mk(
                        kind,
                        run_id,
                        week_no,
                        policy,
                        severity="critical" if metric in {"money"} else "error",
                        evidence={"metric": metric, "value": fv},
                        message=f"`{metric}` went negative ({fv}).",
                    )
                )

        # Single-week spikes
        if prev_state is not None:
            for metric in UPPER_BOUNDED_METRICS:
                cur = state.get(metric)
                prv = prev_state.get(metric)
                if not isinstance(cur, (int, float)) or not isinstance(prv, (int, float)):
                    continue
                delta = float(cur) - float(prv)
                if abs(delta) >= spike_abs:
                    anomalies.append(
                        _mk(
                            "single_week_spike",
                            run_id,
                            week_no,
                            policy,
                            severity="warning",
                            evidence={
                                "metric": metric,
                                "from": float(prv),
                                "to": float(cur),
                                "delta": delta,
                            },
                            message=(
                                f"`{metric}` jumped from {prv} to {cur} in a single "
                                f"week (Δ={delta:+.1f})."
                            ),
                        )
                    )

        # Dead state detection: numeric state identical for N consecutive weeks
        flat = _flatten_numeric_state(state)
        if prev_state is not None and flat == prev_state:
            dead_streak += 1
            if dead_streak >= dead_state_weeks:
                anomalies.append(
                    _mk(
                        "dead_state",
                        run_id,
                        week_no,
                        policy,
                        severity="warning",
                        evidence={"streak_weeks": dead_streak, "state": flat},
                        message=(
                            f"State identical to previous week for "
                            f"{dead_streak} consecutive weeks."
                        ),
                    )
                )
        else:
            dead_streak = 0
        prev_state = flat

        # Non-repeatable event triggering more than once
        event_id = str(week.get("triggered_event_id") or week.get("event_id", "") or "")
        if event_id:
            seen_events[event_id] += 1
            if seen_events[event_id] > 1:
                # We can only be sure it's a bug if the event is non-repeatable.
                # We assume non-repeatable by default since `study-in-germany`
                # sets `repeatable = false` for the vast majority.
                anomalies.append(
                    _mk(
                        "non_repeatable_event_repeated",
                        run_id,
                        week_no,
                        policy,
                        severity="warning",
                        evidence={
                            "event_id": event_id,
                            "trigger_count": seen_events[event_id],
                        },
                        message=(
                            f"Non-repeatable event `{event_id}` triggered "
                            f"{seen_events[event_id]} times in run {run_id}."
                        ),
                    )
                )

        # Cost_money exceeded the balance immediately before that action.
        # Never use after_state here: doing so applies the same cost twice and
        # turns normal purchases into false positives.
        effects = week.get("action_effects", []) or []
        before_state = week.get("before_state")
        action_balance = (
            before_state.get("money") if isinstance(before_state, dict) else None
        )
        for effect_record in effects:
            if not isinstance(effect_record, dict):
                continue
            effects_dict = effect_record.get("effects", {}) or {}
            cost_money = int(effects_dict.get("money", 0))
            balance_before = action_balance
            if (
                cost_money < 0
                and isinstance(balance_before, (int, float))
                and balance_before + cost_money < 0
            ):
                executed = effect_record.get("executed") is True
                anomalies.append(
                    _mk(
                        "cost_money_exceeds_balance"
                        if executed
                        else "planned_cost_exceeds_balance",
                        run_id,
                        week_no,
                        policy,
                        severity="warning" if executed else "info",
                        evidence={
                            "action_id": effect_record.get("action_id"),
                            "cost_money": cost_money,
                            "balance_before": balance_before,
                            "execution_status": "executed" if executed else "unknown",
                        },
                        message=(
                            f"{'Action' if executed else 'Planned action'} "
                            f"`{effect_record.get('action_id')}` would push money to "
                            f"{balance_before + cost_money}."
                        ),
                    )
                )
            money_delta = effects_dict.get("money", 0)
            if isinstance(action_balance, (int, float)) and isinstance(
                money_delta, (int, float)
            ):
                # The game clamps money at zero and may create arrears. Keep
                # the sequential estimate aligned with that invariant.
                action_balance = max(0, action_balance + money_delta)

        # Week overflow (state.week > max_weeks)
        max_weeks = int(run.get("max_weeks", 20) or 20)
        if week_no > max_weeks:
            anomalies.append(
                _mk(
                    "week_overflow",
                    run_id,
                    week_no,
                    policy,
                    severity="error",
                    evidence={"week": week_no, "max_weeks": max_weeks},
                    message=f"week {week_no} exceeded max_weeks={max_weeks}.",
                )
            )

    # Pipeline stalled guard
    final_ending = (
        run.get("last_ending_id")
        or run.get("final_ending_id")
        or run.get("ending_id")
        or ""
    )
    if final_ending == "pipeline_stalled":
        anomalies.append(
            Anomaly(
                kind="pipeline_stalled",
                severity="warning",
                run_id=run_id,
                week=-1,
                policy=policy,
                message="Run terminated by pipeline_stalled guard.",
            )
        )

    final_ending_id = run.get("final_ending_id") or run.get("ending_id") or ""
    if not final_ending_id or final_ending_id == "unknown":
        anomalies.append(
            Anomaly(
                kind="ending_id_empty",
                severity="info",
                run_id=run_id,
                week=-1,
                policy=policy,
                message="Run ended without producing a concrete ending_id.",
            )
        )

    # Game-semantic invariants (T04). These rules look at the
    # final ending alongside the final / weekly state and the run's
    # flag dict, and surface rule-of-the-game contradictions that the
    # generic invariants cannot catch.
    anomalies.extend(check_semantic_invariants(run))

    return [_with_replay_evidence(anomaly, run) for anomaly in anomalies]


def _flatten_numeric_state(state: dict[str, Any]) -> dict[str, float]:
    """Reduce ``state`` to numeric keys, skipping per-week counters."""
    skip = {"week", "semester"}
    return {
        str(key): float(value)
        for key, value in state.items()
        if isinstance(value, (int, float)) and str(key) not in skip
    }


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


def _with_replay_evidence(anomaly: Anomaly, run: dict[str, Any]) -> Anomaly:
    """Attach seed/week/action context so a finding can be reproduced."""
    evidence = dict(anomaly.evidence)
    if "replay" not in evidence:
        evidence["replay"] = _replay_context(run, anomaly.week)
    return anomaly.model_copy(update={"evidence": evidence})


def _replay_context(run: dict[str, Any], week_no: int) -> dict[str, Any]:
    week_record: dict[str, Any] = {}
    for week in run.get("weekly_log", []) or []:
        if isinstance(week, dict) and int(week.get("week", -999) or -999) == week_no:
            week_record = week
            break
    return {
        "run_id": run.get("run_id"),
        "seed": run.get("seed"),
        "policy": run.get("policy"),
        "difficulty": run.get("difficulty"),
        "scenario": run.get("scenario"),
        "max_weeks": run.get("max_weeks"),
        "week": week_no,
        "actions": (
            week_record.get("selected_action_ids")
            or week_record.get("actions")
            or []
        ),
        "event_id": week_record.get("triggered_event_id") or week_record.get("event_id") or "",
        "event_choice_id": week_record.get("event_choice_id") or week_record.get("choice_id") or "",
    }


def write_anomalies_jsonl(anomalies: Iterable[Anomaly], path: Path) -> int:
    """Persist anomalies as JSONL. Returns count written."""

    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for anomaly in anomalies:
            handle.write(anomaly.model_dump_json())
            handle.write("\n")
            count += 1
    return count


def detect_and_write(runs: list[dict[str, Any]], out_dir: Path) -> list[Anomaly]:
    """Convenience helper used by CLIs: run detect + write JSONL + return."""
    anomalies = detect_anomalies(runs)
    write_anomalies_jsonl(anomalies, out_dir / "anomalies.jsonl")
    return anomalies


__all__ = [
    "DEFAULT_DEAD_STATE_WEEKS",
    "DEFAULT_SPIKE_ABS",
    "detect_anomalies",
    "detect_and_write",
    "write_anomalies_jsonl",
]
