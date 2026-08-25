# SGLang unseen-seed quality decision and repair proof

Date: 2026-08-09
Status: generation default accepted; game candidate rejected and not merged

## Test contract

The paired generation experiment used local SGLang with
`qwen3.6-27b-nvfp4`, Docker Godot 4.4, MTP steps 3, the same six personas,
seeds 142/143/144, 20 requested weeks, concurrency 4, and no resume. Only the
generation profile changed: `thinking-5120` versus `no-thinking-2048`.

Both arms had to complete 18/18 cells with 100% valid decisions, zero fallback,
and zero provider errors. The frozen non-inferiority limits for no-thinking
were no more than a two-point decline in aggregate persona alignment or risk
acknowledgement and no more than a 0.05 decline in mean pairwise persona action
TV. Persona-local deltas were inspected separately.

The repair experiment retained fixed seeds 42/43/44 and unseen holdouts
1042/1043/1044. It used the hash-locked reference design contract and the
deterministic `fixture-authoring-policy-v1` against real Docker Godot.

## Paired generation result

| Metric | thinking-5120 | no-thinking-2048 | no-thinking delta |
| --- | ---: | ---: | ---: |
| Completed cells / decisions | 18 / 342 | 18 / 342 | equal |
| Valid / fallback / provider error | 100% / 0% / 0% | 100% / 0% / 0% | equal |
| First-pass parsed decisions | 337/342 | 342/342 | +5 |
| Repair weeks | 5 | 0 | -5 |
| Persona alignment | 69.59% | 74.85% | +5.26 pp |
| Risk acknowledgement | 29.82% | 45.03% | +15.20 pp |
| Mean pairwise persona action TV | 0.305 | 0.359 | +0.054 |
| Decision output tokens | 1,108,478 | 47,403 | -95.7% |
| Decision latency p50 / p95 | 27.353 / 41.627 s | 3.088 / 4.896 s | lower |
| Decision outputs at least 5,100 / 2,040 tokens | 5 | 0 | -5 |

No-thinking passed every frozen aggregate gate and improved behavioral
divergence. Its known local exception is the money persona: alignment declined
from 50.88% to 35.09% (-15.79 pp); visa declined by 3.51 pp. Social and study
improved materially, newbie remained near-perfect, and slacker remained 100%.
The general six-persona default is therefore `no-thinking-2048`, while
`thinking-5120` remains an explicit diagnostic option for money-focused audits
or future paired revalidation.

The sanitized gate reports are retained locally under:

- `reports/persona-campaigns/sglang-quality-qa-142-144-thinking-5120/public/`
  (`campaign_summary.json` SHA-256 `53f9c9b6...621ae624`);
- `reports/persona-campaigns/sglang-quality-qa-142-144-no-thinking-2048/public/`
  (`campaign_summary.json` SHA-256 `337ca9b6...b96f91a`).

## Bounded game candidate

Both generation arms independently reproduced the selected cashflow/stress
attractor (14/18 thinking cells and 15/18 no-thinking cells). Prior governed
experiments had already rejected blocked-account smoothing and a one-action
recovery buff. The new locked hypothesis tested only a normal-difficulty
recurring living-cost reduction while preserving rent, blocked-account totals,
personas, prompts, tests, gates, and endings.

Sensitivity at 35, 55, and 75 EUR relief per week produced 6/6 target members
on seed 42 in every variant. The 75 EUR candidate did execute mechanically—it
reduced the representative money trajectory's final arrears from 3,197 to
2,437—but did not change the target, ending, or stress saturation. The locked
candidate changed two allowlisted files by nine added lines; patch SHA-256 is
`dd10468e...b8014ffb` and its isolated commit is `fa04cb5`.

Formal proof confirmed the sensitivity result:

| Cohort | Baseline target | Patched target | Reduction |
| --- | ---: | ---: | ---: |
| Fixed 42/43/44 | 18/18 | 18/18 | 0% |
| Holdout 1042/1043/1044 | 18/18 | 18/18 | 0% |

Critical invariants, validity, provider health, persona preservation, invalid
ending protection, and designed-failure preservation passed. `fixed_target`,
`holdout_target`, `non_failure_persona_improvement`, and `balance_quality`
failed. The proof record SHA-256 is
`b64d5bb1...086ea9`; the candidate is rejected and remains isolated.

## Decision and next experiment

The generation-mode task is accepted and implemented. The attempted game
mechanism repair is completed as a rejected experiment, not represented as a
fix. The three currently allowed single-mechanism classes now all have negative
causal evidence. A next repair needs an approved contract expansion based on a
cumulative pressure-channel trace (weekly drift, action stress, hunger,
arrears, and event costs) and must also address the deterministic proof
policy's zero persona-route distance before another game patch is attempted.
