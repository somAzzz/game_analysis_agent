from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.report_manifest import (
    MANIFEST_FILE,
    REPORT_INDEX_FILE,
    execution_source_fingerprint,
    runtime_source_fingerprint,
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
    assert manifest["source_files"][0]["modified_at"]
    assert manifest["schema_version"] == "trace-manifest-v2"
    provenance = manifest["provenance"]
    assert provenance["agent_repository"]["commit"]
    assert len(provenance["fingerprints"]["config_sha256"]) == 64
    assert len(provenance["fingerprints"]["prompts_sha256"]) == 64
    assert len(provenance["fingerprints"]["runtime_source_sha256"]) == 64
    assert len(provenance["fingerprints"]["execution_source_sha256"]) == 64
    assert provenance["runtime"]["python"]


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


def test_runtime_source_fingerprint_tracks_source_but_ignores_cache(tmp_path: Path) -> None:
    source = tmp_path / "src" / "package" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    first = runtime_source_fingerprint(tmp_path)

    cache = source.parent / "__pycache__" / "module.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"generated")
    assert runtime_source_fingerprint(tmp_path) == first

    source.write_text("VALUE = 2\n", encoding="utf-8")
    assert runtime_source_fingerprint(tmp_path) != first


def test_execution_source_fingerprint_tracks_game_but_ignores_reports(
    tmp_path: Path,
) -> None:
    agent_root = tmp_path / "agent"
    game_root = tmp_path / "game"
    (agent_root / "src").mkdir(parents=True)
    (agent_root / "src" / "agent.py").write_text("VALUE = 1\n", encoding="utf-8")
    (game_root / "scripts").mkdir(parents=True)
    game_script = game_root / "scripts" / "simulation.gd"
    game_script.write_text("const VALUE = 1\n", encoding="utf-8")
    first = execution_source_fingerprint(agent_root, game_root)

    (game_root / "reports").mkdir()
    (game_root / "reports" / "generated.json").write_text("{}", encoding="utf-8")
    assert execution_source_fingerprint(agent_root, game_root) == first

    game_script.write_text("const VALUE = 2\n", encoding="utf-8")
    assert execution_source_fingerprint(agent_root, game_root) != first


def test_report_manifest_records_materialized_game_without_absolute_paths(
    tmp_path: Path, monkeypatch
) -> None:
    game = tmp_path / "game"
    report = tmp_path / "report"
    game.mkdir()
    report.mkdir()
    (game / ".playtest-forge-source.json").write_text(
        json.dumps(
            {
                "schema_version": "build-week-game-materialized-v1",
                "commit": "a" * 40,
                "tree": "b" * 40,
                "archive_sha256": "c" * 64,
                "content_tree_sha256": "d" * 64,
                "file_count": 80,
            }
        ),
        encoding="utf-8",
    )
    external = tmp_path / "private" / "input.json"
    external.parent.mkdir()
    external.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GAME_PROJECT_PATH", str(game))

    manifest = write_report_manifest(
        report,
        report_type="test",
        source_files=[external],
    )

    game_source = manifest["provenance"]["game_repository"]
    assert game_source["source_type"] == "materialized_bundle"
    assert game_source["commit"] == "a" * 40
    assert manifest["source_files"][0]["path"] == "<external>/input.json"
    assert str(tmp_path) not in json.dumps(manifest)
