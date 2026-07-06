"""Tests for ``tools.compare_reports`` (T07)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.compare_reports import compare_reports, render_markdown


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _populate_report(
    root: Path,
    *,
    endings: list[dict[str, str]],
    actions: list[dict[str, str]],
    weekly: list[dict[str, str]],
    anomalies: list[dict],
    value_report: dict | None = None,
    route_report: dict | None = None,
) -> None:
    _write_csv(root / "ending_distribution.csv", endings)
    _write_csv(root / "action_pick_rates.csv", actions)
    _write_csv(root / "weekly_stats.csv", weekly)
    _write_jsonl(root / "anomalies.jsonl", anomalies)
    if value_report is not None:
        (root / "value_report.json").write_text(
            json.dumps(value_report, ensure_ascii=False), encoding="utf-8"
        )
    if route_report is not None:
        (root / "route_report.json").write_text(
            json.dumps(route_report, ensure_ascii=False), encoding="utf-8"
        )


def test_compare_reports_emits_diff(tmp_path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    _populate_report(
        before,
        endings=[
            {"policy": "balanced", "ending_id": "academic_success", "count": "60", "rate": "0.6"},
            {"policy": "balanced", "ending_id": "burnout", "count": "40", "rate": "0.4"},
        ],
        actions=[
            {"policy": "balanced", "action_id": "study_library", "count": "100", "rate_per_run": "1.0"},
        ],
        weekly=[
            {"policy": "balanced", "week": "10", "metric": "stress", "mean": "20", "median": "20", "p10": "10", "p90": "30", "min": "0", "max": "40"},
        ],
        anomalies=[
            {"kind": "crisis_success_ending", "severity": "critical", "run_id": 0, "week": 5, "policy": "balanced", "evidence": {}, "message": ""},
        ],
        value_report={"finding_count": 3, "by_kind": {"action_dominant": 1, "action_dead": 2}},
    )
    _populate_report(
        after,
        endings=[
            {"policy": "balanced", "ending_id": "academic_success", "count": "40", "rate": "0.4"},
            {"policy": "balanced", "ending_id": "burnout", "count": "50", "rate": "0.5"},
            {"policy": "balanced", "ending_id": "barely_survived", "count": "10", "rate": "0.1"},
        ],
        actions=[
            {"policy": "balanced", "action_id": "study_library", "count": "70", "rate_per_run": "0.7"},
            {"policy": "balanced", "action_id": "mini_job", "count": "40", "rate_per_run": "0.4"},
        ],
        weekly=[
            {"policy": "balanced", "week": "10", "metric": "stress", "mean": "50", "median": "50", "p10": "30", "p90": "70", "min": "20", "max": "80"},
        ],
        anomalies=[
            {"kind": "social_success_under_survival_crisis", "severity": "critical", "run_id": 1, "week": 3, "policy": "balanced", "evidence": {}, "message": ""},
            {"kind": "social_success_under_survival_crisis", "severity": "critical", "run_id": 2, "week": 4, "policy": "balanced", "evidence": {}, "message": ""},
        ],
        value_report={"finding_count": 4, "by_kind": {"action_dominant": 0, "action_dead": 4}},
    )
    diff = compare_reports(before, after)
    assert diff["before"] == str(before)
    assert diff["after"] == str(after)
    # Endings: academic_success drops, burnout rises, barely_survived new.
    ending_map = {
        (row["policy"], row["ending_id"]): row["delta"]
        for row in diff["endings"]["rows"]
    }
    assert ending_map[("balanced", "academic_success")] < 0
    assert ending_map[("balanced", "burnout")] > 0
    assert ending_map[("balanced", "barely_survived")] > 0
    # Actions: study_library dropped, mini_job new.
    action_map = {
        (row["policy"], row["action_id"]): row["delta"]
        for row in diff["actions"]["rows"]
    }
    assert action_map[("balanced", "study_library")] < 0
    assert action_map[("balanced", "mini_job")] > 0
    # Anomalies: crisis_success_ending gone, social_success_under_survival_crisis appeared.
    anomaly_map = {row["kind"]: row["delta"] for row in diff["anomalies"]["rows"]}
    assert anomaly_map["crisis_success_ending"] < 0
    assert anomaly_map["social_success_under_survival_crisis"] > 0
    # Value report: action_dominant drops to 0, action_dead rises.
    value_map = {row["kind"]: row["delta"] for row in diff["value_report"]["rows"]}
    assert value_map["action_dominant"] < 0
    assert value_map["action_dead"] > 0


def test_render_markdown_includes_all_dimensions(tmp_path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    _populate_report(
        before,
        endings=[
            {"policy": "balanced", "ending_id": "academic_success", "count": "100", "rate": "1.0"},
        ],
        actions=[],
        weekly=[],
        anomalies=[{"kind": "x", "severity": "warning", "run_id": 0, "week": 1, "policy": "p", "evidence": {}, "message": ""}],
    )
    _populate_report(
        after,
        endings=[
            {"policy": "balanced", "ending_id": "academic_success", "count": "80", "rate": "0.8"},
            {"policy": "balanced", "ending_id": "burnout", "count": "20", "rate": "0.2"},
        ],
        actions=[],
        weekly=[],
        anomalies=[],
    )
    diff = compare_reports(before, after)
    md = render_markdown(diff)
    for header in (
        "# Report Diff",
        "## Endings",
        "## Actions",
        "## Weekly stats",
        "## Anomalies",
        "## value_report.json",
        "## route_report.json",
    ):
        assert header in md, f"Missing section: {header}"


def test_compare_reports_handles_missing_files(tmp_path) -> None:
    before = tmp_path / "empty_before"
    after = tmp_path / "empty_after"
    diff = compare_reports(before, after)
    assert diff["endings"]["rows"] == []
    assert diff["actions"]["rows"] == []
    assert diff["weekly_stats"]["rows"] == []
    assert diff["anomalies"]["rows"] == []