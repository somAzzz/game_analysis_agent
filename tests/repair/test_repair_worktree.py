"""Isolated worktree, allowlist, budget, and patch persistence tests."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from game_analysis_agent.repair_experiment import RepairExperimentPlan
from game_analysis_agent.repair_worktree import (
    PROTECTED_REPAIR_PATHS,
    RepairWorktreeError,
    create_repair_worktree,
    validate_and_save_patch,
    validate_verification_worktrees,
)


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "game"
    repository.mkdir()
    validator = repository / PROTECTED_REPAIR_PATHS[0]
    validator.parent.mkdir(parents=True)
    validator.write_text("extends SceneTree\n", encoding="utf-8")
    _git(repository, "init")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "Test")
    source = repository / "scripts/simulation/EconomyRules.gd"
    source.parent.mkdir(parents=True)
    source.write_text("const COST = 100\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository, _git(repository, "rev-parse", "HEAD")


def _plan(baseline: str, tree: str, *, lines: int = 10) -> RepairExperimentPlan:
    return RepairExperimentPlan.model_validate(
        {
            "experiment_id": "worktree-test-v1",
            "created_at": datetime.now(tz=UTC),
            "design_contract_path": "config/design.json",
            "design_contract_sha256": "a" * 64,
            "target_path": "config/target.json",
            "target_sha256": "b" * 64,
            "selected_cluster_id": "cashflow-stress-attractor",
            "baseline_game_commit": baseline,
            "baseline_game_tree": tree,
            "hypothesis": "Recurring living costs create the shared failure attractor.",
            "predicted_effect": "A bounded cost change reduces cross-persona collapse.",
            "mechanism_class": "recurring_living_cost_drift",
            "allowlist": ["scripts/simulation/EconomyRules.gd"],
            "maximum_changed_files": 1,
            "maximum_changed_lines": lines,
            "fixed_seeds": [42, 43, 44],
            "holdout_seeds": [1042, 1043, 1044],
            "thresholds": {
                "acceptance_max_fixed_members": 12,
                "minimum_holdout_relative_reduction": 0.25,
                "minimum_valid_rate": 0.95,
                "maximum_fallback_rate": 0.05,
                "maximum_provider_error_rate": 0.05,
                "maximum_persona_alignment_decline": 0.05,
            },
            "facts": [
                {
                    "campaign_id": "c",
                    "cell_id": "newbie-seed-42-a",
                    "persona": "newbie",
                    "seed": 42,
                    "week": 3,
                    "artifact_path": "persona_runs.jsonl",
                    "line_number": 1,
                    "record_sha256": "1" * 64,
                },
                {
                    "campaign_id": "c",
                    "cell_id": "money-seed-43-b",
                    "persona": "money",
                    "seed": 43,
                    "week": 4,
                    "artifact_path": "persona_runs.jsonl",
                    "line_number": 2,
                    "record_sha256": "2" * 64,
                },
            ],
        }
    )


def test_isolated_committed_allowed_patch_is_saved_before_verification(tmp_path: Path) -> None:
    repository, baseline = _repository(tmp_path)
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    worktree = create_repair_worktree(
        source_repository=repository,
        destination=tmp_path / "candidate",
        baseline_commit=baseline,
        branch="codex/repair-test",
    )
    source = worktree / "scripts/simulation/EconomyRules.gd"
    source.write_text("const COST = 90\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-m", "repair")

    evidence = validate_and_save_patch(
        worktree=worktree,
        plan=_plan(baseline, tree),
        patch_path="reports/patch.diff",
        project_root=tmp_path,
    )

    assert evidence.modified_paths == ("scripts/simulation/EconomyRules.gd",)
    assert evidence.changed_files == 1
    assert evidence.added_lines + evidence.deleted_lines == 2
    assert (tmp_path / evidence.patch_path).is_file()


def test_patch_rejects_path_outside_allowlist(tmp_path: Path) -> None:
    repository, baseline = _repository(tmp_path)
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    worktree = create_repair_worktree(
        source_repository=repository,
        destination=tmp_path / "candidate",
        baseline_commit=baseline,
        branch="codex/outside-test",
    )
    (worktree / "README.md").write_text("changed\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-m", "outside")

    with pytest.raises(RepairWorktreeError, match="outside allowlist"):
        validate_and_save_patch(
            worktree=worktree,
            plan=_plan(baseline, tree),
            patch_path="reports/patch.diff",
            project_root=tmp_path,
        )


def test_patch_rejects_seed_specific_branch(tmp_path: Path) -> None:
    repository, baseline = _repository(tmp_path)
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    worktree = create_repair_worktree(
        source_repository=repository,
        destination=tmp_path / "candidate",
        baseline_commit=baseline,
        branch="codex/seed-test",
    )
    source = worktree / "scripts/simulation/EconomyRules.gd"
    source.write_text("const COST = 100\nif seed == 1042:\n\tpass\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-m", "seed branch")

    with pytest.raises(RepairWorktreeError, match="seed-specific"):
        validate_and_save_patch(
            worktree=worktree,
            plan=_plan(baseline, tree),
            patch_path="reports/patch.diff",
            project_root=tmp_path,
        )


def test_patch_rejects_changes_to_protected_focused_validator(tmp_path: Path) -> None:
    repository, baseline = _repository(tmp_path)
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    worktree = create_repair_worktree(
        source_repository=repository,
        destination=tmp_path / "candidate",
        baseline_commit=baseline,
        branch="codex/protected-test",
    )
    validator = worktree / PROTECTED_REPAIR_PATHS[0]
    validator.write_text("extends SceneTree\nfunc _init(): quit(0)\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-m", "weaken validator")
    plan = _plan(baseline, tree).model_copy(update={"allowlist": PROTECTED_REPAIR_PATHS})

    with pytest.raises(RepairWorktreeError, match="protected validator"):
        validate_and_save_patch(
            worktree=worktree,
            plan=plan,
            patch_path="reports/protected.diff",
            project_root=tmp_path,
            protected_paths=PROTECTED_REPAIR_PATHS,
        )


def test_verification_binds_real_worktrees_tree_and_patch_bytes(tmp_path: Path) -> None:
    repository, baseline = _repository(tmp_path)
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    plan = _plan(baseline, tree)
    worktree = create_repair_worktree(
        source_repository=repository,
        destination=tmp_path / "candidate",
        baseline_commit=baseline,
        branch="codex/binding-test",
    )
    source = worktree / "scripts/simulation/EconomyRules.gd"
    source.write_text("const COST = 90\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-m", "bounded repair")
    evidence = validate_and_save_patch(
        worktree=worktree,
        plan=plan,
        patch_path="reports/binding.diff",
        project_root=tmp_path,
    )

    validate_verification_worktrees(
        baseline_game=repository,
        patched_game=worktree,
        plan=plan,
        patch=evidence,
        project_root=tmp_path,
    )

    wrong_tree = evidence.model_copy(update={"patched_tree": "f" * 40})
    with pytest.raises(RepairWorktreeError, match="tree differs"):
        validate_verification_worktrees(
            baseline_game=repository,
            patched_game=worktree,
            plan=plan,
            patch=wrong_tree,
            project_root=tmp_path,
        )

    (tmp_path / evidence.patch_path).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(RepairWorktreeError, match="bytes or hash"):
        validate_verification_worktrees(
            baseline_game=repository,
            patched_game=worktree,
            plan=plan,
            patch=evidence,
            project_root=tmp_path,
        )
