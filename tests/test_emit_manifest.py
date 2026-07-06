"""Tests for ``tools.emit_manifest`` — the Python side of the React data feed."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from emit_manifest import emit_all


def test_emit_writes_top_level_manifest(tmp_path) -> None:
    """Smoke test: emit_all walks reports/ and writes a top-level manifest."""
    # Build a minimal report tree.
    balance = tmp_path / "reports" / "balance" / "test-run"
    balance.mkdir(parents=True)
    (balance / "summary.json").write_text(
        json.dumps({"total_runs": 5, "policies": {"balanced": 5}}),
        encoding="utf-8",
    )
    (balance / "ending_distribution.csv").write_text(
        "policy,ending_id,count,rate\nbalanced,academic_success,5,1.0\n",
        encoding="utf-8",
    )
    summary = emit_all(tmp_path / "reports")
    assert (tmp_path / "reports" / "manifest.json").exists()
    parsed = json.loads((tmp_path / "reports" / "manifest.json").read_text())
    assert parsed["counts"]["issues"] >= 1
    assert any(card["id"] == "test-run" for card in parsed["issues"])


def test_emit_writes_per_issue_manifest(tmp_path) -> None:
    balance = tmp_path / "reports" / "balance" / "test-run"
    balance.mkdir(parents=True)
    (balance / "raw_runs.jsonl").write_text(
        json.dumps(
            {
                "run_id": 0,
                "policy": "balanced",
                "max_weeks": 5,
                "weekly_log": [
                    {
                        "week": 1,
                        "triggered_event_id": "evt",
                        "event_choice_id": "evt.choice_01",
                        "selected_action_ids": [],
                        "after_state": {},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    emit_all(tmp_path / "reports")
    issue_manifest = tmp_path / "reports" / "browse" / "balance" / "test-run" / "manifest.json"
    assert issue_manifest.exists()
    parsed = json.loads(issue_manifest.read_text())
    assert parsed["kind"] == "balance"
    assert parsed["id"] == "test-run"
    assert parsed["raw_runs_count"] == 1


def test_emit_writes_decision_graph_manifest(tmp_path) -> None:
    balance = tmp_path / "reports" / "balance" / "graph-run"
    balance.mkdir(parents=True)
    (balance / "raw_runs.jsonl").write_text(
        json.dumps(
            {
                "run_id": 0,
                "policy": "balanced",
                "max_weeks": 5,
                "weekly_log": [
                    {
                        "week": 1,
                        "triggered_event_id": "evt",
                        "event_choice_id": "evt.choice_01",
                        "selected_action_ids": [],
                        "after_state": {},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (balance / "event_graph.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "evt",
                        "title": "Event",
                        "event_type": "fixed",
                        "trigger": {"week": 1},
                        "choices": [{"text": "a"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    emit_all(tmp_path / "reports")
    dg_manifest = (
        tmp_path / "reports" / "browse" / "decision_graph" / "graph-run" / "0" / "manifest.json"
    )
    assert dg_manifest.exists()
    parsed = json.loads(dg_manifest.read_text())
    assert parsed["policy"] == "balanced"
    assert len(parsed["event_graph"]["events"]) == 1


def test_emit_handles_missing_data_gracefully(tmp_path) -> None:
    """A report dir with only ``summary.json`` (no raw_runs) still produces a card."""
    balance = tmp_path / "reports" / "balance" / "minimal"
    balance.mkdir(parents=True)
    (balance / "summary.json").write_text(
        json.dumps({"total_runs": 1}), encoding="utf-8"
    )
    summary = emit_all(tmp_path / "reports")
    parsed = json.loads((tmp_path / "reports" / "manifest.json").read_text())
    assert any(card["id"] == "minimal" for card in parsed["issues"])
    assert parsed["counts"]["issues"] == summary["counts"]["issues"]