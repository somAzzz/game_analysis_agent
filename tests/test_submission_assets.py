"""Submission draft claim-ledger checks."""

from __future__ import annotations

from tools.review_submission_assets import review


def test_submission_drafts_use_only_verified_claim_text() -> None:
    result = review()

    assert result["status"] == "passed"
    assert result["release_status"] == "blocked"
    assert result["failure_count"] == 0
