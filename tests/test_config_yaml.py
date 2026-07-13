"""Smoke tests for the T08 config files (matrix.yaml, gates.yaml)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def test_matrix_yaml_has_required_sections() -> None:
    matrix = _load("matrix.yaml")
    for key in ("version", "weeks", "runs_per_cell", "difficulties", "policies", "boundary"):
        assert key in matrix, f"matrix.yaml missing key: {key}"
    assert isinstance(matrix["policies"], list) and matrix["policies"]
    assert "work" in matrix["policies"]
    assert "admin" in matrix["policies"]
    assert "money" not in matrix["policies"]
    assert "low_money_start" in matrix["scenarios"]
    assert isinstance(matrix["boundary"]["extremes"], list)
    assert "zero_money" in matrix["boundary"]["extremes"]
    assert "already_registered" in matrix["boundary"]["extremes"]


def test_gates_yaml_has_required_sections() -> None:
    gates = _load("gates.yaml")
    for key in ("critical_fail", "balance", "design"):
        assert key in gates, f"gates.yaml missing key: {key}"
    # The v0.2 review-added invariants must be present and zero-tolerance.
    critical = gates["critical_fail"]
    assert critical["crisis_success_ending"] == 0
    assert critical["social_success_under_survival_crisis"] == 0
    assert critical["visa_success_without_registration"] == 0
    # Balance ceilings.
    balance = gates["balance"]
    assert balance["max_single_ending_rate_normal"] <= 0.5
    assert balance["max_action_pick_share"] <= 1.0
    assert balance["min_distinct_endings_normal"] >= 3
