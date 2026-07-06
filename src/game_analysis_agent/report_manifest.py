"""Traceable report manifests for generated gameplay-agent reports.

The manifest is intentionally sidecar metadata: existing CSV/JSONL files
remain the source of truth, while ``report_manifest.json`` gives humans and
frontends a stable entry point for provenance, run ids, file inventory, and
trace references.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_FILE = "report_manifest.json"
REPORT_INDEX_FILE = "report_index.json"
SCHEMA_VERSION = "trace-manifest-v1"


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
                "final_week": row.get("final_week")
                or (row.get("final_state") or {}).get("week"),
                "step_count": len(weekly_log) if isinstance(weekly_log, list) else 0,
            }
        )
    return {"primary_file": raw_path.name, "runs": runs, "steps": []}


def _file_ref(report_dir: Path, item: str | Path) -> dict[str, Any]:
    raw_path = item if isinstance(item, Path) else Path(item)
    path = raw_path if raw_path.is_absolute() else report_dir / raw_path
    exists = path.exists()
    try:
        rel: Path | str = path.relative_to(report_dir)
    except ValueError:
        rel = path
    return {
        "path": str(rel),
        "exists": exists,
        "bytes": path.stat().st_size if exists and path.is_file() else 0,
        "sha256": _sha256(path) if exists and path.is_file() else "",
    }


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
    "write_report_manifest",
    "write_reports_index",
]
