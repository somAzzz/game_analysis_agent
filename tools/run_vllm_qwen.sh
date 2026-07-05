#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-/models/qwen3.6-nvfp4}"
HOST="${VLLM_HOST:-127.0.0.1}"
PORT="${VLLM_PORT:-8000}"
API_KEY="${VLLM_API_KEY:-local-dev-token}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.90}"

exec vllm serve "$MODEL_ID" \
  --host "$HOST" \
  --port "$PORT" \
  --api-key "$API_KEY" \
  --dtype auto \
  --max-model-len "$MAX_MODEL_LEN" \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
  --generation-config vllm
