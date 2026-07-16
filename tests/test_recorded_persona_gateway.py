"""Tests for exact, hash-pinned Replay persona decisions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from game_analysis_agent.persona_gateway import (
    PersonaDecisionRequest,
    PersonaErrorCategory,
    PersonaEventChoiceRequest,
    PersonaProvider,
    PersonaProviderMode,
    PersonaResultStatus,
)
from game_analysis_agent.recorded_persona_gateway import (
    RecordedPersonaGateway,
    ReplayFixtureError,
)
from game_analysis_agent.schemas import WeekContext

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/build_week_2026_replay.json"


def _context(*, persona: str = "newbie", money: int = 420) -> WeekContext:
    return WeekContext.model_validate(
        {
            "game_version": "test",
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "persona": persona,
            "state": {"week": 1, "money": money, "stress": 55},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
                "contract_version": "1.0",
            },
            "available_actions": [
                {"id": "budget_call", "name": "Budget call"},
                {"id": "rest_at_home", "name": "Rest"},
            ],
            "current_event_id": "rent_pressure",
            "event_choices": [
                {"choice_id": "rent_pressure.pay_now", "text": "Pay now"},
                {
                    "choice_id": "rent_pressure.ask_extension",
                    "text": "Ask extension",
                },
            ],
            "memory": {"persona": persona},
        }
    )


def _gateway() -> RecordedPersonaGateway:
    return RecordedPersonaGateway.from_manifest(MANIFEST, project_root=ROOT)


def test_exact_decision_and_event_lookup_are_explicit_replay() -> None:
    gateway = _gateway()
    context = _context()
    decision = gateway.decide(
        PersonaDecisionRequest.from_context(
            context, request_id="newbie-42-w1-decision"
        )
    )
    event = gateway.choose_event(
        PersonaEventChoiceRequest.from_context(
            context,
            request_id="newbie-42-w1-event",
            selected_actions=["budget_call"],
        )
    )

    assert decision.status == PersonaResultStatus.COMPLETED
    assert decision.decision is not None
    assert decision.decision.actions == ["budget_call"]
    assert event.choice is not None
    assert event.choice.event_choice_id == "rent_pressure.ask_extension"
    assert decision.metadata.provider == PersonaProvider.REPLAY
    assert decision.metadata.mode == PersonaProviderMode.REPLAY


def test_replay_entry_is_single_use_and_exhausts() -> None:
    gateway = _gateway()
    request = PersonaDecisionRequest.from_context(
        _context(), request_id="newbie-42-w1-decision"
    )
    assert gateway.decide(request).status == PersonaResultStatus.COMPLETED
    exhausted = gateway.decide(request)

    assert exhausted.status == PersonaResultStatus.FAILED
    assert exhausted.error is not None
    assert exhausted.error.category == PersonaErrorCategory.FIXTURE_MISMATCH
    assert "exhausted" in exhausted.error.message


@pytest.mark.parametrize(
    "context",
    [_context(money=421), _context(persona="study")],
    ids=["state-mismatch", "cross-persona"],
)
def test_replay_never_uses_nearby_or_cross_persona_entry(context: WeekContext) -> None:
    result = _gateway().decide(
        PersonaDecisionRequest.from_context(
            context, request_id="newbie-42-w1-decision"
        )
    )

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.FIXTURE_MISMATCH


def test_corrupted_fixture_hash_is_rejected_before_read(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text('{"schema_version":"persona-replay-fixture-v1","entries":[]}')

    with pytest.raises(ReplayFixtureError, match="hash mismatch"):
        RecordedPersonaGateway(fixture, expected_sha256="0" * 64)


def test_partial_fixture_is_rejected(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "schema_version": "persona-replay-fixture-v1",
                "entries": [{"entry_id": "partial", "kind": "decision"}],
            }
        ),
        encoding="utf-8",
    )
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()

    with pytest.raises(ReplayFixtureError, match="missing fingerprint"):
        RecordedPersonaGateway(fixture, expected_sha256=digest)
