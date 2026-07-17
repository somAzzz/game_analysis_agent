# Repair experiment

- Decision: **rejected**
- Hypothesis: When spendable cash reaches crisis range, the recurring cash-shortfall stress feedback is applied strongly enough that aligned non-failure personas cannot recover before entering the cashflow/stress attractor; one bounded reduction or cap in that feedback should delay or prevent first entry without removing designed failure endings.
- Mechanism: `cashflow_crisis_stress_feedback`
- Fixed target reduction: 0.0%
- Holdout target reduction: 0.0%
- Reason: Repair rejected because required proof failed: fixed_target, holdout_target

## Gates

- fixed_target: **failed** — 48 <= 27
- holdout_target: **failed** — 0.000000 >= 0.250000
- critical_invariants: **passed** — patched fixed and holdout critical counters are zero
- decision_validity: **passed** — patched fixed and holdout validity meet threshold
- provider_health: **passed** — deterministic policy produced no hidden failure
- persona_preservation: **passed** — fixed and holdout persona alignment decline is bounded
- no_new_invalid_endings: **passed** — patched cohorts do not add unknown or pipeline-stalled endings
- designed_failure_preserved: **passed** — designed failure remains possible and is not reclassified
