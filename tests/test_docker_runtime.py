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


def test_vllm_defaults_to_v026_hybrid_apc_without_mtp() -> None:
    payload = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = payload["services"]["vllm"]
    command = " ".join(service["command"])
    environment = service["environment"]

    assert service["image"] == "vllm/vllm-openai:v0.26.0"
    assert "--reasoning-parser qwen3" in command
    assert "--enable-prefix-caching" in command
    assert "--no-enable-prefix-caching" in command
    assert "--mamba-cache-mode $${LLM_MAMBA_CACHE_MODE:-align}" in command
    assert "--prefix-match-unit $${LLM_PREFIX_MATCH_UNIT:-16}" in command
    assert 'if [ "$${LLM_ENABLE_PREFIX_CACHING:-1}" = "1" ]' in command
    assert 'if [ "$${LLM_ENABLE_MTP:-0}" = "1" ]' in command
    assert "LLM_ENABLE_PREFIX_CACHING=${LLM_ENABLE_PREFIX_CACHING:-1}" in environment
    assert "LLM_MAMBA_CACHE_MODE=${LLM_MAMBA_CACHE_MODE:-align}" in environment
    assert "LLM_PREFIX_MATCH_UNIT=${LLM_PREFIX_MATCH_UNIT:-16}" in environment
    assert "LLM_ENABLE_MTP=${LLM_ENABLE_MTP:-0}" in environment
    assert (
        "LLM_MTP_NUM_SPECULATIVE_TOKENS=${LLM_MTP_NUM_SPECULATIVE_TOKENS:-3}" in environment
    )
    assert 'num_speculative_tokens\\":$${LLM_MTP_NUM_SPECULATIVE_TOKENS:-3}' in command
    assert "--max-model-len " in command
    assert "$${LLM_MAX_MODEL_LEN:-65536}" in command
    assert "--max-num-seqs $${LLM_MAX_NUM_SEQS:-4}" in command
    assert "--language-model-only" in command
    assert "--max-num-batched-tokens $${LLM_MAX_NUM_BATCHED_TOKENS}" in command
    assert "--max-num-batched-tokens 65536" not in command


def test_sglang_is_primary_hybrid_radix_mtp_backend() -> None:
    payload = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = payload["services"]["sglang"]
    command = " ".join(service["command"])
    environment = service["environment"]

    assert service["image"] == "lmsysorg/sglang:v0.5.16-cu130-runtime"
    assert service["profiles"] == ["local-nvidia", "local-sglang"]
    assert "--quantization modelopt_fp4" in command
    assert "--mamba-radix-cache-strategy" in command
    assert "$${SGLANG_MAMBA_CACHE_STRATEGY:-extra_buffer}" in command
    assert "--page-size" in command
    assert 'if [ "$${SGLANG_ENABLE_MTP:-1}" = "1" ]' in command
    assert "--speculative-algorithm NEXTN" in command
    assert "--speculative-num-steps" in command
    assert "--speculative-eagle-topk" in command
    assert "--speculative-num-draft-tokens" in command
    assert "SGLANG_ENABLE_MTP=${SGLANG_ENABLE_MTP:-1}" in environment
    assert "SGLANG_SPEC_TOPK=${SGLANG_SPEC_TOPK:-1}" in environment


def test_host_sglang_script_uses_the_same_primary_defaults() -> None:
    script_path = ROOT / "tools" / "run_sglang_qwen.sh"
    script = script_path.read_text(encoding="utf-8")

    assert os.access(script_path, os.X_OK)
    assert 'ENABLE_MTP="${SGLANG_ENABLE_MTP:-1}"' in script
    assert 'MAMBA_CACHE_STRATEGY="${SGLANG_MAMBA_CACHE_STRATEGY:-extra_buffer}"' in script
    assert "--quantization modelopt_fp4" in script
    assert "--mamba-radix-cache-strategy" in script
    assert "--speculative-algorithm NEXTN" in script


def test_host_vllm_script_uses_the_same_apc_only_defaults() -> None:
    script = (ROOT / "tools" / "run_vllm_qwen.sh").read_text(encoding="utf-8")

    assert 'ENABLE_PREFIX_CACHING="${LLM_ENABLE_PREFIX_CACHING:-1}"' in script
    assert 'MAMBA_CACHE_MODE="${LLM_MAMBA_CACHE_MODE:-align}"' in script
    assert 'PREFIX_MATCH_UNIT="${LLM_PREFIX_MATCH_UNIT:-16}"' in script
    assert 'ENABLE_MTP="${LLM_ENABLE_MTP:-0}"' in script
    assert 'MTP_NUM_SPECULATIVE_TOKENS="${LLM_MTP_NUM_SPECULATIVE_TOKENS:-3}"' in script
    assert "--enable-prefix-caching" in script
    assert "--mamba-cache-mode" in script
    assert "--prefix-match-unit" in script


def test_godot_wrapper_prefers_compose_and_preserves_current_user() -> None:
    wrapper = ROOT / "scripts" / "godot-docker-wrapper"
    text = wrapper.read_text(encoding="utf-8")

    assert os.access(wrapper, os.X_OK)
    assert "ps --quiet --status running" in text
    assert "exec --no-TTY" in text
    assert '--user "$(id -u):$(id -g)"' in text
    assert "exec docker run --rm \\" in text
    assert '--volume "$PROJECTS_ROOT:$PROJECTS_ROOT"' in text
