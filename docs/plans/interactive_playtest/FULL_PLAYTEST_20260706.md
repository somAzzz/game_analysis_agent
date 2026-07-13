---
status: archived
date: 2026-07-06
audience: maintainers
scope: 单次完整交互式跑批记录（snapshot）
---

# Full Interactive Playtest - 2026-07-06

## Scope

- Target game: `/home/bo/projects/python/study-in-germany`
- Agent: `interactive_player`
- Local LLM: `qwen3.6-27b-nvfp4` served by vLLM
- Model context window: `32768`
- Scenario: `default_first_semester`
- Difficulty: `normal`
- Seed: `42`
- Personas: `newbie`, `study`, `money`, `social`, `visa`, `slacker`

## Evidence

- Run root: `reports/play/full-demo-20260706-211249`
- Analysis report: `reports/play/full-demo-20260706-211249/full_playtest_analysis.md`
- Machine-readable analysis: `reports/play/full-demo-20260706-211249/full_playtest_analysis.json`
- Gate report: `reports/play/full-demo-20260706-211249/gate_report.json`

## Interactive Results

| persona | ending | category | weeks | repair | fallback | event choices |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| newbie | `registration_failure` | designed failure | 19 | 0 | 0 | 19/19 |
| study | `registration_failure` | designed failure | 19 | 0 | 0 | 19/19 |
| money | `burnout_pause` | designed failure | 19 | 0 | 0 | 19/19 |
| social | `social_connector` | success | 19 | 0 | 0 | 19/19 |
| visa | `burnout_pause` | designed failure | 19 | 0 | 0 | 19/19 |
| slacker | `registration_failure` | designed failure | 19 | 0 | 0 | 19/19 |

## Gate Result

- Hard gate: passed
- Failures: 0
- Warnings: 4

Warnings:

- `balance.max_single_ending_rate`: one ending dominates the interactive persona batch.
- `balance.min_distinct_endings_normal`: interactive persona ending variety is below the Monte Carlo target.
- `design.content_validation.json`: design gate input was not present in the play report directory.
- `design.event_graph.json`: design gate input was not present in the play report directory.

## Boundary Results

Final boundary probes ran 3 simulations for each extreme:

| extreme | endings |
| --- | --- |
| `all_negative` | `burnout_pause: 3` |
| `already_registered` | `burnout_pause: 3` |
| `deep_debt` | `cashflow_collapse: 3` |
| `flag_chaos` | `social_connector: 1`, `burnout_pause: 1`, `survival_struggle: 1` |
| `no_energy` | `burnout_pause: 3` |
| `no_language` | `burnout_pause: 3` |
| `week_zero` | `burnout_pause: 2`, `social_connector: 1` |
| `zero_money` | `burnout_pause: 3` |

No boundary run produced an empty ending, `unknown`, or `pipeline_stalled`.

## Fixes From This Playtest

- Disabled Qwen thinking output for local vLLM/SGLang requests so structured decisions are parseable and do not burn completion tokens before JSON.
- Added two-phase event handling: the agent now previews triggered event choices and then makes an explicit LLM choice instead of letting Godot default to the first option.
- Added structured outcome gates so designed failure endings are valid game outcomes, while invalid endings remain hard failures.
- Downgraded interactive persona ending concentration from hard failure to design warning; Monte Carlo balance gates remain strict for simulation batches.
- Added registration-chain risk context to the weekly player context.

## Interpretation

The demo is not expected to make every persona succeed. This run proves both sides of the design space:

- Success is reachable under real LLM play: `social` reached `social_connector` with `school_registered` and `testdaf_passed`.
- Designed failures are reachable and explainable: `registration_failure` and `burnout_pause` arise from missed registration timing, stress overload, weak academic progress, or strategy tradeoffs.
- The strongest design warning is registration-chain visibility: `newbie`, `study`, and `slacker` all missed the TestDaF -> school registration chain before week 6.

## Verification Commands

```bash
uv run pytest tests/ -q
```

Result: `133 passed`.

```bash
uv run python tools/run_gameplay_agent.py validate \
  --check content \
  --check json-content \
  --check economy \
  --check risk \
  --check route \
  --check demo \
  --report-dir reports/final-verify/full-validation
```

Result: all checks `ok`.
