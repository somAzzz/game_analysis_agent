---
status: complete
date: 2026-07-17
question: does the game report contain the user's high-pressure/burnout finding?
verdict: yes
---

# Pressure/burnout finding cross-check

## User observation

> The game's pressure preset is high and very easily causes player burnout.

## Audit verdict

**Present and confirmed.** The game report makes this its P0 conclusion and
supports it with all 150 real playthroughs. A separate “why the report missed
it” report is not required because the issue was not missed.

The observation should be stated more precisely as:

> On `normal/default_first_semester`, the forced low spendable-cash start and
> recurring deficit activate stacked arrears, hunger, and stress penalties.
> This creates a difficult-to-recover cross-persona pressure attractor and
> causes burnout or pressure-linked failure even when agents frequently select
> recovery actions.

The strongest evidence is:

- sustained burnout risk in 144/150 cells (96.00%);
- stress reaches 100 in 145/150 (96.67%);
- only 9/144 (6.25%) recover below 80 after reaching 90;
- 29 explicit `burnout_pause` endings, but another 90 higher-priority
  `cashflow_collapse` endings often co-occur with high stress;
- study, social, visa, and newbie personas show the same convergence, so the
  result is not driven only by designed-failure `slacker` behavior.

## Comparison with earlier project evidence

This is a replication and expansion, not a newly discovered defect:

- `docs/reviews/LOCAL_LLM_GAME_SYSTEM_AUDIT_20260713.md` already labeled the
  resource-pressure attractor `GAME-P0-02` and reported recovery actions failing
  to escape stress saturation.
- `docs/plans/openai_build_week_2026/IMPLEMENTATION_PLAN.md` defines the golden
  demo problem as non-failure personas converging on burnout/cashflow collapse.
- `docs/reviews/openai_build_week_2026/G2-campaign.md` recomputed burnout and
  cashflow clusters in all 18 frozen evidence cells.
- `docs/reviews/openai_build_week_2026/G3-repair.md` records that the candidate
  cashflow repair failed fixed and unseen-holdout target gates and was rejected.

The baseline still contains the problem because Playtest Forge intentionally
did not merge an unproven repair. That is correct agent behavior and an honest
competition story: the project detects the problem, attempts a bounded change,
and can reject its own ineffective patch.

## Why the problem can still look underreported

Although it was not absent from the game report, three product defects can hide
its magnitude:

1. all 150 structured campaign endings are `unknown`, while the true endings
   remain only in Markdown cell summaries;
2. `cashflow_collapse` has higher priority than `burnout_pause`, so a single
   displayed ending masks co-occurring burnout conditions;
3. the frontend displays only one cohort and has no combined 25-seed view.

Those are agent/reporting gaps. They explain why a viewer might see fewer
explicit burnout endings than the state evidence supports; they do not weaken
the game-mechanism conclusion.

