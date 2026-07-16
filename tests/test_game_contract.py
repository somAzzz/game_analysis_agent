"""Contract tests for artifacts exchanged with ``study-in-germany``."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from game_analysis_agent.contracts import (
    CONTRACT_VERSION,
    ActionCatalog,
    BoundaryTrace,
    ContractKind,
    ContractValidationError,
    EventGraph,
    InteractiveProbeTrace,
    RunTrace,
    ValidatorReport,
    validate_contract,
    validate_contract_file,
    validate_trace_catalog_consistency,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"


@pytest.mark.parametrize(
    ("filename", "kind", "expected_type"),
    [
        ("trace_v1.json", ContractKind.TRACE, RunTrace),
        ("action_catalog_v1.json", ContractKind.ACTION_CATALOG, ActionCatalog),
        ("event_graph_v1.json", ContractKind.EVENT_GRAPH, EventGraph),
        ("validator_report_v1.json", ContractKind.VALIDATOR_REPORT, ValidatorReport),
        ("interactive_probe_v1.json", ContractKind.INTERACTIVE_PROBE, InteractiveProbeTrace),
    ],
)
def test_versioned_contract_fixtures(
    filename: str,
    kind: ContractKind,
    expected_type: type,
) -> None:
    artifact = validate_contract_file(FIXTURES / filename, kind=kind)
    assert isinstance(artifact, expected_type)


def test_contract_rejects_mismatched_embedded_version() -> None:
    payload = json.loads((FIXTURES / "action_catalog_v1.json").read_text(encoding="utf-8"))
    payload["contract_version"] = "2.0"

    with pytest.raises(ContractValidationError, match="does not match"):
        validate_contract(payload, kind=ContractKind.ACTION_CATALOG)


def test_contract_rejects_wrong_declared_count() -> None:
    payload = json.loads((FIXTURES / "event_graph_v1.json").read_text(encoding="utf-8"))
    payload["event_count"] = 2

    with pytest.raises(ContractValidationError, match="event_count"):
        validate_contract(payload, kind=ContractKind.EVENT_GRAPH)


def _interactive_probe_payload() -> dict:
    return json.loads((FIXTURES / "interactive_probe_v1.json").read_text(encoding="utf-8"))


def test_probe_contract_rejects_stale_risk_guidance() -> None:
    payload = _interactive_probe_payload()
    payload["risk_guidance"]["generated_for_week"] = 1

    with pytest.raises(ContractValidationError, match="risk guidance week"):
        validate_contract(payload, kind=ContractKind.INTERACTIVE_PROBE)


def test_probe_contract_rejects_noncanonical_or_coerced_risk_data() -> None:
    payload = _interactive_probe_payload()
    payload["risk_guidance"]["source"] = "python_fallback"

    with pytest.raises(ContractValidationError, match="game_risk_evaluator"):
        validate_contract(payload, kind=ContractKind.INTERACTIVE_PROBE)

    payload = _interactive_probe_payload()
    payload["risk_guidance"]["top_risks"][0]["score"] = "78"
    with pytest.raises(ContractValidationError, match="valid integer"):
        validate_contract(payload, kind=ContractKind.INTERACTIVE_PROBE)

    payload = _interactive_probe_payload()
    payload["risk_guidance"].pop("contract_version")
    with pytest.raises(ContractValidationError, match="Field required"):
        validate_contract(payload, kind=ContractKind.INTERACTIVE_PROBE)


def test_probe_helper_mirror_emits_versioned_game_risk_guidance() -> None:
    helper = (ROOT / "scripts" / "tools" / "RunInteractiveProbe.gd").read_text(encoding="utf-8")
    assert 'preload("res://scripts/simulation/RiskEvaluator.gd")' in helper
    assert '"source": "game_risk_evaluator"' in helper
    assert '"evaluator": "RiskEvaluator.get_top_risks"' in helper
    assert "RiskEvaluatorScript.get_top_risks(game_state, 3)" in helper


def test_clean_validator_gate_is_fail_closed() -> None:
    payload = json.loads((FIXTURES / "validator_report_v1.json").read_text(encoding="utf-8"))
    payload["errors"] = [{"type": "duplicate_id", "id": "event-a"}]

    with pytest.raises(ContractValidationError, match="contains 1 error"):
        validate_contract(
            payload,
            kind=ContractKind.VALIDATOR_REPORT,
            require_clean=True,
        )


def test_jsonl_error_reports_line_number(tmp_path: Path) -> None:
    trace = json.loads((FIXTURES / "trace_v1.json").read_text(encoding="utf-8"))
    trace_path = tmp_path / "raw_runs.jsonl"
    trace_path.write_text(f"{json.dumps(trace)}\n{{not-json}}\n", encoding="utf-8")

    with pytest.raises(ContractValidationError, match=r"raw_runs\.jsonl:2"):
        validate_contract_file(trace_path, kind=ContractKind.TRACE)


def test_boundary_trace_contract_accepts_current_game_shape() -> None:
    trace = json.loads((FIXTURES / "trace_v1.json").read_text(encoding="utf-8"))
    for key in ("scenario", "content_version", "rules_version"):
        trace.pop(key)
    trace["extreme"] = "zero_money"

    artifact = validate_contract(trace, kind=ContractKind.BOUNDARY_TRACE)

    assert isinstance(artifact, BoundaryTrace)


def test_trace_catalog_consistency_rejects_unknown_action(tmp_path: Path) -> None:
    trace = json.loads((FIXTURES / "trace_v1.json").read_text(encoding="utf-8"))
    graph = json.loads((FIXTURES / "event_graph_v1.json").read_text(encoding="utf-8"))
    catalog = json.loads((FIXTURES / "action_catalog_v1.json").read_text(encoding="utf-8"))
    trace["weekly_log"][0]["available_action_ids"] = [catalog["actions"][0]["id"]]
    trace["weekly_log"][0]["selected_action_ids"] = ["ghost_action"]
    event = graph["events"][0]
    choice = event["choices"][0]
    trace["weekly_log"][0]["triggered_event_id"] = event["id"]
    trace["weekly_log"][0]["event_choice_id"] = (
        f"{event['id']}.choice_01_{choice['text'].lower().replace(' ', '_')}"
    )
    trace_path = tmp_path / "raw_runs.jsonl"
    graph_path = tmp_path / "event_graph.json"
    catalog_path = tmp_path / "action_catalog.json"
    trace_path.write_text(json.dumps(trace) + "\n", encoding="utf-8")
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    with pytest.raises(ContractValidationError, match="ghost_action"):
        validate_trace_catalog_consistency(trace_path, graph_path, catalog_path)


def _game_project() -> Path:
    configured = os.getenv("GAME_PROJECT_PATH")
    if not configured:
        pytest.skip("set GAME_PROJECT_PATH explicitly for the real-game contract smoke")
    game_project = Path(configured)
    if not game_project.exists():
        pytest.skip(
            "study-in-germany checkout is unavailable; set GAME_PROJECT_PATH for contract smoke"
        )
    assert (game_project / "project.godot").is_file(), (
        f"GAME_PROJECT_PATH is not a Godot project: {game_project}"
    )
    return game_project


def _required_artifact(game_project: Path, env_name: str, relative_path: str) -> Path:
    configured = os.getenv(env_name)
    artifact = Path(configured) if configured else game_project / relative_path
    assert artifact.is_file(), f"required game contract artifact is missing: {artifact}"
    return artifact


@pytest.mark.game_contract
def test_study_in_germany_artifacts_match_contract() -> None:
    """Smoke-test real exports only when their game runtime is explicitly configured."""

    game_project = _game_project()
    reports = game_project / "reports"
    configured_trace = os.getenv("GAME_CONTRACT_TRACE")
    if configured_trace:
        trace_path = Path(configured_trace)
    else:
        candidates = sorted(reports.glob("*_runs.jsonl"))
        assert candidates, f"no simulation trace found under {reports}"
        trace_path = candidates[0]

    event_graph = _required_artifact(
        game_project,
        "GAME_CONTRACT_EVENT_GRAPH",
        "reports/event_graph.json",
    )
    action_catalog = _required_artifact(
        game_project,
        "GAME_CONTRACT_ACTION_CATALOG",
        "reports/action_catalog.json",
    )
    configured_validator = os.getenv("GAME_CONTRACT_VALIDATOR")
    if configured_validator:
        validator_paths = [Path(configured_validator)]
    else:
        validator_paths = sorted(reports.glob("*_validation.json"))
        assert validator_paths, f"no validator reports found under {reports}"

    validate_contract_file(trace_path, kind=ContractKind.TRACE, version=CONTRACT_VERSION)
    validate_contract_file(
        event_graph,
        kind=ContractKind.EVENT_GRAPH,
        version=CONTRACT_VERSION,
    )
    validate_contract_file(
        action_catalog,
        kind=ContractKind.ACTION_CATALOG,
        version=CONTRACT_VERSION,
    )
    for validator_path in validator_paths:
        validate_contract_file(
            validator_path,
            kind=ContractKind.VALIDATOR_REPORT,
            version=CONTRACT_VERSION,
            require_clean=True,
        )
    if configured_trace:
        validate_trace_catalog_consistency(trace_path, event_graph, action_catalog)
    configured_interactive_probe = os.getenv("GAME_CONTRACT_INTERACTIVE_PROBE")
    if configured_interactive_probe:
        interactive = validate_contract_file(
            Path(configured_interactive_probe),
            kind=ContractKind.INTERACTIVE_PROBE,
            version=CONTRACT_VERSION,
        )
        assert isinstance(interactive, InteractiveProbeTrace)
        assert interactive.risk_guidance is not None
        assert interactive.risk_guidance.source == "game_risk_evaluator"
