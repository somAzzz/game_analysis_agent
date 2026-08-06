"""Tests for the pinned Build Week toolchain doctor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_analysis_agent.build_week_toolchain import (
    ToolchainError,
    evaluate_toolchain,
    load_toolchain,
    platform_identifier,
    strict_exit_code,
)


def _manifest() -> dict:
    return {
        "schema_version": "build-week-toolchain-v1",
        "python": {"version": "3.12"},
        "node": {
            "version": "20.20.2",
            "assets": {
                "darwin-arm64": {},
                "linux-amd64": {},
                "linux-arm64": {},
            },
        },
        "godot": {
            "version": "4.4.stable",
            "assets": {"darwin-arm64": {}, "linux-amd64": {}},
        },
    }


def _inventory(
    *,
    system: str = "Darwin",
    machine: str = "arm64",
    python: str = "3.12.13",
    node: str = "v20.20.2",
    godot: str = "4.4.stable.official",
    docker: str = "unavailable",
) -> dict:
    return {
        "host": {"system": system, "machine": machine},
        "tools": {
            "python": {"status": "available", "version": python},
            "node": {"status": "available", "version": node},
            "npm": {"status": "available", "version": "10.8.2"},
            "godot": {"status": "available", "version": godot},
            "docker_daemon": {"status": docker, "version": "unknown"},
        },
    }


def test_ready_toolchain_allows_optional_missing_docker() -> None:
    result = evaluate_toolchain(_inventory(), _manifest())

    assert result["status"] == "ready"
    assert result["failure_count"] == 0
    assert result["warning_count"] == 1
    assert strict_exit_code(result) == 0


def test_wrong_node_and_godot_versions_fail() -> None:
    result = evaluate_toolchain(
        _inventory(node="v26.0.0", godot="4.7.stable.official"), _manifest()
    )

    failures = {item["id"] for item in result["checks"] if item["status"] == "fail"}
    assert failures == {"node", "godot"}
    assert strict_exit_code(result) == 1


def test_godot_major_minor_match_does_not_accept_440() -> None:
    result = evaluate_toolchain(_inventory(godot="4.40.stable.official"), _manifest())

    godot = next(item for item in result["checks"] if item["id"] == "godot")
    assert godot["status"] == "fail"


def test_linux_arm64_marks_native_godot_unsupported_not_failed() -> None:
    result = evaluate_toolchain(
        _inventory(system="Linux", machine="aarch64", godot="unknown"), _manifest()
    )

    godot = next(item for item in result["checks"] if item["id"] == "godot")
    assert result["platform"] == "linux-arm64"
    assert godot["status"] == "unsupported"
    assert godot["required"] == "false"
    assert result["status"] == "ready"


def test_platform_identifier_normalizes_common_architectures() -> None:
    assert platform_identifier("Darwin", "arm64") == "darwin-arm64"
    assert platform_identifier("Linux", "x86_64") == "linux-amd64"
    assert platform_identifier("Linux", "aarch64") == "linux-arm64"
    assert platform_identifier("FreeBSD", "amd64") == "freebsd-amd64"


def test_load_toolchain_rejects_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "toolchain.json"
    path.write_text(json.dumps({"schema_version": "future"}), encoding="utf-8")

    with pytest.raises(ToolchainError, match="schema_version"):
        load_toolchain(path)
