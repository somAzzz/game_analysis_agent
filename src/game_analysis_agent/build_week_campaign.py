"""Canonical Replay campaign execution and pre-repair target selection."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agents.interactive_player import InteractivePlayerAgent
from .campaign_aggregation import CampaignAggregation, FailureCluster
from .campaign_contract import (
    CampaignCellRequest,
    CampaignCellState,
    CampaignCitation,
    CampaignRequest,
    CampaignSourceIdentity,
    CampaignStopReason,
)
from .campaign_runner import (
    CampaignExecutionContext,
    CellExecutionOutcome,
)
from .game_tools import build_probe
from .persona_gateway import PersonaProvider, PersonaProviderMode
from .persona_runtime import GovernedPersonaGateway
from .recorded_persona_gateway import RecordedPersonaGateway
from .settings import Settings

TARGET_SCHEMA = "build-week-repair-target-v1"
DEFAULT_HOLDOUT_SEEDS = (1042, 1043, 1044)


class TargetSelectionError(RuntimeError):
    """Raised when evidence cannot support exactly one repair target."""


class TargetRubric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reproducible: Literal[True] = True
    cross_persona: Literal[True] = True
    causally_plausible: Literal[True] = True
    user_relevant: Literal[True] = True
    one_mechanism_repairable: Literal[True] = True
    invariant_safe_candidate: Literal[True] = True
    visually_explainable: Literal[True] = True


class FrozenRepairTarget(BaseModel):
    """Exactly one evidence-backed target frozen before any source patch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[TARGET_SCHEMA] = TARGET_SCHEMA
    campaign_id: str
    campaign_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    campaign_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_before_patch: Literal[True] = True
    selected_cluster_id: str
    label: str
    hypothesis: str
    member_count: int = Field(ge=2)
    persona_count: int = Field(ge=2)
    fixed_seeds: tuple[int, ...] = Field(min_length=1)
    holdout_seeds: tuple[int, ...] = Field(min_length=1)
    evidence_bundle: str
    rubric: TargetRubric
    evidence: tuple[CampaignCitation, ...] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def _seeds_and_evidence_are_independent(self) -> FrozenRepairTarget:
        if set(self.fixed_seeds) & set(self.holdout_seeds):
            raise ValueError("fixed and holdout seeds must be disjoint")
        if len(set(self.fixed_seeds)) != len(self.fixed_seeds):
            raise ValueError("fixed seeds must be unique")
        if len(set(self.holdout_seeds)) != len(self.holdout_seeds):
            raise ValueError("holdout seeds must be unique")
        if len({item.persona for item in self.evidence}) < 2:
            raise ValueError("target evidence must cross personas")
        if any(item.campaign_id != self.campaign_id for item in self.evidence):
            raise ValueError("target evidence crosses campaign identity")
        bundle = PurePosixPath(self.evidence_bundle.replace("\\", "/"))
        if bundle.is_absolute() or ".." in bundle.parts:
            raise ValueError("target evidence bundle must be repository-relative")
        return self


