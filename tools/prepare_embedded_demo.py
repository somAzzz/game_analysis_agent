#!/usr/bin/env python3
"""Verify the bundled Study in Germany demo and create a writable runtime copy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.build_week_game_pin import (  # noqa: E402
    GamePinError,
    prepare_embedded_game_runtime,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare_embedded_game_runtime(ROOT, args.output, replace=args.replace)
    except GamePinError as exc:
        print(f"embedded demo error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Embedded demo runtime prepared: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
