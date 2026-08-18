from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from game_analysis_agent.campaign_contract import CampaignPersona
from game_analysis_agent.persona_gateway import PersonaProvider
from game_analysis_agent.playtest_session import (
    GAME_DIFFICULTIES,
    PlaytestSessionCatalog,
    describe_no_llm_session,
    describe_playtest_profiles,
    describe_session_choices,
    load_playtest_session_catalog,
    provider_for_llm_choice,
)

ROOT = Path(__file__).resolve().parents[2]


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
    assert catalog.defaults.model_dump(mode="json") == {
        "godot_runtime": "docker-godot",
        "llm_provider": "local-sglang",
        "generation_profile": "no-thinking-2048",
        "campaign_profile": "six-strategy",
        "difficulty": "normal",
    }
    assert [profile.id for profile in catalog.generation_profiles] == [
        "no-thinking-2048",
        "thinking-5120",
    ]
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
    assert evidence["command"][evidence["command"].index("--difficulty") + 1] == "normal"
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
    sglang = describe_playtest_profiles(catalog, provider=PersonaProvider.SGLANG)
    vllm = describe_playtest_profiles(catalog, provider=PersonaProvider.VLLM)
    api = describe_playtest_profiles(catalog, provider=PersonaProvider.OPENAI)

    for sglang_profile, vllm_profile, api_profile in zip(
        sglang["profiles"], vllm["profiles"], api["profiles"], strict=True
    ):
        assert sglang_profile["id"] == vllm_profile["id"] == api_profile["id"]
        assert sglang_profile["personas"] == vllm_profile["personas"] == api_profile["personas"]
        assert sglang_profile["seeds"] == vllm_profile["seeds"] == api_profile["seeds"]
        assert sglang_profile["environment"] == vllm_profile["environment"]
        assert vllm_profile["environment"] == api_profile["environment"]
        assert sglang_profile["command"][0] == api_profile["command"][0]
        assert sglang_profile["command"][2:] == api_profile["command"][2:]
        assert sglang_profile["command"][1] == "sglang"
        assert vllm_profile["command"][1] == "vllm"
        assert api_profile["command"][1] == "openai"


def test_initial_choices_expose_frozen_defaults_and_allow_overrides() -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    payload = describe_session_choices(catalog)

    assert payload["schema_version"] == "playtest-session-choices-v1"
    questions = {question["id"]: question for question in payload["questions"]}
    assert questions["difficulty"]["default"] == "normal"
    assert [option["id"] for option in questions["difficulty"]["options"]] == list(
        GAME_DIFFICULTIES
    )
    assert [option["id"] for option in questions["godot_runtime"]["options"]] == [
        "local-godot",
        "docker-godot",
    ]
    assert [option["id"] for option in questions["llm_provider"]["options"]] == [
        "local-sglang",
        "local-vllm",
        "openai-api",
        "none",
    ]
    assert payload["defaults"] == catalog.defaults.model_dump(mode="json")
    assert payload["rules"]["ask_before_profile"] is False
    assert payload["rules"]["apply_defaults_without_prompt"] is True
    assert payload["rules"]["explicit_overrides_win"] is True
    assert provider_for_llm_choice("local-sglang") == PersonaProvider.SGLANG
    assert provider_for_llm_choice("openai-api") == PersonaProvider.OPENAI
    assert provider_for_llm_choice("local-vllm") == PersonaProvider.VLLM
    assert provider_for_llm_choice("none") is None


def test_planner_cli_defaults_to_docker_sglang_no_thinking_six_strategy() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/judge/describe_playtest_session.py"), "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["godot_runtime"] == "docker-godot"
    assert payload["llm_provider"] == "local-sglang"
    assert payload["generation_profile"]["id"] == "no-thinking-2048"
    assert payload["difficulty"] == "normal"
    assert payload["difficulty_lane"] == "config/matrix.normal.yaml"
    assert [profile["id"] for profile in payload["profiles"]] == ["six-strategy"]
    profile = payload["profiles"][0]
    assert profile["personas"] == ["newbie", "study", "money", "social", "visa", "slacker"]
    assert profile["environment"]["GODOT_BIN"] == "scripts/godot-docker-wrapper"
    assert profile["environment"]["PERSONA_ENABLE_THINKING"] == "0"
    assert profile["environment"]["PERSONA_DECISION_MAX_TOKENS"] == "2048"


def test_sglang_choice_emits_sglang_campaign_and_truthful_menu_label() -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    provider = provider_for_llm_choice("local-sglang")
    assert provider is not None
    payload = describe_playtest_profiles(
        catalog,
        provider=provider,
        godot_runtime="docker-godot",
    )

    assert payload["llm_provider"] == "local-sglang"
    assert payload["provider"] == "sglang"
    assert all(profile["command"][1] == "sglang" for profile in payload["profiles"])
    assert payload["generation_profile_selection_required"] is True
    assert [profile["id"] for profile in payload["generation_profiles"]] == [
        "no-thinking-2048",
        "thinking-5120",
    ]


