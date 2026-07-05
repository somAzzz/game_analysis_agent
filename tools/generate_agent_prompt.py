#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analyse_agent.report_bundle import read_report_bundle, render_prompt


def usage() -> None:
    print("Usage: python3 tools/generate_agent_prompt.py <report_dir> [agent_name]")


def main() -> int:
    if len(sys.argv) not in (2, 3):
        usage()
        return 2
    report_dir = Path(sys.argv[1])
    agent_name = sys.argv[2] if len(sys.argv) == 3 else "balance"
    user_template = ROOT / "prompts" / f"{agent_name}_agent_user.md"
    if not user_template.exists():
        print(f"Missing prompt template: {user_template}", file=sys.stderr)
        return 1

    bundle = read_report_bundle(report_dir)
    rendered = render_prompt(user_template, bundle)
    out_path = report_dir / "agent_prompt.md"
    out_path.write_text(rendered, encoding="utf-8")
    print(f"Prompt written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
