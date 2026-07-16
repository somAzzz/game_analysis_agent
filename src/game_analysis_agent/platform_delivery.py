"""Stable source identity for Build Week platform-delivery evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

PLATFORM_CONTRACT_FILES = (
    ".github/workflows/test.yml",
    "Dockerfile.judge",
    "docker-compose.yml",
    "judge",
    "judge-manifest.json",
    "pyproject.toml",
    "uv.lock",
    "frontend/package-lock.json",
    "frontend/package.json",
    "scripts/godot-docker-wrapper",
    "scripts/setup-evaluator",
    "tools/build_judge_frontend_demo.py",
    "tools/build_judge_image.sh",
    "tools/judge_doctor.py",
    "tools/judge_replay.py",
    "tools/run_judge_api.py",
)

PLATFORM_CONTRACT_TREES = (
    "frontend/public-demo",
    "frontend/src",
)

PLATFORM_CONTRACT_SOURCE_NAMES = frozenset(
    {
        "build_week_campaign.py",
        "campaign_aggregation.py",
        "campaign_bundle.py",
        "campaign_contract.py",
        "campaign_runner.py",
        "judge_api.py",
        "local_persona_gateway.py",
        "openai_persona_gateway.py",
        "persona_gateway.py",
        "persona_gateway_factory.py",
        "persona_runtime.py",
        "recorded_persona_gateway.py",
        "repair_bundle.py",
        "repair_experiment.py",
        "repair_verification.py",
    }
)


def platform_contract_fingerprint(project_root: str | Path) -> str:
    """Hash only files that can change Judge/platform execution semantics."""

    root = Path(project_root).resolve()
    candidates = [root / item for item in PLATFORM_CONTRACT_FILES]
    for directory in PLATFORM_CONTRACT_TREES:
        base = root / directory
        if base.is_dir():
            candidates.extend(path for path in base.rglob("*") if path.is_file())
    package = root / "src/game_analysis_agent"
    candidates.extend(package / name for name in PLATFORM_CONTRACT_SOURCE_NAMES)

    digest = hashlib.sha256()
    included = 0
    for path in sorted(set(candidates)):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo", ".orig"}:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        included += 1
    return digest.hexdigest() if included else ""


__all__ = ["platform_contract_fingerprint"]
