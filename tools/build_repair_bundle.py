#!/usr/bin/env python3
"""Build and verify a public-safe repair experiment bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.repair_bundle import (  # noqa: E402
    RepairBundleError,
    build_public_repair_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        gate = build_public_repair_bundle(
            project_root=ROOT, private_record=args.record, destination=args.output
        )
    except (OSError, ValueError, RepairBundleError) as exc:
        print(f"repair bundle error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(gate.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
