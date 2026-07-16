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
    ):
        assert guardrail in skill


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
