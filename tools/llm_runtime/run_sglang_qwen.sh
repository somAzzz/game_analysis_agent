#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-RadixArk/Qwen3.8-27B-NVFP4}"
MODEL_REVISION="${SGLANG_MODEL_REVISION:-554ebba9b5f1b79dc11246341960360e6ef05ef4}"
HOST="${SGLANG_HOST:-127.0.0.1}"
PORT="${SGLANG_PORT:-30000}"
API_KEY="${SGLANG_API_KEY:-local-dev-token}"
SERVED_MODEL_NAME="${SGLANG_MODEL:-qwen3.8-27b}"
MAX_MODEL_LEN="${LLM_MAX_MODEL_LEN:-65536}"
MAX_RUNNING_REQUESTS="${LLM_MAX_NUM_SEQS:-4}"
MEM_FRACTION_STATIC="${SGLANG_MEM_FRACTION_STATIC:-0.85}"
ATTENTION_BACKEND="${SGLANG_ATTENTION_BACKEND:-flashinfer}"
CHUNKED_PREFILL_SIZE="${SGLANG_CHUNKED_PREFILL_SIZE:-2048}"
ENABLE_APC="${SGLANG_ENABLE_APC:-1}"
MAMBA_CACHE_STRATEGY="${SGLANG_MAMBA_CACHE_STRATEGY:-extra_buffer_lazy}"
SPECULATIVE_ALGORITHM="${SGLANG_SPECULATIVE_ALGORITHM:-DFLASH}"
DRAFT_MODEL_PATH="${SGLANG_DRAFT_MODEL_PATH:-incoai/Qwen3.8-27B-DFlash2}"
DRAFT_MODEL_REVISION="${SGLANG_DRAFT_MODEL_REVISION:-dedf8df68adfb1afeaf7b7480c0a0243108177b4}"
NUM_DRAFT_TOKENS="${SGLANG_NUM_DRAFT_TOKENS:-8}"
ENABLE_METRICS="${SGLANG_ENABLE_METRICS:-1}"

args=(
  serve
  --model-path "$MODEL_ID"
  --revision "$MODEL_REVISION"
  --host "$HOST"
  --port "$PORT"
  --api-key "$API_KEY"
  --served-model-name "$SERVED_MODEL_NAME"
  --trust-remote-code
  --dtype bfloat16
  --reasoning-parser qwen3
  --tool-call-parser qwen3_coder
  --sampling-defaults model
  --context-length "$MAX_MODEL_LEN"
  --max-running-requests "$MAX_RUNNING_REQUESTS"
  --mem-fraction-static "$MEM_FRACTION_STATIC"
  --attention-backend "$ATTENTION_BACKEND"
  --chunked-prefill-size "$CHUNKED_PREFILL_SIZE"
  --mamba-radix-cache-strategy "$MAMBA_CACHE_STRATEGY"
)

if [[ "$ENABLE_APC" != "1" ]]; then
  args+=(--disable-radix-cache)
fi

if [[ "$ENABLE_METRICS" == "1" ]]; then
  args+=(--enable-metrics)
fi

if [[ "$SPECULATIVE_ALGORITHM" != "NONE" ]]; then
  args+=(
    --speculative-algorithm "$SPECULATIVE_ALGORITHM"
    --speculative-draft-model-path "$DRAFT_MODEL_PATH"
    --speculative-draft-model-revision "$DRAFT_MODEL_REVISION"
  )
  if [[ -n "$NUM_DRAFT_TOKENS" ]]; then
    args+=(--speculative-num-draft-tokens "$NUM_DRAFT_TOKENS")
  fi
fi

exec sglang "${args[@]}"
