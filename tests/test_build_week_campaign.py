"""Canonical campaign source, executor selection, and target freeze tests."""

from __future__ import annotations

from game_analysis_agent.build_week_campaign import (
    FrozenRepairTarget,
    TargetSelectionError,
    select_repair_target,
)
from game_analysis_agent.campaign_aggregation import (
    CampaignAggregateMetrics,
    CampaignAggregation,
    FailureCluster,
    FailureRule,
)
from game_analysis_agent.campaign_contract import CampaignCitation, CampaignRequest


def _citation(persona: str, seed: int, week: int) -> CampaignCitation:
    return CampaignCitation.model_validate(
        {
            "campaign_id": "target-test-v1",
            "cell_id": f"{persona}-seed-{seed}-abc",
            "persona": persona,
            "seed": seed,
            "week": week,
            "artifact_path": f"reports/{persona}-{seed}/playthrough.jsonl",
            "line_number": week,
            "record_sha256": str(seed)[:1] * 64,
        }
    )


def _cluster(cluster_id: str, members: list[CampaignCitation]) -> FailureCluster:
    return FailureCluster(
        cluster_id=cluster_id,
        label=cluster_id.replace("-", " ").title(),
        rule=FailureRule(
            cluster_id=cluster_id,
            label=cluster_id,
            stress_gte=80,
            consecutive_weeks=2,
        ),
        member_count=len(members),
        cell_rate=len(members) / 3,
        persona_counts={item.persona.value: 1 for item in members},
        members=tuple(members),
        representatives=tuple(members[:3]),
    )


def _request() -> CampaignRequest:
    return CampaignRequest.model_validate(
        {
            "campaign_id": "target-test-v1",
            "personas": ["newbie", "study", "money"],
            "seeds": [42, 43, 44],
            "max_weeks": 20,
            "provider": "replay",
        }
    )


def _aggregation(*clusters: FailureCluster) -> CampaignAggregation:
    return CampaignAggregation(
        campaign_id="target-test-v1",
        request_fingerprint="a" * 64,
        source_fingerprint="b" * 64,
        rules_fingerprint="c" * 64,
        metrics=CampaignAggregateMetrics(
            expected_cells=3,
            completed_cells=3,
            partial_cells=0,
            failed_cells=0,
            cancelled_cells=0,
            total_weeks=60,
        ),
        cells=(),
        clusters=clusters,
    )


def test_target_prefers_cross_persona_cashflow_cluster_and_freezes_holdouts() -> None:
    burnout = _cluster(
        "burnout-risk", [_citation("study", 42, 4), _citation("money", 43, 5)]
    )
    cashflow = _cluster(
        "cashflow-stress-attractor",
        [_citation("newbie", 42, 8), _citation("money", 44, 9)],
    )

    target = select_repair_target(
        request=_request(), aggregation=_aggregation(burnout, cashflow)
    )
    reparsed = FrozenRepairTarget.model_validate_json(target.model_dump_json())

    assert reparsed.selected_cluster_id == "cashflow-stress-attractor"
    assert reparsed.fixed_seeds == (42, 43, 44)
    assert reparsed.holdout_seeds == (1042, 1043, 1044)
    assert set(reparsed.fixed_seeds).isdisjoint(reparsed.holdout_seeds)
    assert reparsed.evidence_bundle == "examples/build_week_2026/campaign-v1"
    assert len({item.persona for item in reparsed.evidence}) == 2


def test_target_selection_fails_closed_without_cross_persona_observation() -> None:
    weak = _cluster("burnout-risk", [_citation("study", 42, 4)])

    try:
        select_repair_target(request=_request(), aggregation=_aggregation(weak))
    except TargetSelectionError as exc:
        assert "two runs and two personas" in str(exc)
    else:
        raise AssertionError("weak evidence must not select a repair target")
