from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.agent_eval import evaluate_and_write, evaluate_playthrough


def _write_artifacts(report_dir: Path) -> None:
    rows = [
        {
            "week": 1,
            "available_actions": ["study", "rest"],
            "chosen_actions": ["study"],
            "event_choice_id": "arrival.ask",
            "validation": {
                "valid": True,
                "errors": [],
                "repair_count": 0,
                "fallback_used": False,
            },
            "decision": {"risk_awareness": ["stress"]},
            "week_context": {
                "top_risks": [{"id": "stress"}],
                "event_choices": [{"choice_id": "arrival.ask"}],
                "persona_strategy": {"priorities": ["study"]},
                "available_actions": [{"id": "study", "tags": ["study"]}],
            },
            "anomalies": [],
        },
        {
            "week": 2,
            "available_actions": ["study", "rest"],
            "chosen_actions": ["rest"],
            "event_choice_id": "",
            "validation": {
                "valid": True,
                "errors": ["initial response invalid"],
                "repair_count": 1,
                "fallback_used": False,
            },
            "decision": {"risk_awareness": []},
            "week_context": {
                "top_risks": [],
                "event_choices": [],
                "persona_strategy": {"priorities": ["recovery"]},
                "available_actions": [{"id": "rest", "tags": ["recovery"]}],
            },
            "anomalies": [{"kind": "high_stress"}],
        },
    ]
    (report_dir / "playthrough.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    (report_dir / "playthrough_agent_report.json").write_text(
        json.dumps(
            {
                "llm_calls": [
                    {"latency_ms": 100, "error": None},
                    {"latency_ms": 300, "error": "timeout"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (report_dir / "playthrough_summary.md").write_text(
        "- final ending: **stable_start**\n",
        encoding="utf-8",
    )


def test_evaluate_playthrough_measures_repairs_risks_and_audit(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)

    report = evaluate_playthrough(tmp_path)
    metrics = report["metrics"]

    assert report["valid"] is True
    assert report["strict_passed"] is False
    assert any("llm_error_rate" in error for error in report["quality_errors"])
    assert report["final_ending"] == "stable_start"
    assert metrics["steps"] == 2
    assert metrics["first_pass_valid_rate"] == 0.5
    assert metrics["final_valid_rate"] == 1.0
    assert metrics["repaired_decision_rate"] == 0.5
    assert metrics["fallback_rate"] == 0.0
    assert metrics["risk_acknowledgement_rate"] == 1.0
    assert metrics["persona_alignment_rate"] == 1.0
    assert metrics["anomaly_rate_per_5_weeks"] == 2.5
    assert metrics["llm_error_rate"] == 0.5
    assert metrics["mean_latency_ms"] == 200.0


def test_evaluate_playthrough_fails_closed_on_invalid_artifacts(tmp_path: Path) -> None:
    (tmp_path / "playthrough.jsonl").write_text(
        '{"chosen_actions": ["ghost"], "available_actions": ["study"], '
        '"validation": {"valid": true}}\nnot-json\n',
        encoding="utf-8",
    )

    report = evaluate_and_write(tmp_path)

    assert report["valid"] is False
    assert report["strict_passed"] is False
    assert report["metrics"]["illegal_action_count"] == 1
    assert any("invalid JSON" in error for error in report["errors"])
    assert any("missing required artifact" in error for error in report["errors"])
    assert (tmp_path / "agent_eval.json").exists()


def test_evaluate_playthrough_rejects_all_fallback_as_strict_success(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    path = tmp_path / "playthrough.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        row["validation"]["valid"] = False
        row["validation"]["fallback_used"] = True
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    report = evaluate_playthrough(tmp_path)

    assert report["valid"] is True
    assert report["strict_passed"] is False
    assert any("final_valid_rate" in error for error in report["quality_errors"])
    assert any("fallback_rate" in error for error in report["quality_errors"])


def test_evaluate_playthrough_deduplicates_cumulative_anomalies(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    path = tmp_path / "playthrough.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    duplicate = dict(rows[-1])
    duplicate["week"] = 3
    rows.append(duplicate)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    metrics = evaluate_playthrough(tmp_path)["metrics"]

    assert metrics["steps"] == 3
    assert metrics["anomaly_count"] == 1
    assert metrics["anomaly_rate_per_5_weeks"] == 1.666667


def test_evaluate_playthrough_rejects_missing_required_event_choice(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    path = tmp_path / "playthrough.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["event_choice_id"] = ""
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    metrics = evaluate_playthrough(tmp_path)["metrics"]

    assert metrics["invalid_event_choice_count"] == 1
    assert metrics["final_valid_rate"] == 0.5


def test_evaluate_playthrough_requires_final_ending(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    (tmp_path / "playthrough_summary.md").unlink()

    report = evaluate_playthrough(tmp_path)

    assert report["valid"] is False
    assert report["final_ending"] == ""
    assert any("final ending is missing" in error for error in report["errors"])


def test_risk_acknowledgement_requires_current_risk_id(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    path = tmp_path / "playthrough.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["decision"]["risk_awareness"] = ["I considered the situation"]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    metrics = evaluate_playthrough(tmp_path)["metrics"]

    assert metrics["risk_acknowledgement_rate"] == 0.0
    assert metrics["unmatched_risk_awareness_count"] == 1


def test_persona_alignment_uses_explicit_action_tag_mapping(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    path = tmp_path / "playthrough.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["week_context"]["persona_strategy"] = {
        "priorities": ["academic_progress", "exam_readiness"],
        "alignment_action_tags": ["study", "exam"],
    }
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    metrics = evaluate_playthrough(tmp_path)["metrics"]

    assert metrics["persona_alignment_rate"] == 1.0
    assert metrics["persona_alignment_opportunities"] == 2
