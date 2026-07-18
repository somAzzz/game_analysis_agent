"""Transport-independent discovery and loading of Judge experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .campaign_aggregation import CampaignAggregation
from .campaign_bundle import PublicFailureClusters, verify_public_campaign_bundle
from .campaign_contract import CampaignManifest
from .repair_bundle import verify_public_repair_bundle
from .repair_experiment import RepairExperimentRecord, file_sha256

SIGNED_CAMPAIGN_ID = "build-week-2026-evidence-v1"
SIGNED_EXPERIMENT_ID = "cashflow-drift-repair-v1"
TARGET_CLUSTER_ID = "cashflow-stress-attractor"
PRIVATE_EXPERIMENT_IDS = frozenset(
    {
        "vllm-cohort-a-pressure-feedback-v1",
        "vllm-cohort-b-survival-recovery-v1",
    }
)
PRIVATE_CAMPAIGN_IDS = frozenset(
    {
        "vllm-audit-25seed-cohort-a",
        "vllm-audit-25seed-cohort-b",
    }
)


class ExperimentRegistryError(RuntimeError):
    """Raised when an experiment cannot be discovered or verified."""


class ExperimentSummary(BaseModel):
    """Small stable record used by the Judge experiment selector."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["judge-experiment-summary-v1"] = "judge-experiment-summary-v1"
    experiment_id: str
    title: str
    source_kind: Literal["signed", "local_vllm", "openai_api"]
    source_label: str
    provider: Literal["replay", "vllm", "openai"]
    provider_mode: str
    model: str
    lifecycle_status: Literal["campaign_complete", "proof_complete"]
    campaign_id: str
    campaign: dict[str, Any]
    campaign_bundle_path: str
    repair_bundle_path: str | None = None
    completed_at: str | None = None


