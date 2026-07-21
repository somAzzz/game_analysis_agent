"""Fail-closed evaluator, UI, and platform evidence review for Build Week G4."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .platform_delivery import platform_contract_fingerprint

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


def _capture(
    checks: list[dict[str, Any]], identifier: str, operation: Callable[[], dict[str, Any]]
) -> None:
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
    delivery_claims = _delivery_claims(project)
    if delivery_claims["current_cross_platform"]:
        _capture(checks, "platform_delivery", lambda: _platform(project))
    else:
        checks.append(
            {
                "id": "platform_delivery",
                "status": "not_claimed",
                "evidence": {
                    "reason": delivery_claims["reason"],
                    "historical_evidence_retained": True,
                },
                "error": "",
            }
        )
    if delivery_claims["published_multiarch_image"]:
        _capture(checks, "published_multiarch_image", lambda: _image(project))
    else:
        checks.append(
            {
                "id": "published_multiarch_image",
                "status": "not_claimed",
                "evidence": {
                    "reason": delivery_claims["reason"],
                    "historical_metadata_retained": True,
                },
                "error": "",
            }
        )
    if execute_commands:
        _capture(
            checks,
            "offline_inspect",
            lambda: _command(
                project,
                ["./judge", "--mode", "inspect", "--offline", "--json", "--output-dir", "-"],
            ),
        )
        _capture(
            checks,
            "offline_replay",
            lambda: _command(
                project, ["./judge", "--mode", "replay", "--offline", "--json", "--output-dir", "-"]
            ),
        )
        _capture(checks, "frontend_tests", lambda: _command(project / "frontend", ["npm", "test"]))
        _capture(
            checks,
            "frontend_public_build",
            lambda: _command(project / "frontend", ["npm", "run", "build:public"]),
        )
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
            "Required evaluator and Judge submission evidence is complete."
            if not failures
            else "G4 failed closed; do not claim cross-platform Judge release readiness."
        ),
    }


def _delivery_claims(project: Path) -> dict[str, Any]:
    metadata = _read(project / "submission/build-week-2026/release-metadata.json")
    claims = metadata.get("delivery_claims") or {}
    cross_platform = claims.get("current_cross_platform")
    published_image = claims.get("published_multiarch_image")
    reason = str(claims.get("reason", "")).strip()
    if not isinstance(cross_platform, bool) or not isinstance(published_image, bool):
        raise G4ReviewError("release metadata must explicitly declare delivery claims")
    if (not cross_platform or not published_image) and not reason:
        raise G4ReviewError("unclaimed delivery capabilities require an explicit reason")
    return {
        "current_cross_platform": cross_platform,
        "published_multiarch_image": published_image,
        "reason": reason,
    }


def _restricted(project: Path) -> dict[str, Any]:
    review = _read(
        project / "docs/reviews/openai_build_week_2026/P4-restricted-environment.review.json"
    )
    scenarios = {item["id"]: item["status"] for item in review.get("scenarios", [])}
    required = {
        "system_python_inspect",
        "locked_offline_replay",
        "no_network_docker_gpu_secret_tty_browser_port",
        "repository_only_no_sibling_game",
        "stdout_only_read_only_output",
        "missing_corrupt_wrong_hash_and_claim",
        "unsupported_python",
        "timeout_cleanup",
        "signal_cleanup",
        "dependency_failure",
        "absent_api_key",
        "mid_run_provider_failure",
    }
    missing = sorted(item for item in required if scenarios.get(item) != "passed")
    if review.get("status") != "passed" or missing:
        raise G4ReviewError(f"restricted evaluator lacks passing scenarios: {missing}")
    return {"scenarios_passed": len(required), "reviewed_commit": review.get("reviewed_commit")}


def _ui(project: Path) -> dict[str, Any]:
    source = (project / "frontend/src/pages/JudgePage.tsx").read_text(encoding="utf-8")
    required = (
        "CAMPAIGN",
        "REPAIR",
        "PROOF",
        "OpenAI live subagent",
        "fixed",
        "holdout",
        "displayedDecision",
        "experiment.source_label",
        'role="status"',
    )
    missing = [token for token in required if token not in source]
    fixture = _read(project / "frontend/public-demo/judge-demo.json")
    if missing or fixture.get("decision") != "rejected" or len(fixture.get("cohorts", [])) != 4:
        raise G4ReviewError(f"Judge UI contract incomplete: {missing}")
    return {"required_labels": len(required), "cohorts": 4, "static_decision": "rejected"}


def _platform(project: Path) -> dict[str, Any]:
    review = _read(project / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json")
    expected_contract = platform_contract_fingerprint(project)
    if review.get("contract_sha256") != expected_contract:
        raise G4ReviewError("platform evidence is stale for the current delivery contract")
    rows = {item["id"]: item for item in review.get("checks", [])}
    by_id = {identifier: item.get("status") for identifier, item in rows.items()}
    absent = sorted(REQUIRED_PLATFORM_CHECKS - set(by_id))
    incomplete = {item for item in REQUIRED_PLATFORM_CHECKS if by_id.get(item) != "passed"}
    stale = {
        item
        for item in REQUIRED_PLATFORM_CHECKS
        if by_id.get(item) == "passed"
        and rows[item].get("source_contract_sha256") != expected_contract
    }
    incomplete.update(stale)
    if absent or incomplete or review.get("status") != "passed":
        raise G4ReviewError(
            f"platform evidence incomplete or stale: {sorted(incomplete) or absent}"
        )
    review_dir = project / "docs/reviews/openai_build_week_2026"
    for identifier in sorted(REQUIRED_PLATFORM_CHECKS):
        row = rows[identifier]
        evidence_name = row.get("evidence")
        if not isinstance(evidence_name, str) or not evidence_name:
            raise G4ReviewError(f"platform row lacks evidence path: {identifier}")
        evidence_path = (review_dir / evidence_name).resolve()
        try:
            evidence_path.relative_to(review_dir.resolve())
        except ValueError as exc:
            raise G4ReviewError(
                f"platform evidence escapes review directory: {identifier}"
            ) from exc
        evidence = _read(evidence_path)
        evidence_checks = {
            item.get("id"): item.get("status")
            for item in evidence.get("checks", [])
            if isinstance(item, dict)
        }
        if (
            evidence.get("schema_version") != "build-week-platform-evidence-v1"
            or evidence.get("status") != "passed"
            or evidence.get("source_contract_sha256") != expected_contract
            or evidence.get("source_contract_sha256") != row.get("source_contract_sha256")
            or evidence.get("source_revision") != row.get("source_revision")
            or evidence_checks.get(identifier) != "passed"
        ):
            raise G4ReviewError(f"platform evidence payload is invalid or stale: {identifier}")
    return {
        "platform_checks_passed": len(REQUIRED_PLATFORM_CHECKS),
        "contract_sha256": expected_contract,
    }


def _image(project: Path) -> dict[str, Any]:
    path = project / "judge-image-metadata.json"
    if not path.is_file():
        raise G4ReviewError("judge-image-metadata.json is missing; no image publication claim")
    value = _read(path)
    if value.get("status") != "built_and_pushed" or value.get("platforms") != [
        "linux/amd64",
        "linux/arm64",
    ]:
        raise G4ReviewError(
            "multi-architecture image metadata is not a published two-platform index"
        )
    digest = str(value.get("index_digest", ""))
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise G4ReviewError("published image index digest is invalid")
    contract = platform_contract_fingerprint(project)
    if value.get("source_contract_sha256") != contract:
        raise G4ReviewError("published image was not built from the current delivery contract")
    return {
        "reference": value.get("reference"),
        "index_digest": digest,
        "platforms": value["platforms"],
        "source_contract_sha256": contract,
    }


def _command(cwd: Path, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command, cwd=cwd, capture_output=True, check=False, text=True, timeout=180
    )
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


def write_g4_review(
    *, json_path: str | Path, markdown_path: str | Path, review: Mapping[str, Any]
) -> None:
    json_destination = Path(json_path)
    markdown_destination = Path(markdown_path)
    json_destination.parent.mkdir(parents=True, exist_ok=True)
    json_destination.write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# G4 Evaluator and Judge Experience Review",
        "",
        f"- Decision: **{review['status']}**",
        f"- Reviewed commit: `{review['reviewed_commit']}`",
        f"- Checks: {review['check_count']}",
        f"- Failures: {review['failure_count']}",
        "",
        "## Checks",
        "",
        "| Check | Status | Error |",
        "| --- | --- | --- |",
    ]
    for item in review["checks"]:
        lines.append(f"| {item['id']} | {item['status']} | {item['error']} |")
    lines.extend(["", "## Decision", "", str(review["decision"]), ""])
    markdown_destination.write_text("\n".join(lines), encoding="utf-8")
