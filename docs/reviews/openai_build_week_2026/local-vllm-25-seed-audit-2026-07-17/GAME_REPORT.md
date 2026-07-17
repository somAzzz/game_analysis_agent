---
status: complete
date: 2026-07-17
system: study-in-germany-demo
verdict: pressure-cashflow-attractor-confirmed
---

# Game report — 25 seeds, 6 personas, nominal 20-week semester

## Executive verdict

The user's observation is confirmed: pressure is too high on the
`normal/default_first_semester` baseline and very easily produces burnout.
More precisely, the defect is a coupled cashflow–hunger–stress attractor, not a
single high starting stress value.

Across 150 real local-LLM playthroughs:

- 144/150 cells (96.00%) entered sustained burnout risk: stress at least 90 for
  two consecutive decision weeks;
- 131/150 (87.33%) entered the cashflow-stress attractor: money at most 0 and
  stress at least 80 for two consecutive weeks;
- 145/150 (96.67%) reached stress 100 at least once;
- mean maximum stress was 99.78;
- median first sustained-burnout entry was week 9;
- only 9/144 high-stress cells (6.25%) later recovered below stress 80;
- final mean money was 21.79 EUR, mean arrears 1,466.97 EUR, and mean hunger
  95.08.

This is not explained by the intentionally failing `slacker` persona. Newbie,
study, social, and visa strategies also converged almost universally.

## Persona results

| Persona | Burnout | Cashflow attractor | Mean max stress | Recovery after 90 | Dominant endings |
| --- | ---: | ---: | ---: | ---: | --- |
| Newbie | 25/25 (100%) | 23/25 (92%) | 100.00 | 2/25 (8%) | burnout 12, living imbalance 7, cashflow 4 |
| Study | 25/25 (100%) | 25/25 (100%) | 100.00 | 0/25 | cashflow collapse 23, mental crash 2 |
| Money | 20/25 (80%) | 9/25 (36%) | 98.80 | 3/20 (15%) | burnout 11, living imbalance 9 |
| Social | 24/25 (96%) | 24/25 (96%) | 99.88 | 0/24 | cashflow collapse 17 |
| Visa | 25/25 (100%) | 25/25 (100%) | 100.00 | 4/25 (16%) | cashflow collapse 21 |
| Slacker | 25/25 (100%) | 25/25 (100%) | 100.00 | 0/25 | cashflow collapse 25 |

Money is the only persona with substantial escape from the cashflow attractor,
which shows that player action still matters. However, even that specialized
strategy hits sustained burnout in 80% of seeds and reaches stress 100 in 21/25.
The system therefore allows one narrow survival route rather than six meaningfully
different viable routes.

## Actual ending distribution

The structured campaign aggregate incorrectly says `unknown`; the real endings
were recovered from the 150 hashed cell summaries:

| Ending | Cells | Rate |
| --- | ---: | ---: |
| `cashflow_collapse` | 90 | 60.00% |
| `burnout_pause` | 29 | 19.33% |
| `living_imbalance` | 21 | 14.00% |
| `survival_struggle` | 4 | 2.67% |
| `academic_failure` | 3 | 2.00% |
| `mental_crash` | 2 | 1.33% |
| `high_pressure_top_student` | 1 | 0.67% |

There were zero `stable_start`, `social_connector`, or `career_launch` endings.
Failure convergence is therefore both a state-distribution problem and an
outcome-diversity problem.

## Causal mechanism

### GAME-P0-01 — Default scenario effectively overrides normal starting cash

