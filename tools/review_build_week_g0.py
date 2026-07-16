#!/usr/bin/env python3
"""Execute and persist the Build Week G0 baseline review."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_g0 import (  # noqa: E402
    G0ReviewError,
    review_g0,
    write_g0_review,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the fail-closed Build Week G0 review.")
    parser.add_argument("--game-project-path", type=Path)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=ROOT / "reports/build-week-2026/baseline/canonical-normal-seed-42",
    )
    parser.add_argument(
        "--reproduction",
        type=Path,
        default=ROOT / "reports/build-week-2026/baseline/repro-canonical-normal-seed-42",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/build-week-2026/reviews/G0-baseline.json",
    )
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    game = args.game_project_path or os.environ.get("GAME_PROJECT_PATH")
    if not game:
        print("G0 review error: provide --game-project-path or GAME_PROJECT_PATH", file=sys.stderr)
        return 2
    try:
        review = review_g0(
            project_root=ROOT,
            game_root=game,
            baseline_dir=args.baseline,
            reproduction_dir=args.reproduction,
            baseline_config_path=ROOT / "config/build_week_2026_baseline.json",
            game_pin_path=ROOT / "config/build_week_2026_game_pin.json",
            toolchain_path=ROOT / "config/build_week_2026_toolchain.json",
            execute_commands=not args.skip_commands,
        )
        write_g0_review(args.output, review)
    except (G0ReviewError, OSError, ValueError) as exc:
        print(f"G0 review error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Build Week G0 {review['status']} "
            f"({review['check_count']} checks, {review['failure_count']} failures)"
        )
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
