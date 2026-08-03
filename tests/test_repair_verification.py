"""Fixed/holdout comparison and decision gate tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from game_analysis_agent.build_week_campaign import FrozenRepairTarget
from game_analysis_agent.design_contract import DesignIntentContract, load_design_contract
from game_analysis_agent.repair_experiment import (
    CodexProvenance,
    FocusedTestResult,
    PatchEvidence,
    RepairCohort,
    RepairExperimentPlan,
    RepairMetricSnapshot,
)
from game_analysis_agent.repair_verification import (
    RepairVerificationError,
    build_repair_record,
    compare_and_gate_repair,
    load_repair_balance_thresholds,
    validate_plan_against_design,
)

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


def _passing_balance_metrics() -> dict[str, float]:
    return {
        "maximum_single_ending_rate": 0.25,
        "minimum_distinct_endings": 5.0,
        "maximum_action_pick_share": 0.2,
        "maximum_recovery_group_rate_per_run": 2.0,
        "maximum_escape_group_rate_per_run": 1.0,
        "minimum_study_group_rate_per_run": 1.0,
        "minimum_work_group_rate_per_run": 0.5,
        "minimum_persona_route_distance": 0.2,
        "minimum_designed_failure_types": 2.0,
        "maximum_single_designed_failure_rate": 0.25,
    }


def _target_counts(members: int) -> dict[str, int]:
    personas = ("newbie", "study", "money", "social", "visa", "slacker")
    quotient, remainder = divmod(members, len(personas))
    return {
        persona: quotient + int(index < remainder)
        for index, persona in enumerate(personas)
        if quotient + int(index < remainder)
    }


def _snapshot(cohort: RepairCohort, members: int) -> RepairMetricSnapshot:
    patched = cohort.value.startswith("patched")
    target_counts = _target_counts(members)
    return RepairMetricSnapshot(
        cohort=cohort,
        game_commit=("e" if patched else "c") * 40,
        seeds=(42, 43, 44) if "fixed" in cohort.value else (1042, 1043, 1044),
        cells=18,
        weeks=342,
        target_members=members,
        target_personas=len(target_counts),
        target_members_by_persona=target_counts,
        mean_final_money=100 if patched else 0,
        mean_max_stress=85 if patched else 100,
        valid_rate=1,
        fallback_rate=0,
        provider_error_rate=0,
        persona_alignment_rate=0.5,
        critical_invariants={"pipeline_stalled": 0},
        designed_failure_endings=("cashflow_collapse", "burnout_pause"),
        ending_counts={
            "cashflow_collapse": 3,
            "burnout_pause": 3,
            "stable_start": 4,
            "social_connector": 4,
            "work_warrior": 4,
        },
        ending_counts_by_persona={
            "newbie": {"stable_start": 3},
            "study": {"stable_start": 3},
            "money": {"work_warrior": 3},
            "social": {"social_connector": 3},
            "visa": {"burnout_pause": 3},
            "slacker": {"cashflow_collapse": 3},
        },
        balance_metrics=_passing_balance_metrics(),
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
        balance_thresholds=load_repair_balance_thresholds(ROOT / "config/gates.yaml"),
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
        item.gate_id == "holdout_target" and item.status.value == "failed" for item in record.gates
    )


def test_plan_validation_rejects_weakened_thresholds_and_seed_cohorts() -> None:
    plan = RepairExperimentPlan.model_validate_json(
        (ROOT / "config/build_week_2026_repair_plan.json").read_text(encoding="utf-8")
    )
    design = load_design_contract(ROOT / plan.design_contract_path, project_root=ROOT)
    target = FrozenRepairTarget.model_validate_json(
        (ROOT / plan.target_path).read_text(encoding="utf-8")
    )

    validate_plan_against_design(plan=plan, design=design, target=target, project_root=ROOT)

    weakened = plan.model_copy(
        update={
            "thresholds": plan.thresholds.model_copy(
                update={"minimum_holdout_relative_reduction": 0.0}
            )
        }
    )
    with pytest.raises(RepairVerificationError, match="thresholds"):
        validate_plan_against_design(plan=weakened, design=design, target=target, project_root=ROOT)

    changed_seeds = plan.model_copy(update={"holdout_seeds": (7, 8, 9)})
    with pytest.raises(RepairVerificationError, match="seed cohorts"):
        validate_plan_against_design(
            plan=changed_seeds, design=design, target=target, project_root=ROOT
        )


def test_balance_gate_rejects_dominant_ending_regression() -> None:
    record = _record(12)
    snapshots = tuple(
        snapshot.model_copy(
            update={
                "balance_metrics": {
                    **snapshot.balance_metrics,
                    "maximum_single_ending_rate": 0.9,
                }
            }
        )
        if snapshot.cohort.value.startswith("patched")
        else snapshot
        for snapshot in record.snapshots
    )

    _, gates = compare_and_gate_repair(
        plan=record.plan,
        snapshots=snapshots,
        design=_design(),
        balance_thresholds=load_repair_balance_thresholds(ROOT / "config/gates.yaml"),
    )

    assert any(
        gate.gate_id == "balance_quality" and gate.status.value == "failed" for gate in gates
    )


def test_cross_persona_gate_rejects_improvement_concentrated_in_one_intent() -> None:
    record = _record(12)
    narrow_counts = {"study": 3, "money": 3, "social": 3, "visa": 3}
    snapshots = []
    for snapshot in record.snapshots:
        if snapshot.cohort.value.startswith("patched"):
            payload = snapshot.model_dump(mode="python")
            payload.update(
                target_members=12,
                target_personas=4,
                target_members_by_persona=narrow_counts,
            )
            snapshot = RepairMetricSnapshot.model_validate(payload)
        snapshots.append(snapshot)

    _, gates = compare_and_gate_repair(
        plan=record.plan,
        snapshots=tuple(snapshots),
        design=_design(),
        balance_thresholds=load_repair_balance_thresholds(ROOT / "config/gates.yaml"),
    )

    assert any(
        gate.gate_id == "non_failure_persona_improvement" and gate.status.value == "failed"
        for gate in gates
    )
