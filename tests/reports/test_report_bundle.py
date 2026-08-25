"""Tests for the small utilities that ship with the project."""

from __future__ import annotations

from pathlib import Path

import pytest

from game_analysis_agent.report_bundle import (
    DEFAULT_REPORT_FILES,
    read_report_bundle,
    render_prompt,
)


def test_read_report_bundle_handles_missing_files(tmp_path: Path) -> None:
    bundle = read_report_bundle(tmp_path, files=["summary.json"])
    assert "MISSING" in bundle
    assert "## summary.json" in bundle


def test_read_report_bundle_includes_existing_files(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text('{"ok": true}', encoding="utf-8")
    bundle = read_report_bundle(tmp_path, files=["summary.json"])
    assert '"ok": true' in bundle


def test_render_prompt_substitutes_bundle(tmp_path: Path) -> None:
    tmpl = tmp_path / "user.md"
    tmpl.write_text("Here is the data:\n{{REPORT_BUNDLE}}\n", encoding="utf-8")
    out = render_prompt(tmpl, "ABC123")
    assert "ABC123" in out
    assert "{{REPORT_BUNDLE}}" not in out


def test_default_report_files_includes_all_artifacts() -> None:
    expected = {
        "summary.json",
        "ending_distribution.csv",
        "weekly_stats.csv",
        "action_pick_rates.csv",
        "event_trigger_rates.csv",
        "choice_pick_rates.csv",
        "anomaly_report.md",
    }
    assert expected.issubset(set(DEFAULT_REPORT_FILES))


@pytest.mark.parametrize(
    "missing_file",
    ["summary.json", "ending_distribution.csv", "weekly_stats.csv"],
)
def test_each_artifact_is_optional(tmp_path: Path, missing_file: str) -> None:
    bundle = read_report_bundle(tmp_path, files=[missing_file])
    assert "MISSING" in bundle