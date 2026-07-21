"""Submission draft claim-ledger checks."""

from __future__ import annotations

from pathlib import Path

from tools.review_submission_assets import review

ROOT = Path(__file__).resolve().parents[1]


def test_submission_drafts_use_only_verified_claim_text() -> None:
    result = review()

    assert result["status"] == "passed"
    assert result["release_status"] == "eligible_for_g5"
    assert result["failure_count"] == 0

    devpost = (ROOT / "submission/build-week-2026/DEVPOST_DRAFT.md").read_text(encoding="utf-8")
    assert "https://github.com/somAzzz/game_analysis_agent" in devpost
    assert "https://somazzz.github.io/game_analysis_agent/" in devpost
    assert "{{REPOSITORY_URL}}" not in devpost
    assert "{{PUBLIC_UI_URL}}" not in devpost
    assert "{{YOUTUBE_URL}}" not in devpost
