# Repair protocol

## Before editing

1. Verify G2 and the design contract.
2. Record at least two cross-persona baseline citations.
3. State one causal hypothesis and predicted measurable direction.
4. Select one mechanism class and a strict subset of the design allowlist.
5. Freeze the plan, source revisions, thresholds, fixed seeds, and holdouts.
6. Create an isolated worktree at the pinned baseline game commit.

## Change validation

- Generate the diff from the pinned baseline commit.
- Reject paths not in the plan allowlist.
- Reject forbidden path prefixes and symbolic-link escapes.
- Count added plus deleted lines from `git diff --numstat`.
- Reject more files or lines than the frozen budget.
- Reject changes containing seed-specific branches or the frozen seed values.
- Reject changes to tests, validators' expected values, gates, personas,
  prompts, ending classifications, or evidence files.
- Reject a diff whose actual mechanism differs from the plan.
- Save and hash `patch.diff` before any outcome verification.

## Verification order

1. Focused Godot test for the selected mechanism.
2. Baseline fixed cohort.
3. Patched fixed cohort.
4. Baseline holdout cohort.
5. Patched holdout cohort.
6. Critical invariant and content validators.
7. Target, persona preservation, designed-failure, and provider gates.

Run all four cohorts with identical personas, difficulty, scenario, weeks, and
deterministic policy. Only game source revision and seed cohort may differ.

## Decision

Accept only if fixed improvement reaches the frozen threshold, holdouts confirm
the direction, every critical invariant remains zero, protected metrics stay
inside bounds, all focused tests pass, and every artifact reparses and hashes.
Otherwise reject. A rejection is a valid experiment outcome and must keep the
failed evidence.
