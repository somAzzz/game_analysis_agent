"""Static portability and profile-isolation tests for Judge containers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_judge_dockerfile_pins_multiarch_base_and_runs_unprivileged() -> None:
    dockerfile = (ROOT / "Dockerfile.judge").read_text(encoding="utf-8")

    assert re.search(r"python:3\.12\.10-slim-bookworm@sha256:[0-9a-f]{64}", dockerfile)
    assert "--platform=" not in dockerfile
    assert "USER judge" in dockerfile
    assert 'ENTRYPOINT ["./judge"]' in dockerfile
    assert "UV_CACHE_DIR=/tmp/uv-cache" in dockerfile
    for required in (
        "judge-manifest.json",
        "COPY .agents/ ./.agents/",
        "COPY demo/ ./demo/",
        "COPY scripts/tools/ ./scripts/tools/",
        "fixtures/",
        "examples/build_week_2026/",
    ):
        assert required in dockerfile


def test_compose_default_is_cpu_dashboard_and_nvidia_is_opt_in() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    default_services = {
        name for name, service in services.items() if not service.get("profiles")
    }

    assert default_services == {"dashboard"}
    assert services["dashboard"]["entrypoint"] == [
        "/app/.venv/bin/python",
        "tools/run_judge_api.py",
    ]
    assert "OPENAI_API_KEY=${OPENAI_API_KEY:-}" in services["dashboard"]["environment"]
    assert services["vllm"]["profiles"] == ["local-nvidia"]
    assert services["godot"]["profiles"] == ["game-tools"]
    assert "GAME_PROJECT_PATH=${GAME_PROJECT_PATH:-/app/demo/study-in-germany}" in services[
        "agent"
    ]["environment"]
    assert "depends_on" not in services["agent"]
    assert services["replay"]["network_mode"] == "none"
    assert services["replay"]["read_only"] is True
    assert services["replay"]["cap_drop"] == ["ALL"]


def test_portable_smoke_fixture_is_hash_pinned_outside_tests() -> None:
    manifest = json.loads(
        (ROOT / "config/build_week_2026_replay.json").read_text(encoding="utf-8")
    )
    fixture = ROOT / manifest["fixture"]

    assert fixture == ROOT / "fixtures/persona_replay/smoke_v1.json"
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == manifest["sha256"]


def test_multiarch_builder_requires_explicit_registry_and_both_native_platforms() -> None:
    script = (ROOT / "tools/build_judge_image.sh").read_text(encoding="utf-8")

    assert "JUDGE_IMAGE_REF:?" in script
    assert "linux/amd64,linux/arm64" in script
    assert "--push" in script
    assert "imagetools inspect" in script
    assert "built_and_pushed" in script
    assert "source_contract_sha256" in script


def test_linux_delivery_ci_runs_native_container_and_dashboard_smokes() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["judge-linux-amd64"]
    rendered = json.dumps(job)

    assert job["runs-on"] == "ubuntu-24.04"
    assert "scripts/setup-evaluator" in rendered
    assert "EVALUATOR_OFFLINE=1" in rendered
    assert "docker build" in rendered
    assert "--network none" in rendered
    assert "--read-only" in rendered
    assert "tools/run_judge_api.py" in rendered
    assert "/api/provider-status" in rendered
    assert "record_platform_evidence.py" in rendered


def test_linux_godot_runner_creates_output_before_first_redirect() -> None:
    script = (ROOT / "scripts/run-p4-linux-godot").read_text(encoding="utf-8")

    assert script.index('mkdir -p "$OUTPUT"') < script.index('> "$OUTPUT/embedded-demo.json"')


def test_godot_workflow_uses_job_safe_embedded_runtime_path() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8"))
    game_path = workflow["jobs"]["godot-contract"]["env"]["GAME_PROJECT_PATH"]

    assert game_path == "${{ github.workspace }}/game-analysis-agent/reports/game-runtime"


def test_workflow_publishes_then_executes_image_on_native_arm64() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8"))
    publish = workflow["jobs"]["publish-judge-image"]
    arm = workflow["jobs"]["judge-linux-arm64"]
    rendered_publish = json.dumps(publish)
    rendered_arm = json.dumps(arm)

    assert publish["permissions"]["packages"] == "write"
    assert "tools/build_judge_image.sh" in rendered_publish
    assert "npm run build:public" in rendered_publish
    assert "GITHUB_REPOSITORY_OWNER" in rendered_publish
    assert "tr '[:upper:]' '[:lower:]'" in rendered_publish
    assert "judge-image-metadata.json" in rendered_publish
    assert arm["runs-on"] == "ubuntu-24.04-arm"
    assert arm["needs"] == "publish-judge-image"
    assert arm["permissions"]["packages"] == "read"
    assert "docker/login-action" in rendered_arm
    assert "run-p4-linux-arm64-image" in rendered_arm
    assert "JUDGE_IMAGE_DIGEST_REF" in rendered_arm
