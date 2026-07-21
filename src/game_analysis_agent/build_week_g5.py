"""Fail-closed final submission review for OpenAI Build Week 2026."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

G5_SCHEMA = "build-week-g5-review-v1"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HTTPS_PATTERN = re.compile(r"^https://[^\s{}]+$")
SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:sk-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,})(?![A-Za-z0-9_-])"
)


class G5ReviewError(RuntimeError):
    """Raised when final release evidence is absent or incomplete."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise G5ReviewError(f"invalid or missing JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise G5ReviewError(f"{path.name} must contain a JSON object")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise G5ReviewError(message)


def _capture(
    checks: list[dict[str, Any]],
    identifier: str,
    operation: Callable[[], dict[str, Any]],
) -> None:
    try:
        evidence = operation()
        checks.append({"id": identifier, "status": "passed", "evidence": evidence, "error": ""})
    except (G5ReviewError, OSError, ValueError, subprocess.SubprocessError) as exc:
        checks.append({"id": identifier, "status": "failed", "evidence": {}, "error": str(exc)})


def review_g5(*, project_root: str | Path) -> dict[str, Any]:
    project = Path(project_root).resolve()
    checks: list[dict[str, Any]] = []
    _capture(checks, "prior_gates", lambda: _prior_gates(project))
    _capture(checks, "claim_ledger", lambda: _claim_ledger(project))
    _capture(checks, "release_metadata", lambda: _release_metadata(project))
    _capture(checks, "manual_comparison", lambda: _manual_comparison(project))
    _capture(checks, "clean_room_review", lambda: _clean_room(project))
    _capture(checks, "video_review", lambda: _video(project))
    _capture(checks, "published_image", lambda: _published_image(project))
    _capture(checks, "license_privacy_secrets", lambda: _security(project))
    failures = [item["id"] for item in checks if item["status"] == "failed"]
    return {
        "schema_version": G5_SCHEMA,
        "gate": "G5",
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "reviewed_commit": _git_revision(project),
        "checks": checks,
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": failures,
        "decision": (
            "Submission evidence is complete and eligible for maintainer authorization."
            if not failures
            else "G5 failed closed; do not submit or publish final release claims."
        ),
    }


def _prior_gates(project: Path) -> dict[str, Any]:
    for name in ("G0-baseline.md", "G1-providers.md"):
        head = (project / "docs/reviews" / name).read_text(encoding="utf-8")[:500]
        _require(re.search(r"(?m)^status:\s*passed\s*$", head) is not None, f"{name} is not passed")
    statuses: dict[str, str] = {"G0": "passed", "G1": "passed"}
    for gate in ("G2-campaign", "G3-repair", "G4-evaluator"):
        value = _read(project / f"docs/reviews/openai_build_week_2026/{gate}.review.json")
        gate_id = gate.split("-", 1)[0]
        statuses[gate_id] = str(value.get("status"))
        _require(value.get("gate") == gate_id and value.get("status") == "passed", f"{gate_id} is not passed")
    return {"statuses": statuses}


def _claim_ledger(project: Path) -> dict[str, Any]:
    value = _read(project / "submission/build-week-2026/claim-ledger.json")
    _require(value.get("status") == "release_ready", "claim ledger is not release_ready")
    claims = value.get("claims") or []
    pending = value.get("pending_external_claims") or []
    _require(claims and all(item.get("status") == "verified" for item in claims), "claim ledger has unverified claims")
    drafts = {
        "devpost": (project / "submission/build-week-2026/DEVPOST_DRAFT.md").read_text(encoding="utf-8"),
        "video": (project / "submission/build-week-2026/VIDEO_SCRIPT.md").read_text(encoding="utf-8"),
    }
    normalized = {name: re.sub(r"\s+", " ", text) for name, text in drafts.items()}
    for claim in claims:
        approved = re.sub(r"\s+", " ", str(claim.get("approved_text", "")))
        for usage in claim.get("used_in") or []:
            _require(approved in normalized[str(usage)], f"claim text missing from {usage}: {claim.get('id')}")
        for evidence in claim.get("evidence") or []:
            source = _read(project / str(evidence["path"]))
            actual = _pointer(source, str(evidence["json_pointer"]))
            _require(actual == evidence["equals"], f"claim evidence mismatch: {claim.get('id')}")
    allowed_external_states = {"completed", "not_claimed"}
    incomplete = [
        item.get("id")
        for item in pending
        if item.get("status") not in allowed_external_states
    ]
    _require(not incomplete, f"external claims remain incomplete: {incomplete}")
    _require("{{" not in "\n".join(drafts.values()), "submission drafts still contain placeholders")
    return {"verified_claims": len(claims), "external_claims": len(pending)}


