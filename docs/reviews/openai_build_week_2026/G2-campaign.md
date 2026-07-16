# G2 Campaign Evidence Review

- Decision: **passed**
- Reviewed commit: `e7b3334195394842721719f3086d03755b38b9ba`
- Checks: 7
- Failures: 0

## Checks

| Check | Status | Evidence |
| --- | --- | --- |
| bundle_integrity | passed | `{"artifacts_hashed": 6, "campaign_id": "build-week-2026-evidence-v1", "checks": 6, "status": "passed"}` |
| source_identity | passed | `{"agent_commit": "5fff398b86364042ef000c0884f843ff06b8ad03", "agent_tree": "a822dc553b61f0e13058c272a9d7dbd93e2786c4", "campaign_config_sha256": "f188e6d4745f568626d4c3a095c7ac18b0646a3913922ef1b246bbd3d22cc13c", "fixture_sha256": "865f4fb83028f7ada18b581462adef3cbb15f2b06ed4c59cb0601f97b0d5f590", "game_commit": "348b9fd5501e71ebc7142e10f9068fc1490b5124"}` |
| public_recomputation | passed | `{"completed_cells": 18, "expected_cells": 18, "fallback_rate": 0.0, "mean_final_money": 0.0, "mean_max_stress": 100.0, "persona_alignment_rate": 0.502924, "provider_error_rate": 0.0, "replay_calls": 684, "request_fingerprint": "8fa65234cb151a16534cfdbad7a2a26b330a9efc0610c701f7e20e87a41b7538", "source_fingerprint": "01dbba63744eec8f0c055fe6cc75bc0dd9ddf02a9ea6192238193dd009eee49b", "total_weeks": 342, "valid_rate": 1.0}` |
| cluster_recomputation | passed | `{"cluster_counts": {"burnout-risk": 18, "cashflow-stress-attractor": 18, "provider-fallback": 0}, "clusters_recomputed": 3}` |
| target_freeze | passed | `{"disjoint": true, "evidence_rows": 3, "fixed_seeds": [42, 43, 44], "holdout_seeds": [1042, 1043, 1044], "members": 18, "personas": 6, "selected_cluster_id": "cashflow-stress-attractor"}` |
| ruff | passed | `{"command": ["uv", "run", "ruff", "check", "."], "exit_code": 0, "tail": "All checks passed!"}` |
| full_pytest | passed | `{"command": ["uv", "run", "pytest", "-q"], "exit_code": 0, "tail": "........................................................................ [ 19%]\n........................................................................ [ 39%]\n........................................................................ [ 58%]\n........................................................................ [ 78%]\n........................................................................ [ 98%]\n.......                                                                  [100%]\n367 passed in 6.07s"}` |

## Decision

G2 passed with no conditions.
