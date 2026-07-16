"""Repository Skill structure, guardrail, and wrapper tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/playtest-forge"


def test_skill_has_required_resources_without_placeholders() -> None:
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "references/design-contract.md",
        "references/evidence-contract.md",
        "references/repair-protocol.md",
        "references/test-strategy.md",
        "references/automated-testing.md",
        "references/subagent-playthrough.md",
        "references/evidence-to-parameters.md",
        "references/scenario-balance-economy.md",
        "references/scenario-content-flow.md",
        "references/scenario-boundary-robustness.md",
        "references/migration-guide.md",
        "references/session-case-study.md",
        "scripts/preflight",
        "scripts/run-campaign",
        "scripts/verify-repair",
    ]
    for relative in required:
        path = SKILL / relative
        assert path.is_file(), relative
        assert "TODO" not in path.read_text(encoding="utf-8")
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for guardrail in (
        "one falsifiable hypothesis",
        "isolated game worktree",
        "fixed seeds",
        "unseen holdouts",
        "accepted",
        "rejected",
        "Do not build an MCP adapter",
        "deterministic baseline",
        "persona/subagent playthroughs",
        "parameter",
        "State which results came from",
    ):
        assert guardrail in skill
    assert len(skill.splitlines()) < 500


def test_skill_routes_scenarios_and_keeps_project_details_in_a_profile() -> None:
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    profile = (SKILL / "references/design-contract.md").read_text(encoding="utf-8")
    migration = (SKILL / "references/migration-guide.md").read_text(encoding="utf-8")

    for route in (
        "automated-testing.md",
        "subagent-playthrough.md",
        "scenario-balance-economy.md",
        "scenario-content-flow.md",
        "scenario-boundary-robustness.md",
        "migration-guide.md",
    ):
        assert route in skill
    assert "current Build Week integration" in profile
    assert "Godot scripts, Unity tests, Unreal commandlets" in migration


def test_skill_scripts_are_executable_and_preflight_passes() -> None:
    for name in ("preflight", "run-campaign", "verify-repair"):
        assert os.access(SKILL / "scripts" / name, os.X_OK)
    completed = subprocess.run(
        [str(SKILL / "scripts/preflight"), "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert '"status": "passed"' in completed.stdout
