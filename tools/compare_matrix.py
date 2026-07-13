#!/usr/bin/env python3
"""Strict fixed-seed comparison for two completed matrix executions."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from game_analysis_agent.agent_eval import evaluate_playthrough  # noqa: E402
from game_analysis_agent.contracts import (  # noqa: E402
    ContractKind,
    ContractValidationError,
    validate_contract_file,
    validate_trace_catalog_consistency,
)
from tools.compare_reports import compare_reports  # noqa: E402

MATRIX_MANIFEST_FILE = "matrix_manifest.json"
MATRIX_COMPARE_SUMMARY_FILE = "matrix_compare_summary.json"
MATRIX_COMPARE_SCHEMA = "matrix-compare-v1"
MATRIX_SCHEMA = "test-matrix-v1"
CELL_KINDS = {"simulation", "boundary", "persona"}
COMPLETED_CELL_STATUSES = {"completed", "skipped"}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_SAFE_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")
_CSV_COLUMNS = {
    "ending_distribution.csv": {
        "policy",
        "difficulty",
        "scenario",
        "ending_id",
        "count",
        "sample_size",
        "rate",
        "ci95_low",
        "ci95_high",
    },
    "action_pick_rates.csv": {"policy", "action_id", "count", "rate_per_run"},
    "weekly_stats.csv": {
        "policy",
        "week",
        "metric",
        "mean",
        "median",
        "p10",
        "p90",
        "min",
        "max",
    },
}


class MatrixCompareError(ValueError):
    """Raised when matrix evidence is missing, malformed, or not pairable."""


@dataclass(frozen=True)
class MatrixCompareResult:
    """Successful matrix comparison and its machine-readable output."""

    summary_path: Path
    summary: dict[str, Any]

    @property
    def exit_code(self) -> int:
        return 0


def compare_matrix_runs(
    before: str | Path,
    after: str | Path,
    *,
    output_dir: str | Path,
) -> MatrixCompareResult:
    """Pair two completed matrices and emit strict per-cell regression evidence."""

    before_path, before_manifest = _load_matrix_manifest(before, label="before")
    after_path, after_manifest = _load_matrix_manifest(after, label="after")
    _validate_matrix_pair(before_manifest, after_manifest)

    before_cells = _index_cells(before_manifest, manifest_path=before_path, label="before")
    after_cells = _index_cells(after_manifest, manifest_path=after_path, label="after")
    before_ids = set(before_cells)
    after_ids = set(after_cells)
    if before_ids != after_ids:
        raise MatrixCompareError(
            "matrix cell sets differ: "
            f"missing_after={sorted(before_ids - after_ids)}, "
            f"missing_before={sorted(after_ids - before_ids)}"
        )

    includes = _comparison_includes(before_manifest, before_path, label="before")
    after_includes = _comparison_includes(after_manifest, after_path, label="after")
    if includes != after_includes:
        raise MatrixCompareError(
            f"matrix compare.include differs: before={list(includes)}, after={list(after_includes)}"
        )

    out_dir = Path(output_dir).resolve()
    cell_rows: list[dict[str, Any]] = []
    changed_artifacts = 0
    unchanged_artifacts = 0
    comparable_cells = 0

    for cell_id in sorted(before_cells):
        before_cell = before_cells[cell_id]
        after_cell = after_cells[cell_id]
        _validate_cell_pair(before_cell, after_cell)
        before_report = Path(before_cell["report_dir"]).resolve()
        after_report = Path(after_cell["report_dir"]).resolve()
        if before_report == after_report:
            raise MatrixCompareError(
                f"cell {cell_id} reuses the same before/after report_dir: {before_report}"
            )
        _require_report_dir(before_report, cell_id=cell_id, label="before")
        _require_report_dir(after_report, cell_id=cell_id, label="after")
        _validate_report_evidence(
            before_cell,
            before_report,
            before_manifest,
            cell_id=cell_id,
            label="before",
        )
        _validate_report_evidence(
            after_cell,
            after_report,
            after_manifest,
            cell_id=cell_id,
            label="after",
        )

        row: dict[str, Any] = {
            "cell_id": cell_id,
            "run_id": before_cell["run_id"],
            "kind": before_cell["kind"],
            "seed": before_cell["parameters"]["seed"],
            "parameters": before_cell["parameters"],
            "before_report_dir": str(before_report),
            "after_report_dir": str(after_report),
            "comparable": before_cell["kind"] == "simulation",
            "artifacts": [],
            "diff_file": "",
        }
        if before_cell["kind"] == "simulation":
            comparable_cells += 1
            artifacts: list[dict[str, Any]] = []
            for relative_name in includes:
                before_artifact = before_report / relative_name
                after_artifact = after_report / relative_name
                _validate_artifact(before_artifact, cell_id=cell_id, label="before")
                _validate_artifact(after_artifact, cell_id=cell_id, label="after")
                before_sha = _sha256(before_artifact)
                after_sha = _sha256(after_artifact)
                changed = before_sha != after_sha
                changed_artifacts += int(changed)
                unchanged_artifacts += int(not changed)
                artifacts.append(
                    {
                        "path": relative_name,
                        "before_sha256": before_sha,
                        "after_sha256": after_sha,
                        "before_bytes": before_artifact.stat().st_size,
                        "after_bytes": after_artifact.stat().st_size,
                        "changed": changed,
                    }
                )

            diff_path = out_dir / "cells" / cell_id / "compare_diff.json"
            _atomic_write_json(diff_path, compare_reports(before_report, after_report))
            row["artifacts"] = artifacts
            row["diff_file"] = str(diff_path)
        cell_rows.append(row)

    summary = {
        "schema_version": MATRIX_COMPARE_SCHEMA,
        "status": "completed",
        "generated_at": _now(),
        "before_manifest": str(before_path),
        "after_manifest": str(after_path),
        "before_matrix_id": before_manifest["matrix_id"],
        "after_matrix_id": after_manifest["matrix_id"],
        "config_version": before_manifest["config_version"],
        "config_hash": before_manifest["config_hash"],
        "before_code_fingerprint": before_manifest["code_fingerprint"],
        "after_code_fingerprint": after_manifest["code_fingerprint"],
        "include": list(includes),
        "total_cells": len(cell_rows),
        "comparable_cells": comparable_cells,
        "paired_seeds": sorted({int(row["seed"]) for row in cell_rows}),
        "changed_artifacts": changed_artifacts,
        "unchanged_artifacts": unchanged_artifacts,
        "cells": cell_rows,
    }
    summary_path = out_dir / MATRIX_COMPARE_SUMMARY_FILE
    _atomic_write_json(summary_path, summary)
    return MatrixCompareResult(summary_path=summary_path, summary=summary)


def _load_matrix_manifest(value: str | Path, *, label: str) -> tuple[Path, dict[str, Any]]:
    path = Path(value).resolve()
    if path.is_dir():
        path = path / MATRIX_MANIFEST_FILE
    if not path.is_file():
        raise MatrixCompareError(f"{label} matrix manifest does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MatrixCompareError(f"cannot read {label} matrix manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MatrixCompareError(f"{label} matrix manifest must be a JSON object: {path}")
    required = {
        "schema_version",
        "matrix_id",
        "config_version",
        "config_hash",
        "code_fingerprint",
        "status",
        "dry_run",
        "cells",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise MatrixCompareError(f"{label} matrix manifest missing keys: {', '.join(missing)}")
    if payload["schema_version"] != MATRIX_SCHEMA:
        raise MatrixCompareError(
            f"{label} matrix schema must be {MATRIX_SCHEMA!r}, got {payload['schema_version']!r}"
        )
    if payload["status"] != "completed" or payload["dry_run"] is not False:
        raise MatrixCompareError(f"{label} matrix must be a completed non-dry-run execution")
    if not isinstance(payload["matrix_id"], str) or not payload["matrix_id"]:
        raise MatrixCompareError(f"{label} matrix_id must be a non-empty string")
    if not isinstance(payload["config_version"], str) or not payload["config_version"]:
        raise MatrixCompareError(f"{label} config_version must be a non-empty string")
    if not isinstance(payload["config_hash"], str) or not _SHA256_RE.fullmatch(
        payload["config_hash"]
    ):
        raise MatrixCompareError(f"{label} config_hash must be a lowercase SHA-256")
    if not isinstance(payload["code_fingerprint"], str) or not _SHA256_RE.fullmatch(
        payload["code_fingerprint"]
    ):
        raise MatrixCompareError(f"{label} code_fingerprint must be a lowercase SHA-256")
    if not isinstance(payload["cells"], list) or not payload["cells"]:
        raise MatrixCompareError(f"{label} matrix cells must be a non-empty list")
    return path, payload


def _validate_matrix_pair(before: dict[str, Any], after: dict[str, Any]) -> None:
    for key in ("matrix_id", "config_version", "config_hash"):
        if before[key] != after[key]:
            raise MatrixCompareError(
                f"matrix {key} differs: before={before[key]!r}, after={after[key]!r}"
            )


def _comparison_includes(
    manifest: dict[str, Any], manifest_path: Path, *, label: str
) -> tuple[str, ...]:
    raw = manifest.get("compare")
    if raw is None:
        config_path = manifest.get("config_path")
        if not isinstance(config_path, str) or not config_path:
            raise MatrixCompareError(
                f"{label} matrix has neither embedded compare config nor config_path"
            )
        try:
            from game_analysis_agent.test_matrix import load_matrix_config

            config = load_matrix_config(config_path)
        except (OSError, ValueError) as exc:
            raise MatrixCompareError(
                f"cannot recover compare config for {label} matrix {manifest_path}: {exc}"
            ) from exc
        if config.config_hash != manifest["config_hash"]:
            raise MatrixCompareError(f"{label} config_path hash does not match matrix manifest")
        return _validate_include_values(config.compare.include, label=label)
    if not isinstance(raw, dict) or set(raw) != {"output_dir", "include"}:
        raise MatrixCompareError(
            f"{label} matrix compare config must contain exactly output_dir and include"
        )
    if not isinstance(raw["output_dir"], str) or not raw["output_dir"].strip():
        raise MatrixCompareError(f"{label} matrix compare.output_dir must be a string")
    return _validate_include_values(raw["include"], label=label)


def _validate_include_values(value: Any, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise MatrixCompareError(f"{label} matrix compare.include must be non-empty")
    includes: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise MatrixCompareError(
                f"{label} matrix compare.include entries must be non-empty strings"
            )
        candidate = Path(item)
        if candidate.is_absolute() or ".." in candidate.parts or len(candidate.parts) != 1:
            raise MatrixCompareError(
                f"{label} matrix compare.include contains unsafe path: {item!r}"
            )
        includes.append(item)
    if len(includes) != len(set(includes)):
        raise MatrixCompareError(f"{label} matrix compare.include contains duplicates")
    return tuple(includes)


def _index_cells(
    manifest: dict[str, Any], *, manifest_path: Path, label: str
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(manifest["cells"]):
        path = f"{label}.cells[{index}]"
        if not isinstance(raw, dict):
            raise MatrixCompareError(f"{path} must be an object")
        required = {
            "cell_id",
            "run_id",
            "kind",
            "parameters",
            "report_dir",
            "cell_manifest",
            "command",
            "cwd",
            "status",
            "exit_code",
        }
        missing = sorted(required - set(raw))
        if missing:
            raise MatrixCompareError(f"{path} missing keys: {', '.join(missing)}")
        for key in ("cell_id", "run_id", "report_dir", "cell_manifest", "cwd"):
            if not isinstance(raw[key], str) or not raw[key]:
                raise MatrixCompareError(f"{path}.{key} must be a non-empty string")
        if (
            not isinstance(raw["command"], list)
            or not raw["command"]
            or not all(isinstance(item, str) and item for item in raw["command"])
        ):
            raise MatrixCompareError(f"{path}.command must be a non-empty string list")
        for key in ("cell_id", "run_id"):
            if not _SAFE_ID_RE.fullmatch(raw[key]):
                raise MatrixCompareError(f"{path}.{key} contains unsafe characters: {raw[key]!r}")
        if raw["kind"] not in CELL_KINDS:
            raise MatrixCompareError(f"{path}.kind is invalid: {raw['kind']!r}")
        if raw["status"] not in COMPLETED_CELL_STATUSES or raw["exit_code"] != 0:
            raise MatrixCompareError(f"{path} is not successfully completed")
        parameters = raw["parameters"]
        if not isinstance(parameters, dict):
            raise MatrixCompareError(f"{path}.parameters must be an object")
        seed = parameters.get("seed")
        if type(seed) is not int or seed <= 0:
            raise MatrixCompareError(f"{path}.parameters.seed must be a positive integer")
        cell_id = raw["cell_id"]
        if cell_id in indexed:
            raise MatrixCompareError(f"{label} matrix has duplicate cell_id {cell_id!r}")
        _validate_cell_manifest(raw, manifest, manifest_path=manifest_path, label=path)
        indexed[cell_id] = raw
    return indexed


def _validate_cell_manifest(
    cell: dict[str, Any],
    matrix: dict[str, Any],
    *,
    manifest_path: Path,
    label: str,
) -> None:
    path = Path(cell["cell_manifest"])
    if not path.is_absolute():
        path = manifest_path.parent / path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MatrixCompareError(f"cannot read {label}.cell_manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MatrixCompareError(f"{label}.cell_manifest must be a JSON object")
    expected = {
        "schema_version": MATRIX_SCHEMA,
        "matrix_id": matrix["matrix_id"],
        "config_hash": matrix["config_hash"],
        "code_fingerprint": matrix["code_fingerprint"],
        "cell_id": cell["cell_id"],
        "run_id": cell["run_id"],
        "kind": cell["kind"],
        "parameters": cell["parameters"],
        "command": cell["command"],
        "cwd": cell["cwd"],
        "report_dir": cell["report_dir"],
        "status": "completed",
        "exit_code": 0,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise MatrixCompareError(
                f"{label}.cell_manifest {key} mismatch: "
                f"expected {expected_value!r}, got {payload.get(key)!r}"
            )


def _validate_cell_pair(before: dict[str, Any], after: dict[str, Any]) -> None:
    cell_id = before["cell_id"]
    for key in ("cell_id", "run_id", "kind", "parameters"):
        if before[key] != after[key]:
            raise MatrixCompareError(
                f"cell {cell_id} {key} differs: before={before[key]!r}, after={after[key]!r}"
            )


def _require_report_dir(path: Path, *, cell_id: str, label: str) -> None:
    if not path.is_dir():
        raise MatrixCompareError(f"cell {cell_id} {label} report_dir does not exist: {path}")


def _validate_report_evidence(
    cell: dict[str, Any],
    report_dir: Path,
    matrix: dict[str, Any],
    *,
    cell_id: str,
    label: str,
) -> None:
    required = {
        "simulation": (
            "report_manifest.json",
            "raw_runs.jsonl",
            "summary.json",
            "ending_distribution.csv",
            "action_pick_rates.csv",
            "weekly_stats.csv",
            "coverage_report.json",
            "anomalies.jsonl",
            "value_report.json",
            "route_report.json",
            "event_graph.json",
            "action_catalog.json",
        ),
        "boundary": (
            "report_manifest.json",
            "boundary_runs.jsonl",
            "anomalies.jsonl",
            "value_report.json",
            "route_report.json",
        ),
        "persona": (
            "report_manifest.json",
            "playthrough.jsonl",
            "playthrough_agent_report.json",
            "playthrough_summary.md",
            "agent_eval.json",
        ),
    }[cell["kind"]]
    for name in required:
        _validate_artifact(report_dir / name, cell_id=cell_id, label=label)

    manifest = _read_object(report_dir / "report_manifest.json")
    if manifest.get("schema_version") != "trace-manifest-v2":
        raise MatrixCompareError(
            f"cell {cell_id} {label} report manifest has the wrong schema_version"
        )
    if manifest.get("run_id") != cell["run_id"] or manifest.get("status") != "completed":
        raise MatrixCompareError(f"cell {cell_id} {label} report manifest identity/status mismatch")
    fingerprint = ((manifest.get("provenance") or {}).get("fingerprints") or {}).get(
        "execution_source_sha256"
    )
    if fingerprint != matrix["code_fingerprint"]:
        raise MatrixCompareError(
            f"cell {cell_id} {label} report source fingerprint does not match its matrix"
        )

    try:
        if cell["kind"] == "simulation":
            validate_contract_file(report_dir / "raw_runs.jsonl", kind=ContractKind.TRACE)
            validate_contract_file(report_dir / "event_graph.json", kind=ContractKind.EVENT_GRAPH)
            validate_contract_file(
                report_dir / "action_catalog.json", kind=ContractKind.ACTION_CATALOG
            )
            validate_trace_catalog_consistency(
                report_dir / "raw_runs.jsonl",
                report_dir / "event_graph.json",
                report_dir / "action_catalog.json",
            )
            _require_keys(report_dir / "summary.json", {"total_runs", "policies", "top_events"})
            _require_keys(
                report_dir / "value_report.json",
                {"finding_count", "by_kind", "findings"},
            )
            _require_keys(
                report_dir / "route_report.json",
                {"finding_count", "by_kind", "axes", "groups", "route_separation"},
            )
            coverage = _require_keys(
                report_dir / "coverage_report.json",
                {
                    "schema_version",
                    "total_runs",
                    "event_coverage",
                    "action_coverage",
                    "data_quality",
                },
            )
            if coverage.get("schema_version") != "coverage-v2":
                raise ValueError("coverage_report.json schema_version must be coverage-v2")
            if not (coverage.get("event_coverage") or {}).get("catalog_available"):
                raise ValueError("coverage_report.json has no event catalog denominator")
            if not (coverage.get("action_coverage") or {}).get("catalog_available"):
                raise ValueError("coverage_report.json has no action catalog denominator")
            catalog_errors = (coverage.get("data_quality") or {}).get("catalog_errors")
            if catalog_errors != []:
                raise ValueError("coverage_report.json has catalog errors or missing error list")
        elif cell["kind"] == "boundary":
            validate_contract_file(
                report_dir / "boundary_runs.jsonl", kind=ContractKind.BOUNDARY_TRACE
            )
            _require_keys(
                report_dir / "value_report.json",
                {"finding_count", "by_kind", "findings"},
            )
            _require_keys(
                report_dir / "route_report.json",
                {"finding_count", "by_kind", "axes", "groups"},
            )
        else:
            recorded = _require_keys(
                report_dir / "agent_eval.json",
                {"schema_version", "valid", "errors", "final_ending", "metrics"},
            )
            recomputed = evaluate_playthrough(report_dir)
            if recorded.get("schema_version") != "agent-eval-v1":
                raise ValueError("agent_eval.json has the wrong schema_version")
            if recorded.get("valid") is not True or recorded.get("errors") != []:
                raise ValueError("agent_eval.json is not valid and clean")
            if recomputed.get("valid") is not True:
                raise ValueError(f"playthrough evidence is invalid: {recomputed.get('errors')}")
            if recorded.get("metrics") != recomputed.get("metrics"):
                raise ValueError("agent_eval.json metrics do not match the playthrough")
            if not recorded.get("final_ending") or (
                recorded.get("final_ending") != recomputed.get("final_ending")
            ):
                raise ValueError("agent_eval.json final ending does not match the playthrough")
    except (OSError, ValueError, ContractValidationError) as exc:
        raise MatrixCompareError(f"cell {cell_id} invalid {label} report evidence: {exc}") from exc


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} root must be an object")
    return value


def _require_keys(path: Path, keys: set[str]) -> dict[str, Any]:
    value = _read_object(path)
    missing = sorted(keys - set(value))
    if missing:
        raise ValueError(f"{path.name} is missing required keys: {missing}")
    return value


def _validate_artifact(path: Path, *, cell_id: str, label: str) -> None:
    if not path.is_file():
        raise MatrixCompareError(f"cell {cell_id} missing {label} artifact: {path}")
    try:
        if path.suffix == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("JSON artifact is not an object")
        elif path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError(f"line {line_number} is not a JSON object")
        elif path.suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or any(not column.strip() for column in reader.fieldnames):
                    raise ValueError("CSV header is missing or contains blank columns")
                required = _CSV_COLUMNS.get(path.name, set())
                missing = sorted(required - set(reader.fieldnames))
                if missing:
                    raise ValueError(f"CSV is missing required columns: {missing}")
                for row in reader:
                    if None in row:
                        raise ValueError("CSV row has more columns than the header")
        else:
            path.read_bytes()
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error, ValueError) as exc:
        raise MatrixCompareError(f"cell {cell_id} invalid {label} artifact {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


__all__ = [
    "MATRIX_COMPARE_SCHEMA",
    "MATRIX_COMPARE_SUMMARY_FILE",
    "MatrixCompareError",
    "MatrixCompareResult",
    "compare_matrix_runs",
]
