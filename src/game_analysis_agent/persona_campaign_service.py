"""End-to-end persona campaign service for local and live providers."""

from __future__ import annotations

import json
import os
import shutil
import threading
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from .build_week_campaign import (
    PersonaCampaignExecutor,
    TargetSelectionError,
    build_provider_source_identity,
    select_repair_target,
    write_target,
)
from .campaign_aggregation import aggregate_campaign, load_failure_rules
from .campaign_bundle import (
    PublicFailureClusters,
    build_public_campaign_bundle,
    verify_public_campaign_bundle,
)
from .campaign_contract import (
    CampaignCellRequest,
    CampaignCellResult,
    CampaignManifest,
    CampaignRequest,
    CampaignSourceIdentity,
    build_campaign_cells,
    resume_compatible,
)
from .campaign_runner import CampaignRunner, CampaignRunSummary
from .llm_client import LocalLLMClient
from .persona_gateway import PersonaProvider
from .persona_gateway_factory import build_persona_gateway
from .persona_runtime import (
    PersonaCancellationToken,
    PersonaRuntimeSettings,
    redact_sensitive_text,
)
from .playthrough_view import (
    build_playthrough_views,
    truth_label_for,
    verify_playthrough_evidence,
)
from .settings import Settings


class PersonaCampaignServiceError(RuntimeError):
    """Raised before unsafe execution or when campaign evidence is incomplete."""


_SESSION_STATE_KEYS = (
    "week",
    "money",
    "energy",
    "stress",
    "hunger",
    "arrears_amount",
    "cash_shortfall_count",
    "academic_progress",
    "visa_progress",
)