def _pointer(value: Any, pointer: str) -> Any:
    current = value
    for raw in pointer.removeprefix("/").split("/") if pointer else []:
        token = raw.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def _release_metadata(project: Path) -> dict[str, Any]:
    value = _read(project / "submission/build-week-2026/release-metadata.json")
    _require(value.get("status") == "ready", "release metadata is not ready")
    _require(SHA_PATTERN.fullmatch(str(value.get("release_revision", ""))) is not None, "release revision is invalid")
    for field in ("repository", "public_ui"):
        item = value.get(field) or {}
        _require(HTTPS_PATTERN.fullmatch(str(item.get("url", ""))) is not None, f"{field} URL is invalid")
        _require(item.get("access_verified") is True, f"{field} access is not verified")
        _require(bool(item.get("verified_at")), f"{field} access lacks a verification date")
        devpost = (project / "submission/build-week-2026/DEVPOST_DRAFT.md").read_text(encoding="utf-8")
        _require(str(item["url"]) in devpost, f"{field} URL is absent from Devpost draft")
    _require(bool(value.get("codex_session_id")), "Codex feedback session id is missing")
    model_evidence = value.get("live_openai_evidence") or {}
    model = str(model_evidence.get("model", ""))
    _require(model_evidence.get("status") == "verified", "GPT-5.6 evidence is not verified")
    _require(
        model == "gpt-5.6" or model.startswith("gpt-5.6-"),
        "GPT-5.6 model evidence is missing",
    )
    bundle = project / str(model_evidence.get("public_bundle", ""))
    _require(bundle.is_dir(), "GPT-5.6 public evidence bundle is missing")
    return {
        "repository": value["repository"]["url"],
        "public_ui": value["public_ui"]["url"],
        "gpt_model": model,
    }


def _manual_comparison(project: Path) -> dict[str, Any]:
    value = _read(project / "submission/build-week-2026/manual-comparison.json")
    disposition = _external_claim_status(project, "manual_time_comparison")
    if disposition == "not_claimed":
        _require(
            value.get("status") in {"not_measured", "not_claimed"},
            "unclaimed manual comparison has an inconsistent record",
        )
        return {"disposition": "not_claimed", "reason": value.get("notes", "")}
    _require(value.get("status") == "completed", "manual comparison is not completed")
    _require(value.get("same_task") is True and value.get("same_stopping_rule") is True, "comparison is not controlled")
    manual = float(value.get("manual_seconds", 0))
    forge = float(value.get("forge_seconds", 0))
    _require(manual > 0 and forge > 0, "comparison durations must be positive")
    _require(value.get("reviewer_role") == "non_builder", "comparison must be run by a non-builder")
    return {"manual_seconds": manual, "forge_seconds": forge}


def _clean_room(project: Path) -> dict[str, Any]:
    value = _read(project / "submission/build-week-2026/clean-room-review.json")
    disposition = _external_claim_status(project, "clean_room_reviewer")
    if disposition == "not_claimed":
        _require(
            value.get("status") in {"not_run", "not_claimed"},
            "unclaimed clean-room review has an inconsistent record",
        )
        return {"disposition": "not_claimed", "reason": value.get("notes", "")}
    _require(value.get("status") == "completed", "clean-room review is not completed")
    _require(value.get("reviewer_role") == "non_builder", "clean-room reviewer is not independent")
    _require(0 < float(value.get("elapsed_seconds", 0)) <= 720, "clean-room review exceeded twelve minutes")
    tasks = value.get("tasks") or {}
    required = {"product", "roles", "first_command", "headline_evidence", "repair_decision"}
    incomplete = sorted(item for item in required if tasks.get(item) is not True)
    _require(not incomplete, f"clean-room tasks incomplete: {incomplete}")
    _require(not value.get("stop_ship_findings"), "clean-room review contains stop-ship findings")
    return {"elapsed_seconds": value["elapsed_seconds"], "tasks_passed": len(required)}


