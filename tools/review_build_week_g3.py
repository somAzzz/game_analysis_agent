#!/usr/bin/env python3
"""Execute and persist the independent Build Week G3 repair review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_g3 import (  # noqa: E402
    G3ReviewError,
    review_g3,
    write_g3_review,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment",
        type=Path,
        default=ROOT / "examples/build_week_2026/experiment-v1",
    )
    parser.add_argument(
        "--campaign",
        type=Path,
        default=ROOT / "examples/build_week_2026/campaign-v1",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=ROOT / "config/build_week_2026_target.json",
    )
    parser.add_argument(
        "--design-contract",
        type=Path,
        default=ROOT / "config/build_week_2026_design_contract.json",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "docs/reviews/openai_build_week_2026/G3-repair.review.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "docs/reviews/openai_build_week_2026/G3-repair.md",
    )
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        review = review_g3(
            project_root=ROOT,
            experiment_bundle=args.experiment,
            campaign_bundle=args.campaign,
            target_path=args.target,
            design_contract_path=args.design_contract,
            execute_commands=not args.skip_commands,
        )
        write_g3_review(
            json_path=args.json_output,
            markdown_path=args.markdown_output,
            review=review,
        )
    except (G3ReviewError, OSError, ValueError) as exc:
        print(f"G3 review error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Build Week G3 {review['status']} "
            f"({review['check_count']} checks, {review['failure_count']} failures)"
        )
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
