#!/usr/bin/env python3
"""Freeze the public Judge experiment for static and GitHub Pages demos."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.judge_api import PUBLIC_EXPERIMENT_ID, JudgeService  # noqa: E402

TARGETS = (ROOT / "frontend/public-demo/judge-demo.json",)

STATIC_EXPERIMENT_ROOT = ROOT / "frontend/public-demo/experiments"
STATIC_INDEX = ROOT / "frontend/public-demo/experiment-index.json"


def main() -> int:
    service = JudgeService(project_root=ROOT, environment={})
    payload = service.experiment(PUBLIC_EXPERIMENT_ID)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")

    summaries = [
        item
        for item in service.list_experiments()["experiments"]
        if item["experiment_id"] == PUBLIC_EXPERIMENT_ID
        or (
            item["lifecycle_status"] == "proof_complete"
            and item["campaign_bundle_path"].startswith("examples/build_week_2026/experiments/")
        )
    ]
    index = {"schema_version": "judge-experiment-index-v1", "experiments": summaries}
    STATIC_INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    published_ids = {str(item["experiment_id"]) for item in summaries}
    if STATIC_EXPERIMENT_ROOT.exists():
        for child in STATIC_EXPERIMENT_ROOT.iterdir():
            if child.is_dir() and child.name not in published_ids:
                shutil.rmtree(child)

    for summary in summaries:
        experiment_id = summary["experiment_id"]
        if experiment_id == PUBLIC_EXPERIMENT_ID:
            continue
        target = STATIC_EXPERIMENT_ROOT / experiment_id / "judge-experiment.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(service.experiment(experiment_id), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(f"wrote {len(TARGETS) + len(summaries)} Judge demo fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
