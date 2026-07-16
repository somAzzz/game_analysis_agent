#!/usr/bin/env bash
# run_balance_sim.sh — thin wrapper around study-in-germany's
# `scripts/tools/RunSimulation.gd`. Hard-coded macOS paths from earlier
# revisions are gone; everything is read from environment variables.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

RUN_ID="${1:-baseline}"
POLICY="${2:-${SIM_POLICY:-balanced}}"
RUNS="${RUNS:-${SIM_RUNS:-100}}"
SEED="${SEED:-${SIM_SEED:-42}}"
WEEKS="${WEEKS:-${SIM_WEEKS:-20}}"
DIFFICULTY="${DIFFICULTY:-${SIM_DIFFICULTY:-normal}}"
GODOT_BIN="${GODOT_BIN:-godot4}"
CANONICAL_GAME="$ROOT/demo/study-in-germany"
if [ -z "${GAME_PROJECT_PATH:-}" ]; then
  GAME_PROJECT_PATH="$ROOT/reports/runtime/balance-sim-game"
  (cd "$ROOT" && uv run python tools/prepare_embedded_demo.py \
    --output "$GAME_PROJECT_PATH" --replace --json >/dev/null)
fi
if [ "$(cd "$GAME_PROJECT_PATH" 2>/dev/null && pwd)" = "$CANONICAL_GAME" ]; then
  echo "Refusing to run Godot inside the canonical embedded demo; use a writable runtime." >&2
  exit 2
fi

OUT_DIR="$ROOT/reports/balance/${RUN_ID}"
mkdir -p "$OUT_DIR"
OUT_FILE="${OUT_DIR}/raw_runs.jsonl"

if [ ! -d "$GAME_PROJECT_PATH" ]; then
  echo "GAME_PROJECT_PATH does not exist: $GAME_PROJECT_PATH" >&2
  echo "Set GAME_PROJECT_PATH to a Study in Germany Godot project." >&2
  exit 2
fi

"$GODOT_BIN" --headless \
  --path "$GAME_PROJECT_PATH" \
  -s res://scripts/tools/RunSimulation.gd \
  --runs="$RUNS" \
  --policy="$POLICY" \
  --seed="$SEED" \
  --weeks="$WEEKS" \
  --difficulty="$DIFFICULTY" \
  --out="res://balance_runs.jsonl" || {
    echo "Godot simulation runner failed" >&2
    exit 3
  }

# study-in-germany writes to `res://balance_runs.jsonl` (user-relative).
# We re-export it to our OUT_FILE in the cwd.
GLOBAL_USER_DIR="${HOME}/.local/share/godot/app_userdata/${GAME_PROJECT_PATH##*/}"
RES_PATH="${GLOBAL_USER_DIR}/balance_runs.jsonl"
if [ -f "$RES_PATH" ]; then
  cp "$RES_PATH" "$OUT_FILE"
elif [ -f "$GAME_PROJECT_PATH/balance_runs.jsonl" ]; then
  cp "$GAME_PROJECT_PATH/balance_runs.jsonl" "$OUT_FILE"
else
  echo "Could not locate Godot output (looked in $RES_PATH and $GAME_PROJECT_PATH)" >&2
  exit 4
fi

python3 "$ROOT/tools/analyze_balance.py" "$OUT_FILE" "$OUT_DIR"
python3 "$ROOT/tools/generate_agent_prompt.py" "$OUT_DIR" balance

echo "Wrote simulation artifacts to $OUT_DIR"
