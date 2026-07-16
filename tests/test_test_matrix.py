from __future__ import annotations

import json
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from game_analysis_agent.agent_eval import evaluate_and_write
from game_analysis_agent.report_manifest import execution_source_fingerprint
from game_analysis_agent.test_matrix import (
    CELL_MANIFEST_FILE,
    MATRIX_MANIFEST_FILE,
    MATRIX_SUMMARY_FILE,
    ExecutionOutcome,
    MatrixConfigError,
    build_matrix_plan,
    execute_matrix,
    expand_matrix_cells,
    load_matrix_config,
    run_matrix_file,
)

ROOT = Path(__file__).resolve().parents[1]
MATRIX_CONFIG = ROOT / "config" / "matrix.yaml"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _small_config(tmp_path: Path) -> Path:
    payload = yaml.safe_load(MATRIX_CONFIG.read_text(encoding="utf-8"))
    payload.update(
        {
            "runs_per_cell": 2,
            "seeds": [42],
            "difficulties": ["normal"],
            "policies": ["balanced"],
            "policy_aliases": {},
            "scenarios": ["default_first_semester"],
        }
    )
    payload["boundary"].update(
        {"runs": 2, "seed": 42, "weeks": 2, "policy": "balanced", "extremes": ["zero_money"]}
    )
    payload["play"].update(
        {
            "default_persona": "newbie",
            "personas": ["newbie"],
            "weeks": 2,
            "difficulty": "normal",
            "seeds": [42],
        }
    )
    payload["play"]["outcome_coverage"]["expected_categories"] = ["success"]
    path = tmp_path / "matrix.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_cell_evidence(command_plan: Any, *, ending: str = "stable_start") -> None:
    report_dir = command_plan.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "trace-manifest-v2",
        "run_id": command_plan.cell.run_id,
        "status": "completed",
        "provenance": {
            "fingerprints": {
                "execution_source_sha256": command_plan.code_fingerprint,
            }
        },
    }
    fixture_root = ROOT / "tests" / "fixtures" / "contracts"
    if command_plan.cell.kind == "simulation":
        trace = json.loads((fixture_root / "trace_v1.json").read_text(encoding="utf-8"))
        event_graph = json.loads((fixture_root / "event_graph_v1.json").read_text(encoding="utf-8"))
        action_catalog = json.loads(
            (fixture_root / "action_catalog_v1.json").read_text(encoding="utf-8")
        )
        action_id = action_catalog["actions"][0]["id"]
        event = event_graph["events"][0]
        choice = event["choices"][0]
        choice_id = f"{event['id']}.choice_01_{choice['text'].lower().replace(' ', '_')}"
        trace.update(
            {
                "policy": command_plan.cell.parameters["policy"],
                "difficulty": command_plan.cell.parameters["difficulty"],
                "scenario": command_plan.cell.parameters["scenario"],
                "seed": command_plan.cell.parameters["seed"],
            }
        )
        trace["weekly_log"][0].update(
            {
                "available_action_ids": [action_id],
                "selected_action_ids": [action_id],
                "triggered_event_id": event["id"],
                "event_choice_id": choice_id,
            }
        )
        trace["action_sequence"] = [{"week": 1, "actions": [action_id], "event_choice": choice_id}]
        (report_dir / "raw_runs.jsonl").write_text(
            json.dumps(trace) + "\n",
            encoding="utf-8",
        )
        _write_json(report_dir / "event_graph.json", event_graph)
        _write_json(report_dir / "action_catalog.json", action_catalog)
        _write_json(
            report_dir / "summary.json",
            {"total_runs": 1, "policies": {"balanced": 1}, "top_events": {}},
        )
        _write_json(
            report_dir / "value_report.json",
            {"finding_count": 0, "by_kind": {}, "findings": []},
        )
        _write_json(
            report_dir / "route_report.json",
            {
                "finding_count": 0,
                "by_kind": {},
                "axes": [],
                "groups": [],
                "crisis_response": [],
                "ending_contradictions": [],
                "route_separation": [],
            },
        )
        _write_json(
            report_dir / "coverage_report.json",
            {
                "schema_version": "coverage-v2",
                "total_runs": 1,
                "event_coverage": {"catalog_available": True},
                "action_coverage": {"catalog_available": True},
                "data_quality": {"catalog_errors": []},
            },
        )
        (report_dir / "ending_distribution.csv").write_text(
            "policy,difficulty,scenario,ending_id,count,sample_size,rate,"
            "ci95_low,ci95_high\n"
            "balanced,normal,default_first_semester,stable_start,1,1,1.0,0.2,1.0\n",
            encoding="utf-8",
        )
        (report_dir / "action_pick_rates.csv").write_text(
            f"policy,action_id,count,rate_per_run\nbalanced,{action_id},1,1.0\n",
            encoding="utf-8",
        )
        (report_dir / "weekly_stats.csv").write_text(
            "policy,week,metric,mean,median,p10,p90,min,max\n"
            "balanced,1,money,1000,1000,1000,1000,1000,1000\n",
            encoding="utf-8",
        )
        (report_dir / "anomalies.jsonl").write_text("", encoding="utf-8")
    elif command_plan.cell.kind == "boundary":
        trace = json.loads((fixture_root / "trace_v1.json").read_text(encoding="utf-8"))
        for key in ("scenario", "content_version", "rules_version"):
            trace.pop(key)
        trace.update(
            {
                "policy": command_plan.cell.parameters["policy"],
                "seed": command_plan.cell.parameters["seed"],
                "extreme": command_plan.cell.parameters["extreme"],
            }
        )
        (report_dir / "boundary_runs.jsonl").write_text(
            json.dumps(trace) + "\n",
            encoding="utf-8",
        )
        (report_dir / "anomalies.jsonl").write_text("", encoding="utf-8")
        _write_json(
            report_dir / "value_report.json",
            {"finding_count": 0, "by_kind": {}, "findings": []},
        )
        _write_json(
            report_dir / "route_report.json",
            {"finding_count": 0, "by_kind": {}, "axes": [], "groups": []},
        )
    else:
        row = {
            "week": 1,
            "available_actions": ["study_library"],
            "chosen_actions": ["study_library"],
            "event_choice_id": "",
            "validation": {
                "valid": True,
                "errors": [],
                "repair_count": 0,
                "fallback_used": False,
            },
            "decision": {"risk_awareness": []},
            "week_context": {
                "top_risks": [],
                "event_choices": [],
                "persona_strategy": {"priorities": ["study"]},
                "available_actions": [{"id": "study_library", "tags": ["study"]}],
            },
            "anomalies": [],
        }
        (report_dir / "playthrough.jsonl").write_text(
            json.dumps(row) + "\n",
            encoding="utf-8",
        )
        _write_json(report_dir / "playthrough_agent_report.json", {"llm_calls": []})
        (report_dir / "playthrough_summary.md").write_text(
            f"- final ending: **{ending}**\n",
            encoding="utf-8",
        )
        evaluate_and_write(report_dir)
    _write_json(report_dir / "report_manifest.json", manifest)


