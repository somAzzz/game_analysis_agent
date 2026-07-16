"""Independent committed-evidence recomputation tests for G2."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from game_analysis_agent.build_week_g2 import (
    G2ReviewError,
    recompute_public_clusters,
    recompute_public_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "examples/build_week_2026/campaign-v1"


def test_committed_public_campaign_recomputes_headline_metrics_and_clusters() -> None:
    metrics = recompute_public_evidence(BUNDLE)
    clusters = recompute_public_clusters(BUNDLE)

    assert metrics["expected_cells"] == 18
    assert metrics["total_weeks"] == 342
    assert metrics["replay_calls"] == 684
    assert metrics["valid_rate"] == 1.0
    assert metrics["fallback_rate"] == 0.0
    assert clusters["cluster_counts"]["cashflow-stress-attractor"] == 18
    assert clusters["cluster_counts"]["provider-fallback"] == 0


def test_public_metric_recomputation_rejects_tampered_week(tmp_path: Path) -> None:
    destination = tmp_path / "bundle"
    shutil.copytree(BUNDLE, destination)
    path = destination / "persona_runs.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["valid"] = False
    lines[0] = json.dumps(row, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(G2ReviewError, match="public metric mismatch"):
        recompute_public_evidence(destination)
