Read the boundary probe report bundle below.

The Python pipeline has already produced:

- `boundary_runs.jsonl` — one row per extreme initial state × per run.
- A grouped summary by `extreme` label: average final week, ending
  distribution, top anomaly kinds.
- The standard balance bundle (`summary.json`,
  `ending_distribution.csv`, `weekly_stats.csv`,
  `action_pick_rates.csv`, `event_trigger_rates.csv`,
  `choice_pick_rates.csv`, `anomaly_report.md`).

Your job:

1. List every extreme where ≥ 50% of runs ended via `pipeline_stalled`,
   `unknown` ending, or a default fallback ending — those are likely
   gameplay dead-ends.
2. For each, recommend the minimum design change (scenario defaults,
   starting-state caps, action availability) that would give the player a
   realistic path forward.
3. Call out any extreme where the engine never reached a positive ending
   even after running for the full `max_weeks` weeks.

Required output structure:

# Boundary Report

## Critical Dead-Ends
## Fragile Combinations
## Numeric Drift Findings
## Recommended Hardening

Report bundle:

{{REPORT_BUNDLE}}