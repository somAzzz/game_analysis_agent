#!/usr/bin/env python3
"""Build frontend-ready actual path views from retained real-Godot traces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.playthrough_view import (  # noqa: E402
    PlaythroughViewError,
    build_playthrough_views,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--campaign-manifest", type=Path, required=True)
    parser.add_argument("--failure-clusters", type=Path, required=True)
    parser.add_argument("--public-gate", type=Path, required=True)
    parser.add_argument("--personas", type=Path)
    parser.add_argument(
        "--action-catalog",
        type=Path,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    personas = args.personas or args.source_root / "config/player_personas.yaml"
    action_catalog = (
        args.action_catalog
        or args.source_root / "demo/study-in-germany/data/actions/generated_actions.json"
    )
    try:
        result = build_playthrough_views(
            source_root=args.source_root,
            campaign_manifest_path=args.campaign_manifest,
            failure_clusters_path=args.failure_clusters,
            public_gate_path=args.public_gate,
            personas_path=personas,
            action_catalog_path=action_catalog,
            output_dir=args.output,
        )
    except (OSError, ValueError, PlaythroughViewError) as exc:
        print(f"playthrough view error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
