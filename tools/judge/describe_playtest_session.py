#!/usr/bin/env python3
"""Print the frozen Codex-guided playtest menu without starting a model call."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.campaign_contract import CampaignPersona  # noqa: E402
from game_analysis_agent.persona_gateway import PersonaProvider  # noqa: E402
from game_analysis_agent.playtest_session import (  # noqa: E402
    GAME_DIFFICULTIES,
    describe_no_llm_session,
    describe_playtest_profiles,
    describe_session_choices,
    load_playtest_session_catalog,
    provider_for_llm_choice,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    provider_group = parser.add_mutually_exclusive_group()
    provider_group.add_argument(
        "--provider",
        choices=("vllm", "sglang", "openai", "deepseek"),
        help="advanced/backward-compatible provider name",
    )
    provider_group.add_argument(
        "--llm-provider",
        choices=("local-sglang", "local-vllm", "openai-api", "none"),
        help="primary interactive LLM choice",
    )
    parser.add_argument(
        "--difficulty",
        choices=GAME_DIFFICULTIES,
        help="difficulty frozen across automation, persona evidence, and repair",
    )
    parser.add_argument(
        "--godot-runtime",
        choices=("local-godot", "docker-godot"),
        default="docker-godot",
    )
    parser.add_argument(
        "--godot-bin",
        help="resolved local Godot 4.4 executable; normally set after readiness probing",
    )
    parser.add_argument("--choices-only", action="store_true")
    parser.add_argument(
        "--persona",
        choices=tuple(persona.value for persona in CampaignPersona),
        default="newbie",
        help="strategy used by the one-strategy profile",
    )
    parser.add_argument("--profile", choices=("one-strategy", "six-strategy", "repair-evidence"))
    parser.add_argument(
        "--generation-profile",
        help="local generation profile from config/playtest_session_profiles.json",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    selected_difficulty = args.difficulty or catalog.defaults.difficulty
    if args.choices_only:
        payload = describe_session_choices(catalog)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for question in payload["questions"]:
                print(f"\n{question['prompt']}")
                for option in question["options"]:
                    print(f"  {option['id']}: {option['description']}")
        return 0

    selected_llm_provider = args.llm_provider or (
        None if args.provider else catalog.defaults.llm_provider
    )
    if selected_llm_provider == "none":
        if args.profile:
            build_parser().error("--profile is unavailable when --llm-provider none")
        payload = describe_no_llm_session(
            godot_runtime=args.godot_runtime,
            difficulty=selected_difficulty,
            godot_bin=args.godot_bin,
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("LLM: none")
            print("Route: deterministic automation and committed Replay")
            for command in payload["commands"]:
                print(f"  {shlex.join(command)}")
        return 0

    provider = (
        provider_for_llm_choice(selected_llm_provider)
        if selected_llm_provider
        else PersonaProvider(args.provider or "sglang")
    )
    assert provider is not None
    if args.generation_profile and provider not in {
        PersonaProvider.SGLANG,
        PersonaProvider.VLLM,
    }:
        build_parser().error(
            "--generation-profile is only available for local SGLang or vLLM"
        )
    selected_profile = args.profile or catalog.defaults.campaign_profile
    selected_generation_profile = args.generation_profile
    if (
        selected_generation_profile is None
        and provider in {PersonaProvider.SGLANG, PersonaProvider.VLLM}
    ):
        selected_generation_profile = catalog.defaults.generation_profile
    try:
        generation_profile = (
            catalog.get_generation_profile(selected_generation_profile)
            if selected_generation_profile
            else None
        )
    except ValueError as exc:
        build_parser().error(str(exc))
    payload = describe_playtest_profiles(
        catalog,
        provider=provider,
        single_persona=CampaignPersona(args.persona),
        godot_runtime=args.godot_runtime,
        difficulty=selected_difficulty,
        godot_bin=args.godot_bin,
        generation_profile=generation_profile,
    )
    payload["defaults"] = catalog.defaults.model_dump(mode="json")
    payload["profiles"] = [
        profile for profile in payload["profiles"] if profile["id"] == selected_profile
    ]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Godot: {payload['godot_runtime']} ({payload['godot_bin']})")
        print(f"Difficulty: {payload['difficulty']} ({payload['difficulty_lane']})")
        print(f"LLM: {payload['llm_provider']} ({payload['provider']})")
        if payload["generation_profile_selection_required"]:
            print("Generation profile: choose one before execution")
            for generation in payload["generation_profiles"]:
                print(f"  {generation['id']}: {generation['description']}")
        elif payload["generation_profile"]:
            print(f"Generation profile: {payload['generation_profile']['id']}")
        for profile in payload["profiles"]:
            print(
                f"\n{profile['id']}: {profile['label']}\n"
                f"  {profile['description']}\n"
                f"  cells={profile['cell_count']} weeks={profile['max_weeks']} "
                f"max_calls={profile['max_calls']}\n"
                f"  {profile['shell_preview']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
