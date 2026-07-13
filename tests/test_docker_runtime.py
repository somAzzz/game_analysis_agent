from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_defines_persistent_godot_sidecar_with_shared_mount() -> None:
    payload = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = payload["services"]["godot"]

    assert "barichello/godot-ci:4.4" in service["image"]
    assert service["command"] == ["exec sleep infinity"]
    assert service["healthcheck"]["test"] == ["CMD", "godot", "--version"]
    assert service["restart"] == "unless-stopped"
    shared_mount = service["volumes"][0]
    assert shared_mount.count("GODOT_DOCKER_MOUNT_ROOT") == 2
    assert service["volumes"][1] == "/tmp:/tmp"


def test_godot_wrapper_prefers_compose_and_preserves_current_user() -> None:
    wrapper = ROOT / "scripts" / "godot-docker-wrapper"
    text = wrapper.read_text(encoding="utf-8")

    assert os.access(wrapper, os.X_OK)
    assert "ps --quiet --status running" in text
    assert "exec --no-TTY" in text
    assert '--user "$(id -u):$(id -g)"' in text
    assert "exec docker run --rm \\" in text
    assert '--volume "$PROJECTS_ROOT:$PROJECTS_ROOT"' in text
