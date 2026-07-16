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
    materialize_game_tree,
    verify_game_pin,
    verify_materialized_game_tree,
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


def test_materialize_uses_pinned_tree_and_writes_provenance(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    _manifest(repo, commit, pin_path)
    (repo / "scripts/tools/RunInteractiveProbe.gd").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "later checkout without runner")
    output = tmp_path / "materialized"

    result = materialize_game_tree(repo, load_game_pin(pin_path), output)

    assert result["status"] == "materialized"
    assert result["commit"] == commit
    assert (output / "scripts/tools/RunInteractiveProbe.gd").is_file()
    provenance = json.loads(
        (output / ".playtest-forge-source.json").read_text(encoding="utf-8")
    )
    assert provenance["commit"] == commit
    assert provenance["file_count"] == len(REQUIRED_PATHS)
    assert provenance["public_distribution"] is False


def test_materialize_refuses_to_replace_unmanaged_directory(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    manifest = _manifest(repo, commit, pin_path)
    output = tmp_path / "materialized"
    output.mkdir()
    (output / "user-file.txt").write_text("preserve me", encoding="utf-8")

    with pytest.raises(GamePinError, match="unmanaged"):
        materialize_game_tree(repo, manifest, output, replace=True)

    assert (output / "user-file.txt").read_text(encoding="utf-8") == "preserve me"


def test_materialize_replaces_only_matching_managed_directory(tmp_path: Path) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    manifest = _manifest(repo, commit, pin_path)
    output = tmp_path / "materialized"
    first = materialize_game_tree(repo, manifest, output)
    (output / "extra.txt").write_text("remove", encoding="utf-8")

    second = materialize_game_tree(repo, manifest, output, replace=True)

    assert first["content_tree_sha256"] == second["content_tree_sha256"]
    assert not (output / "extra.txt").exists()
    assert not output.with_name(".materialized.previous").exists()


def test_verify_materialized_tree_detects_source_mutation_without_upstream_git(
    tmp_path: Path,
) -> None:
    repo, commit = _repository(tmp_path)
    pin_path = tmp_path / "pin.json"
    manifest = _manifest(repo, commit, pin_path)
    output = tmp_path / "embedded"
    materialize_game_tree(repo, manifest, output)

    result = verify_materialized_game_tree(output, manifest)

    assert result["status"] == "verified"
    assert result["commit"] == commit
    (output / "project.godot").write_text("mutated\n", encoding="utf-8")
    with pytest.raises(GamePinError, match="file mismatch: project.godot"):
        verify_materialized_game_tree(output, manifest)
