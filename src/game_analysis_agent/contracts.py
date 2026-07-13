"""Versioned contracts for artifacts exchanged with the Godot game project.

The game currently emits plain JSON without an embedded schema identifier.  The
consumer therefore selects a contract revision explicitly; new producers may
also include ``contract_version`` and it will be checked against that revision.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

CONTRACT_VERSION = "1.0"
SUPPORTED_CONTRACT_VERSIONS = frozenset({CONTRACT_VERSION})

CORE_STATE_FIELDS = frozenset(
    {
        "week",
        "money",
        "energy",
        "stress",
        "loneliness",
        "academic_progress",
        "language",
        "social",
        "visa_progress",
        "career_progress",
    }
)


class ContractKind(str, Enum):
    """Stable names used by tests, CI, and the command-line validator."""

    TRACE = "trace"
    BOUNDARY_TRACE = "boundary_trace"
    ACTION_CATALOG = "action_catalog"
    EVENT_GRAPH = "event_graph"
    VALIDATOR_REPORT = "validator_report"
    INTERACTIVE_PROBE = "interactive_probe"


class ContractValidationError(ValueError):
    """Raised when an artifact does not satisfy the selected contract."""


class ContractModel(BaseModel):
    """Forward-compatible base for cross-repository documents."""

    model_config = ConfigDict(extra="allow")

    contract_version: str | None = None


def _require_state_fields(state: Mapping[str, Any], *, location: str) -> None:
    missing = sorted(CORE_STATE_FIELDS.difference(state))
    if missing:
        raise ValueError(f"{location} is missing core state fields: {', '.join(missing)}")


class WeeklyTrace(ContractModel):
    """One deterministic simulator week in a batch trace."""

    week: int
    available_action_ids: list[str]
    selected_action_ids: list[str]
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    triggered_event_id: str
    event_choice_id: str
    event_effects: dict[str, float]
    event_success: bool | None

    @model_validator(mode="after")
    def _validate_states(self) -> WeeklyTrace:
        _require_state_fields(self.before_state, location="weekly_log.before_state")
        _require_state_fields(self.after_state, location="weekly_log.after_state")
        return self


class RunTrace(ContractModel):
    """One complete run emitted by ``RunSimulation.gd``."""

    run_id: int = Field(ge=0)
    seed: int
    policy: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    scenario: str
    content_version: str = Field(min_length=1)
    rules_version: str = Field(min_length=1)
    max_weeks: int = Field(gt=0)
    final_ending_id: str
    final_state: dict[str, Any]
    weekly_log: list[WeeklyTrace] = Field(min_length=1)
    action_sequence: list[dict[str, Any]] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_final_state(self) -> RunTrace:
        _require_state_fields(self.final_state, location="final_state")
        return self


class BoundaryTrace(ContractModel):
    """One extreme-state run emitted by ``RunBoundaryProbe.gd``."""

    run_id: int = Field(ge=0)
    seed: int
    policy: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    extreme: str = Field(min_length=1)
    max_weeks: int = Field(gt=0)
    final_ending_id: str = Field(min_length=1)
    final_state: dict[str, Any]
    weekly_log: list[WeeklyTrace] = Field(min_length=1)
    action_sequence: list[dict[str, Any]] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_final_state(self) -> BoundaryTrace:
        _require_state_fields(self.final_state, location="final_state")
        return self


class ActionRecord(ContractModel):
    """One action exposed to policies and interactive agents."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str
    cost_energy: float
    cost_money: float
    cost_slots: int = Field(gt=0)
    effects: dict[str, float]
    requirements: dict[str, Any]
    tags: list[str]
    risk_tags: list[str]
    set_flag: str
    cooldown_group: str
    max_per_week: int = Field(ge=0)


class ActionCatalog(ContractModel):
    """Action export produced next to ``event_graph.json``."""

    actions: list[ActionRecord] = Field(min_length=1)
    action_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_action_index(self) -> ActionCatalog:
        if self.action_count != len(self.actions):
            raise ValueError("action_count does not match actions length")
        ids = [action.id for action in self.actions]
        if len(ids) != len(set(ids)):
            raise ValueError("action ids must be unique")
        return self


class EventChoiceRecord(ContractModel):
    """One choice in an exported event."""

    text: str = Field(min_length=1)
    success_rate: float = Field(ge=0.0, le=1.0)
    success_effects: dict[str, float]
    failure_effects: dict[str, float]
    success_modifiers: dict[str, float]
    requirements: dict[str, Any]
    set_flag: str
    next_event_id: str


