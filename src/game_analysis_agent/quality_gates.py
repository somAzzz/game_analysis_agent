"""Deterministic, fail-closed quality-gate evaluation for report directories."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

Cell = tuple[str, str, str]

_ALLOWED_TOP_LEVEL = {"critical_fail", "balance", "outcomes", "design"}
_ALLOWED_KEYS: dict[str, set[str]] = {
    "critical_fail": {
        "ending_id_empty",
        "pipeline_stalled",
        "stat_overflow",
        "stat_underflow",
        "negative_money",
        "non_repeatable_event_repeated",
        "dead_state",
        "week_overflow",
        "single_week_spike",
        "cost_money_exceeds_balance",
        "crisis_success_ending",
        "social_success_under_survival_crisis",
        "academic_success_with_failed_courses",
        "visa_success_without_registration",
        "testdaf_pass_with_low_language",
        "aps_pass_with_low_aps_knowledge",
    },
    "balance": {
        "max_single_ending_rate_normal",
        "max_single_ending_rate_realistic",
        "max_action_rate_per_run",
        "max_action_pick_share",
        "max_recovery_group_rate_per_run",
        "max_escape_group_rate_per_run",
        "min_distinct_endings_normal",
        "min_distinct_endings_realistic",
        "min_study_group_rate_per_run",
        "min_work_group_rate_per_run",
        "min_route_distance",
    },
    "outcomes": {
        "designed_failure_endings",
        "recovery_or_mixed_endings",
        "success_endings",
        "invalid_endings",
        "require_designed_failure_coverage",
        "min_designed_failure_types_normal",
        "min_designed_failure_types_realistic",
        "max_single_designed_failure_rate_play",
    },
    "design": {
        "max_generated_choice_ratio_key_events",
        "min_key_event_tradeoff_score",
        "min_event_trigger_rate_for_key_events",
        "max_playthrough_anomalies_per_5_weeks",
        "min_decision_valid_rate",
        "max_fallback_rate",
        "max_illegal_action_rate",
        "max_llm_error_rate",
    },
}
_LIST_KEYS = {
    "outcomes.designed_failure_endings",
    "outcomes.recovery_or_mixed_endings",
    "outcomes.success_endings",
    "outcomes.invalid_endings",
}
_BOOL_KEYS = {"outcomes.require_designed_failure_coverage"}
_GROUP_GATES = {
    "max_recovery_group_rate_per_run": ("recovery", "max"),
    "max_escape_group_rate_per_run": ("escape", "max"),
    "min_study_group_rate_per_run": ("study", "min"),
    "min_work_group_rate_per_run": ("work", "min"),
}
_GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "recovery": ("sleep", "rest", "nap", "recover", "therapy", "meditat", "yoga"),
    "escape": ("bilibili", "scroll", "binge", "video", "netflix", "tiktok"),
    "study": (
        "study",
        "library",
        "lecture",
        "homework",
        "exam",
        "course",
        "problem",
        "hausarbeit",
    ),
    "work": (
        "work",
        "shift",
        "mini_job",
        "tutoring",
        "part_time",
        "freelance",
        "job",
    ),
}
_GOOD_EFFECT_KEYS = {
    "academic_progress",
    "aps_knowledge",
    "aps_score",
    "blocked_account_balance",
    "career_progress",
    "energy",
    "exam_readiness",
    "gpa_score",
    "language",
    "money",
    "social",
    "visa_progress",
}
_BAD_EFFECT_KEYS = {"failed_courses", "hunger", "loneliness", "stress"}
_GENERIC_CHOICE_TEXTS = {
    "稳妥处理",
    "寻求帮助",
    "冒险推进",
    "暂时回避",
}


def evaluate_report_dir(report_dir: Path, gates_path: Path) -> dict[str, Any]:
    """Evaluate configured gates without treating missing evidence as success."""

    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    gates = _load_gates(gates_path, failures)
    if gates is None:
        return _result(failures, warnings, _empty_outcome_summary(), {}, {})

    _validate_gate_config(gates, failures)
    sections = {
        name: value if isinstance(value, dict) else {}
        for name, value in gates.items()
        if name in _ALLOWED_TOP_LEVEL
    }
    critical = sections.get("critical_fail", {})
    balance = sections.get("balance", {})
    outcomes = sections.get("outcomes", {})
    design = sections.get("design", {})

    manifest = _read_json(
        report_dir / "report_manifest.json",
        failures,
        required=False,
        gate="input.report_manifest",
    )
    defaults = _manifest_defaults(manifest or {})
    difficulty_candidates = _difficulty_candidates(balance, outcomes)

    _eval_critical(report_dir, critical, defaults, failures)

    ending_gates = {
        "max_single_ending_rate_normal",
        "max_single_ending_rate_realistic",
        "min_distinct_endings_normal",
        "min_distinct_endings_realistic",
    }
    action_gates = {
        "max_action_rate_per_run",
        "max_action_pick_share",
        *_GROUP_GATES,
    }
    endings = (
        _read_ending_rows(report_dir, defaults, difficulty_candidates, failures)
        if outcomes or ending_gates.intersection(balance)
        else []
    )
    actions = (
        _read_action_rows(report_dir, defaults, difficulty_candidates, failures)
        if action_gates.intersection(balance)
        else []
    )

    balance_summary = _eval_balance(
        report_dir,
        balance,
        defaults,
        endings,
        actions,
        failures,
        warnings,
    )
    outcome_summary = _eval_outcomes(outcomes, endings, failures, warnings)
    design_summary = _eval_design(
        report_dir,
        design,
        defaults,
        difficulty_candidates,
        failures,
        warnings,
    )
    return _result(
        failures,
        warnings,
        outcome_summary,
        balance_summary,
        design_summary,
    )


def write_gate_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _result(
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    outcomes: dict[str, Any],
    balance: dict[str, Any],
    design: dict[str, Any],
) -> dict[str, Any]:
    return {
        "passed": not failures,
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
        "outcome_summary": outcomes,
        "balance_summary": balance,
        "design_summary": design,
    }


def _load_gates(
    path: Path,
    failures: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        _input_failure(
            failures,
            "gates.yaml",
            "missing",
            str(exc),
            "input.gates_config",
        )
        return None
    try:
        payload = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        _input_failure(
            failures,
            path.name,
            "invalid",
            str(exc),
            "input.gates_config",
        )
        return None
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        _input_failure(
            failures,
            path.name,
            "invalid",
            "gate configuration must be a mapping",
            "input.gates_config",
        )
        return None
    return payload


def _validate_gate_config(
    gates: dict[str, Any],
    failures: list[dict[str, Any]],
) -> None:
    for key in sorted(set(gates) - _ALLOWED_TOP_LEVEL):
        _config_failure(failures, key, "unknown top-level gate section")
    for section in sorted(_ALLOWED_TOP_LEVEL.intersection(gates)):
        values = gates[section]
        if not isinstance(values, dict):
            _config_failure(failures, section, "gate section must be a mapping")
            continue
        for key in sorted(set(values) - _ALLOWED_KEYS[section]):
            _config_failure(failures, f"{section}.{key}", "unknown gate key")
        for key, value in values.items():
            full = f"{section}.{key}"
            if key not in _ALLOWED_KEYS[section]:
                continue
            if full in _LIST_KEYS:
                if not isinstance(value, list) or any(
                    not isinstance(item, str) for item in value
                ):
                    _config_failure(failures, full, "must be a list of strings")
                continue
            if full in _BOOL_KEYS:
                if not isinstance(value, bool):
                    _config_failure(failures, full, "must be a boolean")
                continue
            number = _finite_number(value)
            if number is None or number < 0:
                _config_failure(
                    failures,
                    full,
                    "must be a finite non-negative number",
                )
            elif section == "critical_fail" and not number.is_integer():
                _config_failure(
                    failures,
                    full,
                    "critical anomaly allowance must be an integer",
                )

    outcome_section = gates.get("outcomes")
    if isinstance(outcome_section, dict):
        classifications: dict[str, str] = {}
        for key in (
            "designed_failure_endings",
            "recovery_or_mixed_endings",
            "success_endings",
            "invalid_endings",
        ):
            values = outcome_section.get(key)
            if not isinstance(values, list):
                continue
            for ending in values:
                if not isinstance(ending, str):
                    continue
                previous = classifications.get(ending)
                if previous and previous != key:
                    _config_failure(
                        failures,
                        f"outcomes.{key}",
                        (
                            f"ending {ending!r} is also classified in "
                            f"outcomes.{previous}"
                        ),
                    )
                classifications[ending] = key


def _config_failure(
    failures: list[dict[str, Any]],
    path: str,
    message: str,
) -> None:
    item = {
        "gate": "config.invalid",
        "actual": path,
        "message": f"{path}: {message}",
    }
    if item not in failures:
        failures.append(item)


def _input_failure(
    failures: list[dict[str, Any]],
    filename: str,
    actual: str,
    message: str,
    gate: str | None = None,
) -> None:
    item = {
        "gate": gate or f"input.{filename}",
        "actual": actual,
        "message": f"{filename}: {message}",
    }
    if item not in failures:
        failures.append(item)


def _eval_critical(
    report_dir: Path,
    critical: dict[str, Any],
    defaults: dict[str, str],
    failures: list[dict[str, Any]],
) -> None:
    if not critical:
        return
    rows = _read_jsonl(
        report_dir / "anomalies.jsonl",
        failures,
        required=True,
        allow_empty=True,
        gate="input.anomalies",
    )
    if rows is None:
        return
    counts: Counter[tuple[Cell, str]] = Counter()
    for line, payload in rows:
        kind = str(payload.get("kind") or "").strip()
        if not kind:
            _input_failure(
                failures,
                "anomalies.jsonl",
                "invalid",
                f"line {line} has no anomaly kind",
                "input.anomalies",
            )
            continue
        cell = _payload_cell(payload, defaults, require_difficulty=False)
        counts[(cell, kind)] += 1
    for (cell, kind), actual in sorted(counts.items()):
        if kind not in critical:
            continue
        allowed = _finite_number(critical[kind])
        if allowed is not None and actual > int(allowed):
            failures.append(
                {
                    "gate": f"critical_fail.{kind}",
                    "actual": actual,
                    "threshold": int(allowed),
                    **_cell_payload(cell),
                    "message": (
                        f"{kind} count {actual} exceeds {int(allowed)} "
                        f"in {_cell_label(cell)}"
                    ),
                }
            )


def _read_ending_rows(
    report_dir: Path,
    defaults: dict[str, str],
    difficulty_candidates: set[str],
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = _read_csv(
        report_dir / "ending_distribution.csv",
        {"policy", "ending_id", "count", "rate"},
        failures,
        required=True,
        gate="input.ending_distribution",
    )
    parsed: list[dict[str, Any]] = []
    for line, row in rows or []:
        ending_id = str(row.get("ending_id") or "").strip()
        count = _row_number(
            row, "count", line, "ending_distribution.csv", failures
        )
        rate = _row_number(
            row, "rate", line, "ending_distribution.csv", failures
        )
        cell = _row_cell(
            row,
            defaults,
            difficulty_candidates,
            failures,
            "ending_distribution.csv",
            line,
        )
        if not ending_id:
            _input_failure(
                failures,
                "ending_distribution.csv",
                "invalid",
                f"line {line} has an empty ending_id",
                "input.ending_distribution",
            )
        if count is not None and (count < 0 or not count.is_integer()):
            _input_failure(
                failures,
                "ending_distribution.csv",
                "invalid",
                f"line {line} count must be a non-negative integer",
                "input.ending_distribution",
            )
            count = None
        if rate is not None and not 0 <= rate <= 1:
            _input_failure(
                failures,
                "ending_distribution.csv",
                "invalid",
                f"line {line} rate must be between 0 and 1",
                "input.ending_distribution",
            )
            rate = None
        if (
            ending_id
            and count is not None
            and rate is not None
            and cell is not None
        ):
            parsed.append(
                {
                    "cell": cell,
                    "ending_id": ending_id,
                    "count": int(count),
                    "rate": rate,
                }
            )
    _validate_ending_rates(parsed, failures)
    return parsed


def _read_action_rows(
    report_dir: Path,
    defaults: dict[str, str],
    difficulty_candidates: set[str],
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = _read_csv(
        report_dir / "action_pick_rates.csv",
        {"policy", "action_id", "count", "rate_per_run"},
        failures,
        required=True,
        gate="input.action_pick_rates",
    )
    parsed: list[dict[str, Any]] = []
    seen: set[tuple[Cell, str]] = set()
    for line, row in rows or []:
        action_id = str(row.get("action_id") or "").strip()
        count = _row_number(
            row, "count", line, "action_pick_rates.csv", failures
        )
        rate = _row_number(
            row, "rate_per_run", line, "action_pick_rates.csv", failures
        )
        cell = _row_cell(
            row,
            defaults,
            difficulty_candidates,
            failures,
            "action_pick_rates.csv",
            line,
        )
        if not action_id:
            _input_failure(
                failures,
                "action_pick_rates.csv",
                "invalid",
                f"line {line} has an empty action_id",
                "input.action_pick_rates",
            )
        if count is not None and (count < 0 or not count.is_integer()):
            _input_failure(
                failures,
                "action_pick_rates.csv",
                "invalid",
                f"line {line} count must be a non-negative integer",
                "input.action_pick_rates",
            )
            count = None
        if rate is not None and rate < 0:
            _input_failure(
                failures,
                "action_pick_rates.csv",
                "invalid",
                f"line {line} rate_per_run must be non-negative",
                "input.action_pick_rates",
            )
            rate = None
        identity = (cell, action_id) if cell is not None else None
        if identity and identity in seen:
            _input_failure(
                failures,
                "action_pick_rates.csv",
                "invalid",
                (
                    f"line {line} duplicates action {action_id!r} "
                    f"in {_cell_label(cell)}"
                ),
                "input.action_pick_rates",
            )
        if identity:
            seen.add(identity)
        if (
            action_id
            and count is not None
            and rate is not None
            and cell is not None
        ):
            parsed.append(
                {
                    "cell": cell,
                    "action_id": action_id,
                    "count": int(count),
                    "rate": rate,
                }
            )
    return parsed


def _validate_ending_rates(
    rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> None:
    totals: Counter[Cell] = Counter()
    seen: set[tuple[Cell, str]] = set()
    for row in rows:
        totals[row["cell"]] += row["count"]
        identity = (row["cell"], row["ending_id"])
        if identity in seen:
            _input_failure(
                failures,
                "ending_distribution.csv",
                "invalid",
                (
                    f"duplicate ending {row['ending_id']!r} "
                    f"in {_cell_label(row['cell'])}"
                ),
                "input.ending_distribution",
            )
        seen.add(identity)
    for row in rows:
        total = totals[row["cell"]]
        if total <= 0:
            _input_failure(
                failures,
                "ending_distribution.csv",
                "invalid",
                f"total count is zero in {_cell_label(row['cell'])}",
                "input.ending_distribution",
            )
            continue
        expected = row["count"] / total
        if abs(expected - row["rate"]) > 0.000002:
            _input_failure(
                failures,
                "ending_distribution.csv",
                "invalid",
                (
                    f"rate for {row['ending_id']!r} in "
                    f"{_cell_label(row['cell'])} is {row['rate']}, "
                    f"expected {expected:.6f} from count"
                ),
                "input.ending_distribution",
            )


def _eval_balance(
    report_dir: Path,
    balance: dict[str, Any],
    defaults: dict[str, str],
    endings: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    if not balance:
        return {}
    ending_cells = {row["cell"] for row in endings}
    action_cells = {row["cell"] for row in actions}
    if endings and actions and ending_cells != action_cells:
        for cell in sorted(ending_cells - action_cells):
            _input_failure(
                failures,
                "action_pick_rates.csv",
                "incomplete",
                f"missing rows for {_cell_label(cell)}",
                "input.cell_coverage",
            )
        for cell in sorted(action_cells - ending_cells):
            _input_failure(
                failures,
                "ending_distribution.csv",
                "incomplete",
                f"missing rows for {_cell_label(cell)}",
                "input.cell_coverage",
            )

    summary: dict[str, Any] = {"cells": {}}
    by_ending_cell: dict[Cell, list[dict[str, Any]]] = defaultdict(list)
    for row in endings:
        by_ending_cell[row["cell"]].append(row)
    for cell, rows in sorted(by_ending_cell.items()):
        total = sum(row["count"] for row in rows)
        max_rate = max(
            (row["count"] / total for row in rows),
            default=0.0,
        )
        distinct = sum(row["count"] > 0 for row in rows)
        cell_summary = summary["cells"].setdefault(
            _cell_key(cell),
            _cell_payload(cell),
        )
        cell_summary.update(
            {
                "max_single_ending_rate": round(max_rate, 6),
                "distinct_endings": distinct,
            }
        )

        max_threshold = _difficulty_threshold(
            balance, "max_single_ending_rate", cell, failures
        )
        if max_threshold is not None and max_rate > max_threshold:
            target = warnings if _is_interactive_cell(cell) else failures
            target.append(
                {
                    "gate": "balance.max_single_ending_rate",
                    "configured_gate": (
                        f"balance.max_single_ending_rate_{cell[1]}"
                    ),
                    "actual": round(max_rate, 6),
                    "threshold": max_threshold,
                    **_cell_payload(cell),
                    "message": (
                        "single ending dominates the interactive persona batch"
                        if _is_interactive_cell(cell)
                        else f"single ending dominates {_cell_label(cell)}"
                    ),
                }
            )
        min_threshold = _difficulty_threshold(
            balance, "min_distinct_endings", cell, failures
        )
        if min_threshold is not None and distinct < int(min_threshold):
            target = warnings if _is_interactive_cell(cell) else failures
            target.append(
                {
                    "gate": f"balance.min_distinct_endings_{cell[1]}",
                    "actual": distinct,
                    "threshold": int(min_threshold),
                    **_cell_payload(cell),
                    "message": (
                        "interactive persona ending variety is below "
                        "Monte Carlo target"
                        if _is_interactive_cell(cell)
                        else (
                            "ending variety is below target in "
                            f"{_cell_label(cell)}"
                        )
                    ),
                }
            )

    by_action_cell: dict[Cell, list[dict[str, Any]]] = defaultdict(list)
    for row in actions:
        by_action_cell[row["cell"]].append(row)
    max_action_threshold = _configured_number(
        balance, "max_action_rate_per_run"
    )
    if max_action_threshold is not None:
        for cell, rows in sorted(by_action_cell.items()):
            top = max(rows, key=lambda row: row["rate"])
            summary["cells"].setdefault(
                _cell_key(cell), _cell_payload(cell)
            )["max_action_rate_per_run"] = round(top["rate"], 6)
            if top["rate"] > max_action_threshold:
                target = warnings if _is_interactive_cell(cell) else failures
                target.append(
                    {
                        "gate": "balance.max_action_rate_per_run",
                        "actual": round(top["rate"], 6),
                        "threshold": max_action_threshold,
                        "action_id": top["action_id"],
                        **_cell_payload(cell),
                        "message": (
                            "one action is picked too often in "
                            f"{_cell_label(cell)}"
                        ),
                    }
                )

    max_action_share_threshold = _configured_number(
        balance, "max_action_pick_share"
    )
    if max_action_share_threshold is not None:
        for cell, rows in sorted(by_action_cell.items()):
            total_picks = sum(row["count"] for row in rows)
            top = max(
                rows,
                key=lambda row: row["count"] / max(1, total_picks),
            )
            top_share = top["count"] / max(1, total_picks)
            summary["cells"].setdefault(
                _cell_key(cell), _cell_payload(cell)
            )["max_action_pick_share"] = round(top_share, 6)
            if top_share > max_action_share_threshold:
                target = warnings if _is_interactive_cell(cell) else failures
                target.append(
                    {
                        "gate": "balance.max_action_pick_share",
                        "actual": round(top_share, 6),
                        "threshold": max_action_share_threshold,
                        "action_id": top["action_id"],
                        **_cell_payload(cell),
                        "message": (
                            "one action owns too much of all action picks in "
                            f"{_cell_label(cell)}"
                        ),
                    }
                )

    route_payload = None
    route_path = report_dir / "route_report.json"
    if route_path.exists():
        route_payload = _read_json(
            route_path,
            failures,
            required=False,
            gate="input.route_report",
        )
    catalog_payload = None
    catalog_path = report_dir / "action_catalog.json"
    if catalog_path.exists():
        catalog_payload = _read_json(
            catalog_path,
            failures,
            required=False,
            gate="input.action_catalog",
        )

    configured_group_gates = [
        key for key in _GROUP_GATES if key in balance
    ]
    if configured_group_gates:
        all_action_ids = {row["action_id"] for row in actions}
        memberships = _action_group_memberships(
            all_action_ids,
            route_payload or {},
            catalog_payload or {},
        )
        for cell, rows in sorted(by_action_cell.items()):
            group_rates: Counter[str] = Counter()
            for row in rows:
                for group in memberships.get(row["action_id"], set()):
                    group_rates[group] += row["rate"]
            summary["cells"].setdefault(
                _cell_key(cell), _cell_payload(cell)
            )["group_rates_per_run"] = {
                key: round(value, 6)
                for key, value in sorted(group_rates.items())
            }
            for gate_key in configured_group_gates:
                group, direction = _GROUP_GATES[gate_key]
                threshold = _configured_number(balance, gate_key)
                if threshold is None:
                    continue
                actual = float(group_rates[group])
                violated = (
                    actual > threshold
                    if direction == "max"
                    else actual < threshold
                )
                if violated:
                    target = (
                        warnings if _is_interactive_cell(cell) else failures
                    )
                    target.append(
                        {
                            "gate": f"balance.{gate_key}",
                            "actual": round(actual, 6),
                            "threshold": threshold,
                            "group": group,
                            **_cell_payload(cell),
                            "message": (
                                f"{group} action group rate is outside "
                                f"its {direction}imum target in "
                                f"{_cell_label(cell)}"
                            ),
                        }
                    )

    route_threshold = _configured_number(balance, "min_route_distance")
    if route_threshold is not None:
        summary["route_distances"] = _eval_route_distance(
            report_dir,
            route_payload or {},
            defaults,
            route_threshold,
            failures,
            warnings,
        )

    coverage_path = report_dir / "coverage_report.json"
    if coverage_path.exists():
        coverage = _read_json(
            coverage_path,
            failures,
            required=False,
            gate="input.coverage_report",
        )
        regimes = (
            coverage.get("state_regimes")
            if isinstance(coverage, dict)
            else None
        )
        if regimes is not None and not isinstance(regimes, list):
            _input_failure(
                failures,
                "coverage_report.json",
                "invalid",
                "state_regimes must be a list",
                "input.coverage_report",
            )
        elif isinstance(regimes, list):
            uncovered = [
                row.get("regime")
                for row in regimes
                if isinstance(row, dict)
                and row.get("regime")
                in {"low_money", "high_stress", "high_hunger"}
                and _finite_number(row.get("run_count")) == 0
            ]
            if uncovered:
                warnings.append(
                    {
                        "gate": "coverage.core_crisis_regimes",
                        "actual": uncovered,
                        "message": (
                            "important crisis regimes were not covered "
                            "by this batch"
                        ),
                    }
                )
    return summary


def _action_group_memberships(
    action_ids: Iterable[str],
    route: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, set[str]]:
    result = {action_id: set() for action_id in action_ids}
    tags_used = route.get("action_tags_used")
    if isinstance(tags_used, dict):
        for action_id, group in tags_used.items():
            if (
                str(action_id) in result
                and str(group) in _GROUP_KEYWORDS
            ):
                result[str(action_id)].add(str(group))
    actions = catalog.get("actions")
    if isinstance(actions, list):
        for item in actions:
            if not isinstance(item, dict):
                continue
            action_id = str(item.get("id") or item.get("action_id") or "")
            if action_id not in result:
                continue
            metadata = [
                item.get("type"),
                item.get("group"),
                item.get("cooldown_group"),
                *(
                    item.get("tags")
                    if isinstance(item.get("tags"), list)
                    else []
                ),
            ]
            for value in metadata:
                text = str(value or "").lower()
                if text in _GROUP_KEYWORDS:
                    result[action_id].add(text)
                if text == "avoidance":
                    result[action_id].add("escape")
                if text in {"rest", "mental_recovery"}:
                    result[action_id].add("recovery")
    for action_id in result:
        lowered = action_id.lower()
        for group, keywords in _GROUP_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                result[action_id].add(group)
    return result


def _eval_route_distance(
    report_dir: Path,
    route: dict[str, Any],
    defaults: dict[str, str],
    threshold: float,
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_paths = []
    raw_path = report_dir / "raw_runs.jsonl"
    if raw_path.exists():
        raw_paths.append(raw_path)
    raw_paths.extend(_validation_prerequisite_paths(report_dir, failures))
    if raw_paths:
        combined_runs: list[dict[str, Any]] = []
        seen_paths: set[Path] = set()
        for candidate in raw_paths:
            resolved = candidate.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            raw_rows = _read_jsonl(
                candidate,
                failures,
                required=True,
                allow_empty=False,
                gate="input.raw_runs",
            )
            if raw_rows is not None:
                combined_runs.extend(payload for _, payload in raw_rows)
        if combined_runs:
            return _route_distances_from_runs(
                combined_runs,
                defaults,
                threshold,
                failures,
                warnings,
            )

    explicit = _explicit_route_distances(route, defaults, failures)
    if explicit:
        for item in explicit:
            if item["distance"] < threshold:
                cell = item["cell"]
                target = warnings if _is_interactive_cell(cell) else failures
                target.append(
                    {
                        "gate": "balance.min_route_distance",
                        "actual": round(item["distance"], 6),
                        "threshold": threshold,
                        **_cell_payload(cell),
                        "message": (
                            "route distance is below target in "
                            f"{_cell_label(cell)}"
                        ),
                    }
                )
        return [
            {
                **_cell_payload(item["cell"]),
                "distance": round(item["distance"], 6),
            }
            for item in explicit
        ]

    findings = route.get("route_separation")
    if isinstance(findings, list) and findings:
        emitted = []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            target_id = str(
                finding.get("target_id")
                or defaults.get("policy")
                or "unknown"
            )
            policy = target_id.split(":", 1)[0]
            cell = (
                policy,
                defaults.get("difficulty", "unspecified"),
                defaults.get("scenario", "default"),
            )
            failures.append(
                {
                    "gate": "balance.min_route_distance",
                    "actual": f"less than {threshold}",
                    "threshold": threshold,
                    **_cell_payload(cell),
                    "message": str(
                        finding.get("description")
                        or "route separation finding"
                    ),
                }
            )
            emitted.append(
                {
                    **_cell_payload(cell),
                    "distance": None,
                    "finding": True,
                }
            )
        if emitted:
            return emitted

    _input_failure(
        failures,
        "route_report.json/raw_runs.jsonl",
        "missing_or_incomplete",
        (
            "min_route_distance requires raw runs with a balanced "
            "comparator or explicit route distances"
        ),
        "input.route_distance",
    )
    return []


def _validation_prerequisite_paths(
    report_dir: Path,
    failures: list[dict[str, Any]],
) -> list[Path]:
    summary_path = report_dir / "validation_summary.json"
    if not summary_path.exists():
        return []
    summary = _read_json(
        summary_path,
        failures,
        required=False,
        gate="input.validation_summary",
    )
    prerequisites = summary.get("prerequisites") if isinstance(summary, dict) else None
    if prerequisites is None:
        return []
    if not isinstance(prerequisites, list):
        _input_failure(
            failures,
            "validation_summary.json",
            "invalid",
            "prerequisites must be a list",
            "input.validation_summary",
        )
        return []
    paths = []
    for item in prerequisites:
        if not isinstance(item, dict):
            continue
        logical = str(item.get("logical_path") or "")
        raw_path = item.get("path")
        if not logical.endswith(".jsonl") or not isinstance(raw_path, str):
            continue
        candidate = Path(raw_path)
        if candidate.is_file():
            paths.append(candidate)
    return paths


def _route_distances_from_runs(
    runs: list[dict[str, Any]],
    defaults: dict[str, str],
    threshold: float,
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    axes = {
        "academic": "academic_progress",
        "work": "money",
        "social": "social",
        "admin": "visa_progress",
        "slacker": "stress",
    }
    values: dict[Cell, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for index, run in enumerate(runs, start=1):
        cell = _payload_cell(run, defaults, require_difficulty=False)
        state = run.get("final_state")
        if not isinstance(state, dict):
            log = run.get("weekly_log")
            if isinstance(log, list) and log and isinstance(log[-1], dict):
                state = (
                    log[-1].get("after_state")
                    or log[-1].get("state_after")
                )
        if not isinstance(state, dict):
            _input_failure(
                failures,
                "raw_runs.jsonl",
                "invalid",
                f"run {index} has no final state for route distance",
                "input.raw_runs",
            )
            continue
        present = 0
        for axis, key in axes.items():
            number = _finite_number(state.get(key))
            if number is not None:
                values[cell][axis].append(number)
                present += 1
        if not present:
            _input_failure(
                failures,
                "raw_runs.jsonl",
                "invalid",
                f"run {index} has no route axis metrics",
                "input.raw_runs",
            )

    by_context: dict[tuple[str, str], list[Cell]] = defaultdict(list)
    for cell in values:
        by_context[(cell[1], cell[2])].append(cell)
    results: list[dict[str, Any]] = []
    comparison_count = 0
    for (difficulty, scenario), cells in sorted(by_context.items()):
        baseline_cell = next(
            (cell for cell in cells if cell[0] == "balanced"),
            None,
        )
        alternatives = [cell for cell in cells if cell[0] != "balanced"]
        if baseline_cell is None or not alternatives:
            _input_failure(
                failures,
                "raw_runs.jsonl",
                "incomplete",
                (
                    "route distance requires balanced and non-balanced "
                    f"policies for difficulty={difficulty}, "
                    f"scenario={scenario}"
                ),
                "input.route_distance",
            )
            continue
        baseline = values[baseline_cell]
        for cell in alternatives:
            distances = []
            for axis in axes:
                ours = values[cell].get(axis, [])
                reference = baseline.get(axis, [])
                if not ours or not reference:
                    continue
                ours_mean = sum(ours) / len(ours)
                ref_mean = sum(reference) / len(reference)
                distances.append(
                    abs(ours_mean - ref_mean)
                    / max(1.0, abs(ref_mean))
                )
            if not distances:
                _input_failure(
                    failures,
                    "raw_runs.jsonl",
                    "incomplete",
                    f"no comparable route axes for {_cell_label(cell)}",
                    "input.route_distance",
                )
                continue
            comparison_count += 1
            distance = min(distances)
            results.append(
                {
                    **_cell_payload(cell),
                    "distance": round(distance, 6),
                }
            )
            if distance < threshold:
                target = warnings if _is_interactive_cell(cell) else failures
                target.append(
                    {
                        "gate": "balance.min_route_distance",
                        "actual": round(distance, 6),
                        "threshold": threshold,
                        **_cell_payload(cell),
                        "message": (
                            "route distance is below target in "
                            f"{_cell_label(cell)}"
                        ),
                    }
                )
    if not comparison_count and not by_context:
        _input_failure(
            failures,
            "raw_runs.jsonl",
            "incomplete",
            "no usable runs for route distance",
            "input.route_distance",
        )
    return results


def _explicit_route_distances(
    route: dict[str, Any],
    defaults: dict[str, str],
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    payload = route.get("route_distances", route.get("distances"))
    if isinstance(payload, dict):
        payload = [
            {"policy": policy, "distance": value}
            for policy, value in payload.items()
        ]
    if not isinstance(payload, list):
        return []
    result = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            _input_failure(
                failures,
                "route_report.json",
                "invalid",
                f"route distance row {index} must be an object",
                "input.route_report",
            )
            continue
        distance = _finite_number(
            item.get("distance", item.get("value"))
        )
        if distance is None or distance < 0:
            _input_failure(
                failures,
                "route_report.json",
                "invalid",
                f"route distance row {index} has an invalid distance",
                "input.route_report",
            )
            continue
        cell = _payload_cell(item, defaults, require_difficulty=False)
        result.append({"cell": cell, "distance": distance})
    return result


def _eval_outcomes(
    outcomes: dict[str, Any],
    endings: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = _empty_outcome_summary()
    if not outcomes:
        return summary
    designed = set(_string_list(outcomes.get("designed_failure_endings")))
    mixed = set(_string_list(outcomes.get("recovery_or_mixed_endings")))
    successes = set(_string_list(outcomes.get("success_endings")))
    invalid = set(_string_list(outcomes.get("invalid_endings")))
    by_cell: dict[Cell, list[dict[str, Any]]] = defaultdict(list)
    aggregates: dict[str, Counter[str]] = {
        "designed_failure_endings": Counter(),
        "recovery_or_mixed_endings": Counter(),
        "success_endings": Counter(),
        "unknown_or_unclassified_endings": Counter(),
    }
    for row in endings:
        by_cell[row["cell"]].append(row)
    for cell, rows in sorted(by_cell.items()):
        cell_total = sum(row["count"] for row in rows)
        cell_summary = {
            "designed_failure_endings": {},
            "recovery_or_mixed_endings": {},
            "success_endings": {},
            "unknown_or_unclassified_endings": {},
        }
        for row in rows:
            ending_id = row["ending_id"]
            payload = {
                "count": row["count"],
                "rate": round(row["count"] / max(1, cell_total), 6),
            }
            if ending_id in invalid:
                category = "unknown_or_unclassified_endings"
                failures.append(
                    {
                        "gate": "outcomes.invalid_endings",
                        "actual": ending_id,
                        **_cell_payload(cell),
                        "message": (
                            f"{ending_id} is not a valid designed ending"
                        ),
                    }
                )
            elif ending_id in designed:
                category = "designed_failure_endings"
            elif ending_id in mixed:
                category = "recovery_or_mixed_endings"
            elif ending_id in successes:
                category = "success_endings"
            else:
                category = "unknown_or_unclassified_endings"
                warnings.append(
                    {
                        "gate": "outcomes.unclassified_ending",
                        "actual": ending_id,
                        **_cell_payload(cell),
                        "message": (
                            "ending is not classified as success, mixed, "
                            "designed failure, or invalid"
                        ),
                    }
                )
            cell_summary[category][ending_id] = payload
            aggregates[category][ending_id] += row["count"]
        summary["cells"][_cell_key(cell)] = {
            **_cell_payload(cell),
            **cell_summary,
        }

        max_failure = _configured_number(
            outcomes, "max_single_designed_failure_rate_play"
        )
        if max_failure is not None:
            for ending_id, payload in cell_summary[
                "designed_failure_endings"
            ].items():
                if payload["rate"] > max_failure:
                    warnings.append(
                        {
                            "gate": (
                                "outcomes."
                                "max_single_designed_failure_rate_play"
                            ),
                            "actual": payload["rate"],
                            "threshold": max_failure,
                            "ending_id": ending_id,
                            **_cell_payload(cell),
                            "message": (
                                "one designed failure outcome dominates "
                                "playtest personas; this is a balance/design "
                                "warning, not a hard failure"
                            ),
                        }
                    )
        if outcomes.get("require_designed_failure_coverage") is True:
            min_types = _difficulty_threshold(
                outcomes,
                "min_designed_failure_types",
                cell,
                failures,
            )
            actual_types = len(
                cell_summary["designed_failure_endings"]
            )
            if min_types is not None and actual_types < int(min_types):
                warnings.append(
                    {
                        "gate": "outcomes.min_designed_failure_types",
                        "actual": actual_types,
                        "threshold": int(min_types),
                        **_cell_payload(cell),
                        "message": (
                            "designed failure endings are under-covered; "
                            "failure routes are part of the test matrix"
                        ),
                    }
                )

    aggregate_total = sum(
        sum(counter.values()) for counter in aggregates.values()
    )
    for category, counter in aggregates.items():
        summary[category] = {
            ending_id: {
                "count": count,
                "rate": round(count / max(1, aggregate_total), 6),
            }
            for ending_id, count in sorted(counter.items())
        }
    return summary


def _empty_outcome_summary() -> dict[str, Any]:
    return {
        "designed_failure_endings": {},
        "recovery_or_mixed_endings": {},
        "success_endings": {},
        "unknown_or_unclassified_endings": {},
        "cells": {},
    }


def _eval_design(
    report_dir: Path,
    design: dict[str, Any],
    defaults: dict[str, str],
    difficulty_candidates: set[str],
    failures: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    if not design:
        return {}
    summary: dict[str, Any] = {}
    content = None
    content_path = report_dir / "content_validation.json"
    if content_path.exists():
        content = _read_json(
            content_path,
            failures,
            required=False,
            gate="input.content_validation",
        )
        if content is not None:
            errors = content.get("errors", [])
            content_warnings = content.get("warnings", [])
            if not isinstance(errors, list) or not isinstance(
                content_warnings,
                list,
            ):
                _input_failure(
                    failures,
                    "content_validation.json",
                    "invalid",
                    "errors and warnings must be lists",
                    "input.content_validation",
                )
            else:
                summary["content_validation"] = {
                    "error_count": len(errors),
                    "warning_count": len(content_warnings),
                }
                if errors:
                    failures.append(
                        {
                            "gate": "design.content_validation_errors",
                            "actual": len(errors),
                            "threshold": 0,
                            "message": "content validation reported errors",
                        }
                    )
                if content_warnings:
                    warnings.append(
                        {
                            "gate": "design.content_validation_warnings",
                            "actual": len(content_warnings),
                            "message": "content validation reported warnings",
                        }
                    )

    event_keys = {
        "max_generated_choice_ratio_key_events",
        "min_key_event_tradeoff_score",
        "min_event_trigger_rate_for_key_events",
    }
    event_graph = None
    if event_keys.intersection(design):
        event_graph = _read_json(
            report_dir / "event_graph.json",
            failures,
            required=True,
            gate="input.event_graph",
        )
    key_events = (
        _key_events(event_graph or {}, failures)
        if event_graph is not None
        else []
    )

    if "max_generated_choice_ratio_key_events" in design:
        threshold = _configured_number(
            design, "max_generated_choice_ratio_key_events"
        )
        actual = _first_metric(
            [content or {}, event_graph or {}],
            (
                "generated_choice_ratio_key_events",
                "key_event_generated_choice_ratio",
            ),
        )
        if actual is None:
            actual = _generated_choice_ratio(key_events)
        if actual is None:
            _input_failure(
                failures,
                "content_validation.json/event_graph.json",
                "incomplete",
                (
                    "no generated-choice markers or aggregate metric "
                    "for key events"
                ),
                "input.design.generated_choice_ratio",
            )
        elif threshold is not None:
            summary["generated_choice_ratio_key_events"] = round(actual, 6)
            if actual > threshold:
                failures.append(
                    {
                        "gate": (
                            "design."
                            "max_generated_choice_ratio_key_events"
                        ),
                        "actual": round(actual, 6),
                        "threshold": threshold,
                        "message": (
                            "generated choices exceed the key-event limit"
                        ),
                    }
                )

    if "min_key_event_tradeoff_score" in design:
        threshold = _configured_number(
            design, "min_key_event_tradeoff_score"
        )
        actual = _first_metric(
            [content or {}, event_graph or {}],
            (
                "key_event_tradeoff_score",
                "mean_key_event_tradeoff_score",
            ),
        )
        if actual is None:
            actual = _derived_tradeoff_score(key_events)
        if actual is None:
            _input_failure(
                failures,
                "content_validation.json/event_graph.json",
                "incomplete",
                (
                    "no key-event tradeoff score and event choices "
                    "cannot be scored"
                ),
                "input.design.tradeoff_score",
            )
        elif threshold is not None:
            summary["key_event_tradeoff_score"] = round(actual, 6)
            if actual < threshold:
                failures.append(
                    {
                        "gate": "design.min_key_event_tradeoff_score",
                        "actual": round(actual, 6),
                        "threshold": threshold,
                        "message": (
                            "key-event choice tradeoffs are below target"
                        ),
                    }
                )

    if "min_event_trigger_rate_for_key_events" in design:
        threshold = _configured_number(
            design, "min_event_trigger_rate_for_key_events"
        )
        event_rows = _read_event_rate_rows(
            report_dir,
            defaults,
            difficulty_candidates,
            failures,
        )
        event_ids = {
            str(event.get("id") or event.get("event_id") or "")
            for event in key_events
        }
        event_ids.discard("")
        if not event_ids:
            _input_failure(
                failures,
                "event_graph.json",
                "incomplete",
                "no key event ids are available for trigger-rate evaluation",
                "input.design.key_events",
            )
        elif threshold is not None and event_rows:
            rates: dict[tuple[Cell, str], float] = {
                (row["cell"], row["event_id"]): row["rate"]
                for row in event_rows
            }
            cells = sorted({row["cell"] for row in event_rows})
            cell_summary = {}
            for cell in cells:
                minimum = min(
                    rates.get((cell, event_id), 0.0)
                    for event_id in event_ids
                )
                cell_summary[_cell_key(cell)] = {
                    **_cell_payload(cell),
                    "minimum_key_event_trigger_rate": round(minimum, 6),
                }
                for event_id in sorted(event_ids):
                    actual = rates.get((cell, event_id), 0.0)
                    if actual < threshold:
                        target = (
                            warnings if _is_interactive_cell(cell) else failures
                        )
                        target.append(
                            {
                                "gate": (
                                    "design."
                                    "min_event_trigger_rate_for_key_events"
                                ),
                                "actual": round(actual, 6),
                                "threshold": threshold,
                                "event_id": event_id,
                                **_cell_payload(cell),
                                "message": (
                                    "key event trigger rate is below "
                                    f"target in {_cell_label(cell)}"
                                ),
                            }
                        )
            summary["event_trigger_cells"] = cell_summary

    eval_keys = {
        "min_decision_valid_rate",
        "max_fallback_rate",
        "max_illegal_action_rate",
        "max_llm_error_rate",
    }
    agent_eval = None
    agent_eval_path = report_dir / "agent_eval.json"
    play_paths = sorted(report_dir.rglob("playthrough.jsonl"))
    has_play_evidence = agent_eval_path.exists() or bool(play_paths)
    configured_eval = eval_keys.intersection(design)
    if configured_eval and has_play_evidence:
        agent_eval = _read_json(
            agent_eval_path,
            failures,
            required=True,
            gate="input.agent_eval",
        )
        if agent_eval is not None:
            eval_errors = agent_eval.get("errors")
            if agent_eval.get("schema_version") != "agent-eval-v1":
                _input_failure(
                    failures,
                    "agent_eval.json",
                    "invalid",
                    "schema_version must be 'agent-eval-v1'",
                    "input.agent_eval",
                )
                agent_eval = None
            elif agent_eval.get("valid") is not True:
                _input_failure(
                    failures,
                    "agent_eval.json",
                    "invalid",
                    "valid must be true",
                    "input.agent_eval",
                )
                agent_eval = None
            elif not isinstance(eval_errors, list) or eval_errors:
                _input_failure(
                    failures,
                    "agent_eval.json",
                    "invalid",
                    "errors must be an empty list",
                    "input.agent_eval",
                )
                agent_eval = None

        if agent_eval is not None:
            metrics = agent_eval.get("metrics")
            if not isinstance(metrics, dict):
                _input_failure(
                    failures,
                    "agent_eval.json",
                    "invalid",
                    "metrics must be an object",
                    "input.agent_eval",
                )
                agent_eval = None
            else:
                steps = _finite_number(metrics.get("steps"))
                if steps is None or steps <= 0:
                    _input_failure(
                        failures,
                        "agent_eval.json",
                        "incomplete",
                        "metrics.steps must be greater than zero",
                        "input.agent_eval",
                    )
    elif agent_eval_path.exists():
        agent_eval = _read_json(
            agent_eval_path,
            failures,
            required=False,
            gate="input.agent_eval",
        )
    elif configured_eval:
        warnings.append(
            {
                "gate": "design.agent_eval_not_applicable",
                "message": (
                    "Agent decision metrics are not applicable to this "
                    "Monte Carlo report"
                ),
            }
        )

    if agent_eval is not None:
        metrics = agent_eval.get("metrics", {})
        mappings = {
            "min_decision_valid_rate": (
                ("final_valid_rate", "decision_valid_rate"),
                "min",
            ),
            "max_fallback_rate": (("fallback_rate",), "max"),
            "max_illegal_action_rate": (("illegal_action_rate",), "max"),
            "max_llm_error_rate": (("llm_error_rate",), "max"),
        }
        eval_summary = {}
        for gate_key, (metric_names, direction) in mappings.items():
            if gate_key not in design:
                continue
            actual = _metric_from_mapping(metrics, metric_names)
            threshold = _configured_number(design, gate_key)
            if actual is None:
                _input_failure(
                    failures,
                    "agent_eval.json",
                    "incomplete",
                    f"metrics is missing {' or '.join(metric_names)}",
                    "input.agent_eval",
                )
                continue
            eval_summary[metric_names[0]] = round(actual, 6)
            if threshold is None:
                continue
            violated = (
                actual < threshold
                if direction == "min"
                else actual > threshold
            )
            if violated:
                failures.append(
                    {
                        "gate": f"design.{gate_key}",
                        "actual": round(actual, 6),
                        "threshold": threshold,
                        "message": (
                            "agent evaluation "
                            f"{metric_names[0]} is outside target"
                        ),
                    }
                )
        if eval_summary:
            summary["agent_eval"] = eval_summary

    anomaly_gate = "max_playthrough_anomalies_per_5_weeks"
    if anomaly_gate in design and has_play_evidence:
        threshold = _configured_number(design, anomaly_gate)
        anomaly_rate = None
        if agent_eval is not None:
            anomaly_rate = _metric_from_mapping(
                agent_eval.get("metrics", {}),
                ("anomaly_rate_per_5_weeks",),
            )
        play_rates = []
        if anomaly_rate is None:
            play_rates = _playthrough_anomaly_rates(report_dir, failures)
            if not play_rates:
                _input_failure(
                    failures,
                    "agent_eval.json/playthrough.jsonl",
                    "missing_or_incomplete",
                    (
                        "no anomaly_rate_per_5_weeks metric or usable "
                        "playthrough trace"
                    ),
                    "input.design.playthrough_anomalies",
                )
        else:
            play_rates = [
                {"source": "agent_eval.json", "rate": anomaly_rate}
            ]
        summary["playthrough_anomaly_rates"] = play_rates
        if threshold is not None:
            for item in play_rates:
                if item["rate"] > threshold:
                    failures.append(
                        {
                            "gate": (
                                "design."
                                "max_playthrough_anomalies_per_5_weeks"
                            ),
                            "actual": round(item["rate"], 6),
                            "threshold": threshold,
                            "source": item["source"],
                            "message": (
                                "playthrough anomaly rate exceeds target"
                            ),
                        }
                    )
    elif anomaly_gate in design:
        warnings.append(
            {
                "gate": "design.playthrough_anomalies_not_applicable",
                "message": (
                    "Playthrough anomaly metrics are not applicable to this "
                    "Monte Carlo report"
                ),
            }
        )
    return summary


def _key_events(
    event_graph: dict[str, Any],
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events = event_graph.get("events")
    if not isinstance(events, list):
        _input_failure(
            failures,
            "event_graph.json",
            "invalid",
            "events must be a list",
            "input.event_graph",
        )
        return []
    valid = [event for event in events if isinstance(event, dict)]
    explicit = [
        event
        for event in valid
        if (
            "is_key_event" in event
            or "key_event" in event
            or "key" in event
        )
    ]
    if explicit:
        return [
            event
            for event in explicit
            if bool(
                event.get(
                    "is_key_event",
                    event.get("key_event", event.get("key")),
                )
            )
        ]
    return [
        event
        for event in valid
        if (
            str(
                event.get("event_type") or event.get("type") or ""
            ).lower()
            == "fixed"
            or "key"
            in {
                str(tag).lower()
                for tag in event.get("tags", [])
                if isinstance(tag, str)
            }
        )
    ]


def _generated_choice_ratio(
    events: list[dict[str, Any]],
) -> float | None:
    generated = 0
    total = 0
    marker_seen = False
    for event in events:
        explicit_count = _finite_number(
            event.get("generated_choice_count")
        )
        choice_count = _finite_number(event.get("choice_count"))
        if (
            explicit_count is not None
            and choice_count is not None
            and choice_count >= 0
        ):
            marker_seen = True
            generated += int(explicit_count)
            total += int(choice_count)
            continue
        choices = event.get("choices")
        if not isinstance(choices, list):
            continue
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            total += 1
            marker = None
            if "is_generated" in choice:
                marker = bool(choice["is_generated"])
            elif "generated" in choice:
                marker = bool(choice["generated"])
            elif "source" in choice:
                marker = str(choice["source"]).lower() in {
                    "generated",
                    "llm",
                    "fallback",
                }
            if marker is not None:
                marker_seen = True
                generated += int(marker)
    if marker_seen and total > 0:
        return generated / total

    # Current Godot exports predate explicit generated markers. Generic
    # fallback labels are still deterministic evidence, so derive the ratio
    # instead of failing every otherwise valid Monte Carlo report.
    generic = 0
    total = 0
    for event in events:
        choices = event.get("choices")
        if not isinstance(choices, list):
            continue
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            total += 1
            if str(choice.get("text") or "").strip() in _GENERIC_CHOICE_TEXTS:
                generic += 1
    return generic / total if total else None


def _derived_tradeoff_score(
    events: list[dict[str, Any]],
) -> float | None:
    scores = []
    for event in events:
        explicit = _finite_number(event.get("tradeoff_score"))
        if explicit is not None:
            scores.append(explicit)
            continue
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices:
            continue
        scored = [
            choice for choice in choices if isinstance(choice, dict)
        ]
        if not scored:
            continue
        scores.append(
            sum(_choice_has_tradeoff(choice) for choice in scored)
            / len(scored)
        )
    return sum(scores) / len(scores) if scores else None


def _choice_has_tradeoff(choice: dict[str, Any]) -> bool:
    effects = choice.get("success_effects") or choice.get("effects") or {}
    if not isinstance(effects, dict):
        effects = {}
    benefit = False
    cost = False
    for key, value in effects.items():
        number = _finite_number(value)
        if number is None or number == 0:
            continue
        if key in _GOOD_EFFECT_KEYS:
            benefit |= number > 0
            cost |= number < 0
        elif key in _BAD_EFFECT_KEYS:
            benefit |= number < 0
            cost |= number > 0
    success_rate = _finite_number(choice.get("success_rate"))
    failure_effects = choice.get("failure_effects")
    if (
        success_rate is not None
        and success_rate < 1
        and isinstance(failure_effects, dict)
    ):
        for key, value in failure_effects.items():
            number = _finite_number(value)
            if number is None:
                continue
            if (
                key in _GOOD_EFFECT_KEYS
                and number < 0
                or key in _BAD_EFFECT_KEYS
                and number > 0
            ):
                cost = True
    return benefit and cost


def _read_event_rate_rows(
    report_dir: Path,
    defaults: dict[str, str],
    difficulty_candidates: set[str],
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = _read_csv(
        report_dir / "event_trigger_rates.csv",
        {"policy", "event_id", "count", "rate_per_run"},
        failures,
        required=True,
        gate="input.event_trigger_rates",
    )
    parsed = []
    seen: set[tuple[Cell, str]] = set()
    for line, row in rows or []:
        event_id = str(row.get("event_id") or "").strip()
        count = _row_number(
            row, "count", line, "event_trigger_rates.csv", failures
        )
        rate = _row_number(
            row, "rate_per_run", line, "event_trigger_rates.csv", failures
        )
        cell = _row_cell(
            row,
            defaults,
            difficulty_candidates,
            failures,
            "event_trigger_rates.csv",
            line,
        )
        if not event_id or count is None or rate is None or cell is None:
            _input_failure(
                failures,
                "event_trigger_rates.csv",
                "invalid",
                f"line {line} is incomplete",
                "input.event_trigger_rates",
            )
            continue
        if count < 0 or not count.is_integer() or rate < 0:
            _input_failure(
                failures,
                "event_trigger_rates.csv",
                "invalid",
                (
                    f"line {line} has a negative or "
                    "non-integral count/rate"
                ),
                "input.event_trigger_rates",
            )
            continue
        identity = (cell, event_id)
        if identity in seen:
            _input_failure(
                failures,
                "event_trigger_rates.csv",
                "invalid",
                (
                    f"line {line} duplicates event {event_id!r} "
                    f"in {_cell_label(cell)}"
                ),
                "input.event_trigger_rates",
            )
            continue
        seen.add(identity)
        parsed.append(
            {
                "cell": cell,
                "event_id": event_id,
                "count": int(count),
                "rate": rate,
            }
        )
    return parsed


def _playthrough_anomaly_rates(
    report_dir: Path,
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    paths = sorted(report_dir.rglob("playthrough.jsonl"))
    results = []
    for path in paths:
        rows = _read_jsonl(
            path,
            failures,
            required=True,
            allow_empty=False,
            gate="input.playthrough",
        )
        if rows is None:
            continue
        weeks = 0
        anomalies: set[tuple[str, int, str, str]] = set()
        for _, row in rows:
            week = _finite_number(row.get("week"))
            if week is not None:
                weeks = max(weeks, int(week))
            payload = row.get("anomalies", [])
            if not isinstance(payload, list):
                _input_failure(
                    failures,
                    str(path.relative_to(report_dir)),
                    "invalid",
                    "anomalies must be a list",
                    "input.playthrough",
                )
                continue
            for anomaly in payload:
                if not isinstance(anomaly, dict):
                    continue
                severity = str(
                    anomaly.get("severity") or "warning"
                ).lower()
                if severity in {"debug", "info"}:
                    continue
                anomaly_week = _finite_number(anomaly.get("week"))
                anomalies.add(
                    (
                        str(anomaly.get("kind") or "unknown"),
                        (
                            int(anomaly_week)
                            if anomaly_week is not None
                            else -1
                        ),
                        severity,
                        str(anomaly.get("message") or ""),
                    )
                )
        if weeks <= 0:
            _input_failure(
                failures,
                str(path.relative_to(report_dir)),
                "incomplete",
                "no positive week values",
                "input.playthrough",
            )
            continue
        results.append(
            {
                "source": str(path.relative_to(report_dir)),
                "weeks": weeks,
                "anomaly_count": len(anomalies),
                "rate": round(len(anomalies) * 5 / weeks, 6),
            }
        )
    return results


def _read_csv(
    path: Path,
    required_columns: set[str],
    failures: list[dict[str, Any]],
    *,
    required: bool,
    gate: str,
) -> list[tuple[int, dict[str, str | None]]] | None:
    if not path.exists():
        if required:
            _input_failure(
                failures,
                path.name,
                "missing",
                "required file not found",
                gate,
            )
        return None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            fields = reader.fieldnames
            if not fields:
                _input_failure(
                    failures,
                    path.name,
                    "invalid",
                    "CSV header is missing",
                    gate,
                )
                return None
            if len(fields) != len(set(fields)):
                _input_failure(
                    failures,
                    path.name,
                    "invalid",
                    "CSV header has duplicates",
                    gate,
                )
                return None
            missing = sorted(required_columns - set(fields))
            if missing:
                _input_failure(
                    failures,
                    path.name,
                    "invalid",
                    (
                        "missing required columns: "
                        f"{', '.join(missing)}"
                    ),
                    gate,
                )
                return None
            rows = []
            for line, row in enumerate(reader, start=2):
                if None in row or any(
                    value is None for value in row.values()
                ):
                    _input_failure(
                        failures,
                        path.name,
                        "invalid",
                        f"line {line} has the wrong number of columns",
                        gate,
                    )
                    continue
                rows.append((line, row))
    except (OSError, UnicodeError, csv.Error) as exc:
        _input_failure(failures, path.name, "invalid", str(exc), gate)
        return None
    if not rows:
        _input_failure(
            failures,
            path.name,
            "empty",
            "no data rows",
            gate,
        )
        return None
    return rows


def _read_json(
    path: Path,
    failures: list[dict[str, Any]],
    *,
    required: bool,
    gate: str,
) -> dict[str, Any] | None:
    if not path.exists():
        if required:
            _input_failure(
                failures,
                path.name,
                "missing",
                "required file not found",
                gate,
            )
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _input_failure(failures, path.name, "invalid", str(exc), gate)
        return None
    if not isinstance(payload, dict):
        _input_failure(
            failures,
            path.name,
            "invalid",
            "top-level JSON must be an object",
            gate,
        )
        return None
    return payload


def _read_jsonl(
    path: Path,
    failures: list[dict[str, Any]],
    *,
    required: bool,
    allow_empty: bool,
    gate: str,
) -> list[tuple[int, dict[str, Any]]] | None:
    if not path.exists():
        if required:
            _input_failure(
                failures,
                path.name,
                "missing",
                "required file not found",
                gate,
            )
        return None
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        _input_failure(failures, path.name, "invalid", str(exc), gate)
        return None
    for line, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            _input_failure(
                failures,
                path.name,
                "invalid",
                f"line {line}: {exc}",
                gate,
            )
            continue
        if not isinstance(payload, dict):
            _input_failure(
                failures,
                path.name,
                "invalid",
                f"line {line} must contain a JSON object",
                gate,
            )
            continue
        rows.append((line, payload))
    if not rows and not allow_empty:
        _input_failure(
            failures,
            path.name,
            "empty",
            "no JSON objects",
            gate,
        )
        return None
    return rows


def _manifest_defaults(manifest: dict[str, Any]) -> dict[str, str]:
    defaults: dict[str, str] = {}
    parameters = manifest.get("parameters")
    if isinstance(parameters, dict):
        for key in ("policy", "difficulty", "scenario"):
            value = parameters.get(key)
            if value not in (None, ""):
                defaults[key] = str(value)
    operations = manifest.get("operations")
    if isinstance(operations, list):
        for key in ("policy", "difficulty", "scenario"):
            if key in defaults:
                continue
            values = {
                str(operation.get("parameters", {}).get(key))
                for operation in operations
                if isinstance(operation, dict)
                and isinstance(operation.get("parameters"), dict)
                and operation["parameters"].get(key) not in (None, "")
            }
            if len(values) == 1:
                defaults[key] = values.pop()
    return defaults


def _row_cell(
    row: Mapping[str, Any],
    defaults: dict[str, str],
    difficulty_candidates: set[str],
    failures: list[dict[str, Any]],
    filename: str,
    line: int,
) -> Cell | None:
    policy = str(
        row.get("policy") or defaults.get("policy") or ""
    ).strip()
    difficulty = str(
        row.get("difficulty") or defaults.get("difficulty") or ""
    ).strip()
    scenario = str(
        row.get("scenario")
        or row.get("scenario_id")
        or defaults.get("scenario")
        or "default"
    ).strip()
    if not policy:
        _input_failure(
            failures,
            filename,
            "incomplete",
            (
                f"line {line} has no policy and manifest supplies "
                "no policy"
            ),
            "input.cell_dimension",
        )
    if not difficulty:
        if len(difficulty_candidates) == 1:
            difficulty = next(iter(difficulty_candidates))
        elif difficulty_candidates:
            _input_failure(
                failures,
                filename,
                "incomplete",
                (
                    f"line {line} needs difficulty because normal "
                    "and realistic thresholds differ"
                ),
                "input.cell_dimension",
            )
        else:
            difficulty = "unspecified"
    if (
        difficulty_candidates
        and difficulty not in difficulty_candidates
    ):
        _input_failure(
            failures,
            filename,
            "invalid",
            (
                f"line {line} difficulty {difficulty!r} has no "
                "configured difficulty threshold"
            ),
            "input.cell_dimension",
        )
    return (
        (policy, difficulty, scenario or "default")
        if policy and difficulty
        else None
    )


def _payload_cell(
    payload: Mapping[str, Any],
    defaults: dict[str, str],
    *,
    require_difficulty: bool,
) -> Cell:
    state = payload.get("final_state")
    state = state if isinstance(state, dict) else {}
    context = payload.get("week_context")
    context = context if isinstance(context, dict) else {}
    policy = str(
        payload.get("policy")
        or state.get("policy")
        or context.get("persona")
        or defaults.get("policy")
        or "unknown"
    )
    difficulty = str(
        payload.get("difficulty")
        or state.get("difficulty")
        or context.get("difficulty")
        or defaults.get("difficulty")
        or ("unknown" if require_difficulty else "unspecified")
    )
    scenario = str(
        payload.get("scenario")
        or payload.get("scenario_id")
        or context.get("scenario")
        or defaults.get("scenario")
        or "default"
    )
    return policy, difficulty, scenario


def _difficulty_candidates(
    balance: dict[str, Any],
    outcomes: dict[str, Any],
) -> set[str]:
    result = set()
    for key in (*balance, *outcomes):
        if key.endswith("_normal"):
            result.add("normal")
        elif key.endswith("_realistic"):
            result.add("realistic")
    return result


def _difficulty_threshold(
    section: dict[str, Any],
    base: str,
    cell: Cell,
    failures: list[dict[str, Any]],
) -> float | None:
    key = f"{base}_{cell[1]}"
    if key in section:
        return _configured_number(section, key)
    available = [
        name
        for name in (f"{base}_normal", f"{base}_realistic")
        if name in section
    ]
    if available:
        _input_failure(
            failures,
            "report cell",
            "unsupported",
            (
                f"{_cell_label(cell)} has no matching threshold "
                f"for {base}"
            ),
            "input.cell_dimension",
        )
    return None


def _configured_number(
    section: dict[str, Any],
    key: str,
) -> float | None:
    if key not in section:
        return None
    return _finite_number(section[key])


def _row_number(
    row: Mapping[str, Any],
    key: str,
    line: int,
    filename: str,
    failures: list[dict[str, Any]],
) -> float | None:
    number = _finite_number(row.get(key))
    if number is None:
        _input_failure(
            failures,
            filename,
            "invalid",
            f"line {line} field {key!r} is not a finite number",
            f"input.{Path(filename).stem}",
        )
    return number


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _first_metric(
    payloads: Iterable[dict[str, Any]],
    names: tuple[str, ...],
) -> float | None:
    for payload in payloads:
        value = _metric_from_mapping(payload, names)
        if value is not None:
            return value
        for container in (
            "metrics",
            "summary",
            "design_metrics",
            "quality_metrics",
        ):
            nested = payload.get(container)
            if isinstance(nested, dict):
                value = _metric_from_mapping(nested, names)
                if value is not None:
                    return value
    return None


def _metric_from_mapping(
    mapping: Mapping[str, Any],
    names: tuple[str, ...],
) -> float | None:
    for name in names:
        value = _finite_number(mapping.get(name))
        if value is not None:
            return value
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value
        if isinstance(item, str) and item
    ]


def _cell_payload(cell: Cell) -> dict[str, str]:
    return {
        "policy": cell[0],
        "difficulty": cell[1],
        "scenario": cell[2],
    }


def _cell_key(cell: Cell) -> str:
    return "/".join(cell)


def _cell_label(cell: Cell) -> str:
    return (
        f"policy={cell[0]}, difficulty={cell[1]}, "
        f"scenario={cell[2]}"
    )


def _is_interactive_cell(cell: Cell) -> bool:
    policy = cell[0].lower()
    return (
        policy in {"interactive_personas", "interactive_player"}
        or policy.startswith("persona:")
    )


__all__ = ["evaluate_report_dir", "write_gate_report"]
