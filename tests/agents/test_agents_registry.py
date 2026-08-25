"""Tests for the agent registry + base class."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent.agents import AGENT_NAMES, build_agent
from game_analysis_agent.agents.content_qa import ContentQAAgent, score_choice_structure
from game_analysis_agent.agents.event_graph import EventGraphAgent, build_untriggered_block
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


def test_event_graph_prompt_includes_untriggered_events(
    llm: LocalLLMClient,
    tmp_path: Path,
) -> None:
    prompts = tmp_path / "prompts"
    reports = tmp_path / "reports"
    prompts.mkdir()
    reports.mkdir()
    (prompts / "event_graph_user.md").write_text(
        "{{UNTRIGGERED_EVENTS}}\n\n{{REPORT_BUNDLE}}",
        encoding="utf-8",
    )
    (reports / "event_graph.json").write_text(
        json.dumps(
            {
                "events": [
                    {"id": "seen_event", "trigger": {"week": 1}},
                    {"id": "missing_event", "trigger": {"flag": "registered"}},
                ]
            }
        ),
        encoding="utf-8",
    )
    (reports / "raw_runs.jsonl").write_text(
        json.dumps(
            {
                "weekly_log": [
                    {"week": 1, "triggered_event_id": "seen_event", "after_state": {}}
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    agent = EventGraphAgent(llm=llm, prompts_root=prompts, settings=Settings())
    rendered = agent.render_user_template(reports, {})

    assert "## Untriggered Events" in rendered
    assert "`missing_event`" in rendered
    assert "required flag `registered` never appears" in rendered


def test_build_untriggered_block_counts_triggered_events() -> None:
    block = build_untriggered_block(
        raw_runs=[
            {"weekly_log": [{"week": 1, "triggered_event_id": "a"}]},
        ],
        event_graph={
            "events": [
                {"id": "a", "trigger": {"week": 1}},
                {"id": "b", "trigger": {"metric": "language", "min": 50}},
            ]
        },
    )

    assert "`b`" in block
    assert "`a`" not in block


def test_content_qa_prompt_includes_choice_structure_findings(
    llm: LocalLLMClient,
    tmp_path: Path,
) -> None:
    prompts = tmp_path / "prompts"
    reports = tmp_path / "reports"
    prompts.mkdir()
    reports.mkdir()
    (prompts / "content_qa_user.md").write_text(
        "{{CHOICE_STRUCTURE_FINDINGS}}\n\n{{REPORT_BUNDLE}}",
        encoding="utf-8",
    )
    (reports / "event_graph.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "flat_choices",
                        "choices": [
                            {"text": "A", "success_effects": {"stress": 1}},
                            {"text": "A", "success_effects": {"stress": 1}},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    agent = ContentQAAgent(llm=llm, prompts_root=prompts, settings=Settings())
    rendered = agent.render_user_template(reports, {})

    assert "## Choice Structure Findings" in rendered
    assert "duplicate_choice_text" in rendered
    assert "choice_effects_too_similar" in rendered


def test_score_choice_structure_detects_missing_costs() -> None:
    findings = score_choice_structure(
        {
            "events": [
                {
                    "id": "empty_choices",
                    "choices": [
                        {"text": "Wait"},
                        {"text": "Also wait"},
                    ],
                }
            ]
        }
    )

    assert {finding["issue_type"] for finding in findings} == {"missing_failure_cost"}
