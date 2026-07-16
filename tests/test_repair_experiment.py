"""Repair plan, proof completeness, budget, and accept/reject tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from game_analysis_agent.repair_experiment import (
    CodexProvenance,
    FocusedTestResult,
    PatchEvidence,
    RepairCohort,
    RepairComparison,
    RepairExperimentPlan,
    RepairExperimentRecord,
    RepairGateResult,
    RepairMetricSnapshot,
    RepairThresholds,
)


def _plan() -> RepairExperimentPlan:
    facts = []
    for persona, seed, line in (("newbie", 42, 1), ("money", 43, 2)):
        facts.append(
            {
                "campaign_id": "campaign-v1",
                "cell_id": f"{persona}-seed-{seed}-abc",
                "persona": persona,
                "seed": seed,
                "week": 3,
                "artifact_path": "persona_runs.jsonl",
                "line_number": line,
                "record_sha256": str(line) * 64,
            }
        )
    return RepairExperimentPlan.model_validate(
        {
            "experiment_id": "repair-v1",
            "created_at": datetime.now(tz=UTC),
            "design_contract_path": "config/design.json",
            "design_contract_sha256": "a" * 64,
            "target_path": "config/target.json",
            "target_sha256": "b" * 64,
            "selected_cluster_id": "cashflow-stress-attractor",
            "baseline_game_commit": "c" * 40,
            "baseline_game_tree": "d" * 40,
            "hypothesis": "Recurring living cost is too strong for every player intent.",
            "predicted_effect": "Lower recurring pressure will reduce cross-persona collapse.",
            "mechanism_class": "recurring_living_cost_drift",
            "allowlist": ["scripts/simulation/EconomyRules.gd"],
            "maximum_changed_files": 1,
            "maximum_changed_lines": 20,
            "fixed_seeds": [42, 43, 44],
            "holdout_seeds": [1042, 1043, 1044],
            "thresholds": RepairThresholds(
                acceptance_max_fixed_members=12,
                minimum_holdout_relative_reduction=0.25,
                minimum_valid_rate=0.95,
                maximum_fallback_rate=0.05,
                maximum_provider_error_rate=0.05,
                maximum_persona_alignment_decline=0.05,
            ),
            "facts": facts,
        }
    )


def _snapshot(cohort: RepairCohort, *, patched: bool) -> RepairMetricSnapshot:
    return RepairMetricSnapshot(
        cohort=cohort,
        game_commit=("e" if patched else "c") * 40,
        seeds=(42, 43, 44) if "fixed" in cohort.value else (1042, 1043, 1044),
        cells=18,
        weeks=342,
        target_members=9 if patched else 18,
        target_personas=4 if patched else 6,
        mean_final_money=100 if patched else 0,
        mean_max_stress=85 if patched else 100,
        valid_rate=1,
        fallback_rate=0,
        provider_error_rate=0,
        persona_alignment_rate=0.5,
        critical_invariants={"pipeline_stalled": 0},
        designed_failure_endings=("cashflow_collapse",),
        artifact_path=f"reports/{cohort.value}.json",
        artifact_sha256="f" * 64,
    )


def _record(*, decision: str = "accepted", failed_gate: bool = False, lines: int = 2):
    plan = _plan()
    return {
        "plan": plan,
        "plan_fingerprint": plan.fingerprint(),
        "patch": PatchEvidence(
            baseline_commit="c" * 40,
            patched_commit="e" * 40,
            patched_tree="1" * 40,
            patch_path="reports/patch.diff",
            patch_sha256="2" * 64,
            mechanism_class="recurring_living_cost_drift",
            modified_paths=("scripts/simulation/EconomyRules.gd",),
            changed_files=1,
            added_lines=lines,
            deleted_lines=0,
        ),
        "focused_tests": (
            FocusedTestResult(
                command=("godot", "--headless"),
                exit_code=0,
                output_sha256="3" * 64,
                duration_seconds=1,
            ),
        ),
        "snapshots": tuple(
            _snapshot(cohort, patched=cohort.value.startswith("patched"))
            for cohort in RepairCohort
        ),
        "comparison": RepairComparison(
            fixed_member_delta=-9,
            fixed_relative_reduction=0.5,
            holdout_member_delta=-9,
            holdout_relative_reduction=0.5,
            fixed_persona_alignment_delta=0,
            holdout_persona_alignment_delta=0,
        ),
        "gates": (
            RepairGateResult(
                gate_id="critical",
                status="failed" if failed_gate else "passed",
                detail="checked",
            ),
        ),
        "decision": decision,
        "decision_reason": "All fixed and holdout evidence was evaluated explicitly.",
        "codex": CodexProvenance(
            task_reference="task-1",
            feedback_session_id="session-1",
            model="gpt-5.6",
        ),
        "completed_at": datetime.now(tz=UTC),
    }


def test_complete_four_cohort_proof_can_be_accepted() -> None:
    record = RepairExperimentRecord.model_validate(_record())

    assert record.decision.value == "accepted"
    assert len(record.snapshots) == 4


def test_acceptance_rejects_failed_gate_but_rejected_record_preserves_it() -> None:
    with pytest.raises(ValueError, match="failed gate"):
        RepairExperimentRecord.model_validate(_record(failed_gate=True))

    rejected = RepairExperimentRecord.model_validate(
        _record(decision="rejected", failed_gate=True)
    )
    assert rejected.decision.value == "rejected"


def test_change_budget_is_enforced_before_acceptance() -> None:
    with pytest.raises(ValueError, match="changed-line budget"):
        RepairExperimentRecord.model_validate(_record(lines=21))
