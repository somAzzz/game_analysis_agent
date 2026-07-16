# Test strategy selection

Use the smallest combination that can answer the question, but keep a
deterministic proof layer for every source change.

| Layer | Best for | Weakness | Truth label |
| --- | --- | --- | --- |
| Deterministic automation | State coverage, invariants, seed matrices, sensitivity, regression | Limited behavioral meaning | `automated` |
| Live persona worker | Intent diversity, choice plausibility, exploration, qualitative explanation | Stochastic, costly, provider-dependent | `live` |
| Recorded Replay | Repeatable judging, debugging, no-key environments | Cannot prove a fresh model/game execution | `prerecorded` |
| Focused engine test | Local mechanic correctness | Does not prove player-level impact | `focused` |

## Default hybrid

1. Automation discovers reproducible state patterns.
2. Persona workers test whether different intents encounter or respond to the
   pattern differently.
3. Codex forms one causal hypothesis from cited evidence.
4. Focused tests validate implementation legality.
5. Automated fixed/holdout A/B decides the repair.
6. Persona replay or a bounded live rerun checks behavioral preservation.

Do not use stochastic playthroughs to replace invariant checks, and do not use
scripted coverage alone to claim realistic player behavior.

Before running, freeze provider, actual model, prompt/profile revision, action
schema, fallback policy, retry limit, concurrency, maximum calls/weeks, and
failure semantics. If provider behavior changes mid-cohort, mark the affected
cells failed or partial rather than mixing them into a passing aggregate.
