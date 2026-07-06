"""Deterministic quality-gate evaluation for report directories."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


def evaluate_report_dir(report_dir: Path, gates_path: Path) -> dict[str, Any]:
    gates = yaml.safe_load(gates_path.read_text(encoding="utf-8")) or {}
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    _eval_critical(report_dir, gates.get("critical_fail", {}) or {}, failures)
    _eval_balance(report_dir, gates.get("balance", {}) or {}, failures, warnings)
    outcome_summary = _eval_outcomes(
        report_dir,
        gates.get("outcomes", {}) or {},
        failures,
        warnings,
    )
    _eval_design(report_dir, gates.get("design", {}) or {}, warnings)

    return {
        "passed": not failures,
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
        "outcome_summary": outcome_summary,
    }


def write_gate_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _eval_critical(
    report_dir: Path,
    critical: dict[str, Any],
    failures: list[dict[str, Any]],
) -> None:
    counts = _anomaly_counts(report_dir / "anomalies.jsonl")
    for kind, allowed in sorted(critical.items()):
        actual = counts.get(kind, 0)
        if actual > int(allowed):
            failures.append(
                {
                    "gate": f"critical_fail.{kind}",
                    "actual": actual,
                    "threshold": int(allowed),
                    "message": f"{kind} count {actual} exceeds {allowed}",
                }
            )


def _eval_balance(
    report_dir: Path,
    balance: dict[str, Any],
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    endings = _read_csv(report_dir / "ending_distribution.csv")
    actions = _read_csv(report_dir / "action_pick_rates.csv")
    coverage = _read_json(report_dir / "coverage_report.json")

    if endings:
        interactive_playtest = _is_interactive_playtest_distribution(endings)
        max_rate = max(float(row.get("rate", 0) or 0) for row in endings)
        threshold = float(
            balance.get("max_single_ending_rate_normal")
            or balance.get("max_single_ending_rate_realistic")
            or 1.0
        )
        if max_rate > threshold:
            target = warnings if interactive_playtest else failures
            target.append(
                {
                    "gate": "balance.max_single_ending_rate",
                    "actual": round(max_rate, 6),
                    "threshold": threshold,
                    "message": (
                        "single ending dominates the interactive persona batch"
                        if interactive_playtest
                        else "single ending dominates the run batch"
                    ),
                }
            )
        distinct = len({row.get("ending_id", "") for row in endings if row.get("ending_id")})
        min_distinct = int(balance.get("min_distinct_endings_normal", 0) or 0)
        if min_distinct and distinct < min_distinct:
            target = warnings if interactive_playtest else failures
            target.append(
                {
                    "gate": "balance.min_distinct_endings_normal",
                    "actual": distinct,
                    "threshold": min_distinct,
                    "message": (
                        "interactive persona ending variety is below Monte Carlo target"
                        if interactive_playtest
                        else "ending variety is below target"
                    ),
                }
            )

    if actions:
        max_action = max(float(row.get("rate_per_run", 0) or 0) for row in actions)
        threshold = float(balance.get("max_action_rate_per_run", 1.0) or 1.0)
        if max_action > threshold:
            failures.append(
                {
                    "gate": "balance.max_action_rate_per_run",
                    "actual": round(max_action, 6),
                    "threshold": threshold,
                    "message": "one action is picked too often per run",
                }
            )

    regimes = coverage.get("state_regimes", []) if isinstance(coverage, dict) else []
    uncovered = [
        row.get("regime")
        for row in regimes
        if row.get("regime") in {"low_money", "high_stress", "high_hunger"}
        and int(row.get("run_count", 0) or 0) == 0
    ]
    if uncovered:
        warnings.append(
            {
                "gate": "coverage.core_crisis_regimes",
                "actual": uncovered,
                "message": "important crisis regimes were not covered by this batch",
            }
        )


def _eval_design(report_dir: Path, design: dict[str, Any], warnings: list[dict[str, Any]]) -> None:
    # The design gates are mostly LLM/content-validator driven. We only
    # surface missing inputs here so a CI report can tell the operator what
    # was not checked.
    for required in ("content_validation.json", "event_graph.json"):
        if not (report_dir / required).exists():
            warnings.append(
                {
                    "gate": f"design.{required}",
                    "message": f"{required} not found; design gate was not evaluated",
                }
            )


def _eval_outcomes(
    report_dir: Path,
    outcomes: dict[str, Any],
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    endings = _read_csv(report_dir / "ending_distribution.csv")
    if not endings:
        ending_id = _read_playthrough_final_ending(report_dir / "playthrough_summary.md")
        endings = [{"ending_id": ending_id, "count": "1", "rate": "1.0"}] if ending_id else []

    designed_failures = set(_string_list(outcomes.get("designed_failure_endings")))
    mixed = set(_string_list(outcomes.get("recovery_or_mixed_endings")))
    successes = set(_string_list(outcomes.get("success_endings")))
    invalid = set(_string_list(outcomes.get("invalid_endings")))

    summary = {
        "designed_failure_endings": {},
        "recovery_or_mixed_endings": {},
        "success_endings": {},
        "unknown_or_unclassified_endings": {},
    }
    for row in endings:
        ending_id = str(row.get("ending_id", "") or "").strip()
        if not ending_id:
            continue
        count = int(float(row.get("count", 0) or 0))
        rate = float(row.get("rate", 0) or 0)
        payload = {"count": count, "rate": round(rate, 6)}
        if ending_id in invalid:
            failures.append(
                {
                    "gate": "outcomes.invalid_endings",
                    "actual": ending_id,
                    "message": f"{ending_id} is not a valid designed ending",
                }
            )
            summary["unknown_or_unclassified_endings"][ending_id] = payload
        elif ending_id in designed_failures:
            summary["designed_failure_endings"][ending_id] = payload
        elif ending_id in mixed:
            summary["recovery_or_mixed_endings"][ending_id] = payload
        elif ending_id in successes:
            summary["success_endings"][ending_id] = payload
        else:
            summary["unknown_or_unclassified_endings"][ending_id] = payload
            warnings.append(
                {
                    "gate": "outcomes.unclassified_ending",
                    "actual": ending_id,
                    "message": "ending is not classified as success, mixed, designed failure, or invalid",
                }
            )

    max_failure_rate = float(outcomes.get("max_single_designed_failure_rate_play", 0) or 0)
    if max_failure_rate:
        total_count = sum(item["count"] for item in summary["designed_failure_endings"].values())
        total_count += sum(item["count"] for item in summary["success_endings"].values())
        total_count += sum(item["count"] for item in summary["recovery_or_mixed_endings"].values())
        if total_count:
            for ending_id, payload in summary["designed_failure_endings"].items():
                rate = payload["count"] / total_count
                if rate > max_failure_rate:
                    warnings.append(
                        {
                            "gate": "outcomes.max_single_designed_failure_rate_play",
                            "actual": round(rate, 6),
                            "threshold": max_failure_rate,
                            "ending_id": ending_id,
                            "message": "one designed failure outcome dominates playtest personas; this is a balance/design warning, not a hard failure",
                        }
                    )

    if bool(outcomes.get("require_designed_failure_coverage", False)):
        actual_types = len(summary["designed_failure_endings"])
        min_types = int(
            outcomes.get("min_designed_failure_types_normal")
            or outcomes.get("min_designed_failure_types_realistic")
            or 0
        )
        if min_types and endings and actual_types < min_types:
            warnings.append(
                {
                    "gate": "outcomes.min_designed_failure_types",
                    "actual": actual_types,
                    "threshold": min_types,
                    "message": "designed failure endings are under-covered; failure routes are part of the test matrix",
                }
            )
    return summary


def _anomaly_counts(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not path.exists():
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = str(payload.get("kind") or "")
        if kind:
            counts[kind] += 1
    return counts


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _is_interactive_playtest_distribution(rows: list[dict[str, str]]) -> bool:
    return any(str(row.get("policy", "")) == "interactive_personas" for row in rows)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_playthrough_final_ending(path: Path) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- final ending:"):
            parts = line.split("**")
            return parts[1] if len(parts) > 1 else line.rsplit(":", 1)[-1].strip()
    return ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


__all__ = ["evaluate_report_dir", "write_gate_report"]
