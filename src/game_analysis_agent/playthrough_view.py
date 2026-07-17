"""Build truthful frontend views from completed real-game campaign traces."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .campaign_contract import CampaignCellResult, CampaignManifest, canonical_sha256

VIEW_SCHEMA = "playthrough-view-v1"
MANIFEST_SCHEMA = "playthrough-evidence-manifest-v1"
PERSONAS_SCHEMA = "playthrough-personas-v1"
TRUTH_LABEL = "prerecorded-real-godot-replay"
TRUTH_LABELS = {
    ("replay", "replay"): TRUTH_LABEL,
    ("openai", "live"): "live-openai-real-godot",
    ("deepseek", "live"): "live-deepseek-real-godot",
    ("vllm", "local"): "local-vllm-real-godot",
    ("sglang", "local"): "local-sglang-real-godot",
}


class PlaythroughViewError(RuntimeError):
    """Raised when source evidence cannot support a truthful path view."""


def build_playthrough_views(
    *,
    source_root: str | Path,
    campaign_manifest_path: str | Path,
    failure_clusters_path: str | Path,
    public_gate_path: str | Path,
    personas_path: str | Path,
    action_catalog_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Validate a complete campaign and emit one deterministic view per cell."""

    source = Path(source_root).resolve()
    campaign_path = Path(campaign_manifest_path).resolve()
    clusters_path = Path(failure_clusters_path).resolve()
    gate_path = Path(public_gate_path).resolve()
    output = Path(output_dir).resolve()
    manifest = CampaignManifest.model_validate_json(campaign_path.read_text(encoding="utf-8"))
    truth_label = truth_label_for(
        manifest.source.provider.value, manifest.source.provider_mode.value
    )
    clusters = _load_json(clusters_path)
    gate = _load_json(gate_path)
    if gate.get("status") != "passed":
        raise PlaythroughViewError("source public campaign gate is not passed")
    if gate.get("campaign_id") != manifest.request.campaign_id:
        raise PlaythroughViewError("public gate campaign identity mismatch")

    output.mkdir(parents=True, exist_ok=True)
    cells_dir = output / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    attractors = _attractor_index(clusters, manifest.request.campaign_id)
    action_tags = _action_tags(Path(action_catalog_path))
    views: list[dict[str, Any]] = []
    source_artifacts: list[dict[str, Any]] = []
    derived_artifacts: list[dict[str, Any]] = []

    for cell in manifest.cells:
        cell_root = source / cell.output_dir
        result_path = cell_root / "cell_result.json"
        trace_path = cell_root / "playthrough.jsonl"
        summary_path = cell_root / "playthrough_summary.md"
        result = CampaignCellResult.model_validate_json(result_path.read_text(encoding="utf-8"))
        view = build_cell_view(
            manifest=manifest,
            result=result,
            trace_path=trace_path,
            summary_path=summary_path,
            attractors=attractors.get(cell.cell_id, {}),
        )
        destination = cells_dir / f"{cell.persona.value}-seed-{cell.seed}.json"
        _write_json(destination, view)
        views.append(view)
        source_artifacts.extend(
            [
                _artifact(source, result_path, role="cell-result"),
                _artifact(source, trace_path, role="raw-playthrough"),
                _artifact(source, summary_path, role="playthrough-summary"),
            ]
        )
        derived_artifacts.append(_artifact(output, destination, role="playthrough-view"))

    persona_view = _build_persona_view(Path(personas_path), views, action_tags, truth_label)
    personas_destination = output / "personas.json"
    _write_json(personas_destination, persona_view)
    derived_artifacts.append(_artifact(output, personas_destination, role="persona-view"))

    evidence_manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "campaign_id": manifest.request.campaign_id,
        "truth_label": truth_label,
        "playthrough_data_ready": True,
        "frontend_implementation_requires_design_approval": True,
        "request": manifest.request.model_dump(mode="json"),
        "source": manifest.source.model_dump(mode="json"),
        "request_fingerprint": manifest.request_fingerprint,
        "source_fingerprint": manifest.source_fingerprint,
        "cell_count": len(views),
        "node_count": sum(len(view["nodes"]) for view in views),
        "actual_edge_count": sum(len(view["actual_edges"]) for view in views),
        "legal_event_choice_count": sum(
            len(node["event"]["legal_choices"]) for view in views for node in view["nodes"]
        ),
        "source_campaign_manifest": _artifact(source, campaign_path, role="campaign-manifest"),
        "source_public_gate": _artifact(source, gate_path, role="campaign-gate"),
        "source_failure_clusters": _artifact(source, clusters_path, role="failure-clusters"),
        "source_personas": _artifact(source, Path(personas_path), role="persona-contract"),
        "source_action_catalog": _artifact(
            source, Path(action_catalog_path), role="game-action-catalog"
        ),
        "source_artifacts": sorted(source_artifacts, key=lambda item: item["path"]),
        "derived_artifacts": sorted(derived_artifacts, key=lambda item: item["path"]),
        "checks": [
            {
                "id": "completed_cells",
                "status": "passed",
                "detail": f"{len(views)}/{len(manifest.cells)}",
            },
            {"id": "raw_hashes", "status": "passed", "detail": f"{len(views)} traces"},
            {
                "id": "row_citations",
                "status": "passed",
                "detail": f"{sum(len(view['nodes']) for view in views)} rows",
            },
            {"id": "state_continuity", "status": "passed", "detail": "all adjacent nodes"},
            {"id": "action_legality", "status": "passed", "detail": "all selected actions"},
            {"id": "event_choice_legality", "status": "passed", "detail": "all selected choices"},
            {"id": "delta_consistency", "status": "passed", "detail": "all numeric deltas"},
            {
                "id": "provider_health",
                "status": "passed",
                "detail": "0 fallback / 0 provider error",
            },
        ],
    }
    _write_json(output / "manifest.json", evidence_manifest)
    return evidence_manifest


