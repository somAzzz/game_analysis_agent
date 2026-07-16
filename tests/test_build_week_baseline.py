"""Tests for the canonical Build Week baseline declaration and comparison."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent.build_week_baseline import (
    BaselineError,
    build_command_plan,
    compare_baselines,
    load_baseline_config,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/build_week_2026_baseline.json"


def test_tracked_baseline_config_has_fixed_real_game_parameters() -> None:
    config = load_baseline_config(CONFIG)

    assert config["parameters"] == {
        "runs": 100,
        "policy": "balanced",
        "seed": 42,
        "weeks": 20,
        "difficulty": "normal",
        "scenario": "default_first_semester",
    }
    assert "demo" not in config["contract_validators"]
    assert config["quality_observation"]["validator"] == "demo"


def test_command_plan_runs_clean_contracts_observation_and_invariants(tmp_path: Path) -> None:
    config = load_baseline_config(CONFIG)
    plan = build_command_plan(config, project_root=ROOT, output_dir=tmp_path)

    assert [item[0] for item in plan] == [
        "simulate_and_analyze",
        "export_catalog",
        "reanalyze_with_catalog",
        "validate_contracts",
        "observe_quality_defect",
        "evaluate_invariants",
    ]
    assert plan[4][2] == {1}
    assert "config/ci_gates.yaml" in " ".join(plan[5][1])


def test_compare_baselines_is_byte_exact(tmp_path: Path) -> None:
    config = {"canonical_artifacts": ["raw.jsonl", "nested/report.json"]}
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        (root / "nested").mkdir(parents=True)
        (root / "raw.jsonl").write_text("same\n", encoding="utf-8")
        (root / "nested/report.json").write_text("{}\n", encoding="utf-8")

    assert compare_baselines(first, second, config)["status"] == "passed"
    (second / "raw.jsonl").write_text("changed\n", encoding="utf-8")
    comparison = compare_baselines(first, second, config)

    assert comparison["status"] == "failed"
    assert comparison["mismatches"][0]["path"] == "raw.jsonl"


def test_config_rejects_unsafe_artifact_path(tmp_path: Path) -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    payload["canonical_artifacts"] = ["../private"]
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BaselineError, match="unsafe path"):
        load_baseline_config(path)
