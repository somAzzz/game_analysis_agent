"""Verify and export the exact Build Week reference-game Git object."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "build-week-game-pin-v1"
VERIFICATION_SCHEMA_VERSION = "build-week-game-verification-v1"
MATERIALIZED_PROVENANCE_FILE = ".playtest-forge-source.json"
MATERIALIZED_SCHEMA_VERSION = "build-week-game-materialized-v1"
RUNTIME_OVERLAY_FILE = ".playtest-forge-runtime-overlay.json"
RUNTIME_OVERLAY_SCHEMA_VERSION = "build-week-game-runtime-overlay-v1"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GamePinError(RuntimeError):
    """Raised when the pinned game source cannot be verified exactly."""


def load_game_pin(path: str | Path) -> dict[str, Any]:
    """Load and validate the game-pin manifest."""

    pin_path = Path(path)
    try:
        payload = json.loads(pin_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GamePinError(f"game pin not found: {pin_path.name}") from exc
    except json.JSONDecodeError as exc:
        raise GamePinError(f"game pin is invalid JSON: {pin_path.name}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise GamePinError(f"game pin schema_version must be {SCHEMA_VERSION!r}")

    repository = _mapping(payload, "repository")
    pin = _mapping(payload, "pin")
    packaging = _mapping(payload, "packaging")
    required_files = payload.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        raise GamePinError("game pin requires a non-empty required_files list")
    if not isinstance(repository.get("name"), str) or "/" not in repository["name"]:
        raise GamePinError("game pin repository.name must be an owner/name slug")
    if not _SHA1.fullmatch(str(pin.get("commit", ""))):
        raise GamePinError("game pin commit must be a full 40-character Git SHA")
    if not _SHA1.fullmatch(str(pin.get("tree", ""))):
        raise GamePinError("game pin tree must be a full 40-character Git SHA")
    if not _SHA256.fullmatch(str(pin.get("archive_sha256", ""))):
        raise GamePinError("game pin archive_sha256 must be a SHA-256 digest")
    if not _SHA256.fullmatch(str(pin.get("content_tree_sha256", ""))):
        raise GamePinError("game pin content_tree_sha256 must be a SHA-256 digest")
    if not isinstance(pin.get("file_count"), int) or pin["file_count"] < 1:
        raise GamePinError("game pin file_count must be a positive integer")
    if packaging.get("mode") not in {"private_competition_bundle", "public_bundle"}:
        raise GamePinError("game pin packaging.mode is unsupported")

    seen_paths: set[str] = set()
    for index, item in enumerate(required_files):
        if not isinstance(item, dict):
            raise GamePinError(f"required_files[{index}] must be an object")
        file_path = _safe_git_path(item.get("path"), index=index)
        if file_path in seen_paths:
            raise GamePinError(f"duplicate required file: {file_path}")
        seen_paths.add(file_path)
        if not _SHA1.fullmatch(str(item.get("git_blob", ""))):
            raise GamePinError(f"required file has invalid git_blob: {file_path}")
        if not _SHA256.fullmatch(str(item.get("sha256", ""))):
            raise GamePinError(f"required file has invalid sha256: {file_path}")
    return payload


def verify_game_pin(source_repo: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the repository, commit, tree, archive, and required file hashes."""

    source = Path(source_repo).expanduser().resolve()
    if not source.is_dir():
        raise GamePinError("game source repository is unavailable")
    repository = _mapping(manifest, "repository")
    pin = _mapping(manifest, "pin")
    expected_slug = str(repository["name"])
    commit = str(pin["commit"])

    inside = _git_text(source, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        raise GamePinError("game source is not a Git worktree")
    remote = _git_text(source, "remote", "get-url", "origin")
    if _repository_slug(remote) != expected_slug.lower():
        raise GamePinError(
            f"game source origin mismatch: expected {expected_slug}, got {_repository_slug(remote)}"
        )
    _git(source, "cat-file", "-e", f"{commit}^{{commit}}")

    actual_tree = _git_text(source, "rev-parse", f"{commit}^{{tree}}")
    if actual_tree != pin["tree"]:
        raise GamePinError(f"game tree mismatch: expected {pin['tree']}, got {actual_tree}")

    files = [
        line
        for line in _git_text(source, "ls-tree", "-r", "--name-only", commit).splitlines()
        if line
    ]
    if len(files) != pin["file_count"]:
        raise GamePinError(
            f"game file count mismatch: expected {pin['file_count']}, got {len(files)}"
        )

    verified_files: list[dict[str, str]] = []
    for item in manifest["required_files"]:
        file_path = str(item["path"])
        actual_blob = _git_text(source, "rev-parse", f"{commit}:{file_path}")
        if actual_blob != item["git_blob"]:
            raise GamePinError(
                f"game blob mismatch for {file_path}: expected {item['git_blob']}, got {actual_blob}"
            )
        content = _git_bytes(source, "show", f"{commit}:{file_path}")
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != item["sha256"]:
            raise GamePinError(
                f"game content mismatch for {file_path}: "
                f"expected {item['sha256']}, got {actual_sha256}"
            )
        verified_files.append(
            {"path": file_path, "git_blob": actual_blob, "sha256": actual_sha256}
        )

    archive = _git_bytes(source, "archive", "--format=tar", commit)
    archive_sha256 = hashlib.sha256(archive).hexdigest()
    if archive_sha256 != pin["archive_sha256"]:
        raise GamePinError(
            "game archive mismatch: "
            f"expected {pin['archive_sha256']}, got {archive_sha256}"
        )

    checkout_revision = _git_text(source, "rev-parse", "HEAD")
    status = _git_text(source, "status", "--porcelain", "--untracked-files=normal")
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "verified",
        "repository": expected_slug,
        "source_path": f"<external>/{source.name}",
        "commit": commit,
        "tree": actual_tree,
        "archive_sha256": archive_sha256,
        "file_count": len(files),
        "required_files": verified_files,
        "checkout": {
            "revision": checkout_revision,
            "matches_pin": checkout_revision == commit,
            "dirty": bool(status),
            "changed_file_count": len([line for line in status.splitlines() if line.strip()]),
        },
        "packaging": dict(_mapping(manifest, "packaging")),
    }