def verify_playthrough_evidence(
    output_dir: str | Path,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    """Rehash retained source and derived views and recheck aggregate counts."""

    output = Path(output_dir).resolve()
    source = Path(source_root).resolve() if source_root is not None else output / "source"
    manifest = _load_json(output / "manifest.json")
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise PlaythroughViewError("playthrough evidence manifest schema mismatch")
    source_identity = manifest.get("source") or {}
    expected_truth_label = truth_label_for(
        str(source_identity.get("provider") or ""),
        str(source_identity.get("provider_mode") or ""),
    )
    if manifest.get("truth_label") != expected_truth_label:
        raise PlaythroughViewError("playthrough evidence truth label mismatch")
    if manifest.get("playthrough_data_ready") is not True:
        raise PlaythroughViewError("playthrough data is not marked ready")
    if any(check.get("status") != "passed" for check in manifest.get("checks") or []):
        raise PlaythroughViewError("playthrough evidence contains a failed check")

    _verify_artifact(source, manifest.get("source_campaign_manifest"))
    _verify_artifact(source, manifest.get("source_public_gate"))
    _verify_artifact(source, manifest.get("source_failure_clusters"))
    _verify_artifact(source, manifest.get("source_personas"))
    _verify_artifact(source, manifest.get("source_action_catalog"))
    for artifact in manifest.get("source_artifacts") or []:
        _verify_artifact(source, artifact)
    for artifact in manifest.get("derived_artifacts") or []:
        _verify_artifact(output, artifact)

    views = []
    for artifact in manifest.get("derived_artifacts") or []:
        if artifact.get("role") != "playthrough-view":
            continue
        view = _load_json(output / str(artifact["path"]))
        if (
            view.get("schema_version") != VIEW_SCHEMA
            or view.get("truth_label") != expected_truth_label
        ):
            raise PlaythroughViewError(f"invalid derived playthrough view: {artifact['path']}")
        if view.get("branch_semantics", {}).get("projected_counterfactual_states") is not False:
            raise PlaythroughViewError(
                f"counterfactual branch truth is ambiguous: {artifact['path']}"
            )
        views.append(view)
    node_count = sum(len(view.get("nodes") or []) for view in views)
    edge_count = sum(len(view.get("actual_edges") or []) for view in views)
    if len(views) != manifest.get("cell_count"):
        raise PlaythroughViewError("derived cell count mismatch")
    if node_count != manifest.get("node_count") or edge_count != manifest.get("actual_edge_count"):
        raise PlaythroughViewError("derived path aggregate mismatch")
    return {
        "status": "passed",
        "campaign_id": manifest["campaign_id"],
        "cells": len(views),
        "nodes": node_count,
        "actual_edges": edge_count,
        "truth_label": manifest["truth_label"],
    }


def build_cell_view(
    *,
    manifest: CampaignManifest,
    result: CampaignCellResult,
    trace_path: str | Path,
    summary_path: str | Path,
    attractors: dict[int, list[str]] | None = None,
) -> dict[str, Any]:
    """Validate one trace and convert its actual weekly sequence to UI data."""

    trace = Path(trace_path)
    summary = Path(summary_path)
    request = result.request
    truth_label = truth_label_for(
        result.source.provider.value,
        result.source.provider_mode.value,
    )
    expected = next((cell for cell in manifest.cells if cell.cell_id == request.cell_id), None)
    if expected is None or expected != request:
        raise PlaythroughViewError(
            f"cell {request.cell_id}: request is absent from campaign manifest"
        )
    if result.state.value != "completed" or result.error:
        raise PlaythroughViewError(f"cell {request.cell_id}: result is not a clean completion")
    if result.source != manifest.source or result.source_fingerprint != manifest.source_fingerprint:
        raise PlaythroughViewError(f"cell {request.cell_id}: source identity mismatch")

    artifact = next(
        (item for item in result.artifacts if item.path.endswith("playthrough.jsonl")), None
    )
    if artifact is None:
        raise PlaythroughViewError(f"cell {request.cell_id}: playthrough artifact is missing")
    if hashlib.sha256(trace.read_bytes()).hexdigest() != artifact.sha256:
        raise PlaythroughViewError(f"cell {request.cell_id}: raw trace hash mismatch")
    rows = _load_jsonl(trace)
    if len(rows) != result.completed_weeks or artifact.record_count != len(rows):
        raise PlaythroughViewError(f"cell {request.cell_id}: trace record count mismatch")
    if len(result.citations) != len(rows):
        raise PlaythroughViewError(f"cell {request.cell_id}: row citation count mismatch")

    nodes: list[dict[str, Any]] = []
    previous_after: dict[str, Any] | None = None
    attractor_map = attractors or {}
    for index, (row, citation) in enumerate(zip(rows, result.citations, strict=True), start=1):
        week = int(row.get("week", 0))
        if week != index or citation.week != week or citation.line_number != index:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: non-contiguous week at line {index}"
            )
        if row.get("run_id") != request.cell_id:
            raise PlaythroughViewError(f"cell {request.cell_id}: run id mismatch at week {week}")
        if canonical_sha256(row) != citation.record_sha256:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: citation hash mismatch at week {week}"
            )

        before_wrapper = _mapping(row, "state_before", request.cell_id, week)
        before = _mapping(before_wrapper, "state", request.cell_id, week)
        after = _mapping(row, "state_after", request.cell_id, week)
        result_payload = _mapping(row, "result", request.cell_id, week)
        result_state = _mapping(result_payload, "state", request.cell_id, week)
        if result_state != after:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: result/state_after mismatch at week {week}"
            )
        if previous_after is not None and before != previous_after:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: broken state continuity at week {week}"
            )

        available = _string_list(row.get("available_actions"))
        chosen = _string_list(row.get("chosen_actions"))
        if not available or not chosen or not set(chosen).issubset(available):
            raise PlaythroughViewError(
                f"cell {request.cell_id}: illegal selected action at week {week}"
            )
        decision = _mapping(row, "decision", request.cell_id, week)
        if _string_list(decision.get("actions")) != chosen:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: decision/action mismatch at week {week}"
            )
        if decision.get("persona") != request.persona.value or int(decision.get("week", 0)) != week:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: decision identity mismatch at week {week}"
            )

        event_id = str(row.get("triggered_event_id") or "")
        choice_id = str(row.get("event_choice_id") or "")
        legal_choices = result_payload.get("event_choices") or []
        if not isinstance(legal_choices, list) or any(
            not isinstance(item, dict) for item in legal_choices
        ):
            raise PlaythroughViewError(
                f"cell {request.cell_id}: invalid event choices at week {week}"
            )
        legal_choice_ids = {str(item.get("choice_id") or "") for item in legal_choices}
        if event_id and choice_id not in legal_choice_ids:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: illegal event choice at week {week}"
            )
        if not event_id and (choice_id or legal_choices):
            raise PlaythroughViewError(
                f"cell {request.cell_id}: choice without event at week {week}"
            )

        full_numeric_delta = _numeric_delta(before, after)
        expected_delta = {
            key: full_numeric_delta[key]
            for key in (
                "money",
                "energy",
                "stress",
                "hunger",
                "loneliness",
                "academic_progress",
                "exam_readiness",
                "language",
                "social",
                "visa_progress",
                "career_progress",
            )
            if key in full_numeric_delta
        }
        delta = row.get("delta") or {}
        if not isinstance(delta, dict) or delta != expected_delta:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: state delta mismatch at week {week}"
            )
        validation = _mapping(row, "validation", request.cell_id, week)
        if validation.get("valid") is not True or validation.get("fallback_used") is not False:
            raise PlaythroughViewError(
                f"cell {request.cell_id}: invalid/fallback decision at week {week}"
            )
        anomalies = row.get("anomalies") or []
        if not isinstance(anomalies, list) or any(not isinstance(item, dict) for item in anomalies):
            raise PlaythroughViewError(
                f"cell {request.cell_id}: malformed anomaly evidence at week {week}"
            )
        calls = row.get("persona_calls") or []
        if not isinstance(calls, list) or any(
            not _healthy_provider_call(
                call,
                provider=result.source.provider.value,
                mode=result.source.provider_mode.value,
            )
            for call in calls
        ):
            raise PlaythroughViewError(
                f"cell {request.cell_id}: unhealthy provider call at week {week}"
            )

        nodes.append(
            {
                "id": f"w{week}",
                "week": week,
                "kind": "actual",
                "state_before": before,
                "state_after": after,
                "delta": delta,
                "full_numeric_delta": full_numeric_delta,
                "available_action_ids": available,
                "selected_action_ids": chosen,
                "decision": {
                    "strategic_goal": str(decision.get("strategic_goal") or ""),
                    "risk_awareness": _string_list(decision.get("risk_awareness")),
                    "expected_tradeoff": str(decision.get("expected_tradeoff") or ""),
                    "confidence": decision.get("confidence"),
                },
                "event": {
                    "id": event_id,
                    "selected_choice_id": choice_id,
                    "legal_choices": legal_choices,
                },
                "risk_guidance": result_payload.get("risk_guidance"),
                "finished": bool(result_payload.get("finished")),
                "attractors": attractor_map.get(week, []),
                "anomalies": anomalies,
                "evidence": {
                    "source_line": index,
                    "source_record_sha256": citation.record_sha256,
                    "decision_request_fingerprint": _call_fingerprint(calls, "decision"),
                    "event_request_fingerprint": _call_fingerprint(calls, "event_choice"),
                },
            }
        )
        previous_after = after

    final_ending = _final_ending(summary)
    actual_edges = [
        {
            "id": f"w{week}-to-w{week + 1}",
            "from": f"w{week}",
            "to": f"w{week + 1}",
            "kind": "actual",
        }
        for week in range(1, len(nodes))
    ]
    return {
        "schema_version": VIEW_SCHEMA,
        "campaign_id": request.campaign_id,
        "cell_id": request.cell_id,
        "persona": request.persona.value,
        "seed": request.seed,
        "truth_label": truth_label,
        "provider": result.source.provider.value,
        "provider_mode": result.source.provider_mode.value,
        "provider_revision": result.source.provider_revision,
        "agent_commit": result.source.agent_commit,
        "game_commit": result.source.game_commit,
        "game_tree": result.source.game_tree,
        "scenario": request.scenario,
        "difficulty": request.difficulty,
        "completed_weeks": result.completed_weeks,
        "stop_reason": result.stop_reason.value,
        "final_ending": final_ending,
        "source_trace": {
            "artifact_path": artifact.path,
            "artifact_sha256": artifact.sha256,
            "record_count": artifact.record_count,
        },
        "nodes": nodes,
        "actual_edges": actual_edges,
        "branch_semantics": {
            "event_choices": "legal-options-not-executed-unless-selected",
            "available_actions": "legal-actions-not-future-state-branches",
            "projected_counterfactual_states": False,
        },
    }


