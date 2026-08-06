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


def test_evaluate_report_dir_treats_designed_failure_as_valid_outcome(tmp_path: Path) -> None:
    gates = tmp_path / "gates.yaml"
    gates.write_text(
        """
critical_fail: {}
balance:
  max_single_ending_rate_normal: 1.0
  max_action_rate_per_run: 2.0
  min_distinct_endings_normal: 1
outcomes:
  designed_failure_endings:
    - burnout_pause
  invalid_endings:
    - unknown
    - pipeline_stalled
  require_designed_failure_coverage: true
  min_designed_failure_types_normal: 1
design: {}
""",
        encoding="utf-8",
    )
    (tmp_path / "anomalies.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "ending_distribution.csv").write_text(
        "policy,ending_id,count,rate\nbalanced,burnout_pause,1,1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\nbalanced,sleep_recover,1,1.0\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
    assert "burnout_pause" in report["outcome_summary"]["designed_failure_endings"]


def test_evaluate_report_dir_fails_on_invalid_outcome(tmp_path: Path) -> None:
    gates = tmp_path / "gates.yaml"
    gates.write_text(
        """
critical_fail: {}
balance:
  max_single_ending_rate_normal: 1.0
  max_action_rate_per_run: 2.0
  min_distinct_endings_normal: 1
outcomes:
  designed_failure_endings:
    - burnout_pause
  invalid_endings:
    - unknown
    - pipeline_stalled
design: {}
""",
        encoding="utf-8",
    )
    (tmp_path / "ending_distribution.csv").write_text(
        "policy,ending_id,count,rate\nbalanced,unknown,1,1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\nbalanced,study,1,1.0\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is False
    assert report["failures"][0]["gate"] == "outcomes.invalid_endings"


def test_evaluate_report_dir_warns_on_dominant_designed_failure(tmp_path: Path) -> None:
    gates = tmp_path / "gates.yaml"
    gates.write_text(
        """
critical_fail: {}
balance:
  max_single_ending_rate_normal: 1.0
  max_action_rate_per_run: 2.0
  min_distinct_endings_normal: 1
outcomes:
  designed_failure_endings:
    - registration_failure
    - burnout_pause
  success_endings:
    - social_connector
  invalid_endings:
    - unknown
  max_single_designed_failure_rate_play: 0.5
design: {}
""",
        encoding="utf-8",
    )
    (tmp_path / "ending_distribution.csv").write_text(
        "\n".join(
            [
                "policy,ending_id,count,rate",
                "balanced,registration_failure,4,0.666667",
                "balanced,burnout_pause,1,0.166667",
                "balanced,social_connector,1,0.166667",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\nbalanced,study,1,1.0\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
    assert any(
        warning["gate"] == "outcomes.max_single_designed_failure_rate_play"
        for warning in report["warnings"]
    )


def test_interactive_persona_distribution_balance_issues_are_warnings(tmp_path: Path) -> None:
    gates = tmp_path / "gates.yaml"
    gates.write_text(
        """
critical_fail: {}
balance:
  max_single_ending_rate_normal: 0.45
  max_action_rate_per_run: 2.0
  min_distinct_endings_normal: 5
outcomes:
  designed_failure_endings:
    - registration_failure
    - burnout_pause
  success_endings:
    - social_connector
  invalid_endings:
    - unknown
design: {}
""",
        encoding="utf-8",
    )
    (tmp_path / "ending_distribution.csv").write_text(
        "\n".join(
            [
                "policy,ending_id,count,rate",
                "interactive_personas,registration_failure,3,0.5",
                "interactive_personas,burnout_pause,2,0.333333",
                "interactive_personas,social_connector,1,0.166667",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\ninteractive_personas,study,1,1.0\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
    assert not report["failures"]
    warning_gates = {warning["gate"] for warning in report["warnings"]}
    assert "balance.max_single_ending_rate" in warning_gates
    assert "balance.min_distinct_endings_normal" in warning_gates
