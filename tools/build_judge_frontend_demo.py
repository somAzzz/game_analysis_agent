#!/usr/bin/env python3
"""Freeze the public Judge experiment for static and GitHub Pages demos."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.judge_api import PUBLIC_EXPERIMENT_ID, JudgeService  # noqa: E402

TARGETS = (
    ROOT / "frontend/public-demo/judge-demo.json",
)


def main() -> int:
    payload = JudgeService(project_root=ROOT, environment={}).experiment(PUBLIC_EXPERIMENT_ID)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")
    print(f"wrote {len(TARGETS)} Judge demo fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
