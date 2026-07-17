from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent.build_week_game_pin import (
    RUNTIME_OVERLAY_FILE,
    GamePinError,
    load_game_pin,
    prepare_embedded_game_runtime,
    verify_materialized_game_tree,
)
from game_analysis_agent.report_manifest import _game_provenance

ROOT = Path(__file__).resolve().parents[1]


def test_prepares_verified_writable_runtime_with_audited_overlay(tmp_path: Path) -> None:
    output = tmp_path / "game-runtime"
    result = prepare_embedded_game_runtime(ROOT, output)

    assert result["status"] == "prepared"
    marker = json.loads((output / RUNTIME_OVERLAY_FILE).read_text(encoding="utf-8"))
    overlay = marker["overlays"][0]
    assert overlay["path"] == "scripts/tools/RunInteractiveProbe.gd"
    assert overlay["canonical_sha256"] != overlay["runtime_sha256"]
    assert (output / overlay["path"]).read_bytes() == (ROOT / overlay["source"]).read_bytes()
    assert {item["path"] for item in marker["overlays"]} == {
        "scripts/tools/RunInteractiveProbe.gd",
        "autoload/DataRegistry.gd",
        "scenes/main/Main.gd",
        "scripts/data/DataLoader.gd",
        "scripts/data/EventChoiceDef.gd",
        "scripts/data/EventDef.gd",
        "data/localization/events.json",
    }
    localization = next(
        item for item in marker["overlays"] if item["path"] == "data/localization/events.json"
    )
    assert localization["canonical_sha256"] is None
    assert (output / localization["path"]).read_bytes() == (
        ROOT / localization["source"]
    ).read_bytes()
    assert _game_provenance(output)["source_type"] == "embedded_runtime_overlay"
    verify_materialized_game_tree(
        ROOT / "demo/study-in-germany",
        load_game_pin(ROOT / "config/build_week_2026_game_pin.json"),
    )


def test_refuses_to_replace_an_unmanaged_destination(tmp_path: Path) -> None:
    output = tmp_path / "game-runtime"
    output.mkdir()
    (output / "keep.txt").write_text("owner data", encoding="utf-8")

    with pytest.raises(GamePinError, match="unmanaged runtime"):
        prepare_embedded_game_runtime(ROOT, output, replace=True)

    assert (output / "keep.txt").read_text(encoding="utf-8") == "owner data"


def test_refuses_minimal_forged_runtime_marker(tmp_path: Path) -> None:
    output = tmp_path / "game-runtime"
    output.mkdir()
    pin = load_game_pin(ROOT / "config/build_week_2026_game_pin.json")
    (output / RUNTIME_OVERLAY_FILE).write_text(
        json.dumps(
            {
                "schema_version": "build-week-game-runtime-overlay-v1",
                "base_commit": pin["pin"]["commit"],
            }
        ),
        encoding="utf-8",
    )
    (output / "keep.txt").write_text("owner data", encoding="utf-8")

    with pytest.raises(GamePinError, match="different provenance"):
        prepare_embedded_game_runtime(ROOT, output, replace=True)

    assert (output / "keep.txt").is_file()


def test_replaces_only_intact_runtime_with_known_generated_files(tmp_path: Path) -> None:
    output = tmp_path / "game-runtime"
    prepare_embedded_game_runtime(ROOT, output)
    generated = output / ".godot/imported/cache.bin"
    generated.parent.mkdir(parents=True)
    generated.write_bytes(b"cache")

    result = prepare_embedded_game_runtime(ROOT, output, replace=True)

    assert result["status"] == "prepared"
    assert not generated.exists()


def test_refuses_runtime_with_unmanaged_extra_file(tmp_path: Path) -> None:
    output = tmp_path / "game-runtime"
    prepare_embedded_game_runtime(ROOT, output)
    (output / "owner.txt").write_text("preserve", encoding="utf-8")

    with pytest.raises(GamePinError, match="unmanaged files"):
        prepare_embedded_game_runtime(ROOT, output, replace=True)

    assert (output / "owner.txt").is_file()
