from __future__ import annotations

from pathlib import Path

import pytest

from game_analysis_agent.campaign_contract import CampaignCellResult, CampaignManifest
from game_analysis_agent.playthrough_view import (
    TRUTH_LABEL,
    PlaythroughViewError,
    build_cell_view,
    build_playthrough_views,
    verify_playthrough_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "examples/build_week_2026/playthrough-v1"
SOURCE = EVIDENCE / "source"
CAMPAIGN = SOURCE / "reports/playthrough-evidence/campaigns/playthrough-evidence-full-v1"


def test_committed_playthrough_evidence_is_complete_and_hash_verified() -> None:
    result = verify_playthrough_evidence(EVIDENCE)

    assert result == {
        "status": "passed",
        "campaign_id": "playthrough-evidence-full-v1",
        "cells": 18,
        "nodes": 342,
        "actual_edges": 324,
        "truth_label": TRUTH_LABEL,
    }


def test_money_seed_42_view_uses_actual_trace_and_truthful_branch_semantics() -> None:
    manifest = CampaignManifest.model_validate_json(
        (CAMPAIGN / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    cell_dir = CAMPAIGN / "cells/money-seed-42-0814df41bd32"
    result = CampaignCellResult.model_validate_json(
        (cell_dir / "cell_result.json").read_text(encoding="utf-8")
    )

    view = build_cell_view(
        manifest=manifest,
        result=result,
        trace_path=cell_dir / "playthrough.jsonl",
        summary_path=cell_dir / "playthrough_summary.md",
        attractors={3: ["cashflow-stress-attractor"], 4: ["burnout-risk"]},
    )

    assert view["completed_weeks"] == 19
    assert view["final_ending"] == "cashflow_collapse"
    assert view["nodes"][0]["selected_action_ids"] == [
        "problem_set",
        "library_day",
        "language_school_germany",
        "language_tandem",
    ]
    assert view["nodes"][2]["event"]["id"] == "missing_school_registration"
    assert view["nodes"][2]["attractors"] == ["cashflow-stress-attractor"]
    assert view["nodes"][2]["state_after"]["money"] == 0
    assert view["nodes"][2]["state_after"]["stress"] == 82
    assert view["branch_semantics"] == {
        "event_choices": "legal-options-not-executed-unless-selected",
        "available_actions": "legal-actions-not-future-state-branches",
        "projected_counterfactual_states": False,
    }


def test_cell_view_rejects_tampered_raw_trace(tmp_path: Path) -> None:
    manifest = CampaignManifest.model_validate_json(
        (CAMPAIGN / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    cell_dir = CAMPAIGN / "cells/money-seed-42-0814df41bd32"
    result = CampaignCellResult.model_validate_json(
        (cell_dir / "cell_result.json").read_text(encoding="utf-8")
    )
    tampered = tmp_path / "playthrough.jsonl"
    tampered.write_bytes((cell_dir / "playthrough.jsonl").read_bytes() + b"\n")

    with pytest.raises(PlaythroughViewError, match="raw trace hash mismatch"):
        build_cell_view(
            manifest=manifest,
            result=result,
            trace_path=tampered,
            summary_path=cell_dir / "playthrough_summary.md",
        )


def test_builder_emits_hash_bound_cell_index_for_lazy_review(tmp_path: Path) -> None:
    output = tmp_path / "playthrough"

    manifest = build_playthrough_views(
        source_root=SOURCE,
        campaign_manifest_path=CAMPAIGN / "campaign_manifest.json",
        failure_clusters_path=SOURCE / "public/failure_clusters.json",
        public_gate_path=SOURCE / "public/gate_report.json",
        personas_path=SOURCE / "config/player_personas.yaml",
        action_catalog_path=SOURCE / "demo/study-in-germany/data/actions/generated_actions.json",
        output_dir=output,
    )
    index = __import__("json").loads((output / "index.json").read_text(encoding="utf-8"))

    assert manifest["cell_index"]["path"] == "index.json"
    assert index["cell_count"] == 18
    assert len(index["cells"]) == 18
    assert {
        "persona": "money",
        "seed": 42,
        "path": "cells/money-seed-42.json",
        "final_ending": "cashflow_collapse",
    }.items() <= next(
        cell.items() for cell in index["cells"] if cell["persona"] == "money" and cell["seed"] == 42
    )
    assert verify_playthrough_evidence(output, source_root=SOURCE)["cells"] == 18
