# G4 Evaluator and Judge Experience Review

- Decision: **failed**
- Reviewed commit: `3544f6fdb59aed12dc7e7cae4b3bee072f92efc8`
- Checks: 8
- Failures: 2

## Checks

| Check | Status | Error |
| --- | --- | --- |
| restricted_evaluator | passed |  |
| human_judge_ui | passed |  |
| platform_delivery | failed | platform evidence incomplete or stale: ['linux_amd64_native_and_container', 'linux_arm64_container', 'linux_pinned_real_godot', 'live_openai_campaign'] |
| published_multiarch_image | failed | published image was not built from the current delivery contract |
| offline_inspect | passed |  |
| offline_replay | passed |  |
| frontend_tests | passed |  |
| frontend_public_build | passed |  |

## Decision

G4 failed closed; do not claim cross-platform Judge release readiness.
