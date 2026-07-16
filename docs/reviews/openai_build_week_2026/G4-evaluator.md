# G4 Evaluator and Judge Experience Review

- Decision: **failed**
- Reviewed commit: `74d56a7c02a88a6a330782619908ee6f952df5ec`
- Checks: 8
- Failures: 2

## Checks

| Check | Status | Error |
| --- | --- | --- |
| restricted_evaluator | passed |  |
| human_judge_ui | passed |  |
| platform_delivery | failed | platform evidence is stale for the current delivery contract |
| published_multiarch_image | failed | published image was not built from the current delivery contract |
| offline_inspect | passed |  |
| offline_replay | passed |  |
| frontend_tests | passed |  |
| frontend_public_build | passed |  |

## Decision

G4 failed closed; do not claim cross-platform Judge release readiness.