Normal difficulty declares an initial money range of 2,500–7,500 EUR in
[`DifficultyConfig.gd`](../../../../demo/study-in-germany/autoload/DifficultyConfig.gd#L27),
but the default scenario forces spendable money to 500 EUR in
[`default_first_semester.json`](../../../../demo/study-in-germany/data/scenarios/default_first_semester.json#L7).
The displayed `normal` label therefore does not describe the actual scenario
start.

### GAME-P0-02 — Baseline cashflow requires a large mandatory side income

Normal drift removes 255 EUR every week while the game releases 992 EUR and
charges 620 EUR rent every four weeks. For the 19 decision weeks used by the
semester:

```text
500 initial + 5 × 992 release - 5 × 620 rent - 19 × 255 living drift
= -2,485 EUR
```

Those values are defined in
[`DifficultyConfig.gd`](../../../../demo/study-in-germany/autoload/DifficultyConfig.gd#L26)
and [`GameState.gd`](../../../../demo/study-in-germany/autoload/GameState.gd#L9).
Before discretionary action/event costs, a player must earn roughly 2,485 EUR
just to avoid ending below zero. That requirement competes for the same four
weekly action slots needed by study, visa, registration, social, food, and
recovery routes.

### GAME-P0-03 — Arrears trigger a self-reinforcing pressure cascade

Normal baseline stress is +2/week. Once arrears exist, the game adds +8 stress
and +12 hunger; arrears at least 500 or two shortfalls add another +8 stress,
+10 hunger, and -8 energy; hunger above 70 adds another +5 stress, -8 energy,
and -2 academic progress. At that point the weekly passive stress increment can
reach +23 before actions and events. See
[`GameState.gd`](../../../../demo/study-in-germany/autoload/GameState.gd#L328).

This creates the observed loop:

```text
base deficit -> arrears -> hunger/stress -> lost energy and academic progress
             -> more recovery/survival actions -> less route progress/income
             -> larger deficit
```

The action data includes powerful recovery choices, and agents used them
heavily: `go_running` 1,960 times, `cook_at_home` 1,744,
`take_a_real_break` 1,376, and `language_tandem` 1,242. Yet recovery below 80
after entering stress 90 happened in only 6.25% of affected cells. This rules
out the simple explanation that players merely ignored recovery.

### GAME-P1-04 — Stress saturation destroys useful outcome gradients

Stress reached the hard cap of 100 in 145/150 cells. Once almost every route
saturates, changes in player quality or event severity are no longer visible in
the maximum-stress metric. The game needs either a less aggressive feedback
loop, a longer recoverable range, or additional duration/area-under-pressure
metrics; simply increasing the cap would hide rather than fix the attractor.

### GAME-P1-05 — Ending priority masks part of the burnout problem

`cashflow_collapse` has priority 118, `living_imbalance` 116, and
`burnout_pause` 114 in
[`generated_endings.json`](../../../../demo/study-in-germany/data/endings/generated_endings.json#L12).
When a player satisfies both cashflow and burnout conditions, the cashflow
ending wins. That is why the explicit burnout ending appears only 29 times even
though 144 cells meet the sustained burnout-risk rule. The ending system is not
wrong to choose one primary cause, but reports must show co-occurring terminal
conditions so designers do not undercount burnout.

### GAME-P1-06 — Successful routes are too narrow for the declared personas

Study aligns strongly with its action tags (96%) but cashflow-collapses in
23/25 seeds. Social aligns at 98.53% but cashflow-collapses in 17/25. Visa aligns
at 92.84% but cashflow-collapses in 21/25. These are not cases of the LLM
ignoring its strategy; persona-appropriate behavior is being overridden by the
global survival economy.

## Repair guidance

Do not fix this by lowering only initial stress or buffing one rest action. The
prior `cashflow-drift-repair-v1` experiment improved a focused mechanism but
failed both fixed and holdout target gates and was correctly rejected. The next
experiment should remain bounded and test one causal mechanism at a time:

1. reconcile `normal` scenario cash with the difficulty profile, or reduce the
   recurring mandatory deficit while preserving rent and blocked-account facts;
2. separately test whether arrears/hunger penalties should ramp rather than
   stack immediately;
3. keep `slacker` as a designed-failure control;
4. require non-failure personas to improve on both fixed and unseen holdouts;
5. protect economy, legal-work, registration, visa, event, and ending invariants;
6. judge recovery rate, first-attractor week, and ending diversity—not only
   final money.

No game change was applied during this audit. The report establishes the next
falsifiable repair target; acceptance still requires the Playtest Forge fixed
and holdout protocol.