def _attractor_index(payload: dict[str, Any], campaign_id: str) -> dict[str, dict[int, list[str]]]:
    index: dict[str, dict[int, list[str]]] = {}
    for cluster in payload.get("clusters") or []:
        cluster_id = str(cluster.get("cluster_id") or "")
        if not cluster_id or cluster_id == "provider-fallback":
            continue
        for member in cluster.get("members") or []:
            if member.get("campaign_id") != campaign_id:
                raise PlaythroughViewError("failure cluster campaign identity mismatch")
            cell_id = str(member.get("cell_id") or "")
            week = int(member.get("week") or 0)
            index.setdefault(cell_id, {}).setdefault(week, []).append(cluster_id)
    return index


def _build_persona_view(
    personas_path: Path,
    views: list[dict[str, Any]],
    action_tags: dict[str, tuple[str, ...]],
    truth_label: str,
) -> dict[str, Any]:
    config = yaml.safe_load(personas_path.read_text(encoding="utf-8"))
    personas = config.get("personas") if isinstance(config, dict) else None
    if not isinstance(personas, dict):
        raise PlaythroughViewError("player persona config is invalid")
    output = []
    for slug, contract in personas.items():
        cells = [view for view in views if view["persona"] == slug]
        selected = [
            action
            for view in cells
            for node in view["nodes"]
            for action in node["selected_action_ids"]
        ]
        tag_counts: Counter[str] = Counter()
        for action in selected:
            tag_counts.update(action_tags.get(action, ()))
        denominator = len(selected)
        first_attractor = [
            node["week"]
            for view in cells
            for node in view["nodes"]
            if "cashflow-stress-attractor" in node["attractors"]
        ]
        output.append(
            {
                "slug": slug,
                "contract": contract,
                "observed": {
                    "cell_count": len(cells),
                    "completed_cells": sum(
                        view["stop_reason"] in {"game_finished", "week_limit"} for view in cells
                    ),
                    "seeds": sorted(view["seed"] for view in cells),
                    "weeks": sum(view["completed_weeks"] for view in cells),
                    "final_endings": dict(
                        sorted(Counter(view["final_ending"] for view in cells).items())
                    ),
                    "first_cashflow_stress_attractor_weeks": sorted(first_attractor),
                    "selected_action_count": denominator,
                    "action_tag_rates": {
                        tag: round(count / denominator, 6)
                        for tag, count in sorted(tag_counts.items())
                    }
                    if denominator
                    else {},
                },
            }
        )
    return {"schema_version": PERSONAS_SCHEMA, "truth_label": truth_label, "personas": output}