def test_load_and_expand_repository_matrix() -> None:
    config = load_matrix_config(MATRIX_CONFIG)

    cells = expand_matrix_cells(config)
    by_kind = {
        kind: [cell for cell in cells if cell.kind == kind]
        for kind in ("simulation", "boundary", "persona")
    }

    assert len(by_kind["simulation"]) == 2 * 7 * 3 * 3
    assert len(by_kind["boundary"]) == 8
    assert len(by_kind["persona"]) == 6
    assert len(cells) == 140
    assert len({cell.cell_id for cell in cells}) == len(cells)
    assert len({cell.run_id for cell in cells}) == len(cells)
    assert len(config.config_hash) == 64
    assert config.boundary.policy == "balanced"


def test_ids_and_command_plan_are_stable_and_complete(tmp_path: Path) -> None:
    config = load_matrix_config(_small_config(tmp_path))

    first = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "out")
    second = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "out")

    assert first.matrix_id == second.matrix_id
    assert first.code_fingerprint == second.code_fingerprint
    assert len(first.code_fingerprint) == 64
    assert [item.cell.cell_id for item in first.cells] == [
        item.cell.cell_id for item in second.cells
    ]
    assert [item.cell.run_id for item in first.cells] == [item.cell.run_id for item in second.cells]
    assert [item.cell.kind for item in first.cells] == ["simulation", "boundary", "persona"]

    simulation, boundary, persona = first.cells
    assert simulation.argv[2] == "all"
    assert "--scenario" in simulation.argv
    assert (
        simulation.report_dir == tmp_path / "out" / "reports" / "balance" / simulation.cell.run_id
    )
    assert simulation.argv[-2:] == ("--report-dir", str(simulation.report_dir))
    assert boundary.argv[2] == "probe"
    assert boundary.argv[-2:] == ("--extreme", "zero_money")
    assert persona.argv[2] == "play"
    assert "--persona" in persona.argv
    assert persona.report_dir == tmp_path / "out" / "reports" / "play" / persona.cell.run_id


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("runs_per_cell",), 0, "positive integer"),
        (("weeks",), True, "positive integer"),
        (("seeds",), [42, 42], "duplicates"),
        (("seeds",), [42, 43], "batches overlap"),
        (("boundary", "runs"), -1, "positive integer"),
        (("play", "outcome_coverage", "designed_failure_is_valid"), "yes", "boolean"),
    ],
)
def test_strict_schema_rejects_invalid_values(
    tmp_path: Path,
    path: tuple[str, ...],
    value: Any,
    message: str,
) -> None:
    payload = yaml.safe_load(MATRIX_CONFIG.read_text(encoding="utf-8"))
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(MatrixConfigError, match=message):
        load_matrix_config(config_path)


