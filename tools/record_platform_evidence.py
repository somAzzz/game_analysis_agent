#!/usr/bin/env python3
"""Validate raw P4 outputs and write a secret-safe platform evidence record."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_analysis_agent.build_week_g4 import REQUIRED_PLATFORM_CHECKS  # noqa: E402
from game_analysis_agent.platform_delivery import platform_contract_fingerprint  # noqa: E402

MODE_CHECKS = {
    "macos": (
        "macos_system_python_inspect",
        "macos_locked_replay",
        "macos_idempotent_setup",
        "macos_native_ui_api",
        "macos_pinned_real_godot",
    ),
    "linux-amd64": ("linux_amd64_native_and_container",),
    "linux-godot": ("linux_pinned_real_godot",),
    "linux-arm64": ("linux_arm64_container",),
    "live-openai": ("live_openai_campaign",),
}


class PlatformEvidenceError(RuntimeError):
    """Raised when raw outputs cannot support a passing platform claim."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlatformEvidenceError(f"invalid or missing JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PlatformEvidenceError(f"JSON root must be an object: {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PlatformEvidenceError(message)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True
    )
    return completed.stdout.strip()


def _artifact_digests(paths: list[Path], base: Path) -> list[dict[str, str]]:
    return [
        {"name": path.relative_to(base).as_posix(), "sha256": _digest(path)}
        for path in sorted(set(paths))
    ]


def _macos(directory: Path, revision: str) -> tuple[dict[str, Any], list[Path]]:
    names = (
        "doctor-inspect.json",
        "doctor-dashboard-native.json",
        "doctor-real-game.json",
        "judge-inspect.json",
        "judge-replay.json",
        "provider-status.json",
        "experiment.json",
        "root.html",
        "fresh-godot/report_manifest.json",
        "fresh-godot/raw_runs.jsonl",
    )
    paths = [directory / name for name in names]
    values = {path.name: _read(path) for path in paths if path.suffix == ".json"}
    for name in ("doctor-inspect.json", "doctor-dashboard-native.json", "doctor-real-game.json"):
        item = values[name]
        _require(item.get("status") == "ready", f"{name} is not ready")
        host = item.get("platform") or {}
        _require(host.get("system") == "Darwin", f"{name} was not produced on macOS")
        _require(str(host.get("machine", "")).lower() == "arm64", f"{name} is not arm64")
        source = item.get("source") or {}
        _require(source.get("revision") == revision, f"{name} revision differs from checkout")
        _require(source.get("dirty") is False, f"{name} came from a dirty worktree")
    for name in ("judge-inspect.json", "judge-replay.json"):
        _require(values[name].get("status") == "passed", f"{name} did not pass")
    providers = values["provider-status.json"].get("providers") or {}
    _require((providers.get("replay") or {}).get("status") == "available", "native Replay provider unavailable")
    experiment = values["experiment.json"]
    _require(
        experiment.get("status") == "passed" and experiment.get("decision") in {"accepted", "rejected"},
        "native experiment API did not return a governed decision",
    )
    root_html = (directory / "root.html").read_text(encoding="utf-8")
    _require('<div id="root"></div>' in root_html, "native Judge frontend did not load")
    manifest = values["report_manifest.json"]
    provenance = manifest.get("provenance") or {}
    agent = provenance.get("agent_repository") or {}
    runtime = provenance.get("runtime") or {}
    godot = runtime.get("godot") or {}
    game = provenance.get("game_repository") or {}
    _require(agent.get("commit") == revision, "macOS Godot report agent revision differs from checkout")
    _require(agent.get("dirty") is False, "macOS Godot report came from a dirty worktree")
    _require(str(runtime.get("platform", "")).lower().startswith("macos"), "Godot report is not from macOS")
    _require(str(godot.get("version", "")).startswith("4.4.stable"), "Godot report did not use pinned 4.4")
    _require(len(str(game.get("commit", ""))) == 40, "Godot report lacks pinned game commit")
    raw = directory / "fresh-godot/raw_runs.jsonl"
    _require(raw.is_file() and raw.stat().st_size > 0, "Godot raw trace is missing")
    return {
        "platform": {"system": "macOS", "architecture": "arm64"},
        "toolchain": {"godot": godot.get("version")},
        "game_revision": game.get("commit"),
        "checks": [{"id": identifier, "status": "passed"} for identifier in MODE_CHECKS["macos"]],
    }, paths


