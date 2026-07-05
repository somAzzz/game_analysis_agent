"""Development-side local LLM agent pipeline for Godot simulations.

Public surface:

* :mod:`game_analysis_agent.analytics` — pure statistics over raw_runs.jsonl.
* :mod:`game_analysis_agent.anomaly_detector` — invariant + spike + repeat detection.
* :mod:`game_analysis_agent.bug_summarizer` — turn anomalies into Markdown.
* :mod:`game_analysis_agent.value_analyzer` — pick-rate / ending dominance checks.
* :mod:`game_analysis_agent.llm_client` — OpenAI-compatible LLM client with
  provider switching (vllm / sglang / deepseek) and call auditing.
* :mod:`game_analysis_agent.tool_loop` — OpenAI-compatible tool-calling loop.
* :mod:`game_analysis_agent.game_tools` — tool schemas + Godot subprocess wrappers
  used by the interactive player.
* :mod:`game_analysis_agent.agents` — seven specialized agents: balance,
  content_qa, event_graph, bug_hunter, boundary_prober, value_reviewer,
  interactive_player.
* :mod:`game_analysis_agent.settings` — process-wide config dataclass.
* :mod:`game_analysis_agent.schemas` — Pydantic models for audit + findings.
"""

from __future__ import annotations

from game_analysis_agent import (
    agents,
    analytics,
    anomaly_detector,
    bug_summarizer,
    game_tools,
    llm_client,
    report_bundle,
    schemas,
    settings,
    tool_loop,
    value_analyzer,
)

__all__ = [
    "agents",
    "analytics",
    "anomaly_detector",
    "bug_summarizer",
    "game_tools",
    "llm_client",
    "report_bundle",
    "schemas",
    "settings",
    "tool_loop",
    "value_analyzer",
]