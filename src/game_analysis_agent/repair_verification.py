"""Deterministic real-game fixed/holdout cohorts and repair decision gates."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .agents.interactive_player import InteractivePlayerAgent
from .campaign_contract import CampaignPersona
from .design_contract import DesignIntentContract
from .game_tools import build_probe
from .persona_fixture_authoring import FixtureAuthoringGateway
from .repair_experiment import (
    CodexProvenance,
    FocusedTestResult,
    GateStatus,
    PatchEvidence,
    RepairCohort,
    RepairComparison,
    RepairDecision,
    RepairExperimentPlan,
    RepairExperimentRecord,
    RepairGateResult,
    RepairMetricSnapshot,
)
from .settings import Settings

COHORT_EVIDENCE_SCHEMA = "repair-cohort-evidence-v1"
CRITICAL_KINDS = {
    "ending_id_empty",
    "pipeline_stalled",
    "stat_overflow",
    "stat_underflow",
    "crisis_success_ending",
    "social_success_under_survival_crisis",
    "academic_success_with_failed_courses",
    "visa_success_without_registration",
    "testdaf_pass_with_low_language",
    "aps_pass_with_low_aps_knowledge",
}
INVALID_ENDINGS = {"unknown", "pipeline_stalled", ""}


class RepairVerificationError(RuntimeError):
    """Raised when a cohort is partial, malformed, or cannot be persisted."""


class CohortCellEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    persona: str
    seed: int
    weeks: int = Field(ge=1)
    target_first_week: int | None = Field(default=None, ge=1)
    final_money: float | None
    max_stress: float | None
    valid_rate: float = Field(ge=0, le=1)
    fallback_rate: float = Field(ge=0, le=1)
    provider_error_rate: float = Field(ge=0, le=1)
    persona_alignment_rate: float | None = Field(default=None, ge=0, le=1)
    ending: str
    critical_invariants: dict[str, int]


class CohortEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[COHORT_EVIDENCE_SCHEMA] = COHORT_EVIDENCE_SCHEMA
    cohort: RepairCohort
    game_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    decision_policy: Literal["fixture-authoring-policy-v1"] = (
        "fixture-authoring-policy-v1"
    )
    cells: tuple[CohortCellEvidence, ...] = Field(min_length=1)


def run_repair_cohort(
    *,
    project_root: str | Path,
    game_root: str | Path,
    game_commit: str,
    cohort: RepairCohort,
    seeds: tuple[int, ...],
    output_dir: str | Path,
    design: DesignIntentContract,
    settings: Settings,
    concurrency: int = 4,
    max_weeks: int = 20,
    progress: Callable[[str], None] | None = None,
) -> RepairMetricSnapshot:
    """Run a complete six-persona cohort through one transparent policy."""

    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    destination = Path(output_dir)
    if not destination.is_absolute():
        destination = project / destination
    destination.mkdir(parents=True, exist_ok=True)
    cohort_settings = replace(settings, game_project_path=game)
    cells = [(persona, seed) for persona in CampaignPersona for seed in seeds]
    results: dict[tuple[str, int], CohortCellEvidence] = {}

    def execute(persona: CampaignPersona, seed: int) -> CohortCellEvidence:
        cell_id = f"{persona.value}-seed-{seed}"
        cell_dir = destination / "private" / cell_id
        gateway = FixtureAuthoringGateway()
        agent = InteractivePlayerAgent(
            llm=None,
            persona_gateway=gateway,
            prompts_root=project / "prompts",
            settings=cohort_settings,
            max_weeks=max_weeks,
            persona=persona.value,
            difficulty="normal",
            scenario="default_first_semester",
            seed=seed,
        )
        result, _paths = agent.play_through(
            cell_dir,
            probe=build_probe(cohort_settings),
            context={"run_id": cell_id},
        )
        rows = _read_rows(cell_dir / "playthrough.jsonl")
        if len(rows) != len(result.steps) or not rows:
            raise RepairVerificationError(f"incomplete repair cell: {cell_id}")
        evidence = _cell_evidence(
            persona=persona.value,
            seed=seed,
            rows=rows,
            ending=result.final_ending,
        )
        if progress is not None:
            progress(f"{cohort.value}:{cell_id}:{evidence.weeks}")
        return evidence

    with ThreadPoolExecutor(max_workers=min(4, max(1, concurrency))) as pool:
        futures = {
            pool.submit(execute, persona, seed): (persona.value, seed)
            for persona, seed in cells
        }
        for future in as_completed(futures):
            identity = futures[future]
            results[identity] = future.result()
    ordered = tuple(results[(persona.value, seed)] for persona, seed in cells)
    evidence = CohortEvidence(cohort=cohort, game_commit=game_commit, cells=ordered)
    public_path = destination / "cohort.json"
    public_path.write_text(evidence.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return _snapshot_from_evidence(
        project=project,
        path=public_path,
        evidence=evidence,
        design=design,
        seeds=seeds,
    )


def compare_and_gate_repair(
    *,
    plan: RepairExperimentPlan,
    snapshots: tuple[RepairMetricSnapshot, ...],
    design: DesignIntentContract,
) -> tuple[RepairComparison, tuple[RepairGateResult, ...]]:
    by_cohort = {item.cohort: item for item in snapshots}
    if set(by_cohort) != set(RepairCohort):
        raise RepairVerificationError("comparison requires all four repair cohorts")
    baseline_fixed = by_cohort[RepairCohort.BASELINE_FIXED]
    patched_fixed = by_cohort[RepairCohort.PATCHED_FIXED]
    baseline_holdout = by_cohort[RepairCohort.BASELINE_HOLDOUT]
    patched_holdout = by_cohort[RepairCohort.PATCHED_HOLDOUT]
    comparison = RepairComparison(
        fixed_member_delta=patched_fixed.target_members - baseline_fixed.target_members,
        fixed_relative_reduction=_reduction(
            baseline_fixed.target_members, patched_fixed.target_members
        ),
        holdout_member_delta=(
            patched_holdout.target_members - baseline_holdout.target_members
        ),
        holdout_relative_reduction=_reduction(
            baseline_holdout.target_members, patched_holdout.target_members
        ),
        fixed_persona_alignment_delta=_delta(
            baseline_fixed.persona_alignment_rate,
            patched_fixed.persona_alignment_rate,
        ),
        holdout_persona_alignment_delta=_delta(
            baseline_holdout.persona_alignment_rate,
            patched_holdout.persona_alignment_rate,
        ),
    )
    thresholds = plan.thresholds
    gates = (
        _gate(
            "fixed_target",
            patched_fixed.target_members <= thresholds.acceptance_max_fixed_members,
            f"{patched_fixed.target_members} <= {thresholds.acceptance_max_fixed_members}",
        ),
        _gate(
            "holdout_target",
            comparison.holdout_relative_reduction
            >= thresholds.minimum_holdout_relative_reduction,
            (
                f"{comparison.holdout_relative_reduction:.6f} >= "
                f"{thresholds.minimum_holdout_relative_reduction:.6f}"
            ),
        ),
        _gate(
            "critical_invariants",
            all(
                value == 0
                for snapshot in (patched_fixed, patched_holdout)
                for value in snapshot.critical_invariants.values()
            ),
            "patched fixed and holdout critical counters are zero",
        ),
        _gate(
            "decision_validity",
            min(patched_fixed.valid_rate, patched_holdout.valid_rate)
            >= thresholds.minimum_valid_rate,
            "patched fixed and holdout validity meet threshold",
        ),
        _gate(
            "provider_health",
            max(patched_fixed.fallback_rate, patched_holdout.fallback_rate)
            <= thresholds.maximum_fallback_rate
            and max(
                patched_fixed.provider_error_rate,
                patched_holdout.provider_error_rate,
            )
            <= thresholds.maximum_provider_error_rate,
            "deterministic policy produced no hidden failure",
        ),
        _gate(
            "persona_preservation",
            _alignment_preserved(comparison, thresholds.maximum_persona_alignment_decline),
            "fixed and holdout persona alignment decline is bounded",
        ),
        _gate(
            "no_new_invalid_endings",
            _invalid_count(patched_fixed) <= _invalid_count(baseline_fixed)
            and _invalid_count(patched_holdout) <= _invalid_count(baseline_holdout),
            "patched cohorts do not add unknown or pipeline-stalled endings",
        ),
        _gate(
            "designed_failure_preserved",
            _designed_failure_preserved(
                baseline_fixed,
                patched_fixed,
                baseline_holdout,
                patched_holdout,
                design,
            ),
            "designed failure remains possible and is not reclassified",
        ),
    )
    return comparison, gates


def build_repair_record(
    *,
    plan: RepairExperimentPlan,
    patch: PatchEvidence,
    focused_tests: tuple[FocusedTestResult, ...],
    snapshots: tuple[RepairMetricSnapshot, ...],
    design: DesignIntentContract,
    codex: CodexProvenance,
    completed_at: datetime,
) -> RepairExperimentRecord:
    comparison, gates = compare_and_gate_repair(
        plan=plan, snapshots=snapshots, design=design
    )
    accepted = all(item.status == GateStatus.PASSED for item in gates) and all(
        item.exit_code == 0 for item in focused_tests
    )
    decision = RepairDecision.ACCEPTED if accepted else RepairDecision.REJECTED
    failures = [item.gate_id for item in gates if item.status == GateStatus.FAILED]
    if any(item.exit_code != 0 for item in focused_tests):
        failures.insert(0, "focused_tests")
    reason = (
        "All focused tests and frozen fixed/holdout repair gates passed."
        if accepted
        else "Repair rejected because required proof failed: " + ", ".join(failures)
    )
    return RepairExperimentRecord(
        plan=plan,
        plan_fingerprint=plan.fingerprint(),
        patch=patch,
        focused_tests=focused_tests,
        snapshots=snapshots,
        comparison=comparison,
        gates=gates,
        decision=decision,
        decision_reason=reason,
        codex=codex,
        completed_at=completed_at,
    )


def _cell_evidence(
    *, persona: str, seed: int, rows: list[dict[str, Any]], ending: str
) -> CohortCellEvidence:
    money = []
    stress = []
    signals = []
    valid = fallback = errors = alignment_hits = alignment_total = 0
    critical = Counter({kind: 0 for kind in CRITICAL_KINDS})
    for row in rows:
        state = _state(row)
        if isinstance(state.get("money"), (int, float)):
            money.append(float(state["money"]))
        if isinstance(state.get("stress"), (int, float)):
            stress.append(float(state["stress"]))
        signals.append(
            bool(money and money[-1] <= 0 and stress and stress[-1] >= 80)
        )
        validation = row.get("validation") or {}
        fallback_used = validation.get("fallback_used") is True
        valid += int(validation.get("valid") is True and not fallback_used)
        fallback += int(fallback_used)
        errors += int(
            any(call.get("status") != "completed" for call in row.get("persona_calls", []))
        )
        aligned = _alignment(row)
        if aligned is not None:
            alignment_total += 1
            alignment_hits += int(aligned)
        for anomaly in row.get("anomalies", []):
            kind = str(anomaly.get("kind", ""))
            if kind in CRITICAL_KINDS:
                critical[kind] += 1
    normalized_ending = ending or "unknown"
    if normalized_ending == "pipeline_stalled":
        critical["pipeline_stalled"] += 1
    return CohortCellEvidence(
        persona=persona,
        seed=seed,
        weeks=len(rows),
        target_first_week=_first_consecutive(signals, 2),
        final_money=money[-1] if money else None,
        max_stress=max(stress) if stress else None,
        valid_rate=_ratio(valid, len(rows)),
        fallback_rate=_ratio(fallback, len(rows)),
        provider_error_rate=_ratio(errors, len(rows)),
        persona_alignment_rate=(
            _ratio(alignment_hits, alignment_total) if alignment_total else None
        ),
        ending=normalized_ending,
        critical_invariants=dict(sorted(critical.items())),
    )


def _snapshot_from_evidence(
    *,
    project: Path,
    path: Path,
    evidence: CohortEvidence,
    design: DesignIntentContract,
    seeds: tuple[int, ...],
) -> RepairMetricSnapshot:
    cells = evidence.cells
    alignment_weight = sum(
        (item.persona_alignment_rate or 0) * item.weeks
        for item in cells
        if item.persona_alignment_rate is not None
    )
    alignment_weeks = sum(
        item.weeks for item in cells if item.persona_alignment_rate is not None
    )
    endings = Counter(item.ending for item in cells)
    critical = Counter({kind: 0 for kind in design.critical_invariants})
    for item in cells:
        critical.update(item.critical_invariants)
    target_cells = [item for item in cells if item.target_first_week is not None]
    relative = path.resolve().relative_to(project).as_posix()
    return RepairMetricSnapshot(
        cohort=evidence.cohort,
        game_commit=evidence.game_commit,
        seeds=seeds,
        cells=len(cells),
        weeks=sum(item.weeks for item in cells),
        target_members=len(target_cells),
        target_personas=len({item.persona for item in target_cells}),
        mean_final_money=_mean(
            [item.final_money for item in cells if item.final_money is not None]
        ),
        mean_max_stress=_mean(
            [item.max_stress for item in cells if item.max_stress is not None]
        ),
        valid_rate=_weighted(cells, "valid_rate"),
        fallback_rate=_weighted(cells, "fallback_rate"),
        provider_error_rate=_weighted(cells, "provider_error_rate"),
        persona_alignment_rate=(
            round(alignment_weight / alignment_weeks, 6) if alignment_weeks else None
        ),
        critical_invariants=dict(sorted(critical.items())),
        designed_failure_endings=tuple(
            sorted(set(endings) & set(design.designed_failure_endings))
        ),
        ending_counts=dict(sorted(endings.items())),
        artifact_path=relative,
        artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _alignment(row: dict[str, Any]) -> bool | None:
    context = row.get("week_context") or {}
    strategy = context.get("persona_strategy")
    actions = context.get("available_actions")
    chosen = {str(item) for item in row.get("chosen_actions", []) if str(item)}
    if not isinstance(strategy, dict) or not isinstance(actions, list) or not chosen:
        return None
    tags = {str(item) for item in strategy.get("alignment_action_tags", []) if str(item)}
    ids = {str(item) for item in strategy.get("alignment_action_ids", []) if str(item)}
    if not tags and not ids:
        tags = {str(item) for item in strategy.get("priorities", []) if str(item)}
    action_tags = set()
    for action in actions:
        if isinstance(action, dict) and str(action.get("id")) in chosen:
            action_tags.update(str(item) for item in action.get("tags", []) if str(item))
            action_tags.update(
                str(item) for item in action.get("risk_tags", []) if str(item)
            )
    return bool(ids & chosen or tags & action_tags or tags & chosen)


def _state(row: dict[str, Any]) -> dict[str, Any]:
    state = row.get("state_after")
    if isinstance(state, dict) and isinstance(state.get("state"), dict):
        return state["state"]
    return state if isinstance(state, dict) else {}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _first_consecutive(values: list[bool], length: int) -> int | None:
    streak = 0
    for index, value in enumerate(values, start=1):
        streak = streak + 1 if value else 0
        if streak >= length:
            return index - length + 1
    return None


def _weighted(cells: tuple[CohortCellEvidence, ...], field: str) -> float:
    total = sum(item.weeks for item in cells)
    return round(
        sum(float(getattr(item, field)) * item.weeks for item in cells) / total, 6
    )


def _mean(values: list[float]) -> float | None:
    return round(fmean(values), 6) if values else None


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _reduction(baseline: int, patched: int) -> float:
    if baseline == 0:
        return 0.0 if patched == 0 else -1.0
    return round((baseline - patched) / baseline, 6)


def _delta(baseline: float | None, patched: float | None) -> float | None:
    if baseline is None or patched is None:
        return None
    return round(patched - baseline, 6)


def _alignment_preserved(comparison: RepairComparison, maximum_decline: float) -> bool:
    values = (
        comparison.fixed_persona_alignment_delta,
        comparison.holdout_persona_alignment_delta,
    )
    return all(value is not None and value >= -maximum_decline for value in values)


def _invalid_count(snapshot: RepairMetricSnapshot) -> int:
    return sum(snapshot.ending_counts.get(item, 0) for item in INVALID_ENDINGS)


def _designed_failure_preserved(
    baseline_fixed: RepairMetricSnapshot,
    patched_fixed: RepairMetricSnapshot,
    baseline_holdout: RepairMetricSnapshot,
    patched_holdout: RepairMetricSnapshot,
    design: DesignIntentContract,
) -> bool:
    if not design.protected_metrics.require_designed_failure_coverage:
        return True
    baseline = set(baseline_fixed.designed_failure_endings) | set(
        baseline_holdout.designed_failure_endings
    )
    patched = set(patched_fixed.designed_failure_endings) | set(
        patched_holdout.designed_failure_endings
    )
    return bool(baseline and patched)


def _gate(gate_id: str, passed: bool, detail: str) -> RepairGateResult:
    return RepairGateResult(
        gate_id=gate_id,
        status=GateStatus.PASSED if passed else GateStatus.FAILED,
        detail=detail,
    )


__all__ = [
    "COHORT_EVIDENCE_SCHEMA",
    "CohortCellEvidence",
    "CohortEvidence",
    "RepairVerificationError",
    "build_repair_record",
    "compare_and_gate_repair",
    "run_repair_cohort",
]
