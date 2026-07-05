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