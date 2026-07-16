"""Bounded native OpenAI persona campaign used by Judge Mode."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from .build_week_campaign import LiveCampaignExecutor, build_live_source_identity
from .campaign_contract import CampaignPersona, CampaignRequest
from .campaign_runner import CampaignRunner
from .persona_gateway import PersonaProvider
from .persona_gateway_factory import build_persona_gateway
from .persona_runtime import PersonaCancellationToken, PersonaRuntimeSettings
from .settings import Settings


class LiveCampaignJob(Protocol):
    campaign_id: str
    request: Any
    cancelled: Any


class JudgeLiveCampaignError(RuntimeError):
    """Raised when a live campaign cannot produce complete truthful evidence."""


def run_judge_live_campaign(
    job: LiveCampaignJob,
    *,
    project_root: str | Path,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Run the bounded API request without provider fallback or secret output."""

    project = Path(project_root).resolve()
    game = Path(str(environment.get("GAME_PROJECT_PATH", ""))).expanduser().resolve()
    runtime_env = dict(environment)
    runtime_env["PERSONA_PROVIDER"] = "openai"
    persona_settings = PersonaRuntimeSettings.from_env(runtime_env)
    cancellation = PersonaCancellationToken()
    built = build_persona_gateway(
        persona_settings,
        project_root=project,
        cancellation=cancellation,
    )
    cell_count = len(job.request.personas) * len(job.request.seeds)
    concurrency = min(cell_count, persona_settings.limits.max_concurrency, 4)
    built.gateway.validate_campaign(
        runs=cell_count,
        weeks=job.request.max_weeks,
        concurrency=concurrency,
    )
    request = CampaignRequest(
        campaign_id=job.campaign_id,
        personas=tuple(CampaignPersona(item) for item in job.request.personas),
        seeds=tuple(job.request.seeds),
        max_weeks=job.request.max_weeks,
        provider=PersonaProvider.OPENAI,
        concurrency=concurrency,
        report_root="reports/judge-live",
    )
    source = build_live_source_identity(
        project_root=project,
        game_root=game,
        request=request,
        model=persona_settings.openai_model,
    )
    settings = Settings(
        godot_bin=str(environment.get("GODOT_BIN", "godot4")),
        game_project_path=game,
    )
    executor = LiveCampaignExecutor(
        gateway=built.gateway,
        settings=settings,
        external_cancelled=job.cancelled.is_set,
    )
    summary = CampaignRunner(
        project_root=project,
        request=request,
        source=source,
        executor=executor,
        cancellation=cancellation,
    ).run(resume=False)
    provider = _provider_evidence(project, summary.results)
    if not summary.submittable:
        raise JudgeLiveCampaignError(
            f"live campaign did not complete every cell: {summary.status_counts}"
        )
    return {
        "schema_version": "judge-live-campaign-result-v1",
        "source": "fresh-openai-godot-campaign",
        "campaign_id": summary.campaign_id,
        "provider": "openai",
        "mode": "live",
        "model": persona_settings.openai_model,
        "completed_cells": sum(summary.status_counts.values()),
        "completed_weeks": sum(item.completed_weeks for item in summary.results),
        "status_counts": summary.status_counts,
        "calls_used": built.gateway.calls_used,
        "provider_evidence": provider,
        "manifest": summary.manifest_path.relative_to(project).as_posix(),
    }


def _provider_evidence(project: Path, results: tuple[Any, ...]) -> dict[str, object]:
    response_ids: list[str] = []
    models: set[str] = set()
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    call_count = 0
    for result in results:
        for artifact in result.artifacts:
            if not artifact.path.endswith("playthrough.jsonl"):
                continue
            for line in (project / artifact.path).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                for call in row.get("persona_calls", []):
                    metadata = call.get("metadata") or {}
                    if call.get("status") != "completed" or metadata.get("mode") != "live":
                        continue
                    call_count += 1
                    response_id = str(metadata.get("response_id", ""))
                    if response_id and len(response_ids) < 8:
                        response_ids.append(response_id)
                    model = str(metadata.get("model", ""))
                    if model:
                        models.add(model)
                    usage = metadata.get("usage") or {}
                    for key in totals:
                        value = usage.get(key)
                        if isinstance(value, int):
                            totals[key] += value
    return {
        "call_count": call_count,
        "models": sorted(models),
        "response_ids": response_ids,
        "usage": totals,
        "outputs_recorded": False,
    }


__all__ = ["JudgeLiveCampaignError", "run_judge_live_campaign"]
