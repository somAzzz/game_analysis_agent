"""Public-safe campaign bundle schema, hash, and fail-closed tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from game_analysis_agent.campaign_aggregation import aggregate_campaign, load_failure_rules
from game_analysis_agent.campaign_bundle import (
    CampaignBundleError,
    build_public_campaign_bundle,
    verify_public_campaign_bundle,
)
from game_analysis_agent.campaign_contract import (
    CampaignCellState,
    CampaignManifest,
    CampaignRequest,
    CampaignSourceIdentity,
    build_campaign_cells,
    canonical_sha256,
)
from game_analysis_agent.campaign_runner import CampaignRunner, CellExecutionOutcome

ROOT = Path(__file__).resolve().parents[1]


def _inputs(tmp_path: Path):  # noqa: ANN202
    request = CampaignRequest(
        campaign_id="bundle-test-v1",
        personas=("newbie",),
        seeds=(42,),
        max_weeks=1,
        provider="replay",
        concurrency=1,
        report_root="reports/campaigns",
    )
    source = CampaignSourceIdentity(
        agent_commit="a" * 40,
        agent_tree="b" * 40,
        game_commit="c" * 40,
        game_tree="d" * 40,
        game_archive_sha256="e" * 64,
        campaign_config_sha256="f" * 64,
        provider="replay",
        provider_mode="replay",
        provider_revision="fixture:test",
    )

    def execute(cell, output_dir, context):  # noqa: ANN001
        del context
        row = {
            "week": 1,
            "state_after": {"money": 0, "stress": 85},
            "chosen_actions": ["rest_at_home"],
            "validation": {"valid": False, "fallback_used": True},
            "week_context": {},
            "persona_calls": [
                {
                    "phase": "decision",
                    "status": "completed",
                    "metadata": {
                        "provider": "replay",
                        "mode": "replay",
                        "model": "fixture",
                    },
                    "error": None,
                }
            ],
            "result": {"final_ending": "semester_complete"},
        }
        (output_dir / "playthrough.jsonl").write_text(
            json.dumps(row) + "\n", encoding="utf-8"
        )
        return CellExecutionOutcome(
            state=CampaignCellState.COMPLETED,
            stop_reason="week_limit",
            completed_weeks=1,
        )

    results = CampaignRunner(
        project_root=tmp_path, request=request, source=source, executor=execute
    ).run().results
    manifest = CampaignManifest(
        request=request,
        request_fingerprint=request.fingerprint(),
        source=source,
        source_fingerprint=source.fingerprint(),
        cells=build_campaign_cells(request),
        created_at=datetime.now(tz=UTC),
    )
    aggregation = aggregate_campaign(
        project_root=tmp_path,
        results=results,
        rules=load_failure_rules(ROOT / "config/build_week_2026_failure_rules.json"),
    )
    return manifest, results, aggregation


def test_bundle_contains_only_recomputable_public_safe_artifacts(tmp_path: Path) -> None:
    manifest, results, aggregation = _inputs(tmp_path)
    bundle = tmp_path / "public"

    gate = build_public_campaign_bundle(
        project_root=tmp_path,
        bundle_dir=bundle,
        manifest=manifest,
        results=results,
        aggregation=aggregation,
    )

    assert gate.status == "passed"
    assert len(gate.artifacts) == 6
    assert verify_public_campaign_bundle(bundle) == gate
    assert {path.name for path in bundle.iterdir()} == {
        "campaign_manifest.json",
        "campaign_summary.json",
        "persona_runs.jsonl",
        "agent_eval.jsonl",
        "llm_calls.jsonl",
        "failure_clusters.json",
        "gate_report.json",
    }
    combined = "\n".join(path.read_text() for path in bundle.iterdir())
    assert "prompt_text" not in combined
    assert "response_text" not in combined
    assert "api_key" not in combined
    cluster_payload = json.loads((bundle / "failure_clusters.json").read_text())
    fallback_cluster = next(
        item for item in cluster_payload["clusters"] if item["cluster_id"] == "provider-fallback"
    )
    assert fallback_cluster["members"][0]["artifact_path"] == "persona_runs.jsonl"
    assert fallback_cluster["members"][0]["line_number"] == 1
    public_row = json.loads((bundle / "persona_runs.jsonl").read_text().splitlines()[0])
    assert fallback_cluster["members"][0]["record_sha256"] == canonical_sha256(public_row)


def test_bundle_verifier_rejects_post_gate_mutation(tmp_path: Path) -> None:
    manifest, results, aggregation = _inputs(tmp_path)
    bundle = tmp_path / "public"
    build_public_campaign_bundle(
        project_root=tmp_path,
        bundle_dir=bundle,
        manifest=manifest,
        results=results,
        aggregation=aggregation,
    )
    with (bundle / "persona_runs.jsonl").open("a") as handle:
        handle.write("{}\n")

    with pytest.raises(CampaignBundleError, match="hash mismatch"):
        verify_public_campaign_bundle(bundle)


def test_incomplete_campaign_cannot_emit_passed_bundle(tmp_path: Path) -> None:
    manifest, results, aggregation = _inputs(tmp_path)
    failed = results[0].model_copy(
        update={"state": CampaignCellState.FAILED, "completed_weeks": 0}
    )

    with pytest.raises(CampaignBundleError, match="preflight"):
        build_public_campaign_bundle(
            project_root=tmp_path,
            bundle_dir=tmp_path / "public",
            manifest=manifest,
            results=[failed],
            aggregation=aggregation,
        )
