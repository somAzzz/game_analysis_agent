# Evidence contract

## General contract

Every campaign must record:

- campaign/test contract and source/runtime/config revisions;
- cell matrix and terminal completeness state;
- per-step typed state, legal actions/choices, selected IDs, and outcomes;
- provider/model or deterministic-policy provenance;
- selected local generation profile and its frozen thinking/max-token values;
- aggregate metrics, failure clusters, invariants, and gate results;
- exact citations from repair-driving facts to fields or rows.

Every repair must record the frozen plan, design-contract fingerprint, cited
facts, hypothesis, predicted effect, fixed/holdout cohorts, change allowlist
and budget, patch diff/hash, focused tests, comparisons, protected gates,
provider health, Codex provenance, and accepted/rejected decision.

Hash immutable artifacts and canonical JSONL rows. Hashes detect later mutation
and bind citations to exact evidence; they do not make bad data correct. Verify
schema, completeness, provenance, and design meaning separately.

Private JSONL is hot evidence only while its producing cell is running and
until that cell's evidence checks pass. An immutable validated cell may be
sealed before cohort aggregation because first-party readers stream and verify
the cold representation. Archive it by default as `<name>.jsonl.zst` plus an adjacent
`<name>.jsonl.zst.manifest.json`. The manifest must bind the exact raw and
compressed SHA-256, byte counts, JSON record count, codec, level, and schema.
Delete the raw source only after decompression, JSONL parsing, and every raw
identity field match. An archive failure is a non-success state and must leave
the current raw source intact. Never seal a file still open for writing. Restore
exact JSONL before using a reader that does not support compressed input. Keep
compact public evidence uncompressed.

Do not publish prompts, raw model responses, secrets, private game text, host
paths, or private traces. Create a sanitized bundle with the same aggregate and
citation identities.

## Dynamic local/live persona campaigns

A non-Replay campaign must use `persona_campaign_service.run(...)` through `scripts/run-persona-campaign`; do not duplicate CLI logic in a skill. Retain raw cell evidence under `reports/persona-campaigns/<campaign>/cells`, publish only the sanitized bundle, and generate the frontend view under `frontend/public/live-playthrough`.

The public truth label must match the frozen provider and mode, including `local-vllm-real-godot`, `local-sglang-real-godot`, `live-openai-real-godot`, or `live-deepseek-real-godot`. Never relabel local evidence as live. Reject partial cells and any fallback week. A single-persona campaign must publish `repair_target_eligible=false`.

`frontend/public/live-playthrough/session.json` is a sanitized, ephemeral
progress contract shared by local and API providers. `running` and `finalizing`
are UI telemetry, not citable completed evidence. Only after the service writes
`completed` and the public bundle/view verifiers pass may Codex cite the final
manifest, gate, and hashed rows. A `failed` session must remain failed; it must
never fall back to Replay or a different provider under the same identity.

## Current repository adapter

For the retained Build Week campaign, verify these committed artifacts before
citing them:

- `examples/build_week_2026/campaign-v1/campaign_manifest.json`
- `examples/build_week_2026/campaign-v1/campaign_summary.json`
- `examples/build_week_2026/campaign-v1/persona_runs.jsonl`
- `examples/build_week_2026/campaign-v1/agent_eval.jsonl`
- `examples/build_week_2026/campaign-v1/llm_calls.jsonl`
- `examples/build_week_2026/campaign-v1/failure_clusters.json`
- `examples/build_week_2026/campaign-v1/gate_report.json`
- `config/build_week_2026_target.json`

Run `tools/build_week/review_build_week_g2.py --skip-commands` or `scripts/preflight`.
The final current-project experiment contains `repair_experiment.json`,
`repair_summary.md`, baseline/patched fixed and holdout snapshots,
`comparison.json`, and `patch.diff`. `scripts/verify-repair` archives terminal
private JSONL by default; `--keep-jsonl` is the explicit compatibility/debug
override.
