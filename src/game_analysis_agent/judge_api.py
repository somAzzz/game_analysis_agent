"""Bounded, public-bundle-first service layer for human Judge Mode."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .campaign_aggregation import CampaignAggregation
from .campaign_bundle import verify_public_campaign_bundle
from .openai_persona_gateway import DEFAULT_OPENAI_PERSONA_MODEL
from .repair_bundle import verify_public_repair_bundle
from .repair_experiment import RepairExperimentRecord

MAX_REQUEST_BYTES = 32 * 1024
MAX_CAMPAIGNS = 2
PUBLIC_CAMPAIGN_ID = "build-week-2026-evidence-v1"
PUBLIC_EXPERIMENT_ID = "cashflow-drift-repair-v1"
PERSONAS = frozenset({"newbie", "study", "money", "social", "visa", "slacker"})


class JudgeAPIError(RuntimeError):
    """Typed public API error that never contains secrets or SDK objects."""

    def __init__(
        self, code: str, message: str, remediation: str, *, status_code: int = 400
    ) -> None:
        super().__init__(message)
        self.code = code
        self.remediation = remediation
        self.status_code = status_code

    def payload(self) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": str(self),
                "remediation": self.remediation,
            }
        }


class ProviderTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["replay", "openai"]


class CampaignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["replay", "openai"] = "replay"
    personas: tuple[str, ...] = Field(default=("newbie",), min_length=1, max_length=3)
    seeds: tuple[int, ...] = Field(default=(42,), min_length=1, max_length=3)
    max_weeks: int = Field(default=3, ge=1, le=5)

    @model_validator(mode="after")
    def _bounded_inputs(self) -> CampaignCreateRequest:
        if len(set(self.personas)) != len(self.personas) or not set(self.personas).issubset(
            PERSONAS
        ):
            raise ValueError("personas must be unique known ids")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be unique")
        return self


@dataclass
class CampaignJob:
    campaign_id: str
    request: CampaignCreateRequest
    status: str = "queued"
    mode: str = "prerecorded"
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    events: list[dict[str, object]] = field(default_factory=list)
    result: dict[str, object] | None = None
    error: dict[str, object] | None = None
    cancelled: threading.Event = field(default_factory=threading.Event, repr=False)

    def public(self) -> dict[str, object]:
        return {
            "campaign_id": self.campaign_id,
            "status": self.status,
            "mode": self.mode,
            "request": self.request.model_dump(mode="json"),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
        }


class ProviderService:
    def __init__(
        self,
        *,
        project_root: Path,
        environment: Mapping[str, str] | None = None,
        openai_client_factory: Callable[..., Any] = OpenAI,
    ) -> None:
        self.project = project_root.resolve()
        self.environment = dict(environment if environment is not None else os.environ)
        self._openai_client_factory = openai_client_factory
        self.model = self.environment.get("OPENAI_PERSONA_MODEL", DEFAULT_OPENAI_PERSONA_MODEL)

    def status(self) -> dict[str, object]:
        configured = bool(self.environment.get("OPENAI_API_KEY", "").strip())
        game_available = _game_available(self.environment.get("GAME_PROJECT_PATH"))
        return {
            "schema_version": "judge-provider-status-v1",
            "providers": {
                "replay": {
                    "status": "available",
                    "mode": "prerecorded",
                    "requires_api_key": False,
                    "requires_game_runtime": False,
                },
                "openai": {
                    "status": "available" if configured else "unavailable",
                    "mode": "live",
                    "model": self.model,
                    "requires_api_key": True,
                    "api_key_configured": configured,
                    "game_runtime_configured": game_available,
                    "live_campaign_ready": configured and game_available,
                },
            },
        }

    def test(self, request: ProviderTestRequest) -> dict[str, object]:
        if request.provider == "replay":
            gate = verify_public_campaign_bundle(
                self.project / "examples/build_week_2026/campaign-v1"
            )
            return {
                "status": "passed",
                "provider": "replay",
                "mode": "prerecorded",
                "campaign_id": gate.campaign_id,
            }
        key = self.environment.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise JudgeAPIError(
                "openai_key_missing",
                "OpenAI provider is not configured",
                "Set OPENAI_API_KEY in the server environment; never send it from the browser.",
                status_code=503,
            )
        started = time.monotonic()
        try:
            client = self._openai_client_factory(api_key=key, timeout=10, max_retries=0)
            response = client.responses.create(
                model=self.model,
                input="Return exactly READY.",
                max_output_tokens=16,
                store=False,
            )
        except Exception as exc:
            raise JudgeAPIError(
                "openai_provider_test_failed",
                f"OpenAI provider test failed: {exc.__class__.__name__}",
                "Check the restricted server key, network, model access, and rate limits.",
                status_code=502,
            ) from exc
        return {
            "status": "passed",
            "provider": "openai",
            "mode": "live",
            "model": str(getattr(response, "model", self.model)),
            "response_id": str(getattr(response, "id", "")),
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }


class CampaignService:
    def __init__(
        self,
        *,
        project_root: Path,
        provider_service: ProviderService,
        live_runner: Callable[[CampaignJob], dict[str, object]] | None = None,
    ) -> None:
        self.project = project_root.resolve()
        self.providers = provider_service
        self.live_runner = live_runner
        self._jobs: dict[str, CampaignJob] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=MAX_CAMPAIGNS, thread_name_prefix="judge")

    def create(self, request: CampaignCreateRequest) -> dict[str, object]:
        with self._lock:
            active = sum(job.status in {"queued", "running"} for job in self._jobs.values())
            if active >= MAX_CAMPAIGNS:
                raise JudgeAPIError(
                    "campaign_capacity_exceeded",
                    "Judge Mode already has the maximum number of active campaigns",
                    "Wait for a campaign to finish or cancel it before retrying.",
                    status_code=429,
                )
            identifier = f"judge-{uuid.uuid4().hex[:16]}"
            job = CampaignJob(
                campaign_id=identifier,
                request=request,
                mode="live" if request.provider == "openai" else "prerecorded",
            )
            self._jobs[identifier] = job
        self._executor.submit(self._run, job)
        return job.public()

    def get(self, campaign_id: str) -> dict[str, object]:
        return self._job(campaign_id).public()

    def events(self, campaign_id: str) -> list[dict[str, object]]:
        job = self._job(campaign_id)
        with self._lock:
            return [dict(item) for item in job.events]

    def cancel(self, campaign_id: str) -> dict[str, object]:
        job = self._job(campaign_id)
        job.cancelled.set()
        with self._lock:
            if job.status == "queued":
                job.status = "cancelled"
                job.updated_at = datetime.now(tz=UTC).isoformat()
        return job.public()

    def _job(self, campaign_id: str) -> CampaignJob:
        if not _safe_id(campaign_id):
            raise JudgeAPIError(
                "campaign_id_invalid", "Invalid campaign id", "Use the id returned by POST /api/campaigns."
            )
        with self._lock:
            job = self._jobs.get(campaign_id)
        if job is None:
            raise JudgeAPIError(
                "campaign_not_found",
                "Campaign does not exist",
                "Use the id returned by POST /api/campaigns.",
                status_code=404,
            )
        return job

    def _run(self, job: CampaignJob) -> None:
        if job.cancelled.is_set():
            return
        self._update(job, "running", "campaign_started", "Campaign worker started")
        try:
            if job.request.provider == "replay":
                result = self._run_replay(job)
            else:
                result = self._run_live(job)
            if job.cancelled.is_set():
                self._update(job, "cancelled", "campaign_cancelled", "Campaign cancelled")
                return
            with self._lock:
                job.result = result
            self._update(job, "completed", "campaign_completed", "Campaign completed")
        except JudgeAPIError as exc:
            with self._lock:
                job.error = exc.payload()["error"]
            self._update(job, "failed", "campaign_failed", str(exc))
        except Exception as exc:  # noqa: BLE001 - background errors become sanitized
            with self._lock:
                job.error = {
                    "code": "campaign_failed",
                    "message": f"Campaign failed: {exc.__class__.__name__}",
                    "remediation": "Use Replay or inspect the server logs.",
                }
            self._update(job, "failed", "campaign_failed", "Campaign failed")

    def _run_replay(self, job: CampaignJob) -> dict[str, object]:
        bundle = self.project / "examples/build_week_2026/campaign-v1"
        gate = verify_public_campaign_bundle(bundle)
        summary = CampaignAggregation.model_validate_json(
            (bundle / "campaign_summary.json").read_text(encoding="utf-8")
        )
        self._event(
            job,
            "facts_loaded",
            f"Loaded {summary.metrics.completed_cells} cells and {summary.metrics.total_weeks} weeks",
        )
        return {
            "source": "committed-public-bundle",
            "campaign_id": gate.campaign_id,
            "completed_cells": summary.metrics.completed_cells,
            "total_weeks": summary.metrics.total_weeks,
            "valid_rate": summary.metrics.valid_rate,
            "fallback_rate": summary.metrics.fallback_rate,
        }

    def _run_live(self, job: CampaignJob) -> dict[str, object]:
        status = self.providers.status()["providers"]["openai"]
        if not status["api_key_configured"]:
            raise JudgeAPIError(
                "openai_key_missing",
                "Live campaign requires a server-side OpenAI key",
                "Configure OPENAI_API_KEY on the server or choose Replay.",
                status_code=503,
            )
        if not status["game_runtime_configured"]:
            raise JudgeAPIError(
                "game_runtime_missing",
                "Live campaign requires a configured real game runtime",
                "Set GAME_PROJECT_PATH and GODOT_BIN on the server or choose Replay.",
                status_code=503,
            )
        if self.live_runner is None:
            raise JudgeAPIError(
                "live_runner_unavailable",
                "Live campaign runner is not enabled in this deployment",
                "Use Replay or start the native Judge API with its governed live runner.",
                status_code=503,
            )
        return self.live_runner(job)

    def _event(self, job: CampaignJob, event_type: str, message: str) -> None:
        with self._lock:
            job.events.append(
                {
                    "sequence": len(job.events) + 1,
                    "type": event_type,
                    "message": message,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }
            )
            job.updated_at = datetime.now(tz=UTC).isoformat()

    def _update(self, job: CampaignJob, status: str, event_type: str, message: str) -> None:
        with self._lock:
            job.status = status
            job.updated_at = datetime.now(tz=UTC).isoformat()
        self._event(job, event_type, message)


class JudgeService:
    def __init__(
        self,
        *,
        project_root: str | Path,
        environment: Mapping[str, str] | None = None,
        openai_client_factory: Callable[..., Any] = OpenAI,
        live_runner: Callable[[CampaignJob], dict[str, object]] | None = None,
    ) -> None:
        self.project = Path(project_root).resolve()
        self.providers = ProviderService(
            project_root=self.project,
            environment=environment,
            openai_client_factory=openai_client_factory,
        )
        self.campaigns = CampaignService(
            project_root=self.project,
            provider_service=self.providers,
            live_runner=live_runner,
        )

    def experiment(self, experiment_id: str) -> dict[str, object]:
        if experiment_id != PUBLIC_EXPERIMENT_ID or not _safe_id(experiment_id):
            raise JudgeAPIError(
                "experiment_not_found",
                "Only the committed public experiment is available",
                f"Use {PUBLIC_EXPERIMENT_ID}.",
                status_code=404,
            )
        bundle = self.project / "examples/build_week_2026/experiment-v1"
        gate = verify_public_repair_bundle(bundle)
        record = RepairExperimentRecord.model_validate_json(
            (bundle / "repair_experiment.json").read_text(encoding="utf-8")
        )
        return {
            "schema_version": "judge-public-experiment-v1",
            "experiment_id": gate.experiment_id,
            "status": gate.status,
            "decision": record.decision.value,
            "decision_reason": record.decision_reason,
            "hypothesis": record.plan.hypothesis,
            "mechanism_class": record.plan.mechanism_class,
            "comparison": record.comparison.model_dump(mode="json"),
            "cohorts": [item.model_dump(mode="json") for item in record.snapshots],
            "gates": [item.model_dump(mode="json") for item in record.gates],
            "patch": record.patch.model_dump(mode="json"),
            "codex": record.codex.model_dump(mode="json"),
            "mode": "prerecorded",
        }


def parse_json_body(content: bytes, model: type[BaseModel]) -> BaseModel:
    if len(content) > MAX_REQUEST_BYTES:
        raise JudgeAPIError(
            "request_too_large",
            "Request body exceeds 32 KiB",
            "Send only the documented bounded fields.",
            status_code=413,
        )
    try:
        payload = json.loads(content or b"{}")
        return model.model_validate(payload)
    except (json.JSONDecodeError, ValueError) as exc:
        raise JudgeAPIError(
            "request_invalid",
            "Request body does not match the endpoint schema",
            "Remove unknown fields, including any API key, and use documented limits.",
        ) from exc


def _safe_id(value: str) -> bool:
    return 1 <= len(value) <= 64 and all(char.islower() or char.isdigit() or char == "-" for char in value)


def _game_available(value: str | None) -> bool:
    if not value:
        return False
    path = Path(value)
    return path.is_dir() and (path / "project.godot").is_file()


__all__ = [
    "CampaignCreateRequest",
    "JudgeAPIError",
    "JudgeService",
    "MAX_REQUEST_BYTES",
    "ProviderTestRequest",
    "parse_json_body",
]
