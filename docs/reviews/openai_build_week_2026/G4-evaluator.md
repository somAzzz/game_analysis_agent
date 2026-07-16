# G4 Evaluator and Judge Experience Review

- Decision: **failed**
- Reviewed commit: `be56673fea66155e5eec93d2bcfa5a7a76ce10e0`
- Checks: 4
- Failures: 2

## Checks

| Check | Status | Error |
| --- | --- | --- |
| restricted_evaluator | passed |  |
| human_judge_ui | passed |  |
| platform_delivery | failed | platform evidence incomplete or stale: ['linux_arm64_container', 'live_openai_campaign'] |
| published_multiarch_image | failed | published image was not built from the current delivery contract |

## Decision

G4 failed closed; do not claim cross-platform Judge release readiness.
