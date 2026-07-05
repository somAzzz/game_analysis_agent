#!/usr/bin/env python3
"""CLI: run one analysis agent against a prepared report directory.

This script is a thin front-end. Each agent is selected via its slug
(``balance``, ``content_qa``, ``event_graph``, ``bug_hunter``,
``boundary_prober``, ``value_reviewer``). The output files are written
into ``<report_dir>`` exactly like the previous version so callers that
``grep`` for them keep working.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.agents import (
    AGENT_NAMES,
    AgentRunResult,
    build_agent,
    write_agent_result,
)
from game_analysis_agent.env import load_dotenv
from game_analysis_agent.llm_client import LocalLLMClient
from game_analysis_agent.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one analysis agent against a report directory."
    )
    parser.add_argument(
        "agent",
        choices=AGENT_NAMES,
        help="Agent slug.",
    )
    parser.add_argument(
        "report_dir",
        type=Path,
        help="Directory containing raw_runs.jsonl + analytics CSVs.",
    )
    parser.add_argument(
        "--prompt-root",
        type=Path,
        default=ROOT / "prompts",
        help="Directory holding <agent>_system.md / <agent>_user.md (default: prompts/).",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Override LLM_PROVIDER for this run (vllm | sglang | deepseek).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override model id for the active provider.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    settings = get_settings()

    provider = args.provider or None
    model = args.model or None
    llm = LocalLLMClient.from_settings(
        settings,
        provider=provider,
        model=model,
    )

    report_dir: Path = args.report_dir
    if not report_dir.exists():
        print(f"Missing report directory: {report_dir}", file=sys.stderr)
        return 1

    agent = build_agent(
        args.agent,
        llm=llm,
        prompts_root=args.prompt_root,
        settings=settings,
    )
    result: AgentRunResult = agent.run(report_dir)
    written = write_agent_result(report_dir, result)
    for path in written:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())