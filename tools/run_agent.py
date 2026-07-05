#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.env import load_dotenv
from game_analysis_agent.llm_client import LLMConfig, LocalLLMClient
from game_analysis_agent.report_bundle import read_report_bundle, render_prompt


AGENT_OUTPUTS = {
    "balance": ["agent_diagnosis.md", "tuning_proposal.md"],
    "content_qa": ["content_issues.md"],
    "event_graph": ["event_graph_report.md"],
}


def usage() -> None:
    print("Usage: python3 tools/run_agent.py <balance|content_qa|event_graph> <report_dir>")


def split_balance_output(text: str) -> dict[str, str]:
    marker = "# Tuning Proposal"
    if marker not in text:
        return {
            "agent_diagnosis.md": text,
            "tuning_proposal.md": "# Tuning Proposal\n\nAgent did not emit a separate section.\n",
        }
    before, after = text.split(marker, 1)
    return {
        "agent_diagnosis.md": before.strip() + "\n",
        "tuning_proposal.md": marker + after.strip() + "\n",
    }


def main() -> int:
    if len(sys.argv) != 3:
        usage()
        return 2

    load_dotenv(ROOT / ".env")
    agent_name = sys.argv[1]
    report_dir = Path(sys.argv[2])
    if agent_name not in AGENT_OUTPUTS:
        usage()
        return 2
    if not report_dir.exists():
        print(f"Missing report directory: {report_dir}", file=sys.stderr)
        return 1

    system_path = ROOT / "prompts" / f"{agent_name}_agent_system.md"
    user_path = ROOT / "prompts" / f"{agent_name}_agent_user.md"
    system_prompt = system_path.read_text(encoding="utf-8")
    report_bundle = read_report_bundle(report_dir)
    user_prompt = render_prompt(user_path, report_bundle)

    client = LocalLLMClient(LLMConfig.from_env())
    response = client.chat(system_prompt, user_prompt)

    if agent_name == "balance":
        outputs = split_balance_output(response)
    else:
        outputs = {AGENT_OUTPUTS[agent_name][0]: response}

    for file_name, content in outputs.items():
        out_path = report_dir / file_name
        out_path.write_text(content, encoding="utf-8")
        print(f"Wrote {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