class _CampaignSessionPublisher:
    """Publish sanitized weekly progress without claiming completed evidence."""

    def __init__(
        self,
        *,
        view: Path,
        request: CampaignRequest,
        truth_label: str,
        model: str,
    ) -> None:
        self.path = view / "session.json"
        self._lock = threading.Lock()
        cells = [
            {
                "cell_id": cell.cell_id,
                "persona": cell.persona.value,
                "seed": cell.seed,
                "status": "pending",
                "phase": "pending",
                "current_week": 0,
                "completed_weeks": 0,
                "max_weeks": cell.max_weeks,
                "diagnostics": _empty_session_diagnostics(),
            }
            for cell in build_campaign_cells(request)
        ]
        self._payload: dict[str, Any] = {
            "schema_version": "persona-campaign-session-v1",
            "campaign_id": request.campaign_id,
            "status": "running",
            "truth_label": truth_label,
            "provider": request.provider.value,
            "model": model,
            "request": request.model_dump(mode="json"),
            "progress": {
                "completed_cells": 0,
                "running_cells": 0,
                "failed_cells": 0,
                "completed_weeks": 0,
                "total_cells": len(cells),
                "total_requested_weeks": len(cells) * request.max_weeks,
            },
            "cells": cells,
            "diagnostics": _aggregate_session_diagnostics(cells),
            "latest": None,
            "message": "Campaign started; completed weekly decisions will appear here.",
        }
        self._write_locked()

    def progress(
        self,
        cell: CampaignCellRequest,
        output_dir: Path,
        event: dict[str, Any],
    ) -> None:
        with self._lock:
            record = self._cell(cell.cell_id)
            record.update(
                {
                    "status": "running",
                    "phase": (
                        "game_finished_pending_validation"
                        if bool(event.get("finished"))
                        else str(event.get("phase") or "running")
                    ),
                    "current_week": int(event.get("week") or 0),
                    "completed_weeks": int(event.get("completed_weeks") or 0),
                }
            )
            playthrough_path = output_dir / "playthrough.jsonl"
            latest_row = _latest_jsonl_row(playthrough_path)
            record["diagnostics"] = _session_diagnostics(playthrough_path)
            self._payload["latest"] = _session_latest(cell, event, latest_row)
            self._payload["message"] = (
                f"{cell.persona.value} seed {cell.seed}: "
                f"week {record['current_week']}/{cell.max_weeks} {record['phase']}"
            )
            self._refresh_counts()
            self._write_locked()

    def hydrate(self, retained: tuple[CampaignCellResult, ...]) -> None:
        """Expose resume candidates without claiming final validation."""

        if not retained:
            return
        with self._lock:
            for result in retained:
                record = self._cell(result.request.cell_id)
                record.update(
                    {
                        "status": "retained",
                        "phase": "resume_candidate_pending_validation",
                        "current_week": result.completed_weeks,
                        "completed_weeks": result.completed_weeks,
                    }
                )
            self._payload["message"] = (
                f"{len(retained)} compatible completed cells retained; "
                "they will be revalidated before publication."
            )
            self._refresh_counts()
            self._write_locked()

    def finalizing(self, summary: CampaignRunSummary) -> None:
        with self._lock:
            self._payload["status"] = "finalizing"
            for result in summary.results:
                record = self._cell(result.request.cell_id)
                record.update(
                    {
                        "status": result.state.value,
                        "phase": "complete" if result.state.value == "completed" else "stopped",
                        "completed_weeks": result.completed_weeks,
                        "current_week": result.completed_weeks,
                    }
                )
            self._payload["message"] = "Every cell stopped; validating and publishing evidence."
            self._refresh_counts()
            self._write_locked()

    def completed(self, *, calls_used: int, repair_target_eligible: bool) -> None:
        with self._lock:
            self._payload["status"] = "completed"
            self._payload["calls_used"] = calls_used
            self._payload["repair_target_eligible"] = repair_target_eligible
            self._payload["message"] = "Campaign evidence passed and the complete paths are ready."
            self._refresh_counts()
            self._write_locked()

    def failed(self, message: str) -> None:
        with self._lock:
            self._payload["status"] = "failed"
            self._payload["message"] = redact_sensitive_text(message)[:500]
            self._refresh_counts()
            self._write_locked()

    def _cell(self, cell_id: str) -> dict[str, Any]:
        return next(cell for cell in self._payload["cells"] if cell["cell_id"] == cell_id)

    def _refresh_counts(self) -> None:
        cells = self._payload["cells"]
        self._payload["progress"] = {
            **self._payload["progress"],
            "completed_cells": sum(cell["status"] == "completed" for cell in cells),
            "running_cells": sum(cell["status"] == "running" for cell in cells),
            "failed_cells": sum(cell["status"] in {"failed", "partial"} for cell in cells),
            "completed_weeks": sum(int(cell["completed_weeks"]) for cell in cells),
            "retained_cells": sum(cell["status"] == "retained" for cell in cells),
        }
        self._payload["diagnostics"] = _aggregate_session_diagnostics(cells)

    def _write_locked(self) -> None:
        _write_json(self.path, self._payload)


