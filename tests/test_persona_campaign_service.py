from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent import build_week_campaign
from game_analysis_agent.build_week_campaign import (
    PersonaCampaignExecutor,
    TargetSelectionError,
    build_provider_source_identity,
)
from game_analysis_agent.campaign_contract import (
    CampaignCellResult,
    CampaignManifest,
    CampaignRequest,
    build_campaign_cells,
)
from game_analysis_agent.persona_campaign_service import (
    PersonaCampaignServiceError,
    _CampaignSessionPublisher,
    _clear_view_evidence,
    _provider_call_count,
    run_persona_campaign,
)
from game_analysis_agent.persona_gateway import PersonaProvider, PersonaProviderMode
from game_analysis_agent.playthrough_view import PlaythroughViewError, truth_label_for


def _request(provider: str = "vllm") -> CampaignRequest:
    return CampaignRequest(
        campaign_id=f"{provider}-newbie-seed-42-20w",
        personas=("newbie",),
        seeds=(42,),
        max_weeks=20,
        provider=provider,
        concurrency=1,
        report_root="reports/persona-campaigns",
    )


def _game_root(tmp_path: Path) -> Path:
    game = tmp_path / "game"
    game.mkdir()
    (game / "project.godot").write_text("[application]\n", encoding="utf-8")
    (game / ".playtest-forge-source.json").write_text(
        json.dumps(
            {
                "commit": "c" * 40,
                "tree": "d" * 40,
                "archive_sha256": "e" * 64,
            }
        ),
        encoding="utf-8",
    )
    return game


def test_truth_labels_distinguish_replay_local_and_live() -> None:
    assert truth_label_for("replay", "replay") == "prerecorded-real-godot-replay"
    assert truth_label_for("vllm", "local") == "local-vllm-real-godot"
    assert truth_label_for("openai", "live") == "live-openai-real-godot"
    with pytest.raises(PlaythroughViewError, match="unsupported"):
        truth_label_for("openai", "replay")


def test_persona_executor_accepts_local_but_rejects_replay() -> None:
    class Gateway:
        provider = PersonaProvider.VLLM
        mode = PersonaProviderMode.LOCAL

    executor = PersonaCampaignExecutor(gateway=Gateway(), settings=object())  # type: ignore[arg-type]
    assert executor.gateway.provider == PersonaProvider.VLLM

    Gateway.provider = PersonaProvider.REPLAY
    Gateway.mode = PersonaProviderMode.REPLAY
    with pytest.raises(ValueError, match="non-Replay"):
        PersonaCampaignExecutor(gateway=Gateway(), settings=object())  # type: ignore[arg-type]


def test_local_source_identity_is_truthful_and_hash_pinned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    game = _game_root(tmp_path)

    def fake_git(_project: Path, *args: str) -> str:
        if args[0] == "status":
            return ""
        if args[-1] == "HEAD^{tree}":
            return "b" * 40
        return "a" * 40

    monkeypatch.setattr(build_week_campaign, "_git", fake_git)
    source = build_provider_source_identity(
        project_root=project,
        game_root=game,
        request=_request(),
        provider=PersonaProvider.VLLM,
        mode=PersonaProviderMode.LOCAL,
        model="qwen-local",
    )
    assert source.provider == PersonaProvider.VLLM
    assert source.provider_mode == PersonaProviderMode.LOCAL
    assert source.provider_revision == "model:qwen-local"


def test_source_identity_rejects_provider_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    game = _game_root(tmp_path)
    monkeypatch.setattr(build_week_campaign, "_git", lambda *_args: "")
    with pytest.raises(TargetSelectionError, match="provider mismatch"):
        build_provider_source_identity(
            project_root=project,
            game_root=game,
            request=_request(),
            provider=PersonaProvider.OPENAI,
            mode=PersonaProviderMode.LIVE,
            model="gpt",
        )


def test_full_semester_preflight_requires_worst_case_call_budget(tmp_path: Path) -> None:
    game = _game_root(tmp_path)
    with pytest.raises(PersonaCampaignServiceError, match="need at least 40"):
        run_persona_campaign(
            project_root=tmp_path,
            game_root=game,
            request=_request(),
            bundle_dir="reports/public",
            view_dir="frontend/public/live-playthrough",
            environment={
                "PERSONA_MAX_RUNS": "1",
                "PERSONA_MAX_WEEKS": "20",
                "PERSONA_MAX_CONCURRENCY": "1",
                "PERSONA_MAX_CALLS": "39",
            },
        )


def test_campaign_rejects_destructive_view_target_before_execution(tmp_path: Path) -> None:
    game = _game_root(tmp_path)
    with pytest.raises(PersonaCampaignServiceError, match="view_dir must stay"):
        run_persona_campaign(
            project_root=tmp_path,
            game_root=game,
            request=_request(),
            bundle_dir="reports/public",
            view_dir="src",
            environment={},
        )


