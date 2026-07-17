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
from game_analysis_agent.build_week_game_pin import (  # noqa: E402
    _runtime_overlay_specs,
    load_game_pin,
)
from game_analysis_agent.platform_delivery import platform_contract_fingerprint  # noqa: E402
from game_analysis_agent.report_manifest import (  # noqa: E402
    execution_source_fingerprint,
    game_source_fingerprint,
    runtime_source_fingerprint,
)

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


def _validate_game_provenance(
    manifest: dict[str, Any], directory: Path, revision: str
) -> dict[str, Any]:
    provenance = manifest.get("provenance") or {}
    game = provenance.get("game_repository") or {}
    fingerprints = provenance.get("fingerprints") or {}
    pin = load_game_pin(ROOT / "config/build_week_2026_game_pin.json")["pin"]
    runtime = directory / "game-runtime"
    overlays = game.get("runtime_overlays") or []
    _require(
        game.get("source_type") == "embedded_runtime_overlay",
        "Godot report did not use the embedded runtime overlay",
    )
    for field in ("commit", "tree", "archive_sha256", "content_tree_sha256", "file_count"):
        _require(game.get(field) == pin.get(field), f"Godot report game {field} differs from pin")
    expected_overlays = []
    for overlay_path, overlay_source in _runtime_overlay_specs():
        canonical = ROOT / "demo/study-in-germany" / overlay_path
        runtime_source = ROOT / overlay_source
        runtime_target = runtime / overlay_path
        expected_overlays.append(
            {
                "path": overlay_path,
                "source": overlay_source,
                "canonical_sha256": _digest(canonical) if canonical.is_file() else None,
                "runtime_sha256": _digest(runtime_source),
            }
        )
        _require(runtime_target.is_file(), f"Godot runtime overlay is missing: {overlay_path}")
        _require(
            _digest(runtime_target) == _digest(runtime_source),
            f"Godot runtime overlay content differs: {overlay_path}",
        )
    _require(
        overlays == expected_overlays,
        "Godot report runtime overlays differ from the audited adapters",
    )
    _require(runtime.is_dir(), "prepared game runtime is missing from platform artifacts")
    expected_game = game_source_fingerprint(runtime)
    expected_runtime = runtime_source_fingerprint(ROOT)
    _require(
        fingerprints.get("game_source_sha256") == expected_game,
        "Godot report game fingerprint differs from runtime",
    )
    _require(
        fingerprints.get("runtime_source_sha256") == expected_runtime,
        "Godot report agent fingerprint differs from checkout",
    )
    _require(
        fingerprints.get("execution_source_sha256") == execution_source_fingerprint(ROOT, runtime),
        "Godot report execution fingerprint differs from checkout and runtime",
    )
    agent = provenance.get("agent_repository") or {}
    _require(
        agent.get("commit") == revision and agent.get("dirty") is False,
        "Godot report agent provenance differs from clean checkout",
    )
    return game


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
    _require(
        (providers.get("replay") or {}).get("status") == "available",
        "native Replay provider unavailable",
    )
    experiment = values["experiment.json"]
    _require(
        experiment.get("status") == "passed"
        and experiment.get("decision") in {"accepted", "rejected"},
        "native experiment API did not return a governed decision",
    )
    root_html = (directory / "root.html").read_text(encoding="utf-8")
    _require('<div id="root"></div>' in root_html, "native Judge frontend did not load")
    manifest = values["report_manifest.json"]
    provenance = manifest.get("provenance") or {}
    runtime = provenance.get("runtime") or {}
    godot = runtime.get("godot") or {}
    game = _validate_game_provenance(manifest, directory, revision)
    _require(
        str(runtime.get("platform", "")).lower().startswith("macos"),
        "Godot report is not from macOS",
    )
    _require(
        str(godot.get("version", "")).startswith("4.4.stable"),
        "Godot report did not use pinned 4.4",
    )
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
        _require(
            str(host.get("machine", "")).lower() in {"x86_64", "amd64"}, f"{name} is not amd64"
        )
        source = item.get("source") or {}
        _require(source.get("revision") == revision, f"{name} revision differs from checkout")
        _require(source.get("dirty") is False, f"{name} came from a dirty worktree")
    for name in (
        "judge-inspect.json",
        "judge-replay.json",
        "container-inspect.json",
        "container-replay.json",
    ):
        _require(values[name].get("status") == "passed", f"{name} did not pass")
    providers = values["provider-status.json"].get("providers") or {}
    _require(
        (providers.get("replay") or {}).get("status") == "available",
        "container Replay provider unavailable",
    )
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
    _require(
        len(manifests) == 1, "expected exactly one ci-smoke simulation manifest with raw trace"
    )
    manifest_path = manifests[0]
    manifest = _read(manifest_path)
    provenance = manifest.get("provenance") or {}
    runtime = provenance.get("runtime") or {}
    godot = runtime.get("godot") or {}
    game = _validate_game_provenance(manifest, directory, revision)
    _require(
        str(runtime.get("platform", "")).lower().startswith("linux"),
        "Godot report is not from Linux",
    )
    _require(
        str(godot.get("version", "")).startswith("4.4.stable"),
        "Godot report did not use pinned 4.4",
    )
    raw = manifest_path.parent / "raw_runs.jsonl"
    _require(raw.is_file() and raw.stat().st_size > 0, "Godot raw trace is missing")
    expected_findings = directory / "expected-demo-findings.json"
    findings = _read(expected_findings)
    _require(
        findings.get("schema_version") == "build-week-expected-demo-findings-result-v1"
        and findings.get("status") == "passed"
        and findings.get("game_commit") == game.get("commit"),
        "declared demo findings were not verified",
    )
    return {
        "platform": {"system": "Linux", "architecture": "amd64"},
        "toolchain": {"godot": godot.get("version")},
        "game_revision": game.get("commit"),
        "checks": [{"id": MODE_CHECKS["linux-godot"][0], "status": "passed"}],
    }, [manifest_path, raw, expected_findings]


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
    _require(
        str(runner.get("machine", "")).lower() in {"aarch64", "arm64"}, "runner is not native arm64"
    )
    for name in ("container-inspect.json", "container-replay.json"):
        _require(values[name].get("status") == "passed", f"{name} did not pass")
    providers = values["provider-status.json"].get("providers") or {}
    _require(
        (providers.get("replay") or {}).get("status") == "available",
        "arm64 Replay provider unavailable",
    )
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
    _require(
        "sk-" not in encoded and "OPENAI_API_KEY" not in encoded,
        "live evidence contains a possible secret",
    )
    _require(value.get("status") == "completed", "live OpenAI campaign is not completed")
    _require(value.get("mode") == "live", "live campaign is not labeled live")
    result = value.get("result") or {}
    _require(result.get("provider") == "openai", "live campaign provider is not OpenAI")
    _require(result.get("mode") == "live", "live result is not labeled live")
    evidence = result.get("provider_evidence") or {}
    model = str(result.get("model", ""))
    _require(
        model == "gpt-5.6" or model.startswith("gpt-5.6-"),
        "live campaign did not use the required GPT-5.6 model family",
    )
    _require(
        int(evidence.get("call_count", 0)) > 0, "live result contains no completed provider calls"
    )
    _require(bool(evidence.get("response_ids")), "live result contains no OpenAI response IDs")
    _require(
        evidence.get("outputs_recorded") is False,
        "live result claims raw model outputs were retained",
    )
    return {
        "platform": {"system": platform.system(), "architecture": platform.machine()},
        "provider": "openai",
        "model": model,
        "checks": [{"id": MODE_CHECKS["live-openai"][0], "status": "passed"}],
    }, [path]


