"""Authoring-only deterministic Replay fixture tests."""

from __future__ import annotations

from game_analysis_agent.persona_fixture_authoring import FixtureAuthoringGateway
from game_analysis_agent.persona_gateway import (
    PersonaDecisionRequest,
    PersonaEventChoiceRequest,
    PersonaResultStatus,
)
from game_analysis_agent.recorded_persona_gateway import RecordedPersonaGateway
from game_analysis_agent.schemas import WeekContext


def _context(*, with_event: bool = True) -> WeekContext:
    return WeekContext.model_validate(
        {
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "persona": "study",
            "state": {"week": 1, "money": 100, "stress": 50},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
            },
            "top_risks": [
                {
                    "id": "money",
                    "severity": "high",
                    "reason": "low cash",
                    "suggested_action_ids": ["part_time_job"],
                }
            ],
            "available_actions": [
                {"id": "study_library", "type": "study", "tags": ["study"]},
                {"id": "part_time_job", "type": "work", "tags": ["work"]},
                {"id": "rest_at_home", "type": "recovery", "tags": ["recovery"]},
            ],
            "current_event_id": "rent" if with_event else "",
            "event_choices": (
                [{"choice_id": "rent.pay"}, {"choice_id": "rent.delay"}]
                if with_event
                else []
            ),
            "memory": {"persona": "study"},
        }
    )


def test_authored_fixture_round_trips_through_exact_recorded_gateway(tmp_path) -> None:
    author = FixtureAuthoringGateway()
    context = _context(with_event=False)
    event_context = _context()
    decision_request = PersonaDecisionRequest.from_context(
        context, request_id="study-42-w1-decision"
    )
    event_request = PersonaEventChoiceRequest.from_context(
        event_context,
        request_id="study-42-w1-event",
        selected_actions=["part_time_job", "study_library"],
    )
    authored_decision = author.decide(decision_request)
    authored_event = author.choose_event(event_request)
    fixture, manifest, _digest = author.write(
        project_root=tmp_path,
        fixture_path="fixtures/full.json",
        manifest_path="config/manifest.json",
        fixture_id="test-v1",
    )

    replay = RecordedPersonaGateway.from_manifest(manifest, project_root=tmp_path)
    replay_decision = replay.decide(decision_request)
    replay_event = replay.choose_event(event_request)

    assert fixture.is_file()
    assert authored_decision.status == PersonaResultStatus.COMPLETED
    assert replay_decision.decision == authored_decision.decision
    assert replay_event.choice == authored_event.choice
    assert replay_decision.metadata.model == "recorded-fixture"


def test_authoring_is_deterministic_across_instances() -> None:
    context = _context()
    request = PersonaDecisionRequest.from_context(
        context, request_id="study-42-w1-decision"
    )
    first = FixtureAuthoringGateway()
    second = FixtureAuthoringGateway()

    assert first.decide(request).decision == second.decide(request).decision
    assert first.fixture_payload(fixture_id="same") == second.fixture_payload(
        fixture_id="same"
    )
