---
name: playtest-forge
description: Diagnose the committed Playtest Forge persona campaign, form one evidence-cited causal hypothesis, make one budgeted game-mechanism change in an isolated worktree, and accept or reject it using fixed-seed and unseen-holdout proof. Use for Build Week game balance repair, campaign failure analysis, causal patch experiments, or verification of a candidate study-in-germany gameplay fix.
---

# Playtest Forge

Run one auditable repair experiment. Preserve the distinction between observed
facts, inference, and verified outcomes. Never optimize a patch only for the
recorded seeds or force acceptance.

## Required workflow

1. Run `scripts/preflight`. Stop if it fails.
2. Read `references/design-contract.md` before inspecting candidate game source.
3. Read `references/evidence-contract.md`, then inspect the public campaign and
   cite exact artifact paths, rows, fields, and hashes.
4. State one falsifiable hypothesis and one predicted effect. Do not name a
   source change until the evidence facts are explicit.
5. Read `references/repair-protocol.md` before editing.
6. Create the typed experiment plan before the patch. Select exactly one
   allowed mechanism class and copy the frozen fixed and holdout seeds.
7. Create an isolated game worktree from the pinned baseline commit. Never edit
   the canonical baseline bundle in place.
8. Restrict edits to the plan allowlist and change budget. Do not modify tests,
   gates, personas, prompts, evidence, or target thresholds.
9. Save `patch.diff` before verification. Fail if its paths, file count, line
   count, or mechanism differ from the plan.
10. Run focused deterministic tests first.
11. Run baseline and patch with identical fixed seeds, then baseline and patch
    with the frozen unseen holdouts. Use the same persona policy and schemas in
    all four cohorts.
12. Run `scripts/verify-repair`. Evaluate target, critical invariant, persona,
    designed-failure, validity, fallback, and provider-error gates.
13. Write `accepted` only when every required gate passes. Otherwise preserve
    all evidence and write `rejected` with the exact reason.

## Non-negotiable boundaries

- Treat designed failure endings as valid outcomes; the `slacker` persona is
  intentionally failure-seeking and is not required to win.
- Never weaken a test, gate, persona, prompt, or evidence threshold.
- Never use patched results to revise the hypothesis, holdouts, or acceptance
  thresholds for the same experiment.
- Never present Replay as an OpenAI live result or a partial cohort as proof.
- Never automatically merge or silently copy an accepted patch into baseline.
- Do not build an MCP adapter and do not expose argparse `cmd_*` functions as
  tools. This Skill orchestrates repository scripts and typed services only.
- Retain the Codex task reference, actual model identifier, and `/feedback`
  Session ID. Never invent missing provenance.

## Outputs

Produce the complete experiment artifacts defined in
`references/evidence-contract.md`. End with a concise facts → hypothesis → diff
→ fixed proof → holdout proof → accepted/rejected summary.
