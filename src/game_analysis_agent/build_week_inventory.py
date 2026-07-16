"""Machine-readable Build Week scope and environment inventory.

The inventory is intentionally observational. Missing tools and repositories
are reported as unavailable or unknown instead of being inferred from plans or
developer-specific paths. No environment values or credentials are copied into
the output.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "build-week-inventory-v1"
SCOPE_SCHEMA_VERSION = "build-week-scope-v1"
UNKNOWN = "unknown"
DEFAULT_SCOPE_FILE = "config/build_week_2026_scope.json"

CommandRunner = Callable[[Sequence[str], Path | None], tuple[int, str, str]]


def collect_inventory(
    repo_root: str | Path,
    *,
    game_project_path: str | Path | None = None,
    scope_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    now: datetime | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Collect a sanitized inventory for the analysis and game repositories."""

    root = Path(repo_root).resolve()
    env = dict(os.environ if environ is None else environ)
    scope_file = Path(scope_path).resolve() if scope_path else root / DEFAULT_SCOPE_FILE
    scope = _read_scope(scope_file)
    runner = command_runner or _run_command
    configured_game = game_project_path or env.get("GAME_PROJECT_PATH")
    game_path = Path(configured_game).expanduser().resolve() if configured_game else None

    analysis_repo = _git_inventory(root, root=root, runner=runner)
    game_repo = _game_inventory(
        game_path,
        root=root,
        required_files=scope["required_game_files"],
        runner=runner,
    )
    tools = _collect_tools(env=env, runner=runner)
    blockers = _inventory_blockers(analysis_repo, game_repo, scope)

    timestamp = now or datetime.now(tz=UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp.astimezone(UTC).isoformat(),
        "scope": scope,
        "host": {
            "system": platform.system() or UNKNOWN,
            "release": platform.release() or UNKNOWN,
            "machine": platform.machine() or UNKNOWN,
            "python_implementation": platform.python_implementation() or UNKNOWN,
        },
        "analysis_repository": analysis_repo,
        "game_repository": game_repo,
        "tools": tools,
        "readiness": {
            "status": "ready" if not blockers else "incomplete",
            "blockers": blockers,
            "blocker_count": len(blockers),
        },
    }


