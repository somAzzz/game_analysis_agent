"""Tests for the Build Week P0.1 inventory."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from game_analysis_agent.build_week_inventory import (
    collect_inventory,
    strict_exit_code,
    write_inventory,
)
from tools.build_week_inventory import _display_path


def _scope(path: Path, *, license_status: str = "approved") -> Path:
    payload = {
        "schema_version": "build-week-scope-v1",
        "project_name": "Playtest Forge",
        "track": "Developer Tools",
        "required_game_files": ["project.godot", "scripts/tools/RunSimulation.gd"],
        "repositories": [
            {"id": "analysis", "required": True, "license_status": license_status},
            {"id": "game", "required": True, "license_status": license_status},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fake_git_runner(command: list[str] | tuple[str, ...], cwd: Path | None) -> tuple[int, str, str]:
    joined = " ".join(command)
    if "rev-parse --is-inside-work-tree" in joined:
        return 0, "true", ""
    if "rev-parse HEAD^{tree}" in joined:
        return 0, "b" * 40, ""
    if "rev-parse HEAD" in joined:
        return 0, "a" * 40, ""
    if "branch --show-current" in joined:
        return 0, "test-branch", ""
    if "status --porcelain" in joined:
        return 0, "", ""
    if command[0] in {"node", "npm", "uv", "ruff", "docker", "godot", "godot4"}:
        return 0, "1.0.0", ""
    return 1, "", "not available"


def test_collect_inventory_redacts_external_game_path(tmp_path: Path) -> None:
    repo = tmp_path / "analysis"
    game = tmp_path / "private" / "study-in-germany"
    repo.mkdir()
    (game / "scripts/tools").mkdir(parents=True)
    (game / "project.godot").write_text("[application]\n", encoding="utf-8")
    (game / "scripts/tools/RunSimulation.gd").write_text("extends SceneTree\n")
    scope = _scope(tmp_path / "scope.json")

    payload = collect_inventory(
        repo,
        game_project_path=game,
        scope_path=scope,
        environ={},
        now=datetime(2026, 7, 16, tzinfo=UTC),
        command_runner=_fake_git_runner,
    )

    assert payload["generated_at"] == "2026-07-16T00:00:00+00:00"
    assert payload["analysis_repository"]["path"] == "."
    assert payload["game_repository"]["path"] == "<external>/study-in-germany"
    assert str(tmp_path) not in json.dumps(payload)
    assert payload["game_repository"]["missing_required_files"] == []
    assert payload["readiness"] == {"status": "ready", "blockers": [], "blocker_count": 0}


def test_collect_inventory_reports_unknown_game_without_guessing(tmp_path: Path) -> None:
    repo = tmp_path / "analysis"
    repo.mkdir()
    scope = _scope(tmp_path / "scope.json")

    payload = collect_inventory(
        repo,
        scope_path=scope,
        environ={},
        command_runner=_fake_git_runner,
    )

    game = payload["game_repository"]
    assert game["status"] == "not_configured"
    assert game["path"] == "unknown"
    assert game["revision"] == "unknown"
    assert {item["code"] for item in payload["readiness"]["blockers"]} == {
        "game_repository_unavailable",
        "required_game_file_missing",
    }
    assert strict_exit_code(payload) == 1


def test_collect_inventory_accepts_verified_materialized_game(tmp_path: Path) -> None:
    repo = tmp_path / "analysis"
    game = repo / "reports" / "game-source"
    repo.mkdir()
    (game / "scripts/tools").mkdir(parents=True)
    (game / "project.godot").write_text("[application]\n", encoding="utf-8")
    (game / "scripts/tools/RunSimulation.gd").write_text("extends SceneTree\n")
    (game / ".playtest-forge-source.json").write_text(
        json.dumps(
            {
                "schema_version": "build-week-game-materialized-v1",
                "commit": "a" * 40,
                "tree": "b" * 40,
                "archive_sha256": "c" * 64,
                "content_tree_sha256": "d" * 64,
            }
        ),
        encoding="utf-8",
    )
    scope = _scope(tmp_path / "scope.json")

    payload = collect_inventory(
        repo,
        game_project_path=game,
        scope_path=scope,
        environ={},
        command_runner=_fake_git_runner,
    )

    source = payload["game_repository"]
    assert source["status"] == "available"
    assert source["source_type"] == "materialized_bundle"
    assert source["revision"] == "a" * 40
    assert payload["readiness"]["status"] == "ready"


def test_license_review_is_a_strict_blocker(tmp_path: Path) -> None:
    repo = tmp_path / "analysis"
    game = tmp_path / "game"
    repo.mkdir()
    (game / "scripts/tools").mkdir(parents=True)
    (game / "project.godot").write_text("", encoding="utf-8")
    (game / "scripts/tools/RunSimulation.gd").write_text("", encoding="utf-8")
    scope = _scope(tmp_path / "scope.json", license_status="review_required")

    payload = collect_inventory(
        repo,
        game_project_path=game,
        scope_path=scope,
        environ={},
        command_runner=_fake_git_runner,
    )

    license_blockers = [
        item for item in payload["readiness"]["blockers"] if item["code"] == "license_review_required"
    ]
    assert [item["message"] for item in license_blockers] == [
        "license review required: analysis",
        "license review required: game",
    ]
    assert strict_exit_code(payload) == 1


def test_write_inventory_replaces_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "nested/inventory.json"
    output.parent.mkdir()
    output.write_text("stale", encoding="utf-8")

    written = write_inventory(output, {"schema_version": "test", "status": "ok"})

    assert written == output
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "schema_version": "test",
        "status": "ok",
    }
    assert list(output.parent.glob("*.tmp")) == []


def test_rejects_unknown_scope_schema(tmp_path: Path) -> None:
    repo = tmp_path / "analysis"
    repo.mkdir()
    scope = _scope(tmp_path / "scope.json")
    payload = json.loads(scope.read_text(encoding="utf-8"))
    payload["schema_version"] = "future-scope"
    scope.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        collect_inventory(repo, scope_path=scope, environ={})


def test_cli_display_path_redacts_external_location(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    assert _display_path(root / "reports/inventory.json", root) == "reports/inventory.json"
    assert _display_path(tmp_path / "private/inventory.json", root) == "<external>/inventory.json"
