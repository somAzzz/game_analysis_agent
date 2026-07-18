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


def test_committed_correctness_experiment_is_hash_verified_and_accepted() -> None:
    registry = ExperimentRegistry(ROOT)

    index = registry.list()
    summary = next(
        item
        for item in index["experiments"]
        if item["experiment_id"] == "localization-choice-identity-v1"
    )
    detail = registry.get(summary["experiment_id"])

    assert summary["source_label"] == "DETERMINISTIC GODOT"
    assert detail["proof_kind"] == "content_correctness"
    assert detail["decision"] == "accepted"
    assert detail["correctness_proof"]["patched_identity_errors"] == 0
    assert detail["patch"]["disposition"] == "integrated_uncommitted"
    assert "Ask a friend to cover the semester contribution" in detail["patch"]["diff"]


def test_committed_openai_campaign_is_hash_verified_and_replayable() -> None:
    registry = ExperimentRegistry(ROOT)

    summary = next(
        item
        for item in registry.list()["experiments"]
        if item["experiment_id"] == "openai-all-six-seed-42-20w"
    )
    detail = registry.get(summary["experiment_id"])

    assert summary["source_label"] == "OPENAI API"
    assert summary["lifecycle_status"] == "campaign_complete"
    assert summary["campaign"]["cells"] == 6
    assert summary["campaign"]["weeks"] == 114
    assert summary["campaign"]["fallback_rate"] == 0
    assert summary["playthrough_bundle_path"].endswith("/playthrough")
    assert detail["decision"] is None
    assert detail["patch"] is None

    static = ROOT / "frontend/public-demo/experiments/openai-all-six-seed-42-20w"
    assert (static / "judge-experiment.json").is_file()
    assert (static / "playthrough/index.json").is_file()
    assert len(list((static / "playthrough/cells").glob("*.json"))) == 6
    assert not (static / "playthrough/session.json").exists()


def test_private_local_ab_campaigns_are_not_frontend_visible(monkeypatch) -> None:  # noqa: ANN001
    registry = ExperimentRegistry(ROOT)
    private = _local_campaign().model_copy(
        update={
            "experiment_id": "vllm-cohort-a-pressure-feedback-v1",
            "campaign_id": "vllm-audit-25seed-cohort-a",
        }
    )
    monkeypatch.setattr(registry, "_committed_experiments", lambda: ())
    monkeypatch.setattr(registry, "_committed_correctness_experiments", lambda: ())
    monkeypatch.setattr(registry, "_runtime_campaigns", lambda: (private,))
    monkeypatch.setattr(registry, "_runtime_repairs", lambda _campaigns: ())

    experiment_ids = {item["experiment_id"] for item in registry.list()["experiments"]}

    assert private.experiment_id not in experiment_ids