def _video(project: Path) -> dict[str, Any]:
    value = _read(project / "submission/build-week-2026/video-review.json")
    _require(value.get("status") == "completed", "video review is not completed")
    _require(0 < float(value.get("duration_seconds", 0)) < 180, "video is not under three minutes")
    _require(HTTPS_PATTERN.fullmatch(str(value.get("url", ""))) is not None, "video URL is invalid")
    for field in ("signed_out_access", "audio_verified", "no_secrets_verified"):
        _require(value.get(field) is True, f"video check is incomplete: {field}")
    _require(
        value.get("captions_verified") in {True, "burned_in", "not_required"},
        "video caption disposition is missing",
    )
    devpost = (project / "submission/build-week-2026/DEVPOST_DRAFT.md").read_text(encoding="utf-8")
    _require(str(value["url"]) in devpost, "video URL is absent from Devpost draft")
    return {"url": value["url"], "duration_seconds": value["duration_seconds"]}


def _published_image(project: Path) -> dict[str, Any]:
    value = _read(project / "judge-image-metadata.json")
    disposition = _external_claim_status(project, "multiarch_image")
    if disposition == "not_claimed":
        digest = str(value.get("index_digest", ""))
        reference = str(value.get("reference", ""))
        devpost = (project / "submission/build-week-2026/DEVPOST_DRAFT.md").read_text(encoding="utf-8")
        _require(
            not reference or not digest or f"{reference}@{digest}" not in devpost,
            "unclaimed historical image digest appears in Devpost draft",
        )
        return {"disposition": "not_claimed", "historical_metadata_retained": True}
    _require(value.get("status") == "built_and_pushed", "Judge image is not published")
    _require(value.get("platforms") == ["linux/amd64", "linux/arm64"], "Judge image platforms are incomplete")
    digest = str(value.get("index_digest", ""))
    _require(re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is not None, "Judge image digest is invalid")
    devpost = (project / "submission/build-week-2026/DEVPOST_DRAFT.md").read_text(encoding="utf-8")
    _require(f"{value.get('reference')}@{digest}" in devpost, "image digest is absent from Devpost draft")
    return {"reference": value.get("reference"), "index_digest": digest}


def _external_claim_status(project: Path, identifier: str) -> str:
    ledger = _read(project / "submission/build-week-2026/claim-ledger.json")
    matches = [
        item for item in ledger.get("pending_external_claims", []) if item.get("id") == identifier
    ]
    _require(len(matches) == 1, f"external claim ledger entry is missing: {identifier}")
    status = str(matches[0].get("status", ""))
    _require(status in {"completed", "not_claimed"}, f"external claim is unresolved: {identifier}")
    return status


def _security(project: Path) -> dict[str, Any]:
    metadata = _read(project / "submission/build-week-2026/release-metadata.json")
    license_path = project / str(metadata.get("license_path", ""))
    _require(license_path.is_file(), "declared repository license is missing")
    privacy = metadata.get("privacy_review") or {}
    _require(privacy.get("status") == "completed", "privacy review is not completed")
    _require(privacy.get("raw_prompts_committed") is False, "raw prompts are included")
    _require(privacy.get("raw_model_outputs_committed") is False, "raw model outputs are included")
    tracked = _tracked_files(project)
    findings: list[str] = []
    for path in tracked:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if SECRET_PATTERN.search(text):
            findings.append(path.relative_to(project).as_posix())
    _require(not findings, f"possible committed secrets: {findings[:5]}")
    return {"license": license_path.relative_to(project).as_posix(), "tracked_files_scanned": len(tracked)}


def _tracked_files(project: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=project, capture_output=True, check=True
    )
    return [project / item.decode() for item in completed.stdout.split(b"\0") if item]


def _git_revision(project: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=project, capture_output=True, check=False, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def write_g5_review(*, json_path: str | Path, markdown_path: str | Path, review: Mapping[str, Any]) -> None:
    json_destination = Path(json_path)
    markdown_destination = Path(markdown_path)
    json_destination.parent.mkdir(parents=True, exist_ok=True)
    json_destination.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# G5 Final Release Review", "", f"- Decision: **{review['status']}**",
        f"- Reviewed commit: `{review['reviewed_commit']}`", f"- Checks: {review['check_count']}",
        f"- Failures: {review['failure_count']}", "", "## Checks", "",
        "| Check | Status | Error |", "| --- | --- | --- |",
    ]
    for item in review["checks"]:
        lines.append(f"| {item['id']} | {item['status']} | {item['error']} |")
    lines.extend(["", "## Decision", "", str(review["decision"]), ""])
    markdown_destination.write_text("\n".join(lines), encoding="utf-8")


__all__ = ["G5ReviewError", "review_g5", "write_g5_review"]
