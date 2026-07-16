"""Stable P4 delivery-contract fingerprint tests."""

from __future__ import annotations

from pathlib import Path

from game_analysis_agent.platform_delivery import platform_contract_fingerprint


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_contract_covers_runtime_and_evidence_entrypoints_but_not_gate_reviewers(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "src/game_analysis_agent/judge_live_campaign.py"
    reviewer = tmp_path / "src/game_analysis_agent/build_week_g5.py"
    recorder = tmp_path / "tools/record_platform_evidence.py"
    overlay = tmp_path / "scripts/tools/RunInteractiveProbe.gd"
    _write(runtime, "runtime = 1\n")
    _write(reviewer, "reviewer = 1\n")
    _write(recorder, "recorder = 1\n")
    _write(overlay, "extends SceneTree\n")
    baseline = platform_contract_fingerprint(tmp_path)

    _write(runtime, "runtime = 2\n")
    runtime_changed = platform_contract_fingerprint(tmp_path)
    _write(recorder, "recorder = 2\n")
    recorder_changed = platform_contract_fingerprint(tmp_path)
    _write(reviewer, "reviewer = 2\n")
    reviewer_changed = platform_contract_fingerprint(tmp_path)
    _write(overlay, "extends SceneTree\n# changed\n")
    overlay_changed = platform_contract_fingerprint(tmp_path)

    assert runtime_changed != baseline
    assert recorder_changed != runtime_changed
    assert reviewer_changed == recorder_changed
    assert overlay_changed != reviewer_changed
