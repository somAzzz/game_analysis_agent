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
from types import SimpleNamespace
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


def test_play_fails_preflight_before_clearing_existing_report(
    run_gameplay_agent, tmp_path
) -> None:
    report_dir = tmp_path / "play"
    report_dir.mkdir()
    existing = report_dir / "playthrough.jsonl"
    existing.write_text("existing evidence\n", encoding="utf-8")
    fake_llm = SimpleNamespace(
        provider="vllm",
        model="missing-model",
        settings=SimpleNamespace(deepseek_configured=lambda: False),
    )

    def fail_preflight() -> None:
        raise run_gameplay_agent.LLMPreflightError("model is not served")

    fake_llm.validate_model_available = fail_preflight
    with patch.object(
        run_gameplay_agent.LocalLLMClient,
        "from_settings",
        return_value=fake_llm,
    ):
        rc = run_gameplay_agent.main(
            ["play", "--report-dir", str(report_dir), "--weeks", "1"]
        )

    assert rc == 5
    assert existing.read_text(encoding="utf-8") == "existing evidence\n"


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

    def run_godot(*_args, **kwargs):  # noqa: ANN002, ANN003
        output = Path(
            next(arg for arg in kwargs["extra_args"] if arg.startswith("--out=")).removeprefix(
                "--out="
            )
        )
        payload = json.loads(
            (ROOT / "tests" / "fixtures" / "contracts" / "trace_v1.json").read_text()
        )
        payload["run_id"] = 0
        output.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return completed

    with (
        patch.object(run_gameplay_agent, "_run_godot", side_effect=run_godot),
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

    def run_godot_impl(*_args, **kwargs):  # noqa: ANN002, ANN003
        output = Path(
            next(arg for arg in kwargs["extra_args"] if arg.startswith("--out=")).removeprefix(
                "--out="
            )
        )
        payload = json.loads(
            (ROOT / "tests" / "fixtures" / "contracts" / "trace_v1.json").read_text()
        )
        payload.update({"policy": "work", "scenario": "low_money_start"})
        output.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return completed

    with (
        patch.object(
            run_gameplay_agent,
            "_run_godot",
            side_effect=run_godot_impl,
        ) as run_godot,
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


def test_sim_honors_isolated_report_directory(run_gameplay_agent, tmp_path) -> None:
    report_dir = tmp_path / "matrix" / "reports" / "balance" / "cell"
    completed = type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    def run_godot(*_args, **kwargs):  # noqa: ANN002, ANN003
        out_arg = next(arg for arg in kwargs["extra_args"] if arg.startswith("--out="))
        output = Path(out_arg.removeprefix("--out="))
        output.parent.mkdir(parents=True, exist_ok=True)
        fixture = ROOT / "tests" / "fixtures" / "contracts" / "trace_v1.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        output.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return completed

    with patch.object(run_gameplay_agent, "_run_godot", side_effect=run_godot):
        rc = run_gameplay_agent.main(
            [
                "sim",
                "--run-id",
                "cell",
                "--runs",
                "1",
                "--report-dir",
                str(report_dir),
            ]
        )

    assert rc == 0
    assert (report_dir / "raw_runs.jsonl").is_file()
    assert not (ROOT / "reports" / "balance" / "cell" / "raw_runs.jsonl").exists()


def test_sim_resolves_relative_report_directory_before_godot(
    run_gameplay_agent, tmp_path, monkeypatch
) -> None:
    completed = type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
    captured_output: list[Path] = []

    def run_godot(*_args, **kwargs):  # noqa: ANN002, ANN003
        out_arg = next(arg for arg in kwargs["extra_args"] if arg.startswith("--out="))
        output = Path(out_arg.removeprefix("--out="))
        captured_output.append(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        fixture = ROOT / "tests" / "fixtures" / "contracts" / "trace_v1.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        output.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return completed

    monkeypatch.chdir(tmp_path)
    with patch.object(run_gameplay_agent, "_run_godot", side_effect=run_godot):
        rc = run_gameplay_agent.main(
            ["sim", "--runs", "1", "--report-dir", "relative-report"]
        )

    expected = (tmp_path / "relative-report" / "raw_runs.jsonl").resolve()
    assert rc == 0
    assert captured_output == [expected]
    assert expected.is_file()


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

    rc = run_gameplay_agent.main(["gates", "--report-dir", str(tmp_path), "--gates", str(gates)])

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

    def run_validator(*_args, **kwargs):  # noqa: ANN002, ANN003
        output = Path(kwargs["extra_args"][0].removeprefix("--out="))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps({"errors": [], "warnings": [], "summary": {}}),
            encoding="utf-8",
        )
        return completed

    with (
        patch.object(
            run_gameplay_agent,
            "_run_godot",
            side_effect=run_validator,
        ) as run_godot,
        patch.object(run_gameplay_agent, "_resolve_user_path", return_value=fake_user_dir),
    ):
        rc = run_gameplay_agent.main(
            ["validate", "--report-dir", str(tmp_path / "out"), "--check", "content"]
        )

    assert rc == 0
    assert run_godot.call_args.kwargs["script"] == "res://scripts/tools/ValidateContent.gd"
    assert (tmp_path / "out" / "content_validation.json").exists()


def test_validate_defaults_to_all_checks(run_gameplay_agent, tmp_path) -> None:
    completed = type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    def run_validator(*_args, **kwargs):  # noqa: ANN002, ANN003
        script = kwargs["script"]
        if script not in {
            "res://scripts/tools/ValidateJsonContent.gd",
            "res://scripts/tools/ValidateEconomyRules.gd",
        }:
            output = Path(kwargs["extra_args"][0].removeprefix("--out="))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps({"errors": [], "warnings": [], "summary": {}}),
                encoding="utf-8",
            )
        return completed

    with (
        patch.object(
            run_gameplay_agent,
            "_ensure_route_validation_inputs",
            return_value=[],
        ),
        patch.object(
            run_gameplay_agent,
            "_ensure_demo_validation_inputs",
            return_value=[],
        ),
        patch.object(
            run_gameplay_agent,
            "_run_godot",
            side_effect=run_validator,
        ) as run_godot,
    ):
        rc = run_gameplay_agent.main(["validate", "--report-dir", str(tmp_path / "validation")])

    assert rc == 0
    scripts = {call.kwargs["script"] for call in run_godot.call_args_list}
    assert scripts == {script for script, _output in run_gameplay_agent.VALIDATOR_SCRIPTS.values()}
    summary = json.loads((tmp_path / "validation" / "validation_summary.json").read_text())
    assert summary["schema_version"] == "validation-summary-v2"
    assert len(summary["checks"]) == 6


def test_validate_fails_when_successful_process_has_no_output(
    run_gameplay_agent,
    tmp_path,
) -> None:
    completed = type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
    with (
        patch.object(run_gameplay_agent, "_run_godot", return_value=completed),
        patch.object(run_gameplay_agent, "_copy_user_file", return_value=None),
    ):
        rc = run_gameplay_agent.main(
            [
                "validate",
                "--report-dir",
                str(tmp_path),
                "--check",
                "content",
            ]
        )

    assert rc == 1
    summary = json.loads((tmp_path / "validation_summary.json").read_text())
    assert summary["passed"] is False
    assert "did not produce content_validation.json" in summary["checks"][0]["output_error"]


def test_all_runs_export_validation_qa_and_gates_in_order(
    run_gameplay_agent,
    tmp_path,
) -> None:
    calls: list[str] = []
    report_dir = tmp_path / "full-run"

    def sim(args) -> int:  # noqa: ANN001
        calls.append("sim")
        args._report_dir = report_dir
        return 0

    def record(name: str):
        def command(_args) -> int:  # noqa: ANN001
            calls.append(name)
            return 0

        return command

    with (
        patch.object(run_gameplay_agent, "cmd_sim", side_effect=sim),
        patch.object(run_gameplay_agent, "cmd_export", side_effect=record("export")),
        patch.object(run_gameplay_agent, "cmd_analyze", side_effect=record("reanalyze")),
        patch.object(run_gameplay_agent, "validate_trace_catalog_consistency"),
        patch.object(run_gameplay_agent, "cmd_validate", side_effect=record("validate")),
        patch.object(run_gameplay_agent, "cmd_qa", side_effect=record("qa")),
        patch.object(run_gameplay_agent, "cmd_gates", side_effect=record("gates")),
    ):
        rc = run_gameplay_agent.main(["all", "--run-id", "full-run"])

    assert rc == 0
    assert calls == ["sim", "export", "reanalyze", "validate", "qa", "gates"]


def test_matrix_cli_dry_run_expands_repository_config(
    run_gameplay_agent,
    tmp_path,
) -> None:
    rc = run_gameplay_agent.main(
        [
            "matrix",
            "--dry-run",
            "--jobs",
            "4",
            "--out",
            str(tmp_path / "matrix"),
        ]
    )

    assert rc == 0
    manifest = json.loads((tmp_path / "matrix" / "matrix_manifest.json").read_text())
    assert manifest["status"] == "planned"
    assert manifest["summary"]["total"] == 140
    first_simulation = next(cell for cell in manifest["cells"] if cell["kind"] == "simulation")
    assert first_simulation["command"][2] == "sim"


def test_interactive_probe_cli_persists_canonical_risk_evidence(
    run_gameplay_agent,
    tmp_path,
) -> None:
    payload = json.loads(
        (ROOT / "tests" / "fixtures" / "contracts" / "interactive_probe_v1.json").read_text(
            encoding="utf-8"
        )
    )
    report_dir = tmp_path / "interactive"

    with patch(
        "game_analysis_agent.game_tools._run_one_step",
        return_value=payload,
    ):
        rc = run_gameplay_agent.main(
            [
                "interactive-probe",
                "--run-id",
                "probe-test",
                "--report-dir",
                str(report_dir),
            ]
        )

    assert rc == 0
    written = json.loads((report_dir / "interactive_probe.json").read_text())
    assert written["risk_guidance"]["source"] == "game_risk_evaluator"
    manifest = json.loads((report_dir / "report_manifest.json").read_text())
    assert manifest["run_id"] == "probe-test"
    assert manifest["summary"]["risk_source"] == "game_risk_evaluator"


def test_interactive_probe_cli_rejects_missing_risk_and_removes_stale_output(
    run_gameplay_agent,
    tmp_path,
) -> None:
    payload = json.loads(
        (ROOT / "tests" / "fixtures" / "contracts" / "interactive_probe_v1.json").read_text(
            encoding="utf-8"
        )
    )
    payload.pop("risk_guidance")
    report_dir = tmp_path / "interactive"
    report_dir.mkdir()
    stale = report_dir / "interactive_probe.json"
    stale.write_text('{"stale": true}', encoding="utf-8")

    with patch(
        "game_analysis_agent.game_tools._run_one_step",
        return_value=payload,
    ):
        rc = run_gameplay_agent.main(["interactive-probe", "--report-dir", str(report_dir)])

    assert rc == 8
    assert not stale.exists()


def test_require_fresh_output_rejects_unchanged_artifact(
    run_gameplay_agent,
    tmp_path,
) -> None:
    output = tmp_path / "stale.jsonl"
    output.write_text("{}\n", encoding="utf-8")
    signature = run_gameplay_agent._artifact_signature(output)
    completed = type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    settings = SimpleNamespace(game_project_path=tmp_path)

    with (
        patch.object(run_gameplay_agent, "_find_godot_output", return_value=output),
        pytest.raises(RuntimeError, match="stale artifact unchanged"),
    ):
        run_gameplay_agent._require_fresh_output(
            settings,
            "stale.jsonl",
            completed,
            previous_signature=signature,
        )
