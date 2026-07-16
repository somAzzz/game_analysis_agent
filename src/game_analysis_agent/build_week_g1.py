"""Fail-closed provider correctness and security review for Build Week G1."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .recorded_persona_gateway import MANIFEST_SCHEMA, RecordedPersonaGateway

G1_SCHEMA = "build-week-g1-review-v1"
TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = {
    "openai_key": re.compile(
        r"(?<![A-Za-z0-9_-])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"
    ),
    "bearer_token": re.compile(
        r"(?i)authorization\s*[:=]\s*bearer\s+[A-Za-z0-9._-]{20,}"
    ),
    "assigned_api_key": re.compile(
        r"(?im)^(?:OPENAI_API_KEY|DEEPSEEK_API_KEY)\s*=\s*[^\s#]{16,}$"
    ),
}


class G1ReviewError(RuntimeError):
    """Raised when G1 evidence cannot be evaluated safely."""


def review_g1(
    *,
    project_root: str | Path,
    game_root: str | Path,
    baseline_dir: str | Path,
    diff_base: str,
    execute_commands: bool = True,
    live_smoke: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    project = Path(project_root).resolve()
    game = Path(game_root).resolve()
    baseline = Path(baseline_dir).resolve()
    env = dict(os.environ if environ is None else environ)
    env.update(_contract_environment(game, baseline))
    checks: list[dict[str, Any]] = []

    _capture(checks, "replay_fixture_hash", lambda: _replay_evidence(project))
    _capture(checks, "browser_key_boundary", lambda: _browser_boundary(project))
    _capture(checks, "provider_failure_truthfulness", lambda: _source_boundary(project))

    if execute_commands:
        npm = env.get("BUILD_WEEK_NPM_BIN", "npm")
        commands = [
            (
                "provider_unit_tests",
                [
                    "uv",
                    "run",
                    "pytest",
                    "-q",
                    "tests/test_persona_gateway.py",
                    "tests/test_recorded_persona_gateway.py",
                    "tests/test_openai_persona_gateway.py",
                    "tests/test_persona_runtime.py",
                    "tests/test_interactive_persona_gateway.py",
                ],
            ),
            ("ruff", ["uv", "run", "ruff", "check", "."],),
            ("full_pytest", ["uv", "run", "pytest", "-q", "-ra"]),
            (
                "frontend_public_build",
                [npm, "--prefix", "frontend", "run", "build:public"],
            ),
        ]
        for check_id, command in commands:
            _capture(
                checks,
                check_id,
                lambda command=command: _command_evidence(command, project, env),
            )

    _capture(
        checks,
        "secret_scan",
        lambda: _secret_evidence(project, diff_base=diff_base, checks=checks),
    )
    if live_smoke:
        _capture(
            checks,
            "openai_live_smoke",
            lambda: _live_smoke_evidence(env),
        )
    else:
        checks.append(
            {
                "id": "openai_live_smoke",
                "status": "not_run",
                "evidence": {
                    "reason": "no restricted submission key supplied for this review"
                },
                "error": "",
            }
        )

    failures = [item for item in checks if item["status"] == "failed"]
    return {
        "schema_version": G1_SCHEMA,
        "gate": "G1",
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "reviewed_diff": f"{diff_base}..HEAD",
        "checks": checks,
        "check_count": len(checks),
        "not_run_count": sum(item["status"] == "not_run" for item in checks),
        "failure_count": len(failures),
        "failures": [item["id"] for item in failures],
    }


def write_g1_review(path: str | Path, review: Mapping[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def scan_secret_text(text: str, *, location: str) -> list[dict[str, str]]:
    """Return secret signatures without copying the matched value."""

    findings = []
    for pattern_id, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append(
                {
                    "location": location,
                    "pattern": pattern_id,
                    "line": str(text.count("\n", 0, match.start()) + 1),
                }
            )
    return findings


def _capture(checks: list[dict[str, Any]], check_id: str, operation) -> None:
    try:
        evidence = operation()
    except Exception as exc:
        checks.append(
            {
                "id": check_id,
                "status": "failed",
                "evidence": {},
                "error": _sanitize_error(exc),
            }
        )
        return
    checks.append(
        {"id": check_id, "status": "passed", "evidence": evidence, "error": ""}
    )


def _replay_evidence(project: Path) -> dict[str, Any]:
    manifest_path = project / "config/build_week_2026_replay.json"
    manifest = _required_json(manifest_path)
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise G1ReviewError("Replay manifest schema is invalid")
    fixture_path = project / str(manifest.get("fixture", ""))
    expected = str(manifest.get("sha256", ""))
    actual = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    if actual != expected:
        raise G1ReviewError("Replay fixture hash does not match manifest")
    gateway = RecordedPersonaGateway.from_manifest(manifest_path, project_root=project)
    return {
        "manifest": manifest_path.relative_to(project).as_posix(),
        "fixture": fixture_path.relative_to(project).as_posix(),
        "sha256": actual,
        "provider": gateway.provider.value,
        "mode": gateway.mode.value,
    }


def _browser_boundary(project: Path) -> dict[str, Any]:
    frontend = project / "frontend"
    forbidden = ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "sk-proj-")
    findings = []
    checked = 0
    for path in _text_files(frontend, excluded={"node_modules", "dist", "coverage"}):
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(token in text for token in forbidden):
            findings.append(path.relative_to(project).as_posix())
    if findings:
        raise G1ReviewError(f"browser source references server secret fields: {findings}")
    return {"files_checked": checked, "forbidden_secret_references": 0}


def _source_boundary(project: Path) -> dict[str, Any]:
    factory = (project / "src/game_analysis_agent/persona_gateway_factory.py").read_text(
        encoding="utf-8"
    )
    runtime = (project / "src/game_analysis_agent/persona_runtime.py").read_text(
        encoding="utf-8"
    )
    player = (
        project / "src/game_analysis_agent/agents/interactive_player.py"
    ).read_text(encoding="utf-8")
    required = {
        "single_factory_selection": "selection = settings.resolve_provider()" in factory,
        "no_factory_fallback_branch": "except" not in factory,
        "typed_budget_failure": "BUDGET_EXHAUSTED" in runtime,
        "typed_cancelled_failure": "PersonaResultStatus.CANCELLED" in runtime,
        "player_gateway_seam": "self.persona_gateway.decide(request)" in player,
        "player_failure_record": '"error": result.error.model_dump' in player,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise G1ReviewError(f"provider boundary invariant missing: {missing}")
    return required


def _secret_evidence(
    project: Path, *, diff_base: str, checks: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    findings = []
    diff = subprocess.run(
        ["git", "diff", "--no-ext-diff", f"{diff_base}..HEAD"],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if diff.returncode != 0:
        raise G1ReviewError("could not read reviewed Git diff")
    findings.extend(scan_secret_text(diff.stdout, location="git-diff"))

    roots = [project / "reports/build-week-2026", project / "frontend/dist"]
    file_count = 0
    for root in roots:
        if not root.exists():
            continue
        for path in _text_files(root, excluded={"game-source"}):
            file_count += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            findings.extend(
                scan_secret_text(text, location=path.relative_to(project).as_posix())
            )
    command_text = json.dumps(list(checks), ensure_ascii=False)
    findings.extend(scan_secret_text(command_text, location="review-command-output"))
    if findings:
        locations = sorted({item["location"] for item in findings})
        raise G1ReviewError(f"secret signature found in {locations}")
    return {
        "reviewed_diff": f"{diff_base}..HEAD",
        "artifact_files_checked": file_count,
        "command_outputs_checked": len(checks),
        "secret_findings": 0,
    }


def _live_smoke_evidence(env: Mapping[str, str]) -> dict[str, Any]:
    # This path is explicit (--live-smoke), performs exactly one request, and
    # never prints or serializes the key or returned decision text.
    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise G1ReviewError("--live-smoke requires OPENAI_API_KEY")
    from openai import OpenAI

    from .schemas import PlayerDecision

    model = env.get("OPENAI_PERSONA_MODEL", "gpt-5.6-luna")
    client = OpenAI(api_key=api_key, timeout=30, max_retries=0)
    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": "Return the requested game persona decision schema only.",
            },
            {
                "role": "user",
                "content": (
                    "For persona smoke_test in week 1, choose action rest_at_home. "
                    "Use a concise goal and tradeoff, confidence 0.5."
                ),
            },
        ],
        text_format=PlayerDecision,
        max_output_tokens=300,
        store=False,
    )
    if getattr(response, "output_parsed", None) is None:
        raise G1ReviewError("OpenAI live smoke returned no parsed decision")
    usage = getattr(response, "usage", None)
    return {
        "response_id": str(getattr(response, "id", "")),
        "model": str(getattr(response, "model", model)),
        "total_tokens": getattr(usage, "total_tokens", None),
        "structured_output": "parsed",
        "request_count": 1,
    }


def _command_evidence(
    command: Sequence[str], project: Path, env: Mapping[str, str]
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=project,
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise G1ReviewError(f"review command unavailable: {exc.__class__.__name__}") from exc
    stdout = _sanitize_output(completed.stdout[-3000:], project)
    stderr = _sanitize_output(completed.stderr[-3000:], project)
    if completed.returncode != 0:
        raise G1ReviewError(
            f"command exited {completed.returncode}: {(stderr or stdout).strip()[:500]}"
        )
    return {
        "command": [Path(command[0]).name, *command[1:]],
        "returncode": completed.returncode,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
    }


def _text_files(root: Path, *, excluded: set[str]) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not excluded.intersection(path.relative_to(root).parts)
        and (path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith(".env"))
    ]


def _contract_environment(game: Path, baseline: Path) -> dict[str, str]:
    return {
        "GAME_PROJECT_PATH": str(game),
        "GAME_CONTRACT_TRACE": str(baseline / "raw_runs.jsonl"),
        "GAME_CONTRACT_EVENT_GRAPH": str(baseline / "event_graph.json"),
        "GAME_CONTRACT_ACTION_CATALOG": str(baseline / "action_catalog.json"),
        "GAME_CONTRACT_VALIDATOR": str(baseline / "content_validation.json"),
    }


def _sanitize_output(value: str, project: Path) -> str:
    return value.replace(str(project), "<project>").replace(str(Path.home()), "<home>")


def _sanitize_error(exc: Exception) -> str:
    text = str(exc)
    for pattern in SECRET_PATTERNS.values():
        text = pattern.sub("<redacted>", text)
    return text[:500]


def _required_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise G1ReviewError(f"required JSON unavailable: {path.name}") from exc
    if not isinstance(payload, dict):
        raise G1ReviewError(f"required JSON is not an object: {path.name}")
    return payload


__all__ = [
    "G1ReviewError",
    "review_g1",
    "scan_secret_text",
    "write_g1_review",
]
