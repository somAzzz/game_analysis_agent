"""Tests for exact Build Week game-source pinning and export."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from game_analysis_agent.build_week_game_pin import (
    GamePinError,
    load_game_pin,
    verify_game_pin,
    write_pinned_archive,
)

REQUIRED_PATHS = (
    "project.godot",
    "scripts/tools/RunSimulation.gd",
    "scripts/tools/RunInteractiveProbe.gd",
)


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_bytes,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "study-in-germany"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "remote", "add", "origin", "git@github.com:example/study-in-germany.git")
    for index, name in enumerate(REQUIRED_PATHS):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture {index}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "canonical")
    return repo, _git(repo, "rev-parse", "HEAD").decode().strip()


def _manifest(repo: Path, commit: str, path: Path) -> dict:
    tree = _git(repo, "rev-parse", f"{commit}^{{tree}}").decode().strip()
    archive = _git(repo, "archive", "--format=tar", commit)
    names = _git(repo, "ls-tree", "-r", "--name-only", commit).decode().splitlines()
    required_files = []
    for name in REQUIRED_PATHS:
        content = _git(repo, "show", f"{commit}:{name}")
        required_files.append(
            {
                "path": name,
                "git_blob": _git(repo, "rev-parse", f"{commit}:{name}").decode().strip(),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    payload = {
        "schema_version": "build-week-game-pin-v1",
        "repository": {
            "name": "example/study-in-germany",
            "url": "https://github.com/example/study-in-germany",
        },
        "pin": {
            "commit": commit,
            "tree": tree,
            "archive_sha256": hashlib.sha256(archive).hexdigest(),
            "file_count": len(names),
        },
        "packaging": {
            "mode": "private_competition_bundle",
            "distribution_status": "test",
        },
        "required_files": required_files,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_verify_pin_uses_exact_object_not_current_checkout(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    _manifest(repo, commit, pin_path)
    (repo / "scripts/tools/RunInteractiveProbe.gd").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "later checkout without runner")

    result = verify_game_pin(repo, load_game_pin(pin_path))

    assert result["status"] == "verified"
    assert result["commit"] == commit
    assert result["checkout"]["matches_pin"] is False
    assert result["required_files"][2]["path"] == "scripts/tools/RunInteractiveProbe.gd"
    assert str(tmp_path) not in json.dumps(result)


def test_verify_pin_rejects_required_file_hash_mismatch(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    payload = _manifest(repo, commit, pin_path)
    payload["required_files"][0]["sha256"] = "0" * 64
    pin_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GamePinError, match="content mismatch"):
        verify_game_pin(repo, load_game_pin(pin_path))


def test_verify_pin_rejects_wrong_origin(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    payload = _manifest(repo, commit, pin_path)
    payload["repository"]["name"] = "another/project"
    pin_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GamePinError, match="origin mismatch"):
        verify_game_pin(repo, load_game_pin(pin_path))


def test_write_pinned_archive_is_exact_and_atomic(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    manifest = _manifest(repo, commit, pin_path)
    output = tmp_path / "bundle/game.tar"

    written = write_pinned_archive(repo, load_game_pin(pin_path), output)

    assert written == output
    assert hashlib.sha256(output.read_bytes()).hexdigest() == manifest["pin"]["archive_sha256"]
    assert list(output.parent.glob("*.tmp")) == []


def test_load_pin_rejects_unsafe_required_path(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    payload = _manifest(repo, commit, pin_path)
    payload["required_files"][0]["path"] = "../project.godot"
    pin_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GamePinError, match="unsafe"):
        load_game_pin(pin_path)
