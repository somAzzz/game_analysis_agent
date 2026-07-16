# Study in Germany project profile

Read this file only for the current Build Week integration. For another game,
create the project profile described in `migration-guide.md` and do not carry
these personas, mechanics, paths, or thresholds across.

Run `scripts/preflight --json` first and stop if it fails.

Read `config/build_week_2026_design_contract.json` through
`game_analysis_agent.design_contract.load_design_contract`; do not copy values
from memory. The loader verifies the G2 review, frozen target, release gates,
and persona definitions by SHA-256.

Interpret the contract as follows:

- The defect is cross-persona convergence on the cashflow/stress attractor,
  not the existence of failure endings.
- `newbie`, `study`, `money`, `social`, and `visa` are non-failure-intent.
- `slacker` is failure-seeking and is not required to succeed.
- All critical invariant counters must remain zero.
- Select one allowed mechanism class. Do not combine economy, crisis feedback,
  and recovery-action changes in one experiment.
- The allowlist is the outer set of inspectable repair locations, not
  permission to change all of them. The experiment file/line budget still
  applies.
- Non-goals are hard constraints, including no persona, prompt, gate, test,
  provider, UI, API, or seed-specific change.

The experiment record must include the design contract fingerprint generated
before the candidate patch.
