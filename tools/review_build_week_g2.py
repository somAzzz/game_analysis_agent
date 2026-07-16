#!/usr/bin/env python3
"""Execute and persist the independent Build Week G2 campaign review."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_g2 import (  # noqa: E402
    G2ReviewError,
    review_g2,
    write_g2_review,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-project-path", type=Path)
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
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/build_week_2026_campaign.json"
    )
    parser.add_argument(
        "--replay-manifest",
        type=Path,
        default=ROOT / "config/build_week_2026_full_replay.json",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "docs/reviews/openai_build_week_2026/G2-campaign.review.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "docs/reviews/openai_build_week_2026/G2-campaign.md",
    )
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    game = args.game_project_path or os.environ.get("GAME_PROJECT_PATH")
    if not game:
        print("G2 review error: provide --game-project-path or GAME_PROJECT_PATH", file=sys.stderr)
        return 2
    try:
        review = review_g2(
            project_root=ROOT,
            game_root=game,
            bundle_dir=args.bundle,
            target_path=args.target,
            campaign_config=args.config,
            replay_manifest=args.replay_manifest,
            execute_commands=not args.skip_commands,
        )
        write_g2_review(
            json_path=args.json_output,
            markdown_path=args.markdown_output,
            review=review,
        )
    except (G2ReviewError, OSError, ValueError) as exc:
        print(f"G2 review error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Build Week G2 {review['status']} "
            f"({review['check_count']} checks, {review['failure_count']} failures)"
        )
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
