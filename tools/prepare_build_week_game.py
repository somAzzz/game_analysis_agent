#!/usr/bin/env python3
"""Verify or export the exact pinned Build Week reference game."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_game_pin import (  # noqa: E402
    GamePinError,
    load_game_pin,
    materialize_game_tree,
    verify_game_pin,
    write_pinned_archive,
)

DEFAULT_PIN = ROOT / "config/build_week_2026_game_pin.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the canonical game Git object and optionally export its exact archive."
    )
    parser.add_argument("--source", type=Path, help="game Git repository")
    parser.add_argument("--pin", type=Path, default=DEFAULT_PIN)
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument("--output-archive", type=Path)
    outputs.add_argument("--materialize-dir", type=Path)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace only a previously managed materialized directory with matching provenance",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configured_source = args.source or os.environ.get("GAME_PROJECT_PATH")
    if not configured_source:
        print("game pin error: provide --source or GAME_PROJECT_PATH", file=sys.stderr)
        return 2
    try:
        manifest = load_game_pin(args.pin)
        result = verify_game_pin(configured_source, manifest)
        if args.output_archive:
            output = write_pinned_archive(configured_source, manifest, args.output_archive)
            result["output_archive"] = _display_path(output, ROOT)
        elif args.materialize_dir:
            result["materialized"] = materialize_game_tree(
                configured_source,
                manifest,
                args.materialize_dir,
                replace=args.replace,
            )
    except GamePinError as exc:
        print(f"game pin error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        checkout = result["checkout"]
        print(
            "Build Week game pin verified "
            f"(commit={result['commit'][:12]}, tree={result['tree'][:12]}, "
            f"checkout_matches_pin={str(checkout['matches_pin']).lower()})"
        )
    return 0


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


if __name__ == "__main__":
    raise SystemExit(main())
