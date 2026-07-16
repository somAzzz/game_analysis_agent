"""Public-safe, hash-verified bundle for one repair experiment."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .repair_experiment import RepairCohort, RepairExperimentRecord
from .repair_verification import CohortEvidence

REPAIR_BUNDLE_GATE_SCHEMA = "repair-bundle-gate-v1"
COHORT_PATHS = {
    RepairCohort.BASELINE_FIXED: "baseline/fixed.json",
    RepairCohort.BASELINE_HOLDOUT: "baseline/holdout.json",
    RepairCohort.PATCHED_FIXED: "patched/fixed.json",
    RepairCohort.PATCHED_HOLDOUT: "patched/holdout.json",
}


class RepairBundleError(RuntimeError):
    """Raised when private experiment evidence cannot become a safe bundle."""


class RepairBundleArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)


class RepairBundleGate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[REPAIR_BUNDLE_GATE_SCHEMA] = REPAIR_BUNDLE_GATE_SCHEMA
    experiment_id: str
    status: Literal["passed"] = "passed"
    decision: Literal["accepted", "rejected"]
    artifacts: tuple[RepairBundleArtifact, ...]
    checks: tuple[str, ...]


def build_public_repair_bundle(
    *,
    project_root: str | Path,
    private_record: str | Path,
    destination: str | Path,
) -> RepairBundleGate:
    project = Path(project_root).resolve()
    record_path = Path(private_record).resolve()
    target = Path(destination)
    if not target.is_absolute():
        target = project / target
    target.mkdir(parents=True, exist_ok=True)
    record = RepairExperimentRecord.model_validate_json(
        record_path.read_text(encoding="utf-8")
    )
    snapshots = []
    for snapshot in record.snapshots:
        source = project / snapshot.artifact_path
        _require_hash(source, snapshot.artifact_sha256)
        cohort = CohortEvidence.model_validate_json(source.read_text(encoding="utf-8"))
        if cohort.cohort != snapshot.cohort or cohort.game_commit != snapshot.game_commit:
            raise RepairBundleError("cohort artifact identity differs from snapshot")
        relative = COHORT_PATHS[snapshot.cohort]
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        _write_json(output, cohort.model_dump(mode="json"))
        snapshots.append(
            snapshot.model_copy(
                update={"artifact_path": relative, "artifact_sha256": _sha(output)}
            )
        )
    patch_source = project / record.patch.patch_path
    _require_hash(patch_source, record.patch.patch_sha256)
    patch_output = target / "patch.diff"
    patch_output.write_bytes(patch_source.read_bytes())
    public_patch = record.patch.model_copy(
        update={"patch_path": "patch.diff", "patch_sha256": _sha(patch_output)}
    )
    public_record = RepairExperimentRecord.model_validate(
        record.model_dump(mode="json")
        | {
            "patch": public_patch.model_dump(mode="json"),
            "snapshots": [item.model_dump(mode="json") for item in snapshots],
        }
    )
    _write_json(target / "repair_experiment.json", public_record.model_dump(mode="json"))
    _write_json(target / "comparison.json", public_record.comparison.model_dump(mode="json"))
    (target / "repair_summary.md").write_text(
        _summary(public_record), encoding="utf-8"
    )
    names = [
        "repair_experiment.json",
        "repair_summary.md",
        "comparison.json",
        "patch.diff",
        *COHORT_PATHS.values(),
    ]
    _scan_public_safety(target, names)
    artifacts = tuple(
        RepairBundleArtifact(
            path=name, sha256=_sha(target / name), bytes=(target / name).stat().st_size
        )
        for name in names
    )
    gate = RepairBundleGate(
        experiment_id=public_record.plan.experiment_id,
        decision=public_record.decision.value,
        artifacts=artifacts,
        checks=(
            "record_reparsed",
            "four_cohorts_reparsed",
            "patch_hash_verified",
            "comparison_recomputed_by_record_schema",
            "public_safety_scan_passed",
        ),
    )
    _write_json(target / "gate_report.json", gate.model_dump(mode="json"))
    return verify_public_repair_bundle(target)


def verify_public_repair_bundle(path: str | Path) -> RepairBundleGate:
    root = Path(path)
    gate = RepairBundleGate.model_validate_json(
        (root / "gate_report.json").read_text(encoding="utf-8")
    )
    for artifact in gate.artifacts:
        _require_hash(root / artifact.path, artifact.sha256)
    record = RepairExperimentRecord.model_validate_json(
        (root / "repair_experiment.json").read_text(encoding="utf-8")
    )
    if record.plan.experiment_id != gate.experiment_id:
        raise RepairBundleError("repair gate experiment identity mismatch")
    for snapshot in record.snapshots:
        CohortEvidence.model_validate_json(
            (root / snapshot.artifact_path).read_text(encoding="utf-8")
        )
        _require_hash(root / snapshot.artifact_path, snapshot.artifact_sha256)
    _scan_public_safety(root, [item.path for item in gate.artifacts])
    return gate


def _summary(record: RepairExperimentRecord) -> str:
    lines = [
        "# Repair experiment",
        "",
        f"- Decision: **{record.decision.value}**",
        f"- Hypothesis: {record.plan.hypothesis}",
        f"- Mechanism: `{record.plan.mechanism_class}`",
        f"- Fixed target reduction: {record.comparison.fixed_relative_reduction:.1%}",
        f"- Holdout target reduction: {record.comparison.holdout_relative_reduction:.1%}",
        f"- Reason: {record.decision_reason}",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- {item.gate_id}: **{item.status.value}** — {item.detail}"
        for item in record.gates
    )
    return "\n".join(lines) + "\n"


def _scan_public_safety(root: Path, names: list[str]) -> None:
    forbidden = re.compile(
        r"(?i)(?:api[_-]?key|authorization|bearer\s+[a-z0-9._-]{16,}|"
        r"sk-(?:proj-)?[a-z0-9_-]{20,}|/(?:Users|home)/[^/\s\"']+)"
    )
    findings = []
    for name in names:
        path = root / name
        if path.suffix in {".json", ".md", ".diff"} and forbidden.search(
            path.read_text(encoding="utf-8", errors="replace")
        ):
            findings.append(name)
    if findings:
        raise RepairBundleError(f"repair public-safety scan failed: {findings}")


def _require_hash(path: Path, expected: str) -> None:
    if not path.is_file() or _sha(path) != expected:
        raise RepairBundleError(f"repair artifact hash mismatch: {path.name}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "REPAIR_BUNDLE_GATE_SCHEMA",
    "RepairBundleError",
    "RepairBundleGate",
    "build_public_repair_bundle",
    "verify_public_repair_bundle",
]
