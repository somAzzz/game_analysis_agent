"""Judge adapter over the shared local/API persona campaign service."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from .campaign_contract import CampaignPersona, CampaignRequest
from .persona_campaign_service import run_persona_campaign
from .persona_gateway import PersonaProvider


class LiveCampaignJob(Protocol):
    campaign_id: str
    request: Any
    cancelled: Any


class JudgeLiveCampaignError(RuntimeError):
    """Raised when a provider campaign cannot produce complete truthful evidence."""


def run_judge_persona_campaign(
    job: LiveCampaignJob,
    *,
    project_root: str | Path,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Run vLLM or OpenAI through the same service, Godot probe, and publisher."""

    project = Path(project_root).resolve()
    game = Path(str(environment.get("GAME_PROJECT_PATH", ""))).expanduser().resolve()
    try:
        provider = PersonaProvider(str(job.request.provider))
    except ValueError as exc:
        raise JudgeLiveCampaignError("unsupported Judge action provider") from exc
    if provider not in {PersonaProvider.VLLM, PersonaProvider.OPENAI}:
        raise JudgeLiveCampaignError("Judge runner accepts vllm or openai only")

    cell_count = len(job.request.personas) * len(job.request.seeds)
    request = CampaignRequest(
        campaign_id=job.campaign_id,
        personas=tuple(CampaignPersona(item) for item in job.request.personas),
        seeds=tuple(job.request.seeds),
        max_weeks=job.request.max_weeks,
        provider=provider,
        concurrency=min(cell_count, 4),
        report_root="reports/judge-campaigns",
    )
    result = run_persona_campaign(
        project_root=project,
        game_root=game,
        request=request,
        bundle_dir=f"reports/judge-bundles/{job.campaign_id}",
        view_dir="frontend/public/live-playthrough",
        environment=environment,
        resume=True,
        external_cancelled=job.cancelled.is_set,
    )
    cells = result.get("cells")
    completed_cells = int(cells.get("completed", 0)) if isinstance(cells, dict) else 0
    if completed_cells != cell_count:
        raise JudgeLiveCampaignError(
            f"provider campaign completed {completed_cells}/{cell_count} cells"
        )
    return {
        **result,
        "schema_version": "judge-provider-campaign-result-v1",
        "source": f"fresh-{provider.value}-godot-campaign",
        "completed_cells": completed_cells,
        "completed_weeks": result.get("weeks", 0),
    }


# Backward-compatible name for callers outside this repository.
def run_judge_live_campaign(
    job: LiveCampaignJob,
    *,
    project_root: str | Path,
    environment: Mapping[str, str],
) -> dict[str, object]:
    return run_judge_persona_campaign(
        job,
        project_root=project_root,
        environment=environment,
    )


__all__ = [
    "JudgeLiveCampaignError",
    "run_judge_live_campaign",
    "run_judge_persona_campaign",
]
