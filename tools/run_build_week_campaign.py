#!/usr/bin/env python3
"""Run, aggregate, and gate the canonical full Replay evidence campaign."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_campaign import (  # noqa: E402
    ReplayCampaignExecutor,
    build_source_identity,
    select_repair_target,
    write_target,
)
from game_analysis_agent.campaign_aggregation import (  # noqa: E402
    aggregate_campaign,
    load_failure_rules,
)
from game_analysis_agent.campaign_bundle import (  # noqa: E402
    PublicFailureClusters,
    build_public_campaign_bundle,
    verify_public_campaign_bundle,
)
from game_analysis_agent.campaign_contract import (  # noqa: E402
    CampaignManifest,
    CampaignRequest,
)
from game_analysis_agent.campaign_runner import CampaignRunner  # noqa: E402
from game_analysis_agent.settings import Settings  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/build_week_2026_campaign.json"
    )
    parser.add_argument(
        "--replay-manifest",
        type=Path,
        default=ROOT / "config/build_week_2026_full_replay.json",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=ROOT / "config/build_week_2026_failure_rules.json",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "examples/build_week_2026/campaign-v1",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=ROOT / "config/build_week_2026_target.json",
    )
    parser.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings()
    if not (settings.game_project_path / "project.godot").is_file():
        print("GAME_PROJECT_PATH does not contain project.godot", file=sys.stderr)
        return 2
    request = CampaignRequest.model_validate_json(args.config.read_text(encoding="utf-8"))
    source = build_source_identity(
        project_root=ROOT,
        game_root=settings.game_project_path,
        campaign_config=args.config,
        replay_manifest=args.replay_manifest,
    )
    executor = ReplayCampaignExecutor(
        project_root=ROOT,
        manifest_path=args.replay_manifest,
        settings=settings,
    )
    summary = CampaignRunner(
        project_root=ROOT,
        request=request,
        source=source,
        executor=executor,
    ).run(resume=not args.no_resume)
    if not summary.submittable:
        print(json.dumps({"status": "failed", "cells": summary.status_counts}, indent=2))
        return 1
    manifest = CampaignManifest.model_validate_json(
        summary.manifest_path.read_text(encoding="utf-8")
    )
    aggregation = aggregate_campaign(
        project_root=ROOT,
        results=summary.results,
        rules=load_failure_rules(args.rules),
    )
    gate = build_public_campaign_bundle(
        project_root=ROOT,
        bundle_dir=args.bundle,
        manifest=manifest,
        results=summary.results,
        aggregation=aggregation,
    )
    verify_public_campaign_bundle(args.bundle)
    public_clusters = PublicFailureClusters.model_validate_json(
        (args.bundle / "failure_clusters.json").read_text(encoding="utf-8")
    )
    target = select_repair_target(
        request=request,
        aggregation=aggregation,
        clusters=public_clusters.clusters,
        evidence_bundle=args.bundle.relative_to(ROOT).as_posix(),
    )
    write_target(args.target, target)
    print(
        json.dumps(
            {
                "status": gate.status,
                "campaign_id": request.campaign_id,
                "cells": summary.status_counts,
                "weeks": aggregation.metrics.total_weeks,
                "bundle": args.bundle.relative_to(ROOT).as_posix(),
                "target": target.selected_cluster_id,
                "target_members": target.member_count,
                "fixed_seeds": list(target.fixed_seeds),
                "holdout_seeds": list(target.holdout_seeds),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
