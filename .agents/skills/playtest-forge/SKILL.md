---
name: playtest-forge
description: Turn automated game tests and persona/subagent playthrough evidence into bounded, auditable game changes, then accept or reject them with fixed and unseen-holdout proof. Use when Codex needs to review game balance, economy, progression, content routes, choices, endings, boundary behavior, invariants, player-persona divergence, parameter tuning, causal repair experiments, or migration of the testing-and-repair workflow to another game or engine.
---

# Playtest Forge

Act as the main game-review and repair agent. Let automated tests establish
state truth, let persona workers expose behavioral intent, and let deterministic
gates decide whether a change survives. Never optimize toward acceptance.

## Route the task

Read only the references required for the request:

- Choose test layers or distinguish Replay/live evidence: `references/test-strategy.md`.
- Run deterministic matrices, simulations, sweeps, or regression tests:
  `references/automated-testing.md`.
- Run live LLM/Codex persona playthroughs: `references/subagent-playthrough.md`.
- Convert observed metrics into a parameter or mechanism change:
  `references/evidence-to-parameters.md`.
- Review economy, resource pressure, difficulty, or progression:
  `references/scenario-balance-economy.md`.
- Review events, choices, routes, quests, or endings:
  `references/scenario-content-flow.md`.
- Review limits, invalid state, exploit, or invariant behavior:
  `references/scenario-boundary-robustness.md`.
- Plan and verify a source/parameter change: `references/repair-protocol.md`.
- Define citations, artifacts, schemas, and public evidence:
  `references/evidence-contract.md`.
- Adapt the Skill to another project or engine: `references/migration-guide.md`.
- Work on this repository's Build Week case: `references/design-contract.md`.
- Explain the retained cashflow repair example: `references/session-case-study.md`.

## Core workflow

1. Discover the game adapter, runtime, contracts, source revision, tests,
   telemetry, and writable report locations. Do not assume Godot or this repo.
2. Freeze a test contract before interpreting results: scenarios, personas,
   seeds, duration, parameters, outcomes, invariants, designed failures,
   protected metrics, completeness rules, and provider truth labels.
3. Establish a deterministic baseline first. Use automated testing for state
   coverage, reproducibility, sensitivity, and regression truth.
4. Add persona/subagent playthroughs when semantic choice quality, exploration,
   or distinct player intent matters. Keep the action schema and game runtime
   shared with automation. Label live, Replay, partial, and failed runs.
5. Reject incomplete, stale, schema-invalid, fallback-obscured, or
   provider-error evidence before diagnosis.
6. Separate observed facts, interpretation, and hypothesis. Cite the exact
   run/seed/week/field or row hash behind every repair-driving fact.
7. Select one failure cluster or protected objective. Prefer cross-persona and
   cross-seed evidence; preserve intentionally difficult or failing styles.
8. Map the symptom to the closest controllable mechanic and parameter. State
   one falsifiable hypothesis and predicted metric direction before editing.
9. Freeze fixed seeds, unseen holdouts, thresholds, change allowlist, file/line
   budget, and one mechanism class. Create an isolated game worktree.
10. Make the smallest change that tests the mechanism. Never modify prompts,
    personas, tests, gates, evidence, seeds, or target thresholds to manufacture
    improvement.
11. Run focused deterministic tests, fixed baseline/patch A/B, unseen holdout
    baseline/patch A/B, critical invariants, persona preservation, designed
    failure, and provider-health gates—in that order.
12. Write `accepted` only when every frozen gate passes. Otherwise preserve the
    evidence and write `rejected` with the failed causal or safety gates.

## Evidence-to-edit rules

- Convergence across unlike personas suggests a shared game mechanic before a
  persona prompt problem.
- One-persona failure suggests strategy, affordance, or route-specific logic
  before a global parameter change.
- Broken invariants outrank balance tuning. Repair correctness first.
- A symptom metric improving while the target outcome is unchanged is not a
  successful repair; reject and revisit the causal chain.
- Fixed improvement without holdout confirmation is overfit.
- Eliminating designed-failure outcomes is overcorrection.
- Unreachable content suggests trigger/graph conditions before reward tuning.
- Floor/ceiling saturation suggests scale, clamp, or update-order analysis.
- Non-monotonic responses require a sensitivity sweep before a direct patch.

## Boundaries

- Persona workers may choose actions and explain intent; only the main Codex
  agent may inspect private source, plan edits, change code, and judge release.
- Replay proves reproducibility, not a fresh model call. Never relabel it live.
- Never accept a partial cohort, silently fall back after a provider failure,
  or merge a patch automatically.
- Do not build an MCP adapter or wrap argparse `cmd_*` functions. Use typed,
  transport-independent services and repository scripts.
- Retain actual provider/model/runtime/source provenance. Never invent a key,
  token count, cost, session ID, platform result, or live execution.

## Output

End with: test contract → cited facts → interpretation → one hypothesis →
bounded diff → focused test → fixed proof → holdout proof → protected gates →
accepted/rejected decision → next experiment. State which results came from
automation, live persona workers, or Replay.
