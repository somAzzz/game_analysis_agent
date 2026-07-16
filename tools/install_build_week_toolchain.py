#!/usr/bin/env python3
"""Install pinned Node and Godot builds into the ignored local tools directory."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_toolchain import load_toolchain  # noqa: E402
from game_analysis_agent.build_week_toolchain_install import (  # noqa: E402
    ToolchainInstallError,
    install_toolchain,
)

DEFAULT_MANIFEST = ROOT / "config/build_week_2026_toolchain.json"
DEFAULT_INSTALL_ROOT = ROOT / ".tools/build-week"
DEFAULT_CACHE_ROOT = ROOT / ".tools/cache"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the pinned Build Week toolchain.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--install-root", type=Path, default=DEFAULT_INSTALL_ROOT)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--tools", nargs="+", choices=("node", "godot"), default=["node", "godot"])
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = load_toolchain(args.manifest)
        result = install_toolchain(
            manifest,
            install_root=args.install_root,
            cache_root=args.cache_root,
            system=platform.system(),
            machine=platform.machine(),
            tools=args.tools,
            replace=args.replace,
        )
    except (OSError, ValueError, ToolchainInstallError) as exc:
        print(f"toolchain install error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        states = ", ".join(f"{name}={item['status']}" for name, item in result["tools"].items())
        print(f"Build Week toolchain {result['status']} ({states}); source {result['environment_file']}")
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
