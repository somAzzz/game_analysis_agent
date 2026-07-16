"""Typed plan, patch, proof, and decision contracts for one causal repair."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .campaign_contract import CampaignCitation

REPAIR_PLAN_SCHEMA = "repair-experiment-plan-v1"
REPAIR_RECORD_SCHEMA = "repair-experiment-record-v1"
REQUIRED_REPAIR_GATES = frozenset(
    {
        "fixed_target",
        "holdout_target",
        "critical_invariants",
        "decision_validity",
        "provider_health",
        "persona_preservation",
        "no_new_invalid_endings",
        "designed_failure_preserved",
    }
)


class RepairDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RepairCohort(StrEnum):
    BASELINE_FIXED = "baseline_fixed"
    PATCHED_FIXED = "patched_fixed"
    BASELINE_HOLDOUT = "baseline_holdout"
    PATCHED_HOLDOUT = "patched_holdout"


class GateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class RepairThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    acceptance_max_fixed_members: int = Field(ge=0)
    minimum_holdout_relative_reduction: float = Field(ge=0, le=1)
    minimum_valid_rate: float = Field(ge=0, le=1)
    maximum_fallback_rate: float = Field(ge=0, le=1)
    maximum_provider_error_rate: float = Field(ge=0, le=1)
    maximum_persona_alignment_decline: float = Field(ge=0, le=1)


class RepairExperimentPlan(BaseModel):
    """Hypothesis and locks created before inspecting candidate changes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[REPAIR_PLAN_SCHEMA] = REPAIR_PLAN_SCHEMA
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,99}$")
    created_at: datetime
    design_contract_path: str
    design_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_path: str
    target_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_cluster_id: str
    baseline_game_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    baseline_game_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    hypothesis: str = Field(min_length=20, max_length=1200)
    predicted_effect: str = Field(min_length=20, max_length=1200)
    mechanism_class: str
    allowlist: tuple[str, ...] = Field(min_length=1)
    maximum_changed_files: int = Field(ge=1, le=10)
    maximum_changed_lines: int = Field(ge=1, le=500)
    fixed_seeds: tuple[int, ...] = Field(min_length=1)
    holdout_seeds: tuple[int, ...] = Field(min_length=1)
    thresholds: RepairThresholds
    facts: tuple[CampaignCitation, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def _plan_is_locked(self) -> RepairExperimentPlan:
        _safe_paths((*self.allowlist, self.design_contract_path, self.target_path))
        if set(self.fixed_seeds) & set(self.holdout_seeds):
            raise ValueError("repair fixed and holdout seeds must be disjoint")
        if len({item.persona for item in self.facts}) < 2:
            raise ValueError("repair hypothesis needs cross-persona facts")
        return self

    def fingerprint(self) -> str:
        return _canonical_sha256(self.model_dump(mode="json"))


class PatchEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    patched_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    patched_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    patch_path: str
    patch_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mechanism_class: str
    modified_paths: tuple[str, ...] = Field(min_length=1)
    changed_files: int = Field(ge=1)
    added_lines: int = Field(ge=0)
    deleted_lines: int = Field(ge=0)

    @model_validator(mode="after")
    def _patch_counts_match(self) -> PatchEvidence:
        _safe_paths((*self.modified_paths, self.patch_path))
        if self.changed_files != len(self.modified_paths):
            raise ValueError("patch changed_files differs from modified paths")
        if self.baseline_commit == self.patched_commit:
            raise ValueError("patch must change the game commit")
        return self


class FocusedTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command: tuple[str, ...] = Field(min_length=1)
    exit_code: int
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_seconds: float = Field(ge=0)


class RepairMetricSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cohort: RepairCohort
    game_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    decision_policy: Literal["fixture-authoring-policy-v1"] = (
        "fixture-authoring-policy-v1"
    )
    seeds: tuple[int, ...] = Field(min_length=1)
    cells: int = Field(ge=1)
    weeks: int = Field(ge=1)
    target_members: int = Field(ge=0)
    target_personas: int = Field(ge=0)
    mean_final_money: float | None
    mean_max_stress: float | None
    valid_rate: float = Field(ge=0, le=1)
    fallback_rate: float = Field(ge=0, le=1)
    provider_error_rate: float = Field(ge=0, le=1)
    persona_alignment_rate: float | None = Field(default=None, ge=0, le=1)
    critical_invariants: dict[str, int]
    designed_failure_endings: tuple[str, ...]
    ending_counts: dict[str, int]
    artifact_path: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _snapshot_path_is_safe(self) -> RepairMetricSnapshot:
        _safe_paths((self.artifact_path,))
        if self.target_members > self.cells or self.target_personas > 6:
            raise ValueError("repair target counts exceed cohort size")
        return self


class RepairComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fixed_member_delta: int
    fixed_relative_reduction: float
    holdout_member_delta: int
    holdout_relative_reduction: float
    fixed_persona_alignment_delta: float | None
    holdout_persona_alignment_delta: float | None


class RepairGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_id: str
    status: GateStatus
    detail: str
    evidence_paths: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _gate_paths_are_safe(self) -> RepairGateResult:
        _safe_paths(self.evidence_paths)
        return self


class CodexProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_reference: str = Field(min_length=1)
    feedback_session_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    skill: Literal["playtest-forge"] = "playtest-forge"
    hypothesis_owned_by_codex: Literal[True] = True
    patch_owned_by_codex: Literal[True] = True
    decision_owned_by_codex: Literal[True] = True


class RepairExperimentRecord(BaseModel):
    """Complete proof; acceptance is impossible when any required gate is absent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[REPAIR_RECORD_SCHEMA] = REPAIR_RECORD_SCHEMA
    plan: RepairExperimentPlan
    plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    patch: PatchEvidence
    focused_tests: tuple[FocusedTestResult, ...] = Field(min_length=1)
    snapshots: tuple[RepairMetricSnapshot, ...] = Field(min_length=4, max_length=4)
    comparison: RepairComparison
    gates: tuple[RepairGateResult, ...] = Field(min_length=1)
    decision: RepairDecision
    decision_reason: str = Field(min_length=20, max_length=1200)
    codex: CodexProvenance
    completed_at: datetime

    @model_validator(mode="after")
    def _proof_controls_decision(self) -> RepairExperimentRecord:
        if self.plan_fingerprint != self.plan.fingerprint():
            raise ValueError("repair plan fingerprint mismatch")
        if self.patch.baseline_commit != self.plan.baseline_game_commit:
            raise ValueError("patch baseline differs from locked plan")
        if self.patch.mechanism_class != self.plan.mechanism_class:
            raise ValueError("patch mechanism differs from locked plan")
        if not set(self.patch.modified_paths).issubset(self.plan.allowlist):
            raise ValueError("patch modifies a path outside the locked allowlist")
        if self.patch.changed_files > self.plan.maximum_changed_files:
            raise ValueError("patch exceeds changed-file budget")
        if self.patch.added_lines + self.patch.deleted_lines > self.plan.maximum_changed_lines:
            raise ValueError("patch exceeds changed-line budget")
        by_cohort = {item.cohort: item for item in self.snapshots}
        if set(by_cohort) != set(RepairCohort):
            raise ValueError("repair proof requires all four unique cohorts")
        if (
            by_cohort[RepairCohort.BASELINE_FIXED].seeds != self.plan.fixed_seeds
            or by_cohort[RepairCohort.PATCHED_FIXED].seeds != self.plan.fixed_seeds
            or by_cohort[RepairCohort.BASELINE_HOLDOUT].seeds != self.plan.holdout_seeds
            or by_cohort[RepairCohort.PATCHED_HOLDOUT].seeds != self.plan.holdout_seeds
        ):
            raise ValueError("repair snapshot seeds differ from locked cohorts")
        if (
            by_cohort[RepairCohort.BASELINE_FIXED].game_commit
            != self.plan.baseline_game_commit
            or by_cohort[RepairCohort.BASELINE_HOLDOUT].game_commit
            != self.plan.baseline_game_commit
            or by_cohort[RepairCohort.PATCHED_FIXED].game_commit
            != self.patch.patched_commit
            or by_cohort[RepairCohort.PATCHED_HOLDOUT].game_commit
            != self.patch.patched_commit
        ):
            raise ValueError("repair snapshot game commits differ from plan/patch")
        self._validate_comparison(by_cohort)
        if self.decision == RepairDecision.ACCEPTED:
            self._require_acceptance(by_cohort)
        return self

    def _validate_comparison(
        self, by_cohort: dict[RepairCohort, RepairMetricSnapshot]
    ) -> None:
        baseline_fixed = by_cohort[RepairCohort.BASELINE_FIXED]
        patched_fixed = by_cohort[RepairCohort.PATCHED_FIXED]
        baseline_holdout = by_cohort[RepairCohort.BASELINE_HOLDOUT]
        patched_holdout = by_cohort[RepairCohort.PATCHED_HOLDOUT]
        expected = (
            patched_fixed.target_members - baseline_fixed.target_members,
            _reduction(baseline_fixed.target_members, patched_fixed.target_members),
            patched_holdout.target_members - baseline_holdout.target_members,
            _reduction(
                baseline_holdout.target_members, patched_holdout.target_members
            ),
            _delta(
                baseline_fixed.persona_alignment_rate,
                patched_fixed.persona_alignment_rate,
            ),
            _delta(
                baseline_holdout.persona_alignment_rate,
                patched_holdout.persona_alignment_rate,
            ),
        )
        observed = (
            self.comparison.fixed_member_delta,
            self.comparison.fixed_relative_reduction,
            self.comparison.holdout_member_delta,
            self.comparison.holdout_relative_reduction,
            self.comparison.fixed_persona_alignment_delta,
            self.comparison.holdout_persona_alignment_delta,
        )
        if observed != expected:
            raise ValueError("repair comparison does not recompute from snapshots")

    def _require_acceptance(
        self, by_cohort: dict[RepairCohort, RepairMetricSnapshot]
    ) -> None:
        gate_ids = {item.gate_id for item in self.gates}
        if gate_ids != REQUIRED_REPAIR_GATES or len(self.gates) != len(gate_ids):
            raise ValueError("accepted repair lacks the exact required gate set")
        if any(item.exit_code != 0 for item in self.focused_tests):
            raise ValueError("accepted repair has a failed focused test")
        if any(item.status != GateStatus.PASSED for item in self.gates):
            raise ValueError("accepted repair has a failed gate")
        thresholds = self.plan.thresholds
        patched_fixed = by_cohort[RepairCohort.PATCHED_FIXED]
        if patched_fixed.target_members > thresholds.acceptance_max_fixed_members:
            raise ValueError("accepted repair misses fixed target threshold")
        if (
            self.comparison.holdout_relative_reduction
            < thresholds.minimum_holdout_relative_reduction
        ):
            raise ValueError("accepted repair misses holdout target threshold")
        alignment_deltas = (
            self.comparison.fixed_persona_alignment_delta,
            self.comparison.holdout_persona_alignment_delta,
        )
        if any(
            value is None
            or value < -thresholds.maximum_persona_alignment_decline
            for value in alignment_deltas
        ):
            raise ValueError("accepted repair exceeds persona alignment decline")
        for snapshot in (
            patched_fixed,
            by_cohort[RepairCohort.PATCHED_HOLDOUT],
        ):
            if any(value != 0 for value in snapshot.critical_invariants.values()):
                raise ValueError("accepted repair violates a critical invariant")
            if snapshot.valid_rate < thresholds.minimum_valid_rate:
                raise ValueError("accepted repair lowers decision validity")
            if snapshot.fallback_rate > thresholds.maximum_fallback_rate:
                raise ValueError("accepted repair exceeds fallback threshold")
            if snapshot.provider_error_rate > thresholds.maximum_provider_error_rate:
                raise ValueError("accepted repair exceeds provider error threshold")


def write_repair_record_atomic(
    path: str | Path, record: RepairExperimentRecord
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(record.model_dump_json(indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(temporary).replace(destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safe_paths(values: tuple[str, ...]) -> None:
    for value in values:
        path = PurePosixPath(value.replace("\\", "/"))
        if not value or path.is_absolute() or ".." in path.parts:
            raise ValueError("repair evidence paths must be repository-relative")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _reduction(baseline: int, patched: int) -> float:
    if baseline == 0:
        return 0.0 if patched == 0 else -1.0
    return round((baseline - patched) / baseline, 6)


def _delta(baseline: float | None, patched: float | None) -> float | None:
    if baseline is None or patched is None:
        return None
    return round(patched - baseline, 6)


__all__ = [
    "CodexProvenance",
    "FocusedTestResult",
    "GateStatus",
    "PatchEvidence",
    "REQUIRED_REPAIR_GATES",
    "REPAIR_PLAN_SCHEMA",
    "REPAIR_RECORD_SCHEMA",
    "RepairCohort",
    "RepairComparison",
    "RepairDecision",
    "RepairExperimentPlan",
    "RepairExperimentRecord",
    "RepairGateResult",
    "RepairMetricSnapshot",
    "RepairThresholds",
    "file_sha256",
    "write_repair_record_atomic",
]
