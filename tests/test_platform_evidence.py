"""P4 raw platform evidence validation tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import tools.record_platform_evidence as platform_evidence
from game_analysis_agent.build_week_game_pin import prepare_embedded_game_runtime
from game_analysis_agent.report_manifest import (
    _game_provenance,
    execution_source_fingerprint,
    runtime_source_fingerprint,
)
from tools.record_platform_evidence import PlatformEvidenceError, build_evidence

ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()


def _embedded_provenance(runtime: Path, *, system: str) -> dict:
    return {
        "agent_repository": {"commit": _revision(), "dirty": False},
        "runtime": {
            "platform": system,
            "godot": {"version": "4.4.stable.official"},
        },
        "game_repository": _game_provenance(runtime),
        "fingerprints": {
            "runtime_source_sha256": runtime_source_fingerprint(ROOT),
            "game_source_sha256": platform_evidence.game_source_fingerprint(runtime),
            "execution_source_sha256": execution_source_fingerprint(ROOT, runtime),
        },
    }


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
    runtime = tmp_path / "game-runtime"
    prepare_embedded_game_runtime(ROOT, runtime)
    manifest = {
        "provenance": _embedded_provenance(runtime, system="Linux-6.8-x86_64")
    }
    _write(simulation / "report_manifest.json", manifest)
    (simulation / "raw_runs.jsonl").write_text('{"week": 1}\n', encoding="utf-8")
    _write(interactive / "report_manifest.json", {"kind": "interactive"})
    _write(
        tmp_path / "expected-demo-findings.json",
        {
            "schema_version": "build-week-expected-demo-findings-result-v1",
            "status": "passed",
            "game_commit": _embedded_provenance(runtime, system="Linux")[
                "game_repository"
            ]["commit"],
        },
    )

    evidence = build_evidence("linux-godot", tmp_path)

    assert evidence["status"] == "passed"
    assert evidence["toolchain"]["godot"] == "4.4.stable.official"
    assert len(evidence["artifact_digests"]) == 3


def test_linux_godot_rejects_forged_game_pin(tmp_path: Path) -> None:
    simulation = tmp_path / "ci-smoke"
    simulation.mkdir()
    runtime = tmp_path / "game-runtime"
    prepare_embedded_game_runtime(ROOT, runtime)
    provenance = _embedded_provenance(runtime, system="Linux-6.8-x86_64")
    provenance["game_repository"]["commit"] = "a" * 40
    _write(simulation / "report_manifest.json", {"provenance": provenance})
    (simulation / "raw_runs.jsonl").write_text('{}\n', encoding="utf-8")
    _write(
        tmp_path / "expected-demo-findings.json",
        {
            "schema_version": "build-week-expected-demo-findings-result-v1",
            "status": "passed",
            "game_commit": "a" * 40,
        },
    )

    with pytest.raises(PlatformEvidenceError, match="commit differs from pin"):
        build_evidence("linux-godot", tmp_path)


def test_macos_evidence_rejects_stale_doctor_outputs(tmp_path: Path) -> None:
    doctor = {
        "status": "ready",
        "platform": {"system": "Darwin", "machine": "arm64"},
        "source": {"revision": "0" * 40, "dirty": False},
    }
    for name in ("doctor-inspect.json", "doctor-dashboard-native.json", "doctor-real-game.json"):
        _write(tmp_path / name, doctor)
    for name in ("judge-inspect.json", "judge-replay.json"):
        _write(tmp_path / name, {"status": "passed"})
    _write(tmp_path / "provider-status.json", {"providers": {"replay": {"status": "available"}}})
    _write(tmp_path / "experiment.json", {"status": "passed", "decision": "rejected"})
    (tmp_path / "root.html").write_text('<div id="root"></div>', encoding="utf-8")
    godot = tmp_path / "fresh-godot"
    godot.mkdir()
    _write(godot / "report_manifest.json", {"provenance": {}})
    (godot / "raw_runs.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(PlatformEvidenceError, match="revision differs"):
        build_evidence("macos", tmp_path)


def test_live_openai_requires_completed_calls_and_rejects_secret(tmp_path: Path) -> None:
    result = {
        "status": "completed",
        "mode": "live",
        "result": {
            "provider": "openai",
            "mode": "live",
            "model": "gpt-5.6-luna",
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


def test_live_openai_rejects_wrong_model_family(tmp_path: Path) -> None:
    _write(
        tmp_path / "live-openai-campaign.json",
        {
            "status": "completed",
            "mode": "live",
            "result": {
                "provider": "openai",
                "mode": "live",
                "model": "gpt-test",
                "provider_evidence": {
                    "call_count": 1,
                    "response_ids": ["resp_1"],
                    "outputs_recorded": False,
                },
            },
        },
    )

    with pytest.raises(PlatformEvidenceError, match="GPT-5.6"):
        build_evidence("live-openai", tmp_path)


def test_review_update_marks_old_platform_rows_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    review_dir = project / "docs/reviews/openai_build_week_2026"
    evidence_dir = review_dir / "platform-evidence"
    evidence_dir.mkdir(parents=True)
    source_review = json.loads(
        (ROOT / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json").read_text(
            encoding="utf-8"
        )
    )
    (review_dir / "P4-platform-delivery.review.json").write_text(
        json.dumps(source_review), encoding="utf-8"
    )
    probe = project / "scripts/tools/RunInteractiveProbe.gd"
    probe.parent.mkdir(parents=True)
    probe.write_text("extends SceneTree\n", encoding="utf-8")
    evidence_path = evidence_dir / "macos-native.json"
    evidence_path.write_text("{}\n", encoding="utf-8")
    contract = platform_evidence.platform_contract_fingerprint(project)
    evidence = {
        "mode": "macos",
        "source_revision": "a" * 40,
        "source_contract_sha256": contract,
    }
    monkeypatch.setattr(platform_evidence, "ROOT", project)
    monkeypatch.setattr(platform_evidence, "_git_revision", lambda: "a" * 40)

    platform_evidence.update_review(evidence_path, evidence)

    updated = json.loads(
        (review_dir / "P4-platform-delivery.review.json").read_text(encoding="utf-8")
    )
    rows = {item["id"]: item for item in updated["checks"]}
    assert rows["macos_system_python_inspect"]["status"] == "passed"
    assert rows["linux_amd64_native_and_container"]["status"] == "stale"
    assert rows["linux_arm64_container"]["status"] == "stale"
    assert "STUDY_IN_GERMANY_TOKEN" not in rows["linux_pinned_real_godot"]["remediation"]
    assert updated["status"] == "partial"


def test_review_update_refuses_stale_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    review_dir = project / "docs/reviews/openai_build_week_2026"
    review_dir.mkdir(parents=True)
    source = ROOT / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json"
    (review_dir / source.name).write_bytes(source.read_bytes())
    evidence_path = review_dir / "platform-evidence/stale.json"
    evidence_path.parent.mkdir()
    evidence_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(platform_evidence, "ROOT", project)

    with pytest.raises(PlatformEvidenceError, match="stale delivery contract"):
        platform_evidence.update_review(
            evidence_path,
            {
                "mode": "macos",
                "source_revision": "a" * 40,
                "source_contract_sha256": "0" * 64,
            },
        )
