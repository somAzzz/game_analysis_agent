# SGLang persona plan-integrity repair — 2026-08-09

## Decision

Accept the candidate as a **plan-integrity repair**: Godot no longer silently
executes a subset of a persona's proposed actions. Keep it isolated for human
review; this workflow does not merge game changes automatically.

Reject the same candidate as a **cashflow/stress balance repair**. It improves
the fixed cohort from 18 to 14 target members and the unseen holdout from 18 to
16, but does not meet the frozen acceptance bounds. A separate, single-mechanism
experiment is required.

## Test contract and provenance

- Workflow: checked-in `playtest-forge`, with both offline `judge inspect` and
  `judge replay` passing before real-game execution.
- Frozen personas: six personas over fixed seeds `42,43,44` and unseen holdout
  seeds `1042,1043,1044` (18 cells per cohort).
- Provider: local Docker SGLang, `lmsysorg/sglang:v0.5.16-cu130-runtime`,
  Qwen3.6-27B NVFP4, no-thinking, 2048 completion tokens, MTP 3, concurrency 4.
- Engine: Docker Godot `4.4.stable.official.4c311cbee`.
- Agent implementation: commits `9b690db`, `b81a20b`, `6cc87b1`, `522dbc2`.
- Isolated game candidate: branch
  `playtest-forge/authoritative-subset-full-20260809`, commit `5b718a5`.
- Candidate patch SHA-256:
  `e74dbba08c1ec08972b3a5fc98689f967343648fd6101627b2ced3593edde104`.
- Materialized game archive SHA-256:
  `de294b7333b9b0d1d2fb88aab5e11079ea428f5c569879970e65f82e5f08294d`.
- Materialized content-tree SHA-256:
  `aa312c8bd4f11910cc84a42c418c953a1b7257796cf2140fb727c013b75c8027`.

The campaign artifacts are local generated evidence under:

`/home/bo/projects/python/gaa-authoritative-subset-runner-522dbc2/reports/authoritative-subset-20260809/persona-campaigns/`

## Cited facts

The earlier 342-decision SGLang cohort contained 108 intentionally underfilled
plans and 15 true silent-subset executions. The defect was therefore not
"persona must always fill four slots". It was that the interactive Godot probe
could accept a shorter action list than the model proposed without surfacing an
error. The silent reductions clustered in study (7) and visa (8) persona
decisions and were caused by conflicting cooldown, meal, or recovery actions.

An exact-four-slot candidate was tested first and rejected: all six seed-42
personas became partial because intentional underfill is valid game behavior.
That negative result constrained the accepted hypothesis below.

## One hypothesis and bounded diff

**Hypothesis:** require Godot's `selected_action_ids` to equal the persona's
`proposed_action_ids`, while continuing to allow intentional underfill. If the
sets differ, validate without state mutation, expose rejected IDs, and give the
model one compact deterministic repair opportunity.

The game candidate changes only:

- `scripts/tools/RunInteractiveProbe.gd`
- `scripts/tools/ValidatePlanCombinationContract.gd` (new)

The diff is 106 insertions and 1 deletion. It does not change economy values,
stress rates, endings, UI, or other simulation runners. The agent-side changes
add a non-mutating validation seam, preserve `at_most_count` for real contexts,
report accepted/rejected IDs, and use a compact temperature-zero repair prompt.
The initial decision prompt is unchanged.

## Focused test

- Frozen user-authored contract test: 4/4 passed.
- Relevant Python regression set: 75/75 passed before the final prompt-only
  refinement; the final focused set passed 33/33.
- Ruff: passed.
- Direct Godot contract:
  - conflicting four-action proposal: invalid, only two accepted internally,
    and `before_state == after_state`;
  - legal three-action proposal: valid, with selected IDs exactly equal to the
    proposed IDs.
- `ValidatePlanCombinationContract.gd`: passed.

## Fixed and holdout proof

| Cohort | Cells | Decisions | Valid | Repair weeks | Fallback/provider error | Alignment | Cashflow/stress target |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixed 42–44 | 18/18 complete | 342 | 342/342 | 1 | 0/0 | 0.725146 | 14/18 |
| Holdout 1042–1044 | 18/18 complete | 342 | 342/342 | 3 | 0/0 | 0.707602 | 16/18 |

Fixed evidence:

- campaign manifest SHA-256:
  `a17dec672110d27a32206173effdf8bc22626326ccf043d6de5dea89bf555bba`
- public summary SHA-256:
  `6bd09eccc02c1fe500fcb379b875a5f97b637ab51f3f80fcd29832cd7aea21fb`

Holdout evidence:

- campaign manifest SHA-256:
  `db9ca446bc5f076b461580d79a8f553ad08c365dec0f9ce0c1c6847175f14b02`
- public summary SHA-256:
  `2d4a24d4846733ef54a1ad66f684ed8491d3787f18f76e5bb3088968bd19cf94`

Every campaign cell completed and all 684 evaluated decisions were valid. The
automatic holdout command nevertheless exited nonzero after cell and public
artifact generation because its `FrozenRepairTarget` publication step tried to
treat the one holdout campaign's seeds as both fixed and holdout, then correctly
rejected the overlap. This is a post-processing/schema limitation, not a failed
game cell; the run summary records 18 complete, 0 partial, 0 failed, and
`submittable: true`. It is not silently counted as a passing publication gate.

## Protected gates

- Offline `judge inspect`: passed after implementation.
- Offline `judge replay`: passed after implementation.
- Godot `ValidateEconomyRules.gd`: passed.
- Godot `ValidateContent.gd`: 0 errors, 6 existing warnings.
- Godot `ValidateRiskGuidance.gd`: 9/9 scenarios passed.
- Full Python suite at the time: 552 passed and 1 environment-dependent test
  skipped.

## Acceptance and next experiment

The plan-integrity candidate is **accepted but not merged**. It satisfies its
frozen contract on fixed and unseen seeds and makes the one observed repair
week in fixed plus three in holdout explicit rather than silently changing
player intent.

It is **rejected as the cashflow/stress repair**. Against an 18-member baseline,
fixed reaches 14 (22.2% reduction, required at most 12) and holdout reaches 16
(11.1% reduction, required at least 25%, or at most 13 members when rounded to
whole campaign cells).

The next bounded experiment should use the now-authoritative action traces to
attribute weekly stress and cash deltas by channel, freeze the dominant
recurring channel, and change one parameter or rule only. The leading question
is whether ordinary recurring stress drift, hunger/recovery costs, or the cash
channel is the actual attractor; no one of these should be selected without the
new trace evidence.

## Audit chain

test contract → cited facts → interpretation → one hypothesis → bounded diff → focused test → fixed proof → holdout proof → protected gates → accepted/rejected decision → next experiment
