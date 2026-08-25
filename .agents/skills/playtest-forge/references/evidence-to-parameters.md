# From evidence to parameters

## Build a causal map

Write the chain before opening candidate source:

`player intent → action availability/choice → mechanic update → intermediate
state → feedback loop → target outcome`

Locate the earliest repeatable divergence from design intent. Rank candidate
controls by causal proximity, blast radius, observability, monotonicity,
interaction risk, and whether the design contract permits the change.

## Choose the change class

| Evidence pattern | Inspect first | Avoid as first move |
| --- | --- | --- |
| Cross-persona resource collapse | recurring costs/income, recovery, compounding feedback | persona prompts |
| One route dominates | rewards, prerequisites, opportunity cost, route visibility | global stat clamps |
| Intended action never selected | availability, copy/affordance, relative value | forced selection |
| Event/ending unreachable | trigger graph, ordering, prerequisite state | reward magnitude |
| Stat saturates at bound | update order, unit scale, clamp, repeated application | raising the clamp alone |
| Fixed seeds improve only | seed-specific interaction or overfit | changing holdouts/thresholds |
| Safety invariant fails | transition correctness and validation | balance tuning |

## Freeze the hypothesis

State:

- cited facts and affected cohorts;
- suspected mechanism, not merely a file/value;
- predicted target direction and protected metrics;
- one allowed parameter or cohesive mechanic class;
- counter-evidence that would reject the hypothesis.

Prefer the smallest reversible edit. Do not combine a recurring-cost change,
stress-feedback change, and recovery buff in one experiment: the result would
not identify which mechanism mattered.

## Interpret the result

A local metric can improve without repairing the target. For example, higher
ending cash with unchanged collapse membership means the patch moved a symptom
but did not break the failure attractor. Reject it, preserve the evidence, and
form a new experiment around the next plausible link in the causal chain.
