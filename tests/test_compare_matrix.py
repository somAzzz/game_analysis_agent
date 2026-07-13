from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from game_analysis_agent.agent_eval import evaluate_and_write
from tools import run_gameplay_agent
from tools.compare_matrix import (
    MATRIX_COMPARE_SUMMARY_FILE,
    MatrixCompareError,
    compare_matrix_runs,
)

CONFIG_HASH = "a" * 64
ROOT = Path(__file__).resolve().parents[1]
INCLUDES = [
    "ending_distribution.csv",
    "action_pick_rates.csv",
    "weekly_stats.csv",
    "anomalies.jsonl",
    "value_report.json",
    "route_report.json",
    "coverage_report.json",
]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fingerprint(revision: str) -> str:
    return ("c" if revision == "after" else "b") * 64


def _write_report_manifest(cell: dict[str, Any], *, revision: str) -> None:
    _write_json(
        Path(cell["report_dir"]) / "report_manifest.json",
        {
            "schema_version": "trace-manifest-v2",
            "run_id": cell["run_id"],
            "status": "completed",
            "provenance": {"fingerprints": {"execution_source_sha256": _fingerprint(revision)}},
        },
    )


def _write_analysis_reports(report_dir: Path) -> None:
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


def _contract_trace(
    *, boundary: bool = False
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fixture_root = ROOT / "tests" / "fixtures" / "contracts"
    trace = json.loads((fixture_root / "trace_v1.json").read_text(encoding="utf-8"))
    event_graph = json.loads((fixture_root / "event_graph_v1.json").read_text(encoding="utf-8"))
    action_catalog = json.loads(
        (fixture_root / "action_catalog_v1.json").read_text(encoding="utf-8")
    )
    action_id = action_catalog["actions"][0]["id"]
    event = event_graph["events"][0]
    choice = event["choices"][0]
    choice_id = f"{event['id']}.choice_01_{choice['text'].lower().replace(' ', '_')}"
    trace["weekly_log"][0].update(
        {
            "available_action_ids": [action_id],
            "selected_action_ids": [action_id],
            "triggered_event_id": event["id"],
            "event_choice_id": choice_id,
        }
    )
    trace["action_sequence"] = [{"week": 1, "actions": [action_id], "event_choice": choice_id}]
    if boundary:
        trace["extreme"] = "zero_money"
    return trace, event_graph, action_catalog


def _write_simulation_artifacts(report_dir: Path, *, after: bool) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    trace, event_graph, action_catalog = _contract_trace()
    report_dir.joinpath("raw_runs.jsonl").write_text(json.dumps(trace) + "\n", encoding="utf-8")
    _write_json(report_dir / "event_graph.json", event_graph)
    _write_json(report_dir / "action_catalog.json", action_catalog)
    _write_json(
        report_dir / "summary.json",
        {"total_runs": 1, "policies": {"balanced": 1}, "top_events": {}},
    )
    rate = "0.6" if after else "0.4"
    report_dir.joinpath("ending_distribution.csv").write_text(
        "policy,difficulty,scenario,ending_id,count,sample_size,rate,ci95_low,ci95_high\n"
        f"balanced,normal,default_first_semester,success,1,1,{rate},0.1,0.9\n",
        encoding="utf-8",
    )
    report_dir.joinpath("action_pick_rates.csv").write_text(
        "policy,action_id,count,rate_per_run\nbalanced,study_library,1,1.0\n",
        encoding="utf-8",
    )
    report_dir.joinpath("weekly_stats.csv").write_text(
        "policy,week,metric,mean,median,p10,p90,min,max\n"
        "balanced,1,money,1000,1000,1000,1000,1000,1000\n",
        encoding="utf-8",
    )
    report_dir.joinpath("anomalies.jsonl").write_text(
        '{"kind":"ending_conflict"}\n' if after else "",
        encoding="utf-8",
    )
    _write_analysis_reports(report_dir)
    _write_json(
        report_dir / "coverage_report.json",
        {
            "schema_version": "coverage-v2",
            "total_runs": 1,
            "event_coverage": {"catalog_available": True},
            "action_coverage": {"catalog_available": True},
            "data_quality": {"catalog_errors": []},
            "after": after,
        },
    )


def _write_boundary_artifacts(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    trace, _event_graph, _action_catalog = _contract_trace(boundary=True)
    report_dir.joinpath("boundary_runs.jsonl").write_text(
        json.dumps(trace) + "\n", encoding="utf-8"
    )
    report_dir.joinpath("anomalies.jsonl").write_text("", encoding="utf-8")
    _write_analysis_reports(report_dir)


def _write_persona_artifacts(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
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
    report_dir.joinpath("playthrough.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    _write_json(report_dir / "playthrough_agent_report.json", {"llm_calls": []})
    report_dir.joinpath("playthrough_summary.md").write_text(
        "- final ending: **stable_start**\n", encoding="utf-8"
    )
    evaluate_and_write(report_dir)


def _matrix_cell(
    root: Path,
    *,
    revision: str,
    kind: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    cell_id = f"{kind}-cell"
    run_id = f"demo-{cell_id}"
    report_dir = root / revision / "reports" / kind
    report_dir.mkdir(parents=True, exist_ok=True)
    command = ["python", "tools/run_gameplay_agent.py", kind]
    cwd = str(root / revision)
    cell_manifest = root / revision / "cells" / cell_id / "cell_manifest.json"
    _write_json(
        cell_manifest,
        {
            "schema_version": "test-matrix-v1",
            "matrix_id": "matrix-demo",
            "config_hash": CONFIG_HASH,
            "code_fingerprint": _fingerprint(revision),
            "cell_id": cell_id,
            "run_id": run_id,
            "kind": kind,
            "parameters": parameters,
            "command": command,
            "cwd": cwd,
            "report_dir": str(report_dir),
            "status": "completed",
            "exit_code": 0,
        },
    )
    return {
        "cell_id": cell_id,
        "run_id": run_id,
        "kind": kind,
        "parameters": parameters,
        "report_dir": str(report_dir),
        "cell_manifest": str(cell_manifest),
        "command": command,
        "cwd": cwd,
        "status": "completed",
        "exit_code": 0,
    }


def _write_matrix(root: Path, revision: str, *, status: str = "completed") -> Path:
    cells = [
        _matrix_cell(
            root,
            revision=revision,
            kind="simulation",
            parameters={
                "runs": 200,
                "weeks": 20,
                "difficulty": "normal",
                "policy": "balanced",
                "scenario": "default_first_semester",
                "seed": 42,
            },
        ),
        _matrix_cell(
            root,
            revision=revision,
            kind="boundary",
            parameters={
                "runs": 30,
                "weeks": 20,
                "policy": "balanced",
                "extreme": "zero_money",
                "seed": 42,
            },
        ),
        _matrix_cell(
            root,
            revision=revision,
            kind="persona",
            parameters={
                "weeks": 20,
                "persona": "newbie",
                "difficulty": "realistic",
                "scenario": "default_first_semester",
                "seed": 42,
            },
        ),
    ]
    _write_simulation_artifacts(
        Path(cells[0]["report_dir"]),
        after=revision == "after",
    )
    _write_boundary_artifacts(Path(cells[1]["report_dir"]))
    _write_persona_artifacts(Path(cells[2]["report_dir"]))
    for cell in cells:
        _write_report_manifest(cell, revision=revision)
    manifest_path = root / revision / "matrix_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "test-matrix-v1",
            "matrix_id": "matrix-demo",
            "config_version": "demo-v02",
            "config_hash": CONFIG_HASH,
            "code_fingerprint": _fingerprint(revision),
            "status": status,
            "dry_run": False,
            "compare": {
                "output_dir": "reports/compare",
                "include": INCLUDES,
            },
            "cells": cells,
        },
    )
    return manifest_path


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_compare_matrix_pairs_fixed_seed_cells_and_writes_diffs(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    output = tmp_path / "comparison"

    result = compare_matrix_runs(before.parent, after, output_dir=output)

    assert result.exit_code == 0
    assert result.summary_path == output / MATRIX_COMPARE_SUMMARY_FILE
    summary = _read(result.summary_path)
    assert summary["schema_version"] == "matrix-compare-v1"
    assert summary["status"] == "completed"
    assert summary["total_cells"] == 3
    assert summary["comparable_cells"] == 1
    assert summary["paired_seeds"] == [42]
    assert summary["before_code_fingerprint"] == "b" * 64
    assert summary["after_code_fingerprint"] == "c" * 64
    assert summary["changed_artifacts"] == 3
    assert summary["unchanged_artifacts"] == 4
    simulation = next(row for row in summary["cells"] if row["kind"] == "simulation")
    assert simulation["parameters"]["seed"] == 42
    assert Path(simulation["diff_file"]).is_file()
    diff = _read(Path(simulation["diff_file"]))
    assert diff["endings"]["rows"][0]["delta"] == pytest.approx(0.2)


def test_compare_matrix_rejects_seed_or_parameter_drift(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    payload = _read(after)
    simulation = next(cell for cell in payload["cells"] if cell["kind"] == "simulation")
    simulation["parameters"]["seed"] = 43
    _write_json(after, payload)

    with pytest.raises(MatrixCompareError, match="parameters mismatch"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_rejects_missing_required_artifact(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    missing = (
        Path(
            next(cell for cell in _read(after)["cells"] if cell["kind"] == "simulation")[
                "report_dir"
            ]
        )
        / "coverage_report.json"
    )
    missing.unlink()

    with pytest.raises(MatrixCompareError, match="missing after artifact"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_rejects_reused_report_directory(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    before_payload = _read(before)
    after_payload = _read(after)
    before_sim = next(cell for cell in before_payload["cells"] if cell["kind"] == "simulation")
    after_sim = next(cell for cell in after_payload["cells"] if cell["kind"] == "simulation")
    after_sim["report_dir"] = before_sim["report_dir"]
    _write_json(after, after_payload)

    with pytest.raises(MatrixCompareError, match="report_dir mismatch"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_rejects_wrong_csv_schema(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    cell = next(item for item in _read(after)["cells"] if item["kind"] == "simulation")
    Path(cell["report_dir"], "ending_distribution.csv").write_text(
        "wrong_header\n", encoding="utf-8"
    )

    with pytest.raises(MatrixCompareError, match="missing required columns"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_rejects_empty_coverage_object(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    cell = next(item for item in _read(after)["cells"] if item["kind"] == "simulation")
    _write_json(Path(cell["report_dir"]) / "coverage_report.json", {})

    with pytest.raises(MatrixCompareError, match="missing required keys"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_rejects_missing_boundary_evidence(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    cell = next(item for item in _read(after)["cells"] if item["kind"] == "boundary")
    Path(cell["report_dir"], "boundary_runs.jsonl").unlink()

    with pytest.raises(MatrixCompareError, match="missing after artifact"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_recomputes_persona_evaluation(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    cell = next(item for item in _read(after)["cells"] if item["kind"] == "persona")
    eval_path = Path(cell["report_dir"], "agent_eval.json")
    payload = _read(eval_path)
    payload["metrics"]["steps"] = 999
    _write_json(eval_path, payload)

    with pytest.raises(MatrixCompareError, match="metrics do not match"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_rejects_cell_manifest_command_drift(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    cell = next(item for item in _read(after)["cells"] if item["kind"] == "simulation")
    manifest_path = Path(cell["cell_manifest"])
    payload = _read(manifest_path)
    payload["command"] = ["python", "wrong.py"]
    _write_json(manifest_path, payload)

    with pytest.raises(MatrixCompareError, match="command mismatch"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_rejects_unsafe_cell_id(tmp_path: Path) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    for manifest in (before, after):
        payload = _read(manifest)
        payload["cells"][0]["cell_id"] = "../../outside"
        _write_json(manifest, payload)

    with pytest.raises(MatrixCompareError, match="cell_id contains unsafe characters"):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("matrix-status", "completed non-dry-run"),
        ("cell-set", "matrix cell sets differ"),
        ("cell-manifest", "cell_manifest status mismatch"),
    ],
)
def test_compare_matrix_fails_closed_on_incomplete_evidence(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    payload = _read(after)
    if mutation == "matrix-status":
        payload["status"] = "failed"
    elif mutation == "cell-set":
        payload["cells"].pop()
    else:
        cell_manifest = Path(payload["cells"][0]["cell_manifest"])
        cell_payload = _read(cell_manifest)
        cell_payload["status"] = "failed"
        _write_json(cell_manifest, cell_payload)
    _write_json(after, payload)

    with pytest.raises(MatrixCompareError, match=message):
        compare_matrix_runs(before, after, output_dir=tmp_path / "comparison")


def test_compare_matrix_cli_returns_machine_summary_and_nonzero_on_drift(
    tmp_path: Path,
) -> None:
    before = _write_matrix(tmp_path, "before")
    after = _write_matrix(tmp_path, "after")
    output = tmp_path / "cli-output"

    assert (
        run_gameplay_agent.main(
            [
                "compare-matrix",
                "--before",
                str(before),
                "--after",
                str(after),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    assert (output / MATRIX_COMPARE_SUMMARY_FILE).is_file()

    payload = _read(after)
    payload["config_hash"] = "b" * 64
    _write_json(after, payload)
    assert (
        run_gameplay_agent.main(
            [
                "compare-matrix",
                "--before",
                str(before),
                "--after",
                str(after),
                "--out",
                str(output),
            ]
        )
        == 2
    )
