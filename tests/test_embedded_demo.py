"""Repository-only canonical Godot demo checks."""

from __future__ import annotations

from pathlib import Path

from game_analysis_agent.build_week_game_pin import (
    load_game_pin,
    verify_materialized_game_tree,
)

ROOT = Path(__file__).resolve().parents[1]


def test_embedded_study_in_germany_matches_public_game_pin() -> None:
    manifest = load_game_pin(ROOT / "config/build_week_2026_game_pin.json")

    result = verify_materialized_game_tree(ROOT / "demo/study-in-germany", manifest)

    assert result["status"] == "verified"
    assert result["public_distribution"] is True
    assert result["file_count"] == 80
