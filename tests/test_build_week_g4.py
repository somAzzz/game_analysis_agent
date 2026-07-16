"""Fail-closed G4 evaluator and platform review tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from game_analysis_agent.build_week_g4 import REQUIRED_PLATFORM_CHECKS, review_g4

ROOT = Path(__file__).resolve().parents[1]


def test_current_g4_fails_only_unproven_release_evidence() -> None:
    review = review_g4(project_root=ROOT, execute_commands=False)

    assert review["status"] == "failed"
    assert review["failures"] == ["platform_delivery", "published_multiarch_image"]
    assert review["checks"][0]["status"] == "passed"
    assert review["checks"][1]["status"] == "passed"


def test_g4_passes_when_all_platform_rows_and_image_are_proven(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "dist", "reports"))
    review_path = project / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json"
    platform_review = json.loads(review_path.read_text(encoding="utf-8"))
    platform_review["status"] = "passed"
    by_id = {item["id"]: item for item in platform_review["checks"]}
    for identifier in REQUIRED_PLATFORM_CHECKS:
        by_id[identifier]["status"] = "passed"
    review_path.write_text(json.dumps(platform_review), encoding="utf-8")
    (project / "judge-image-metadata.json").write_text(
        json.dumps({
            "status": "built_and_pushed", "reference": "registry/judge:tag",
            "index_digest": "sha256:" + "a" * 64,
            "platforms": ["linux/amd64", "linux/arm64"],
        }),
        encoding="utf-8",
    )

    review = review_g4(project_root=project, execute_commands=False)

    assert review["status"] == "passed"
    assert review["failure_count"] == 0
