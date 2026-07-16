"""Public repair bundle hash and tamper tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from game_analysis_agent.repair_bundle import (
    RepairBundleError,
    verify_public_repair_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "examples/build_week_2026/experiment-v1"


def test_committed_rejected_experiment_is_complete_and_hash_verified() -> None:
    if not BUNDLE.is_dir():
        pytest.skip("public experiment bundle is generated after this capability commit")
    gate = verify_public_repair_bundle(BUNDLE)

    assert gate.status == "passed"
    assert gate.decision == "rejected"
    assert len(gate.artifacts) == 8


def test_repair_bundle_detects_tampered_artifact(tmp_path: Path) -> None:
    if not BUNDLE.is_dir():
        pytest.skip("public experiment bundle is generated after this capability commit")
    target = tmp_path / "bundle"
    shutil.copytree(BUNDLE, target)
    comparison = target / "comparison.json"
    payload = json.loads(comparison.read_text())
    payload["fixed_relative_reduction"] = 1
    comparison.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RepairBundleError, match="hash mismatch"):
        verify_public_repair_bundle(target)
