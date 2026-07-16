"""AI discoverability and capability-label checks for Judge Mode docs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSPECT = "./judge --mode inspect --offline --json --output-dir -"
REPLAY = "./judge --mode replay --offline --json --output-dir -"


def test_primary_commands_are_consistent_and_early_in_entry_docs() -> None:
    manifest = json.loads((ROOT / "judge-manifest.json").read_text(encoding="utf-8"))
    assert manifest["primary_commands"] == {"inspect": INSPECT, "replay": REPLAY}

    for relative in ("AGENTS.md", "README.md", "README.zh-CN.md", "JUDGE.md"):
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert INSPECT in content[:2500], relative
        assert REPLAY in content[:2500], relative


def test_judge_guide_distinguishes_every_evaluator_state() -> None:
    guide = (ROOT / "JUDGE.md").read_text(encoding="utf-8")

    for label in ("Prerecorded", "Live", "Unsupported", "Failed"):
        assert f"| {label} |" in guide
    assert "does not call OpenAI" in guide
    assert "not merged" in guide
