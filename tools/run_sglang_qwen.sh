#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-nvidia/Qwen3.6-27B-NVFP4}"
HOST="${SGLANG_HOST:-127.0.0.1}"
PORT="${SGLANG_PORT:-30000}"
API_KEY="${SGLANG_API_KEY:-local-dev-token}"
SERVED_MODEL_NAME="${LLM_SERVED_MODEL_NAME:-qwen3.6-27b-nvfp4}"
MAX_MODEL_LEN="${LLM_MAX_MODEL_LEN:-65536}"
MAX_RUNNING_REQUESTS="${LLM_MAX_NUM_SEQS:-4}"
MEM_FRACTION_STATIC="${SGLANG_MEM_FRACTION_STATIC:-0.80}"
MAMBA_CACHE_STRATEGY="${SGLANG_MAMBA_CACHE_STRATEGY:-extra_buffer}"
PAGE_SIZE="${SGLANG_PAGE_SIZE:-64}"
ENABLE_MTP="${SGLANG_ENABLE_MTP:-1}"
SPEC_NUM_STEPS="${SGLANG_SPEC_NUM_STEPS:-3}"
SPEC_TOPK="${SGLANG_SPEC_TOPK:-1}"
SPEC_NUM_DRAFT_TOKENS="${SGLANG_SPEC_NUM_DRAFT_TOKENS:-4}"

args=(
  serve
  --model-path "$MODEL_ID"
  --host "$HOST"
  --port "$PORT"
  --api-key "$API_KEY"
  --served-model-name "$SERVED_MODEL_NAME"
  --trust-remote-code
  --quantization modelopt_fp4
  --dtype bfloat16
  --reasoning-parser qwen3
  --tool-call-parser qwen3_coder
  --sampling-defaults model
  --context-length "$MAX_MODEL_LEN"
  --max-running-requests "$MAX_RUNNING_REQUESTS"
  --mem-fraction-static "$MEM_FRACTION_STATIC"
  --mamba-radix-cache-strategy "$MAMBA_CACHE_STRATEGY"
  --page-size "$PAGE_SIZE"
)

if [[ "$ENABLE_MTP" == "1" ]]; then
  args+=(
    --speculative-algorithm NEXTN
    --speculative-num-steps "$SPEC_NUM_STEPS"
    --speculative-eagle-topk "$SPEC_TOPK"
    --speculative-num-draft-tokens "$SPEC_NUM_DRAFT_TOKENS"
  )
fi

exec sglang "${args[@]}"