def write_inventory(path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Atomically write an inventory JSON document."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_name = handle.name
        os.replace(temporary_name, destination)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
    return destination


def strict_exit_code(payload: Mapping[str, Any]) -> int:
    """Return zero only when the inventory has no readiness blockers."""

    readiness = payload.get("readiness")
    if not isinstance(readiness, Mapping):
        return 1
    return 0 if readiness.get("status") == "ready" else 1


def _read_scope(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Build Week scope file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Build Week scope file is invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Build Week scope must be a JSON object: {path}")
    if payload.get("schema_version") != SCOPE_SCHEMA_VERSION:
        raise ValueError(
            "Build Week scope schema_version must be "
            f"{SCOPE_SCHEMA_VERSION!r}: {path}"
        )
    required_files = payload.get("required_game_files")
    if not isinstance(required_files, list) or not all(
        isinstance(item, str) and item for item in required_files
    ):
        raise ValueError("Build Week scope requires a non-empty required_game_files list")
    return payload


def _git_inventory(path: Path, *, root: Path, runner: CommandRunner) -> dict[str, Any]:
    display_path = _display_path(path, root=root)
    if not path.is_dir():
        return {
            "status": "unavailable",
            "path": display_path,
            "revision": UNKNOWN,
            "tree_revision": UNKNOWN,
            "branch": UNKNOWN,
            "dirty": UNKNOWN,
            "changed_file_count": UNKNOWN,
        }

    inside_code, inside_out, _ = runner(
        ["git", "rev-parse", "--is-inside-work-tree"], path
    )
    if inside_code != 0 or inside_out.strip() != "true":
        return {
            "status": "not_git",
            "path": display_path,
            "revision": UNKNOWN,
            "tree_revision": UNKNOWN,
            "branch": UNKNOWN,
            "dirty": UNKNOWN,
            "changed_file_count": UNKNOWN,
        }

    revision = _git_value(path, ["rev-parse", "HEAD"], runner)
    tree_revision = _git_value(path, ["rev-parse", "HEAD^{tree}"], runner)
    branch = _git_value(path, ["branch", "--show-current"], runner) or "detached"
    status_code, status_out, _ = runner(
        ["git", "status", "--porcelain", "--untracked-files=normal"], path
    )
    if status_code == 0:
        changed_count: int | str = len(
            [line for line in status_out.splitlines() if line.strip()]
        )
        dirty: bool | str = changed_count > 0
    else:
        changed_count = UNKNOWN
        dirty = UNKNOWN
    return {
        "status": "available",
        "path": display_path,
        "revision": revision or UNKNOWN,
        "tree_revision": tree_revision or UNKNOWN,
        "branch": branch,
        "dirty": dirty,
        "changed_file_count": changed_count,
    }


def _game_inventory(
    path: Path | None,
    *,
    root: Path,
    required_files: Sequence[str],
    runner: CommandRunner,
) -> dict[str, Any]:
    if path is None:
        return {
            "status": "not_configured",
            "path": UNKNOWN,
            "revision": UNKNOWN,
            "tree_revision": UNKNOWN,
            "branch": UNKNOWN,
            "dirty": UNKNOWN,
            "changed_file_count": UNKNOWN,
            "required_files": {item: "unknown" for item in required_files},
            "missing_required_files": list(required_files),
        }
    inventory = _git_inventory(path, root=root, runner=runner)
    required_status = {
        item: "present" if (path / item).is_file() else "missing" for item in required_files
    }
    inventory["required_files"] = required_status
    inventory["missing_required_files"] = [
        item for item, status in required_status.items() if status != "present"
    ]
    return inventory


def _collect_tools(*, env: Mapping[str, str], runner: CommandRunner) -> dict[str, Any]:
    godot_override = env.get("GODOT_BIN")
    tool_specs: dict[str, tuple[list[str], list[str]]] = {
        "node": (["node"], ["--version"]),
        "npm": (["npm"], ["--version"]),
        "uv": (["uv"], ["--version"]),
        "ruff": (["ruff"], ["--version"]),
        "docker": (["docker"], ["--version"]),
    }
    tools = {
        name: _command_inventory(candidates, args, runner=runner)
        for name, (candidates, args) in tool_specs.items()
    }
    godot_candidates = [godot_override] if godot_override else ["godot", "godot4"]
    tools["godot"] = _command_inventory(godot_candidates, ["--version"], runner=runner)
    tools["python"] = {
        "status": "available",
        "command": Path(sys.executable).name,
        "version": platform.python_version(),
    }

    docker_command = tools["docker"].get("command")
    if tools["docker"]["status"] == "available" and isinstance(docker_command, str):
        code, output, error = runner(
            [docker_command, "info", "--format", "{{.ServerVersion}}"], None
        )
        tools["docker_daemon"] = {
            "status": "available" if code == 0 else "error",
            "command": "docker info",
            "version": _first_line(output) if code == 0 else UNKNOWN,
            "error": "" if code == 0 else _safe_error(error),
        }
    else:
        tools["docker_daemon"] = {
            "status": "unavailable",
            "command": "docker info",
            "version": UNKNOWN,
            "error": "",
        }
    return tools


def _command_inventory(
    candidates: Sequence[str | None],
    version_args: Sequence[str],
    *,
    runner: CommandRunner,
) -> dict[str, Any]:
    executable = next(
        (
            candidate
            for candidate in candidates
            if candidate and (Path(candidate).is_file() or shutil.which(candidate))
        ),
        None,
    )
    display_command = Path(executable).name if executable else next(
        (Path(item).name for item in candidates if item), UNKNOWN
    )
    if executable is None:
        return {
            "status": "unavailable",
            "command": display_command,
            "version": UNKNOWN,
            "error": "",
        }
    code, output, error = runner([executable, *version_args], None)
    if code != 0:
        return {
            "status": "error",
            "command": display_command,
            "version": UNKNOWN,
            "error": _safe_error(error or output),
        }
    return {
        "status": "available",
        "command": display_command,
        "version": _first_line(output or error) or UNKNOWN,
        "error": "",
    }


def _inventory_blockers(
    analysis_repo: Mapping[str, Any],
    game_repo: Mapping[str, Any],
    scope: Mapping[str, Any],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if analysis_repo.get("status") != "available":
        blockers.append(
            {"code": "analysis_repository_unavailable", "message": "analysis Git repository unavailable"}
        )
    if game_repo.get("status") != "available":
        blockers.append(
            {"code": "game_repository_unavailable", "message": "canonical game Git repository unavailable"}
        )
    for item in game_repo.get("missing_required_files", []):
        blockers.append(
            {"code": "required_game_file_missing", "message": f"missing game file: {item}"}
        )
    repositories = scope.get("repositories", [])
    if isinstance(repositories, list):
        for repository in repositories:
            if not isinstance(repository, Mapping):
                continue
            if repository.get("required") and repository.get("license_status") != "approved":
                blockers.append(
                    {
                        "code": "license_review_required",
                        "message": f"license review required: {repository.get('id', UNKNOWN)}",
                    }
                )
    return blockers


def _git_value(path: Path, args: Sequence[str], runner: CommandRunner) -> str:
    code, output, _ = runner(["git", *args], path)
    return output.strip() if code == 0 else ""


def _display_path(path: Path, *, root: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return f"<external>/{path.name}"
    return "." if not relative.parts else relative.as_posix()


def _run_command(command: Sequence[str], cwd: Path | None) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", exc.__class__.__name__
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _first_line(value: str) -> str:
    return value.strip().splitlines()[0].strip() if value.strip() else ""


def _safe_error(value: str) -> str:
    first_line = _first_line(value)
    if not first_line:
        return UNKNOWN
    sanitized = first_line.replace(str(Path.home()), "<home>")
    sanitized = re.sub(r"/(?:Users|home)/[^/\s]+", "/<user>", sanitized)
    sanitized = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+", r"C:\\<user>", sanitized)
    return sanitized[:240]
