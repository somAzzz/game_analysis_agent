"""Deterministic quality metrics for recorded interactive Agent playthroughs."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import fmean
from typing import Any


class AgentEvalError(ValueError):
    """Raised when a playthrough artifact cannot be evaluated safely."""


MIN_FINAL_VALID_RATE = 0.95
MAX_FALLBACK_RATE = 0.05
MAX_LLM_ERROR_RATE = 0.05


def evaluate_playthrough(report_dir: Path) -> dict[str, Any]:
    """Evaluate recorded decisions without calling an LLM or Godot.

    The evaluator is suitable for cassettes, local live runs, and CI artifacts.
    It validates what was actually submitted to the game rather than trusting
    the model's prose or the playthrough summary.
    """

    rows, errors = _read_jsonl(report_dir / "playthrough.jsonl")
    total = len(rows)
    first_pass_valid = 0
    final_valid = 0
    fallbacks = 0
    repaired = 0
    illegal_actions = 0
    invalid_event_choices = 0
    unique_anomalies: set[tuple[str, int, str, str]] = set()
    risk_opportunities = 0
    risk_acknowledged = 0
    persona_opportunities = 0
    persona_aligned = 0

    for index, row in enumerate(rows, start=1):
        validation = row.get("validation") if isinstance(row.get("validation"), dict) else {}
        repair_count = _non_negative_int(validation.get("repair_count"))
        fallback_used = validation.get("fallback_used") is True
        chosen = _string_list(row.get("chosen_actions"))
        available = set(_string_list(row.get("available_actions")))
        illegal = [action for action in chosen if action not in available]
        illegal_actions += len(illegal)

        week_context = (
            row.get("week_context") if isinstance(row.get("week_context"), dict) else {}
        )
        valid_choices = {
            str(choice.get("choice_id") or choice.get("id"))
            for choice in week_context.get("event_choices", [])
            if isinstance(choice, dict) and (choice.get("choice_id") or choice.get("id"))
        }
        selected_choice = str(row.get("event_choice_id") or "")
        choice_invalid = bool(valid_choices and selected_choice not in valid_choices)
        invalid_event_choices += int(choice_invalid)

        record_valid = (
            validation.get("valid") is True
            and not fallback_used
            and not illegal
            and not choice_invalid
        )
        final_valid += int(record_valid)
        first_pass_valid += int(record_valid and repair_count == 0)
        fallbacks += int(fallback_used)
        repaired += int(repair_count > 0)

        anomalies = row.get("anomalies") if isinstance(row.get("anomalies"), list) else []
        for anomaly in anomalies:
            if not isinstance(anomaly, dict):
                continue
            severity = str(anomaly.get("severity") or "warning").lower()
            if severity in {"debug", "info"}:
                continue
            anomaly_week = _optional_int(anomaly.get("week"))
            unique_anomalies.add(
                (
                    str(anomaly.get("kind") or "unknown"),
                    anomaly_week if anomaly_week is not None else -1,
                    severity,
                    str(anomaly.get("message") or ""),
                )
            )

        decision = row.get("decision") if isinstance(row.get("decision"), dict) else {}
        risks = week_context.get("top_risks")
        if isinstance(risks, list) and risks:
            risk_opportunities += 1
            awareness = _string_list(decision.get("risk_awareness"))
            risk_acknowledged += int(bool(awareness))

        strategy = week_context.get("persona_strategy")
        actions = week_context.get("available_actions")
        if isinstance(strategy, dict) and isinstance(actions, list):
            priorities = {str(item) for item in strategy.get("priorities", []) if str(item)}
            action_by_id = {
                str(action.get("id")): action
                for action in actions
                if isinstance(action, dict) and action.get("id")
            }
            if priorities and chosen:
                persona_opportunities += 1
                chosen_tags: set[str] = set()
                for action_id in chosen:
                    action = action_by_id.get(action_id, {})
                    chosen_tags.update(_string_list(action.get("tags")))
                    chosen_tags.update(_string_list(action.get("risk_tags")))
                persona_aligned += int(bool(priorities & (chosen_tags | set(chosen))))

        if not chosen:
            errors.append(f"line {index}: chosen_actions is empty")
        if not available:
            errors.append(f"line {index}: available_actions is empty")

    audit = _read_json(report_dir / "playthrough_agent_report.json", errors)
    calls = audit.get("llm_calls", []) if isinstance(audit, dict) else []
    if not isinstance(calls, list):
        errors.append("playthrough_agent_report.json: llm_calls must be a list")
        calls = []
    valid_calls = [call for call in calls if isinstance(call, dict)]
    llm_errors = sum(1 for call in valid_calls if call.get("error"))
    latencies = [
        float(call.get("latency_ms"))
        for call in valid_calls
        if isinstance(call.get("latency_ms"), (int, float))
    ]

    final_ending = _read_final_ending(report_dir / "playthrough_summary.md")
    if not final_ending:
        errors.append("playthrough_summary.md: final ending is missing")
    anomaly_count = len(unique_anomalies)
    metrics = {
        "steps": total,
        "first_pass_valid_rate": _ratio(first_pass_valid, total),
        "final_valid_rate": _ratio(final_valid, total),
        "fallback_rate": _ratio(fallbacks, total),
        "repaired_decision_rate": _ratio(repaired, total),
        "illegal_action_count": illegal_actions,
        "illegal_action_rate": _ratio(illegal_actions, max(1, sum(
            len(_string_list(row.get("chosen_actions"))) for row in rows
        ))),
        "invalid_event_choice_count": invalid_event_choices,
        "anomaly_count": anomaly_count,
        "anomaly_rate_per_5_weeks": round(anomaly_count * 5 / total, 6) if total else None,
        "risk_acknowledgement_rate": _ratio(risk_acknowledged, risk_opportunities),
        "persona_alignment_rate": _ratio(persona_aligned, persona_opportunities),
        "llm_call_count": len(valid_calls),
        "llm_error_rate": _ratio(llm_errors, len(valid_calls)),
        "mean_latency_ms": round(fmean(latencies), 3) if latencies else None,
    }
    if total == 0:
        errors.append("playthrough.jsonl contains no decision rows")
    quality_errors: list[str] = []
    final_valid_rate = metrics["final_valid_rate"]
    fallback_rate = metrics["fallback_rate"]
    llm_error_rate = metrics["llm_error_rate"]
    if isinstance(final_valid_rate, (int, float)) and final_valid_rate < MIN_FINAL_VALID_RATE:
        quality_errors.append(
            f"final_valid_rate {final_valid_rate} is below {MIN_FINAL_VALID_RATE}"
        )
    if isinstance(fallback_rate, (int, float)) and fallback_rate > MAX_FALLBACK_RATE:
        quality_errors.append(
            f"fallback_rate {fallback_rate} exceeds {MAX_FALLBACK_RATE}"
        )
    if illegal_actions:
        quality_errors.append(f"illegal_action_count is {illegal_actions}, expected 0")
    if invalid_event_choices:
        quality_errors.append(
            f"invalid_event_choice_count is {invalid_event_choices}, expected 0"
        )
    if total and not valid_calls:
        quality_errors.append("no LLM calls were recorded for a non-empty playthrough")
    elif isinstance(llm_error_rate, (int, float)) and llm_error_rate > MAX_LLM_ERROR_RATE:
        quality_errors.append(
            f"llm_error_rate {llm_error_rate} exceeds {MAX_LLM_ERROR_RATE}"
        )
    return {
        "schema_version": "agent-eval-v1",
        "valid": not errors,
        "errors": errors,
        "strict_passed": not errors and not quality_errors,
        "quality_errors": quality_errors,
        "final_ending": final_ending,
        "metrics": metrics,
    }


def evaluate_and_write(report_dir: Path, output: Path | None = None) -> dict[str, Any]:
    report = evaluate_playthrough(report_dir)
    target = output or report_dir / "agent_eval.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return [], [f"missing required artifact: {path.name}"]
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{line_no}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{path.name}:{line_no}: row must be an object")
            continue
        rows.append(payload)
    return rows, errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing required artifact: {path.name}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name}: invalid JSON: {exc.msg}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.name}: root must be an object")
        return {}
    return payload


def _read_final_ending(path: Path) -> str:
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


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


__all__ = ["AgentEvalError", "evaluate_and_write", "evaluate_playthrough"]
