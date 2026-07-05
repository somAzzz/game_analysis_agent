"""Agent registry + lazy-import helpers.

Each agent module exports a single class implementing
:class:`game_analysis_agent.agents.base.Agent`. Consumers should import from
this package rather than reaching into individual modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game_analysis_agent.agents.base import (
    Agent,
    AgentOutput,
    AgentRunResult,
    load_profile,
    render_prompt_text,
    resolve_prompts_root,
    write_agent_result,
)

if TYPE_CHECKING:
    from game_analysis_agent.agents.balance import BalanceAgent  # noqa: F401
    from game_analysis_agent.agents.boundary_prober import BoundaryProberAgent  # noqa: F401
    from game_analysis_agent.agents.bug_hunter import BugHunterAgent  # noqa: F401
    from game_analysis_agent.agents.content_qa import ContentQAAgent  # noqa: F401
    from game_analysis_agent.agents.event_graph import EventGraphAgent  # noqa: F401
    from game_analysis_agent.agents.interactive_player import InteractivePlayerAgent  # noqa: F401
    from game_analysis_agent.agents.value_reviewer import ValueReviewerAgent  # noqa: F401


AGENT_NAMES: tuple[str, ...] = (
    "balance",
    "content_qa",
    "event_graph",
    "bug_hunter",
    "boundary_prober",
    "value_reviewer",
    "interactive_player",
)


def build_agent(name: str, **kwargs):
    """Construct one agent by slug.

    ``kwargs`` is forwarded to the agent's ``__init__``. The common
    shape: ``llm=..., prompts_root=..., settings=..., extra_files=...``.
    For :class:`InteractivePlayerAgent`, you must also pass
    ``tool_definitions=`` and ``tool_map=``.
    """
    if name not in AGENT_NAMES:
        raise KeyError(f"Unknown agent: {name!r}. Known: {AGENT_NAMES}")
    module = __import__(f"game_analysis_agent.agents.{name}", fromlist=[name])
    # Each module exports a single class matching its name (with
    # "Agent" suffix). We look it up by suffix to keep the import side
    # effects minimal.
    for attr in vars(module).values():
        if isinstance(attr, type) and attr.__name__.endswith("Agent") and attr is not Agent:
            return attr(**kwargs)
    raise RuntimeError(f"No agent class found in module: {name}")


def list_agents() -> tuple[str, ...]:
    return AGENT_NAMES


__all__ = [
    "AGENT_NAMES",
    "Agent",
    "AgentOutput",
    "AgentRunResult",
    "build_agent",
    "list_agents",
    "load_profile",
    "render_prompt_text",
    "resolve_prompts_root",
    "write_agent_result",
]
