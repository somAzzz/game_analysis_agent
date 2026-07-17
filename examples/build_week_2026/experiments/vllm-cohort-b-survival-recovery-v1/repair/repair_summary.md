# Repair experiment

- Decision: **rejected**
- Hypothesis: Aligned non-failure personas enter the cashflow/stress attractor because the existing crisis-negotiation recovery action removes too little arrears while adding stress once crisis begins; one bounded improvement to that action effect should create liability and stress headroom without weakening ordinary costs or guaranteeing success.
- Mechanism: `survival_recovery_action_effect`
- Fixed target reduction: 0.0%
- Holdout target reduction: 0.0%
- Reason: Repair rejected because required proof failed: fixed_target, holdout_target

## Gates

- fixed_target: **failed** — 48 <= 28
- holdout_target: **failed** — 0.000000 >= 0.250000
- critical_invariants: **passed** — patched fixed and holdout critical counters are zero
- decision_validity: **passed** — patched fixed and holdout validity meet threshold
- provider_health: **passed** — deterministic policy produced no hidden failure
- persona_preservation: **passed** — fixed and holdout persona alignment decline is bounded
- no_new_invalid_endings: **passed** — patched cohorts do not add unknown or pipeline-stalled endings
- designed_failure_preserved: **passed** — designed failure remains possible and is not reclassified
