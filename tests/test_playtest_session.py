from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from game_analysis_agent.campaign_contract import CampaignPersona
from game_analysis_agent.persona_gateway import PersonaProvider
from game_analysis_agent.playtest_session import (
    PlaytestSessionCatalog,
    describe_playtest_profiles,
    load_playtest_session_catalog,
)

ROOT = Path(__file__).resolve().parents[1]


def test_committed_profiles_freeze_full_semester_order_and_budgets() -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    payload = describe_playtest_profiles(
        catalog,
        provider=PersonaProvider.VLLM,
        single_persona=CampaignPersona.STUDY,
    )

    assert payload["recommended_order"] == [
        "one-strategy",
        "six-strategy",
        "repair-evidence",
    ]
    profiles = {profile["id"]: profile for profile in payload["profiles"]}
    assert profiles["one-strategy"]["personas"] == ["study"]
    assert profiles["one-strategy"]["cell_count"] == 1
    assert profiles["one-strategy"]["worst_case_calls"] == 40
    assert profiles["six-strategy"]["cell_count"] == 6
    assert profiles["six-strategy"]["worst_case_calls"] == 240
    assert profiles["repair-evidence"]["cell_count"] == 18
    assert profiles["repair-evidence"]["worst_case_calls"] == 720
    assert profiles["repair-evidence"]["repair_decision_ready"] is True
    assert all(profile["max_weeks"] == 20 for profile in profiles.values())


def test_profile_command_preserves_provider_and_every_matrix_axis() -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    payload = describe_playtest_profiles(catalog, provider=PersonaProvider.OPENAI)
    evidence = next(
        profile for profile in payload["profiles"] if profile["id"] == "repair-evidence"
    )

    assert evidence["command"][:2] == ["scripts/run-persona-campaign", "openai"]
    assert evidence["command"].count("--persona") == 6
    assert evidence["command"].count("--seed") == 3
    assert evidence["environment"] == {
        "PERSONA_MAX_RUNS": "18",
        "PERSONA_MAX_WEEKS": "20",
        "PERSONA_MAX_CONCURRENCY": "4",
        "PERSONA_MAX_CALLS": "760",
    }
    assert "OPENAI_API_KEY" not in evidence["shell_preview"]


def test_local_and_api_profiles_share_the_same_campaign_shape() -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    local = describe_playtest_profiles(catalog, provider=PersonaProvider.VLLM)
    api = describe_playtest_profiles(catalog, provider=PersonaProvider.OPENAI)

    for local_profile, api_profile in zip(local["profiles"], api["profiles"], strict=True):
        assert local_profile["id"] == api_profile["id"]
        assert local_profile["personas"] == api_profile["personas"]
        assert local_profile["seeds"] == api_profile["seeds"]
        assert local_profile["environment"] == api_profile["environment"]
        assert local_profile["command"][0] == api_profile["command"][0]
        assert local_profile["command"][2:] == api_profile["command"][2:]
        assert local_profile["command"][1] == "vllm"
        assert api_profile["command"][1] == "openai"


def test_profile_rejects_a_call_budget_below_worst_case() -> None:
    with pytest.raises(ValidationError, match="worst case"):
        PlaytestSessionCatalog.model_validate(
            {
                "schema_version": "playtest-session-profiles-v1",
                "profiles": [
                    {
                        "id": f"profile-{index}",
                        "label": "Invalid",
                        "stage": "pipeline",
                        "description": "Invalid budget",
                        "personas": ["newbie"],
                        "allow_persona_override": True,
                        "seeds": [42],
                        "max_weeks": 20,
                        "concurrency": 1,
                        "max_calls": 39,
                        "repair_target_eligible": False,
                        "repair_decision_ready": False,
                    }
                    for index in range(3)
                ],
            }
        )
