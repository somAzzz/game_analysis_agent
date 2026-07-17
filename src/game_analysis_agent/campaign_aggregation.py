"""Deterministic campaign metrics and citation-backed failure clustering."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import fmean
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .campaign_contract import (
    CampaignCellResult,
    CampaignCellState,
    CampaignCitation,
    canonical_sha256,
)

RULES_SCHEMA = "campaign-failure-rules-v1"
AGGREGATION_SCHEMA = "campaign-aggregation-v1"


class CampaignAggregationError(ValueError):
    """Raised when raw rows cannot reproduce their declared evidence."""


class FailureRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cluster_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    label: str = Field(min_length=1, max_length=160)
    money_lte: float | None = None
    stress_gte: float | None = None
    fallback_used: bool | None = None
    consecutive_weeks: int = Field(default=1, ge=1, le=20)

    @model_validator(mode="after")
    def _has_signal(self) -> FailureRule:
        if self.money_lte is None and self.stress_gte is None and self.fallback_used is None:
            raise ValueError("failure rule requires at least one signal")
        return self


class FailureRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[RULES_SCHEMA] = RULES_SCHEMA
    rules: tuple[FailureRule, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> FailureRules:
        ids = [rule.cluster_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("failure rule ids must be unique")
        return self

    def fingerprint(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class CampaignCellMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cell_id: str
    persona: str
    seed: int
    state: CampaignCellState
    weeks: int = Field(ge=0)
    ending: str = "unknown"
    min_money: float | None = None
    final_money: float | None = None
    max_stress: float | None = None
    cashflow_crisis_weeks: int = Field(ge=0)
    burnout_risk_weeks: int = Field(ge=0)
    valid_rate: float | None = Field(default=None, ge=0, le=1)
    fallback_rate: float | None = Field(default=None, ge=0, le=1)
    provider_error_rate: float | None = Field(default=None, ge=0, le=1)
    persona_alignment_rate: float | None = Field(default=None, ge=0, le=1)
    first_failure_entries: dict[str, CampaignCitation] = Field(default_factory=dict)


class FailureCluster(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cluster_id: str
    label: str
    rule: FailureRule
    member_count: int = Field(ge=0)
    cell_rate: float = Field(ge=0, le=1)
    persona_counts: dict[str, int]
    members: tuple[CampaignCitation, ...]
    representatives: tuple[CampaignCitation, ...]


class CampaignAggregateMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_cells: int = Field(ge=1)
    completed_cells: int = Field(ge=0)
    partial_cells: int = Field(ge=0)
    failed_cells: int = Field(ge=0)
    cancelled_cells: int = Field(ge=0)
    total_weeks: int = Field(ge=0)
    mean_final_money: float | None = None
    mean_max_stress: float | None = None
    valid_rate: float | None = Field(default=None, ge=0, le=1)
    fallback_rate: float | None = Field(default=None, ge=0, le=1)
    provider_error_rate: float | None = Field(default=None, ge=0, le=1)
    persona_alignment_rate: float | None = Field(default=None, ge=0, le=1)


class CampaignAggregation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[AGGREGATION_SCHEMA] = AGGREGATION_SCHEMA
    campaign_id: str
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    rules_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    metrics: CampaignAggregateMetrics
    cells: tuple[CampaignCellMetrics, ...]
    clusters: tuple[FailureCluster, ...]


def load_failure_rules(path: str | Path) -> FailureRules:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignAggregationError("failure rules are unavailable") from exc
    return FailureRules.model_validate(payload)


def aggregate_campaign(
    *,
    project_root: str | Path,
    results: tuple[CampaignCellResult, ...] | list[CampaignCellResult],
    rules: FailureRules,
) -> CampaignAggregation:
    if not results:
        raise CampaignAggregationError("campaign has no cell results")
    project = Path(project_root).resolve()
    campaign_ids = {item.request.campaign_id for item in results}
    request_fingerprints = {item.request.campaign_fingerprint for item in results}
    source_fingerprints = {item.source_fingerprint for item in results}
    if len(campaign_ids) != 1 or len(request_fingerprints) != 1:
        raise CampaignAggregationError("cell results cross campaign identity")
    if len(source_fingerprints) != 1:
        raise CampaignAggregationError("cell results cross source identity")

    cell_metrics = []
    cluster_members: dict[str, list[CampaignCitation]] = {
        rule.cluster_id: [] for rule in rules.rules
    }
    total_valid = total_fallback = total_provider_errors = 0
    alignment_hits = alignment_opportunities = 0
    total_weeks = 0
    for result in results:
        rows = _verified_rows(project, result)
        metrics, counts = _cell_metrics(result, rows, rules)
        cell_metrics.append(metrics)
        total_weeks += metrics.weeks
        total_valid += counts["valid"]
        total_fallback += counts["fallback"]
        total_provider_errors += counts["provider_errors"]
        alignment_hits += counts["alignment_hits"]
        alignment_opportunities += counts["alignment_opportunities"]
        for cluster_id, citation in metrics.first_failure_entries.items():
            cluster_members[cluster_id].append(citation)

    clusters = []
    for rule in rules.rules:
        members = tuple(
            sorted(
                cluster_members[rule.cluster_id],
                key=lambda item: (item.persona.value, item.seed, item.week, item.cell_id),
            )
        )
        persona_counts = dict(sorted(Counter(item.persona.value for item in members).items()))
        clusters.append(
            FailureCluster(
                cluster_id=rule.cluster_id,
                label=rule.label,
                rule=rule,
                member_count=len(members),
                cell_rate=_ratio(len(members), len(results)) or 0.0,
                persona_counts=persona_counts,
                members=members,
                representatives=members[:3],
            )
        )

    completed = sum(item.state == CampaignCellState.COMPLETED for item in results)
    partial = sum(item.state == CampaignCellState.PARTIAL for item in results)
    failed = sum(item.state == CampaignCellState.FAILED for item in results)
    cancelled = sum(item.state == CampaignCellState.CANCELLED for item in results)
    final_money = [item.final_money for item in cell_metrics if item.final_money is not None]
    max_stress = [item.max_stress for item in cell_metrics if item.max_stress is not None]
    return CampaignAggregation(
        campaign_id=next(iter(campaign_ids)),
        request_fingerprint=next(iter(request_fingerprints)),
        source_fingerprint=next(iter(source_fingerprints)),
        rules_fingerprint=rules.fingerprint(),
        metrics=CampaignAggregateMetrics(
            expected_cells=len(results),
            completed_cells=completed,
            partial_cells=partial,
            failed_cells=failed,
            cancelled_cells=cancelled,
            total_weeks=total_weeks,
            mean_final_money=_mean(final_money),
            mean_max_stress=_mean(max_stress),
            valid_rate=_ratio(total_valid, total_weeks),
            fallback_rate=_ratio(total_fallback, total_weeks),
            provider_error_rate=_ratio(total_provider_errors, total_weeks),
            persona_alignment_rate=_ratio(alignment_hits, alignment_opportunities),
        ),
        cells=tuple(cell_metrics),
        clusters=tuple(clusters),
    )


def _verified_rows(project: Path, result: CampaignCellResult) -> list[dict[str, Any]]:
    if result.completed_weeks == 0:
        return []
    path = project / result.request.output_dir / "playthrough.jsonl"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CampaignAggregationError(f"missing playthrough for {result.request.cell_id}") from exc
    rows = []
    citations = {item.line_number: item for item in result.citations}
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CampaignAggregationError(
                f"invalid playthrough row {result.request.cell_id}:{line_number}"
            ) from exc
        if not isinstance(row, dict):
            raise CampaignAggregationError("playthrough row must be an object")
        citation = citations.get(line_number)
        if citation is None or citation.record_sha256 != canonical_sha256(row):
            raise CampaignAggregationError(
                f"citation hash mismatch {result.request.cell_id}:{line_number}"
            )
        rows.append(row)
    if len(rows) != result.completed_weeks:
        raise CampaignAggregationError(f"week count mismatch for {result.request.cell_id}")
    return rows


def _cell_metrics(
    result: CampaignCellResult,
    rows: list[dict[str, Any]],
    rules: FailureRules,
) -> tuple[CampaignCellMetrics, dict[str, int]]:
    money_values = []
    stress_values = []
    valid = fallback = provider_errors = 0
    alignment_hits = alignment_opportunities = 0
    cashflow_weeks = burnout_weeks = 0
    signals: dict[str, list[bool]] = {rule.cluster_id: [] for rule in rules.rules}
    citations_by_week = {item.week: item for item in result.citations}
    ending = "unknown"
    for index, row in enumerate(rows, start=1):
        state = _state_after(row)
        money = _number(state.get("money"))
        stress = _number(state.get("stress"))
        if money is not None:
            money_values.append(money)
        if stress is not None:
            stress_values.append(stress)
        flags = state.get("flags") if isinstance(state.get("flags"), dict) else {}
        cashflow = money is not None and money <= 0 or flags.get("cashflow_crisis") is True
        burnout = stress is not None and stress >= 90
        cashflow_weeks += int(cashflow)
        burnout_weeks += int(burnout)
        validation = row.get("validation") if isinstance(row.get("validation"), dict) else {}
        fallback_used = validation.get("fallback_used") is True
        valid += int(validation.get("valid") is True and not fallback_used)
        fallback += int(fallback_used)
        persona_calls = (
            row.get("persona_calls") if isinstance(row.get("persona_calls"), list) else []
        )
        provider_errors += int(
            any(
                isinstance(call, dict) and call.get("status") != "completed"
                for call in persona_calls
            )
        )
        aligned = _alignment(row)
        if aligned is not None:
            alignment_opportunities += 1
            alignment_hits += int(aligned)
        for rule in rules.rules:
            signals[rule.cluster_id].append(
                _matches_rule(rule, money=money, stress=stress, fallback=fallback_used)
            )
        candidate = _ending(row)
        if candidate:
            ending = candidate

    if result.state == CampaignCellState.COMPLETED and ending in {"", "unknown"}:
        raise CampaignAggregationError(
            f"completed cell has no structured ending: {result.request.cell_id}"
        )
    first_entries = {}
    for rule in rules.rules:
        week = _first_consecutive(signals[rule.cluster_id], rule.consecutive_weeks)
        if week is not None:
            first_entries[rule.cluster_id] = citations_by_week[week]
    return (
        CampaignCellMetrics(
            cell_id=result.request.cell_id,
            persona=result.request.persona.value,
            seed=result.request.seed,
            state=result.state,
            weeks=len(rows),
            ending=ending,
            min_money=min(money_values) if money_values else None,
            final_money=money_values[-1] if money_values else None,
            max_stress=max(stress_values) if stress_values else None,
            cashflow_crisis_weeks=cashflow_weeks,
            burnout_risk_weeks=burnout_weeks,
            valid_rate=_ratio(valid, len(rows)),
            fallback_rate=_ratio(fallback, len(rows)),
            provider_error_rate=_ratio(provider_errors, len(rows)),
            persona_alignment_rate=_ratio(alignment_hits, alignment_opportunities),
            first_failure_entries=first_entries,
        ),
        {
            "valid": valid,
            "fallback": fallback,
            "provider_errors": provider_errors,
            "alignment_hits": alignment_hits,
            "alignment_opportunities": alignment_opportunities,
        },
    )


def _state_after(row: dict[str, Any]) -> dict[str, Any]:
    state = row.get("state_after")
    if isinstance(state, dict) and isinstance(state.get("state"), dict):
        return state["state"]
    if isinstance(state, dict):
        return state
    result = row.get("result")
    return result.get("state", {}) if isinstance(result, dict) else {}


def _alignment(row: dict[str, Any]) -> bool | None:
    context = row.get("week_context") if isinstance(row.get("week_context"), dict) else {}
    strategy = context.get("persona_strategy")
    actions = context.get("available_actions")
    chosen = {str(item) for item in row.get("chosen_actions", []) if str(item)}
    if not isinstance(strategy, dict) or not isinstance(actions, list) or not chosen:
        return None
    tags = {str(item) for item in strategy.get("alignment_action_tags", []) if str(item)}
    ids = {str(item) for item in strategy.get("alignment_action_ids", []) if str(item)}
    priorities = {str(item) for item in strategy.get("priorities", []) if str(item)}
    if not tags and not ids:
        tags = priorities
    if not tags and not ids:
        return None
    action_tags = set()
    for action in actions:
        if isinstance(action, dict) and str(action.get("id")) in chosen:
            action_tags.update(str(item) for item in action.get("tags", []) if str(item))
            action_tags.update(str(item) for item in action.get("risk_tags", []) if str(item))
    return bool(ids & chosen or tags & action_tags or tags & chosen)


def _matches_rule(
    rule: FailureRule,
    *,
    money: float | None,
    stress: float | None,
    fallback: bool,
) -> bool:
    if rule.money_lte is not None and (money is None or money > rule.money_lte):
        return False
    if rule.stress_gte is not None and (stress is None or stress < rule.stress_gte):
        return False
    return rule.fallback_used is None or fallback is rule.fallback_used


def _first_consecutive(values: list[bool], length: int) -> int | None:
    streak = 0
    for index, matched in enumerate(values, start=1):
        streak = streak + 1 if matched else 0
        if streak >= length:
            return index - length + 1
    return None


def _ending(row: dict[str, Any]) -> str:
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    state = _state_after(row)
    return str(
        result.get("final_ending") or result.get("ending_id") or state.get("ending_id") or ""
    )


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _mean(values: list[float]) -> float | None:
    return round(fmean(values), 6) if values else None


__all__ = [
    "CampaignAggregation",
    "CampaignAggregationError",
    "CampaignCellMetrics",
    "FailureCluster",
    "FailureRule",
    "FailureRules",
    "aggregate_campaign",
    "load_failure_rules",
]
