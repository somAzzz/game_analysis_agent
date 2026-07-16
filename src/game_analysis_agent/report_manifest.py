"""Traceable report manifests for generated gameplay-agent reports.

The manifest is intentionally sidecar metadata: existing CSV/JSONL files
remain the source of truth, while ``report_manifest.json`` gives humans and
frontends a stable entry point for provenance, run ids, file inventory, and
trace references.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_FILE = "report_manifest.json"
REPORT_INDEX_FILE = "report_index.json"
SCHEMA_VERSION = "trace-manifest-v2"
MATERIALIZED_GAME_MARKER = ".playtest-forge-source.json"
MATERIALIZED_GAME_SCHEMA = "build-week-game-materialized-v1"


def write_report_manifest(
    report_dir: Path,
    *,
    report_type: str,
    run_id: str | None = None,
    command: str = "",
    parameters: dict[str, Any] | None = None,
    source_files: list[str | Path] | None = None,
    generated_files: list[str | Path] | None = None,
    status: str = "completed",
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``report_manifest.json`` and return the payload."""

    report_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = report_dir / MANIFEST_FILE
    previous = _read_json(manifest_path)
    stable_run_id = str(run_id or previous.get("run_id") or report_dir.name)
    stable_report_type = str(previous.get("report_type") or report_type)
    generated_at = previous.get("generated_at") or datetime.now(tz=UTC).isoformat()
    operation = {
        "command": command,
        "report_type": report_type,
        "status": status,
        "updated_at": datetime.now(tz=UTC).isoformat(),
        "parameters": parameters or {},
    }

    source_refs = [_file_ref(report_dir, item) for item in source_files or []]
    generated_refs = [_file_ref(report_dir, item) for item in generated_files or []]
    inventory = [
        _file_ref(report_dir, path)
        for path in sorted(report_dir.rglob("*"))
        if path.is_file() and path.name != MANIFEST_FILE
    ]

    trace = _trace_index(report_dir, stable_run_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "report_id": f"{stable_report_type}:{stable_run_id}",
        "report_type": stable_report_type,
        "run_id": stable_run_id,
        "status": status,
        "generated_at": generated_at,
        "updated_at": datetime.now(tz=UTC).isoformat(),
        "command": command or previous.get("command", ""),
        "operations": [*(previous.get("operations") or []), operation],
        "parameters": {**(previous.get("parameters") or {}), **(parameters or {})},
        "summary": {**(previous.get("summary") or {}), **(summary or {})},
        "source_files": _dedupe_refs([*(previous.get("source_files") or []), *source_refs]),
        "generated_files": _dedupe_refs(
            [*(previous.get("generated_files") or []), *generated_refs]
        ),
        "file_inventory": inventory,
        "trace": trace,
        "provenance": collect_provenance(),
        "frontend": {
            "detail_href": "index.html",
            "primary_trace_file": trace.get("primary_file", ""),
            "manifest_href": MANIFEST_FILE,
        },
    }
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def write_reports_index(reports_root: Path) -> dict[str, Any]:
    """Write a frontend-friendly index over every report manifest."""

    manifests = []
    for path in sorted(reports_root.rglob(MANIFEST_FILE)):
        payload = _read_json(path)
        if not payload:
            continue
        rel_dir = path.parent.relative_to(reports_root)
        manifests.append(
            {
                "report_id": payload.get("report_id", ""),
                "report_type": payload.get("report_type", ""),
                "run_id": payload.get("run_id", ""),
                "status": payload.get("status", ""),
                "generated_at": payload.get("generated_at", ""),
                "updated_at": payload.get("updated_at", ""),
                "summary": payload.get("summary", {}),
                "manifest": str(rel_dir / MANIFEST_FILE),
                "detail_href": str(rel_dir / "index.html"),
                "trace": payload.get("trace", {}),
            }
        )
    index = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "report_count": len(manifests),
        "reports": manifests,
    }
    reports_root.mkdir(parents=True, exist_ok=True)
    (reports_root / REPORT_INDEX_FILE).write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return index


