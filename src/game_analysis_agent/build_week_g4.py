"""Fail-closed evaluator, UI, and platform evidence review for Build Week G4."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

G4_SCHEMA = "build-week-g4-review-v1"
REQUIRED_PLATFORM_CHECKS = frozenset(
    {
        "macos_system_python_inspect",
        "macos_locked_replay",
        "macos_idempotent_setup",
        "macos_native_ui_api",
        "macos_pinned_real_godot",
        "live_openai_campaign",
        "linux_amd64_native_and_container",
        "linux_pinned_real_godot",
        "linux_arm64_container",
    }
)


class G4ReviewError(RuntimeError):
    """Raised when release evidence is absent, stale, or incomplete."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise G4ReviewError(f"{path.name} must contain a JSON object")
    return value


def _capture(checks: list[dict[str, Any]], identifier: str, operation: Callable[[], dict[str, Any]]) -> None:
    try:
        evidence = operation()
        checks.append({"id": identifier, "status": "passed", "evidence": evidence, "error": ""})
    except (G4ReviewError, OSError, ValueError, subprocess.SubprocessError) as exc:
        checks.append({"id": identifier, "status": "failed", "evidence": {}, "error": str(exc)})


def review_g4(*, project_root: str | Path, execute_commands: bool = True) -> dict[str, Any]:
    project = Path(project_root).resolve()
    checks: list[dict[str, Any]] = []
    _capture(checks, "restricted_evaluator", lambda: _restricted(project))
    _capture(checks, "human_judge_ui", lambda: _ui(project))
    _capture(checks, "platform_delivery", lambda: _platform(project))
    _capture(checks, "published_multiarch_image", lambda: _image(project))
    if execute_commands:
        _capture(checks, "offline_inspect", lambda: _command(project, ["./judge", "--mode", "inspect", "--offline", "--json", "--output-dir", "-"]))
        _capture(checks, "offline_replay", lambda: _command(project, ["./judge", "--mode", "replay", "--offline", "--json", "--output-dir", "-"]))
        _capture(checks, "frontend_tests", lambda: _command(project / "frontend", ["npm", "test"]))
        _capture(checks, "frontend_public_build", lambda: _command(project / "frontend", ["npm", "run", "build:public"]))
    failures = [item for item in checks if item["status"] == "failed"]
    return {
        "schema_version": G4_SCHEMA,
        "gate": "G4",
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "reviewed_commit": _git_revision(project),
        "checks": checks,
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": [item["id"] for item in failures],
        "decision": (
            "Evaluator and Judge delivery evidence is complete."
            if not failures
            else "G4 failed closed; do not claim cross-platform Judge release readiness."
        ),
    }


def _restricted(project: Path) -> dict[str, Any]:
    review = _read(project / "docs/reviews/openai_build_week_2026/P4-restricted-environment.review.json")
    scenarios = {item["id"]: item["status"] for item in review.get("scenarios", [])}
    required = {
        "system_python_inspect", "locked_offline_replay",
        "no_network_docker_gpu_secret_tty_browser_port", "repository_only_no_sibling_game",
        "stdout_only_read_only_output", "missing_corrupt_wrong_hash_and_claim",
        "unsupported_python", "timeout_cleanup", "signal_cleanup", "dependency_failure",
        "absent_api_key", "mid_run_provider_failure",
    }
    missing = sorted(item for item in required if scenarios.get(item) != "passed")
    if review.get("status") != "passed" or missing:
        raise G4ReviewError(f"restricted evaluator lacks passing scenarios: {missing}")
    return {"scenarios_passed": len(required), "reviewed_commit": review.get("reviewed_commit")}


def _ui(project: Path) -> dict[str, Any]:
    source = (project / "frontend/src/pages/JudgePage.tsx").read_text(encoding="utf-8")
    required = (
        "CAMPAIGN", "REPAIR", "PROOF", "prerecorded evidence", "OpenAI live subagent",
        "fixed", "holdout", "REJECTED", 'role="status"',
    )
    missing = [token for token in required if token not in source]
    fixture = _read(project / "frontend/public-demo/judge-demo.json")
    if missing or fixture.get("decision") != "rejected" or len(fixture.get("cohorts", [])) != 4:
        raise G4ReviewError(f"Judge UI contract incomplete: {missing}")
    return {"required_labels": len(required), "cohorts": 4, "static_decision": "rejected"}


def _platform(project: Path) -> dict[str, Any]:
    review = _read(project / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json")
    by_id = {item["id"]: item["status"] for item in review.get("checks", [])}
    absent = sorted(REQUIRED_PLATFORM_CHECKS - set(by_id))
    incomplete = sorted(item for item in REQUIRED_PLATFORM_CHECKS if by_id.get(item) != "passed")
    if absent or incomplete or review.get("status") != "passed":
        raise G4ReviewError(f"platform evidence incomplete: {incomplete or absent}")
    return {"platform_checks_passed": len(REQUIRED_PLATFORM_CHECKS)}


def _image(project: Path) -> dict[str, Any]:
    path = project / "judge-image-metadata.json"
    if not path.is_file():
        raise G4ReviewError("judge-image-metadata.json is missing; no image publication claim")
    value = _read(path)
    if value.get("status") != "built_and_pushed" or value.get("platforms") != ["linux/amd64", "linux/arm64"]:
        raise G4ReviewError("multi-architecture image metadata is not a published two-platform index")
    digest = str(value.get("index_digest", ""))
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise G4ReviewError("published image index digest is invalid")
    return {"reference": value.get("reference"), "index_digest": digest, "platforms": value["platforms"]}


def _command(cwd: Path, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, check=False, text=True, timeout=180)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout)[-1200:]
        raise G4ReviewError(f"command failed ({completed.returncode}): {' '.join(command)}: {tail}")
    output = completed.stdout.strip()
    if command[0] == "./judge":
        payload = json.loads(output)
        if payload.get("status") != "passed":
            raise G4ReviewError(f"Judge command did not pass: {payload.get('status')}")
    return {"command": command, "exit_code": 0, "tail": output[-1200:]}


def _git_revision(project: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project,
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def write_g4_review(*, json_path: str | Path, markdown_path: str | Path, review: Mapping[str, Any]) -> None:
    json_destination = Path(json_path)
    markdown_destination = Path(markdown_path)
    json_destination.parent.mkdir(parents=True, exist_ok=True)
    json_destination.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# G4 Evaluator and Judge Experience Review", "",
        f"- Decision: **{review['status']}**", f"- Reviewed commit: `{review['reviewed_commit']}`",
        f"- Checks: {review['check_count']}", f"- Failures: {review['failure_count']}", "",
        "## Checks", "", "| Check | Status | Error |", "| --- | --- | --- |",
    ]
    for item in review["checks"]:
        lines.append(f"| {item['id']} | {item['status']} | {item['error']} |")
    lines.extend(["", "## Decision", "", str(review["decision"]), ""])
    markdown_destination.write_text("\n".join(lines), encoding="utf-8")