@pytest.mark.parametrize("location", ["root", "boundary", "play", "coverage", "compare"])
def test_strict_schema_rejects_unknown_keys(tmp_path: Path, location: str) -> None:
    payload = yaml.safe_load(MATRIX_CONFIG.read_text(encoding="utf-8"))
    targets = {
        "root": payload,
        "boundary": payload["boundary"],
        "play": payload["play"],
        "coverage": payload["play"]["outcome_coverage"],
        "compare": payload["compare"],
    }
    targets[location]["surprise"] = 1
    config_path = tmp_path / f"unknown-{location}.yaml"
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(MatrixConfigError, match="unknown keys: surprise"):
        load_matrix_config(config_path)


def test_dry_run_writes_plan_without_calling_executor_or_cell_manifests(tmp_path: Path) -> None:
    config_path = _small_config(tmp_path)
    output_dir = tmp_path / "matrix-output"

    def should_not_run(_plan: object) -> int:
        raise AssertionError("dry-run invoked executor")

    result = run_matrix_file(
        config_path,
        project_root=ROOT,
        matrix_dir=output_dir,
        dry_run=True,
        jobs=3,
        executor=should_not_run,
    )

    assert result.status == "planned"
    assert result.exit_code == 0
    assert result.summary["total"] == 3
    assert result.summary["planned"] == 3
    assert (output_dir / MATRIX_MANIFEST_FILE).exists()
    assert (output_dir / MATRIX_SUMMARY_FILE).exists()
    assert not list((output_dir / "cells").glob(f"*/{CELL_MANIFEST_FILE}"))
    manifest = _read_json(output_dir / MATRIX_MANIFEST_FILE)
    config = load_matrix_config(config_path)
    assert manifest["compare"]["output_dir"] == config.compare.output_dir
    assert manifest["compare"]["include"] == list(config.compare.include)
    assert manifest["code_fingerprint"] == execution_source_fingerprint(
        ROOT, ROOT / "demo/study-in-germany"
    )


def test_parallel_execution_records_failures_then_resume_only_retries_failed_cell(
    tmp_path: Path,
) -> None:
    config = load_matrix_config(_small_config(tmp_path))
    plan = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "run")
    active = 0
    max_active = 0
    lock = threading.Lock()

    def first_executor(command_plan: object) -> ExecutionOutcome:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        kind = command_plan.cell.kind  # type: ignore[attr-defined]
        if kind == "boundary":
            return ExecutionOutcome(7, stderr="boundary exploded")
        return ExecutionOutcome(0, stdout=f"finished {kind}")

    first = execute_matrix(
        plan,
        jobs=3,
        executor=first_executor,
        verify_evidence=False,
    )

    assert first.status == "failed"
    assert first.exit_code == 1
    assert first.summary["completed"] == 2
    assert first.summary["failed"] == 1
    assert max_active >= 2
    failed = next(cell for cell in first.cells if cell["status"] == "failed")
    assert failed["kind"] == "boundary"
    assert failed["exit_code"] == 7
    assert failed["error"] == "boundary exploded"
    for command_plan in plan.cells:
        cell_manifest = _read_json(command_plan.manifest_path)
        assert cell_manifest["config_hash"] == config.config_hash
        assert cell_manifest["parameters"] == dict(command_plan.cell.parameters)
        assert cell_manifest["started_at"]
        assert cell_manifest["finished_at"]

    retried: list[str] = []

    def retry_executor(command_plan: object) -> int:
        retried.append(command_plan.cell.kind)  # type: ignore[attr-defined]
        return 0

    second = execute_matrix(
        plan,
        jobs=2,
        resume=True,
        executor=retry_executor,
        verify_evidence=False,
    )

    assert retried == ["boundary"]
    assert second.status == "completed"
    assert second.summary["completed"] == 1
    assert second.summary["skipped"] == 2
    assert second.summary["failed"] == 0
    boundary_manifest = _read_json(
        next(item for item in plan.cells if item.cell.kind == "boundary").manifest_path
    )
    assert boundary_manifest["status"] == "completed"
    assert boundary_manifest["attempt"] == 2


