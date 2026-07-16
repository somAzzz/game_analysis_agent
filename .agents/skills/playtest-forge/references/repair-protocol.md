# Repair protocol

## Before editing

1. Verify the test/evidence bundle and design intent independently.
2. Record cross-seed and, when relevant, cross-persona citations.
3. State one causal hypothesis, predicted direction, protected metrics, and
   explicit rejection evidence.
4. Select one mechanism class and the smallest source/parameter allowlist.
5. Freeze source revision, fixed seeds, unseen holdouts, thresholds, file/line
   budget, runtime/provider contract, and artifact locations.
6. Create an isolated worktree at the pinned baseline revision.

## Change validation

- Generate the diff from the pinned baseline and hash it before outcome tests.
- Reject paths outside the plan or through symlink/traversal escapes.
- Reject excess files/lines and changes to forbidden verification areas.
- Reject seed-specific branches and literal use of frozen test seeds.
- Reject changes to tests, gates, personas, prompts, evidence, outcome labels,
  or thresholds made to help the candidate.
- Reject a diff whose actual mechanism differs from the frozen plan.

## Verification order

1. Focused engine/unit test for the selected mechanism.
2. Baseline fixed cohort.
3. Patched fixed cohort.
4. Baseline holdout cohort.
5. Patched holdout cohort.
6. Critical invariants and content/contract validators.
7. Target, persona/strategy preservation, designed-failure, validity,
   fallback, and provider gates.

Use identical scenario, difficulty, duration, persona/action policy, schemas,
and aggregation in all four cohorts. Only revision and declared seed cohort may
differ.

## Decision

Accept only if fixed improvement reaches the frozen threshold, holdouts confirm
direction, focused tests pass, critical invariants remain clean, protected
metrics stay bounded, intentional failure remains possible, and all artifacts
reparse and hash. Otherwise reject and retain the failed experiment.

For this repository, run `scripts/verify-repair`. On another project, use the
typed verifier declared in its project profile; never assume this wrapper is
portable.
