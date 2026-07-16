#!/usr/bin/env python3
"""Write the P0.1 OpenAI Build Week repository/environment inventory."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_inventory import (  # noqa: E402
    collect_inventory,
    strict_exit_code,
    write_inventory,
)

DEFAULT_OUTPUT = ROOT / "reports/build-week-2026/baseline/inventory.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect a sanitized Build Week scope and environment inventory."
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--game-project-path", type=Path)
    parser.add_argument(
        "--scope",
        type=Path,
        default=ROOT / "config/build_week_2026_scope.json",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true", help="also print the inventory to stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when required repositories, files, or license approvals are missing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    game_path = args.game_project_path or os.environ.get("GAME_PROJECT_PATH")
    try:
        inventory = collect_inventory(
            args.repo_root,
            game_project_path=game_path,
            scope_path=args.scope,
        )
        output = write_inventory(args.output, inventory)
    except (OSError, ValueError) as exc:
        print(f"inventory error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        readiness = inventory["readiness"]
        print(
            f"Build Week inventory written to {_display_path(output, args.repo_root)} "
            f"(status={readiness['status']}, blockers={readiness['blocker_count']})"
        )
    return strict_exit_code(inventory) if args.strict else 0


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


if __name__ == "__main__":
    raise SystemExit(main())
