#!/usr/bin/env python3
"""Offline, read-only preflight for the Playtest Forge repair workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_campaign import FrozenRepairTarget  # noqa: E402
from game_analysis_agent.build_week_g2 import (  # noqa: E402
    recompute_public_clusters,
    recompute_public_evidence,
)
from game_analysis_agent.campaign_bundle import verify_public_campaign_bundle  # noqa: E402
from game_analysis_agent.design_contract import load_design_contract  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bundle = ROOT / "examples/build_week_2026/campaign-v1"
    contract = load_design_contract(
        ROOT / "config/build_week_2026_design_contract.json", project_root=ROOT
    )
    target = FrozenRepairTarget.model_validate_json(
        (ROOT / "config/build_week_2026_target.json").read_text(encoding="utf-8")
    )
    gate = verify_public_campaign_bundle(bundle)
    metrics = recompute_public_evidence(bundle)
    clusters = recompute_public_clusters(bundle)
    if target.selected_cluster_id != contract.selected_target.cluster_id:
        raise RuntimeError("target and design contract differ")
    payload = {
        "status": "passed",
        "campaign_id": target.campaign_id,
        "target": target.selected_cluster_id,
        "target_members": target.member_count,
        "fixed_seeds": list(target.fixed_seeds),
        "holdout_seeds": list(target.holdout_seeds),
        "design_contract_sha256": contract.fingerprint(),
        "bundle_gate": gate.status,
        "weeks_recomputed": metrics["total_weeks"],
        "clusters_recomputed": clusters["clusters_recomputed"],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"Playtest Forge preflight passed: {payload['target']} "
            f"({payload['target_members']} baseline members)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
