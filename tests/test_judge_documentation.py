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


def test_codex_skill_is_auto_discoverable_and_has_a_direct_read_fallback() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "judge-manifest.json").read_text(encoding="utf-8"))
    skill = manifest["codex_skill"]

    assert skill["path"] == ".agents/skills/playtest-forge/SKILL.md"
    assert skill["discovery_root"] == ".agents/skills"
    assert skill["explicit_invocation"] == "$playtest-forge"
    assert "Read .agents/skills/playtest-forge/SKILL.md directly" in skill["fallback"]
    for content in (agents, readme):
        assert "$playtest-forge" in content
        assert ".agents/skills/playtest-forge/SKILL.md" in content
        assert "direct" in content.lower()
    skill_artifacts = {
        item["path"] for item in manifest["artifacts"] if item["role"].startswith("codex-skill")
    }
    assert len(skill_artifacts) == 17
