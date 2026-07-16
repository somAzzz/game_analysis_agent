"""Isolated, resumable, bounded-concurrency persona campaign scheduler."""

from __future__ import annotations

import hashlib
import json
import shutil
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from .campaign_contract import (
    CampaignArtifact,
    CampaignCellRequest,
    CampaignCellResult,
    CampaignCellState,
    CampaignManifest,
    CampaignRequest,
    CampaignSourceIdentity,
    CampaignStopReason,
    build_campaign_cells,
    citation_for_row,
    resume_compatible,
)
from .persona_runtime import PersonaCancellationToken, redact_sensitive_text


class CampaignRunnerError(RuntimeError):
    """Raised when campaign scheduling cannot safely start."""


@dataclass(frozen=True)
class CellExecutionOutcome:
    state: CampaignCellState
    stop_reason: CampaignStopReason
    completed_weeks: int
    error: str = ""
    artifact_names: tuple[str, ...] = ("playthrough.jsonl",)


class CampaignCellExecutor(Protocol):
    def __call__(
        self, request: CampaignCellRequest, output_dir: Path, context: CampaignExecutionContext
    ) -> CellExecutionOutcome: ...


class ChildProcess(Protocol):
    def poll(self) -> int | None: ...
    def terminate(self) -> Any: ...
    def wait(self, timeout: float | None = None) -> Any: ...
    def kill(self) -> Any: ...


