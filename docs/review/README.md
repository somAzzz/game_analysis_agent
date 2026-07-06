# Review Documentation Index

This directory keeps the review material layered so each document has one job.

## Layers

1. Source feedback: [../REVIEW_FEEDBACK.md](../REVIEW_FEEDBACK.md)
   - Original review, target loop, task rationale, and implementation log.
2. Task plan: [../ACTION_PLAN.md](../ACTION_PLAN.md)
   - Review items broken into executable tasks T01-T13.
3. Alignment audit: [ALIGNMENT_AUDIT.md](ALIGNMENT_AUDIT.md)
   - Current code state against the review feedback.
4. Detailed follow-up plan: [DETAILED_EXECUTION_PLAN.md](DETAILED_EXECUTION_PLAN.md)
   - Concrete patch plan for gaps found in the audit.
5. Real test gap analysis: [REAL_TEST_GAP_ANALYSIS.md](REAL_TEST_GAP_ANALYSIS.md)
   - Comparison against `study-in-germany` and the next real-test capabilities.

## Current Status

As of this audit and remediation pass, the repo is aligned with the P0/P1
feedback items that can be implemented without a live Godot runtime:

- implemented: T02, T03, T04, T05, T06, T07, T08, T09, T10;
- added real-test bridge: policy aliases, scenario-aware simulation,
  Godot validator orchestration, executable gates, coverage report, replay evidence;
- environment-dependent: T01, T12 full matrix execution;
- future work: T13.

This pass also fixed one threshold drift in `anomaly_semantics.py`:
`hunger_ignored_too_long` now uses the documented `hunger >= 85` threshold.

## Real-Test Commands

```bash
python tools/run_gameplay_agent.py sim \
  --run-id low-money-work-smoke \
  --runs 20 --policy money --scenario low_money_start

python tools/run_gameplay_agent.py validate \
  --report-dir reports/validation/latest

python tools/run_gameplay_agent.py gates \
  --report-dir reports/balance/low-money-work-smoke
```

`money` and `visa` are accepted as aliases for the Godot policies `work`
and `admin`.