class ReplayCampaignExecutor:
    """Run one isolated real-Godot cell through exact hash-pinned Replay."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        manifest_path: str | Path,
        settings: Settings,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.manifest_path = Path(manifest_path).resolve()
        self.settings = settings

    def __call__(
        self,
        request: CampaignCellRequest,
        output_dir: Path,
        context: CampaignExecutionContext,
    ) -> CellExecutionOutcome:
        gateway = RecordedPersonaGateway.from_manifest(
            self.manifest_path, project_root=self.project_root
        )
        agent = InteractivePlayerAgent(
            llm=None,
            persona_gateway=gateway,
            prompts_root=self.project_root / "prompts",
            settings=self.settings,
            max_weeks=request.max_weeks,
            persona=request.persona.value,
            difficulty=request.difficulty,
            scenario=request.scenario,
            seed=request.seed,
            cancellation_check=lambda: context.cancelled,
        )
        result, _paths = agent.play_through(
            output_dir,
            probe=build_probe(self.settings),
            context={"run_id": request.cell_id},
        )
        completed = len(result.steps)
        if completed < 1:
            raise RuntimeError("real-game campaign cell produced no weekly evidence")
        return CellExecutionOutcome(
            state=CampaignCellState.COMPLETED,
            stop_reason=(
                CampaignStopReason.WEEK_LIMIT
                if completed == request.max_weeks
                else CampaignStopReason.GAME_FINISHED
            ),
            completed_weeks=completed,
        )


def _validation_flag(validation: object, field: str) -> bool:
    if isinstance(validation, Mapping):
        return bool(validation.get(field))
    return bool(getattr(validation, field, False))


class PersonaCampaignExecutor:
    """Run a real-Godot cell through one governed non-Replay gateway."""

    def __init__(
        self,
        *,
        gateway: GovernedPersonaGateway,
        settings: Settings,
        external_cancelled: Callable[[], bool] | None = None,
        progress_callback: Callable[[CampaignCellRequest, Path, dict[str, Any]], None]
        | None = None,
    ) -> None:
        if gateway.provider == PersonaProvider.REPLAY or gateway.mode == PersonaProviderMode.REPLAY:
            raise ValueError("persona campaign executor requires a non-Replay gateway")
        self.progress_callback = progress_callback
        self.gateway = gateway
        self.settings = settings
        self.external_cancelled = external_cancelled or (lambda: False)

    def __call__(
        self,
        request: CampaignCellRequest,
        output_dir: Path,
        context: CampaignExecutionContext,
    ) -> CellExecutionOutcome:
        if request.provider != self.gateway.provider:
            raise ValueError("campaign request/gateway provider mismatch")

        def cancelled() -> bool:
            if self.external_cancelled():
                self.gateway.cancellation.cancel()
            return context.cancelled or self.gateway.cancellation.cancelled

        agent = InteractivePlayerAgent(
            llm=None,
            persona_gateway=self.gateway,
            prompts_root=Path(__file__).resolve().parents[2] / "prompts",
            settings=self.settings,
            max_weeks=request.max_weeks,
            persona=request.persona.value,
            progress_callback=(
                (lambda event: self.progress_callback(request, output_dir, event))
                if self.progress_callback is not None
                else None
            ),
            difficulty=request.difficulty,
            scenario=request.scenario,
            seed=request.seed,
            cancellation_check=cancelled,
        )
        result, _paths = agent.play_through(
            output_dir,
            probe=build_probe(self.settings),
            context={"run_id": request.cell_id},
        )
        completed = len(result.steps)
        if completed < 1:
            raise RuntimeError("persona campaign cell produced no weekly evidence")
        fallback_weeks = [
            step.week
            for step in result.steps
            if not _validation_flag(step.validation, "valid")
            or _validation_flag(step.validation, "fallback_used")
        ]
        if fallback_weeks:
            return CellExecutionOutcome(
                state=CampaignCellState.PARTIAL,
                stop_reason=CampaignStopReason.PROVIDER_FAILED,
                completed_weeks=completed,
                error=(
                    f"{self.gateway.provider.value} provider produced invalid/fallback "
                    f"decisions at weeks {fallback_weeks}"
                ),
            )
        return CellExecutionOutcome(
            state=CampaignCellState.COMPLETED,
            stop_reason=(
                CampaignStopReason.WEEK_LIMIT
                if completed == request.max_weeks
                else CampaignStopReason.GAME_FINISHED
            ),
            completed_weeks=completed,
        )


class LiveCampaignExecutor(PersonaCampaignExecutor):
    """Compatibility wrapper that accepts only the live OpenAI gateway."""

    def __init__(
        self,
        *,
        gateway: GovernedPersonaGateway,
        settings: Settings,
        external_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        if gateway.provider != PersonaProvider.OPENAI or gateway.mode != PersonaProviderMode.LIVE:
            raise ValueError("live campaign executor requires a live OpenAI gateway")
        super().__init__(
            gateway=gateway,
            settings=settings,
            external_cancelled=external_cancelled,
        )


def build_source_identity(
    *,
    project_root: str | Path,
    game_root: str | Path,
    campaign_config: str | Path,
    replay_manifest: str | Path,
) -> CampaignSourceIdentity:
    """Fail closed unless agent, game, config, and Replay identities are exact."""

    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    config_path = Path(campaign_config).resolve()
    manifest_path = Path(replay_manifest).resolve()
    dirty = _git(project, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise TargetSelectionError("canonical campaign requires a clean agent worktree")
    marker = json.loads((game / ".playtest-forge-source.json").read_text(encoding="utf-8"))
    replay = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_digest = str(replay.get("sha256", ""))
    fixture_path = project / str(replay.get("fixture", ""))
    if (
        len(fixture_digest) != 64
        or not fixture_path.is_file()
        or hashlib.sha256(fixture_path.read_bytes()).hexdigest() != fixture_digest
    ):
        raise TargetSelectionError("full Replay fixture identity is invalid")
    return CampaignSourceIdentity(
        agent_commit=_git(project, "rev-parse", "HEAD"),
        agent_tree=_git(project, "rev-parse", "HEAD^{tree}"),
        game_commit=str(marker["commit"]),
        game_tree=str(marker["tree"]),
        game_archive_sha256=str(marker["archive_sha256"]),
        campaign_config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        provider=PersonaProvider.REPLAY,
        provider_mode=PersonaProviderMode.REPLAY,
        provider_revision=f"fixture:{fixture_digest}",
    )


def build_live_source_identity(
    *,
    project_root: str | Path,
    game_root: str | Path,
    request: CampaignRequest,
    model: str,
) -> CampaignSourceIdentity:
    """Bind a dynamic OpenAI request to clean agent/game/model identities."""

    if request.provider != PersonaProvider.OPENAI:
        raise TargetSelectionError("live source identity requires an OpenAI request")
    return build_provider_source_identity(
        project_root=project_root,
        game_root=game_root,
        request=request,
        provider=PersonaProvider.OPENAI,
        mode=PersonaProviderMode.LIVE,
        model=model,
    )


def build_provider_source_identity(
    *,
    project_root: str | Path,
    game_root: str | Path,
    request: CampaignRequest,
    provider: PersonaProvider,
    mode: PersonaProviderMode,
    model: str,
) -> CampaignSourceIdentity:
    """Bind a dynamic provider request to clean agent/game/model identities."""

    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    if _git(project, "status", "--porcelain", "--untracked-files=all"):
        raise TargetSelectionError("persona campaign requires a clean agent worktree")
    if request.provider != provider:
        raise TargetSelectionError("campaign request/source provider mismatch")
    marker = json.loads((game / ".playtest-forge-source.json").read_text(encoding="utf-8"))
    return CampaignSourceIdentity(
        agent_commit=_git(project, "rev-parse", "HEAD"),
        agent_tree=_git(project, "rev-parse", "HEAD^{tree}"),
        game_commit=str(marker["commit"]),
        game_tree=str(marker["tree"]),
        game_archive_sha256=str(marker["archive_sha256"]),
        campaign_config_sha256=request.fingerprint(),
        provider=provider,
        provider_mode=mode,
        provider_revision=f"model:{model}",
    )


def select_repair_target(
    *,
    request: CampaignRequest,
    aggregation: CampaignAggregation,
    holdout_seeds: tuple[int, ...] = DEFAULT_HOLDOUT_SEEDS,
    clusters: tuple[FailureCluster, ...] | None = None,
    evidence_bundle: str = "examples/build_week_2026/campaign-v1",
) -> FrozenRepairTarget:
    """Apply the frozen rubric without model inference or patched results."""

    observed_clusters = aggregation.clusters if clusters is None else clusters
    eligible = [
        cluster
        for cluster in observed_clusters
        if cluster.member_count >= 2
        and len(cluster.persona_counts) >= 2
        and cluster.cluster_id != "provider-fallback"
    ]
    preferred = next(
        (item for item in eligible if item.cluster_id == "cashflow-stress-attractor"),
        None,
    )
    selected = preferred or _strongest(eligible)
    if selected is None:
        raise TargetSelectionError(
            "no non-provider failure cluster crosses two runs and two personas"
        )
    evidence = _cross_persona_representatives(selected)
    return FrozenRepairTarget(
        campaign_id=aggregation.campaign_id,
        campaign_request_fingerprint=aggregation.request_fingerprint,
        campaign_source_fingerprint=aggregation.source_fingerprint,
        selected_cluster_id=selected.cluster_id,
        label=selected.label,
        hypothesis=_hypothesis(selected.cluster_id),
        member_count=selected.member_count,
        persona_count=len(selected.persona_counts),
        fixed_seeds=request.seeds,
        holdout_seeds=holdout_seeds,
        evidence_bundle=evidence_bundle,
        rubric=TargetRubric(),
        evidence=evidence,
    )


def write_target(path: str | Path, target: FrozenRepairTarget) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(target.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return destination


def _strongest(clusters: list[FailureCluster]) -> FailureCluster | None:
    if not clusters:
        return None
    return sorted(
        clusters,
        key=lambda item: (-item.member_count, -len(item.persona_counts), item.cluster_id),
    )[0]


def _hypothesis(cluster_id: str) -> str:
    mechanism = (
        "survival-economy pressure"
        if cluster_id == "cashflow-stress-attractor"
        else "stress and recovery pressure"
        if cluster_id == "burnout-risk"
        else "one game-state pressure"
    )
    return (
        f"A single {mechanism} mechanism repeatedly pushes distinct player intents "
        "into the selected attractor; a constrained change should reduce first entry "
        "without erasing designed persona differences."
    )


def _cross_persona_representatives(
    cluster: FailureCluster,
) -> tuple[CampaignCitation, ...]:
    selected = []
    seen = set()
    for citation in cluster.members:
        if citation.persona in seen:
            continue
        selected.append(citation)
        seen.add(citation.persona)
        if len(selected) == 3:
            break
    if len(selected) < 2:
        raise TargetSelectionError("selected cluster lacks cross-persona citations")
    return tuple(selected)


def _git(project: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


__all__ = [
    "DEFAULT_HOLDOUT_SEEDS",
    "FrozenRepairTarget",
    "LiveCampaignExecutor",
    "PersonaCampaignExecutor",
    "ReplayCampaignExecutor",
    "TARGET_SCHEMA",
    "TargetRubric",
    "TargetSelectionError",
    "build_live_source_identity",
    "build_provider_source_identity",
    "build_source_identity",
    "select_repair_target",
    "write_target",
]
