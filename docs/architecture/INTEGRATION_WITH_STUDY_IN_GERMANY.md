# Integration with `study-in-germany`

`game_analysis_agent` does not re-implement the simulation. The Godot
project `study-in-germany` owns the canonical simulation engine and
its deterministic runners; this project wraps them with a Python
analysis + LLM review layer.

The integration has three faces:

1. **Monte Carlo** — reuse the existing `RunSimulation.gd`.
2. **Boundary probing** — extend the same engine with a new runner
   that injects extreme scenarios.
3. **Interactive play** — wrap a single playthrough so the LLM can
   drive it step-by-step through the tool loop.

The runner scripts in `game_analysis_agent/scripts/tools/` and the
Python glue in `src/game_analysis_agent/game_tools.py` are designed to drop
into the same `study-in-germany` repository — they assume the existing
`autoload/GameState.gd` / `autoload/DataRegistry.gd` / `scripts/simulation/SimulationEngine.gd`
interfaces are present.

## 1. Monte Carlo via `RunSimulation.gd`

`study-in-germany/scripts/tools/RunSimulation.gd` already accepts:

```text
--runs=N                 runs per scenario
--policy=NAME            random | balanced | study | player
--seed=N                 base seed (run i uses base_seed + i)
--weeks=N                max weeks per run (default 20)
--difficulty=NAME        easy | normal | hard | realistic
--scenario=ID            optional path to data/scenarios/<id>.json
--out=res://path.jsonl   output file (Godot res:// or absolute)
```

`game_analysis_agent/tools/run_balance_sim.sh` and
`tools/run_gameplay_agent.py sim` both shell out to it with these
arguments. The shell script copies the resulting file from
`${HOME}/.local/share/godot/app_userdata/<project_name>/` into the
agent's `reports/balance/<run_id>/raw_runs.jsonl`.

The Python layer reads both legacy v0.1 keys (`actions`,
`event_id`, `choice_id`) and the v0.2 keys (`selected_action_ids`,
`triggered_event_id`, `event_choice_id`, `after_state`).

## 2. Boundary probing via `RunBoundaryProbe.gd`

`game_analysis_agent/scripts/tools/RunBoundaryProbe.gd` is a new runner
that picks from one of the following "extreme" scenario overlays
(applied via `GameState.apply_scenario()`):

| `--extreme=...` | Effect |
|---|---|
| `zero_money` | `money = 0` |
| `deep_debt` | `money = -1200` |
| `no_energy` | `energy = 0`, `stress = 95` |
| `all_negative` | every negative stat maxed |
| `no_language` | `language = 0`, `aps_knowledge = 0` |
| `flag_chaos` | every positive flag forced true + work / illegal flags forced true |
| `week_zero` | run starts at week -8 with full resources |
| `already_registered` | every positive flag forced true, fresh stats |

Each extreme is run N times (default 3) with the chosen policy
(`--policy` defaults to `random`). The runner emits one JSONL row per
run with `extreme`, `final_ending_id`, `final_week`, `final_state`,
`weekly_log`, and an `anomalies` array produced by the local
`AnomalyCollector.gd`.

## 3. Interactive probe via `RunInteractiveProbe.gd`

`game_analysis_agent/scripts/tools/RunInteractiveProbe.gd` consumes a
JSON plan file:

```json
{
  "command": "step",
  "weeks": 20,
  "plan": [
    {"week": 1, "action_ids": ["cook_at_home", "library_day"], "event_choice_id": ""},
    {"week": 2, "action_ids": ["problem_set"], "event_choice_id": "first_lecture.choice_01_ask_question"}
  ],
  "force_finish": false
}
```

It replays the plan from a fresh `GameState` and writes a trace JSON:

```json
{
  "finished": false,
  "final_week": 2,
  "triggered_event_id": "first_lecture",
  "event_choices": [...],
  "after_state": {...},
  "final_ending_id": "",
  "final_state": {...}
}
```

The Python `game_analysis_agent.game_tools.InteractiveProbe` accumulates a
plan in memory, flushes it through this runner once per LLM tool call,
and merges the resulting `after_state` back into the agent's view of
the world.

## Decision rationale

* We chose to leave `study-in-germany/scripts/tools/RunSimulation.gd`
  untouched. Re-implementing it in this repo would create two divergent
  copies of the runner and break the v0.2 contract.
* The `game_analysis_agent/scripts/tools/RunBalanceSim.gd` shim exists
  only to give a clean error if someone tries to use the old path; it
  forwards nothing.
* The `AnomalyCollector.gd` mirror in Godot is intentional — it lets
  each boundary probe row carry machine-readable flags without forcing
  the Python pipeline to re-scan the trace.

## Required environment

```bash
GODOT_BIN=godot4
GAME_PROJECT_PATH=/home/bo/projects/python/study-in-germany
```

Both are read by `game_analysis_agent.settings.Settings` and overridable
through the corresponding env vars. See `.env.example`.