def _linux_amd64(directory: Path, revision: str) -> tuple[dict[str, Any], list[Path]]:
    names = (
        "doctor-inspect.json",
        "doctor-replay.json",
        "doctor-dashboard-native.json",
        "judge-inspect.json",
        "judge-replay.json",
        "container-inspect.json",
        "container-replay.json",
        "provider-status.json",
        "docker-image.json",
    )
    paths = [directory / name for name in names]
    values = {path.name: _read(path) for path in paths}
    for name in ("doctor-inspect.json", "doctor-replay.json", "doctor-dashboard-native.json"):
        item = values[name]
        _require(item.get("status") == "ready", f"{name} is not ready")
        host = item.get("platform") or {}
        _require(host.get("system") == "Linux", f"{name} was not produced on Linux")
        _require(str(host.get("machine", "")).lower() in {"x86_64", "amd64"}, f"{name} is not amd64")
        source = item.get("source") or {}
        _require(source.get("revision") == revision, f"{name} revision differs from checkout")
        _require(source.get("dirty") is False, f"{name} came from a dirty worktree")
    for name in ("judge-inspect.json", "judge-replay.json", "container-inspect.json", "container-replay.json"):
        _require(values[name].get("status") == "passed", f"{name} did not pass")
    providers = values["provider-status.json"].get("providers") or {}
    _require((providers.get("replay") or {}).get("status") == "available", "container Replay provider unavailable")
    return {
        "platform": {"system": "Linux", "architecture": "amd64"},
        "checks": [{"id": MODE_CHECKS["linux-amd64"][0], "status": "passed"}],
    }, paths


def _linux_godot(directory: Path, revision: str) -> tuple[dict[str, Any], list[Path]]:
    manifests = [
        path
        for path in directory.rglob("report_manifest.json")
        if "ci-smoke" in path.as_posix() and (path.parent / "raw_runs.jsonl").is_file()
    ]
    _require(len(manifests) == 1, "expected exactly one ci-smoke simulation manifest with raw trace")
    manifest_path = manifests[0]
    manifest = _read(manifest_path)
    provenance = manifest.get("provenance") or {}
    agent = provenance.get("agent_repository") or {}
    runtime = provenance.get("runtime") or {}
    godot = runtime.get("godot") or {}
    game = provenance.get("game_repository") or {}
    _require(agent.get("commit") == revision, "Godot report agent revision differs from checkout")
    _require(agent.get("dirty") is False, "Godot report came from a dirty worktree")
    _require(str(runtime.get("platform", "")).lower().startswith("linux"), "Godot report is not from Linux")
    _require(str(godot.get("version", "")).startswith("4.4.stable"), "Godot report did not use pinned 4.4")
    _require(len(str(game.get("commit", ""))) == 40, "Godot report lacks pinned game commit")
    raw = manifest_path.parent / "raw_runs.jsonl"
    _require(raw.is_file() and raw.stat().st_size > 0, "Godot raw trace is missing")
    return {
        "platform": {"system": "Linux", "architecture": "amd64"},
        "toolchain": {"godot": godot.get("version")},
        "game_revision": game.get("commit"),
        "checks": [{"id": MODE_CHECKS["linux-godot"][0], "status": "passed"}],
    }, [manifest_path, raw]


def _linux_arm64(directory: Path, _revision: str) -> tuple[dict[str, Any], list[Path]]:
    names = (
        "runner.json",
        "container-inspect.json",
        "container-replay.json",
        "provider-status.json",
        "image-manifest.json",
    )
    paths = [directory / name for name in names]
    values = {path.name: _read(path) for path in paths}
    runner = values["runner.json"]
    _require(runner.get("system") == "Linux", "arm64 evidence was not produced on Linux")
    _require(str(runner.get("machine", "")).lower() in {"aarch64", "arm64"}, "runner is not native arm64")
    for name in ("container-inspect.json", "container-replay.json"):
        _require(values[name].get("status") == "passed", f"{name} did not pass")
    providers = values["provider-status.json"].get("providers") or {}
    _require((providers.get("replay") or {}).get("status") == "available", "arm64 Replay provider unavailable")
    manifest_text = json.dumps(values["image-manifest.json"])
    _require("linux/arm64" in manifest_text, "image manifest does not declare linux/arm64")
    return {
        "platform": {"system": "Linux", "architecture": "arm64"},
        "checks": [{"id": MODE_CHECKS["linux-arm64"][0], "status": "passed"}],
    }, paths


