#!/usr/bin/env python3
"""Validate current versions against the pinned Build Week toolchain."""

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
    write_inventory,
)
from game_analysis_agent.build_week_toolchain import (  # noqa: E402
    ToolchainError,
    evaluate_toolchain,
    load_toolchain,
    strict_exit_code,
)

DEFAULT_TOOLCHAIN = ROOT / "config/build_week_2026_toolchain.json"
DEFAULT_OUTPUT = ROOT / "reports/build-week-2026/baseline/toolchain.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check the pinned Build Week toolchain.")
    parser.add_argument("--toolchain", type=Path, default=DEFAULT_TOOLCHAIN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = load_toolchain(args.toolchain)
        inventory = collect_inventory(ROOT, environ=os.environ)
        result = evaluate_toolchain(inventory, manifest)
        write_inventory(args.output, result)
    except (OSError, ToolchainError, ValueError) as exc:
        print(f"toolchain error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Build Week toolchain status={result['status']} "
            f"platform={result['platform']} failures={result['failure_count']} "
            f"warnings={result['warning_count']}"
        )
    return strict_exit_code(result) if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
