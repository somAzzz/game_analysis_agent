"""Restricted-environment and failure-injection checks for Judge Mode."""

from __future__ import annotations

import json
import os
import runpy
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "judge"
BASE = [
    str(JUDGE),
    "--mode",
    "replay",
    "--offline",
    "--json",
    "--output-dir",
    "-",
    "--stdout-only",
]


def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(result.stdout)


def _restricted_environment(tmp_path: Path) -> dict[str, str]:
    return {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        "HTTP_PROXY": "http://127.0.0.1:1",
        "HTTPS_PROXY": "http://127.0.0.1:1",
        "DOCKER_HOST": "unix:///missing/docker.sock",
        "CUDA_VISIBLE_DEVICES": "",
        "GAME_PROJECT_PATH": "/missing/sibling-game",
    }


def _process_gone(pid: int) -> bool:
    result = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], text=True, capture_output=True
    )
    return result.returncode != 0 or not result.stdout.strip() or "Z" in result.stdout


def test_inspect_and_replay_pass_without_network_docker_gpu_key_or_game(
    tmp_path: Path,
) -> None:
    environment = _restricted_environment(tmp_path)
    inspect = subprocess.run(
        [
            str(JUDGE),
            "--mode",
            "inspect",
            "--offline",
            "--json",
            "--output-dir",
            "-",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    replay = subprocess.run(
        BASE,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=120,
    )

    assert "OPENAI_API_KEY" not in environment
    assert _payload(inspect)["status"] == "passed"
    assert _payload(replay)["status"] == "passed"
    assert not (ROOT / "judge-result.json").exists()


def test_missing_uv_is_typed_dependency_failure() -> None:
    result = subprocess.run(
        [sys.executable, "-I", str(JUDGE), *BASE[1:]],
        cwd=ROOT,
        env={"PATH": ""},
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert _payload(result)["error_code"] == "dependency_missing"


def test_zero_timeout_fails_before_worker_start() -> None:
    result = subprocess.run(
        [*BASE, "--timeout-seconds", "0"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert _payload(result)["error_code"] == "replay_timeout"


def test_provider_failure_is_not_hidden_by_replay_fallback() -> None:
    result = subprocess.run(
        [
            *BASE,
            "--replay-worker",
            "tests/fixtures/judge_provider_failure_worker.py",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert _payload(result)["error_code"] == "provider_failed_mid_run"


def test_timeout_kills_worker_and_descendant_process_group(tmp_path: Path) -> None:
    pid_file = tmp_path / "pids"
    environment = os.environ.copy()
    environment["JUDGE_TEST_PID_FILE"] = str(pid_file)
    result = subprocess.run(
        [
            *BASE,
            "--replay-worker",
            "tests/fixtures/judge_hanging_worker.py",
            "--timeout-seconds",
            "1",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert _payload(result)["error_code"] == "replay_timeout"
    assert pid_file.is_file()
    assert all(_process_gone(int(pid)) for pid in pid_file.read_text().splitlines())


def test_sigterm_kills_worker_group_and_returns_typed_failure(tmp_path: Path) -> None:
    pid_file = tmp_path / "pids"
    environment = os.environ.copy()
    environment["JUDGE_TEST_PID_FILE"] = str(pid_file)
    process = subprocess.Popen(
        [
            *BASE,
            "--replay-worker",
            "tests/fixtures/judge_hanging_worker.py",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 8
    while not pid_file.is_file() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert pid_file.is_file()
    os.kill(process.pid, signal.SIGTERM)
    stdout, stderr = process.communicate(timeout=8)
    payload = json.loads(stdout)

    assert process.returncode == 1
    assert stderr == ""
    assert payload["error_code"] == "replay_interrupted"
    assert all(_process_gone(int(pid)) for pid in pid_file.read_text().splitlines())


def test_unsafe_external_worker_path_is_rejected() -> None:
    result = subprocess.run(
        [*BASE, "--replay-worker", "/tmp/arbitrary.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert _payload(result)["error_code"] == "replay_worker_unsafe"


def test_unsupported_python_returns_json_not_false_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    namespace = runpy.run_path(str(JUDGE), run_name="judge_test_module")
    monkeypatch.setattr(sys, "version_info", (3, 8, 20))

    exit_code = namespace["main"]([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "unsupported"
    assert payload["error_code"] == "python_unsupported"
