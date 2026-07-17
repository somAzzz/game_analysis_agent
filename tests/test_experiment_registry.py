"""Transport-independent Judge experiment discovery tests."""

from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.experiment_registry import (
    ExperimentRegistry,
    ExperimentSummary,
)

ROOT = Path(__file__).resolve().parents[1]


def _local_campaign() -> ExperimentSummary:
    return ExperimentSummary(
        experiment_id="vllm-campaign-test",
        title="Local campaign test",
        source_kind="local_vllm",
        source_label="LOCAL vLLM",
        provider="vllm",
        provider_mode="local",
        model="qwen-local",
        lifecycle_status="campaign_complete",
        campaign_id="vllm-campaign-test",
        campaign={"cells": 6, "weeks": 114},
        campaign_bundle_path="examples/build_week_2026/campaign-v1",
    )


def test_signed_and_runtime_experiments_share_one_index(monkeypatch) -> None:  # noqa: ANN001
    registry = ExperimentRegistry(ROOT)
    local = _local_campaign()
    monkeypatch.setattr(registry, "_runtime_campaigns", lambda: (local,))
    monkeypatch.setattr(registry, "_runtime_repairs", lambda _campaigns: ())

    index = registry.list()

    experiments = index["experiments"]
    assert experiments[0]["source_label"] == "SIGNED REPLAY"
    runtime = next(item for item in experiments if item["experiment_id"] == local.experiment_id)
    assert runtime["source_label"] == "LOCAL vLLM"
    assert runtime["lifecycle_status"] == "campaign_complete"


def test_campaign_only_detail_does_not_borrow_repair_evidence(monkeypatch) -> None:  # noqa: ANN001
    registry = ExperimentRegistry(ROOT)
    local = _local_campaign()
    monkeypatch.setattr(registry, "_summaries", lambda: (local,))

    detail = registry.get(local.experiment_id)

    assert detail["decision"] is None
    assert detail["patch"] is None
    assert detail["cohorts"] == []
    assert detail["human_review"] is None


def test_committed_metadata_path_escape_fails_closed(tmp_path: Path) -> None:
    metadata = tmp_path / "examples/build_week_2026/experiments/escape/metadata.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(
        json.dumps(
            {
                "schema_version": "judge-committed-experiment-v1",
                "experiment_id": "escape",
                "title": "Escape",
                "campaign_bundle_path": "../outside",
                "repair_bundle_path": "../outside",
            }
        ),
        encoding="utf-8",
    )

    assert ExperimentRegistry(tmp_path)._committed_experiments() == ()
