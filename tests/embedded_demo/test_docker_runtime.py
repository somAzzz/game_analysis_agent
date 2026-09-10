from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_DFLASH2_IMAGE = (
    "lmsysorg/sglang@"
    "sha256:d6e7288627be8b02be88e4bba38e73f6d50e2826869f753c13a4c4385ab3eda9"
)


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


def test_sglang_is_primary_qwen38_apc_dflash2_backend() -> None:
    payload = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = payload["services"]["sglang"]
    command = " ".join(service["command"])
    environment = service["environment"]

    assert OFFICIAL_DFLASH2_IMAGE in service["image"]
    assert service["profiles"] == ["local-nvidia", "local-sglang"]
    assert "$${SGLANG_MODEL_PATH:-RadixArk/Qwen3.8-27B-NVFP4}" in command
    assert "--quantization" not in command
    assert '--attention-backend "$${SGLANG_ATTENTION_BACKEND:-flashinfer}"' in command
    assert '--chunked-prefill-size "$${SGLANG_CHUNKED_PREFILL_SIZE:-2048}"' in command
    assert '--mem-fraction-static "$${SGLANG_MEM_FRACTION_STATIC:-0.80}"' in command
    assert "--mamba-radix-cache-strategy" in command
    assert "$${SGLANG_MAMBA_CACHE_STRATEGY:-extra_buffer_lazy}" in command
    assert 'if [ "$${SGLANG_ENABLE_APC:-1}" != "1" ]' in command
    assert "--disable-radix-cache" in command
    assert 'ALGORITHM="$${SGLANG_SPECULATIVE_ALGORITHM:-DFLASH}"' in command
    assert 'if [ "$$ALGORITHM" != "NONE" ]' in command
    assert '--speculative-algorithm "$$ALGORITHM"' in command
    assert "--speculative-draft-model-path" in command
    assert "incoai/Qwen3.8-27B-DFlash2" in command
    assert "--speculative-draft-model-revision" in command
    assert "--speculative-num-draft-tokens" in command
    assert "--enable-metrics" in command
    assert "--revision" in command
    assert "SGLANG_ENABLE_APC=${SGLANG_ENABLE_APC:-1}" in environment
    assert "SGLANG_MEM_FRACTION_STATIC=${SGLANG_MEM_FRACTION_STATIC:-0.80}" in environment
    assert (
        "SGLANG_SPECULATIVE_ALGORITHM=${SGLANG_SPECULATIVE_ALGORITHM:-DFLASH}"
        in environment
    )


def test_host_sglang_script_uses_the_same_primary_defaults() -> None:
    script_path = ROOT / "tools" / "llm_runtime" / "run_sglang_qwen.sh"
    script = script_path.read_text(encoding="utf-8")

    assert os.access(script_path, os.X_OK)
    assert 'ENABLE_APC="${SGLANG_ENABLE_APC:-1}"' in script
    assert 'MEM_FRACTION_STATIC="${SGLANG_MEM_FRACTION_STATIC:-0.80}"' in script
    assert 'SPECULATIVE_ALGORITHM="${SGLANG_SPECULATIVE_ALGORITHM:-DFLASH}"' in script
    assert (
        'MAMBA_CACHE_STRATEGY="${SGLANG_MAMBA_CACHE_STRATEGY:-extra_buffer_lazy}"' in script
    )
    assert "--quantization" not in script
    assert "--mamba-radix-cache-strategy" in script
    assert '--speculative-algorithm "$SPECULATIVE_ALGORITHM"' in script
    assert "incoai/Qwen3.8-27B-DFlash2" in script
    assert "--speculative-draft-model-revision" in script
    assert "--speculative-num-draft-tokens" in script
    assert "--enable-metrics" in script


def test_sglang_profiles_pin_dflash2_and_dspark_rollbacks() -> None:
    dflash = (ROOT / "config" / "sglang" / "dflash2.env").read_text(encoding="utf-8")
    dspark = (ROOT / "config" / "sglang" / "dspark.env").read_text(encoding="utf-8")
    target_only = (ROOT / "config" / "sglang" / "target-only.env").read_text(
        encoding="utf-8"
    )
    override = (ROOT / "docker-compose.sglang-dflash2.yml").read_text(
        encoding="utf-8"
    )

    assert "SGLANG_SPECULATIVE_ALGORITHM=DFLASH" in dflash
    assert OFFICIAL_DFLASH2_IMAGE in dflash
    assert "SGLANG_MEM_FRACTION_STATIC=0.80" in dflash
    assert "SGLANG_NUM_DRAFT_TOKENS=8" in dflash
    assert "SGLANG_DRAFT_MODEL_REVISION=dedf8df68adfb1afeaf7b7480c0a0243108177b4" in dflash
    assert "SGLANG_SPECULATIVE_ALGORITHM=DSPARK" in dspark
    assert OFFICIAL_DFLASH2_IMAGE in dspark
    assert OFFICIAL_DFLASH2_IMAGE in target_only
    assert "SGLANG_SPECULATIVE_ALGORITHM=NONE" in target_only
    assert OFFICIAL_DFLASH2_IMAGE in override
    assert "build:" not in override


def test_host_vllm_script_uses_the_same_apc_only_defaults() -> None:
    script = (ROOT / "tools" / "llm_runtime" / "run_vllm_qwen.sh").read_text(encoding="utf-8")

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
    assert 'docker exec "$running_id" test -d "$PWD"' in text
    assert "exec --no-TTY" in text
    assert '--user "$(id -u):$(id -g)"' in text
    assert "exec docker run --rm \\" in text
    assert '--volume "$PROJECTS_ROOT:$PROJECTS_ROOT"' in text


def test_godot_wrapper_falls_back_when_sidecar_cannot_see_worktree(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        """#!/bin/sh
if [ "$1" = "compose" ]; then
  for gaa_arg in "$@"; do
    if [ "$gaa_arg" = "ps" ]; then
      printf '%s\\n' fake-sidecar
      exit 0
    fi
  done
  exit 90
fi
if [ "$1" = "exec" ]; then
  exit 1
fi
if [ "$1" = "run" ]; then
  printf '%s\\n' "$*"
  exit 0
fi
exit 91
""",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    result = subprocess.run(
        [str(ROOT / "scripts/godot-docker-wrapper"), "--version"],
        cwd=ROOT,
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.startswith("run --rm ")
    assert f"--volume {ROOT.parent}:{ROOT.parent}" in result.stdout