def test_session_publisher_exposes_only_sanitized_week_progress(tmp_path: Path) -> None:
    request = _request()
    view = tmp_path / "frontend/public/live-playthrough"
    publisher = _CampaignSessionPublisher(
        view=view,
        request=request,
        truth_label="local-vllm-real-godot",
        model="qwen-local",
    )
    cell = build_campaign_cells(request)[0]
    output = tmp_path / "cell"
    output.mkdir()
    secret = "sk-" + "never-publish"
    row = {
        "week": 1,
        "chosen_actions": ["study_library"],
        "triggered_event_id": "arrival",
        "event_choice_id": "arrival.choice_01",
        "state_after": {"week": 2, "money": 100, "stress": 20, "private": secret},
        "llm_summary": secret,
        "validation": {"valid": False, "fallback_used": True},
        "persona_calls": [
            {"raw": secret},
            {
                "phase": "decision",
                "status": "failed",
                "metadata": {
                    "response_id": "",
                    "attempt_count": 2,
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 30,
                        "total_tokens": 130,
                    },
                },
                "error": {
                    "category": "malformed_response",
                    "message": f"schema rejected {secret}",
                },
            },
        ],
    }
    (output / "playthrough.jsonl").write_text(
        json.dumps(row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    publisher.progress(
        cell,
        output,
        {
            "phase": "completed",
            "week": 1,
            "completed_weeks": 1,
            "finished": False,
        },
    )

    session_text = (view / "session.json").read_text(encoding="utf-8")
    session = json.loads(session_text)
    assert session["status"] == "running"
    assert session["progress"]["completed_weeks"] == 1
    assert session["latest"] == {
        "cell_id": cell.cell_id,
        "persona": "newbie",
        "seed": 42,
        "phase": "completed",
        "week": 1,
        "completed_weeks": 1,
        "max_weeks": 20,
        "selected_action_ids": ["study_library"],
        "triggered_event_id": "arrival",
        "selected_choice_id": "arrival.choice_01",
        "state_after": {"week": 2, "money": 100, "stress": 20},
    }
    assert secret not in session_text
    assert "llm_summary" not in session_text
    assert "persona_calls" not in session_text
    assert session["diagnostics"] == {
        "logical_calls": 1,
        "http_attempts": 2,
        "fallback_count": 1,
        "failure_count": 1,
        "response_metadata_missing_attempts": 1,
        "known_usage": {"input_tokens": 100, "output_tokens": 30, "total_tokens": 130},
        "failures": [
            {
                "cell_id": cell.cell_id,
                "persona": "newbie",
                "seed": 42,
                "week": 1,
                "phase": "decision",
                "category": "malformed_response",
                "message": "schema rejected <redacted>",
                "attempts": 2,
            }
        ],
    }

    publisher.progress(
        cell,
        output,
        {
            "phase": "completed",
            "week": 19,
            "completed_weeks": 19,
            "finished": True,
        },
    )
    finished_session = json.loads((view / "session.json").read_text(encoding="utf-8"))
    assert finished_session["status"] == "running"
    assert finished_session["cells"][0]["status"] == "running"
    assert finished_session["cells"][0]["phase"] == "game_finished_pending_validation"
    assert finished_session["latest"]["phase"] == "game_finished_pending_validation"


def test_view_cleanup_preserves_live_session_file(tmp_path: Path) -> None:
    view = tmp_path / "live-playthrough"
    (view / "cells").mkdir(parents=True)
    (view / "cells/old.json").write_text("{}", encoding="utf-8")
    (view / "manifest.json").write_text("{}", encoding="utf-8")
    (view / "session.json").write_text('{"status":"running"}', encoding="utf-8")

    _clear_view_evidence(view)

    assert (view / "session.json").is_file()
    assert not (view / "manifest.json").exists()
    assert not (view / "cells").exists()


def test_session_publisher_hydrates_resume_candidates_and_counts_retained_calls(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/build_week_2026/playthrough-v1/source"
    campaign = source / "reports/playthrough-evidence/campaigns/playthrough-evidence-full-v1"
    manifest = CampaignManifest.model_validate_json(
        (campaign / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    cell = manifest.cells[0]
    result = CampaignCellResult.model_validate_json(
        (source / cell.output_dir / "cell_result.json").read_text(encoding="utf-8")
    )
    view = tmp_path / "live-playthrough"
    publisher = _CampaignSessionPublisher(
        view=view,
        request=manifest.request,
        truth_label="prerecorded-real-godot-replay",
        model="fixture",
    )

    publisher.hydrate((result,))

    session = json.loads((view / "session.json").read_text(encoding="utf-8"))
    retained = next(item for item in session["cells"] if item["cell_id"] == cell.cell_id)
    assert retained["status"] == "retained"
    assert retained["phase"] == "resume_candidate_pending_validation"
    assert session["progress"]["retained_cells"] == 1
    assert session["progress"]["completed_cells"] == 0
    rows = [
        json.loads(line)
        for line in (source / cell.output_dir / "playthrough.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    expected_calls = sum(len(row.get("persona_calls") or []) for row in rows)
    assert _provider_call_count(source, (result,)) == expected_calls
