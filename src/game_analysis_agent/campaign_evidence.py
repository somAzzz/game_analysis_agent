"""Deterministic recomputation of committed public campaign evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

from .campaign_aggregation import CampaignAggregation, FailureCluster
from .campaign_bundle import (
    PublicAgentEval,
    PublicFailureClusters,
    PublicPersonaCall,
    PublicPersonaRun,
)
from .campaign_contract import CampaignManifest, canonical_sha256


class CampaignEvidenceError(RuntimeError):
    """Raised when public campaign rows do not reproduce declared evidence."""


def recompute_public_evidence(bundle_dir: str | Path) -> dict[str, Any]:
    """Reparse and reproduce every headline metric from committed public rows."""

    bundle = Path(bundle_dir)
    summary = CampaignAggregation.model_validate_json(
        (bundle / "campaign_summary.json").read_text(encoding="utf-8")
    )
    manifest = CampaignManifest.model_validate_json(
        (bundle / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    runs = _read_jsonl(bundle / "persona_runs.jsonl", PublicPersonaRun)
    evals = _read_jsonl(bundle / "agent_eval.jsonl", PublicAgentEval)
    calls = _read_jsonl(bundle / "llm_calls.jsonl", PublicPersonaCall)
    expected_cells = {item.cell_id for item in manifest.cells}
    run_cells = {item.cell_id for item in runs}
    eval_cells = {item.cell_id for item in evals}
    if run_cells != expected_cells or eval_cells != expected_cells:
        raise CampaignEvidenceError("public rows do not cover the exact manifest cells")
    if len(calls) != len(runs) * 2:
        raise CampaignEvidenceError(
            "Replay call evidence must contain decision and event per week"
        )
    call_counts = Counter((item.cell_id, item.week, item.phase) for item in calls)
    if set(call_counts.values()) != {1} or any(
        call_counts[(run.cell_id, run.week, phase)] != 1
        for run in runs
        for phase in ("decision", "event_choice")
    ):
        raise CampaignEvidenceError(
            "public Replay call phases are incomplete or duplicated"
        )
    alignment_weight = sum(
        (item.persona_alignment_rate or 0) * item.weeks
        for item in evals
        if item.persona_alignment_rate is not None
    )
    alignment_weeks = sum(
        item.weeks for item in evals if item.persona_alignment_rate is not None
    )
    recomputed = {
        "expected_cells": len(expected_cells),
        "completed_cells": len(evals),
        "total_weeks": len(runs),
        "mean_final_money": _mean(
            [item.final_money for item in evals if item.final_money is not None]
        ),
        "mean_max_stress": _mean(
            [item.max_stress for item in evals if item.max_stress is not None]
        ),
        "valid_rate": _ratio(sum(item.valid for item in runs), len(runs)),
        "fallback_rate": _ratio(sum(item.fallback_used for item in runs), len(runs)),
        "provider_error_rate": _ratio(
            sum(item.provider_error for item in runs), len(runs)
        ),
        "persona_alignment_rate": (
            round(alignment_weight / alignment_weeks, 6) if alignment_weeks else None
        ),
    }
    declared = summary.metrics.model_dump(mode="json")
    for key, value in recomputed.items():
        if declared[key] != value:
            raise CampaignEvidenceError(f"public metric mismatch: {key}")
    if any(item.status != "completed" for item in calls):
        raise CampaignEvidenceError("public Replay evidence contains failed provider calls")
    return {
        **recomputed,
        "replay_calls": len(calls),
        "request_fingerprint": manifest.request_fingerprint,
        "source_fingerprint": manifest.source_fingerprint,
    }


def recompute_public_clusters(bundle_dir: str | Path) -> dict[str, Any]:
    """Rebuild first consecutive failure entries from public weekly rows."""

    bundle = Path(bundle_dir)
    rows = _read_jsonl(bundle / "persona_runs.jsonl", PublicPersonaRun)
    declared = PublicFailureClusters.model_validate_json(
        (bundle / "failure_clusters.json").read_text(encoding="utf-8")
    )
    by_cell: dict[str, list[tuple[int, PublicPersonaRun]]] = defaultdict(list)
    for line_number, row in enumerate(rows, start=1):
        by_cell[row.cell_id].append((line_number, row))
    counts = {}
    for cluster in declared.clusters:
        observed = []
        for cell_id in sorted(by_cell):
            cell_rows = sorted(by_cell[cell_id], key=lambda item: item[1].week)
            signals = [_matches(cluster, item[1]) for item in cell_rows]
            first = _first_consecutive(signals, cluster.rule.consecutive_weeks)
            if first is None:
                continue
            line_number, row = cell_rows[first - 1]
            observed.append(
                (
                    row.cell_id,
                    row.persona,
                    row.seed,
                    row.week,
                    line_number,
                    canonical_sha256(row.model_dump(mode="json")),
                )
            )
        claimed = sorted(
            (
                item.cell_id,
                item.persona.value,
                item.seed,
                item.week,
                item.line_number,
                item.record_sha256,
            )
            for item in cluster.members
        )
        if sorted(observed) != claimed:
            raise CampaignEvidenceError(
                f"cluster membership mismatch: {cluster.cluster_id}"
            )
        if cluster.member_count != len(observed):
            raise CampaignEvidenceError(
                f"cluster count mismatch: {cluster.cluster_id}"
            )
        counts[cluster.cluster_id] = len(observed)
    return {"cluster_counts": counts, "clusters_recomputed": len(counts)}


def _matches(cluster: FailureCluster, row: PublicPersonaRun) -> bool:
    rule = cluster.rule
    if rule.money_lte is not None and (row.money is None or row.money > rule.money_lte):
        return False
    if rule.stress_gte is not None and (
        row.stress is None or row.stress < rule.stress_gte
    ):
        return False
    return rule.fallback_used is None or row.fallback_used is rule.fallback_used


def _first_consecutive(values: list[bool], length: int) -> int | None:
    streak = 0
    for index, matched in enumerate(values, start=1):
        streak = streak + 1 if matched else 0
        if streak >= length:
            return index - length + 1
    return None


def _read_jsonl(path: Path, model) -> list[Any]:  # noqa: ANN001
    return [
        model.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _mean(values: list[float]) -> float | None:
    return round(fmean(values), 6) if values else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


__all__ = [
    "CampaignEvidenceError",
    "recompute_public_clusters",
    "recompute_public_evidence",
]
