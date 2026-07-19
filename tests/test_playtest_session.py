from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from game_analysis_agent.campaign_contract import CampaignPersona
from game_analysis_agent.persona_gateway import PersonaProvider
from game_analysis_agent.playtest_session import (
    PlaytestSessionCatalog,
    describe_no_llm_session,
    describe_playtest_profiles,
    describe_session_choices,
    load_playtest_session_catalog,
    provider_for_llm_choice,
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
        "GODOT_BIN": "scripts/godot-docker-wrapper",
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


def test_initial_choices_require_godot_and_llm_before_profile() -> None:
    payload = describe_session_choices()

    assert payload["schema_version"] == "playtest-session-choices-v1"
    questions = {question["id"]: question for question in payload["questions"]}
    assert [option["id"] for option in questions["godot_runtime"]["options"]] == [
        "local-godot",
        "docker-godot",
    ]
    assert [option["id"] for option in questions["llm_provider"]["options"]] == [
        "openai-api",
        "local-vllm",
        "none",
    ]
    assert payload["rules"]["ask_before_profile"] is True
    assert provider_for_llm_choice("openai-api") == PersonaProvider.OPENAI
    assert provider_for_llm_choice("local-vllm") == PersonaProvider.VLLM
    assert provider_for_llm_choice("none") is None


def test_selected_godot_runtime_is_frozen_into_every_campaign_command() -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    local = describe_playtest_profiles(
        catalog,
        provider=PersonaProvider.VLLM,
        godot_runtime="local-godot",
        godot_bin="/opt/godot-4.4/godot4",
    )
    docker = describe_playtest_profiles(
        catalog,
        provider=PersonaProvider.OPENAI,
        godot_runtime="docker-godot",
    )

    assert local["godot_runtime"] == "local-godot"
    assert local["llm_provider"] == "local-vllm"
    assert all(
        profile["environment"]["GODOT_BIN"] == "/opt/godot-4.4/godot4"
        for profile in local["profiles"]
    )
    assert docker["godot_runtime"] == "docker-godot"
    assert docker["llm_provider"] == "openai-api"
    assert all(
        profile["environment"]["GODOT_BIN"] == "scripts/godot-docker-wrapper"
        for profile in docker["profiles"]
    )


def test_no_llm_route_has_zero_calls_and_no_persona_profiles() -> None:
    payload = describe_no_llm_session(godot_runtime="docker-godot")

    assert payload["provider"] is None
    assert payload["model_calls"] == 0
    assert payload["profiles"] == []
    assert payload["fresh_persona_evidence"] is False
    assert payload["commands"][0] == ["scripts/godot-docker-wrapper", "--version"]
    assert payload["route"] == "deterministic-automation-and-replay"


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


def test_judge_dev_preserves_user_selected_godot_over_dotenv() -> None:
    script = (ROOT / "scripts/run-judge-dev").read_text(encoding="utf-8")

    capture = script.index("gaa_selected_godot_bin=${GODOT_BIN-}")
    dotenv = script.index('. "$ROOT/.env"')
    restore = script.index("GODOT_BIN=$gaa_selected_godot_bin")
    default = script.index(': "${GODOT_BIN:=$ROOT/scripts/godot-docker-wrapper}"')

    assert capture < dotenv < restore < default


@pytest.mark.parametrize(
    ("script_name", "arguments"),
    [
        ("run-judge-dev", ("--host", "127.0.0.1")),
        ("run-persona-campaign", ("openai", "--persona", "newbie")),
    ],
)
@pytest.mark.parametrize(
    ("selected_godot", "dotenv_godot"),
    [
        ("/opt/godot-4.4/godot4", "scripts/godot-docker-wrapper"),
        ("scripts/godot-docker-wrapper", "/opt/godot-4.4/godot4"),
    ],
)
def test_runtime_entrypoints_preserve_selected_local_or_docker_godot_over_dotenv(
    tmp_path: Path,
    script_name: str,
    arguments: tuple[str, ...],
    selected_godot: str,
    dotenv_godot: str,
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    entrypoint = scripts / script_name
    shutil.copyfile(ROOT / "scripts" / script_name, entrypoint)
    entrypoint.chmod(0o755)

    game = tmp_path / "game"
    game.mkdir()
    (game / "project.godot").write_text("[application]\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        f"GODOT_BIN={dotenv_godot}\nGAME_PROJECT_PATH='{game}'\n",
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text('#!/bin/sh\nprintf "%s\\n" "$GODOT_BIN"\n', encoding="utf-8")
    fake_uv.chmod(0o755)

    result = subprocess.run(
        [str(entrypoint), *arguments],
        cwd=tmp_path,
        env={
            **os.environ,
            "GODOT_BIN": selected_godot,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        },
        check=True,
        capture_output=True,
        text=True,
    )

    expected = (
        str(tmp_path / selected_godot) if selected_godot.startswith("scripts/") else selected_godot
    )
    assert result.stdout.strip() == expected