def _live_openai(directory: Path, _revision: str) -> tuple[dict[str, Any], list[Path]]:
    path = directory / "live-openai-campaign.json"
    value = _read(path)
    encoded = json.dumps(value)
    _require("sk-" not in encoded and "OPENAI_API_KEY" not in encoded, "live evidence contains a possible secret")
    _require(value.get("status") == "completed", "live OpenAI campaign is not completed")
    _require(value.get("mode") == "live", "live campaign is not labeled live")
    result = value.get("result") or {}
    _require(result.get("provider") == "openai", "live campaign provider is not OpenAI")
    _require(result.get("mode") == "live", "live result is not labeled live")
    evidence = result.get("provider_evidence") or {}
    _require(int(evidence.get("call_count", 0)) > 0, "live result contains no completed provider calls")
    _require(bool(evidence.get("response_ids")), "live result contains no OpenAI response IDs")
    _require(evidence.get("outputs_recorded") is False, "live result claims raw model outputs were retained")
    return {
        "platform": {"system": platform.system(), "architecture": platform.machine()},
        "provider": "openai",
        "model": result.get("model"),
        "checks": [{"id": MODE_CHECKS["live-openai"][0], "status": "passed"}],
    }, [path]


VALIDATORS = {
    "macos": _macos,
    "linux-amd64": _linux_amd64,
    "linux-godot": _linux_godot,
    "linux-arm64": _linux_arm64,
    "live-openai": _live_openai,
}


def build_evidence(mode: str, directory: Path) -> dict[str, Any]:
    revision = _git_revision()
    contract = platform_contract_fingerprint(ROOT)
    details, paths = VALIDATORS[mode](directory.resolve(), revision)
    return {
        "schema_version": "build-week-platform-evidence-v1",
        "mode": mode,
        "status": "passed",
        "executed_at": datetime.now(tz=UTC).isoformat(),
        "source_revision": revision,
        "source_dirty": False,
        "source_contract_sha256": contract,
        **details,
        "artifact_digests": _artifact_digests(paths, directory.resolve()),
    }


def update_review(evidence_path: Path, evidence: dict[str, Any]) -> None:
    review_path = ROOT / "docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json"
    review = _read(review_path)
    check_ids = MODE_CHECKS[str(evidence["mode"])]
    checks = {item["id"]: item for item in review.get("checks", [])}
    for check_id in check_ids:
        _require(check_id in checks, f"platform review lacks check row: {check_id}")
    try:
        display = evidence_path.resolve().relative_to(review_path.parent.resolve()).as_posix()
    except ValueError as exc:
        raise PlatformEvidenceError("--update-review requires evidence inside the platform review directory") from exc
    for check_id in check_ids:
        checks[check_id] = {
            "id": check_id,
            "status": "passed",
            "evidence": display,
            "source_revision": evidence["source_revision"],
            "source_contract_sha256": evidence["source_contract_sha256"],
        }
    review["checks"] = list(checks.values())
    review["reviewed_at"] = datetime.now(tz=UTC).isoformat()
    review["source_revision"] = _git_revision()
    review["contract_sha256"] = platform_contract_fingerprint(ROOT)
    by_id = {item["id"]: item["status"] for item in review["checks"]}
    incomplete = sorted(item for item in REQUIRED_PLATFORM_CHECKS if by_id.get(item) != "passed")
    review["status"] = "passed" if not incomplete else "partial"
    review["decision"] = (
        "All required macOS, Linux, live-provider, and container platform evidence is complete."
        if not incomplete
        else f"Platform delivery remains incomplete: {incomplete}."
    )
    review_path.write_text(json.dumps(review, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(VALIDATORS), required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--update-review", action="store_true")
    args = parser.parse_args()
    try:
        evidence = build_evidence(args.mode, args.artifact_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.update_review:
            update_review(args.output, evidence)
    except (OSError, PlatformEvidenceError, subprocess.SubprocessError, ValueError) as exc:
        print(f"platform evidence error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "passed", "mode": args.mode, "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
