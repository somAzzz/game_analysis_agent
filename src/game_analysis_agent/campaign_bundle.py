"""Build and verify the public-safe Build Week campaign evidence bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .campaign_aggregation import CampaignAggregation, FailureCluster
from .campaign_contract import (
    CampaignCellResult,
    CampaignCitation,
    CampaignManifest,
    canonical_sha256,
)
from .persona_gateway import PersonaCallMetadata, PersonaProviderError
from .persona_runtime import redact_sensitive_text

BUNDLE_GATE_SCHEMA = "campaign-bundle-gate-v1"
PERSONA_RUN_SCHEMA = "public-persona-run-v1"
AGENT_EVAL_SCHEMA = "public-agent-eval-v1"
LLM_CALL_SCHEMA = "public-persona-call-v1"
CLUSTERS_SCHEMA = "public-failure-clusters-v1"
FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "messages",
    "prompt",
    "prompt_text",
    "response_text",
    "system_prompt",
    "user_prompt",
}


class CampaignBundleError(RuntimeError):
    """Raised when a public bundle cannot pass its own evidence gate."""


class PublicPersonaRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[PERSONA_RUN_SCHEMA] = PERSONA_RUN_SCHEMA
    campaign_id: str
    cell_id: str
    persona: str
    seed: int
    week: int = Field(ge=1)
    money: float | None
    stress: float | None
    valid: bool
    fallback_used: bool
    provider_error: bool
    ending: str
    source_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PublicAgentEval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[AGENT_EVAL_SCHEMA] = AGENT_EVAL_SCHEMA
    campaign_id: str
    cell_id: str
    persona: str
    seed: int
    ending: str
    weeks: int = Field(ge=0)
    min_money: float | None
    final_money: float | None
    max_stress: float | None
    cashflow_crisis_weeks: int = Field(ge=0)
    burnout_risk_weeks: int = Field(ge=0)
    valid_rate: float | None
    fallback_rate: float | None
    provider_error_rate: float | None
    persona_alignment_rate: float | None


class PublicPersonaCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[LLM_CALL_SCHEMA] = LLM_CALL_SCHEMA
    campaign_id: str
    cell_id: str
    persona: str
    seed: int
    week: int = Field(ge=1)
    phase: str
    status: str
    metadata: PersonaCallMetadata
    error: PersonaProviderError | None = None


class PublicFailureClusters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[CLUSTERS_SCHEMA] = CLUSTERS_SCHEMA
    campaign_id: str
    rules_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    clusters: tuple[FailureCluster, ...]


class BundleArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)
    records: int | None = Field(default=None, ge=0)


class BundleCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    status: Literal["passed", "failed"]
    detail: str


class CampaignBundleGate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[BUNDLE_GATE_SCHEMA] = BUNDLE_GATE_SCHEMA
    campaign_id: str
    status: Literal["passed", "failed"]
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifacts: tuple[BundleArtifact, ...]
    checks: tuple[BundleCheck, ...]


def build_public_campaign_bundle(
    *,
    project_root: str | Path,
    bundle_dir: str | Path,
    manifest: CampaignManifest,
    results: tuple[CampaignCellResult, ...] | list[CampaignCellResult],
    aggregation: CampaignAggregation,
) -> CampaignBundleGate:
    project = Path(project_root).resolve()
    destination = Path(bundle_dir)
    if not destination.is_absolute():
        destination = project / destination
    destination.mkdir(parents=True, exist_ok=True)
    checks = _preflight_checks(manifest, results, aggregation)
    if any(item.status == "failed" for item in checks):
        raise CampaignBundleError("campaign bundle preflight failed")

    metrics_by_cell = {item.cell_id: item for item in aggregation.cells}
    persona_runs, public_citations = _public_run_rows(project, results)
    agent_evals = []
    for result in results:
        metric = metrics_by_cell[result.request.cell_id]
        agent_evals.append(
            PublicAgentEval(
                campaign_id=manifest.request.campaign_id,
                cell_id=metric.cell_id,
                persona=metric.persona,
                seed=metric.seed,
                ending=metric.ending,
                weeks=metric.weeks,
                min_money=metric.min_money,
                final_money=metric.final_money,
                max_stress=metric.max_stress,
                cashflow_crisis_weeks=metric.cashflow_crisis_weeks,
                burnout_risk_weeks=metric.burnout_risk_weeks,
                valid_rate=metric.valid_rate,
                fallback_rate=metric.fallback_rate,
                provider_error_rate=metric.provider_error_rate,
                persona_alignment_rate=metric.persona_alignment_rate,
            )
        )
    calls = _public_calls(project, results)
    clusters = PublicFailureClusters(
        campaign_id=manifest.request.campaign_id,
        rules_fingerprint=aggregation.rules_fingerprint,
        clusters=tuple(
            _public_cluster(cluster, public_citations)
            for cluster in aggregation.clusters
        ),
    )

    files = {
        "campaign_manifest.json": manifest.model_dump(mode="json"),
        "campaign_summary.json": aggregation.model_dump(mode="json"),
        "failure_clusters.json": clusters.model_dump(mode="json"),
    }
    for name, payload in files.items():
        _write_json(destination / name, payload)
    _write_jsonl(destination / "persona_runs.jsonl", persona_runs)
    _write_jsonl(destination / "agent_eval.jsonl", agent_evals)
    _write_jsonl(destination / "llm_calls.jsonl", calls)

    _validate_written_files(destination)
    artifact_specs = [
        ("campaign_manifest.json", None),
        ("campaign_summary.json", None),
        ("persona_runs.jsonl", len(persona_runs)),
        ("agent_eval.jsonl", len(agent_evals)),
        ("llm_calls.jsonl", len(calls)),
        ("failure_clusters.json", None),
    ]
    artifacts = tuple(
        _artifact(destination / name, relative=name, records=records)
        for name, records in artifact_specs
    )
    safety_findings = _scan_forbidden(destination, [item[0] for item in artifact_specs])
    if safety_findings:
        raise CampaignBundleError(
            f"public bundle contains forbidden fields: {', '.join(safety_findings)}"
        )
    checks = (
        *checks,
        BundleCheck(id="schemas", status="passed", detail="all artifacts reparsed"),
        BundleCheck(id="hashes", status="passed", detail=f"{len(artifacts)} artifacts hashed"),
        BundleCheck(id="public_safety", status="passed", detail="no forbidden fields or secrets"),
    )
    gate = CampaignBundleGate(
        campaign_id=manifest.request.campaign_id,
        status="passed",
        request_fingerprint=manifest.request_fingerprint,
        source_fingerprint=manifest.source_fingerprint,
        artifacts=artifacts,
        checks=checks,
    )
    _write_json(destination / "gate_report.json", gate.model_dump(mode="json"))
    CampaignBundleGate.model_validate_json(
        (destination / "gate_report.json").read_text(encoding="utf-8")
    )
    return gate


def verify_public_campaign_bundle(bundle_dir: str | Path) -> CampaignBundleGate:
    root = Path(bundle_dir)
    try:
        gate = CampaignBundleGate.model_validate_json(
            (root / "gate_report.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise CampaignBundleError("bundle gate report is unavailable") from exc
    if gate.status != "passed" or any(item.status != "passed" for item in gate.checks):
        raise CampaignBundleError("bundle gate is not passed")
    for artifact in gate.artifacts:
        path = root / artifact.path
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact.sha256:
            raise CampaignBundleError(f"bundle artifact hash mismatch: {artifact.path}")
    _validate_written_files(root)
    findings = _scan_forbidden(root, [item.path for item in gate.artifacts])
    if findings:
        raise CampaignBundleError("bundle public-safety scan failed")
    return gate


def _preflight_checks(
    manifest: CampaignManifest,
    results: tuple[CampaignCellResult, ...] | list[CampaignCellResult],
    aggregation: CampaignAggregation,
) -> tuple[BundleCheck, ...]:
    expected = [cell.cell_id for cell in manifest.cells]
    observed = [result.request.cell_id for result in results]
    checks = [
        BundleCheck(
            id="expected_cells",
            status="passed" if observed == expected else "failed",
            detail=f"{len(observed)}/{len(expected)} ordered cells",
        ),
        BundleCheck(
            id="completed_cells",
            status=(
                "passed"
                if results and all(result.state.value == "completed" for result in results)
                else "failed"
            ),
            detail=f"{sum(result.state.value == 'completed' for result in results)}/{len(expected)} completed",
        ),
        BundleCheck(
            id="identity",
            status=(
                "passed"
                if aggregation.request_fingerprint == manifest.request_fingerprint
                and aggregation.source_fingerprint == manifest.source_fingerprint
                else "failed"
            ),
            detail="manifest and aggregation fingerprints",
        ),
    ]
    return tuple(checks)


def _public_calls(
    project: Path, results: tuple[CampaignCellResult, ...] | list[CampaignCellResult]
) -> list[PublicPersonaCall]:
    calls = []
    for result in results:
        path = project / result.request.output_dir / "playthrough.jsonl"
        rows = _read_jsonl(path)
        for week, row in enumerate(rows, start=1):
            raw_calls = row.get("persona_calls") if isinstance(row.get("persona_calls"), list) else []
            for raw in raw_calls:
                if not isinstance(raw, dict):
                    continue
                error = raw.get("error")
                if isinstance(error, dict) and isinstance(error.get("message"), str):
                    error = dict(error)
                    error["message"] = redact_sensitive_text(error["message"])
                calls.append(
                    PublicPersonaCall(
                        campaign_id=result.request.campaign_id,
                        cell_id=result.request.cell_id,
                        persona=result.request.persona.value,
                        seed=result.request.seed,
                        week=week,
                        phase=str(raw.get("phase") or "decision"),
                        status=str(raw.get("status") or "unknown"),
                        metadata=PersonaCallMetadata.model_validate(raw.get("metadata")),
                        error=PersonaProviderError.model_validate(error) if error else None,
                    )
                )
    return calls


def _public_run_rows(
    project: Path, results: tuple[CampaignCellResult, ...] | list[CampaignCellResult]
) -> tuple[list[PublicPersonaRun], dict[tuple[str, int], CampaignCitation]]:
    public_rows = []
    citations = {}
    line_number = 0
    for result in results:
        rows = _read_jsonl(project / result.request.output_dir / "playthrough.jsonl")
        source_by_week = {item.week: item for item in result.citations}
        for week, row in enumerate(rows, start=1):
            line_number += 1
            state = _public_state(row)
            validation = row.get("validation") if isinstance(row.get("validation"), dict) else {}
            calls = row.get("persona_calls") if isinstance(row.get("persona_calls"), list) else []
            result_payload = row.get("result") if isinstance(row.get("result"), dict) else {}
            public = PublicPersonaRun(
                campaign_id=result.request.campaign_id,
                cell_id=result.request.cell_id,
                persona=result.request.persona.value,
                seed=result.request.seed,
                week=week,
                money=_number(state.get("money")),
                stress=_number(state.get("stress")),
                valid=validation.get("valid") is True,
                fallback_used=validation.get("fallback_used") is True,
                provider_error=any(
                    isinstance(call, dict) and call.get("status") != "completed"
                    for call in calls
                ),
                ending=str(
                    result_payload.get("final_ending")
                    or result_payload.get("ending_id")
                    or state.get("ending_id")
                    or ""
                ),
                source_record_sha256=source_by_week[week].record_sha256,
            )
            public_rows.append(public)
            public_payload = public.model_dump(mode="json")
            citations[(result.request.cell_id, week)] = CampaignCitation(
                campaign_id=result.request.campaign_id,
                cell_id=result.request.cell_id,
                persona=result.request.persona,
                seed=result.request.seed,
                week=week,
                artifact_path="persona_runs.jsonl",
                line_number=line_number,
                record_sha256=canonical_sha256(public_payload),
            )
    return public_rows, citations


def _public_cluster(
    cluster: FailureCluster,
    citations: dict[tuple[str, int], CampaignCitation],
) -> FailureCluster:
    members = tuple(citations[(item.cell_id, item.week)] for item in cluster.members)
    representatives = tuple(
        citations[(item.cell_id, item.week)] for item in cluster.representatives
    )
    return cluster.model_copy(
        update={"members": members, "representatives": representatives}
    )


def _public_state(row: dict[str, Any]) -> dict[str, Any]:
    state = row.get("state_after")
    if isinstance(state, dict) and isinstance(state.get("state"), dict):
        return state["state"]
    if isinstance(state, dict):
        return state
    result = row.get("result")
    return result.get("state", {}) if isinstance(result, dict) else {}


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _validate_written_files(root: Path) -> None:
    CampaignManifest.model_validate_json((root / "campaign_manifest.json").read_text())
    CampaignAggregation.model_validate_json((root / "campaign_summary.json").read_text())
    PublicFailureClusters.model_validate_json((root / "failure_clusters.json").read_text())
    for row in _read_jsonl(root / "persona_runs.jsonl"):
        PublicPersonaRun.model_validate(row)
    for row in _read_jsonl(root / "agent_eval.jsonl"):
        PublicAgentEval.model_validate(row)
    for row in _read_jsonl(root / "llm_calls.jsonl"):
        PublicPersonaCall.model_validate(row)


def _scan_forbidden(root: Path, names: list[str]) -> list[str]:
    findings = []
    for name in names:
        text = (root / name).read_text(encoding="utf-8")
        lowered = text.lower()
        for key in FORBIDDEN_KEYS:
            if f'"{key}"' in lowered:
                findings.append(f"{name}:{key}")
        if "sk-proj-" in lowered or "authorization: bearer" in lowered:
            findings.append(f"{name}:secret_signature")
    return findings


def _artifact(path: Path, *, relative: str, records: int | None) -> BundleArtifact:
    content = path.read_bytes()
    return BundleArtifact(
        path=relative,
        sha256=hashlib.sha256(content).hexdigest(),
        bytes=len(content),
        records=records,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise CampaignBundleError(f"JSONL row is not an object: {path.name}")
            rows.append(payload)
    return rows


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[BaseModel]) -> None:
    path.write_text(
        "".join(
            json.dumps(row.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


__all__ = [
    "CampaignBundleError",
    "CampaignBundleGate",
    "build_public_campaign_bundle",
    "verify_public_campaign_bundle",
]
