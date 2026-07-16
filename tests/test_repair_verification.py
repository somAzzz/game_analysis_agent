"""Fixed/holdout comparison and decision gate tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from game_analysis_agent.design_contract import DesignIntentContract
from game_analysis_agent.repair_experiment import (
    CodexProvenance,
    FocusedTestResult,
    PatchEvidence,
    RepairCohort,
    RepairExperimentPlan,
    RepairMetricSnapshot,
)
from game_analysis_agent.repair_verification import build_repair_record

ROOT = Path(__file__).resolve().parents[1]


def _design() -> DesignIntentContract:
    return DesignIntentContract.model_validate_json(
        (ROOT / "config/build_week_2026_design_contract.json").read_text()
    )


def _plan() -> RepairExperimentPlan:
    target = json.loads((ROOT / "config/build_week_2026_target.json").read_text())
    design = _design()
    return RepairExperimentPlan.model_validate(
        {
            "experiment_id": "verification-test-v1",
            "created_at": datetime.now(tz=UTC),
            "design_contract_path": "config/build_week_2026_design_contract.json",
            "design_contract_sha256": "a" * 64,
            "target_path": "config/build_week_2026_target.json",
            "target_sha256": "b" * 64,
            "selected_cluster_id": target["selected_cluster_id"],
            "baseline_game_commit": "c" * 40,
            "baseline_game_tree": "d" * 40,
            "hypothesis": "Recurring living cost drives all intents into the same attractor.",
            "predicted_effect": "One bounded economy change reduces fixed and holdout entry.",
            "mechanism_class": "recurring_living_cost_drift",
            "allowlist": ["scripts/simulation/EconomyRules.gd"],
            "maximum_changed_files": 1,
            "maximum_changed_lines": 20,
            "fixed_seeds": target["fixed_seeds"],
            "holdout_seeds": target["holdout_seeds"],
            "thresholds": {
                "acceptance_max_fixed_members": design.selected_target.acceptance_max_fixed_members,
                "minimum_holdout_relative_reduction": design.selected_target.minimum_holdout_relative_reduction,
                "minimum_valid_rate": design.protected_metrics.minimum_valid_rate,
                "maximum_fallback_rate": design.protected_metrics.maximum_fallback_rate,
                "maximum_provider_error_rate": design.protected_metrics.maximum_provider_error_rate,
                "maximum_persona_alignment_decline": design.protected_metrics.maximum_persona_alignment_decline,
            },
            "facts": target["evidence"],
        }
    )


def _snapshot(cohort: RepairCohort, members: int) -> RepairMetricSnapshot:
    patched = cohort.value.startswith("patched")
    return RepairMetricSnapshot(
        cohort=cohort,
        game_commit=("e" if patched else "c") * 40,
        seeds=(42, 43, 44) if "fixed" in cohort.value else (1042, 1043, 1044),
        cells=18,
        weeks=342,
        target_members=members,
        target_personas=6 if members else 0,
        mean_final_money=100 if patched else 0,
        mean_max_stress=85 if patched else 100,
        valid_rate=1,
        fallback_rate=0,
        provider_error_rate=0,
        persona_alignment_rate=0.5,
        critical_invariants={"pipeline_stalled": 0},
        designed_failure_endings=("cashflow_collapse",),
        ending_counts={"cashflow_collapse": 18},
        artifact_path=f"reports/{cohort.value}.json",
        artifact_sha256="f" * 64,
    )


def _record(holdout_members: int):
    plan = _plan()
    return build_repair_record(
        plan=plan,
        patch=PatchEvidence(
            baseline_commit="c" * 40,
            patched_commit="e" * 40,
            patched_tree="1" * 40,
            patch_path="reports/patch.diff",
            patch_sha256="2" * 64,
            mechanism_class=plan.mechanism_class,
            modified_paths=plan.allowlist,
            changed_files=1,
            added_lines=1,
            deleted_lines=1,
        ),
        focused_tests=(
            FocusedTestResult(
                command=("godot", "validate"),
                exit_code=0,
                output_sha256="3" * 64,
                duration_seconds=1,
            ),
        ),
        snapshots=(
            _snapshot(RepairCohort.BASELINE_FIXED, 18),
            _snapshot(RepairCohort.PATCHED_FIXED, 10),
            _snapshot(RepairCohort.BASELINE_HOLDOUT, 18),
            _snapshot(RepairCohort.PATCHED_HOLDOUT, holdout_members),
        ),
        design=_design(),
        codex=CodexProvenance(
            task_reference="task", feedback_session_id="session", model="gpt-5.6"
        ),
        completed_at=datetime.now(tz=UTC),
    )


def test_four_cohort_improvement_passes_every_gate_and_accepts() -> None:
    record = _record(12)

    assert record.decision.value == "accepted"
    assert record.comparison.fixed_relative_reduction > 0.4
    assert record.comparison.holdout_relative_reduction > 0.3
    assert all(item.status.value == "passed" for item in record.gates)


def test_holdout_overfit_is_preserved_as_rejected_experiment() -> None:
    record = _record(16)

    assert record.decision.value == "rejected"
    assert any(
        item.gate_id == "holdout_target" and item.status.value == "failed"
        for item in record.gates
    )
