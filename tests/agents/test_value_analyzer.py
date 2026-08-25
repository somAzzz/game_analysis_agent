"""Tests for ``game_analysis_agent.value_analyzer``."""

from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.value_analyzer import (
    analyze_action_groups,
    analyze_and_write,
    analyze_crisis_response,
    analyze_ending_contradictions,
    analyze_route_metrics,
    analyze_route_separation,
    analyze_values,
)


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(header))
        handle.write("\n")
        for row in rows:
            handle.write(",".join(str(v) for v in row))
            handle.write("\n")


def test_dominant_action_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "action_pick_rates.csv",
        ["policy", "action_id", "count", "rate_per_run"],
        [
            ["balanced", "study_library", 90, 0.90],
            ["balanced", "rest_at_home", 50, 0.50],
        ],
    )
    findings = analyze_values(action_csv=tmp_path / "action_pick_rates.csv")
    dominant = [f for f in findings if f.scope == "action" and "study_library" in f.target_id]
    assert dominant
    assert dominant[0].severity == "warning"


def test_dead_action_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "action_pick_rates.csv",
        ["policy", "action_id", "count", "rate_per_run"],
        [
            ["balanced", "study_library", 50, 0.50],
            ["balanced", "obscure_action", 1, 0.01],
        ],
    )
    findings = analyze_values(action_csv=tmp_path / "action_pick_rates.csv")
    dead = [f for f in findings if f.scope == "action" and "obscure_action" in f.target_id]
    assert dead
    assert dead[0].severity == "info"


def test_dominant_choice_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "choice_pick_rates.csv",
        ["policy", "event_id", "choice_id", "count", "rate_per_event"],
        [
            ["balanced", "first_lecture", "first_lecture.choice_01_ask_question", 100, 0.90],
            ["balanced", "first_lecture", "first_lecture.choice_02_stay_silent", 10, 0.10],
        ],
    )
    findings = analyze_values(choice_csv=tmp_path / "choice_pick_rates.csv")
    dom = [f for f in findings if f.scope == "choice" and "first_lecture" in f.target_id]
    assert dom
    assert dom[0].finding_id.startswith("choice_dominant-")


def test_rare_event_is_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "event_trigger_rates.csv",
        ["policy", "event_id", "count", "rate_per_run"],
        [
            ["balanced", "first_lecture", 100, 1.00],
            ["balanced", "obscure_event", 1, 0.001],
        ],
    )
    findings = analyze_values(event_csv=tmp_path / "event_trigger_rates.csv")
    rare = [f for f in findings if f.scope == "event" and "obscure_event" in f.target_id]
    assert rare
    assert rare[0].severity == "info"


def test_ending_dominance_flagged(tmp_path) -> None:
    _write_csv(
        tmp_path / "ending_distribution.csv",
        ["policy", "ending_id", "count", "rate"],
        [
            ["balanced", "academic_success", 95, 0.95],
            ["balanced", "burnout", 5, 0.05],
        ],
    )
    findings = analyze_values(ending_csv=tmp_path / "ending_distribution.csv")
    ending = [f for f in findings if f.scope == "ending"]
    assert ending


def test_analyze_and_write_persists_value_report(tmp_path) -> None:
    _write_csv(
        tmp_path / "action_pick_rates.csv",
        ["policy", "action_id", "count", "rate_per_run"],
        [["balanced", "a", 100, 0.95]],
    )
    _write_csv(
        tmp_path / "event_trigger_rates.csv",
        ["policy", "event_id", "count", "rate_per_run"],
        [["balanced", "x", 100, 1.0]],
    )
    _write_csv(
        tmp_path / "choice_pick_rates.csv",
        ["policy", "event_id", "choice_id", "count", "rate_per_event"],
        [["balanced", "x", "x.choice_01", 100, 1.0]],
    )
    _write_csv(
        tmp_path / "ending_distribution.csv",
        ["policy", "ending_id", "count", "rate"],
        [["balanced", "y", 100, 1.0]],
    )
    findings = analyze_and_write(tmp_path)
    assert isinstance(findings, list)
    assert (tmp_path / "value_report.json").exists()
    payload = json.loads((tmp_path / "value_report.json").read_text(encoding="utf-8"))
    assert payload["finding_count"] == len(findings)


# ---------------------------------------------------------------------------
# T06 — action group / crisis response / ending contradictions / route separation
# ---------------------------------------------------------------------------


def _make_run(
    *,
    run_id: int = 0,
    policy: str = "balanced",
    ending: str = "academic_success",
    actions: list[str] | None = None,
    weeks: int = 5,
    money: float = 500.0,
    stress: float = 30.0,
    hunger: float = 30.0,
    visa_progress: float = 60.0,
    academic_progress: float = 70.0,
    social: float = 30.0,
) -> dict:
    log = []
    for week in range(1, weeks + 1):
        log.append(
            {
                "week": week,
                "selected_action_ids": actions or ["study_library"],
                "after_state": {
                    "week": week,
                    "money": money,
                    "stress": stress,
                    "hunger": hunger,
                    "visa_progress": visa_progress,
                    "academic_progress": academic_progress,
                    "social": social,
                },
            }
        )
    return {
        "run_id": run_id,
        "policy": policy,
        "final_ending_id": ending,
        "weekly_log": log,
        "final_state": log[-1]["after_state"],
    }


