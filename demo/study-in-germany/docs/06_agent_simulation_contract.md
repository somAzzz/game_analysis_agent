# Agent Simulation Contract

This project exposes the game simulator as a deterministic, headless experiment environment for an external Agent analysis system.

## Current Status

Implemented:

- deterministic seed through `RandomService`
- headless batch runner
- seven policies: `random`, `balanced`, `study`, `work`, `admin`, `social`, `slacker`
- four difficulties: `easy`, `normal`, `hard`, `realistic`
- three scenarios: `default_first_semester`, `low_money_start`, `high_stress_start`
- one JSONL record per run
- weekly trace with actions, events, state snapshots, event effects, and event pool
- generated CSV metrics
- content validation report

Not implemented yet:

- replay runner
- content graph export
- external JSON content packs
- effect attribution records
- ending reason codes and near miss analysis

## Run Simulations

```bash
godot4 --headless \
  --path /Users/bo/projects/study-in-germany \
  -s res://scripts/tools/RunSimulation.gd \
  --runs=1000 \
  --policy=balanced \
  --difficulty=normal \
  --seed=42 \
  --scenario=default_first_semester \
  --weeks=20 \
  --out=reports/runs/balanced_seed42.jsonl
```

Supported policies:

- `random`
- `balanced`
- `study`
- `work`
- `admin`
- `social`
- `slacker`

Supported difficulties:

- `easy`
- `normal`
- `hard`
- `realistic`

Supported scenarios:

- `default_first_semester`
- `low_money_start`
- `high_stress_start`

The runner writes one JSON object per run to the JSONL output. Each run includes:

- `run_id`
- `seed`
- `policy`
- `difficulty`
- `content_version`
- `rules_version`
- `final_ending_id`
- `final_exam`
- `final_state`
- `weekly_log`
- `action_sequence`

Each weekly log includes:

- `before_state`
- `available_action_ids`
- `selected_action_ids`
- `action_effects`
- `life_drift_effects`
- `event_pool`
- `triggered_event_id`
- `event_choice_id`
- `event_effects`
- `event_success`
- `after_state`

## Generated Metrics

The runner writes these files next to the raw JSONL:

- `summary.json`
- `ending_distribution.csv`
- `weekly_states.csv`
- `action_pick_rates.csv`
- `event_trigger_rates.csv`

Recommended Agent usage:

- Use `raw_runs.jsonl` for causal analysis and replay case selection.
- Use `ending_distribution.csv` for difficulty and outcome balance.
- Use `weekly_states.csv` for state curve analysis.
- Use `action_pick_rates.csv` for action availability and desirability.
- Use `event_trigger_rates.csv` for event reachability and pacing.
- Use `content_validation.json` before deeper analysis.
- Use `ValidateRouteBoundaries.gd` after route-audit runs to catch policy collapse, pipeline stalls, or missing route-signature actions.

These files are the intended stable interface for the analysis Agent. The Agent should not depend on UI scenes or `Main.gd`.

The Agent should not depend on:

- `scenes/main/Main.gd`
- UI `.tscn` files
- Godot editor state
- screenshots
- ad hoc debug prints
- direct mutation of `GameState`

## Validate Content

```bash
godot4 --headless \
  --path /Users/bo/projects/study-in-germany \
  -s res://scripts/tools/ValidateContent.gd \
  --out=reports/content_validation.json
```

The validation report contains:

- duplicate id errors
- missing `next_event_id` errors
- event choice count warnings
- trigger warnings
- unknown effect stat warnings
- flags that are required but never set

## Reproducibility Rule

For the same content version, rules version, seed, policy, and max week count, `RunSimulation.gd` is expected to produce the same raw run trace.

If a future change intentionally affects simulation behavior, update `rules_version` or `content_version` in `GameState.gd` so Agent reports can compare before and after runs correctly.
