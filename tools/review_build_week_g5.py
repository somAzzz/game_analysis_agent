#!/usr/bin/env python3
"""Run the fail-closed Build Week G5 submission review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.build_week_g5 import review_g5, write_g5_review  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    review = review_g5(project_root=ROOT)
    write_g5_review(
        json_path=ROOT / "docs/reviews/openai_build_week_2026/G5-release.review.json",
        markdown_path=ROOT / "docs/reviews/openai_build_week_2026/G5-release.md",
        review=review,
    )
    if args.json:
        print(json.dumps(review, indent=2, sort_keys=True))
    else:
        print(f"G5 {review['status']}: {review['failure_count']} failure(s)")
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
