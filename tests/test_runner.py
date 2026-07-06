"""Smoke tests for the orchestration CLI.

We mock the Godot subprocess invocation so the tests run in any
environment. The CLI structure is verified end-to-end (argparse + flow),
but the actual Godot binary is never called.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SRC = ROOT / "src"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def run_gameplay_agent():
    spec = importlib.util.spec_from_file_location(
        "run_gameplay_agent_under_test", TOOLS / "run_gameplay_agent.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sim_help_runs(run_gameplay_agent) -> None:
    """Calling ``--help`` should exit 0 (argparse handles it)."""
    with pytest.raises(SystemExit) as exc:
        run_gameplay_agent.main(["sim", "--help"])
    assert exc.value.code == 0


def test_analyze_rejects_missing_raw_runs(run_gameplay_agent, tmp_path) -> None:
    rc = run_gameplay_agent.main(
        [
            "analyze",
            "--report-dir",
            str(tmp_path),
            "--raw-runs",
            str(tmp_path / "missing.jsonl"),
        ]
    )
    assert rc == 1


def test_sim_runs_full_pipeline_with_mocked_godot(run_gameplay_agent, tmp_path) -> None:
    """``sim`` should drive ``analyze`` even when Godot is mocked."""
    fake_user_dir = tmp_path / "user"
    fake_user_dir.mkdir(parents=True, exist_ok=True)
    (fake_user_dir / "balance_runs.jsonl").write_text(
        json.dumps(
            {
                "run_id": 0,
                "policy": "balanced",
                "seed": 42,
                "final_ending_id": "academic_success",
                "max_weeks": 2,
                "final_week": 2,
                "final_state": {"week": 2, "money": 100},
                "weekly_log": [
                    {
                        "week": 1,
                        "selected_action_ids": ["sleep_recover"],
                        "triggered_event_id": "",
                        "after_state": {"week": 1, "money": 100, "energy": 80, "stress": 10},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    completed = type(
        "Proc",
        (),
        {"returncode": 0, "stdout": "ok", "stderr": ""},
    )()

    with (
        patch.object(run_gameplay_agent, "_run_godot", return_value=completed),
        patch.object(
            run_gameplay_agent,
            "_resolve_user_path",
            return_value=fake_user_dir,
        ),
    ):
        rc = run_gameplay_agent.main(
            ["sim", "--run-id", "test", "--runs", "1", "--policy", "balanced"]
        )
    assert rc == 0
    out = ROOT / "reports" / "balance" / "test" / "raw_runs.jsonl"
    assert out.exists()
    manifest = ROOT / "reports" / "balance" / "test" / "report_manifest.json"
    assert manifest.exists()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["run_id"] == "test"
    assert payload["trace"]["runs"][0]["run_id"] == 0


def test_sim_passes_scenario_and_policy_alias(run_gameplay_agent, tmp_path) -> None:
    fake_user_dir = tmp_path / "user"
    fake_user_dir.mkdir(parents=True, exist_ok=True)
    (fake_user_dir / "balance_runs.jsonl").write_text(
        json.dumps(
            {
                "run_id": 0,
                "policy": "work",
                "scenario": "low_money_start",
                "seed": 42,
                "final_ending_id": "cashflow_collapse",
                "max_weeks": 1,
                "final_state": {"week": 1, "money": -1200},
                "weekly_log": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    completed = type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    with (
        patch.object(run_gameplay_agent, "_run_godot", return_value=completed) as run_godot,
        patch.object(run_gameplay_agent, "_resolve_user_path", return_value=fake_user_dir),
    ):
        rc = run_gameplay_agent.main(
            [
                "sim",
                "--run-id",
                "scenario-test",
                "--runs",
                "1",
                "--policy",
                "money",
                "--scenario",
                "low_money_start",
            ]
        )

    assert rc == 0
    extra_args = run_godot.call_args.kwargs["extra_args"]
    assert "--policy=work" in extra_args
    assert "--scenario=low_money_start" in extra_args


def test_copy_godot_output_accepts_configured_project_name(
    run_gameplay_agent, tmp_path, monkeypatch
) -> None:
    game_project = tmp_path / "study-in-germany"
    game_project.mkdir()
    (game_project / "project.godot").write_text(
        '[application]\nconfig/name="study_in_germany"\n',
        encoding="utf-8",
    )
    user_root = tmp_path / ".local" / "share" / "godot" / "app_userdata"
    output_dir = user_root / "study_in_germany"
    output_dir.mkdir(parents=True)
    (output_dir / "balance_runs.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))

    copied = run_gameplay_agent._copy_godot_output(
        game_project, "balance_runs.jsonl", tmp_path / "reports" / "raw_runs.jsonl"
    )

    assert copied == tmp_path / "reports" / "raw_runs.jsonl"
    assert copied.read_text(encoding="utf-8") == "{}\n"


def test_copy_godot_output_accepts_project_root_res_path(run_gameplay_agent, tmp_path) -> None:
    game_project = tmp_path / "game"
    game_project.mkdir()
    (game_project / "content_validation.json").write_text("{}", encoding="utf-8")

    copied = run_gameplay_agent._copy_godot_output(
        game_project, "content_validation.json", tmp_path / "out" / "content_validation.json"
    )

    assert copied == tmp_path / "out" / "content_validation.json"
    assert copied.read_text(encoding="utf-8") == "{}"
    assert not (game_project / "content_validation.json").exists()


def test_gates_command_returns_failure(run_gameplay_agent, tmp_path) -> None:
    gates = tmp_path / "gates.yaml"
    gates.write_text(
        "critical_fail:\n  crisis_success_ending: 0\nbalance: {}\ndesign: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "anomalies.jsonl").write_text(
        json.dumps({"kind": "crisis_success_ending"}) + "\n",
        encoding="utf-8",
    )

    rc = run_gameplay_agent.main(
        ["gates", "--report-dir", str(tmp_path), "--gates", str(gates)]
    )

    assert rc == 1
    assert (tmp_path / "gate_report.json").exists()


def test_validate_runs_selected_check(run_gameplay_agent, tmp_path) -> None:
    fake_user_dir = tmp_path / "user"
    fake_user_dir.mkdir(parents=True, exist_ok=True)
    (fake_user_dir / "content_validation.json").write_text(
        json.dumps({"errors": [], "warnings": []}),
        encoding="utf-8",
    )
    completed = type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    with (
        patch.object(run_gameplay_agent, "_run_godot", return_value=completed) as run_godot,
        patch.object(run_gameplay_agent, "_resolve_user_path", return_value=fake_user_dir),
    ):
        rc = run_gameplay_agent.main(
            ["validate", "--report-dir", str(tmp_path / "out"), "--check", "content"]
        )

    assert rc == 0
    assert run_godot.call_args.kwargs["script"] == "res://scripts/tools/ValidateContent.gd"
    assert (tmp_path / "out" / "content_validation.json").exists()
