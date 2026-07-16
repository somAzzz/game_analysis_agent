"""Pre-patch design-intent lock tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent.design_contract import (
    DesignContractError,
    DesignIntentContract,
    load_design_contract,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/build_week_2026_design_contract.json"


def test_committed_design_contract_verifies_all_approval_sources() -> None:
    contract = load_design_contract(CONTRACT, project_root=ROOT)

    assert contract.approved_before_patch is True
    assert contract.selected_target.cluster_id == "cashflow-stress-attractor"
    assert contract.selected_target.baseline_fixed_members == 18
    assert contract.selected_target.acceptance_max_fixed_members == 12
    assert contract.persona_intent["slacker"] == "failure_seeking"
    assert contract.protected_metrics.slacker_success_required is False
    assert len(contract.fingerprint()) == 64


def test_design_contract_rejects_stale_approval_source(tmp_path: Path) -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    project = tmp_path / "project"
    project.mkdir()
    contract_path = project / "contract.json"
    contract_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DesignContractError, match="approval source changed"):
        load_design_contract(contract_path, project_root=project)


def test_design_contract_rejects_threshold_that_does_not_improve() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    payload["selected_target"]["acceptance_max_fixed_members"] = 18

    with pytest.raises(ValueError, match="must require improvement"):
        DesignIntentContract.model_validate(payload)
