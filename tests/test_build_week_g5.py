"""Build Week G5 release gate tests."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from game_analysis_agent.build_week_g5 import review_g5

ROOT = Path(__file__).resolve().parents[1]


def _copy(source: str, project: Path) -> Path:
    destination = project / source
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / source, destination)
    return destination


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_current_submission_fails_closed_on_external_release_blockers() -> None:
    review = review_g5(project_root=ROOT)

    assert review["status"] == "failed"
    assert review["failure_count"] >= 7
    assert {
        "prior_gates",
        "claim_ledger",
        "release_metadata",
        "manual_comparison",
        "clean_room_review",
        "video_review",
        "published_image",
        "license_privacy_secrets",
    }.issubset(review["failures"])


def test_complete_synthetic_submission_can_pass_all_g5_checks(tmp_path: Path) -> None:
    for source in (
        "docs/reviews/G0-baseline.md",
        "docs/reviews/G1-providers.md",
        "docs/reviews/openai_build_week_2026/G2-campaign.review.json",
        "docs/reviews/openai_build_week_2026/G3-repair.review.json",
        "docs/reviews/openai_build_week_2026/G4-evaluator.review.json",
        "submission/build-week-2026/DEVPOST_DRAFT.md",
        "submission/build-week-2026/VIDEO_SCRIPT.md",
        "submission/build-week-2026/claim-ledger.json",
        "submission/build-week-2026/release-metadata.json",
        "submission/build-week-2026/manual-comparison.json",
        "submission/build-week-2026/clean-room-review.json",
        "submission/build-week-2026/video-review.json",
        "examples/build_week_2026/campaign-v1/campaign_summary.json",
        "examples/build_week_2026/campaign-v1/failure_clusters.json",
        "examples/build_week_2026/experiment-v1/repair_experiment.json",
        "examples/build_week_2026/experiment-v1/comparison.json",
    ):
        _copy(source, tmp_path)

    g4_path = tmp_path / "docs/reviews/openai_build_week_2026/G4-evaluator.review.json"
    g4 = _read(g4_path)
    g4["status"] = "passed"
    _write(g4_path, g4)

    ledger_path = tmp_path / "submission/build-week-2026/claim-ledger.json"
    ledger = _read(ledger_path)
    ledger["status"] = "release_ready"
    for item in ledger["pending_external_claims"]:  # type: ignore[index]
        item["status"] = "completed"
    _write(ledger_path, ledger)

    image_ref = "ghcr.io/example/playtest-forge-judge"
    digest = "sha256:" + "b" * 64
    devpost_path = tmp_path / "submission/build-week-2026/DEVPOST_DRAFT.md"
    devpost = devpost_path.read_text(encoding="utf-8")
    replacements = {
        "{{REPOSITORY_URL}}": "https://example.com/repository",
        "{{PUBLIC_UI_URL}}": "https://example.com/ui",
        "https://github.com/somAzzz/game_analysis_agent": "https://example.com/repository",
        "https://somazzz.github.io/game_analysis_agent/": "https://example.com/ui",
        "{{YOUTUBE_URL}}": "https://youtube.com/watch?v=example",
        "{{IMAGE_REFERENCE_AND_DIGEST}}": f"{image_ref}@{digest}",
    }
    for before, after in replacements.items():
        devpost = devpost.replace(before, after)
    devpost_path.write_text(devpost, encoding="utf-8")

    metadata_path = tmp_path / "submission/build-week-2026/release-metadata.json"
    metadata = _read(metadata_path)
    metadata.update(
        {
            "status": "ready",
            "release_revision": "a" * 40,
            "license_path": "LICENSE",
            "privacy_review": {
                "status": "completed",
                "raw_prompts_committed": False,
                "raw_model_outputs_committed": False,
            },
            "codex_model": "gpt-5.6",
            "codex_model_evidence": {
                "status": "verified",
                "source": "test fixture",
                "verified_at": "2026-07-16T00:00:00Z",
            },
        }
    )
    metadata["repository"] = {
        "url": "https://example.com/repository",
        "access_verified": True,
        "verified_at": "2026-07-16T00:00:00Z",
    }
    metadata["public_ui"] = {
        "url": "https://example.com/ui",
        "access_verified": True,
        "verified_at": "2026-07-16T00:00:00Z",
    }
    _write(metadata_path, metadata)

    _write(
        tmp_path / "submission/build-week-2026/manual-comparison.json",
        {
            "status": "completed",
            "same_task": True,
            "same_stopping_rule": True,
            "manual_seconds": 600,
            "forge_seconds": 120,
            "reviewer_role": "non_builder",
        },
    )
    _write(
        tmp_path / "submission/build-week-2026/clean-room-review.json",
        {
            "status": "completed",
            "reviewer_role": "non_builder",
            "elapsed_seconds": 600,
            "tasks": {name: True for name in ("product", "roles", "first_command", "headline_evidence", "repair_decision")},
            "stop_ship_findings": [],
        },
    )
    _write(
        tmp_path / "submission/build-week-2026/video-review.json",
        {
            "status": "completed",
            "url": "https://youtube.com/watch?v=example",
            "duration_seconds": 170,
            "signed_out_access": True,
            "audio_verified": True,
            "captions_verified": True,
            "no_secrets_verified": True,
        },
    )
    _write(
        tmp_path / "judge-image-metadata.json",
        {
            "status": "built_and_pushed",
            "platforms": ["linux/amd64", "linux/arm64"],
            "reference": image_ref,
            "index_digest": digest,
        },
    )
    (tmp_path / "LICENSE").write_text("Test-only license fixture.\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    review = review_g5(project_root=tmp_path)

    assert review["status"] == "passed"
    assert review["failure_count"] == 0
