#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-nvidia/Qwen3.6-27B-NVFP4}"
HOST="${VLLM_HOST:-127.0.0.1}"
PORT="${VLLM_PORT:-8000}"
API_KEY="${VLLM_API_KEY:-local-dev-token}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-65536}"
GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.90}"
MAX_NUM_SEQS="${LLM_MAX_NUM_SEQS:-4}"
ENABLE_PREFIX_CACHING="${LLM_ENABLE_PREFIX_CACHING:-1}"
MAMBA_CACHE_MODE="${LLM_MAMBA_CACHE_MODE:-align}"
PREFIX_MATCH_UNIT="${LLM_PREFIX_MATCH_UNIT:-16}"
ENABLE_MTP="${LLM_ENABLE_MTP:-0}"
MTP_NUM_SPECULATIVE_TOKENS="${LLM_MTP_NUM_SPECULATIVE_TOKENS:-3}"

args=(
  serve "$MODEL_ID"
  --host "$HOST"
  --port "$PORT"
  --api-key "$API_KEY"
  --trust-remote-code
  --quantization modelopt
  --reasoning-parser qwen3
  --dtype auto
  --max-model-len "$MAX_MODEL_LEN"
  --max-num-seqs "$MAX_NUM_SEQS"
  --language-model-only
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
  --generation-config vllm
)

if [[ "$ENABLE_PREFIX_CACHING" == "1" ]]; then
  args+=(
    --enable-prefix-caching
    --mamba-cache-mode "$MAMBA_CACHE_MODE"
    --prefix-match-unit "$PREFIX_MATCH_UNIT"
  )
else
  args+=(--no-enable-prefix-caching)
fi

if [[ "$ENABLE_MTP" == "1" ]]; then
  args+=(--speculative-config "{\"method\":\"mtp\",\"num_speculative_tokens\":$MTP_NUM_SPECULATIVE_TOKENS}")
fi

exec vllm "${args[@]}"
