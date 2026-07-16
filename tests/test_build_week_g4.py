"""Fail-closed G4 evaluator and platform review tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from game_analysis_agent.build_week_g4 import REQUIRED_PLATFORM_CHECKS, review_g4
from game_analysis_agent.platform_delivery import platform_contract_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def test_current_g4_fails_only_unproven_release_evidence() -> None:
    review = review_g4(project_root=ROOT, execute_commands=False)

    assert review["status"] == "failed"
    assert review["failures"] == ["platform_delivery"]
    platform = next(item for item in review["checks"] if item["id"] == "platform_delivery")
    assert "platform evidence" in platform["error"]
    assert review["checks"][0]["status"] == "passed"
    assert review["checks"][1]["status"] == "passed"
    image = next(
        item for item in review["checks"] if item["id"] == "published_multiarch_image"
    )
    assert image["status"] == "passed"
    assert image["evidence"]["source_contract_sha256"] == (
        platform_contract_fingerprint(ROOT)
    )


def test_g4_rejects_stale_published_image_contract(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(
        ROOT,
        project,
        ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "dist", "reports"),
    )
    metadata_path = project / "judge-image-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["source_contract_sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    review = review_g4(project_root=project, execute_commands=False)

    image = next(
        item for item in review["checks"] if item["id"] == "published_multiarch_image"
    )
    assert image["status"] == "failed"
    assert "current delivery contract" in image["error"]


def test_g4_passes_when_all_platform_rows_and_image_are_proven(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "dist", "reports"))
    review_path = project / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json"
    platform_review = json.loads(review_path.read_text(encoding="utf-8"))
    platform_review["status"] = "passed"
    contract = platform_contract_fingerprint(project)
    platform_review["contract_sha256"] = contract
    by_id = {item["id"]: item for item in platform_review["checks"]}
    evidence_name = "platform-evidence/synthetic-complete.json"
    for identifier in REQUIRED_PLATFORM_CHECKS:
        by_id[identifier]["status"] = "passed"
        by_id[identifier]["source_contract_sha256"] = contract
        by_id[identifier]["source_revision"] = "a" * 40
        by_id[identifier]["evidence"] = evidence_name
    evidence_path = review_path.parent / evidence_name
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps({
            "schema_version": "build-week-platform-evidence-v1",
            "status": "passed",
            "source_contract_sha256": contract,
            "source_revision": "a" * 40,
            "checks": [
                {"id": identifier, "status": "passed"}
                for identifier in sorted(REQUIRED_PLATFORM_CHECKS)
            ],
        }),
        encoding="utf-8",
    )
    review_path.write_text(json.dumps(platform_review), encoding="utf-8")
    (project / "judge-image-metadata.json").write_text(
        json.dumps({
            "status": "built_and_pushed", "reference": "registry/judge:tag",
            "index_digest": "sha256:" + "a" * 64,
            "platforms": ["linux/amd64", "linux/arm64"],
            "source_contract_sha256": platform_contract_fingerprint(project),
        }),
        encoding="utf-8",
    )

    review = review_g4(project_root=project, execute_commands=False)

    assert review["status"] == "passed"
    assert review["failure_count"] == 0


def test_g4_rejects_stale_platform_contract(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "dist", "reports"))
    review_path = project / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json"
    platform_review = json.loads(review_path.read_text(encoding="utf-8"))
    platform_review["contract_sha256"] = "0" * 64
    review_path.write_text(json.dumps(platform_review), encoding="utf-8")

    review = review_g4(project_root=project, execute_commands=False)

    platform = next(item for item in review["checks"] if item["id"] == "platform_delivery")
    assert platform["status"] == "failed"
    assert "stale" in platform["error"]


def test_g4_rejects_one_stale_platform_row_even_when_review_claims_passed(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    shutil.copytree(
        ROOT,
        project,
        ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "dist", "reports"),
    )
    review_path = project / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json"
    platform_review = json.loads(review_path.read_text(encoding="utf-8"))
    contract = platform_contract_fingerprint(project)
    platform_review["status"] = "passed"
    platform_review["contract_sha256"] = contract
    for item in platform_review["checks"]:
        if item["id"] in REQUIRED_PLATFORM_CHECKS:
            item["status"] = "passed"
            item["source_contract_sha256"] = contract
    platform_review["checks"][0]["source_contract_sha256"] = "0" * 64
    review_path.write_text(json.dumps(platform_review), encoding="utf-8")

    review = review_g4(project_root=project, execute_commands=False)

    platform = next(item for item in review["checks"] if item["id"] == "platform_delivery")
    assert platform["status"] == "failed"
    assert "macos_system_python_inspect" in platform["error"]


def test_g4_rejects_missing_platform_evidence_payload(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(
        ROOT,
        project,
        ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "dist", "reports"),
    )
    review_path = project / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json"
    platform_review = json.loads(review_path.read_text(encoding="utf-8"))
    contract = platform_contract_fingerprint(project)
    platform_review["status"] = "passed"
    platform_review["contract_sha256"] = contract
    for item in platform_review["checks"]:
        if item["id"] in REQUIRED_PLATFORM_CHECKS:
            item["status"] = "passed"
            item["source_contract_sha256"] = contract
            item["source_revision"] = "a" * 40
            item["evidence"] = "platform-evidence/missing.json"
    review_path.write_text(json.dumps(platform_review), encoding="utf-8")

    review = review_g4(project_root=project, execute_commands=False)

    platform = next(item for item in review["checks"] if item["id"] == "platform_delivery")
    assert platform["status"] == "failed"
    assert "missing.json" in platform["error"]
