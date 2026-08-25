"""Typed, hashable contracts for auditable persona campaigns."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .persona_gateway import PersonaProvider, PersonaProviderMode

CAMPAIGN_REQUEST_SCHEMA = "persona-campaign-request-v1"
CAMPAIGN_RESULT_SCHEMA = "persona-campaign-cell-result-v1"
CAMPAIGN_MANIFEST_SCHEMA = "persona-campaign-manifest-v1"


class CampaignPersona(StrEnum):
    NEWBIE = "newbie"
    STUDY = "study"
    MONEY = "money"
    SOCIAL = "social"
    VISA = "visa"
    SLACKER = "slacker"


class CampaignCellState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class CampaignStopReason(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    GAME_FINISHED = "game_finished"
    WEEK_LIMIT = "week_limit"
    PROVIDER_FAILED = "provider_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CANCELLED = "cancelled"
    PROBE_FAILED = "probe_failed"
    INVARIANT_FAILED = "invariant_failed"


class CampaignRequest(BaseModel):
    """Complete matrix identity; AUTO provider is resolved before this boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[CAMPAIGN_REQUEST_SCHEMA] = CAMPAIGN_REQUEST_SCHEMA
    campaign_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    personas: tuple[CampaignPersona, ...] = Field(min_length=1, max_length=6)
    seeds: tuple[int, ...] = Field(min_length=1, max_length=20)
    max_weeks: int = Field(default=20, ge=1, le=52)
    difficulty: str = Field(default="normal", min_length=1, max_length=40)
    scenario: str = Field(
        default="default_first_semester", min_length=1, max_length=100
    )
    provider: PersonaProvider
    concurrency: int = Field(default=4, ge=1, le=4)
    report_root: str = "reports/build-week-2026/campaigns"

    @model_validator(mode="after")
    def _matrix_is_unambiguous(self) -> CampaignRequest:
        if len(set(self.personas)) != len(self.personas):
            raise ValueError("campaign personas must be unique")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("campaign seeds must be unique")
        if any(seed < 0 or seed > 2_147_483_647 for seed in self.seeds):
            raise ValueError("campaign seeds must be unsigned 32-bit-safe integers")
        _safe_relative_path(self.report_root, field="report_root")
        return self

    def fingerprint(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class CampaignSourceIdentity(BaseModel):
    """Immutable code/game/config/provider identity copied into every result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    agent_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    agent_dirty: Literal[False] = False
    game_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    game_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    game_archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    campaign_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider: PersonaProvider
    provider_mode: PersonaProviderMode
    provider_revision: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def _provider_mode_is_truthful(self) -> CampaignSourceIdentity:
        expected = {
            PersonaProvider.REPLAY: PersonaProviderMode.REPLAY,
            PersonaProvider.OPENAI: PersonaProviderMode.LIVE,
            PersonaProvider.VLLM: PersonaProviderMode.LOCAL,
            PersonaProvider.SGLANG: PersonaProviderMode.LOCAL,
            PersonaProvider.DEEPSEEK: PersonaProviderMode.LIVE,
        }[self.provider]
        if self.provider_mode != expected:
            raise ValueError(
                f"provider_mode {self.provider_mode} is invalid for {self.provider}"
            )
        return self

    def fingerprint(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class CampaignCellRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    campaign_id: str
    cell_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,119}$")
    persona: CampaignPersona
    seed: int
    max_weeks: int = Field(ge=1, le=52)
    difficulty: str
    scenario: str
    provider: PersonaProvider
    output_dir: str
    campaign_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _paths_and_identity_match(self) -> CampaignCellRequest:
        _safe_relative_path(self.output_dir, field="output_dir")
        if self.persona.value not in self.cell_id or f"seed-{self.seed}" not in self.cell_id:
            raise ValueError("cell_id must expose persona and seed")
        return self

    def fingerprint(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class CampaignArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str = Field(min_length=1, max_length=120)
    record_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _path_is_safe(self) -> CampaignArtifact:
        _safe_relative_path(self.path, field="artifact path")
        return self


class CampaignCitation(BaseModel):
    """Stable row-level evidence reference used by clusters and Codex."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    campaign_id: str
    cell_id: str
    persona: CampaignPersona
    seed: int
    week: int = Field(ge=1, le=52)
    artifact_path: str
    line_number: int = Field(ge=1)
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _artifact_path_is_safe(self) -> CampaignCitation:
        _safe_relative_path(self.artifact_path, field="citation artifact_path")
        return self


class CampaignCellResult(BaseModel):
    """Cell state plus mandatory source identity and exact evidence outputs."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[CAMPAIGN_RESULT_SCHEMA] = CAMPAIGN_RESULT_SCHEMA
    request: CampaignCellRequest
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: CampaignSourceIdentity
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: CampaignCellState
    stop_reason: CampaignStopReason
    completed_weeks: int = Field(default=0, ge=0, le=52)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str = Field(default="", max_length=500)
    artifacts: list[CampaignArtifact] = Field(default_factory=list)
    citations: list[CampaignCitation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _result_is_consistent(self) -> CampaignCellResult:
        if self.request_fingerprint != self.request.fingerprint():
            raise ValueError("request_fingerprint does not match cell request")
        if self.source_fingerprint != self.source.fingerprint():
            raise ValueError("source_fingerprint does not match source identity")
        if self.source.provider != self.request.provider:
            raise ValueError("source provider does not match cell provider")
        if self.completed_weeks > self.request.max_weeks:
            raise ValueError("completed_weeks exceeds requested max_weeks")
        if self.state == CampaignCellState.QUEUED:
            self._require(stop=CampaignStopReason.NOT_STARTED, started=False, completed=False)
        elif self.state == CampaignCellState.RUNNING:
            self._require(stop=CampaignStopReason.IN_PROGRESS, started=True, completed=False)
        else:
            if self.started_at is None or self.completed_at is None:
                raise ValueError("terminal cell state requires start and completion timestamps")
            if self.completed_at < self.started_at:
                raise ValueError("cell completion precedes start")
            if self.state == CampaignCellState.COMPLETED:
                if self.stop_reason not in {
                    CampaignStopReason.GAME_FINISHED,
                    CampaignStopReason.WEEK_LIMIT,
                }:
                    raise ValueError("completed cell has a failure stop reason")
                if self.completed_weeks < 1 or self.error:
                    raise ValueError("completed cell requires weeks and no error")
                if (
                    self.stop_reason == CampaignStopReason.WEEK_LIMIT
                    and self.completed_weeks != self.request.max_weeks
                ):
                    raise ValueError("week-limit completion requires every requested week")
            elif self.state == CampaignCellState.FAILED:
                if self.completed_weeks != 0 or not self.error:
                    raise ValueError("failed cell requires zero completed weeks and an error")
                self._require_failure_stop()
            elif self.state == CampaignCellState.PARTIAL:
                if self.completed_weeks < 1 or not self.error:
                    raise ValueError("partial cell requires completed weeks and an error")
                self._require_failure_stop()
            elif self.state == CampaignCellState.CANCELLED:
                if self.stop_reason != CampaignStopReason.CANCELLED:
                    raise ValueError("cancelled cell requires cancelled stop reason")
        for citation in self.citations:
            if (
                citation.campaign_id != self.request.campaign_id
                or citation.cell_id != self.request.cell_id
                or citation.persona != self.request.persona
                or citation.seed != self.request.seed
            ):
                raise ValueError("citation crosses campaign cell identity")
            if citation.week > self.completed_weeks:
                raise ValueError("citation week exceeds completed cell evidence")
            if not citation.artifact_path.startswith(self.request.output_dir + "/"):
                raise ValueError("citation path crosses campaign cell output")
        for artifact in self.artifacts:
            if not artifact.path.startswith(self.request.output_dir + "/"):
                raise ValueError("artifact path crosses campaign cell output")
        has_week_evidence = self.state in {
            CampaignCellState.COMPLETED,
            CampaignCellState.PARTIAL,
        } or (
            self.state == CampaignCellState.CANCELLED and self.completed_weeks > 0
        )
        if has_week_evidence:
            if not self.artifacts or len(self.citations) != self.completed_weeks:
                raise ValueError("completed evidence requires artifacts and one citation per week")
            if {item.week for item in self.citations} != set(
                range(1, self.completed_weeks + 1)
            ):
                raise ValueError("citations must cover each completed week exactly once")
        elif self.artifacts or self.citations:
            raise ValueError("cell without completed weeks cannot claim evidence artifacts")
        return self

    def _require(
        self, *, stop: CampaignStopReason, started: bool, completed: bool
    ) -> None:
        if self.stop_reason != stop:
            raise ValueError(f"{self.state} cell requires stop_reason={stop}")
        if (self.started_at is not None) != started:
            raise ValueError(f"{self.state} cell start timestamp is inconsistent")
        if (self.completed_at is not None) != completed:
            raise ValueError(f"{self.state} cell completion timestamp is inconsistent")
        if self.completed_weeks != 0 or self.error or self.artifacts or self.citations:
            raise ValueError(f"{self.state} cell cannot contain completed evidence")

    def _require_failure_stop(self) -> None:
        if self.stop_reason not in {
            CampaignStopReason.PROVIDER_FAILED,
            CampaignStopReason.BUDGET_EXHAUSTED,
            CampaignStopReason.PROBE_FAILED,
            CampaignStopReason.INVARIANT_FAILED,
        }:
            raise ValueError("failed or partial cell requires a failure stop reason")


class CampaignManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[CAMPAIGN_MANIFEST_SCHEMA] = CAMPAIGN_MANIFEST_SCHEMA
    request: CampaignRequest
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: CampaignSourceIdentity
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cells: tuple[CampaignCellRequest, ...] = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def _manifest_matches_matrix(self) -> CampaignManifest:
        if self.request_fingerprint != self.request.fingerprint():
            raise ValueError("manifest request fingerprint mismatch")
        if self.source_fingerprint != self.source.fingerprint():
            raise ValueError("manifest source fingerprint mismatch")
        expected = build_campaign_cells(self.request)
        if self.cells != expected:
            raise ValueError("manifest cells do not match the deterministic matrix")
        if self.source.provider != self.request.provider:
            raise ValueError("manifest source provider differs from request")
        return self


def build_campaign_cells(request: CampaignRequest) -> tuple[CampaignCellRequest, ...]:
    cells = []
    campaign_fingerprint = request.fingerprint()
    for persona in request.personas:
        for seed in request.seeds:
            identity = {
                "campaign": request.campaign_id,
                "persona": persona.value,
                "seed": seed,
                "campaign_fingerprint": campaign_fingerprint,
            }
            suffix = canonical_sha256(identity)[:12]
            cell_id = f"{persona.value}-seed-{seed}-{suffix}"
            cells.append(
                CampaignCellRequest(
                    campaign_id=request.campaign_id,
                    cell_id=cell_id,
                    persona=persona,
                    seed=seed,
                    max_weeks=request.max_weeks,
                    difficulty=request.difficulty,
                    scenario=request.scenario,
                    provider=request.provider,
                    output_dir=f"{request.report_root}/{request.campaign_id}/cells/{cell_id}",
                    campaign_fingerprint=campaign_fingerprint,
                )
            )
    return tuple(cells)


def resume_compatible(
    result: CampaignCellResult,
    request: CampaignCellRequest,
    source: CampaignSourceIdentity,
) -> bool:
    """Resume only byte-identical input/source identities and terminal success."""

    return (
        result.state == CampaignCellState.COMPLETED
        and result.request_fingerprint == request.fingerprint()
        and result.source_fingerprint == source.fingerprint()
        and result.request == request
        and result.source == source
    )


def citation_for_row(
    request: CampaignCellRequest,
    *,
    week: int,
    artifact_path: str,
    line_number: int,
    row: object,
) -> CampaignCitation:
    return CampaignCitation(
        campaign_id=request.campaign_id,
        cell_id=request.cell_id,
        persona=request.persona,
        seed=request.seed,
        week=week,
        artifact_path=artifact_path,
        line_number=line_number,
        record_sha256=canonical_sha256(row),
    )


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_relative_path(value: str, *, field: str) -> None:
    path = PurePosixPath(value.replace("\\", "/"))
    windows_drive = bool(path.parts and path.parts[0].endswith(":"))
    if not value or path.is_absolute() or windows_drive or ".." in path.parts:
        raise ValueError(f"{field} must be a safe relative path")


__all__ = [
    "CAMPAIGN_MANIFEST_SCHEMA",
    "CAMPAIGN_REQUEST_SCHEMA",
    "CAMPAIGN_RESULT_SCHEMA",
    "CampaignArtifact",
    "CampaignCellRequest",
    "CampaignCellResult",
    "CampaignCellState",
    "CampaignCitation",
    "CampaignManifest",
    "CampaignPersona",
    "CampaignRequest",
    "CampaignSourceIdentity",
    "CampaignStopReason",
    "build_campaign_cells",
    "canonical_sha256",
    "citation_for_row",
    "resume_compatible",
]
