---
status: complete
date: 2026-07-17
system: game-analysis-agent
verdict: supervised-use-ready, unattended-long-run-not-ready
---

# Agent report — 150-cell local-vLLM real-Godot audit

## Executive verdict

`game-analysis-agent` completed all 150 requested persona/seed cells with real
Godot and real local-model decisions. The retained evidence is strong: 2,850
weekly rows, 5,700 successful calls, 100% valid decisions, no fallback, exact
source identities, and three independently passing public bundle gates.

The project is suitable for supervised local rehearsal and small live-API
campaigns. It is not yet suitable for an unattended 25-seed local run. The
long run exposed repeatable provider-runtime failures, a healthcheck that cannot
detect stuck generation, misleading resume/progress presentation, incomplete
usage accounting, and loss of final endings in structured evidence.

## What passed

- Real-game execution used the Docker Godot 4.4 wrapper and the audited runtime
  overlay; no Replay or scripted-provider substitution occurred.
- All final cells are `completed`; the bundle builders rejected every transient
  partial result before publication.
- Final campaign metrics report `valid_rate=1.0`, `fallback_rate=0.0`, and
  `provider_error_rate=0.0` for retained evidence.
- Only one of 5,700 successful calls required a second attempt/schema repair;
  all other responses parsed on attempt one.
- Successful-call latency was 2.77 s mean, 2.73 s p50, 5.60 s p95, 8.62 s p99,
  and 18.22 s maximum.
- Successful calls consumed 11,109,541 input tokens and 335,195 output tokens
  (11,444,736 total local tokens).
- The same agent/game/model identities survived resume. Completed cells were
  reused only when request and source hashes matched.
- The frontend session file updated during each cohort, and final public bundles
  passed schema, identity, hash, expected-cell, completed-cell, and public-safety
  checks.

## Findings

### AGENT-P0-01 — Local vLLM is not stable for a multi-hour four-way campaign

The first A attempt ended 41 completed / 7 partial after a confirmed vLLM 0.25.0
CUDA Graph segfault and automatic restart. B ended 42 / 6 partial before resume.
C entered a half-alive state: `/v1/models` remained healthy while one generation
request reported 0 tokens/s for several minutes; a manual restart caused four
in-flight cells to finish as partial. Across first attempts, 17 cells therefore
required a governed retry.

All 17 were recovered with the exact campaign identity and the final 150-cell
evidence is valid. That demonstrates evidence integrity, not unattended runtime
reliability. Before relying on the local provider for exhibition-scale runs:

1. add a bounded generation canary/watchdog, not only a model-list healthcheck;
2. test `LLM_ENABLE_MTP=0` and an exposed vLLM eager-mode option in controlled
   A/B runs, because the confirmed crash stack traversed CUDA Graph replay;
3. classify and retain provider incidents separately from final cell evidence;
4. make the client timeout configurable and shorter than the current 600 s for
   bounded campaign traffic.

Do not infer that MTP or CUDA Graph is the sole cause until the controlled A/B
run is performed. The current source identity records only the served model,
not the vLLM image, MTP flag, eager/graph mode, driver, or GPU revision.

### AGENT-P0-02 — Final endings are lost from structured campaign evidence

Every one of the 150 `playthrough_summary.md` files contains a real final
ending, but all 150 cells in the three `campaign_summary.json` files report
`ending: unknown`. The ending exists only after `probe.finish()` and is written
to Markdown; it is not persisted into a structured final-result field consumed
by `campaign_aggregation._ending()`.

This is a correctness issue, not presentation polish. The missing field hides
90 `cashflow_collapse`, 29 `burnout_pause`, 21 `living_imbalance`, and the other
real outcomes from the frontend and deterministic aggregate. Add a structured
final record or final-state artifact, include it in citation/hash verification,
and make unknown ending a failed gate for a normally finished game.

### AGENT-P1-03 — Resume progress presents reused successes as pending

On every resume, `_CampaignSessionPublisher` initialized all cells as pending.
The runner correctly reused hash-compatible completed cells, but the frontend
showed those cells as pending until finalization. Examples:

- A retry actually ran 7 cells while the UI initially showed 41 other cells as
  pending;
- B retry actually ran 6 while 42 were shown pending;
- C retry actually ran 4 while 50 were shown pending.

Hydrate the session publisher from resumable `cell_result.json` files before
launching pending futures. Expose separate `reused_cells`, `retried_cells`, and
`new_cells` counters.

### AGENT-P1-04 — Running progress can overclaim completion before finalization

Before A, B, and C finalization, weekly callbacks marked cells `completed` when
Godot had finished even if a provider error had occurred earlier in the same
cell. Finalization correctly downgraded them to partial: A briefly appeared more
complete before ending 41/7, B ended 42/6, and C displayed 52 completed before
ending 50/4.

