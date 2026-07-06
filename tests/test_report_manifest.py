from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.report_manifest import (
    MANIFEST_FILE,
    REPORT_INDEX_FILE,
    write_report_manifest,
    write_reports_index,
)


def test_write_report_manifest_indexes_raw_runs(tmp_path: Path) -> None:
    raw = tmp_path / "raw_runs.jsonl"
    raw.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "run_id": 7,
                        "policy": "balanced",
                        "seed": 42,
                        "scenario": "default_first_semester",
                        "final_ending_id": "stable_start",
                        "weekly_log": [{"week": 1}],
                    }
                ),
                json.dumps(
                    {
                        "run_id": 8,
                        "policy": "work",
                        "seed": 43,
                        "final_ending_id": "cashflow_collapse",
                        "weekly_log": [],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = write_report_manifest(
        tmp_path,
        report_type="balance",
        run_id="trace-test",
        command="analyze",
        source_files=[raw],
        generated_files=["summary.json"],
    )

    assert (tmp_path / MANIFEST_FILE).exists()
    assert manifest["run_id"] == "trace-test"
    assert manifest["trace"]["primary_file"] == "raw_runs.jsonl"
    assert manifest["trace"]["runs"][0]["run_id"] == 7
    assert manifest["trace"]["runs"][0]["line"] == 1
    assert manifest["source_files"][0]["sha256"]


def test_write_report_manifest_indexes_playthrough_steps(tmp_path: Path) -> None:
    (tmp_path / "playthrough.jsonl").write_text(
        json.dumps(
            {
                "run_id": "play-001",
                "step_id": "s1",
                "week": 1,
                "chosen_actions": ["study_library"],
                "triggered_event_id": "arrival",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = write_report_manifest(
        tmp_path,
        report_type="play",
        run_id="play-001",
        command="play",
        generated_files=["playthrough.jsonl"],
    )

    assert manifest["trace"]["runs"][0]["run_id"] == "play-001"
    assert manifest["trace"]["steps"][0]["step_id"] == "s1"
    assert manifest["trace"]["steps"][0]["line"] == 1


def test_write_reports_index_collects_manifests(tmp_path: Path) -> None:
    report_dir = tmp_path / "balance" / "run-a"
    write_report_manifest(
        report_dir,
        report_type="balance",
        run_id="run-a",
        command="sim",
        summary={"total_runs": 2},
    )

    index = write_reports_index(tmp_path)

    assert (tmp_path / REPORT_INDEX_FILE).exists()
    assert index["report_count"] == 1
    assert index["reports"][0]["run_id"] == "run-a"
    assert index["reports"][0]["manifest"] == "balance/run-a/report_manifest.json"
