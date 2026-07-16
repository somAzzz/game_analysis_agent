"""Typed, hash-locked design intent approved before the repair experiment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .build_week_campaign import FrozenRepairTarget

DESIGN_INTENT_SCHEMA = "build-week-design-intent-v1"


class DesignContractError(ValueError):
    """Raised when design intent is stale, unsafe, or internally inconsistent."""


class ApprovalBasis(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    g2_review: str
    g2_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target: str
    target_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gates_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    personas_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SelectedTargetIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cluster_id: str
    baseline_fixed_members: int = Field(ge=2)
    baseline_fixed_personas: int = Field(ge=2)
    acceptance_max_fixed_members: int = Field(ge=0)
    minimum_holdout_relative_reduction: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _requires_real_improvement(self) -> SelectedTargetIntent:
        if self.acceptance_max_fixed_members >= self.baseline_fixed_members:
            raise ValueError("fixed target threshold must require improvement")
        return self


class ProtectedMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_valid_rate: float = Field(ge=0, le=1)
    maximum_fallback_rate: float = Field(ge=0, le=1)
    maximum_provider_error_rate: float = Field(ge=0, le=1)
    maximum_persona_alignment_decline: float = Field(ge=0, le=1)
    require_designed_failure_coverage: Literal[True] = True
    slacker_success_required: Literal[False] = False


class ChangeBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    maximum_changed_files: int = Field(ge=1, le=10)
    maximum_changed_lines: int = Field(ge=1, le=500)
    allowlist: tuple[str, ...] = Field(min_length=1)
    forbidden_paths: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _paths_are_safe_and_distinct(self) -> ChangeBudget:
        for value in (*self.allowlist, *self.forbidden_paths):
            path = PurePosixPath(value.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("change-budget paths must be repository-relative")
        if len(set(self.allowlist)) != len(self.allowlist):
            raise ValueError("change-budget allowlist contains duplicates")
        return self


class DesignIntentContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[DESIGN_INTENT_SCHEMA] = DESIGN_INTENT_SCHEMA
    contract_id: str
    approved_before_patch: Literal[True] = True
    approval_basis: ApprovalBasis
    selected_target: SelectedTargetIntent
    persona_intent: dict[str, Literal["non_failure", "failure_seeking"]]
    designed_failure_endings: tuple[str, ...] = Field(min_length=1)
    critical_invariants: dict[str, Literal[0]]
    protected_metrics: ProtectedMetrics
    allowed_mechanism_classes: tuple[str, ...] = Field(min_length=1)
    change_budget: ChangeBudget
    non_goals: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _intent_is_complete(self) -> DesignIntentContract:
        expected = {"newbie", "study", "money", "social", "visa", "slacker"}
        if set(self.persona_intent) != expected:
            raise ValueError("design intent must classify all six personas")
        if self.persona_intent["slacker"] != "failure_seeking":
            raise ValueError("slacker must remain failure-seeking")
        if any(
            value != "non_failure"
            for key, value in self.persona_intent.items()
            if key != "slacker"
        ):
            raise ValueError("only slacker may be classified failure-seeking")
        if len(set(self.allowed_mechanism_classes)) != len(
            self.allowed_mechanism_classes
        ):
            raise ValueError("allowed mechanism classes must be unique")
        return self

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()


def load_design_contract(
    path: str | Path, *, project_root: str | Path, verify_sources: bool = True
) -> DesignIntentContract:
    contract = DesignIntentContract.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
    if not verify_sources:
        return contract
    project = Path(project_root).resolve()
    basis = contract.approval_basis
    expected = {
        basis.g2_review: basis.g2_review_sha256,
        basis.target: basis.target_sha256,
        "config/gates.yaml": basis.gates_sha256,
        "config/player_personas.yaml": basis.personas_sha256,
    }
    for relative, digest in expected.items():
        candidate = project / relative
        if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
            raise DesignContractError(f"design approval source changed: {relative}")
    target = FrozenRepairTarget.model_validate_json(
        (project / basis.target).read_text(encoding="utf-8")
    )
    if (
        target.selected_cluster_id != contract.selected_target.cluster_id
        or target.member_count != contract.selected_target.baseline_fixed_members
        or target.persona_count != contract.selected_target.baseline_fixed_personas
    ):
        raise DesignContractError("design target differs from G2 target evidence")
    return contract


__all__ = [
    "DESIGN_INTENT_SCHEMA",
    "ChangeBudget",
    "DesignContractError",
    "DesignIntentContract",
    "ProtectedMetrics",
    "SelectedTargetIntent",
    "load_design_contract",
]
