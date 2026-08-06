"""Unit tests for fail-closed G0 review helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent.build_week_g0 import (
    G0ReviewError,
    _baseline_hash_evidence,
    _privacy_evidence,
)


def test_baseline_hash_evidence_rejects_mutation(tmp_path: Path) -> None:
    artifact = tmp_path / "raw.jsonl"
    artifact.write_text("first\n", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (tmp_path / "baseline_review.json").write_text(
        json.dumps({"artifacts": [{"path": "raw.jsonl", "sha256": digest}]}),
        encoding="utf-8",
    )
    config = {"canonical_artifacts": ["raw.jsonl"]}
    assert _baseline_hash_evidence(tmp_path, config)["artifact_count"] == 1

    artifact.write_text("changed\n", encoding="utf-8")
    with pytest.raises(G0ReviewError, match="hash mismatch"):
        _baseline_hash_evidence(tmp_path, config)


def test_privacy_evidence_rejects_absolute_user_path(tmp_path: Path) -> None:
    (tmp_path / "baseline_review.json").write_text(
        '{"path": "/Users/private/project"}', encoding="utf-8"
    )

    with pytest.raises(G0ReviewError, match="absolute user path"):
        _privacy_evidence(tmp_path)


def test_privacy_evidence_accepts_portable_tokens(tmp_path: Path) -> None:
    (tmp_path / "baseline_review.json").write_text(
        '{"path": "<project>/reports"}', encoding="utf-8"
    )

    evidence = _privacy_evidence(tmp_path)

    assert evidence["absolute_user_paths"] == 0
