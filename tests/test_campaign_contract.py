"""Tests for deterministic, source-bound campaign evidence contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from game_analysis_agent.campaign_contract import (
    CampaignArtifact,
    CampaignCellResult,
    CampaignCellState,
    CampaignManifest,
    CampaignRequest,
    CampaignSourceIdentity,
    CampaignStopReason,
    build_campaign_cells,
    citation_for_row,
    resume_compatible,
)


def _request(**overrides) -> CampaignRequest:  # noqa: ANN003
    payload = {
        "campaign_id": "test-campaign-v1",
        "personas": ["newbie", "study"],
        "seeds": [42, 43],
        "max_weeks": 20,
        "difficulty": "normal",
        "scenario": "default_first_semester",
        "provider": "replay",
        "concurrency": 2,
        "report_root": "reports/campaigns",
    }
    payload.update(overrides)
    return CampaignRequest.model_validate(payload)


def _source(**overrides) -> CampaignSourceIdentity:  # noqa: ANN003
    payload = {
        "agent_commit": "a" * 40,
        "agent_tree": "b" * 40,
        "agent_dirty": False,
        "game_commit": "c" * 40,
        "game_tree": "d" * 40,
        "game_archive_sha256": "e" * 64,
        "campaign_config_sha256": "f" * 64,
        "provider": "replay",
        "provider_mode": "replay",
        "provider_revision": "fixture:c180208d",
    }
    payload.update(overrides)
    return CampaignSourceIdentity.model_validate(payload)


def _completed_result(request=None, source=None) -> CampaignCellResult:  # noqa: ANN001
    request = request or build_campaign_cells(_request())[0]
    source = source or _source()
    started = datetime.now(tz=UTC)
    row = {"week": 1, "money": 420, "stress": 55}
    citation = citation_for_row(
        request,
        week=1,
        artifact_path=f"{request.output_dir}/playthrough.jsonl",
        line_number=1,
        row=row,
    )
    artifact = CampaignArtifact(
        path=f"{request.output_dir}/playthrough.jsonl",
        sha256="1" * 64,
        media_type="application/x-ndjson",
        record_count=1,
    )
    return CampaignCellResult(
        request=request,
        request_fingerprint=request.fingerprint(),
        source=source,
        source_fingerprint=source.fingerprint(),
        state="completed",
        stop_reason="game_finished",
        completed_weeks=1,
        started_at=started,
        completed_at=started + timedelta(seconds=2),
        artifacts=[artifact],
        citations=[citation],
    )


def test_cells_are_deterministic_isolated_and_cover_cartesian_matrix() -> None:
    request = _request()

    first = build_campaign_cells(request)
    second = build_campaign_cells(request)

    assert first == second
    assert len(first) == 4
    assert len({cell.cell_id for cell in first}) == 4
    assert len({cell.output_dir for cell in first}) == 4
    assert first[0].cell_id.startswith("newbie-seed-42-")
    assert all(cell.campaign_fingerprint == request.fingerprint() for cell in first)


def test_tracked_build_week_request_is_valid_and_has_eighteen_cells() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (root / "config/build_week_2026_campaign.json").read_text(encoding="utf-8")
    )
    request = CampaignRequest.model_validate(payload)

    assert len(build_campaign_cells(request)) == 18
    assert len(request.fingerprint()) == 64


@pytest.mark.parametrize(
    "overrides",
    [
        {"personas": ["newbie", "newbie"]},
        {"seeds": [42, 42]},
        {"seeds": [-1]},
        {"concurrency": 5},
        {"report_root": "../private"},
        {"report_root": "C:\\private"},
        {"provider": "auto"},
    ],
)
def test_request_rejects_ambiguous_or_unsafe_inputs(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        _request(**overrides)


def test_source_identity_requires_truthful_provider_mode_and_clean_full_hashes() -> None:
    with pytest.raises(ValidationError, match="provider_mode"):
        _source(provider="openai", provider_mode="replay")
    with pytest.raises(ValidationError):
        _source(agent_commit="abc")
    with pytest.raises(ValidationError):
        _source(agent_dirty=True)


def test_manifest_rejects_missing_or_reordered_cells() -> None:
    request = _request()
    source = _source()
    cells = build_campaign_cells(request)
    manifest = CampaignManifest(
        request=request,
        request_fingerprint=request.fingerprint(),
        source=source,
        source_fingerprint=source.fingerprint(),
        cells=cells,
        created_at=datetime.now(tz=UTC),
    )
    assert manifest.cells == cells

    with pytest.raises(ValidationError, match="deterministic matrix"):
        CampaignManifest(
            request=request,
            request_fingerprint=request.fingerprint(),
            source=source,
            source_fingerprint=source.fingerprint(),
        cells=tuple(reversed(cells)),
            created_at=datetime.now(tz=UTC),
        )


def test_terminal_state_and_citations_fail_closed() -> None:
    result = _completed_result()
    assert result.state == CampaignCellState.COMPLETED

    payload = result.model_dump()
    payload["state"] = "failed"
    payload["stop_reason"] = "provider_failed"
    payload["error"] = "provider failed"
    with pytest.raises(ValidationError, match="zero completed weeks"):
        CampaignCellResult.model_validate(payload)

    payload = result.model_dump()
    payload["citations"][0]["seed"] = 999
    with pytest.raises(ValidationError, match="crosses campaign cell"):
        CampaignCellResult.model_validate(payload)


def test_partial_and_cancelled_are_not_mislabeled_as_success() -> None:
    completed = _completed_result()
    partial = completed.model_dump()
    partial.update(
        state="partial",
        stop_reason="provider_failed",
        completed_weeks=1,
        error="timeout",
    )
    parsed = CampaignCellResult.model_validate(partial)
    assert parsed.state == CampaignCellState.PARTIAL

    cancelled = completed.model_dump()
    cancelled.update(
        state="cancelled",
        stop_reason=CampaignStopReason.CANCELLED,
        completed_weeks=0,
        error="cancelled by reviewer",
        citations=[],
        artifacts=[],
    )
    parsed = CampaignCellResult.model_validate(cancelled)
    assert parsed.state == CampaignCellState.CANCELLED


def test_resume_requires_exact_request_source_and_completed_state() -> None:
    result = _completed_result()
    assert resume_compatible(result, result.request, result.source) is True

    changed_source = _source(provider_revision="fixture:changed")
    assert resume_compatible(result, result.request, changed_source) is False

    partial_payload = result.model_dump()
    partial_payload.update(
        state="partial",
        stop_reason="probe_failed",
        completed_weeks=1,
        error="probe stopped",
    )
    partial = CampaignCellResult.model_validate(partial_payload)
    assert resume_compatible(partial, partial.request, partial.source) is False


def test_citation_hash_changes_with_raw_row() -> None:
    request = build_campaign_cells(_request())[0]
    first = citation_for_row(
        request,
        week=1,
        artifact_path="reports/run/playthrough.jsonl",
        line_number=1,
        row={"stress": 55},
    )
    changed = citation_for_row(
        request,
        week=1,
        artifact_path="reports/run/playthrough.jsonl",
        line_number=1,
        row={"stress": 56},
    )
    assert first.record_sha256 != changed.record_sha256
