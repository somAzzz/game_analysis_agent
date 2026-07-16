# G4 Evaluator and Judge Experience Review

- Decision: **failed**
- Reviewed commit: `aca46922320a31d2e5f918b9537fca36505e2d3a`
- Checks: 8
- Failures: 2

## Checks

| Check | Status | Error |
| --- | --- | --- |
| restricted_evaluator | passed |  |
| human_judge_ui | passed |  |
| platform_delivery | failed | platform evidence incomplete: ['linux_amd64_native_and_container', 'linux_arm64_container', 'macos_container_dashboard', 'macos_live_openai', 'macos_pinned_real_godot'] |
| published_multiarch_image | failed | judge-image-metadata.json is missing; no image publication claim |
| offline_inspect | passed |  |
| offline_replay | passed |  |
| frontend_tests | passed |  |
| frontend_public_build | passed |  |

## Decision

G4 failed closed; do not claim cross-platform Judge release readiness.