def _session_latest(
    cell: CampaignCellRequest,
    event: Mapping[str, Any],
    row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = row.get("state_after") if row else {}
    if not isinstance(state, Mapping):
        state = {}
    return {
        "cell_id": cell.cell_id,
        "persona": cell.persona.value,
        "seed": cell.seed,
        "phase": (
            "game_finished_pending_validation"
            if bool(event.get("finished"))
            else str(event.get("phase") or "running")
        ),
        "week": int(event.get("week") or 0),
        "completed_weeks": int(event.get("completed_weeks") or 0),
        "max_weeks": cell.max_weeks,
        "selected_action_ids": list(row.get("chosen_actions") or []) if row else [],
        "triggered_event_id": str(row.get("triggered_event_id") or "") if row else "",
        "selected_choice_id": str(row.get("event_choice_id") or "") if row else "",
        "state_after": {key: state[key] for key in _SESSION_STATE_KEYS if key in state},
    }


def _latest_jsonl_row(path: Path) -> dict[str, Any] | None:
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        value = json.loads(lines[-1])
    except (FileNotFoundError, IndexError, json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _empty_session_diagnostics() -> dict[str, Any]:
    return {
        "logical_calls": 0,
        "http_attempts": 0,
        "fallback_weeks": [],
        "failure_count": 0,
        "response_metadata_missing_attempts": 0,
        "known_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "failures": [],
    }


def _session_diagnostics(path: Path) -> dict[str, Any]:
    diagnostics = _empty_session_diagnostics()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return diagnostics
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, Mapping):
            continue
        week = _session_nonnegative_int(row.get("week"))
        validation = row.get("validation")
        if (
            isinstance(validation, Mapping)
            and validation.get("fallback_used") is True
            and week not in diagnostics["fallback_weeks"]
        ):
            diagnostics["fallback_weeks"].append(week)
        calls = row.get("persona_calls")
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, Mapping):
                continue
            metadata = call.get("metadata")
            if call.get("status") not in {"completed", "failed"} or not isinstance(
                metadata, Mapping
            ):
                continue
            diagnostics["logical_calls"] += 1
            attempts = max(1, _session_nonnegative_int(metadata.get("attempt_count")))
            diagnostics["http_attempts"] += attempts
            usage = metadata.get("usage")
            usage = usage if isinstance(usage, Mapping) else {}
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                diagnostics["known_usage"][key] += _session_nonnegative_int(usage.get(key))
            if call.get("status") != "failed":
                continue
            diagnostics["failure_count"] += 1
            if not str(metadata.get("response_id") or ""):
                diagnostics["response_metadata_missing_attempts"] += 1
            error = call.get("error")
            error = error if isinstance(error, Mapping) else {}
            if len(diagnostics["failures"]) < 12:
                diagnostics["failures"].append(
                    {
                        "week": week,
                        "phase": str(call.get("phase") or "unknown")[:40],
                        "category": str(error.get("category") or "unknown")[:40],
                        "message": redact_sensitive_text(
                            str(error.get("message") or "provider call failed")
                        )[:180],
                        "attempts": attempts,
                    }
                )
    return diagnostics


