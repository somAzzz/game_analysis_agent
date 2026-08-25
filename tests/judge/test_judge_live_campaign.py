"""Bounded live Judge campaign wiring tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from game_analysis_agent.build_week_campaign import LiveCampaignExecutor
from game_analysis_agent.campaign_contract import (
    CampaignCellState,
    CampaignRequest,
    CampaignStopReason,
    build_campaign_cells,
)
from game_analysis_agent.judge_live_campaign import run_judge_live_campaign
from game_analysis_agent.persona_gateway import PersonaProvider, PersonaProviderMode
from game_analysis_agent.persona_runtime import PersonaCancellationToken


class _Gateway:
    provider = PersonaProvider.OPENAI
    mode = PersonaProviderMode.LIVE
    model = "gpt-test"
    calls_used = 2

    def __init__(self) -> None:
        self.cancellation = PersonaCancellationToken()
        self.validated: dict[str, int] = {}

    def validate_campaign(self, *, runs: int, weeks: int, concurrency: int) -> None:
        self.validated = {"runs": runs, "weeks": weeks, "concurrency": concurrency}


def test_live_executor_marks_fallback_evidence_partial(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    gateway = _Gateway()

    class FakeAgent:
        def __init__(self, **_kwargs) -> None:  # noqa: ANN003
            pass

        def play_through(self, *_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
            validation = SimpleNamespace(valid=False, fallback_used=True)
            return SimpleNamespace(steps=[SimpleNamespace(week=1, validation=validation)]), []

    monkeypatch.setattr("game_analysis_agent.build_week_campaign.InteractivePlayerAgent", FakeAgent)
    monkeypatch.setattr(
        "game_analysis_agent.build_week_campaign.build_probe", lambda _settings: object()
    )
    request = CampaignRequest(
        campaign_id="judge-live-test",
        personas=("newbie",),
        seeds=(42,),
        max_weeks=1,
        provider=PersonaProvider.OPENAI,
        concurrency=1,
    )
    cell = build_campaign_cells(request)[0]
    context = SimpleNamespace(cancelled=False)
    executor = LiveCampaignExecutor(
        gateway=gateway,
        settings=SimpleNamespace(),
    )

    outcome = executor(cell, tmp_path, context)

    assert outcome.state == CampaignCellState.PARTIAL
    assert outcome.stop_reason == CampaignStopReason.PROVIDER_FAILED
    assert "fallback" in outcome.error


@pytest.mark.parametrize("provider", ["vllm", "openai"])
def test_judge_provider_campaign_delegates_to_shared_service(
    monkeypatch,
    tmp_path: Path,
    provider: str,
) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    def fake_campaign_service(**kwargs):  # noqa: ANN003, ANN202
        captured.update(kwargs)
        return {
            "schema_version": "persona-campaign-service-result-v1",
            "status": "passed",
            "provider": provider,
            "mode": "local" if provider == "vllm" else "live",
            "model": "test-model",
            "cells": {"completed": 1, "requested": 1},
            "weeks": 2,
            "calls_used": 2,
        }

    monkeypatch.setattr(
        "game_analysis_agent.judge_live_campaign.run_persona_campaign",
        fake_campaign_service,
    )
    cancelled = SimpleNamespace(is_set=lambda: False)
    job = SimpleNamespace(
        campaign_id="judge-test",
        request=SimpleNamespace(
            provider=provider,
            personas=("newbie",),
            seeds=(42,),
            max_weeks=2,
        ),
        cancelled=cancelled,
    )
    secret = "sk-" + "never-serialize-this"

    output = run_judge_live_campaign(
        job,
        project_root=tmp_path,
        environment={
            "OPENAI_API_KEY": secret,
            "GAME_PROJECT_PATH": str(tmp_path / "game"),
        },
    )

    request = captured["request"]
    assert isinstance(request, CampaignRequest)
    assert request.provider.value == provider
    assert request.max_weeks == 2
    assert captured["view_dir"] == "frontend/public/live-playthrough"
    assert captured["resume"] is True
    assert captured["external_cancelled"] == cancelled.is_set
    assert output["completed_cells"] == 1
    assert output["completed_weeks"] == 2
    assert output["source"] == f"fresh-{provider}-godot-campaign"
    assert secret not in str(output)
