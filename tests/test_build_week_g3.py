"""Independent committed-evidence recomputation tests for G3."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from game_analysis_agent.build_week_g3 import review_g3

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "examples/build_week_2026/experiment-v1"
CAMPAIGN = ROOT / "examples/build_week_2026/campaign-v1"
TARGET = ROOT / "config/build_week_2026_target.json"
DESIGN = ROOT / "config/build_week_2026_design_contract.json"


def _review(experiment: Path) -> dict[str, object]:
    return review_g3(
        project_root=ROOT,
        experiment_bundle=experiment,
        campaign_bundle=CAMPAIGN,
        target_path=TARGET,
        design_contract_path=DESIGN,
        execute_commands=False,
    )


def test_committed_rejected_repair_passes_complete_g3_review() -> None:
    review = _review(EXPERIMENT)

    assert review["status"] == "passed"
    assert review["experiment_decision"] == "rejected"
    assert review["check_count"] == 6
    assert review["independent_findings"]["holdout_direction"] == (
        "not_confirmed_and_rejected"
    )


def test_g3_fails_when_codex_session_is_a_placeholder(tmp_path: Path) -> None:
    destination = tmp_path / "experiment"
    shutil.copytree(EXPERIMENT, destination)
    path = destination / "repair_experiment.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["codex"]["feedback_session_id"] = "pending-user-feedback"
    path.write_text(json.dumps(payload), encoding="utf-8")
    gate = destination / "gate_report.json"
    gate_payload = json.loads(gate.read_text(encoding="utf-8"))
    for artifact in gate_payload["artifacts"]:
        if artifact["path"] == "repair_experiment.json":
            artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            artifact["bytes"] = path.stat().st_size
    gate.write_text(json.dumps(gate_payload), encoding="utf-8")

    review = _review(destination)

    assert review["status"] == "failed"
    assert "codex_centrality" in review["failures"]
