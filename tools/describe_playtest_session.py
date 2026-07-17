#!/usr/bin/env python3
"""Print the frozen Codex-guided playtest menu without starting a model call."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.campaign_contract import CampaignPersona  # noqa: E402
from game_analysis_agent.persona_gateway import PersonaProvider  # noqa: E402
from game_analysis_agent.playtest_session import (  # noqa: E402
    describe_playtest_profiles,
    load_playtest_session_catalog,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=("vllm", "sglang", "openai", "deepseek"),
        default="vllm",
    )
    parser.add_argument(
        "--persona",
        choices=tuple(persona.value for persona in CampaignPersona),
        default="newbie",
        help="strategy used by the one-strategy profile",
    )
    parser.add_argument("--profile", choices=("one-strategy", "six-strategy", "repair-evidence"))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = load_playtest_session_catalog(ROOT / "config/playtest_session_profiles.json")
    payload = describe_playtest_profiles(
        catalog,
        provider=PersonaProvider(args.provider),
        single_persona=CampaignPersona(args.persona),
    )
    if args.profile:
        payload["profiles"] = [
            profile for profile in payload["profiles"] if profile["id"] == args.profile
        ]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Provider: {payload['provider']}")
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