class CommittedExperimentMetadata(BaseModel):
    """Small pointer record; all evidence fields are derived from verified bundles."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["judge-committed-experiment-v1"] = "judge-committed-experiment-v1"
    experiment_id: str
    title: str
    campaign_bundle_path: str
    repair_bundle_path: str


class ExperimentRegistry:
    """Discover committed and runtime experiments through one evidence model."""

    def __init__(self, project_root: str | Path) -> None:
        self.project = Path(project_root).resolve()

    def list(self) -> dict[str, object]:
        summaries = self._summaries()
        return {
            "schema_version": "judge-experiment-index-v1",
            "experiments": [item.model_dump(mode="json") for item in summaries],
        }

    def get(self, experiment_id: str) -> dict[str, object]:
        summary = next(
            (item for item in self._summaries() if item.experiment_id == experiment_id),
            None,
        )
        if summary is None:
            raise ExperimentRegistryError("experiment is not available")
        if summary.repair_bundle_path is None:
            return self._campaign_only(summary)
        if summary.repair_bundle_path.endswith("/accepted_experiment.json"):
            return self._correctness_proof(summary)
        return self._proof(summary)

    def _summaries(self) -> tuple[ExperimentSummary, ...]:
        summaries: list[ExperimentSummary] = [self._signed()]
        by_campaign = {SIGNED_CAMPAIGN_ID: summaries[0]}
        for summary in self._committed_experiments():
            by_campaign[summary.campaign_id] = summary
        for summary in self._committed_correctness_experiments():
            by_campaign[summary.campaign_id] = summary
        for summary in self._runtime_campaigns():
            by_campaign.setdefault(summary.campaign_id, summary)
        for summary in self._runtime_repairs(by_campaign):
            by_campaign[summary.campaign_id] = summary
        ordered = [by_campaign.pop(SIGNED_CAMPAIGN_ID)]
        ordered.extend(
            sorted(
                by_campaign.values(),
                key=lambda item: (item.completed_at or "", item.experiment_id),
                reverse=True,
            )
        )
        return tuple(
            item
            for item in ordered
            if item.experiment_id not in PRIVATE_EXPERIMENT_IDS
            and item.campaign_id not in PRIVATE_CAMPAIGN_IDS
        )

    def _signed(self) -> ExperimentSummary:
        campaign = self.project / "examples/build_week_2026/campaign-v1"
        repair = self.project / "examples/build_week_2026/experiment-v1"
        summary = self._campaign_summary(campaign)
        record = RepairExperimentRecord.model_validate_json(
            (repair / "repair_experiment.json").read_text(encoding="utf-8")
        )
        verify_public_repair_bundle(repair)
        return ExperimentSummary(
            experiment_id=SIGNED_EXPERIMENT_ID,
            title="Signed cashflow repair replay",
            source_kind="signed",
            source_label="SIGNED REPLAY",
            provider="replay",
            provider_mode="prerecorded",
            model="deterministic-persona-policy-fixture",
            lifecycle_status="proof_complete",
            campaign_id=SIGNED_CAMPAIGN_ID,
            campaign=summary,
            campaign_bundle_path=self._relative(campaign),
            repair_bundle_path=self._relative(repair),
            completed_at=record.completed_at.isoformat(),
        )

    def _committed_experiments(self) -> tuple[ExperimentSummary, ...]:
        root = self.project / "examples/build_week_2026/experiments"
        found = []
        for path in sorted(root.glob("*/metadata.json")):
            try:
                metadata = CommittedExperimentMetadata.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
                campaign = self._project_path(metadata.campaign_bundle_path)
                repair = self._project_path(metadata.repair_bundle_path)
                summary = self._summary_from_campaign(campaign)
                verify_public_repair_bundle(repair)
                record = RepairExperimentRecord.model_validate_json(
                    (repair / "repair_experiment.json").read_text(encoding="utf-8")
                )
                target = json.loads(self._project_path(record.plan.target_path).read_text())
                if record.plan.experiment_id != metadata.experiment_id:
                    raise ExperimentRegistryError("metadata experiment id differs from proof")
                if str(target["campaign_id"]) != summary.campaign_id:
                    raise ExperimentRegistryError("campaign differs from repair target")
            except (KeyError, OSError, ValueError, RuntimeError):
                continue
            found.append(
                summary.model_copy(
                    update={
                        "experiment_id": metadata.experiment_id,
                        "title": metadata.title,
                        "lifecycle_status": "proof_complete",
                        "repair_bundle_path": self._relative(repair),
                        "completed_at": record.completed_at.isoformat(),
                    }
                )
            )
        return tuple(found)

    def _committed_correctness_experiments(self) -> tuple[ExperimentSummary, ...]:
        root = self.project / "examples/build_week_2026/experiments"
        found = []
        for path in sorted(root.glob("*/accepted_experiment.json")):
            try:
                payload = self._load_correctness_experiment(path)
                found.append(
                    ExperimentSummary(
                        experiment_id=str(payload["experiment_id"]),
                        title=str(payload["title"]),
                        source_kind=str(payload["source_kind"]),
                        source_label=str(payload["source_label"]),
                        provider=str(payload["provider"]),
                        provider_mode=str(payload["provider_mode"]),
                        model=str(payload["model"]),
                        lifecycle_status=str(payload["lifecycle_status"]),
                        campaign_id=str(payload["campaign_id"]),
                        campaign=dict(payload["campaign"]),
                        campaign_bundle_path=str(payload["campaign_bundle_path"]),
                        repair_bundle_path=self._relative(path),
                        completed_at=str(payload["completed_at"]),
                    )
                )
            except (KeyError, OSError, TypeError, ValueError, RuntimeError):
                continue
        return tuple(found)

    def _correctness_proof(self, summary: ExperimentSummary) -> dict[str, object]:
        if summary.repair_bundle_path is None:
            raise ExperimentRegistryError("correctness proof path is missing")
        return self._load_correctness_experiment(self._project_path(summary.repair_bundle_path))

    def _load_correctness_experiment(self, path: Path) -> dict[str, object]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema_version") != "judge-public-experiment-v3"
            or payload.get("proof_kind") != "content_correctness"
            or payload.get("status") != "passed"
            or payload.get("decision") != "accepted"
            or payload.get("lifecycle_status") != "proof_complete"
        ):
            raise ExperimentRegistryError("invalid accepted correctness experiment")
        gates = payload.get("gates")
        if (
            not isinstance(gates, list)
            or not gates
            or any(not isinstance(item, dict) or item.get("status") != "passed" for item in gates)
        ):
            raise ExperimentRegistryError("correctness experiment has a failed gate")
        proof = payload.get("correctness_proof")
        if not isinstance(proof, dict):
            raise ExperimentRegistryError("correctness proof is missing")
        for artifact in proof.get("artifacts", []):
            artifact_path = self._project_path(str(artifact["path"]))
            if _sha256(artifact_path) != str(artifact["sha256"]):
                raise ExperimentRegistryError("correctness artifact hash mismatch")
        patch = payload.get("patch")
        if not isinstance(patch, dict):
            raise ExperimentRegistryError("correctness patch is missing")
        patch_path = self._project_path(str(patch["patch_path"]))
        if _sha256(patch_path) != str(patch["patch_sha256"]):
            raise ExperimentRegistryError("correctness patch hash mismatch")
        payload["patch"] = dict(patch) | {"diff": patch_path.read_text(encoding="utf-8")}
        payload["evidence_fingerprint"] = _sha256(path)
        return payload

    def _runtime_campaigns(self) -> tuple[ExperimentSummary, ...]:
        roots = [
            self.project / "reports/persona-campaigns",
            self.project / "reports/judge-bundles",
        ]
        found = []
        candidates: list[Path] = []
        for root in roots:
            candidates.extend(root.glob("*/public/gate_report.json"))
            candidates.extend(root.glob("*/gate_report.json"))
        for gate_path in sorted(set(candidates)):
            bundle = gate_path.parent
            try:
                found.append(self._summary_from_campaign(bundle))
            except (OSError, ValueError, RuntimeError):
                continue
        return tuple(found)

    def _runtime_repairs(
        self, campaigns: dict[str, ExperimentSummary]
    ) -> tuple[ExperimentSummary, ...]:
        found = []
        root = self.project / "reports/repair-experiments"
        for record_path in sorted(root.glob("*/public/repair_experiment.json")):
            bundle = record_path.parent
            try:
                verify_public_repair_bundle(bundle)
                record = RepairExperimentRecord.model_validate_json(
                    record_path.read_text(encoding="utf-8")
                )
                target = json.loads((self.project / record.plan.target_path).read_text())
                campaign_id = str(target["campaign_id"])
                campaign = campaigns[campaign_id]
            except (KeyError, OSError, ValueError, RuntimeError):
                continue
            found.append(
                campaign.model_copy(
                    update={
                        "experiment_id": record.plan.experiment_id,
                        "title": _experiment_title(campaign_id, record.plan.mechanism_class),
                        "lifecycle_status": "proof_complete",
                        "repair_bundle_path": self._relative(bundle),
                        "completed_at": record.completed_at.isoformat(),
                    }
                )
            )
        return tuple(found)

    def _summary_from_campaign(self, bundle: Path) -> ExperimentSummary:
        manifest = CampaignManifest.model_validate_json(
            (bundle / "campaign_manifest.json").read_text(encoding="utf-8")
        )
        source = manifest.source
        provider = str(source.provider.value)
        if provider not in {"vllm", "openai"}:
            raise ExperimentRegistryError("runtime registry accepts vllm or openai")
        source_kind = "local_vllm" if provider == "vllm" else "openai_api"
        label = "LOCAL vLLM" if provider == "vllm" else "OPENAI API"
        revision = str(source.provider_revision)
        model = revision.removeprefix("model:")
        return ExperimentSummary(
            experiment_id=manifest.request.campaign_id,
            title=_campaign_title(manifest.request.campaign_id),
            source_kind=source_kind,
            source_label=label,
            provider=provider,
            provider_mode=str(source.provider_mode),
            model=model,
            lifecycle_status="campaign_complete",
            campaign_id=manifest.request.campaign_id,
            campaign=self._campaign_summary(bundle),
            campaign_bundle_path=self._relative(bundle),
        )

    def _campaign_summary(self, bundle: Path) -> dict[str, Any]:
        gate = verify_public_campaign_bundle(bundle)
        manifest = CampaignManifest.model_validate_json(
            (bundle / "campaign_manifest.json").read_text(encoding="utf-8")
        )
        aggregation = CampaignAggregation.model_validate_json(
            (bundle / "campaign_summary.json").read_text(encoding="utf-8")
        )
        clusters = PublicFailureClusters.model_validate_json(
            (bundle / "failure_clusters.json").read_text(encoding="utf-8")
        )
        target = next(
            (item for item in clusters.clusters if item.cluster_id == TARGET_CLUSTER_ID),
            None,
        )
        metrics = aggregation.metrics
        return {
            "gate_status": gate.status,
            "personas": [item.value for item in manifest.request.personas],
            "seeds": list(manifest.request.seeds),
            "max_weeks": manifest.request.max_weeks,
            "cells": metrics.completed_cells,
            "weeks": metrics.total_weeks,
            "target_members": len(target.members) if target is not None else 0,
            "target_personas": (
                len({item.persona for item in target.members}) if target is not None else 0
            ),
            "valid_rate": metrics.valid_rate,
            "fallback_rate": metrics.fallback_rate,
            "provider_error_rate": metrics.provider_error_rate,
            "mean_final_money": metrics.mean_final_money,
            "mean_max_stress": metrics.mean_max_stress,
            "request_fingerprint": gate.request_fingerprint,
            "source_fingerprint": gate.source_fingerprint,
        }

    def _campaign_only(self, summary: ExperimentSummary) -> dict[str, object]:
        fingerprint = _sha256(self.project / summary.campaign_bundle_path / "gate_report.json")
        return {
            **summary.model_dump(mode="json"),
            "schema_version": "judge-public-experiment-v2",
            "evidence_fingerprint": fingerprint,
            "human_review": None,
            "status": "passed",
            "decision": None,
            "decision_reason": None,
            "hypothesis": None,
            "mechanism_class": None,
            "comparison": None,
            "cohorts": [],
            "gates": [],
            "patch": None,
            "codex": None,
            "mode": summary.provider_mode,
        }

    def _proof(self, summary: ExperimentSummary) -> dict[str, object]:
        bundle = self.project / str(summary.repair_bundle_path)
        gate = verify_public_repair_bundle(bundle)
        record_path = bundle / "repair_experiment.json"
        record = RepairExperimentRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
        return {
            **summary.model_dump(mode="json"),
            "schema_version": "judge-public-experiment-v2",
            "experiment_id": gate.experiment_id,
            "evidence_fingerprint": file_sha256(record_path),
            "status": gate.status,
            "decision": record.decision.value,
            "decision_reason": record.decision_reason,
            "hypothesis": record.plan.hypothesis,
            "mechanism_class": record.plan.mechanism_class,
            "comparison": record.comparison.model_dump(mode="json"),
            "cohorts": [item.model_dump(mode="json") for item in record.snapshots],
            "gates": [item.model_dump(mode="json") for item in record.gates],
            "patch": {
                **record.patch.model_dump(mode="json"),
                "canonical_source_path": "demo/study-in-germany",
                "disposition": "candidate_not_merged",
                "diff": (bundle / record.patch.patch_path).read_text(encoding="utf-8"),
            },
            "codex": record.codex.model_dump(mode="json"),
            "mode": summary.provider_mode,
        }

    def _project_path(self, relative: str) -> Path:
        path = (self.project / relative).resolve()
        try:
            path.relative_to(self.project)
        except ValueError as exc:
            raise ExperimentRegistryError("experiment path escapes project root") from exc
        return path

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.project).as_posix()


def _campaign_title(campaign_id: str) -> str:
    return campaign_id.replace("-", " ").title()


def _experiment_title(campaign_id: str, mechanism: str) -> str:
    cohort = "A" if "cohort-a" in campaign_id else "B" if "cohort-b" in campaign_id else ""
    suffix = f"Cohort {cohort}" if cohort else _campaign_title(campaign_id)
    return f"{suffix} · {mechanism.replace('_', ' ')}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "ExperimentRegistry",
    "ExperimentRegistryError",
    "ExperimentSummary",
    "SIGNED_EXPERIMENT_ID",
]
