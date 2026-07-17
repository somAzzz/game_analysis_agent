#!/usr/bin/env python3
"""Run a full-semester local or live persona campaign and publish its UI view."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.campaign_contract import (  # noqa: E402
    CampaignPersona,
    CampaignRequest,
)
from game_analysis_agent.persona_campaign_service import (  # noqa: E402
    PersonaCampaignServiceError,
    run_persona_campaign,
)
from game_analysis_agent.persona_gateway import PersonaProvider  # noqa: E402
from game_analysis_agent.persona_runtime import redact_sensitive_text  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        required=True,
        choices=("openai", "vllm", "sglang", "deepseek"),
    )
    parser.add_argument("--campaign-id")
    parser.add_argument(
        "--persona",
        action="append",
        choices=tuple(item.value for item in CampaignPersona),
    )
    parser.add_argument("--seed", action="append", type=int)
    parser.add_argument("--max-weeks", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--report-root", default="reports/persona-campaigns")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument(
        "--view",
        type=Path,
        default=Path("frontend/public/live-playthrough"),
    )
    parser.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    personas = tuple(CampaignPersona(item) for item in (args.persona or ["newbie"]))
    seeds = tuple(args.seed or [42])
    campaign_id = args.campaign_id or _default_campaign_id(
        args.provider, personas, seeds, args.max_weeks
    )
    game_root = args.game_root or Path(os.environ.get("GAME_PROJECT_PATH", ""))
    if not str(game_root):
        print("--game-root or GAME_PROJECT_PATH is required", file=sys.stderr)
        return 2
    report_root = str(args.report_root).strip("/")
    request = CampaignRequest(
        campaign_id=campaign_id,
        personas=personas,
        seeds=seeds,
        max_weeks=args.max_weeks,
        provider=PersonaProvider(args.provider),
        concurrency=args.concurrency,
        report_root=report_root,
    )
    bundle = args.bundle or Path(report_root) / campaign_id / "public"
    try:
        result = run_persona_campaign(
            project_root=ROOT,
            game_root=game_root,
            request=request,
            bundle_dir=bundle,
            view_dir=args.view,
            environment=os.environ,
            resume=not args.no_resume,
        )
    except Exception as exc:
        safe_message = redact_sensitive_text(str(exc))
        if isinstance(exc, PersonaCampaignServiceError):
            kind = "campaign preflight"
        else:
            kind = exc.__class__.__name__
        print(f"{kind} error: {safe_message}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _default_campaign_id(
    provider: str,
    personas: tuple[CampaignPersona, ...],
    seeds: tuple[int, ...],
    max_weeks: int,
) -> str:
    persona_part = "all-six" if len(personas) == 6 else "-".join(item.value for item in personas)
    seed_part = "-".join(str(seed) for seed in seeds)
    return f"{provider}-{persona_part}-seed-{seed_part}-{max_weeks}w"


if __name__ == "__main__":
    raise SystemExit(main())
