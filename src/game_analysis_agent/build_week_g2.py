"""Fail-closed independent review of the committed Build Week campaign."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from .build_week_campaign import FrozenRepairTarget
from .campaign_aggregation import CampaignAggregation, FailureCluster
from .campaign_bundle import (
    PublicAgentEval,
    PublicFailureClusters,
    PublicPersonaCall,
    PublicPersonaRun,
    verify_public_campaign_bundle,
)
from .campaign_contract import CampaignManifest, CampaignRequest, canonical_sha256

G2_SCHEMA = "build-week-g2-review-v1"


class G2ReviewError(RuntimeError):
    """Raised when committed campaign evidence cannot be reviewed safely."""


def review_g2(
    *,
    project_root: str | Path,
    game_root: str | Path,
    bundle_dir: str | Path,
    target_path: str | Path,
    campaign_config: str | Path,
    replay_manifest: str | Path,
    execute_commands: bool = True,
) -> dict[str, Any]:
    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    bundle = Path(bundle_dir).resolve()
    target_file = Path(target_path).resolve()
    config_file = Path(campaign_config).resolve()
    replay_file = Path(replay_manifest).resolve()
    checks: list[dict[str, Any]] = []

    _capture(checks, "bundle_integrity", lambda: _bundle_evidence(bundle))
    _capture(
        checks,
        "source_identity",
        lambda: _source_evidence(project, game, bundle, config_file, replay_file),
    )
    _capture(checks, "public_recomputation", lambda: recompute_public_evidence(bundle))
    _capture(checks, "cluster_recomputation", lambda: recompute_public_clusters(bundle))
    _capture(checks, "target_freeze", lambda: _target_evidence(bundle, target_file))
    if execute_commands:
        for check_id, command in (
            ("ruff", ["uv", "run", "ruff", "check", "."]),
            ("full_pytest", ["uv", "run", "pytest", "-q"]),
        ):
            _capture(
                checks,
                check_id,
                lambda command=command: _command_evidence(project, command),
            )
    failures = [item for item in checks if item["status"] == "failed"]
    return {
        "schema_version": G2_SCHEMA,
        "gate": "G2",
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "reviewed_commit": _git(project, "rev-parse", "HEAD"),
        "checks": checks,
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": [item["id"] for item in failures],
    }


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
        raise G2ReviewError("public rows do not cover the exact manifest cells")
    if len(calls) != len(runs) * 2:
        raise G2ReviewError("Replay call evidence must contain decision and event per week")
    call_counts = Counter((item.cell_id, item.week, item.phase) for item in calls)
    if set(call_counts.values()) != {1} or any(
        call_counts[(run.cell_id, run.week, phase)] != 1
        for run in runs
        for phase in ("decision", "event_choice")
    ):
        raise G2ReviewError("public Replay call phases are incomplete or duplicated")
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
            raise G2ReviewError(f"public metric mismatch: {key}")
    if any(item.status != "completed" for item in calls):
        raise G2ReviewError("public Replay evidence contains failed provider calls")
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
            raise G2ReviewError(f"cluster membership mismatch: {cluster.cluster_id}")
        if cluster.member_count != len(observed):
            raise G2ReviewError(f"cluster count mismatch: {cluster.cluster_id}")
        counts[cluster.cluster_id] = len(observed)
    return {"cluster_counts": counts, "clusters_recomputed": len(counts)}


def write_g2_review(
    *, json_path: str | Path, markdown_path: str | Path, review: Mapping[str, Any]
) -> tuple[Path, Path]:
    json_destination = Path(json_path)
    markdown_destination = Path(markdown_path)
    json_destination.parent.mkdir(parents=True, exist_ok=True)
    markdown_destination.parent.mkdir(parents=True, exist_ok=True)
    json_destination.write_text(
        json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# G2 Campaign Evidence Review",
        "",
        f"- Decision: **{review['status']}**",
        f"- Reviewed commit: `{review['reviewed_commit']}`",
        f"- Checks: {review['check_count']}",
        f"- Failures: {review['failure_count']}",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for item in review["checks"]:
        evidence = json.dumps(item["evidence"], ensure_ascii=False, sort_keys=True)
        lines.append(f"| {item['id']} | {item['status']} | `{evidence}` |")
    lines.extend(["", "## Decision", "", "G2 passed with no conditions." if review["status"] == "passed" else "G2 failed closed.", ""])
    markdown_destination.write_text("\n".join(lines), encoding="utf-8")
    return json_destination, markdown_destination


def _bundle_evidence(bundle: Path) -> dict[str, Any]:
    gate = verify_public_campaign_bundle(bundle)
    return {
        "campaign_id": gate.campaign_id,
        "artifacts_hashed": len(gate.artifacts),
        "checks": len(gate.checks),
        "status": gate.status,
    }


def _source_evidence(
    project: Path,
    game: Path,
    bundle: Path,
    config_path: Path,
    replay_path: Path,
) -> dict[str, Any]:
    manifest = CampaignManifest.model_validate_json(
        (bundle / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    config = CampaignRequest.model_validate_json(config_path.read_text(encoding="utf-8"))
    source = manifest.source
    if manifest.request != config:
        raise G2ReviewError("committed campaign config differs from manifest request")
    if hashlib.sha256(config_path.read_bytes()).hexdigest() != source.campaign_config_sha256:
        raise G2ReviewError("campaign config hash differs from source identity")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    fixture = project / str(replay["fixture"])
    fixture_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
    if fixture_hash != replay["sha256"] or source.provider_revision != f"fixture:{fixture_hash}":
        raise G2ReviewError("Replay source revision cannot be reproduced")
    marker = json.loads((game / ".playtest-forge-source.json").read_text(encoding="utf-8"))
    if (
        source.game_commit != marker["commit"]
        or source.game_tree != marker["tree"]
        or source.game_archive_sha256 != marker["archive_sha256"]
    ):
        raise G2ReviewError("game source marker differs from campaign source")
    tree = _git(project, "rev-parse", f"{source.agent_commit}^{{tree}}")
    if tree != source.agent_tree:
        raise G2ReviewError("agent commit/tree identity mismatch")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", source.agent_commit, "HEAD"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    return {
        "agent_commit": source.agent_commit,
        "agent_tree": source.agent_tree,
        "game_commit": source.game_commit,
        "fixture_sha256": fixture_hash,
        "campaign_config_sha256": source.campaign_config_sha256,
    }


def _target_evidence(bundle: Path, target_path: Path) -> dict[str, Any]:
    target = FrozenRepairTarget.model_validate_json(target_path.read_text(encoding="utf-8"))
    manifest = CampaignManifest.model_validate_json(
        (bundle / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    clusters = PublicFailureClusters.model_validate_json(
        (bundle / "failure_clusters.json").read_text(encoding="utf-8")
    )
    matches = [
        item for item in clusters.clusters if item.cluster_id == target.selected_cluster_id
    ]
    if len(matches) != 1:
        raise G2ReviewError("target does not resolve to exactly one cluster")
    cluster = matches[0]
    if (
        target.campaign_request_fingerprint != manifest.request_fingerprint
        or target.campaign_source_fingerprint != manifest.source_fingerprint
        or target.member_count != cluster.member_count
        or target.persona_count != len(cluster.persona_counts)
    ):
        raise G2ReviewError("target identity/counts differ from campaign evidence")
    lines = (bundle / "persona_runs.jsonl").read_text(encoding="utf-8").splitlines()
    member_keys = {
        (item.cell_id, item.week, item.line_number, item.record_sha256)
        for item in cluster.members
    }
    for citation in target.evidence:
        key = (
            citation.cell_id,
            citation.week,
            citation.line_number,
            citation.record_sha256,
        )
        if key not in member_keys:
            raise G2ReviewError("target cites a row outside the selected cluster")
        row = json.loads(lines[citation.line_number - 1])
        if canonical_sha256(row) != citation.record_sha256:
            raise G2ReviewError("target citation row hash mismatch")
    if set(target.fixed_seeds) != set(manifest.request.seeds):
        raise G2ReviewError("target fixed seeds differ from campaign seeds")
    return {
        "selected_cluster_id": target.selected_cluster_id,
        "members": target.member_count,
        "personas": target.persona_count,
        "evidence_rows": len(target.evidence),
        "fixed_seeds": list(target.fixed_seeds),
        "holdout_seeds": list(target.holdout_seeds),
        "disjoint": set(target.fixed_seeds).isdisjoint(target.holdout_seeds),
    }


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


def _capture(
    checks: list[dict[str, Any]], check_id: str, operation: Callable[[], Any]
) -> None:
    try:
        evidence = operation()
    except Exception as exc:
        checks.append(
            {
                "id": check_id,
                "status": "failed",
                "evidence": {},
                "error": f"{exc.__class__.__name__}: {str(exc)[:300]}",
            }
        )
    else:
        checks.append(
            {"id": check_id, "status": "passed", "evidence": evidence, "error": ""}
        )


def _command_evidence(project: Path, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command, cwd=project, check=False, capture_output=True, text=True
    )
    if completed.returncode:
        raise G2ReviewError(
            f"command failed ({completed.returncode}): {' '.join(command)}"
        )
    output = (completed.stdout + completed.stderr).strip()
    return {"command": command, "exit_code": completed.returncode, "tail": output[-500:]}


def _git(project: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


__all__ = [
    "G2ReviewError",
    "G2_SCHEMA",
    "recompute_public_clusters",
    "recompute_public_evidence",
    "review_g2",
    "write_g2_review",
]