def _action_tags(path: Path) -> dict[str, tuple[str, ...]]:
    payload = _load_json(path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise PlaythroughViewError("action catalog is invalid")
    return {
        str(item["id"]): tuple(_string_list(item.get("tags")))
        for item in items
        if isinstance(item, dict) and item.get("id")
    }


def truth_label_for(provider: str, mode: str) -> str:
    """Return the public truth label for an exact provider/mode pair."""

    try:
        return TRUTH_LABELS[(provider, mode)]
    except KeyError as exc:
        raise PlaythroughViewError(
            f"unsupported playthrough provider identity: {provider}/{mode}"
        ) from exc


def _healthy_provider_call(call: Any, *, provider: str, mode: str) -> bool:
    if (
        not isinstance(call, dict)
        or call.get("status") != "completed"
        or call.get("error") is not None
    ):
        return False
    metadata = call.get("metadata")
    return (
        isinstance(metadata, dict)
        and metadata.get("provider") == provider
        and metadata.get("mode") == mode
    )


def _call_fingerprint(calls: list[Any], phase: str) -> str:
    for call in calls:
        if isinstance(call, dict) and call.get("phase") == phase:
            return str(call.get("request_fingerprint") or "")
    return ""


def _numeric_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, int | float]:
    delta: dict[str, int | float] = {}
    for key in before.keys() & after.keys():
        left, right = before[key], after[key]
        if isinstance(left, bool) or isinstance(right, bool):
            continue
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            change = right - left
            if change:
                delta[key] = change
    return delta


