"""Common agent base class.

Each agent owns:

* A ``name`` (slug, matches ``config/agent_profiles.yaml`` and the LLM
  log tag).
* A ``system_prompt`` (Markdown template rendered from
  ``prompts/<name>_system.md``).
* A ``user_prompt`` (Markdown template rendered from
  ``prompts/<name>_user.md`` with ``{{REPORT_BUNDLE}}`` filled in).
* A list of ``output_files`` (paths written into ``<report_dir>``).

Subclasses override :meth:`build_user_prompt` for richer context
(e.g. the bug-hunter agent injects anomalies JSONL).

The orchestrator (:mod:`tools.run_gameplay_agent`) decides which agents
to run and is responsible for collecting LLM calls / tool events into a
:class:`game_analysis_agent.schemas.AgentRunReport`. Agents themselves are
side-effect-free apart from writing their output files to disk.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from game_analysis_agent.llm_client import LocalLLMClient
from game_analysis_agent.report_bundle import DEFAULT_REPORT_FILES, read_report_bundle
from game_analysis_agent.settings import Settings


@dataclass
class AgentOutput:
    """One artifact produced by an agent."""

    file_name: str
    content: str


@dataclass
class AgentRunResult:
    agent: str
    outputs: list[AgentOutput] = field(default_factory=list)


class Agent(ABC):
    """Abstract base class for every analysis agent."""

    name: str = "agent"
    default_output_files: tuple[str, ...] = ()
    default_temperature: float = 0.2

    def __init__(
        self,
        *,
        llm: LocalLLMClient,
        prompts_root: Path,
        settings: Settings | None = None,
        output_files: tuple[str, ...] | None = None,
        temperature: float | None = None,
        extra_files: tuple[str, ...] = (),
    ) -> None:
        self.llm = llm
        self.prompts_root = prompts_root
        self.settings = settings
        self.temperature = self._resolve_temperature(temperature)
        self.output_files = tuple(output_files) if output_files else self.default_output_files
        self.extra_files = tuple(extra_files)

    # --- template methods --------------------------------------------------

    @abstractmethod
    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        """Render the user-prompt template (without the report bundle)."""

    def build_system_prompt(self) -> str:
        path = self.prompts_root / f"{self.name}_system.md"
        return path.read_text(encoding="utf-8")

    def render_user_template(self, report_dir: Path, context: dict[str, Any]) -> str:
        """Combine the report bundle with the user prompt template."""
        files = list(DEFAULT_REPORT_FILES) + list(self.extra_files)
        bundle = read_report_bundle(report_dir, files=files)
        user_template = self.build_user_prompt(report_dir, context)
        return render_prompt_text(user_template, bundle)

    def run(
        self,
        report_dir: Path,
        context: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        """Run the agent and return a :class:`AgentRunResult` (no I/O)."""
        context = context or {}
        system_prompt = self.build_system_prompt()
        user_prompt = self.render_user_template(report_dir, context)
        response = self.llm.complete(
            user_prompt,
            system=system_prompt,
            agent=self.name,
            step_name=self.name,
            temperature=self.temperature,
        )
        outputs = self._split_outputs(response)
        return AgentRunResult(agent=self.name, outputs=outputs)

    # --- helpers ----------------------------------------------------------

    def _resolve_temperature(self, override: float | None) -> float:
        if override is not None:
            return override
        if self.settings is not None:
            return self.settings.agent_temperature
        return self.default_temperature

    def _split_outputs(self, response: str) -> list[AgentOutput]:
        """Default: write the whole response to the first output file.

        Subclasses override this to split a single response into multiple
        output files (e.g. ``balance`` writes ``agent_diagnosis.md`` +
        ``tuning_proposal.md``).
        """
        if not self.output_files:
            return []
        return [AgentOutput(file_name=self.output_files[0], content=response.strip() + "\n")]


def render_prompt_text(user_template: str, bundle: str) -> str:
    """Substitute ``{{REPORT_BUNDLE}}`` in the user template."""
    return user_template.replace("{{REPORT_BUNDLE}}", bundle)


def write_agent_result(report_dir: Path, result: AgentRunResult) -> list[Path]:
    written: list[Path] = []
    for output in result.outputs:
        path = report_dir / output.file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output.content, encoding="utf-8")
        written.append(path)
    return written


def load_profile(
    yaml_path: Path,
    agent_name: str,
) -> dict[str, Any]:
    """Load one agent's profile block from ``agent_profiles.yaml``."""
    import yaml

    with yaml_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    agents = payload.get("agents", {}) or {}
    profile = agents.get(agent_name)
    if not profile:
        raise KeyError(f"Agent profile not found: {agent_name}")
    return profile


def resolve_prompts_root(project_root: Path) -> Path:
    return project_root / "prompts"


__all__ = [
    "Agent",
    "AgentOutput",
    "AgentRunResult",
    "load_profile",
    "resolve_prompts_root",
    "render_prompt_text",
    "write_agent_result",
]


# Callable re-export used by sibling modules
CallableAny = Callable[..., Any]

del CallableAny  # silence unused