Running UI states should say `game_finished_pending_validation`; only the cell
result validator may publish `completed`.

### AGENT-P1-05 — Usage accounting resets across resume

The final command responses reported `calls_used` 266 for A, 228 for B, and 152
for C because the gateway counter covered only the retry process. The verified
public bundles contain 1,824, 1,824, and 2,052 successful calls respectively,
5,700 total, plus the failed in-flight attempts that were overwritten on retry.

Persist campaign-level usage atomically across attempts and distinguish
successful, failed, retried, and resumed calls. This is essential before using
a paid OpenAI campaign; a retry must not make spend appear smaller.

### AGENT-P1-06 — Provider health and provenance are too shallow

The Compose healthcheck calls only `/v1/models`, so C remained green while
generation was dead. In addition, `provider_revision` is only
`model:qwen3.6-27b-nvfp4`. It cannot reproduce or compare the runtime conditions
that matter for this incident.

Record sanitized engine provenance: image digest/version, served checkpoint,
quantization, speculative decoding setting, graph/eager mode, max context,
concurrency, GPU/driver family, and restart count. A live OpenAI run should
analogously retain model snapshot/revision and relevant request configuration.

### AGENT-P1-07 — Default runtime preparation is not repeat-run safe

The initial wrapper invocation failed before any model call with
`refusing to replace a runtime containing unmanaged files`. When
`GAME_PROJECT_PATH` is unset, `scripts/run-persona-campaign` always calls the
embedded-demo preparer with `--replace`, but prior real-game runs leave generated
reports inside that runtime. A new isolated runtime path was required.

Give each campaign a dedicated runtime or keep generated reports outside the
materialized game. Do not weaken the unmanaged-file safety check.

### AGENT-P1-08 — The full audit cannot be represented as one campaign/view

The 100-cell safety cap required a 150-cell audit to be split into three
cohorts. That cap is reasonable, but the product has no first-class parent audit
manifest or deterministic multi-cohort aggregate. The frontend only shows the
latest cohort, and each cohort independently declares a repair target.

Add a parent audit contract that pins child request/source fingerprints,
re-verifies their gates, combines metrics without duplicating cells, and lets
the frontend select cohort or combined view. Keep per-campaign resource caps.

### AGENT-P2-09 — Nominal-week progress denominator never reaches 100%

The product documentation correctly permits 19 decisions when the week-19
transition finishes state week 20. The session publisher nevertheless uses
`cells × max_weeks` as its denominator: 3,000 requested weeks versus 2,850 valid
decision rows. A successful campaign therefore appears stuck at 95% by weeks.

Show both `semester_state_week=20` and `decision_rows=19`, or calculate progress
from terminal cells rather than assuming one decision per nominal week.

### AGENT-P2-10 — Anomaly output is dominated by repeated historical findings

The 2,850 rows contain 4,429 anomaly occurrences. Deduplicating `kind+message`
within each cell leaves 904 unique findings: 3,525 occurrences (79.59%) are
repeated historical messages. The raw total is dominated by
`single_week_spike` (3,875) and `hunger_ignored_too_long` (554).

Persist first occurrence plus duration/latest week, or attach a stable anomaly
ID and update it, rather than re-emitting the same accumulated history every
week.

### AGENT-P2-11 — Newbie alignment is not a meaningful comparable metric

Mean persona-alignment rates were newbie 0.0000, study 0.9600, money 0.5095,
social 0.9853, visa 0.9284, and slacker 1.0000. The newbie strategy has no
action-tag target that the current overlap metric can satisfy, so its 0% is a
metric-definition artifact rather than proof of total behavioral failure.

Define a newbie rubric (exploration, risk-learning, and adaptation) or report
alignment as not-applicable. Do not average the current 0% into a release claim.

## Live OpenAI implications

The local and OpenAI providers share campaign scheduling, Godot execution,
validation, evidence, resume, and frontend code, so findings P0-02 and P1-03
through P2-11 also affect live API runs. The CUDA/vLLM engine failures are local
provider-specific, but the 600 s timeout, usage accounting, incident retention,
and health semantics still matter for paid traffic.

Before a paid full campaign, fix structured endings and cumulative usage, then
run one strategy/one seed and the six-strategy/one-seed profile. A live failure
must remain fail-closed and resumable; never substitute Replay or local vLLM.

## Final disposition

- Evidence integrity: **pass**.
- Real Godot and local-provider integration: **pass**.
- Supervised campaign usability: **pass with recorded limitations**.
- Unattended multi-hour local reliability: **fail pending P0/P1 fixes**.
- Paid full-matrix readiness: **conditional on ending and usage-accounting
  fixes, followed by a bounded live validation**.