VALIDATORS = {
    "macos": _macos,
    "linux-amd64": _linux_amd64,
    "linux-godot": _linux_godot,
    "linux-arm64": _linux_arm64,
    "live-openai": _live_openai,
}

STALE_REMEDIATION = {
    "macos_system_python_inspect": "Run scripts/run-p4-macos and import current macOS evidence.",
    "macos_locked_replay": "Run scripts/run-p4-macos and import current macOS evidence.",
    "macos_idempotent_setup": "Run scripts/run-p4-macos and import current macOS evidence.",
    "macos_native_ui_api": "Run scripts/run-p4-macos and import current macOS evidence.",
    "macos_pinned_real_godot": "Run scripts/run-p4-macos and import current macOS evidence.",
    "linux_amd64_native_and_container": "Run scripts/run-p4-linux-amd64 or the Linux amd64 CI job at the current revision.",
    "linux_pinned_real_godot": "Manually dispatch the Test workflow with godot_version=4.4-stable; the embedded demo requires no repository token.",
    "linux_arm64_container": "Publish the current multi-architecture image and run scripts/run-p4-linux-arm64-image on native arm64.",
    "live_openai_campaign": "Set a restricted server-side OPENAI_API_KEY and run scripts/run-p4-live-openai.",
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
    current_contract = platform_contract_fingerprint(ROOT)
    _require(
        evidence.get("source_contract_sha256") == current_contract,
        "refusing to import platform evidence from a stale delivery contract",
    )
    checks = {item["id"]: item for item in review.get("checks", [])}
    for check_id, item in list(checks.items()):
        if (
            item.get("status") == "passed"
            and item.get("source_contract_sha256") != current_contract
        ):
            checks[check_id] = {
                **item,
                "status": "stale",
                "reason": "Evidence was produced for a different delivery contract.",
                "remediation": STALE_REMEDIATION.get(
                    check_id, "Rerun this platform check at the current revision."
                ),
            }
    if (
        "linux_pinned_real_godot" in checks
        and checks["linux_pinned_real_godot"].get("status") != "passed"
    ):
        checks["linux_pinned_real_godot"]["remediation"] = STALE_REMEDIATION[
            "linux_pinned_real_godot"
        ]
    for check_id in check_ids:
        _require(check_id in checks, f"platform review lacks check row: {check_id}")
    try:
        display = evidence_path.resolve().relative_to(review_path.parent.resolve()).as_posix()
    except ValueError as exc:
        raise PlatformEvidenceError(
            "--update-review requires evidence inside the platform review directory"
        ) from exc
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
    review["contract_sha256"] = current_contract
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
        args.output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if args.update_review:
            update_review(args.output, evidence)
    except (OSError, PlatformEvidenceError, subprocess.SubprocessError, ValueError) as exc:
        print(f"platform evidence error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {"status": "passed", "mode": args.mode, "output": str(args.output)}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
