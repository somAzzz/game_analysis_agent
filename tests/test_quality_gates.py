"""Tests for deterministic quality gates."""

from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.quality_gates import evaluate_report_dir


def test_evaluate_report_dir_fails_on_critical_anomaly(tmp_path: Path) -> None:
    gates = tmp_path / "gates.yaml"
    gates.write_text(
        """
critical_fail:
  crisis_success_ending: 0
balance:
  max_single_ending_rate_normal: 0.8
  max_action_rate_per_run: 2.0
  min_distinct_endings_normal: 1
design: {}
""",
        encoding="utf-8",
    )
    (tmp_path / "anomalies.jsonl").write_text(
        json.dumps({"kind": "crisis_success_ending"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "ending_distribution.csv").write_text(
        "policy,ending_id,count,rate\nbalanced,stable_start,1,1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\nbalanced,study,1,1.0\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is False
    assert report["failures"][0]["gate"] == "critical_fail.crisis_success_ending"


def test_evaluate_report_dir_passes_clean_report(tmp_path: Path) -> None:
    gates = tmp_path / "gates.yaml"
    gates.write_text(
        """
critical_fail:
  crisis_success_ending: 0
balance:
  max_single_ending_rate_normal: 1.0
  max_action_rate_per_run: 2.0
  min_distinct_endings_normal: 1
design: {}
""",
        encoding="utf-8",
    )
    (tmp_path / "anomalies.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "ending_distribution.csv").write_text(
        "policy,ending_id,count,rate\nbalanced,stable_start,1,1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\nbalanced,study,1,1.0\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