def write_pinned_archive(
    source_repo: str | Path,
    manifest: Mapping[str, Any],
    destination: str | Path,
) -> Path:
    """Verify and atomically write the exact pinned Git archive."""

    verification = verify_game_pin(source_repo, manifest)
    source = Path(source_repo).expanduser().resolve()
    archive = _git_bytes(source, "archive", "--format=tar", verification["commit"])
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(archive)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_name = handle.name
        os.replace(temporary_name, output)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
    return output


def materialize_game_tree(
    source_repo: str | Path,
    manifest: Mapping[str, Any],
    destination: str | Path,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    """Safely materialize the pinned archive into an independently usable tree."""

    verification = verify_game_pin(source_repo, manifest)
    source = Path(source_repo).expanduser().resolve()
    output = Path(destination).expanduser().resolve()
    if output == source or output in source.parents or source in output.parents:
        raise GamePinError("materialized game destination overlaps the source repository")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if not replace:
            raise GamePinError("materialized game destination already exists; use --replace")
        _require_managed_destination(output, manifest=manifest)

    archive = _git_bytes(source, "archive", "--format=tar", verification["commit"])
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    backup: Path | None = None
    try:
        _extract_regular_archive(archive, temporary)
        content_inventory = _materialized_inventory(temporary)
        if len(content_inventory) != verification["file_count"]:
            raise GamePinError(
                "materialized game file count mismatch: "
                f"expected {verification['file_count']}, got {len(content_inventory)}"
            )
        _verify_materialized_required_files(temporary, verification["required_files"])
        content_tree_sha256 = _content_tree_sha256(content_inventory)
        if content_tree_sha256 != _mapping(manifest, "pin")["content_tree_sha256"]:
            raise GamePinError("materialized game content tree differs from the pinned snapshot")
        provenance = {
            "schema_version": MATERIALIZED_SCHEMA_VERSION,
            "repository": verification["repository"],
            "commit": verification["commit"],
            "tree": verification["tree"],
            "archive_sha256": verification["archive_sha256"],
            "content_tree_sha256": content_tree_sha256,
            "file_count": verification["file_count"],
            "files": content_inventory,
            "public_distribution": verification["packaging"].get(
                "public_distribution", False
            ),
        }
        (temporary / MATERIALIZED_PROVENANCE_FILE).write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if output.exists():
            backup = output.with_name(f".{output.name}.previous")
            if backup.exists():
                raise GamePinError("materialized game backup path already exists")
            os.replace(output, backup)
        os.replace(temporary, output)
        if backup is not None:
            shutil.rmtree(backup)
        return {
            **provenance,
            "status": "materialized",
            "path": f"<materialized>/{output.name}",
            "provenance_file": MATERIALIZED_PROVENANCE_FILE,
        }
    except Exception:
        if backup is not None and backup.exists() and not output.exists():
            os.replace(backup, output)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def verify_materialized_game_tree(
    game_root: str | Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Verify an embedded game snapshot without its upstream Git repository."""

    root = Path(game_root).expanduser().resolve()
    if not (root / "project.godot").is_file():
        raise GamePinError("materialized game is not a Godot project")
    marker_path = root / MATERIALIZED_PROVENANCE_FILE
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise GamePinError("materialized game provenance is missing or invalid") from exc
    if marker.get("schema_version") != MATERIALIZED_SCHEMA_VERSION:
        raise GamePinError("materialized game provenance schema is unsupported")

    pin = _mapping(manifest, "pin")
    packaging = _mapping(manifest, "packaging")
    expected = {
        "repository": _mapping(manifest, "repository")["name"],
        "commit": pin["commit"],
        "tree": pin["tree"],
        "archive_sha256": pin["archive_sha256"],
        "content_tree_sha256": pin["content_tree_sha256"],
        "file_count": pin["file_count"],
        "public_distribution": packaging.get("public_distribution", False),
    }
    for field, value in expected.items():
        if marker.get(field) != value:
            raise GamePinError(f"materialized game provenance mismatch: {field}")

    files = marker.get("files")
    if not isinstance(files, list) or len(files) != pin["file_count"]:
        raise GamePinError("materialized game inventory is missing or incomplete")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise GamePinError(f"materialized game inventory item {index} is invalid")
        relative = _safe_git_path(item.get("path"), index=index)
        if relative in seen:
            raise GamePinError(f"duplicate materialized game path: {relative}")
        seen.add(relative)
        digest = str(item.get("sha256", ""))
        mode = item.get("mode")
        if not _SHA256.fullmatch(digest) or not isinstance(mode, int):
            raise GamePinError(f"invalid materialized game inventory: {relative}")
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise GamePinError(f"materialized game file missing: {relative}")
        if _portable_mode(path) != mode:
            raise GamePinError(f"materialized game file mode mismatch: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise GamePinError(f"materialized game file mismatch: {relative}")
        normalized.append({"path": relative, "mode": mode, "sha256": digest})
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    expected_paths = seen | {MATERIALIZED_PROVENANCE_FILE}
    if actual_paths != expected_paths:
        raise GamePinError("materialized game file set differs from pinned inventory")
    if (
        _content_tree_sha256(normalized) != marker.get("content_tree_sha256")
        or marker.get("content_tree_sha256") != pin["content_tree_sha256"]
    ):
        raise GamePinError("materialized game content-tree hash mismatch")
    _verify_materialized_required_files(root, list(manifest["required_files"]))
    return {
        "schema_version": MATERIALIZED_SCHEMA_VERSION,
        "status": "verified",
        "path": f"<embedded>/{root.name}",
        **expected,
        "content_tree_sha256": marker["content_tree_sha256"],
    }


def prepare_embedded_game_runtime(
    project_root: str | Path,
    destination: str | Path,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    """Create a writable runtime copy from the verified embedded demo.

    The canonical demo remains byte-for-byte identical to the pinned upstream
    tree. Runtime-only adapters are copied from this repository and recorded in
    a separate overlay marker so they cannot be mistaken for game-source edits.
    """

    project = Path(project_root).expanduser().resolve()
    manifest = load_game_pin(project / "config/build_week_2026_game_pin.json")
    embedded_path = str(_mapping(manifest, "packaging").get("embedded_path", ""))
    source = (project / embedded_path).resolve()
    verification = verify_materialized_game_tree(source, manifest)
    output = Path(destination).expanduser().resolve()
    if output == source or output in source.parents or source in output.parents:
        raise GamePinError("runtime game destination overlaps the embedded source")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if not replace:
            raise GamePinError("runtime game destination already exists; use --replace")
        _require_managed_runtime_destination(
            output, project=project, source=source, verification=verification
        )

    overlay_source = project / "scripts/tools/RunInteractiveProbe.gd"
    if not overlay_source.is_file():
        raise GamePinError("runtime interactive probe is unavailable")
    overlay_relative = "scripts/tools/RunInteractiveProbe.gd"
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    backup: Path | None = None
    try:
        shutil.copytree(source, temporary, dirs_exist_ok=True)
        overlay_target = temporary / overlay_relative
        canonical_sha256 = hashlib.sha256(overlay_target.read_bytes()).hexdigest()
        shutil.copy2(overlay_source, overlay_target)
        runtime_sha256 = hashlib.sha256(overlay_target.read_bytes()).hexdigest()
        overlay = {
            "schema_version": RUNTIME_OVERLAY_SCHEMA_VERSION,
            "base_commit": verification["commit"],
            "base_tree": verification["tree"],
            "base_content_tree_sha256": verification["content_tree_sha256"],
            "overlays": [
                {
                    "path": overlay_relative,
                    "source": "scripts/tools/RunInteractiveProbe.gd",
                    "canonical_sha256": canonical_sha256,
                    "runtime_sha256": runtime_sha256,
                }
            ],
        }
        (temporary / RUNTIME_OVERLAY_FILE).write_text(
            json.dumps(overlay, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if output.exists():
            backup = output.with_name(f".{output.name}.previous")
            if backup.exists():
                raise GamePinError("runtime game backup path already exists")
            os.replace(output, backup)
        os.replace(temporary, output)
        if backup is not None:
            shutil.rmtree(backup)
        return {
            "schema_version": RUNTIME_OVERLAY_SCHEMA_VERSION,
            "status": "prepared",
            "path": f"<runtime>/{output.name}",
            "base": verification,
            "overlays": overlay["overlays"],
            "provenance_file": RUNTIME_OVERLAY_FILE,
        }
    except Exception:
        if backup is not None and backup.exists() and not output.exists():
            os.replace(backup, output)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise GamePinError(f"game pin {key} must be an object")
    return value


def _extract_regular_archive(archive: bytes, destination: Path) -> None:
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
            for member in bundle.getmembers():
                relative = _safe_archive_path(member.name)
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise GamePinError(f"unsupported game archive member type: {member.name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                if source is None:
                    raise GamePinError(f"unable to read game archive member: {member.name}")
                with source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
                target.chmod(member.mode & 0o777)
    except (tarfile.TarError, OSError) as exc:
        raise GamePinError(f"unable to materialize game archive: {exc.__class__.__name__}") from exc


def _safe_archive_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise GamePinError(f"unsafe game archive path: {value}")
    return path


def _materialized_inventory(root: Path) -> list[dict[str, Any]]:
    inventory = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        inventory.append(
            {
                "path": relative,
                "mode": _portable_mode(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return inventory


def _content_tree_sha256(inventory: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in inventory:
        digest.update(str(item["mode"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(item["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(item["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _verify_materialized_required_files(
    root: Path, required_files: list[dict[str, str]]
) -> None:
    for item in required_files:
        path = root / item["path"]
        if not path.is_file():
            raise GamePinError(f"materialized required file missing: {item['path']}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise GamePinError(f"materialized required file mismatch: {item['path']}")


def _portable_mode(path: Path) -> int:
    """Return a cross-platform Git-style regular-file mode."""

    return 0o755 if path.stat().st_mode & 0o111 else 0o644


def _require_managed_destination(path: Path, *, manifest: Mapping[str, Any]) -> None:
    try:
        verify_materialized_game_tree(path, manifest)
    except (GamePinError, OSError) as exc:
        raise GamePinError(
            "refusing to replace an unmanaged materialized game destination"
        ) from exc


def _require_managed_runtime_destination(
    path: Path,
    *,
    project: Path,
    source: Path,
    verification: Mapping[str, Any],
) -> None:
    marker = path / RUNTIME_OVERLAY_FILE
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise GamePinError("refusing to replace an unmanaged runtime game destination") from exc
    overlay_path = "scripts/tools/RunInteractiveProbe.gd"
    overlay_source = project / overlay_path
    expected_overlay = {
        "path": overlay_path,
        "source": overlay_path,
        "canonical_sha256": hashlib.sha256((source / overlay_path).read_bytes()).hexdigest(),
        "runtime_sha256": hashlib.sha256(overlay_source.read_bytes()).hexdigest(),
    }
    if payload != {
        "schema_version": RUNTIME_OVERLAY_SCHEMA_VERSION,
        "base_commit": verification["commit"],
        "base_tree": verification["tree"],
        "base_content_tree_sha256": verification["content_tree_sha256"],
        "overlays": [expected_overlay],
    }:
        raise GamePinError("refusing to replace a runtime game with different provenance")
    source_marker = source / MATERIALIZED_PROVENANCE_FILE
    runtime_marker = path / MATERIALIZED_PROVENANCE_FILE
    if runtime_marker.read_bytes() != source_marker.read_bytes():
        raise GamePinError("refusing to replace a runtime with a modified base marker")
    source_inventory = json.loads(source_marker.read_text(encoding="utf-8"))["files"]
    expected_paths = {
        item["path"] for item in source_inventory
    } | {MATERIALIZED_PROVENANCE_FILE, RUNTIME_OVERLAY_FILE}
    actual_paths: set[str] = set()
    for candidate in path.rglob("*"):
        if candidate.is_symlink():
            raise GamePinError("refusing to replace a runtime containing symlinks")
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(path).as_posix()
        actual_paths.add(relative)
        if relative in expected_paths:
            continue
        if not (
            relative == "balance_runs.jsonl"
            or relative.startswith(".godot/")
            or relative.startswith("reports/")
        ):
            raise GamePinError("refusing to replace a runtime containing unmanaged files")
    if not expected_paths.issubset(actual_paths):
        raise GamePinError("refusing to replace an incomplete runtime game")
    for item in source_inventory:
        relative = item["path"]
        candidate = path / relative
        expected_digest = (
            expected_overlay["runtime_sha256"]
            if relative == overlay_path
            else item["sha256"]
        )
        if (
            _portable_mode(candidate) != item["mode"]
            or hashlib.sha256(candidate.read_bytes()).hexdigest() != expected_digest
        ):
            raise GamePinError("refusing to replace a modified runtime game")


def _safe_git_path(value: Any, *, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise GamePinError(f"required_files[{index}].path must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise GamePinError(f"unsafe required file path: {value}")
    return path.as_posix()


def _repository_slug(remote: str) -> str:
    value = remote.strip().removesuffix(".git")
    if value.startswith("git@") and ":" in value:
        value = value.split(":", 1)[1]
    elif "://" in value:
        value = value.split("://", 1)[1]
        value = value.split("/", 1)[1] if "/" in value else value
    return value.strip("/").lower()


def _git_text(source: Path, *args: str) -> str:
    return _git(source, *args).stdout.decode("utf-8", errors="replace").strip()


def _git_bytes(source: Path, *args: str) -> bytes:
    return _git(source, *args).stdout


def _git(source: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=source,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GamePinError(f"Git command failed: git {args[0]}: {exc.__class__.__name__}") from exc
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip().splitlines()
        message = error[0] if error else "unknown Git error"
        raise GamePinError(f"Git command failed: git {args[0]}: {message[:240]}")
    return completed
