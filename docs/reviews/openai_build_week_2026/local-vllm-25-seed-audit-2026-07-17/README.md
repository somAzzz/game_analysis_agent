---
status: complete
date: 2026-07-17
scope: 25 seeds x 6 personas x nominal 20-week local-vLLM real-Godot audit
---

# Local vLLM 25-seed full-flow audit

This packet records a real end-to-end run of Playtest Forge against the pinned
`study-in-germany` demo. It is a validation of the agent project and its game
diagnosis path, not an attempt to polish or silently repair the demo.

## Reports

- [Agent report](AGENT_REPORT.md): orchestration, provider, evidence, resume,
  frontend, observability, and API-readiness findings.
- [Game report](GAME_REPORT.md): balance, pressure, cashflow, persona divergence,
  recovery, and ending findings.
- [Pressure/burnout cross-check](PRESSURE_BURNOUT_CROSSCHECK.md): independent
  comparison of the user's observation with the game report and prior Build
  Week evidence.
- [Machine-readable summary](AUDIT_METRICS.json): frozen headline metrics and
  source identities used by these reports.

## Frozen contract and result

| Field | Value |
| --- | --- |
| Provider / truth label | `vllm` / `local-vllm-real-godot` |
| Model | `qwen3.6-27b-nvfp4` |
| Personas | `newbie`, `study`, `money`, `social`, `visa`, `slacker` |
| Seeds | 42 through 66 inclusive |
| Requested duration | nominal 20-week semester |
| Recorded decisions | 19 per cell; the week-19 transition finishes state week 20 |
| Cells | 150/150 completed |
| Evidence rows | 2,850 weekly decisions |
| Successful model calls | 5,700 |
| Final validity | 100%; zero fallback and zero invalid weeks |
| Public bundle gates | A, B, and C all independently re-verified `passed` |

The repository's campaign cap is 100 cells, so the frozen 150-cell audit was
split without changing provider, model, game, difficulty, scenario, or
concurrency:

- `reports/persona-campaigns/vllm-audit-25seed-cohort-a` — seeds 42–49, 48 cells;
- `reports/persona-campaigns/vllm-audit-25seed-cohort-b` — seeds 50–57, 48 cells;
- `reports/persona-campaigns/vllm-audit-25seed-cohort-c` — seeds 58–66, 54 cells.

All three use agent commit `cb142f99b4e24470fe2aa028233aa78212393429`,
agent tree `6f86561b59348a60ddf6ce92d79cae91de1e9d87`, game commit
`348b9fd5501e71ebc7142e10f9068fc1490b5124`, game tree
`225cd5451d09bb92da674234a79ecaf8db4beb3a`, and game archive SHA-256
`2ee8ed13121a35597cad69f6fa5b03c57bfe2c3565d0dfb9f0def284110f610d`.
The source was clean when each cohort identity was frozen.

## Headline decision

The agent pipeline is evidence-safe and usable under supervision: it runs the
real game, rejects fallback/partial cells, resumes hash-compatible work, and
publishes verifiable bundles. It is not yet reliable enough for an unattended
multi-hour local campaign because the vLLM service can crash or become
generation-dead while its health endpoint remains green, and the resume UI and
usage counters misrepresent recovery.

The game finding is stronger than the user's initial hypothesis: normal/default
pressure is not merely high; coupled cashflow, hunger, and stress rules form a
cross-persona attractor. The issue is present in the game report and was already
the Build Week golden-demo target. The previous candidate repair was correctly
rejected and not merged, so the pinned baseline is expected to retain the defect.

