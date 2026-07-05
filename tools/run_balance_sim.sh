#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${1:-baseline}"
POLICY="${2:-balanced}"
RUNS="${RUNS:-1000}"
SEED="${SEED:-42}"
GODOT_BIN="${GODOT_BIN:-godot4}"
GODOT_PROJECT_PATH="${GODOT_PROJECT_PATH:-/Users/bo/projects/study-in-germany}"
OUT_DIR="reports/balance/${RUN_ID}"
OUT_FILE="$(pwd)/${OUT_DIR}/raw_runs.jsonl"

mkdir -p "$OUT_DIR"

"$GODOT_BIN" --headless \
  --path "$GODOT_PROJECT_PATH" \
  -s res://scripts/tools/RunBalanceSim.gd \
  --runs="$RUNS" \
  --policy="$POLICY" \
  --seed="$SEED" \
  --out="$OUT_FILE"

python3 tools/analyze_balance.py "$OUT_FILE" "$OUT_DIR"
python3 tools/generate_agent_prompt.py "$OUT_DIR"