class EventRecord(ContractModel):
    """One event in the exported decision graph."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str
    event_type: str = Field(min_length=1)
    trigger: dict[str, Any]
    weight: float = Field(ge=0.0)
    repeatable: bool
    choices: list[EventChoiceRecord] = Field(min_length=1)
    choice_count: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_choice_count(self) -> EventRecord:
        if self.choice_count != len(self.choices):
            raise ValueError("choice_count does not match choices length")
        return self


class EventGraph(ContractModel):
    """Event graph export consumed by graph and content-QA agents."""

    events: list[EventRecord] = Field(min_length=1)
    event_count: int = Field(ge=0)
    action_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_event_index(self) -> EventGraph:
        if self.event_count != len(self.events):
            raise ValueError("event_count does not match events length")
        ids = [event.id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("event ids must be unique")
        return self


class ValidatorReport(ContractModel):
    """Common envelope used by all Godot validator reports."""

    errors: list[Any]
    summary: dict[str, Any]
    warnings: list[Any] | None = None

    @field_validator("errors", "warnings")
    @classmethod
    def _validate_findings(cls, value: list[Any] | None) -> list[Any] | None:
        for finding in value or []:
            if not isinstance(finding, (dict, str)):
                raise ValueError("validator findings must be objects or strings")
            if isinstance(finding, str) and not finding.strip():
                raise ValueError("validator finding strings must not be empty")
        return value


class ProbeRiskRecord(ContractModel):
    """One UI risk returned by the game's canonical ``RiskEvaluator``."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    score: int = Field(gt=0, le=100, strict=True)
    body: str = Field(min_length=1)
    suggested_actions: list[str] = Field(min_length=1)

    @field_validator("suggested_actions")
    @classmethod
    def _validate_suggested_actions(cls, value: list[str]) -> list[str]:
        if any(not action.strip() for action in value):
            raise ValueError("suggested action ids must not be empty")
        if len(value) != len(set(value)):
            raise ValueError("suggested action ids must be unique")
        return value


class ProbeRiskGuidance(ContractModel):
    """Versioned risk envelope carried by the interactive probe trace."""

    contract_version: Literal["1.0"]
    source: Literal["game_risk_evaluator"]
    evaluator: Literal["RiskEvaluator.get_top_risks"]
    generated_for_week: int = Field(ge=0, strict=True)
    top_risks: list[ProbeRiskRecord] = Field(max_length=3)

    @model_validator(mode="after")
    def _validate_unique_risks(self) -> ProbeRiskGuidance:
        ids = [risk.id for risk in self.top_risks]
        if len(ids) != len(set(ids)):
            raise ValueError("probe risk ids must be unique")
        return self


class InteractiveProbeTrace(ContractModel):
    """Snapshot returned by ``RunInteractiveProbe.gd``.

    ``risk_guidance`` remains optional for backward compatibility with an
    older game checkout. When present, its producer and payload are strict;
    consumers can distinguish canonical UI guidance from a local fallback.
    """

    finished: bool
    final_week: int = Field(ge=0, strict=True)
    triggered_event_id: str
    event_choices: list[dict[str, Any]]
    final_ending_id: str
    final_state: dict[str, Any]
    current_state: dict[str, Any] | None = None
    state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    risk_guidance: ProbeRiskGuidance | None = None

    @model_validator(mode="after")
    def _validate_snapshot_and_risk_week(self) -> InteractiveProbeTrace:
        snapshots = (self.current_state, self.state, self.after_state)
        if all(snapshot is None for snapshot in snapshots):
            raise ValueError("interactive probe must expose a current state snapshot")
        snapshot = next(snapshot for snapshot in snapshots if snapshot is not None)
        if self.risk_guidance is not None and "week" in snapshot:
            try:
                snapshot_week = int(snapshot["week"])
            except (TypeError, ValueError) as exc:
                raise ValueError("interactive probe state week must be an integer") from exc
            if self.risk_guidance.generated_for_week != snapshot_week:
                raise ValueError("risk guidance week does not match the current state snapshot")
        return self


ContractArtifact = (
    RunTrace
    | BoundaryTrace
    | ActionCatalog
    | EventGraph
    | ValidatorReport
    | InteractiveProbeTrace
)

_MODELS: dict[ContractKind, type[ContractModel]] = {
    ContractKind.TRACE: RunTrace,
    ContractKind.BOUNDARY_TRACE: BoundaryTrace,
    ContractKind.ACTION_CATALOG: ActionCatalog,
    ContractKind.EVENT_GRAPH: EventGraph,
    ContractKind.VALIDATOR_REPORT: ValidatorReport,
    ContractKind.INTERACTIVE_PROBE: InteractiveProbeTrace,
}


def validate_contract(
    payload: Mapping[str, Any],
    *,
    kind: ContractKind | str,
    version: str = CONTRACT_VERSION,
    require_clean: bool = False,
) -> ContractArtifact:
    """Validate one decoded artifact against a named contract revision."""

    try:
        contract_kind = ContractKind(kind)
    except ValueError as exc:
        raise ContractValidationError(f"unknown contract kind: {kind}") from exc
    if version not in SUPPORTED_CONTRACT_VERSIONS:
        raise ContractValidationError(f"unsupported contract version: {version}")
    embedded_version = payload.get("contract_version")
    if embedded_version is not None and embedded_version != version:
        raise ContractValidationError(
            f"embedded contract_version {embedded_version!r} does not match {version!r}"
        )

    try:
        artifact = _MODELS[contract_kind].model_validate(dict(payload))
    except ValidationError as exc:
        raise ContractValidationError(
            f"{contract_kind.value} contract {version} validation failed: {exc}"
        ) from exc

    if require_clean and isinstance(artifact, ValidatorReport) and artifact.errors:
        raise ContractValidationError(f"validator report contains {len(artifact.errors)} error(s)")
    return artifact