def _aggregate_session_diagnostics(cells: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate = _empty_session_diagnostics()
    aggregate.pop("fallback_weeks")
    aggregate["fallback_count"] = 0
    for cell in cells:
        diagnostics = cell.get("diagnostics")
        if not isinstance(diagnostics, Mapping):
            continue
        for key in (
            "logical_calls",
            "http_attempts",
            "failure_count",
            "response_metadata_missing_attempts",
        ):
            aggregate[key] += _session_nonnegative_int(diagnostics.get(key))
        fallback_weeks = diagnostics.get("fallback_weeks")
        if isinstance(fallback_weeks, list):
            aggregate["fallback_count"] += len(fallback_weeks)
        usage = diagnostics.get("known_usage")
        usage = usage if isinstance(usage, Mapping) else {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            aggregate["known_usage"][key] += _session_nonnegative_int(usage.get(key))
        failures = diagnostics.get("failures")
        if not isinstance(failures, list):
            continue
        for failure in failures:
            if not isinstance(failure, Mapping) or len(aggregate["failures"]) >= 50:
                continue
            aggregate["failures"].append(
                {
                    "cell_id": cell["cell_id"],
                    "persona": cell["persona"],
                    "seed": cell["seed"],
                    **failure,
                }
            )
    return aggregate


def _session_nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def run_persona_campaign(
    *,
    project_root: str | Path,
    game_root: str | Path,
    request: CampaignRequest,
    bundle_dir: str | Path,
    view_dir: str | Path,
    environment: Mapping[str, str] | None = None,
    failure_rules_path: str | Path | None = None,
    resume: bool = True,
    external_cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Run one bounded campaign and publish sanitized, frontend-ready evidence."""

    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    if not (game / "project.godot").is_file():
        raise PersonaCampaignServiceError("game_root does not contain project.godot")
    if not (game / ".playtest-forge-source.json").is_file():
        raise PersonaCampaignServiceError("game_root is not a hash-pinned embedded runtime")
    bundle = _inside_project(
        project,
        bundle_dir,
        field="bundle_dir",
        allowed_root=project / "reports",
    )
    view = _inside_project(
        project,
        view_dir,
        field="view_dir",
        allowed_root=project / "frontend/public",
    )
    if request.provider == PersonaProvider.REPLAY:
        raise PersonaCampaignServiceError("use the canonical Replay campaign runner for Replay")

    runtime_env = dict(os.environ if environment is None else environment)
    runtime_env["PERSONA_PROVIDER"] = request.provider.value
    persona_settings = PersonaRuntimeSettings.from_env(runtime_env)
    selection = persona_settings.resolve_provider()
    if selection.selected != request.provider:
        raise PersonaCampaignServiceError("requested and selected persona providers differ")

    runs = len(request.personas) * len(request.seeds)
    persona_settings.limits.validate_campaign(
        runs=runs,
        weeks=request.max_weeks,
        concurrency=request.concurrency,
    )
    worst_case_calls = runs * request.max_weeks * 2
    if persona_settings.limits.max_calls < worst_case_calls:
        raise PersonaCampaignServiceError(
            "PERSONA_MAX_CALLS is below the decision+event worst-case budget: "
            f"need at least {worst_case_calls}"
        )

    settings = _build_settings(runtime_env, game, request.provider)
    local_llm = None
    model = persona_settings.openai_model
    if request.provider != PersonaProvider.OPENAI:
        local_llm = LocalLLMClient.from_settings(settings)
        local_llm.validate_model_available()
        model = local_llm.model

    cancellation = PersonaCancellationToken()
    built = build_persona_gateway(
        persona_settings,
        project_root=project,
        local_llm=local_llm,
        cancellation=cancellation,
    )
    built.gateway.validate_campaign(
        runs=runs,
        weeks=request.max_weeks,
        concurrency=request.concurrency,
    )
    source = build_provider_source_identity(
        project_root=project,
        game_root=game,
        request=request,
        provider=request.provider,
        mode=selection.mode,
        model=model,
    )
    publisher = _CampaignSessionPublisher(
        view=view,
        request=request,
        truth_label=truth_label_for(request.provider.value, selection.mode.value),
        model=model,
    )
    retained = _resumable_results(project, request, source) if resume else ()
    publisher.hydrate(retained)
    retained_calls = _provider_call_count(project, retained)
    runner = CampaignRunner(
        project_root=project,
        request=request,
        source=source,
        executor=PersonaCampaignExecutor(
            gateway=built.gateway,
            settings=settings,
            progress_callback=publisher.progress,
            external_cancelled=external_cancelled,
        ),
        cancellation=cancellation,
    )
    try:
        summary = runner.run(resume=resume)
    except Exception as exc:
        publisher.failed(f"Campaign execution failed: {exc}")
        raise
    publisher.finalizing(summary)
    try:
        if not summary.submittable:
            message = f"campaign did not complete every cell: {summary.status_counts}"
            publisher.failed(message)
            raise PersonaCampaignServiceError(message)

        manifest = CampaignManifest.model_validate_json(
            summary.manifest_path.read_text(encoding="utf-8")
        )
        rules_path = Path(
            failure_rules_path or project / "config/build_week_2026_failure_rules.json"
        )
        aggregation = aggregate_campaign(
            project_root=project,
            results=summary.results,
            rules=load_failure_rules(rules_path),
        )
        gate = build_public_campaign_bundle(
            project_root=project,
            bundle_dir=bundle,
            manifest=manifest,
            results=summary.results,
            aggregation=aggregation,
        )
        verify_public_campaign_bundle(bundle)

        public_clusters = PublicFailureClusters.model_validate_json(
            (bundle / "failure_clusters.json").read_text(encoding="utf-8")
        )
        eligibility: dict[str, Any]
        try:
            target = select_repair_target(
                request=request,
                aggregation=aggregation,
                clusters=public_clusters.clusters,
                evidence_bundle=bundle.relative_to(project).as_posix(),
            )
        except TargetSelectionError as exc:
            (bundle / "repair_target.json").unlink(missing_ok=True)
            eligibility = {
                "schema_version": "repair-target-eligibility-v1",
                "eligible": False,
                "reason": str(exc),
                "required": "at least two runs across at least two personas",
            }
        else:
            target_path = write_target(bundle / "repair_target.json", target)
            eligibility = {
                "schema_version": "repair-target-eligibility-v1",
                "eligible": True,
                "target": target.selected_cluster_id,
                "target_path": target_path.relative_to(project).as_posix(),
            }
        _write_json(bundle / "repair_eligibility.json", eligibility)

        _clear_view_evidence(view)
        view_manifest = build_playthrough_views(
            source_root=project,
            campaign_manifest_path=bundle / "campaign_manifest.json",
            failure_clusters_path=bundle / "failure_clusters.json",
            public_gate_path=bundle / "gate_report.json",
            personas_path=project / "config/player_personas.yaml",
            action_catalog_path=project
            / "demo/study-in-germany/data/actions/generated_actions.json",
            output_dir=view,
        )
        _write_json(view / "repair_eligibility.json", eligibility)
        cumulative_calls = retained_calls + built.gateway.calls_used
        verify_playthrough_evidence(view, source_root=project)
        publisher.completed(
            calls_used=cumulative_calls,
            repair_target_eligible=bool(eligibility["eligible"]),
        )
        return {
            "schema_version": "persona-campaign-service-result-v1",
            "status": gate.status,
            "campaign_id": request.campaign_id,
            "provider": request.provider.value,
            "mode": selection.mode.value,
            "model": model,
            "cells": summary.status_counts,
            "weeks": aggregation.metrics.total_weeks,
            "calls_used": cumulative_calls,
            "resumed_cells": len(summary.resumed_cell_ids),
            "bundle": bundle.relative_to(project).as_posix(),
            "view": view.relative_to(project).as_posix(),
            "truth_label": view_manifest["truth_label"],
            "repair_target_eligible": eligibility["eligible"],
        }
    except Exception as exc:
        publisher.failed(f"Campaign finalization failed: {exc}")
        raise


def _resumable_results(
    project: Path,
    request: CampaignRequest,
    source: CampaignSourceIdentity,
) -> tuple[CampaignCellResult, ...]:
    retained = []
    for cell in build_campaign_cells(request):
        path = project / cell.output_dir / "cell_result.json"
        try:
            result = CampaignCellResult.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if resume_compatible(result, cell, source):
            retained.append(result)
    return tuple(retained)


def _provider_call_count(
    project: Path,
    results: tuple[CampaignCellResult, ...],
) -> int:
    count = 0
    for result in results:
        path = project / result.request.output_dir / "playthrough.jsonl"
        try:
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        except (OSError, json.JSONDecodeError):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            calls = row.get("persona_calls")
            if isinstance(calls, list):
                count += sum(isinstance(call, dict) for call in calls)
    return count


def _clear_view_evidence(view: Path) -> None:
    if not view.exists():
        return
    for child in view.iterdir():
        if child.name == "session.json":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _build_settings(
    environment: Mapping[str, str],
    game_root: Path,
    provider: PersonaProvider,
) -> Settings:
    base = Settings()
    return replace(
        base,
        llm_provider=provider.value,
        vllm_base_url=environment.get("VLLM_BASE_URL", base.vllm_base_url),
        vllm_api_key=environment.get("VLLM_API_KEY", base.vllm_api_key),
        vllm_model=environment.get("LLM_SERVED_MODEL_NAME", base.vllm_model),
        sglang_base_url=environment.get("SGLANG_BASE_URL", base.sglang_base_url),
        sglang_api_key=environment.get("SGLANG_API_KEY", base.sglang_api_key),
        sglang_model=environment.get("SGLANG_MODEL", base.sglang_model),
        deepseek_base_url=environment.get("DEEPSEEK_BASE_URL", base.deepseek_base_url),
        deepseek_api_key=environment.get("DEEPSEEK_API_KEY"),
        deepseek_model=environment.get("DEEPSEEK_MODEL", base.deepseek_model),
        godot_bin=environment.get("GODOT_BIN", base.godot_bin),
        game_project_path=game_root,
    )


def _inside_project(
    project: Path,
    value: str | Path,
    *,
    field: str,
    allowed_root: Path,
) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (project / path).resolve()
    try:
        resolved.relative_to(allowed_root.resolve())
    except ValueError as exc:
        raise PersonaCampaignServiceError(f"{field} must stay inside the project") from exc
    if resolved == allowed_root.resolve():
        raise PersonaCampaignServiceError(f"{field} cannot be the allowed root")
    return resolved


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


__all__ = [
    "PersonaCampaignServiceError",
    "run_persona_campaign",
]
