"""Tier 1 Replay worker and root entrypoint tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.judge_replay import run

ROOT = Path(__file__).resolve().parents[1]


def test_replay_worker_revalidates_fixture_personas_and_rejection() -> None:
    result = run(ROOT)

    assert result["status"] == "passed"
    assert [item["id"] for item in result["checks"]] == [
        "bundle_integrity",
        "exact_replay",
        "full_fixture",
        "persona_and_determinism",
        "designed_failure_and_rejection",
    ]


def test_root_judge_replay_emits_typed_result_without_writing() -> None:
    completed = subprocess.run(
        [
            str(ROOT / "judge"),
            "--mode",
            "replay",
            "--offline",
            "--json",
            "--output-dir",
            "-",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert payload["status"] == "passed"
    assert payload["stage"] == "replay"
    assert len(payload["checks"]) == 5
    assert not (ROOT / "judge-result.json").exists()
