#!/usr/bin/env python3
"""Secret-safe, standard-library preflight for every Judge delivery mode."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = ROOT / "config/build_week_2026_toolchain.json"
MODES = (
    "inspect",
    "replay",
    "dashboard-native",
    "dashboard-container",
    "live-openai",
    "real-game",
    "local-model",
)


def _probe(command: list[str], *, timeout: float = 3) -> dict[str, str]:
    executable = shutil.which(command[0])
    if not executable:
        return {"status": "unavailable", "version": ""}
    try:
        completed = subprocess.run(
            [executable, *command[1:]],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "unavailable", "version": ""}
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return {
        "status": "available" if completed.returncode == 0 else "unavailable",
        "version": output[0][:160] if output else "",
    }


def _expected_godot_version() -> str:
    try:
        value = json.loads(TOOLCHAIN.read_text(encoding="utf-8"))
        return str(value["godot"]["version"])
    except (KeyError, OSError, TypeError, ValueError):
        return ""


def _godot_probe(environment: dict[str, str]) -> dict[str, Any]:
    expected = _expected_godot_version()
    configured = environment.get("GODOT_BIN", "").strip()
    candidates = [configured] if configured else ["godot4", "godot"]
    for candidate in candidates:
        if not candidate:
            continue
        result = _probe([candidate, "--version"], timeout=5)
        if result["status"] == "available":
            result["path"] = shutil.which(candidate) or candidate
            result["expected_version"] = expected
            result["version_matches_pin"] = bool(expected and result["version"].startswith(expected))
            return result
    return {
        "status": "unavailable",
        "version": "",
        "path": configured,
        "expected_version": expected,
        "version_matches_pin": False,
    }


def _docker_probe() -> dict[str, str]:
    binary = shutil.which("docker")
    if not binary:
        return {"status": "unavailable", "version": "", "daemon": "unavailable"}
    version = _probe(["docker", "--version"])
    daemon = _probe(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=5)
    return {
        "status": version["status"],
        "version": version["version"],
        "daemon": daemon["status"],
    }


def _git_state() -> dict[str, Any]:
    revision = _probe(["git", "rev-parse", "HEAD"])
    dirty = _probe(["git", "status", "--porcelain"])
    return {
        "revision": revision["version"] if revision["status"] == "available" else "unknown",
        "dirty": bool(dirty["version"]) if dirty["status"] == "available" else None,
    }


def _check(identifier: str, passed: bool, required: bool, detail: str, remediation: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "status": "passed" if passed else ("failed" if required else "warning"),
        "required": required,
        "detail": detail,
        "remediation": "" if passed else remediation,
    }


def diagnose(mode: str, environment: dict[str, str] | None = None) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"unknown Judge mode: {mode}")
    env = dict(os.environ if environment is None else environment)
    system = platform.system()
    machine = platform.machine()
    supported_host = (system, machine.lower()) in {
        ("Darwin", "arm64"),
        ("Linux", "x86_64"),
        ("Linux", "amd64"),
        ("Linux", "aarch64"),
        ("Linux", "arm64"),
    }
    python_ok = sys.version_info >= (3, 9)
    uv = _probe(["uv", "--version"])
    node = _probe(["node", "--version"])
    npm = _probe(["npm", "--version"])
    godot = _godot_probe(env)
    docker = _docker_probe()
    game_path = Path(env["GAME_PROJECT_PATH"]).expanduser() if env.get("GAME_PROJECT_PATH") else None
    game_ok = bool(game_path and game_path.is_dir() and (game_path / "project.godot").is_file())
    report_path = Path(env.get("JUDGE_REPORT_DIR", ROOT / "reports/judge"))
    writable_parent = next((item for item in (report_path, *report_path.parents) if item.exists()), ROOT)
    reports_writable = os.access(writable_parent, os.W_OK)
    key_configured = bool(env.get("OPENAI_API_KEY", "").strip())

    checks = [_check("supported_host", supported_host, True, f"{system}/{machine}", "Use macOS arm64 or Linux amd64/arm64.")]
    if mode == "inspect":
        checks.append(_check("python", python_ok, True, platform.python_version(), "Install Python 3.9 or newer."))
    if mode in {
        "replay",
        "dashboard-native",
        "dashboard-container",
        "live-openai",
        "real-game",
        "local-model",
    }:
        checks.extend(
            [
                _check("python", python_ok, True, platform.python_version(), "Install Python 3.9 or newer."),
                _check("uv", uv["status"] == "available", True, uv["version"] or "not found", "Install uv, then run scripts/setup-evaluator."),
            ]
        )
    if mode in {"dashboard-native", "dashboard-container"}:
        checks.extend(
            [
                _check("node", node["status"] == "available", False, node["version"] or "not found", "Use scripts/setup-build-week-toolchain for the pinned Node runtime."),
                _check("npm", npm["status"] == "available", False, npm["version"] or "not found", "Install npm or use the prebuilt Judge image."),
                _check("frontend_build", (ROOT / "frontend/dist/index.html").is_file(), True, "frontend/dist/index.html", "Run scripts/setup-evaluator."),
            ]
        )
    if mode == "dashboard-container":
        checks.append(_check("docker", docker["daemon"] == "available", True, docker["version"] or "not found", "Start Docker Desktop/Engine or use dashboard-native."))
    if mode in {"live-openai", "real-game"}:
        checks.extend(
            [
                _check("game_project", game_ok, True, str(game_path or "not configured"), "Set GAME_PROJECT_PATH to a Godot project."),
                _check(
                    "godot",
                    godot["status"] == "available" and bool(godot["version_matches_pin"]),
                    True,
                    godot["version"] or "not found",
                    f"Set GODOT_BIN to the pinned Godot {godot['expected_version'] or 'version'} executable.",
                ),
                _check("report_directory", reports_writable, True, str(report_path), "Choose a writable JUDGE_REPORT_DIR."),
            ]
        )
    if mode == "live-openai":
        checks.append(_check("openai_key", key_configured, True, "configured" if key_configured else "not configured", "Set OPENAI_API_KEY in the server environment."))
    if mode == "local-model":
        checks.append(_check("local_model_endpoint", bool(env.get("VLLM_BASE_URL", "").strip()), True, "configured" if env.get("VLLM_BASE_URL") else "not configured", "Set VLLM_BASE_URL and start the optional local provider."))

    failures = [item for item in checks if item["status"] == "failed"]
    warnings = [item for item in checks if item["status"] == "warning"]
    result = {
        "schema_version": "judge-doctor-v1",
        "status": "ready" if not failures else "unsupported",
        "mode": mode,
        "platform": {"system": system, "machine": machine, "release": platform.release()},
        "source": _git_state(),
        "capabilities": {
            "python": platform.python_version(),
            "uv": uv,
            "node": node,
            "npm": npm,
            "godot": godot,
            "docker": docker,
            "game_project_configured": game_ok,
            "openai_key_configured": key_configured,
            "report_directory_writable": reports_writable,
        },
        "checks": checks,
        "failure_count": len(failures),
        "warning_count": len(warnings),
    }
    serialized = json.dumps(result)
    for secret_name in ("OPENAI_API_KEY", "HF_TOKEN", "VLLM_API_KEY"):
        secret = env.get(secret_name, "")
        if secret and secret in serialized:
            raise RuntimeError(f"doctor output contains {secret_name}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check one Playtest Forge Judge delivery mode.")
    parser.add_argument("--mode", choices=MODES, default="inspect")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = diagnose(args.mode)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Judge doctor: {result['status']} ({result['mode']})")
        for check in result["checks"]:
            print(f"  {check['status']:7} {check['id']}: {check['detail']}")
            if check["remediation"]:
                print(f"           remedy: {check['remediation']}")
    return 0 if result["status"] == "ready" else 10


if __name__ == "__main__":
    raise SystemExit(main())
