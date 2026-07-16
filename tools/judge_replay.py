#!/usr/bin/env python3
"""Locked-dependency worker for the repository-only Judge Replay smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.build_week_g2 import (  # noqa: E402
    recompute_public_clusters,
    recompute_public_evidence,
)
from game_analysis_agent.campaign_bundle import verify_public_campaign_bundle  # noqa: E402
from game_analysis_agent.persona_gateway import (  # noqa: E402
    PersonaDecisionRequest,
    PersonaEventChoiceRequest,
    PersonaResultStatus,
)
from game_analysis_agent.recorded_persona_gateway import (  # noqa: E402
    RecordedPersonaGateway,
)
from game_analysis_agent.repair_bundle import verify_public_repair_bundle  # noqa: E402
from game_analysis_agent.repair_experiment import (  # noqa: E402
    GateStatus,
    RepairExperimentRecord,
)
from game_analysis_agent.schemas import WeekContext  # noqa: E402


def _context() -> WeekContext:
    return WeekContext.model_validate(
        {
            "game_version": "test",
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "persona": "newbie",
            "state": {"week": 1, "money": 420, "stress": 55},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
                "contract_version": "1.0",
            },
            "available_actions": [
                {"id": "budget_call", "name": "Budget call"},
                {"id": "rest_at_home", "name": "Rest"},
            ],
            "current_event_id": "rent_pressure",
            "event_choices": [
                {"choice_id": "rent_pressure.pay_now", "text": "Pay now"},
                {"choice_id": "rent_pressure.ask_extension", "text": "Ask extension"},
            ],
            "memory": {"persona": "newbie"},
        }
    )


def run(project: Path) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    campaign = project / "examples/build_week_2026/campaign-v1"
    experiment = project / "examples/build_week_2026/experiment-v1"
    campaign_gate = verify_public_campaign_bundle(campaign)
    repair_gate = verify_public_repair_bundle(experiment)
    checks.append(
        {
            "id": "bundle_integrity",
            "status": "passed",
            "detail": f"campaign={campaign_gate.status}, repair={repair_gate.status}",
        }
    )

    gateway = RecordedPersonaGateway.from_manifest(
        project / "config/build_week_2026_replay.json", project_root=project
    )
    context = _context()
    decision = gateway.decide(
        PersonaDecisionRequest.from_context(context, request_id="newbie-42-w1-decision")
    )
    event = gateway.choose_event(
        PersonaEventChoiceRequest.from_context(
            context,
            request_id="newbie-42-w1-event",
            selected_actions=["budget_call"],
        )
    )
    if (
        decision.status != PersonaResultStatus.COMPLETED
        or decision.decision is None
        or decision.decision.actions != ["budget_call"]
        or event.status != PersonaResultStatus.COMPLETED
        or event.choice is None
        or event.choice.event_choice_id != "rent_pressure.ask_extension"
    ):
        raise RuntimeError("exact Replay decision/event smoke differs from fixture")
    checks.append(
        {
            "id": "exact_replay",
            "status": "passed",
            "detail": "newbie week-1 decision and event matched exact fingerprints",
        }
    )

    full_manifest = json.loads(
        (project / "config/build_week_2026_full_replay.json").read_text(encoding="utf-8")
    )
    full_fixture = project / full_manifest["fixture"]
    RecordedPersonaGateway(full_fixture, expected_sha256=full_manifest["sha256"])
    entries = json.loads(full_fixture.read_text(encoding="utf-8"))["entries"]
    if len(entries) != 684:
        raise RuntimeError("full Replay fixture no longer contains 684 calls")
    checks.append(
        {
            "id": "full_fixture",
            "status": "passed",
            "detail": "684 unique decision/event entries parsed from the hash-pinned fixture",
        }
    )

    metrics = recompute_public_evidence(campaign)
    clusters = recompute_public_clusters(campaign)
    personas = {
        json.loads(line)["persona"]
        for line in (campaign / "persona_runs.jsonl").read_text(encoding="utf-8").splitlines()
    }
    if (
        personas != {"newbie", "study", "money", "social", "visa", "slacker"}
        or metrics["valid_rate"] != 1.0
        or metrics["fallback_rate"] != 0.0
        or clusters["cluster_counts"]["cashflow-stress-attractor"] != 18
    ):
        raise RuntimeError("representative persona or deterministic campaign gates failed")
    checks.append(
        {
            "id": "persona_and_determinism",
            "status": "passed",
            "detail": "six personas, 1.0 valid rate, zero fallback, 18 target members",
        }
    )

    record = RepairExperimentRecord.model_validate_json(
        (experiment / "repair_experiment.json").read_text(encoding="utf-8")
    )
    designed_failure = next(
        item for item in record.gates if item.gate_id == "designed_failure_preserved"
    )
    if designed_failure.status != GateStatus.PASSED or record.decision.value != "rejected":
        raise RuntimeError("designed-failure or rejected-repair gate failed")
    checks.append(
        {
            "id": "designed_failure_and_rejection",
            "status": "passed",
            "detail": "designed failure preserved and ineffective candidate remains rejected",
        }
    )
    return {
        "schema_version": "judge-replay-worker-v1",
        "status": "passed",
        "checks": checks,
        "artifacts": [
            {
                "path": "config/build_week_2026_full_replay.json",
                "sha256": hashlib.sha256(
                    (project / "config/build_week_2026_full_replay.json").read_bytes()
                ).hexdigest(),
            },
            {
                "path": full_manifest["fixture"],
                "sha256": full_manifest["sha256"],
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = run(args.project_root.resolve())
    except Exception as exc:  # noqa: BLE001 - worker returns one typed failure protocol
        result = {
            "schema_version": "judge-replay-worker-v1",
            "status": "failed",
            "checks": [],
            "artifacts": [],
            "error_code": "replay_evidence_failed",
            "error": str(exc),
            "remediation": "Restore locked dependencies and committed fixtures, then retry.",
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
