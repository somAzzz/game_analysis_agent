"""Tests for the secret-safe delivery-mode doctor."""

from __future__ import annotations

import json

from tools.judge_doctor import diagnose


def test_inspect_requires_only_supported_host_and_python(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("tools.judge_doctor.platform.system", lambda: "Linux")
    monkeypatch.setattr("tools.judge_doctor.platform.machine", lambda: "x86_64")
    monkeypatch.setattr("tools.judge_doctor._git_state", lambda: {"revision": "abc", "dirty": False})

    result = diagnose("inspect", environment={})

    assert result["status"] == "ready"
    assert {item["id"] for item in result["checks"]} == {"supported_host", "python"}


def test_live_mode_is_fail_closed_and_never_serializes_secrets(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("tools.judge_doctor.platform.system", lambda: "Darwin")
    monkeypatch.setattr("tools.judge_doctor.platform.machine", lambda: "arm64")
    monkeypatch.setattr("tools.judge_doctor._git_state", lambda: {"revision": "abc", "dirty": False})
    monkeypatch.setattr("tools.judge_doctor._probe", lambda *_args, **_kwargs: {"status": "unavailable", "version": ""})

    result = diagnose("live-openai", environment={"OPENAI_API_KEY": "sk-do-not-print"})
    encoded = json.dumps(result)

    assert result["status"] == "unsupported"
    assert "sk-do-not-print" not in encoded
    assert result["capabilities"]["openai_key_configured"] is True
    assert {item["id"] for item in result["checks"] if item["status"] == "failed"} >= {
        "uv", "game_project", "godot"
    }


def test_dashboard_reports_docker_remediation_without_making_node_required(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("tools.judge_doctor.platform.system", lambda: "Linux")
    monkeypatch.setattr("tools.judge_doctor.platform.machine", lambda: "aarch64")
    monkeypatch.setattr("tools.judge_doctor._git_state", lambda: {"revision": "abc", "dirty": False})
    monkeypatch.setattr(
        "tools.judge_doctor._probe",
        lambda command, **_kwargs: {
            "status": "available" if command[0] == "uv" else "unavailable",
            "version": "uv 0.11.23" if command[0] == "uv" else "",
        },
    )

    result = diagnose("dashboard-container", environment={})
    by_id = {item["id"]: item for item in result["checks"]}

    assert result["status"] == "unsupported"
    assert by_id["docker"]["status"] == "failed"
    assert by_id["node"]["status"] == "warning"


def test_real_game_rejects_available_but_unpinned_godot(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    (tmp_path / "project.godot").write_text("[application]\n", encoding="utf-8")
    monkeypatch.setattr("tools.judge_doctor.platform.system", lambda: "Darwin")
    monkeypatch.setattr("tools.judge_doctor.platform.machine", lambda: "arm64")
    monkeypatch.setattr("tools.judge_doctor._git_state", lambda: {"revision": "abc", "dirty": False})
    monkeypatch.setattr(
        "tools.judge_doctor._probe",
        lambda command, **_kwargs: {
            "status": "available",
            "version": "4.7.stable" if "--version" in command and command[0] == "godot4" else "available",
        },
    )

    result = diagnose("real-game", environment={"GAME_PROJECT_PATH": str(tmp_path), "GODOT_BIN": "godot4"})
    by_id = {item["id"]: item for item in result["checks"]}

    assert result["status"] == "unsupported"
    assert by_id["godot"]["status"] == "failed"
    assert result["capabilities"]["godot"]["version_matches_pin"] is False