@pytest.mark.parametrize(
    ("profile_id", "thinking", "max_tokens"),
    [("thinking-5120", "1", "5120"), ("no-thinking-2048", "0", "2048")],
)
def test_selected_generation_profile_freezes_both_environment_values(
    profile_id: str,
    thinking: str,
    max_tokens: str,
) -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    payload = describe_playtest_profiles(
        catalog,
        provider=PersonaProvider.SGLANG,
        generation_profile=catalog.get_generation_profile(profile_id),
    )

    assert payload["generation_profile_selection_required"] is False
    assert payload["generation_profile"]["id"] == profile_id
    for profile in payload["profiles"]:
        assert profile["command"][2:4] == [
            "--campaign-id",
            f"sglang-normal-{profile['id']}-{profile_id}",
        ]
        assert profile["environment"]["PERSONA_ENABLE_THINKING"] == thinking
        assert profile["environment"]["PERSONA_DECISION_MAX_TOKENS"] == max_tokens
        assert f"PERSONA_ENABLE_THINKING={thinking}" in profile["shell_preview"]
        assert f"PERSONA_DECISION_MAX_TOKENS={max_tokens}" in profile["shell_preview"]


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
    assert payload["commands"][1][6] == "config/matrix.normal.yaml"
    assert payload["route"] == "deterministic-automation-and-replay"


@pytest.mark.parametrize("difficulty", GAME_DIFFICULTIES)
def test_selected_difficulty_freezes_matrix_and_persona_campaign(difficulty: str) -> None:
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    payload = describe_playtest_profiles(
        catalog,
        provider=PersonaProvider.OPENAI,
        difficulty=difficulty,
    )

    assert payload["difficulty"] == difficulty
    assert payload["difficulty_lane"] == f"config/matrix.{difficulty}.yaml"
    for profile in payload["profiles"]:
        index = profile["command"].index("--difficulty")
        assert profile["command"][index + 1] == difficulty
        assert profile["difficulty"] == difficulty

    no_llm = describe_no_llm_session(
        godot_runtime="docker-godot",
        difficulty=difficulty,
    )
    assert no_llm["difficulty_lane"] == f"config/matrix.{difficulty}.yaml"
    assert f"config/matrix.{difficulty}.yaml" in no_llm["commands"][1]


def test_profile_rejects_a_call_budget_below_worst_case() -> None:
    with pytest.raises(ValidationError, match="worst case"):
        PlaytestSessionCatalog.model_validate(
            {
                "schema_version": "playtest-session-profiles-v4",
                "defaults": {
                    "godot_runtime": "docker-godot",
                    "llm_provider": "local-sglang",
                    "generation_profile": "thinking-5120",
                    "campaign_profile": "profile-0",
                    "difficulty": "normal",
                },
                "generation_profiles": [
                    {
                        "id": "thinking-5120",
                        "label": "Thinking",
                        "description": "Thinking profile",
                        "enable_thinking": True,
                        "decision_max_tokens": 5120,
                    },
                    {
                        "id": "no-thinking-2048",
                        "label": "No thinking",
                        "description": "No-thinking profile",
                        "enable_thinking": False,
                        "decision_max_tokens": 2048,
                    },
                ],
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


@pytest.mark.parametrize(
    ("selected_thinking", "selected_tokens", "dotenv_thinking", "dotenv_tokens"),
    [("1", "5120", "0", "2048"), ("0", "2048", "1", "5120")],
)
def test_campaign_entrypoint_preserves_selected_generation_profile_over_dotenv(
    tmp_path: Path,
    selected_thinking: str,
    selected_tokens: str,
    dotenv_thinking: str,
    dotenv_tokens: str,
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    entrypoint = scripts / "run-persona-campaign"
    shutil.copyfile(ROOT / "scripts/run-persona-campaign", entrypoint)
    entrypoint.chmod(0o755)

    game = tmp_path / "game"
    game.mkdir()
    (game / "project.godot").write_text("[application]\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                f"GAME_PROJECT_PATH='{game}'",
                f"PERSONA_ENABLE_THINKING={dotenv_thinking}",
                f"PERSONA_DECISION_MAX_TOKENS={dotenv_tokens}",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        '#!/bin/sh\nprintf "%s,%s\\n" "$PERSONA_ENABLE_THINKING" '
        '"$PERSONA_DECISION_MAX_TOKENS"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)

    result = subprocess.run(
        [str(entrypoint), "sglang", "--persona", "newbie"],
        cwd=tmp_path,
        env={
            **os.environ,
            "PERSONA_ENABLE_THINKING": selected_thinking,
            "PERSONA_DECISION_MAX_TOKENS": selected_tokens,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        },
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == f"{selected_thinking},{selected_tokens}"
