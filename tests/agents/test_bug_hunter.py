from __future__ import annotations

import json
from pathlib import Path

from game_analysis_agent.agents.bug_hunter import BugHunterAgent


def test_bug_hunter_recomputes_stale_anomalies_from_raw_trace(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw_runs.jsonl"
    anomalies_path = tmp_path / "anomalies.jsonl"
    raw_path.write_text(
        json.dumps(
            {
                "run_id": 1,
                "policy": "balanced",
                "max_weeks": 1,
                "final_ending_id": "stable_start",
                "final_state": {"week": 1, "money": 100},
                "weekly_log": [
                    {
                        "week": 1,
                        "selected_action_ids": ["rest"],
                        "before_state": {"week": 0, "money": 100},
                        "after_state": {"week": 1, "money": 100},
                        "action_effects": [],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    anomalies_path.write_text(
        json.dumps(
            {
                "kind": "negative_money",
                "severity": "critical",
                "run_id": 1,
                "week": 1,
                "policy": "balanced",
                "evidence": {"money": -1},
                "message": "stale",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    agent = BugHunterAgent(llm=object(), prompts_root=tmp_path)  # type: ignore[arg-type]

    anomalies = agent._ensure_anomalies(raw_path, anomalies_path)

    assert not [item for item in anomalies if item.kind == "negative_money"]
    assert "stale" not in anomalies_path.read_text(encoding="utf-8")
