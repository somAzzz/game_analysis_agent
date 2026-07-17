"""CLI contract joining repair worktree validation to proof verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.repair_worktree import build_parser


def test_validate_requires_distinct_diff_and_structured_evidence_paths() -> None:
    parsed = build_parser().parse_args(
        [
            "validate",
            "--worktree",
            "/tmp/candidate",
            "--plan",
            "config/plan.json",
            "--patch",
            "reports/patch.diff",
            "--evidence",
            "reports/patch_evidence.json",
        ]
    )

    assert parsed.patch == Path("reports/patch.diff")
    assert parsed.evidence == Path("reports/patch_evidence.json")

    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "validate",
                "--worktree",
                "/tmp/candidate",
                "--plan",
                "config/plan.json",
                "--patch",
                "reports/patch.diff",
            ]
        )