def validate_contract_file(
    path: str | Path,
    *,
    kind: ContractKind | str,
    version: str = CONTRACT_VERSION,
    require_clean: bool = False,
) -> ContractArtifact | list[ContractArtifact]:
    """Load and validate a JSON artifact or every row in a JSONL artifact."""

    artifact_path = Path(path)
    if artifact_path.suffix == ".jsonl":
        validated: list[ContractArtifact] = []
        with artifact_path.open(encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise ContractValidationError(
                        f"{artifact_path}:{line_number}: invalid JSON: {exc.msg}"
                    ) from exc
                try:
                    validated.append(
                        validate_contract(
                            payload,
                            kind=kind,
                            version=version,
                            require_clean=require_clean,
                        )
                    )
                except ContractValidationError as exc:
                    raise ContractValidationError(f"{artifact_path}:{line_number}: {exc}") from exc
        if not validated:
            raise ContractValidationError(f"{artifact_path}: JSONL artifact is empty")
        return validated

    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractValidationError(f"{artifact_path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ContractValidationError(f"{artifact_path}: top-level JSON value must be an object")
    return validate_contract(
        payload,
        kind=kind,
        version=version,
        require_clean=require_clean,
    )


def validate_trace_catalog_consistency(
    trace_path: str | Path,
    event_graph_path: str | Path,
    action_catalog_path: str | Path,
) -> dict[str, int]:
    """Require every observed batch-trace ID to exist in fresh catalogs."""

    traces = validate_contract_file(trace_path, kind=ContractKind.TRACE)
    graph = validate_contract_file(event_graph_path, kind=ContractKind.EVENT_GRAPH)
    catalog = validate_contract_file(action_catalog_path, kind=ContractKind.ACTION_CATALOG)
    trace_rows = traces if isinstance(traces, list) else [traces]
    if not isinstance(graph, EventGraph) or not isinstance(catalog, ActionCatalog):
        raise ContractValidationError("unexpected catalog contract type")

    action_ids = {action.id for action in catalog.actions}
    event_choices = {
        event.id: {
            f"{event.id}.choice_{index:02d}_{choice.text.lower().replace(' ', '_')}"
            for index, choice in enumerate(event.choices, start=1)
        }
        for event in graph.events
    }
    unknown_actions: set[str] = set()
    unknown_events: set[str] = set()
    unknown_choices: set[str] = set()
    observed_actions: set[str] = set()
    observed_events: set[str] = set()
    observed_choices: set[str] = set()
    for trace in trace_rows:
        if not isinstance(trace, RunTrace):
            raise ContractValidationError("trace artifact did not validate as RunTrace")
        for week in trace.weekly_log:
            for action_id in [*week.available_action_ids, *week.selected_action_ids]:
                observed_actions.add(action_id)
                if action_id not in action_ids:
                    unknown_actions.add(action_id)
            if week.triggered_event_id:
                observed_events.add(week.triggered_event_id)
                if week.triggered_event_id not in event_choices:
                    unknown_events.add(week.triggered_event_id)
            if week.event_choice_id:
                observed_choices.add(week.event_choice_id)
                if week.event_choice_id not in event_choices.get(
                    week.triggered_event_id, set()
                ):
                    unknown_choices.add(week.event_choice_id)

    problems = []
    if unknown_actions:
        problems.append(f"unknown action ids: {sorted(unknown_actions)}")
    if unknown_events:
        problems.append(f"unknown event ids: {sorted(unknown_events)}")
    if unknown_choices:
        problems.append(f"unknown choice ids: {sorted(unknown_choices)}")
    if problems:
        raise ContractValidationError("trace/catalog consistency failed: " + "; ".join(problems))
    return {
        "traces": len(trace_rows),
        "observed_actions": len(observed_actions),
        "observed_events": len(observed_events),
        "observed_choices": len(observed_choices),
    }


def main(argv: list[str] | None = None) -> int:
    """Validate a game artifact from CI or a developer shell."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=[kind.value for kind in ContractKind])
    parser.add_argument("path", type=Path)
    parser.add_argument("--version", default=CONTRACT_VERSION)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args(argv)
    artifacts = validate_contract_file(
        args.path,
        kind=args.kind,
        version=args.version,
        require_clean=args.require_clean,
    )
    count = len(artifacts) if isinstance(artifacts, list) else 1
    print(f"validated {count} {args.kind} artifact(s) against contract {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