def _final_ending(path: Path) -> str:
    match = re.search(
        r"^- final ending: \*\*(.+?)\*\*$", path.read_text(encoding="utf-8"), re.MULTILINE
    )
    if not match:
        raise PlaythroughViewError(f"final ending is missing from {path.name}")
    return match.group(1)


def _mapping(payload: dict[str, Any], key: str, cell_id: str, week: int) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise PlaythroughViewError(f"cell {cell_id}: {key} is not an object at week {week}")
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PlaythroughViewError(f"expected JSON object: {path}")
    return payload


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise PlaythroughViewError(f"expected JSON object at {path}:{index}")
        rows.append(payload)
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _artifact(root: Path, path: Path, *, role: str) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise PlaythroughViewError(f"artifact is outside evidence root: {resolved}") from exc
    safe = PurePosixPath(relative)
    if safe.is_absolute() or ".." in safe.parts:
        raise PlaythroughViewError(f"unsafe artifact path: {relative}")
    return {
        "path": relative,
        "role": role,
        "bytes": resolved.stat().st_size,
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def _verify_artifact(root: Path, artifact: Any) -> None:
    if not isinstance(artifact, dict):
        raise PlaythroughViewError("invalid artifact manifest entry")
    relative = str(artifact.get("path") or "")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise PlaythroughViewError(f"artifact escapes evidence root: {relative}") from exc
    if not path.is_file():
        raise PlaythroughViewError(f"artifact is missing: {relative}")
    if path.stat().st_size != artifact.get("bytes"):
        raise PlaythroughViewError(f"artifact byte count mismatch: {relative}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != artifact.get("sha256"):
        raise PlaythroughViewError(f"artifact hash mismatch: {relative}")


__all__ = [
    "MANIFEST_SCHEMA",
    "PERSONAS_SCHEMA",
    "TRUTH_LABEL",
    "VIEW_SCHEMA",
    "PlaythroughViewError",
    "build_cell_view",
    "build_playthrough_views",
    "truth_label_for",
    "verify_playthrough_evidence",
]