def test_resume_retries_all_cells_after_runtime_source_fingerprint_changes(
    tmp_path: Path,
) -> None:
    config = load_matrix_config(_small_config(tmp_path))
    plan = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "fingerprint")
    assert (
        execute_matrix(plan, executor=lambda _item: 0, verify_evidence=False).status == "completed"
    )

    changed_fingerprint = "f" * 64
    changed_plan = replace(
        plan,
        code_fingerprint=changed_fingerprint,
        cells=tuple(replace(item, code_fingerprint=changed_fingerprint) for item in plan.cells),
    )
    rerun: list[str] = []

    def executor(item: Any) -> int:
        rerun.append(item.cell.cell_id)
        return 0

    resumed = execute_matrix(
        changed_plan,
        resume=True,
        executor=executor,
        verify_evidence=False,
    )

    assert resumed.status == "completed"
    assert sorted(rerun) == sorted(item.cell.cell_id for item in plan.cells)
    assert resumed.summary["skipped"] == 0


def test_executor_exception_is_persisted_as_cell_failure(tmp_path: Path) -> None:
    config = load_matrix_config(_small_config(tmp_path))
    plan = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "exceptions")

    def broken(_plan: object) -> int:
        raise RuntimeError("executor unavailable")

    result = execute_matrix(plan, jobs=1, executor=broken)

    assert result.status == "failed"
    assert result.summary["failed"] == 3
    assert all("RuntimeError: executor unavailable" in cell["error"] for cell in result.cells)


def test_resume_retries_completed_cell_when_report_evidence_was_deleted(
    tmp_path: Path,
) -> None:
    config = load_matrix_config(_small_config(tmp_path))
    plan = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "evidence")

    def first_executor(command_plan: Any) -> int:
        _write_cell_evidence(command_plan)
        return 0

    first = execute_matrix(plan, executor=first_executor)
    assert first.status == "completed"
    simulation = next(item for item in plan.cells if item.cell.kind == "simulation")
    (simulation.report_dir / "raw_runs.jsonl").unlink()
    retried: list[str] = []

    def retry_executor(command_plan: Any) -> int:
        retried.append(command_plan.cell.kind)
        _write_cell_evidence(command_plan)
        return 0

    resumed = execute_matrix(plan, resume=True, executor=retry_executor)

    assert resumed.status == "completed"
    assert retried == ["simulation"]
    assert resumed.summary["skipped"] == 2


def test_invalid_persona_ending_fails_matrix(tmp_path: Path) -> None:
    config = load_matrix_config(_small_config(tmp_path))
    plan = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "invalid-ending")

    def executor(command_plan: Any) -> int:
        _write_cell_evidence(
            command_plan,
            ending="unknown" if command_plan.cell.kind == "persona" else "stable_start",
        )
        return 0

    result = execute_matrix(plan, executor=executor)

    assert result.status == "failed"
    persona = next(cell for cell in result.cells if cell["kind"] == "persona")
    assert persona["status"] == "failed"
    assert "invalid ending 'unknown'" in persona["error"]


def test_default_executor_serializes_only_all_and_parallelizes_unique_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _small_config(tmp_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    payload["seeds"] = [42, 44]
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    config = load_matrix_config(config_path)
    plan = build_matrix_plan(config, project_root=ROOT, matrix_dir=tmp_path / "locked")

    total_active = 0
    total_peak = 0
    all_active = 0
    all_peak = 0
    lock = threading.Lock()

    def fake_run(argv: tuple[str, ...], **_kwargs: Any) -> ExecutionOutcome:
        nonlocal total_active, total_peak, all_active, all_peak
        kind = argv[2]
        with lock:
            total_active += 1
            total_peak = max(total_peak, total_active)
            if kind == "all":
                all_active += 1
                all_peak = max(all_peak, all_active)
        time.sleep(0.02)
        with lock:
            total_active -= 1
            if kind == "all":
                all_active -= 1
        return ExecutionOutcome(0)

    monkeypatch.setattr("game_analysis_agent.test_matrix.subprocess.run", fake_run)
    result = execute_matrix(plan, jobs=4, verify_evidence=False)

    assert result.status == "completed"
    assert all_peak == 1
    assert total_peak >= 2
