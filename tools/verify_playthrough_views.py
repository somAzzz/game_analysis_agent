#!/usr/bin/env python3
"""Verify retained raw traces and derived Playthrough Inspector views."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.playthrough_view import (  # noqa: E402
    PlaythroughViewError,
    verify_playthrough_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "examples/build_week_2026/playthrough-v1",
    )
    args = parser.parse_args(argv)
    try:
        result = verify_playthrough_evidence(args.evidence)
    except (OSError, ValueError, PlaythroughViewError) as exc:
        print(f"playthrough evidence error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
