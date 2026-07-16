"""The real experiment plan is frozen before candidate source inspection."""

from __future__ import annotations

from pathlib import Path

from game_analysis_agent.design_contract import load_design_contract
from game_analysis_agent.repair_experiment import RepairExperimentPlan, file_sha256

ROOT = Path(__file__).resolve().parents[1]


def test_real_repair_plan_matches_design_and_locked_source_hashes() -> None:
    plan = RepairExperimentPlan.model_validate_json(
        (ROOT / "config/build_week_2026_repair_plan.json").read_text(encoding="utf-8")
    )
    design = load_design_contract(
        ROOT / plan.design_contract_path, project_root=ROOT
    )

    assert file_sha256(ROOT / plan.design_contract_path) == plan.design_contract_sha256
    assert file_sha256(ROOT / plan.target_path) == plan.target_sha256
    assert plan.selected_cluster_id == design.selected_target.cluster_id
    assert plan.mechanism_class in design.allowed_mechanism_classes
    assert set(plan.allowlist).issubset(design.change_budget.allowlist)
    assert plan.maximum_changed_files <= design.change_budget.maximum_changed_files
    assert plan.maximum_changed_lines <= design.change_budget.maximum_changed_lines
    assert plan.fixed_seeds == (42, 43, 44)
    assert plan.holdout_seeds == (1042, 1043, 1044)
