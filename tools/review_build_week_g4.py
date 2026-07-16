#!/usr/bin/env python3
"""Execute and persist the fail-closed Build Week G4 evaluator review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.build_week_g4 import review_g4, write_g4_review  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-output", type=Path, default=ROOT / "docs/reviews/openai_build_week_2026/G4-evaluator.review.json")
    parser.add_argument("--markdown-output", type=Path, default=ROOT / "docs/reviews/openai_build_week_2026/G4-evaluator.md")
    args = parser.parse_args(argv)
    review = review_g4(project_root=ROOT, execute_commands=not args.skip_commands)
    write_g4_review(json_path=args.json_output, markdown_path=args.markdown_output, review=review)
    if args.json:
        print(json.dumps(review, indent=2, sort_keys=True))
    else:
        print(f"Build Week G4 {review['status']} ({review['failure_count']} failures)")
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