class ChildProcessRegistry:
    """Own child processes so campaign cancellation cannot orphan Godot jobs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._children: set[ChildProcess] = set()

    def register(self, child: ChildProcess) -> None:
        with self._lock:
            self._children.add(child)

    def unregister(self, child: ChildProcess) -> None:
        with self._lock:
            self._children.discard(child)

    def terminate_all(self, *, grace_s: float = 2.0) -> int:
        with self._lock:
            children = list(self._children)
        terminated = 0
        for child in children:
            if child.poll() is not None:
                self.unregister(child)
                continue
            terminated += 1
            child.terminate()
            try:
                child.wait(timeout=grace_s)
            except Exception:
                child.kill()
                child.wait(timeout=grace_s)
            self.unregister(child)
        return terminated


@dataclass(frozen=True)
class CampaignExecutionContext:
    cancellation: PersonaCancellationToken
    children: ChildProcessRegistry

    @property
    def cancelled(self) -> bool:
        return self.cancellation.cancelled

    def register_child(self, child: ChildProcess) -> None:
        self.children.register(child)

    def unregister_child(self, child: ChildProcess) -> None:
        self.children.unregister(child)


@dataclass(frozen=True)
class CampaignRunSummary:
    campaign_id: str
    manifest_path: Path
    results: tuple[CampaignCellResult, ...]
    resumed_cell_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def status_counts(self) -> dict[str, int]:
        counts = {state.value: 0 for state in CampaignCellState}
        for result in self.results:
            counts[result.state.value] += 1
        return counts

    @property
    def submittable(self) -> bool:
        return bool(self.results) and all(
            result.state == CampaignCellState.COMPLETED for result in self.results
        )


class CampaignRunner:
    def __init__(
        self,
        *,
        project_root: str | Path,
        request: CampaignRequest,
        source: CampaignSourceIdentity,
        executor: CampaignCellExecutor,
        cancellation: PersonaCancellationToken | None = None,
        children: ChildProcessRegistry | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if request.provider != source.provider:
            raise CampaignRunnerError("campaign request/source provider mismatch")
        self.project_root = Path(project_root).resolve()
        self.request = request
        self.source = source
        self.executor = executor
        self.cancellation = cancellation or PersonaCancellationToken()
        self.children = children or ChildProcessRegistry()
        self.context = CampaignExecutionContext(self.cancellation, self.children)
        self.clock = clock or (lambda: datetime.now(tz=UTC))

    @property
    def campaign_dir(self) -> Path:
        return self.project_root / self.request.report_root / self.request.campaign_id

    def cancel(self) -> int:
        self.cancellation.cancel()
        return self.children.terminate_all()

    def run(self, *, resume: bool = True) -> CampaignRunSummary:
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        manifest = self._manifest()
        manifest_path = self.campaign_dir / "campaign_manifest.json"
        _atomic_write_json(manifest_path, manifest.model_dump(mode="json"))
        results_by_id: dict[str, CampaignCellResult] = {}
        pending = []
        resumed = []
        for cell in manifest.cells:
            existing = self._read_result(cell) if resume else None
            if existing is not None and resume_compatible(existing, cell, self.source):
                results_by_id[cell.cell_id] = existing
                resumed.append(cell.cell_id)
            else:
                pending.append(cell)

        with ThreadPoolExecutor(
            max_workers=self.request.concurrency,
            thread_name_prefix="persona-cell",
        ) as pool:
            futures = {pool.submit(self._run_cell, cell): cell for cell in pending}
            for future in as_completed(futures):
                cell = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # defensive scheduler boundary
                    result = self._terminal_failure(
                        cell,
                        started_at=self.clock(),
                        error=f"scheduler failure: {exc.__class__.__name__}",
                    )
                    self._write_result(result)
                results_by_id[cell.cell_id] = result

        ordered = tuple(results_by_id[cell.cell_id] for cell in manifest.cells)
        summary = CampaignRunSummary(
            campaign_id=self.request.campaign_id,
            manifest_path=manifest_path,
            results=ordered,
            resumed_cell_ids=tuple(resumed),
        )
        _atomic_write_json(
            self.campaign_dir / "campaign_run_summary.json",
            {
                "campaign_id": summary.campaign_id,
                "submittable": summary.submittable,
                "status_counts": summary.status_counts,
                "resumed_cell_ids": list(summary.resumed_cell_ids),
            },
        )
        return summary

    def _manifest(self) -> CampaignManifest:
        path = self.campaign_dir / "campaign_manifest.json"
        if path.is_file():
            try:
                existing = CampaignManifest.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValidationError):
                existing = None
            if (
                existing is not None
                and existing.request == self.request
                and existing.source == self.source
            ):
                return existing
        return CampaignManifest(
            request=self.request,
            request_fingerprint=self.request.fingerprint(),
            source=self.source,
            source_fingerprint=self.source.fingerprint(),
            cells=build_campaign_cells(self.request),
            created_at=self.clock(),
        )

    def _run_cell(self, cell: CampaignCellRequest) -> CampaignCellResult:
        output_dir = self.project_root / cell.output_dir
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)
        started = self.clock()
        self._write_result(
            self._state_result(
                cell,
                state=CampaignCellState.RUNNING,
                stop_reason=CampaignStopReason.IN_PROGRESS,
                started_at=started,
            )
        )
        if self.cancellation.cancelled:
            result = self._cancelled(cell, started_at=started)
            self._write_result(result)
            return result
        try:
            outcome = self.executor(cell, output_dir, self.context)
        except Exception as exc:
            result = (
                self._cancelled(cell, started_at=started, output_dir=output_dir)
                if self.cancellation.cancelled
                else self._result_after_exception(cell, output_dir, started, exc)
            )
            self._write_result(result)
            return result
        try:
            result = self._result_from_outcome(cell, output_dir, started, outcome)
        except (CampaignRunnerError, ValidationError, OSError, ValueError) as exc:
            result = self._result_after_exception(cell, output_dir, started, exc)
        self._write_result(result)
        return result

    def _result_from_outcome(
        self,
        cell: CampaignCellRequest,
        output_dir: Path,
        started: datetime,
        outcome: CellExecutionOutcome,
    ) -> CampaignCellResult:
        rows = _read_playthrough(output_dir / "playthrough.jsonl")
        if len(rows) != outcome.completed_weeks:
            raise CampaignRunnerError(
                f"executor claimed {outcome.completed_weeks} weeks but wrote {len(rows)}"
            )
        artifacts, citations = self._evidence(cell, output_dir, outcome, rows)
        return CampaignCellResult(
            request=cell,
            request_fingerprint=cell.fingerprint(),
            source=self.source,
            source_fingerprint=self.source.fingerprint(),
            state=outcome.state,
            stop_reason=outcome.stop_reason,
            completed_weeks=outcome.completed_weeks,
            started_at=started,
            completed_at=self.clock(),
            error=redact_sensitive_text(outcome.error),
            artifacts=artifacts,
            citations=citations,
        )

    def _result_after_exception(
        self,
        cell: CampaignCellRequest,
        output_dir: Path,
        started: datetime,
        exc: Exception,
    ) -> CampaignCellResult:
        error = redact_sensitive_text(f"{exc.__class__.__name__}: {exc}")
        try:
            rows = _read_playthrough(output_dir / "playthrough.jsonl")
        except Exception:
            rows = []
        if not rows:
            return self._terminal_failure(cell, started_at=started, error=error)
        outcome = CellExecutionOutcome(
            state=CampaignCellState.PARTIAL,
            stop_reason=CampaignStopReason.PROBE_FAILED,
            completed_weeks=len(rows),
            error=error,
        )
        artifacts, citations = self._evidence(cell, output_dir, outcome, rows)
        return CampaignCellResult(
            request=cell,
            request_fingerprint=cell.fingerprint(),
            source=self.source,
            source_fingerprint=self.source.fingerprint(),
            state=outcome.state,
            stop_reason=outcome.stop_reason,
            completed_weeks=len(rows),
            started_at=started,
            completed_at=self.clock(),
            error=error,
            artifacts=artifacts,
            citations=citations,
        )

    def _evidence(
        self,
        cell: CampaignCellRequest,
        output_dir: Path,
        outcome: CellExecutionOutcome,
        rows: list[dict[str, Any]],
    ) -> tuple[list[CampaignArtifact], list[Any]]:
        artifacts = []
        for name in outcome.artifact_names:
            path = output_dir / name
            if not path.is_file():
                raise CampaignRunnerError(f"executor artifact missing: {name}")
            artifacts.append(
                CampaignArtifact(
                    path=f"{cell.output_dir}/{name}",
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    media_type=(
                        "application/x-ndjson" if path.suffix == ".jsonl" else "application/json"
                    ),
                    record_count=len(rows) if name == "playthrough.jsonl" else None,
                )
            )
        citations = [
            citation_for_row(
                cell,
                week=index,
                artifact_path=f"{cell.output_dir}/playthrough.jsonl",
                line_number=index,
                row=row,
            )
            for index, row in enumerate(rows, start=1)
        ]
        return artifacts, citations

    def _read_result(self, cell: CampaignCellRequest) -> CampaignCellResult | None:
        path = self.project_root / cell.output_dir / "cell_result.json"
        try:
            return CampaignCellResult.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError):
            return None

    def _write_result(self, result: CampaignCellResult) -> None:
        path = self.project_root / result.request.output_dir / "cell_result.json"
        _atomic_write_json(path, result.model_dump(mode="json"))

    def _state_result(
        self,
        cell: CampaignCellRequest,
        *,
        state: CampaignCellState,
        stop_reason: CampaignStopReason,
        started_at: datetime | None = None,
    ) -> CampaignCellResult:
        return CampaignCellResult(
            request=cell,
            request_fingerprint=cell.fingerprint(),
            source=self.source,
            source_fingerprint=self.source.fingerprint(),
            state=state,
            stop_reason=stop_reason,
            started_at=started_at,
        )

    def _terminal_failure(
        self, cell: CampaignCellRequest, *, started_at: datetime, error: str
    ) -> CampaignCellResult:
        return CampaignCellResult(
            request=cell,
            request_fingerprint=cell.fingerprint(),
            source=self.source,
            source_fingerprint=self.source.fingerprint(),
            state=CampaignCellState.FAILED,
            stop_reason=CampaignStopReason.PROBE_FAILED,
            started_at=started_at,
            completed_at=self.clock(),
            error=redact_sensitive_text(error),
        )

    def _cancelled(
        self,
        cell: CampaignCellRequest,
        *,
        started_at: datetime,
        output_dir: Path | None = None,
    ) -> CampaignCellResult:
        rows = _read_playthrough(output_dir / "playthrough.jsonl") if output_dir else []
        artifacts: list[CampaignArtifact] = []
        citations: list[Any] = []
        if rows and output_dir is not None:
            artifacts, citations = self._evidence(
                cell,
                output_dir,
                CellExecutionOutcome(
                    state=CampaignCellState.CANCELLED,
                    stop_reason=CampaignStopReason.CANCELLED,
                    completed_weeks=len(rows),
                    error="campaign cancelled",
                ),
                rows,
            )
        return CampaignCellResult(
            request=cell,
            request_fingerprint=cell.fingerprint(),
            source=self.source,
            source_fingerprint=self.source.fingerprint(),
            state=CampaignCellState.CANCELLED,
            stop_reason=CampaignStopReason.CANCELLED,
            started_at=started_at,
            completed_weeks=len(rows),
            completed_at=self.clock(),
            error="campaign cancelled",
            artifacts=artifacts,
            citations=citations,
        )


def _read_playthrough(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CampaignRunnerError(f"invalid playthrough JSON at line {line_number}") from exc
        if not isinstance(row, dict):
            raise CampaignRunnerError(f"playthrough line {line_number} is not an object")
        rows.append(row)
    return rows


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


__all__ = [
    "CampaignCellExecutor",
    "CampaignExecutionContext",
    "CampaignRunSummary",
    "CampaignRunner",
    "CampaignRunnerError",
    "CellExecutionOutcome",
    "ChildProcessRegistry",
]
