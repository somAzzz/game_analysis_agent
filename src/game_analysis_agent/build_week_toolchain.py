"""Validate the pinned Build Week toolchain against an observed inventory."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "build-week-toolchain-v1"
DOCTOR_SCHEMA_VERSION = "build-week-toolchain-doctor-v1"


class ToolchainError(ValueError):
    """Raised when the toolchain pin is malformed."""


def load_toolchain(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate the Build Week toolchain pin."""

    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ToolchainError(f"toolchain pin not found: {source.name}") from exc
    except json.JSONDecodeError as exc:
        raise ToolchainError(f"toolchain pin is invalid JSON: {source.name}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ToolchainError(f"toolchain schema_version must be {SCHEMA_VERSION!r}")
    for tool in ("python", "node", "godot"):
        config = payload.get(tool)
        if not isinstance(config, dict) or not isinstance(config.get("version"), str):
            raise ToolchainError(f"toolchain {tool}.version is required")
    for tool in ("node", "godot"):
        assets = payload[tool].get("assets")
        if not isinstance(assets, dict) or not assets:
            raise ToolchainError(f"toolchain {tool}.assets is required")
    return payload


def evaluate_toolchain(
    inventory: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare observed tool versions with the declared platform pins."""

    host = _mapping(inventory, "host")
    tools = _mapping(inventory, "tools")
    platform_id = platform_identifier(host.get("system"), host.get("machine"))
    checks: list[dict[str, str]] = []

    supported = platform_id in manifest["node"]["assets"]
    checks.append(
        _check(
            "platform",
            expected="darwin-arm64, linux-amd64, or linux-arm64",
            actual=platform_id,
            passed=supported,
            remediation="use a documented supported platform",
        )
    )
    checks.append(
        _version_check(
            "python",
            tools,
            expected=str(manifest["python"]["version"]),
            match="major_minor",
            remediation="run uv python install 3.12 and uv sync --extra dev",
        )
    )
    checks.append(
        _version_check(
            "node",
            tools,
            expected=str(manifest["node"]["version"]),
            match="exact",
            remediation="run the Build Week local toolchain installer",
        )
    )
    checks.append(
        _availability_check(
            "npm",
            tools,
            remediation="use npm bundled with the pinned Node runtime",
        )
    )

    godot_supported = platform_id in manifest["godot"]["assets"]
    if godot_supported:
        checks.append(
            _version_check(
                "godot",
                tools,
                expected=str(manifest["godot"]["version"]),
                match="prefix",
                remediation="run the Build Week local toolchain installer",
            )
        )
    else:
        checks.append(
            {
                "id": "godot",
                "status": "unsupported",
                "required": "false",
                "expected": "no pinned native asset for this platform",
                "actual": str(_mapping(tools, "godot").get("version", "unknown")),
                "remediation": "use Linux amd64 for real Godot or an offline Replay mode",
            }
        )

    docker = _mapping(tools, "docker_daemon")
    checks.append(
        {
            "id": "docker_daemon",
            "status": "pass" if docker.get("status") == "available" else "warning",
            "required": "false",
            "expected": "optional for P0; required later for containerized Replay/UI",
            "actual": str(docker.get("status", "unknown")),
            "remediation": "install/start Docker Desktop or use native offline modes",
        }
    )

    failures = [
        check
        for check in checks
        if check["required"] == "true" and check["status"] != "pass"
    ]
    return {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "status": "ready" if not failures else "incomplete",
        "platform": platform_id,
        "checks": checks,
        "failure_count": len(failures),
        "warning_count": len([item for item in checks if item["status"] == "warning"]),
    }


def strict_exit_code(result: Mapping[str, Any]) -> int:
    """Return zero only when every required toolchain check passes."""

    return 0 if result.get("status") == "ready" else 1


def platform_identifier(system: Any, machine: Any) -> str:
    """Normalize platform values used by release asset pins."""

    normalized_system = str(system or "unknown").lower()
    normalized_machine = str(machine or "unknown").lower()
    if normalized_system == "darwin" and normalized_machine in {"arm64", "aarch64"}:
        return "darwin-arm64"
    if normalized_system == "linux" and normalized_machine in {"x86_64", "amd64"}:
        return "linux-amd64"
    if normalized_system == "linux" and normalized_machine in {"arm64", "aarch64"}:
        return "linux-arm64"
    return f"{normalized_system}-{normalized_machine}"


def _version_check(
    tool: str,
    tools: Mapping[str, Any],
    *,
    expected: str,
    match: str,
    remediation: str,
) -> dict[str, str]:
    observed = _mapping(tools, tool)
    actual = str(observed.get("version", "unknown"))
    available = observed.get("status") == "available"
    normalized = _numeric_version(actual)
    if match == "major_minor":
        passed = available and ".".join(normalized.split(".")[:2]) == expected
    elif match == "prefix":
        expected_major_minor = expected.split(".stable", 1)[0]
        passed = (
            available
            and ".".join(normalized.split(".")[:2]) == expected_major_minor
        )
    else:
        passed = available and normalized == expected
    return _check(tool, expected, actual, passed, remediation)


def _availability_check(
    tool: str, tools: Mapping[str, Any], *, remediation: str
) -> dict[str, str]:
    observed = _mapping(tools, tool)
    actual = str(observed.get("version", "unknown"))
    return _check(
        tool,
        expected="available",
        actual=actual,
        passed=observed.get("status") == "available",
        remediation=remediation,
    )


def _check(
    check_id: str,
    expected: str,
    actual: str,
    passed: bool,
    remediation: str,
) -> dict[str, str]:
    return {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "required": "true",
        "expected": expected,
        "actual": actual,
        "remediation": "" if passed else remediation,
    }


def _numeric_version(value: str) -> str:
    match = re.search(r"\d+(?:\.\d+)+", value)
    return match.group(0) if match else "unknown"


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ToolchainError(f"toolchain doctor input {key} must be an object")
    return value
