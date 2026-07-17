"""Bounded live Judge campaign wiring tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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


def test_judge_live_campaign_returns_only_redacted_aggregate(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    gateway = _Gateway()
    built = SimpleNamespace(gateway=gateway)
    manifest = tmp_path / "reports/judge-live/judge-test/campaign_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    result = SimpleNamespace(completed_weeks=2, artifacts=())
    summary = SimpleNamespace(
        campaign_id="judge-test",
        manifest_path=manifest,
        results=(result,),
        status_counts={"completed": 1},
        submittable=True,
    )

    class FakeRunner:
        def __init__(self, **_kwargs) -> None:  # noqa: ANN003
            pass

        def run(self, *, resume: bool):  # noqa: ANN202
            assert resume is False
            return summary

    monkeypatch.setattr(
        "game_analysis_agent.judge_live_campaign.build_persona_gateway",
        lambda *_args, **_kwargs: built,
    )
    monkeypatch.setattr(
        "game_analysis_agent.judge_live_campaign.build_live_source_identity",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr("game_analysis_agent.judge_live_campaign.CampaignRunner", FakeRunner)
    monkeypatch.setattr(
        "game_analysis_agent.judge_live_campaign._provider_evidence",
        lambda *_args: {
            "call_count": 2,
            "models": ["gpt-test"],
            "response_ids": ["resp_1"],
            "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            "outputs_recorded": False,
        },
    )
    job = SimpleNamespace(
        campaign_id="judge-test",
        request=SimpleNamespace(personas=("newbie",), seeds=(42,), max_weeks=2),
        cancelled=SimpleNamespace(is_set=lambda: False),
    )

    secret = "sk-" + "never-serialize-this"
    output = run_judge_live_campaign(
        job,
        project_root=tmp_path,
        environment={
            "OPENAI_API_KEY": secret,
            "OPENAI_PERSONA_MODEL": "gpt-test",
            "GAME_PROJECT_PATH": str(tmp_path / "game"),
            "GODOT_BIN": "godot4",
        },
    )

    assert output["mode"] == "live"
    assert output["completed_cells"] == 1
    assert output["provider_evidence"]["response_ids"] == ["resp_1"]
    assert secret not in str(output)
    assert gateway.validated == {"runs": 1, "weeks": 2, "concurrency": 1}