def _trace_index(report_dir: Path, run_id: str) -> dict[str, Any]:
    raw_path = _first_existing(
        report_dir,
        ["raw_runs.jsonl", "boundary_runs.jsonl", "playthrough.jsonl"],
    )
    if raw_path is None:
        return {"primary_file": "", "runs": [], "steps": []}
    if raw_path.name == "playthrough.jsonl":
        steps = []
        for line_no, row in _read_jsonl_with_lines(raw_path):
            steps.append(
                {
                    "run_id": run_id,
                    "step_id": str(row.get("step_id", "")),
                    "week": row.get("week"),
                    "trace_file": raw_path.name,
                    "line": line_no,
                    "actions": row.get("chosen_actions", []),
                    "event_id": row.get("triggered_event_id", ""),
                    "event_choice_id": row.get("event_choice_id", ""),
                }
            )
        return {
            "primary_file": raw_path.name,
            "runs": [
                {
                    "run_id": run_id,
                    "trace_file": raw_path.name,
                    "line_start": 1 if steps else 0,
                    "line_end": len(steps),
                    "step_count": len(steps),
                }
            ],
            "steps": steps,
        }

    runs = []
    for line_no, row in _read_jsonl_with_lines(raw_path):
        run_value = row.get("run_id", line_no - 1)
        weekly_log = row.get("weekly_log") or []
        runs.append(
            {
                "run_id": run_value,
                "trace_file": raw_path.name,
                "line": line_no,
                "policy": row.get("policy", ""),
                "seed": row.get("seed"),
                "difficulty": row.get("difficulty", ""),
                "scenario": row.get("scenario", ""),
                "final_ending_id": row.get("final_ending_id") or row.get("ending_id", ""),
                "final_week": row.get("final_week") or (row.get("final_state") or {}).get("week"),
                "step_count": len(weekly_log) if isinstance(weekly_log, list) else 0,
            }
        )
    return {"primary_file": raw_path.name, "runs": runs, "steps": []}


def _file_ref(report_dir: Path, item: str | Path) -> dict[str, Any]:
    raw_path = item if isinstance(item, Path) else Path(item)
    path = raw_path if raw_path.is_absolute() else report_dir / raw_path
    exists = path.exists()
    rel = _display_artifact_path(path, report_dir=report_dir)
    return {
        "path": rel,
        "exists": exists,
        "bytes": path.stat().st_size if exists and path.is_file() else 0,
        "sha256": _sha256(path) if exists and path.is_file() else "",
        "modified_at": (
            datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
            if exists and path.is_file()
            else ""
        ),
    }


def collect_provenance() -> dict[str, Any]:
    """Return reproducibility metadata for the Agent and canonical game."""

    root = Path(__file__).resolve().parents[2]
    game_root = Path(
        os.environ.get(
            "GAME_PROJECT_PATH",
            "/home/bo/projects/python/study-in-germany",
        )
    )
    godot_bin = os.environ.get("GODOT_BIN", "godot4")
    agent_source = runtime_source_fingerprint(root)
    game_source = game_source_fingerprint(game_root)
    return {
        "agent_repository": _git_provenance(root, display_path="<project>"),
        "game_repository": _game_provenance(game_root),
        "runtime": {
            "python": platform.python_version(),
            "python_executable": Path(sys.executable).name,
            "platform": platform.platform(),
            "godot": _command_version(godot_bin),
        },
        "fingerprints": {
            "runtime_source_sha256": agent_source,
            "game_source_sha256": game_source,
            "execution_source_sha256": _combine_source_fingerprints(agent_source, game_source),
            "config_sha256": _tree_sha256(root / "config"),
            "prompts_sha256": _tree_sha256(root / "prompts"),
        },
    }


def runtime_source_fingerprint(root: Path) -> str:
    """Hash the executable Agent source, including uncommitted changes.

    A git commit plus a dirty flag cannot distinguish two different dirty
    worktrees. Matrix resume and report provenance need the exact code bytes
    that produced an artifact, so this digest deliberately covers only
    runtime-owned inputs and excludes generated/cache files.
    """

    root = root.resolve()
    candidates: list[Path] = []
    for directory in ("src", "tools", "scripts", "config", "prompts"):
        base = root / directory
        if base.is_dir():
            candidates.extend(path for path in base.rglob("*") if path.is_file())
    candidates.extend(
        path
        for name in ("pyproject.toml", "uv.lock", "Dockerfile", "docker-compose.yml")
        if (path := root / name).is_file()
    )

    digest = hashlib.sha256()
    included = 0
    for path in sorted(set(candidates)):
        relative = path.relative_to(root)
        if (
            "__pycache__" in relative.parts
            or path.suffix in {".pyc", ".pyo", ".orig"}
            or any(part.startswith(".") for part in relative.parts)
        ):
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        included += 1
    return digest.hexdigest() if included else ""


