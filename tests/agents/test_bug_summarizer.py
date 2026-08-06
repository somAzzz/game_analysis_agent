"""Tests for ``game_analysis_agent.bug_summarizer``."""

from __future__ import annotations

from game_analysis_agent.bug_summarizer import render_summary_markdown, summarize_anomalies
from game_analysis_agent.schemas import Anomaly


def _anom(kind: str, severity: str = "warning", run_id: int = 0, week: int = 1, msg: str = ""):
    return Anomaly(
        kind=kind,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        run_id=run_id,
        week=week,
        policy="balanced",
        message=msg or f"example {kind}",
    )


def test_summarize_groups_anomalies() -> None:
    anomalies = [
        _anom("negative_money", "critical", run_id=0, msg="money went -200"),
        _anom("negative_money", "critical", run_id=1),
        _anom("dead_state", "warning", run_id=2),
    ]
    summary = summarize_anomalies(anomalies)
    assert summary["total_anomalies"] == 3
    assert summary["runs_affected"] == 3
    assert summary["by_severity"]["critical"] == 2
    assert summary["by_severity"]["warning"] == 1
    assert summary["by_kind"]["negative_money"]["count"] == 2


def test_render_summary_markdown_includes_heading() -> None:
    anomalies = [_anom("dead_state", "warning", run_id=7, msg="stuck on week 8")]
    summary = summarize_anomalies(anomalies)
    text = render_summary_markdown(summary)
    assert "# Bug & Anomaly Summary" in text
    assert "`dead_state` × 1" in text
    assert "stuck on week 8" in text


def test_render_summary_markdown_handles_empty() -> None:
    text = render_summary_markdown(
        {"total_anomalies": 0, "runs_affected": 0, "by_severity": {}, "by_kind": {}}
    )
    assert "No anomalies detected." in text