def test_analyze_action_groups_flags_recovery_overpick() -> None:
    runs = [
        _make_run(
            run_id=i,
            policy="slacker",
            actions=["sleep_recover", "sleep_recover", "sleep_recover"],
        )
        for i in range(10)
    ]
    tags = {"sleep_recover": "recovery"}
    findings = analyze_action_groups(runs, tags, recovery_threshold=2.0)
    assert any(
        f.scope == "action_group" and f.target_id == "slacker:recovery"
        for f in findings
    )


def test_analyze_action_groups_flags_work_underuse() -> None:
    runs = [
        _make_run(
            run_id=i,
            policy="study",
            actions=["study_library", "study_library"],
        )
        for i in range(10)
    ]
    tags = {"study_library": "study", "mini_job": "work"}
    findings = analyze_action_groups(runs, tags)
    assert any(
        f.scope == "action_group" and f.target_id == "study:work"
        for f in findings
    )


def test_analyze_crisis_response_flags_low_money_no_work() -> None:
    runs = [
        _make_run(
            run_id=i,
            policy="balanced",
            money=100.0,  # crisis
            actions=["study_library"],  # wrong response
        )
        for i in range(5)
    ]
    tags = {"study_library": "study", "mini_job": "work", "cook_at_home": "food"}
    findings = analyze_crisis_response(runs, tags)
    assert any(
        f.scope == "crisis_response" and "low_money" in f.target_id for f in findings
    )


def test_analyze_crisis_response_passes_when_work_chosen() -> None:
    runs = [
        _make_run(
            run_id=i,
            policy="money",
            money=100.0,
            actions=["mini_job", "mini_job"],
        )
        for i in range(5)
    ]
    tags = {"mini_job": "work"}
    findings = analyze_crisis_response(runs, tags)
    assert not any("low_money" in f.target_id for f in findings)


def test_analyze_ending_contradictions_flags_broken_success() -> None:
    runs = [
        _make_run(
            policy="balanced",
            ending="academic_success",
            money=-2000,  # bad
            stress=95,
            hunger=90,
            academic_progress=10,
        )
    ]
    findings = analyze_ending_contradictions(runs)
    assert any(
        f.scope == "ending_contradiction"
        and "academic_success" in f.target_id
        for f in findings
    )


def test_analyze_route_separation_flags_close_to_balanced() -> None:
    runs = []
    # baseline balanced — 20 runs with axis values
    for i in range(20):
        runs.append(
            _make_run(
                run_id=i,
                policy="balanced",
                academic_progress=50.0,
                money=1000.0,
                social=30.0,
                visa_progress=40.0,
                stress=50.0,
            )
        )
    # study policy nearly identical to balanced
    for i in range(20, 30):
        runs.append(
            _make_run(
                run_id=i,
                policy="study",
                academic_progress=51.0,  # too close
                money=1010.0,
                social=30.5,
                visa_progress=40.5,
                stress=49.5,
            )
        )
    findings = analyze_route_separation(runs)
    assert any(f.scope == "route" and f.target_id == "study" for f in findings)


def test_analyze_route_metrics_emits_route_report(tmp_path) -> None:
    runs = [
        _make_run(
            run_id=i,
            policy="balanced",
            academic_progress=50.0,
            money=1000.0,
            social=30.0,
            visa_progress=40.0,
            stress=50.0,
        )
        for i in range(5)
    ]
    runs_path = tmp_path / "raw_runs.jsonl"
    runs_path.write_text(
        "\n".join(json.dumps(run) for run in runs) + "\n", encoding="utf-8"
    )
    report = analyze_route_metrics(
        raw_runs_path=runs_path,
        action_catalog_path=None,
    )
    assert "groups" in report
    assert "crisis_response" in report
    assert "ending_contradictions" in report
    assert "route_separation" in report
    assert "action_tags_used" in report
    # Defaults ensure study/cook at least appear in the inferred tag set.
    assert any("study" in tag for tag in report["action_tags_used"].values())


def test_analyze_and_write_creates_route_report(tmp_path) -> None:
    # Minimal CSVs so the legacy analyzer doesn't crash.
    for name in (
        "action_pick_rates.csv",
        "event_trigger_rates.csv",
        "choice_pick_rates.csv",
        "ending_distribution.csv",
    ):
        _write_csv(tmp_path / name, ["policy", "a", "b", "c"], [["balanced", "x", 0, 0]])
    # Add a tiny raw_runs.jsonl so the T06 analyzers have something to chew on.
    runs_path = tmp_path / "raw_runs.jsonl"
    runs_path.write_text(
        json.dumps(
            _make_run(
                run_id=0,
                policy="balanced",
                ending="academic_success",
                actions=["study_library", "sleep_recover"],
            )
        )
        + "\n",
        encoding="utf-8",
    )
    analyze_and_write(tmp_path)
    assert (tmp_path / "value_report.json").exists()
    assert (tmp_path / "route_report.json").exists()
