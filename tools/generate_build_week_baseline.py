#!/usr/bin/env python3
"""Generate or compare the canonical OpenAI Build Week real-game baseline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_baseline import (  # noqa: E402
    BaselineError,
    compare_baselines,
    generate_baseline,
    load_baseline_config,
)

DEFAULT_CONFIG = ROOT / "config/build_week_2026_baseline.json"
DEFAULT_OUTPUT = ROOT / "reports/build-week-2026/baseline/canonical-normal-seed-42"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the canonical real-game baseline.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--game-project-path", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configured_game = args.game_project_path or os.environ.get("GAME_PROJECT_PATH")
    if not configured_game:
        print("baseline error: provide --game-project-path or GAME_PROJECT_PATH", file=sys.stderr)
        return 2
    try:
        config = load_baseline_config(args.config)
        review = generate_baseline(
            config,
            project_root=ROOT,
            game_root=configured_game,
            output_dir=args.output,
            replace=args.replace,
        )
        result: dict = {"baseline": review}
        if args.compare_to:
            comparison = compare_baselines(args.compare_to, args.output, config)
            result["comparison"] = comparison
            if comparison["status"] != "passed":
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
                return 1
    except BaselineError as exc:
        print(f"baseline error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Build Week baseline {review['status']} ({len(review['artifacts'])} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
