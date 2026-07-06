# Real Test Gap Analysis

Date: 2026-07-06

This document compares `game_analysis_agent` with the adjacent
`/home/bo/projects/python/study-in-germany` Godot project and records the
remaining gap between the current agent pipeline and a real game-test
workflow.

## Current Shape

The agent already covers the central report loop:

```text
Godot RunSimulation.gd
-> raw_runs.jsonl
-> Python analytics / anomalies / value analysis
-> LLM diagnosis and design review
```

The missing layer is test orchestration: Godot already exposes scenarios,
validators, demo gates, route-boundary checks, risk-guidance checks, and
economy rules, but the agent has not treated those as first-class test
capabilities.

## Gaps

| Gap | Why it matters | Required capability |
| --- | --- | --- |
| Policy names drift | Godot uses `work` / `admin`; earlier agent docs used `money` / `visa`. | Canonical aliases so CLI and matrix run the intended route. |
| Scenario is not a matrix dimension | Low-money and high-stress starts are where demo regressions appear. | `--scenario` for `sim/all`, plus scenario rows in `matrix.yaml`. |
| Godot validators are not orchestrated | Content/economy/risk/route/demo gates live in Godot but are not part of agent runs. | A `validate` command that runs those scripts and collects reports. |
| YAML gates are not executable | `config/gates.yaml` documents thresholds but cannot fail a run. | A deterministic `gates` evaluator. |
| Weak replay evidence | An anomaly says what failed but not enough about how to reproduce. | Seed/week/action/event replay evidence on anomaly rows. |
| No state-space coverage report | Endings and action rates do not show whether crisis states were exercised. | `coverage_report.json` with crisis/state/event coverage. |
| Risk guidance is not analyzed | Real players react to visible risks, not raw hidden state. | Export or ingest top-risk guidance per week and compare to choices. |
| Interactive player is still a policy proxy | LLM sees catalog/state, not the full player-facing UI context. | Feed current available actions, event choice text, risk hints, and UI labels. |
| Before/after experiments are manual | `compare_reports.py` exists but does not run fixed-seed experiment pairs. | Matrix runner + compare wrapper. |

## Implemented In This Pass

The first batch focuses on deterministic, low-risk infrastructure:

1. Canonical policy aliasing: `money -> work`, `visa -> admin`.
2. Scenario support in `sim/all`.
3. `validate` CLI for Godot validators.
4. `gates` CLI for `config/gates.yaml`.
5. `coverage_report.json` emitted during `analyze`.
6. Replay evidence attached to anomaly rows.

## Still Deferred

- Risk-guidance ingestion into each weekly run record.
- Full UI-context interactive play.
- Fixed-seed before/after experiment orchestration.
- HTML dashboard.
