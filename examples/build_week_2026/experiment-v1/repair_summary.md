# Repair experiment

- Decision: **rejected**
- Hypothesis: Recurring survival-economy drift depletes spendable cash faster than distinct persona strategies can recover, after which the cash-shortfall stress feedback pushes every intent into the same cashflow/stress attractor.
- Mechanism: `recurring_living_cost_drift`
- Fixed target reduction: 0.0%
- Holdout target reduction: 0.0%
- Reason: Repair rejected because required proof failed: fixed_target, holdout_target

## Gates

- fixed_target: **failed** — 18 <= 12
- holdout_target: **failed** — 0.000000 >= 0.250000
- critical_invariants: **passed** — patched fixed and holdout critical counters are zero
- decision_validity: **passed** — patched fixed and holdout validity meet threshold
- provider_health: **passed** — deterministic policy produced no hidden failure
- persona_preservation: **passed** — fixed and holdout persona alignment decline is bounded
- no_new_invalid_endings: **passed** — patched cohorts do not add unknown or pipeline-stalled endings
- designed_failure_preserved: **passed** — designed failure remains possible and is not reclassified
