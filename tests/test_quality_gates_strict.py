from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.quality_gates import evaluate_report_dir


def _write_gates(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "gates.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _failure_gates(report: dict) -> set[str]:
    return {item["gate"] for item in report["failures"]}


def test_required_inputs_and_unknown_keys_fail_closed(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail:
  ending_id_empty: 0
balance:
  max_action_rate_per_run: 0.8
  typo_threshold: 1
outcomes: {}
design: {}
""",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert {
        "input.anomalies",
        "input.action_pick_rates",
        "config.invalid",
    } <= _failure_gates(report)
    assert any(
        item.get("actual") == "balance.typo_threshold"
        for item in report["failures"]
    )


def test_corrupt_jsonl_csv_and_optional_json_are_failures(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail:
  ending_id_empty: 0
balance:
  max_action_rate_per_run: 1.0
outcomes: {}
design: {}
""",
    )
    (tmp_path / "anomalies.jsonl").write_text("{bad json\n", encoding="utf-8")
    (tmp_path / "action_pick_rates.csv").write_text(
        'policy,action_id,count,rate_per_run\nbalanced,"unterminated,1,0.5\n',
        encoding="utf-8",
    )
    (tmp_path / "coverage_report.json").write_text("{bad", encoding="utf-8")

    report = evaluate_report_dir(tmp_path, gates)

    assert {
        "input.anomalies",
        "input.action_pick_rates",
        "input.coverage_report",
    } <= _failure_gates(report)


def test_manifest_selects_realistic_threshold_for_legacy_rows(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance:
  max_single_ending_rate_normal: 0.45
  max_single_ending_rate_realistic: 0.75
outcomes: {}
design: {}
""",
    )
    (tmp_path / "report_manifest.json").write_text(
        json.dumps(
            {
                "parameters": {
                    "policy": "balanced",
                    "difficulty": "realistic",
                    "scenario": "low_money",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "ending_distribution.csv").write_text(
        "policy,ending_id,count,rate\n"
        "balanced,a,7,0.7\n"
        "balanced,b,3,0.3\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
    assert "balanced/realistic/low_money" in report["balance_summary"]["cells"]


def test_balance_is_evaluated_per_full_cell(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance:
  max_single_ending_rate_normal: 0.5
  max_single_ending_rate_realistic: 0.7
  min_distinct_endings_normal: 2
  min_distinct_endings_realistic: 2
  max_action_rate_per_run: 0.8
outcomes: {}
design: {}
""",
    )
    (tmp_path / "ending_distribution.csv").write_text(
        "policy,difficulty,scenario,ending_id,count,rate\n"
        "balanced,normal,s1,a,6,0.6\n"
        "balanced,normal,s1,b,4,0.4\n"
        "balanced,normal,s2,a,5,0.5\n"
        "balanced,normal,s2,b,5,0.5\n"
        "balanced,realistic,s1,a,6,0.6\n"
        "balanced,realistic,s1,b,4,0.4\n",
        encoding="utf-8",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,difficulty,scenario,action_id,count,rate_per_run\n"
        "balanced,normal,s1,study,9,0.9\n"
        "balanced,normal,s2,study,7,0.7\n"
        "balanced,realistic,s1,study,7,0.7\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    ending_failures = [
        item
        for item in report["failures"]
        if item["gate"] == "balance.max_single_ending_rate"
    ]
    action_failures = [
        item
        for item in report["failures"]
        if item["gate"] == "balance.max_action_rate_per_run"
    ]
    assert [(item["difficulty"], item["scenario"]) for item in ending_failures] == [
        ("normal", "s1")
    ]
    assert [(item["difficulty"], item["scenario"]) for item in action_failures] == [
        ("normal", "s1")
    ]


def test_all_action_group_thresholds_are_enforced(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance:
  max_recovery_group_rate_per_run: 0.5
  max_escape_group_rate_per_run: 0.2
  min_study_group_rate_per_run: 1.0
  min_work_group_rate_per_run: 0.7
outcomes: {}
design: {}
""",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\n"
        "balanced,sleep_recover,4,0.6\n"
        "balanced,bilibili_rest,3,0.3\n"
        "balanced,library_day,8,0.8\n"
        "balanced,part_time_job,6,0.6\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert {
        "balance.max_recovery_group_rate_per_run",
        "balance.max_escape_group_rate_per_run",
        "balance.min_study_group_rate_per_run",
        "balance.min_work_group_rate_per_run",
    } <= _failure_gates(report)


def test_action_dominance_gate_uses_pick_share_not_count_per_run(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance:
  max_action_pick_share: 0.6
outcomes: {}
design: {}
""",
    )
    (tmp_path / "action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\n"
        "balanced,common,20,10.0\n"
        "balanced,other,20,10.0\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert "balance.max_action_pick_share" not in _failure_gates(report)
    cell = next(iter(report["balance_summary"]["cells"].values()))
    assert cell["max_action_pick_share"] == 0.5


def test_route_distance_uses_balanced_comparator_per_context(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance:
  min_route_distance: 0.15
outcomes: {}
design: {}
""",
    )
    states = [
        {
            "policy": "balanced",
            "difficulty": "normal",
            "scenario": "default",
            "final_state": {
                "academic_progress": 100,
                "money": 100,
                "social": 100,
                "visa_progress": 100,
                "stress": 100,
            },
        },
        {
            "policy": "study",
            "difficulty": "normal",
            "scenario": "default",
            "final_state": {
                "academic_progress": 120,
                "money": 120,
                "social": 105,
                "visa_progress": 120,
                "stress": 120,
            },
        },
    ]
    (tmp_path / "raw_runs.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in states),
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    failure = next(
        item
        for item in report["failures"]
        if item["gate"] == "balance.min_route_distance"
    )
    assert failure["actual"] == 0.05
    assert failure["policy"] == "study"


def test_route_distance_missing_comparator_fails_closed(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance:
  min_route_distance: 0.15
outcomes: {}
design: {}
""",
    )
    (tmp_path / "raw_runs.jsonl").write_text(
        json.dumps(
            {
                "policy": "study",
                "difficulty": "normal",
                "scenario": "default",
                "final_state": {
                    "academic_progress": 80,
                    "money": 50,
                    "social": 40,
                    "visa_progress": 70,
                    "stress": 30,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert "input.route_distance" in _failure_gates(report)


def test_design_event_metrics_are_enforced(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance: {}
outcomes: {}
design:
  max_generated_choice_ratio_key_events: 0.2
  min_key_event_tradeoff_score: 0.8
  min_event_trigger_rate_for_key_events: 0.1
""",
    )
    events = {
        "events": [
            {
                "id": "key_a",
                "event_type": "fixed",
                "choices": [
                    {"generated": True, "success_effects": {"money": 10}},
                    {
                        "generated": False,
                        "success_effects": {"money": 10, "stress": 2},
                    },
                ],
            },
            {
                "id": "key_b",
                "event_type": "fixed",
                "choices": [
                    {
                        "generated": False,
                        "success_effects": {"language": 2, "money": -5},
                    },
                    {
                        "generated": False,
                        "success_effects": {"social": 2, "stress": 1},
                    },
                ],
            },
        ]
    }
    (tmp_path / "event_graph.json").write_text(
        json.dumps(events),
        encoding="utf-8",
    )
    (tmp_path / "event_trigger_rates.csv").write_text(
        "policy,event_id,count,rate_per_run\nbalanced,key_a,2,0.2\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert {
        "design.max_generated_choice_ratio_key_events",
        "design.min_key_event_tradeoff_score",
        "design.min_event_trigger_rate_for_key_events",
    } <= _failure_gates(report)
    trigger = next(
        item
        for item in report["failures"]
        if item["gate"] == "design.min_event_trigger_rate_for_key_events"
    )
    assert trigger["event_id"] == "key_b"
    assert trigger["actual"] == 0.0


def test_agent_eval_thresholds_and_anomaly_metric_are_enforced(
    tmp_path: Path,
) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance: {}
outcomes: {}
design:
  min_decision_valid_rate: 0.9
  max_fallback_rate: 0.1
  max_illegal_action_rate: 0.05
  max_llm_error_rate: 0.01
  max_playthrough_anomalies_per_5_weeks: 1.0
""",
    )
    (tmp_path / "agent_eval.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-eval-v1",
                "valid": True,
                "metrics": {
                    "steps": 10,
                    "final_valid_rate": 0.8,
                    "fallback_rate": 0.2,
                    "illegal_action_rate": 0.1,
                    "llm_error_rate": 0.02,
                    "anomaly_rate_per_5_weeks": 2.0,
                },
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert {
        "design.min_decision_valid_rate",
        "design.max_fallback_rate",
        "design.max_illegal_action_rate",
        "design.max_llm_error_rate",
        "design.max_playthrough_anomalies_per_5_weeks",
    } <= _failure_gates(report)


def test_invalid_agent_eval_fails_closed_even_with_good_metrics(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance: {}
outcomes: {}
design:
  min_decision_valid_rate: 0.9
""",
    )
    (tmp_path / "agent_eval.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-eval-v1",
                "valid": False,
                "errors": ["trace is corrupt"],
                "metrics": {"steps": 10, "final_valid_rate": 1.0},
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is False
    assert "input.agent_eval" in _failure_gates(report)


def test_playthrough_anomalies_are_deduplicated_and_info_ignored(
    tmp_path: Path,
) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance: {}
outcomes: {}
design:
  max_playthrough_anomalies_per_5_weeks: 0.6
""",
    )
    warning = {
        "kind": "stat_overflow",
        "week": 4,
        "severity": "warning",
        "message": "same",
    }
    info = {
        "kind": "ending_id_empty",
        "week": -1,
        "severity": "info",
        "message": "partial run",
    }
    (tmp_path / "playthrough.jsonl").write_text(
        json.dumps({"week": 5, "anomalies": [warning, info]})
        + "\n"
        + json.dumps({"week": 10, "anomalies": [warning, info]})
        + "\n",
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
    rates = report["design_summary"]["playthrough_anomaly_rates"]
    assert rates[0]["rate"] == 0.5

def test_monte_carlo_report_skips_play_only_agent_metrics(tmp_path: Path) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance: {}
outcomes: {}
design:
  min_decision_valid_rate: 0.9
  max_fallback_rate: 0.1
  max_playthrough_anomalies_per_5_weeks: 1
""",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
    warning_gates = {item["gate"] for item in report["warnings"]}
    assert "design.agent_eval_not_applicable" in warning_gates
    assert "design.playthrough_anomalies_not_applicable" in warning_gates


def test_route_gate_reads_fresh_validation_prerequisite_traces(
    tmp_path: Path,
) -> None:
    gates = _write_gates(
        tmp_path,
        """
critical_fail: {}
balance:
  min_route_distance: 0.15
outcomes: {}
design: {}
""",
    )
    balanced = {
        "policy": "balanced",
        "difficulty": "normal",
        "scenario": "default",
        "final_state": {
            "academic_progress": 100,
            "money": 100,
            "social": 100,
            "visa_progress": 100,
            "stress": 100,
        },
    }
    study = {
        "policy": "study",
        "difficulty": "normal",
        "scenario": "default",
        "final_state": {
            "academic_progress": 200,
            "money": 200,
            "social": 200,
            "visa_progress": 200,
            "stress": 200,
        },
    }
    (tmp_path / "raw_runs.jsonl").write_text(
        json.dumps(balanced) + "\n",
        encoding="utf-8",
    )
    route_trace = tmp_path / "route_audit_study.jsonl"
    route_trace.write_text(json.dumps(study) + "\n", encoding="utf-8")
    (tmp_path / "validation_summary.json").write_text(
        json.dumps(
            {
                "prerequisites": [
                    {
                        "logical_path": "reports/route_audit_study.jsonl",
                        "path": str(route_trace),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_report_dir(tmp_path, gates)

    assert report["passed"] is True
    assert "input.route_distance" not in _failure_gates(report)
