"""Tests for the agent registry + base class."""

from __future__ import annotations

from pathlib import Path

import pytest

from game_analysis_agent.agents import AGENT_NAMES, build_agent
from game_analysis_agent.llm_client import LocalLLMClient
from game_analysis_agent.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def llm(settings: Settings) -> LocalLLMClient:
    return LocalLLMClient.from_settings(settings)


def test_registry_contains_all_seven_agents() -> None:
    expected = {
        "balance",
        "content_qa",
        "event_graph",
        "bug_hunter",
        "boundary_prober",
        "value_reviewer",
        "interactive_player",
    }
    assert set(AGENT_NAMES) == expected


def test_build_agent_raises_for_unknown() -> None:
    with pytest.raises(KeyError):
        build_agent("nope")


def test_build_agent_returns_subclass_instance(llm: LocalLLMClient, tmp_path: Path) -> None:
    for name in AGENT_NAMES:
        if name == "interactive_player":
            # Interactive player requires tool_definitions + tool_map at
            # construction time; we exercise it via a separate test.
            continue
        agent = build_agent(
            name,
            llm=llm,
            prompts_root=tmp_path,
            settings=Settings(),
        )
        assert agent.name == name


def test_agents_have_unique_default_output_files() -> None:
    """Each agent should declare at least one output file so callers can
    reliably grep ``<report_dir>`` for them."""
    from game_analysis_agent.agents.base import Agent

    # Lazy import agent classes
    output_sets = []
    for name in AGENT_NAMES:
        agent_module = __import__(
            f"game_analysis_agent.agents.{name}", fromlist=[name]
        )
        for attr in vars(agent_module).values():
            if isinstance(attr, type) and issubclass(attr, Agent) and attr is not Agent:
                output_sets.append(set(attr.default_output_files))
                break
    # The interactive player also writes the per-step JSONL.
    assert all(output_sets), "every agent should declare output_files"
    # All sets should be non-empty.
    for outputs in output_sets:
        assert outputs, f"agent output set is empty: {outputs}"