def game_source_fingerprint(root: Path) -> str:
    """Hash canonical Godot code/content while excluding reports and imports."""

    root = root.resolve()
    candidates: list[Path] = []
    for directory in ("autoload", "data", "scenes", "scripts"):
        base = root / directory
        if base.is_dir():
            candidates.extend(path for path in base.rglob("*") if path.is_file())
    project_file = root / "project.godot"
    if project_file.is_file():
        candidates.append(project_file)

    digest = hashlib.sha256()
    included = 0
    for path in sorted(set(candidates)):
        relative = path.relative_to(root)
        if (
            "__pycache__" in relative.parts
            or path.suffix in {".import", ".pyc", ".pyo", ".orig"}
            or any(part.startswith(".") for part in relative.parts)
        ):
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        included += 1
    return digest.hexdigest() if included else ""


def execution_source_fingerprint(agent_root: Path, game_root: Path) -> str:
    """Return one identity for every local source tree affecting a matrix run."""

    return _combine_source_fingerprints(
        runtime_source_fingerprint(agent_root),
        game_source_fingerprint(game_root),
    )


def _combine_source_fingerprints(agent: str, game: str) -> str:
    payload = f"agent:{agent}\ngame:{game}\n".encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _git_provenance(path: Path, *, display_path: str) -> dict[str, Any]:
    base = {"path": display_path, "available": False, "commit": "", "dirty": None}
    if not (path / ".git").exists():
        return base
    commit = _run_capture(["git", "-C", str(path), "rev-parse", "HEAD"])
    status = _run_capture(["git", "-C", str(path), "status", "--porcelain"])
    return {
        **base,
        "available": bool(commit),
        "commit": commit,
        "dirty": bool(status) if commit else None,
    }


def _game_provenance(path: Path) -> dict[str, Any]:
    marker = _read_json(path / MATERIALIZED_GAME_MARKER)
    if marker.get("schema_version") == MATERIALIZED_GAME_SCHEMA:
        return {
            "path": "<game>",
            "available": True,
            "source_type": "materialized_bundle",
            "commit": str(marker.get("commit", "")),
            "tree": str(marker.get("tree", "")),
            "archive_sha256": str(marker.get("archive_sha256", "")),
            "content_tree_sha256": str(marker.get("content_tree_sha256", "")),
            "file_count": marker.get("file_count", 0),
            "dirty": False,
        }
    return _git_provenance(path, display_path="<game>")


@functools.lru_cache(maxsize=8)
def _command_version(command: str) -> dict[str, Any]:
    resolved = shutil.which(command)
    if not resolved:
        fallback = shutil.which("godot") if command == "godot4" else None
        resolved = fallback
    if not resolved:
        return {"available": False, "command": command, "version": ""}
    version = _run_capture([resolved, "--version"], timeout=5)
    return {
        "available": bool(version),
        "command": Path(resolved).name,
        "version": version,
    }


def _display_artifact_path(path: Path, *, report_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(report_dir.resolve()).as_posix()
    except ValueError:
        pass
    project_root = Path(__file__).resolve().parents[2]
    try:
        relative = resolved.relative_to(project_root)
    except ValueError:
        return f"<external>/{resolved.name}"
    return f"<project>/{relative.as_posix()}"


def _run_capture(command: list[str], *, timeout: int = 5) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _tree_sha256(root: Path) -> str:
    if not root.exists():
        return ""
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dedupe_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for item in items:
        path = str(item.get("path", ""))
        if path:
            by_path[path] = item
    return [by_path[path] for path in sorted(by_path)]


def _first_existing(report_dir: Path, names: list[str]) -> Path | None:
    for name in names:
        path = report_dir / name
        if path.exists():
            return path
    return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_with_lines(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append((line_no, payload))
    return rows


__all__ = [
    "MANIFEST_FILE",
    "REPORT_INDEX_FILE",
    "SCHEMA_VERSION",
    "collect_provenance",
    "execution_source_fingerprint",
    "game_source_fingerprint",
    "runtime_source_fingerprint",
    "write_report_manifest",
    "write_reports_index",
]
