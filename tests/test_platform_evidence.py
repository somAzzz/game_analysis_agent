"""P4 raw platform evidence validation tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools.record_platform_evidence import PlatformEvidenceError, build_evidence

ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()


def test_linux_amd64_evidence_requires_native_clean_and_container_results(tmp_path: Path) -> None:
    doctor = {
        "status": "ready",
        "platform": {"system": "Linux", "machine": "x86_64"},
        "source": {"revision": _revision(), "dirty": False},
    }
    for name in ("doctor-inspect.json", "doctor-replay.json", "doctor-dashboard-native.json"):
        _write(tmp_path / name, doctor)
    for name in ("judge-inspect.json", "judge-replay.json", "container-inspect.json", "container-replay.json"):
        _write(tmp_path / name, {"status": "passed"})
    _write(tmp_path / "provider-status.json", {"providers": {"replay": {"status": "available"}}})
    _write(tmp_path / "docker-image.json", {"Id": "sha256:image"})

    evidence = build_evidence("linux-amd64", tmp_path)

    assert evidence["status"] == "passed"
    assert evidence["platform"]["architecture"] == "amd64"
    assert evidence["checks"][0]["id"] == "linux_amd64_native_and_container"
    assert len(evidence["artifact_digests"]) == 9


def test_linux_amd64_rejects_emulated_or_dirty_runner(tmp_path: Path) -> None:
    doctor = {
        "status": "ready",
        "platform": {"system": "Linux", "machine": "aarch64"},
        "source": {"revision": _revision(), "dirty": True},
    }
    for name in ("doctor-inspect.json", "doctor-replay.json", "doctor-dashboard-native.json"):
        _write(tmp_path / name, doctor)
    for name in (
        "judge-inspect.json",
        "judge-replay.json",
        "container-inspect.json",
        "container-replay.json",
        "provider-status.json",
        "docker-image.json",
    ):
        _write(tmp_path / name, {"status": "passed"})

    with pytest.raises(PlatformEvidenceError, match="not amd64"):
        build_evidence("linux-amd64", tmp_path)


def test_linux_godot_selects_simulation_manifest_when_interactive_report_is_present(
    tmp_path: Path,
) -> None:
    simulation = tmp_path / "balance" / "ci-smoke"
    interactive = tmp_path / "interactive" / "ci-smoke"
    simulation.mkdir(parents=True)
    interactive.mkdir(parents=True)
    manifest = {
        "provenance": {
            "agent_repository": {"commit": _revision(), "dirty": False},
            "runtime": {
                "platform": "Linux-6.8-x86_64",
                "godot": {"version": "4.4.stable.official"},
            },
            "game_repository": {"commit": "a" * 40},
        }
    }
    _write(simulation / "report_manifest.json", manifest)
    (simulation / "raw_runs.jsonl").write_text('{"week": 1}\n', encoding="utf-8")
    _write(interactive / "report_manifest.json", {"kind": "interactive"})

    evidence = build_evidence("linux-godot", tmp_path)

    assert evidence["status"] == "passed"
    assert evidence["toolchain"]["godot"] == "4.4.stable.official"
    assert len(evidence["artifact_digests"]) == 2


def test_live_openai_requires_completed_calls_and_rejects_secret(tmp_path: Path) -> None:
    result = {
        "status": "completed",
        "mode": "live",
        "result": {
            "provider": "openai",
            "mode": "live",
            "model": "gpt-test",
            "provider_evidence": {
                "call_count": 2,
                "response_ids": ["resp_1"],
                "outputs_recorded": False,
            },
        },
    }
    _write(tmp_path / "live-openai-campaign.json", result)

    evidence = build_evidence("live-openai", tmp_path)
    assert evidence["provider"] == "openai"

    result["debug"] = "sk-should-not-be-retained"
    _write(tmp_path / "live-openai-campaign.json", result)
    with pytest.raises(PlatformEvidenceError, match="secret"):
        build_evidence("live-openai", tmp_path)
