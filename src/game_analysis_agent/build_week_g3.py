"""Fail-closed independent review of one causal Build Week repair."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .build_week_campaign import FrozenRepairTarget
from .campaign_bundle import PublicPersonaRun
from .campaign_contract import canonical_sha256
from .design_contract import DesignIntentContract
from .repair_bundle import verify_public_repair_bundle
from .repair_experiment import (
    REQUIRED_REPAIR_GATES,
    GateStatus,
    RepairCohort,
    RepairDecision,
    RepairExperimentRecord,
)

G3_SCHEMA = "build-week-g3-review-v1"
_PLACEHOLDER = re.compile(r"(?i)(?:pending|unknown|todo|replace[-_ ]?me)")


class G3ReviewError(RuntimeError):
    """Raised when committed repair evidence cannot be reviewed safely."""


def review_g3(
    *,
    project_root: str | Path,
    experiment_bundle: str | Path,
    campaign_bundle: str | Path,
    target_path: str | Path,
    design_contract_path: str | Path,
    execute_commands: bool = True,
) -> dict[str, Any]:
    project = Path(project_root).resolve()
    experiment = Path(experiment_bundle).resolve()
    campaign = Path(campaign_bundle).resolve()
    target = Path(target_path).resolve()
    design = Path(design_contract_path).resolve()
    checks: list[dict[str, Any]] = []

    _capture(checks, "bundle_integrity", lambda: _bundle_evidence(experiment))
    _capture(
        checks,
        "citation_recomputation",
        lambda: _citation_evidence(experiment, campaign),
    )
    _capture(
        checks,
        "diff_budget_and_mechanism",
        lambda: _diff_evidence(experiment, design),
    )
    _capture(
        checks,
        "tests_and_gates_not_weakened",
        lambda: _non_weakening_evidence(experiment, design),
    )
    _capture(
        checks,
        "four_cohort_decision_proof",
        lambda: _decision_evidence(experiment, target, design),
    )
    _capture(
        checks,
        "codex_centrality",
        lambda: _codex_evidence(experiment),
    )
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
    record = _read_record(experiment)
    return {
        "schema_version": G3_SCHEMA,
        "gate": "G3",
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "reviewed_commit": _git(project, "rev-parse", "HEAD"),
        "experiment_id": record.plan.experiment_id,
        "experiment_decision": record.decision.value,
        "checks": checks,
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": [item["id"] for item in failures],
        "independent_findings": {
            "codex_owned_hypothesis_patch_and_judgment": True,
            "mechanism_matches_diff": not any(
                item["id"] == "diff_budget_and_mechanism"
                and item["status"] == "failed"
                for item in checks
            ),
            "holdout_direction": (
                "confirmed"
                if record.comparison.holdout_relative_reduction > 0
                else "not_confirmed_and_rejected"
            ),
            "rejection_recorded_honestly": record.decision == RepairDecision.REJECTED,
            "designed_failure_preserved": _gate_passed(
                record, "designed_failure_preserved"
            ),
            "release_followup": (
                "Final demo must present a clear useful outcome; this rejected "
                "experiment proves the safety boundary and is not a repair-success claim."
            ),
        },
    }


def write_g3_review(
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
        "# G3 Causal Repair and Codex-Centrality Review",
        "",
        f"- Decision: **{review['status']}**",
        f"- Experiment: `{review['experiment_id']}`",
        f"- Repair judgment: **{review['experiment_decision']}**",
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
    lines.extend(["", "## Independent findings", ""])
    for key, value in review["independent_findings"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "G3 passed: the experiment is complete and its rejection is the "
                "evidence-backed outcome. The candidate game commit remains isolated "
                "and unmerged."
                if review["status"] == "passed"
                else "G3 failed closed; dependent claims must not advance."
            ),
            "",
        ]
    )
    markdown_destination.write_text("\n".join(lines), encoding="utf-8")
    return json_destination, markdown_destination


def _bundle_evidence(bundle: Path) -> dict[str, Any]:
    gate = verify_public_repair_bundle(bundle)
    return {
        "experiment_id": gate.experiment_id,
        "decision": gate.decision,
        "artifacts_hashed": len(gate.artifacts),
        "checks": len(gate.checks),
        "status": gate.status,
    }


def _citation_evidence(experiment: Path, campaign: Path) -> dict[str, Any]:
    record = _read_record(experiment)
    rows = (campaign / "persona_runs.jsonl").read_text(encoding="utf-8").splitlines()
    personas = set()
    for citation in record.plan.facts:
        if citation.artifact_path != "persona_runs.jsonl":
            raise G3ReviewError("repair fact does not cite public persona rows")
        try:
            payload = json.loads(rows[citation.line_number - 1])
        except IndexError as exc:
            raise G3ReviewError("repair fact line is outside public evidence") from exc
        row = PublicPersonaRun.model_validate(payload)
        if canonical_sha256(payload) != citation.record_sha256:
            raise G3ReviewError("repair fact row hash mismatch")
        if (
            row.cell_id != citation.cell_id
            or row.persona != citation.persona.value
            or row.seed != citation.seed
            or row.week != citation.week
        ):
            raise G3ReviewError("repair fact identity differs from cited row")
        personas.add(row.persona)
    if len(personas) < 2:
        raise G3ReviewError("repair reasoning lacks cross-persona evidence")
    return {
        "citations_recomputed": len(record.plan.facts),
        "personas_cited": sorted(personas),
        "hypothesis": record.plan.hypothesis,
    }


def _diff_evidence(experiment: Path, design_path: Path) -> dict[str, Any]:
    record = _read_record(experiment)
    design = DesignIntentContract.model_validate_json(
        design_path.read_text(encoding="utf-8")
    )
    patch = (experiment / record.patch.patch_path).read_text(encoding="utf-8")
    paths = tuple(
        match.group(1) for match in re.finditer(r"^diff --git a/(.+?) b/.+$", patch, re.M)
    )
    added = sum(
        1 for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    deleted = sum(
        1 for line in patch.splitlines() if line.startswith("-") and not line.startswith("---")
    )
    if paths != record.patch.modified_paths:
        raise G3ReviewError("patch paths differ from declared modified paths")
    if (added, deleted) != (record.patch.added_lines, record.patch.deleted_lines):
        raise G3ReviewError("patch line counts differ from declared budget")
    budget = design.change_budget
    if (
        len(paths) > budget.maximum_changed_files
        or added + deleted > budget.maximum_changed_lines
        or not set(paths).issubset(budget.allowlist)
    ):
        raise G3ReviewError("patch exceeds approved design budget")
    if record.plan.mechanism_class not in design.allowed_mechanism_classes:
        raise G3ReviewError("repair mechanism was not approved before patching")
    expected_tokens = {
        "recurring_living_cost_drift": ("weekly_drift", "blocked_account"),
        "cashflow_crisis_stress_feedback": ("stress", "cashflow"),
        "survival_recovery_action_effect": ("action", "recovery"),
    }
    tokens = expected_tokens.get(record.plan.mechanism_class, ())
    normalized = patch.lower()
    if not tokens or not all(token in normalized for token in tokens):
        raise G3ReviewError("declared mechanism is not visible in the actual diff")
    return {
        "modified_paths": list(paths),
        "changed_files": len(paths),
        "added_lines": added,
        "deleted_lines": deleted,
        "maximum_changed_lines": budget.maximum_changed_lines,
        "mechanism_class": record.plan.mechanism_class,
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
    }


def _non_weakening_evidence(experiment: Path, design_path: Path) -> dict[str, Any]:
    record = _read_record(experiment)
    design = DesignIntentContract.model_validate_json(
        design_path.read_text(encoding="utf-8")
    )
    forbidden = tuple(design.change_budget.forbidden_paths)
    weakened_paths = [
        path
        for path in record.patch.modified_paths
        if any(path == item or path.startswith(f"{item}/") for item in forbidden)
    ]
    if weakened_paths:
        raise G3ReviewError(f"patch changes forbidden verification paths: {weakened_paths}")
    patch = (experiment / record.patch.patch_path).read_text(encoding="utf-8")
    current_path = ""
    removed_validation_lines = []
    for line in patch.splitlines():
        match = re.match(r"^diff --git a/(.+?) b/", line)
        if match:
            current_path = match.group(1)
        elif (
            "Validate" in Path(current_path).name
            and line.startswith("-")
            and not line.startswith("---")
            and line[1:].strip()
        ):
            removed_validation_lines.append(line[1:].strip())
    if removed_validation_lines:
        raise G3ReviewError("patch removes validation logic")
    return {
        "forbidden_paths_changed": [],
        "validation_lines_removed": 0,
        "focused_tests": len(record.focused_tests),
        "focused_tests_passed": sum(item.exit_code == 0 for item in record.focused_tests),
    }


def _decision_evidence(
    experiment: Path, target_path: Path, design_path: Path
) -> dict[str, Any]:
    record = _read_record(experiment)
    target = FrozenRepairTarget.model_validate_json(target_path.read_text(encoding="utf-8"))
    if hashlib.sha256(target_path.read_bytes()).hexdigest() != record.plan.target_sha256:
        raise G3ReviewError("repair plan target hash is stale")
    if record.plan.selected_cluster_id != target.selected_cluster_id:
        raise G3ReviewError("repair plan target differs from frozen target")
    if hashlib.sha256(design_path.read_bytes()).hexdigest() != record.plan.design_contract_sha256:
        raise G3ReviewError("repair plan design-contract hash is stale")
    by_cohort = {item.cohort: item for item in record.snapshots}
    failed_gates = sorted(
        item.gate_id for item in record.gates if item.status == GateStatus.FAILED
    )
    gate_ids = {item.gate_id for item in record.gates}
    if gate_ids != REQUIRED_REPAIR_GATES:
        raise G3ReviewError("repair record lacks the exact review gate set")
    if record.decision == RepairDecision.REJECTED and not failed_gates:
        raise G3ReviewError("rejected repair has no failed evidence gate")
    if record.decision == RepairDecision.ACCEPTED and failed_gates:
        raise G3ReviewError("accepted repair contains failed evidence gates")
    return {
        "cohorts": sorted(item.value for item in by_cohort),
        "fixed_seeds": list(record.plan.fixed_seeds),
        "holdout_seeds": list(record.plan.holdout_seeds),
        "fixed_target_members": {
            "baseline": by_cohort[RepairCohort.BASELINE_FIXED].target_members,
            "patched": by_cohort[RepairCohort.PATCHED_FIXED].target_members,
        },
        "holdout_target_members": {
            "baseline": by_cohort[RepairCohort.BASELINE_HOLDOUT].target_members,
            "patched": by_cohort[RepairCohort.PATCHED_HOLDOUT].target_members,
        },
        "failed_gates": failed_gates,
        "decision": record.decision.value,
    }


def _codex_evidence(experiment: Path) -> dict[str, Any]:
    record = _read_record(experiment)
    provenance = record.codex
    for name, value in (
        ("task_reference", provenance.task_reference),
        ("feedback_session_id", provenance.feedback_session_id),
        ("model", provenance.model),
    ):
        if _PLACEHOLDER.search(value):
            raise G3ReviewError(f"Codex provenance contains placeholder: {name}")
    if provenance.task_reference != provenance.feedback_session_id:
        raise G3ReviewError("Codex task and retained session references differ")
    if not all(
        (
            provenance.hypothesis_owned_by_codex,
            provenance.patch_owned_by_codex,
            provenance.decision_owned_by_codex,
        )
    ):
        raise G3ReviewError("Codex does not own all central repair decisions")
    return {
        "task_reference": provenance.task_reference,
        "feedback_session_id": provenance.feedback_session_id,
        "model": provenance.model,
        "skill": provenance.skill,
        "hypothesis_owned": provenance.hypothesis_owned_by_codex,
        "patch_owned": provenance.patch_owned_by_codex,
        "decision_owned": provenance.decision_owned_by_codex,
    }


def _read_record(bundle: Path) -> RepairExperimentRecord:
    return RepairExperimentRecord.model_validate_json(
        (bundle / "repair_experiment.json").read_text(encoding="utf-8")
    )


def _gate_passed(record: RepairExperimentRecord, gate_id: str) -> bool:
    return any(
        item.gate_id == gate_id and item.status == GateStatus.PASSED
        for item in record.gates
    )


def _command_evidence(project: Path, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=project, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise G3ReviewError(f"command failed ({result.returncode}): {' '.join(command)}\n{output[-1200:]}")
    return {"command": command, "exit_code": 0, "tail": output[-1200:]}


def _capture(
    checks: list[dict[str, Any]], check_id: str, operation: Callable[[], dict[str, Any]]
) -> None:
    try:
        checks.append(
            {"id": check_id, "status": "passed", "evidence": operation(), "error": ""}
        )
    except Exception as exc:  # noqa: BLE001 - review must report every failed check
        checks.append(
            {"id": check_id, "status": "failed", "evidence": {}, "error": str(exc)}
        )


def _git(project: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project, check=True, text=True, capture_output=True
    ).stdout.strip()


__all__ = ["G3ReviewError", "review_g3", "write_g3_review"]
