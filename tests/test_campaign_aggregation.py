"""Deterministic metric and citation-backed cluster tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent.campaign_aggregation import (
    CampaignAggregationError,
    aggregate_campaign,
    load_failure_rules,
)
from game_analysis_agent.campaign_contract import (
    CampaignCellState,
    CampaignRequest,
    CampaignSourceIdentity,
)
from game_analysis_agent.campaign_runner import CampaignRunner, CellExecutionOutcome

ROOT = Path(__file__).resolve().parents[1]


def _request() -> CampaignRequest:
    return CampaignRequest(
        campaign_id="aggregation-test-v1",
        personas=("newbie", "study"),
        seeds=(42,),
        max_weeks=3,
        provider="replay",
        concurrency=2,
        report_root="reports/campaigns",
    )


def _source() -> CampaignSourceIdentity:
    return CampaignSourceIdentity(
        agent_commit="a" * 40,
        agent_tree="b" * 40,
        game_commit="c" * 40,
        game_tree="d" * 40,
        game_archive_sha256="e" * 64,
        campaign_config_sha256="f" * 64,
        provider="replay",
        provider_mode="replay",
        provider_revision="fixture:test",
    )


def _executor(request, output_dir, context):  # noqa: ANN001
    del context
    rows = []
    for week, (money, stress) in enumerate([(100, 40), (0, 85), (-10, 92)], start=1):
        fallback = request.persona.value == "newbie" and week == 3
        rows.append(
            {
                "week": week,
                "state_after": {
                    "money": money if request.persona.value == "newbie" else money + 50,
                    "stress": stress,
                },
                "chosen_actions": ["study_library"],
                "validation": {"valid": not fallback, "fallback_used": fallback},
                "persona_calls": [{"status": "failed" if fallback else "completed"}],
                "week_context": {
                    "persona_strategy": {"alignment_action_tags": ["study"]},
                    "available_actions": [
                        {"id": "study_library", "tags": ["study"], "risk_tags": []}
                    ],
                },
                "result": {"final_ending": "semester_complete" if week == 3 else ""},
            }
        )
    (output_dir / "playthrough.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return CellExecutionOutcome(
        state=CampaignCellState.COMPLETED,
        stop_reason="week_limit",
        completed_weeks=3,
    )


def _run(tmp_path: Path):  # noqa: ANN202
    return (
        CampaignRunner(
            project_root=tmp_path,
            request=_request(),
            source=_source(),
            executor=_executor,
        )
        .run()
        .results
    )


def test_aggregation_recomputes_metrics_and_first_attractor_entry(tmp_path: Path) -> None:
    rules = load_failure_rules(ROOT / "config/build_week_2026_failure_rules.json")

    aggregate = aggregate_campaign(project_root=tmp_path, results=_run(tmp_path), rules=rules)

    assert aggregate.metrics.expected_cells == 2
    assert aggregate.metrics.completed_cells == 2
    assert aggregate.metrics.total_weeks == 6
    assert aggregate.metrics.valid_rate == pytest.approx(5 / 6, abs=1e-6)
    assert aggregate.metrics.fallback_rate == pytest.approx(1 / 6, abs=1e-6)
    assert aggregate.metrics.persona_alignment_rate == 1.0
    attractor = next(
        item for item in aggregate.clusters if item.cluster_id == "cashflow-stress-attractor"
    )
    assert attractor.member_count == 1
    assert attractor.members[0].persona.value == "newbie"
    assert attractor.members[0].week == 2
    assert attractor.representatives == attractor.members


def test_aggregation_is_byte_deterministic_for_same_rows(tmp_path: Path) -> None:
    rules = load_failure_rules(ROOT / "config/build_week_2026_failure_rules.json")
    results = _run(tmp_path)

    first = aggregate_campaign(project_root=tmp_path, results=results, rules=rules)
    second = aggregate_campaign(project_root=tmp_path, results=results, rules=rules)

    assert first.model_dump_json() == second.model_dump_json()


def test_aggregation_rejects_row_changed_after_citation(tmp_path: Path) -> None:
    rules = load_failure_rules(ROOT / "config/build_week_2026_failure_rules.json")
    results = _run(tmp_path)
    path = tmp_path / results[0].request.output_dir / "playthrough.jsonl"
    text = path.read_text(encoding="utf-8").replace('"money": 100', '"money": 101', 1)
    path.write_text(text, encoding="utf-8")

    with pytest.raises(CampaignAggregationError, match="citation hash mismatch"):
        aggregate_campaign(project_root=tmp_path, results=results, rules=rules)


def test_aggregation_rejects_completed_cell_with_unknown_ending(tmp_path: Path) -> None:
    request = _request()

    def unknown_ending_executor(cell, output_dir, context):  # noqa: ANN001, ANN202
        outcome = _executor(cell, output_dir, context)
        trace = output_dir / "playthrough.jsonl"
        rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        rows[-1]["result"]["final_ending"] = "unknown"
        trace.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
            encoding="utf-8",
        )
        return outcome

    results = (
        CampaignRunner(
            project_root=tmp_path,
            request=request,
            source=_source(),
            executor=unknown_ending_executor,
        )
        .run()
        .results
    )
    rules = load_failure_rules(ROOT / "config/build_week_2026_failure_rules.json")

    with pytest.raises(CampaignAggregationError, match="no structured ending"):
        aggregate_campaign(project_root=tmp_path, results=results, rules=rules)
