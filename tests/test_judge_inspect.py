"""Black-box tests for the dependency-free Tier 0 judge."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "judge"


def _fixture(tmp_path: Path, *, expected: int = 18) -> Path:
    artifact = tmp_path / "evidence.json"
    artifact.write_text(
        json.dumps({"schema_version": "evidence-v1", "metrics": {"cells": 18}}) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "judge-manifest-v1",
        "artifacts": [
            {
                "path": "evidence.json",
                "role": "campaign",
                "schema_version": "evidence-v1",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "bytes": artifact.stat().st_size,
            }
        ],
        "claims": [
            {
                "id": "campaign_cells",
                "statement": "The campaign contains 18 cells.",
                "evidence": [
                    {"path": "evidence.json", "json_pointer": "/metrics/cells", "equals": expected}
                ],
            }
        ],
        "limitations": ["Committed evidence only."],
    }
    path = tmp_path / "judge-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _run(manifest: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    environment = {"PATH": os.environ.get("PATH", "")}
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(JUDGE),
            "--mode",
            "inspect",
            "--offline",
            "--json",
            "--manifest",
            str(manifest),
            "--output-dir",
            "-",
            *extra,
        ],
        cwd=manifest.parent,
        env=environment,
        text=True,
        capture_output=True,
    )


def test_inspect_passes_without_project_packages_or_writes(tmp_path: Path) -> None:
    result = _run(_fixture(tmp_path))
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload["status"] == "passed"
    assert payload["stage"] == "inspect"
    assert len(payload["artifacts"]) == 1
    assert not (tmp_path / "judge-result.json").exists()


def test_inspect_fails_closed_on_artifact_tampering(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    (tmp_path / "evidence.json").write_text("{}\n", encoding="utf-8")

    result = _run(manifest, "--stdout-only")
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert result.stderr == ""
    assert payload["status"] == "failed"
    assert payload["error_code"] == "artifact_integrity_failed"


def test_inspect_fails_closed_on_missing_artifact(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    (tmp_path / "evidence.json").unlink()

    result = _run(manifest, "--stdout-only")
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["error_code"] == "artifact_missing"


def test_inspect_fails_when_public_claim_does_not_match_evidence(tmp_path: Path) -> None:
    result = _run(_fixture(tmp_path, expected=12))
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["error_code"] == "claim_value_mismatch"
    assert payload["remediation"]


def test_inspect_rejects_parent_path_escape(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0]["path"] = "../evidence.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    result = _run(manifest)
    response = json.loads(result.stdout)

    assert result.returncode == 1
    assert response["error_code"] == "path_unsafe"


def test_committed_judge_manifest_passes_dependency_free_inspect() -> None:
    result = _run(ROOT / "judge-manifest.json")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["status"] == "passed"
    assert len(payload["artifacts"]) == 22
    assert payload["checks"][2]["detail"] == (
        "6 public claims resolved to exact JSON values"
    )
