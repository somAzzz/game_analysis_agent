# Evidence contract

## General contract

Every campaign must record:

- campaign/test contract and source/runtime/config revisions;
- cell matrix and terminal completeness state;
- per-step typed state, legal actions/choices, selected IDs, and outcomes;
- provider/model or deterministic-policy provenance;
- aggregate metrics, failure clusters, invariants, and gate results;
- exact citations from repair-driving facts to fields or rows.

Every repair must record the frozen plan, design-contract fingerprint, cited
facts, hypothesis, predicted effect, fixed/holdout cohorts, change allowlist
and budget, patch diff/hash, focused tests, comparisons, protected gates,
provider health, Codex provenance, and accepted/rejected decision.

Hash immutable artifacts and canonical JSONL rows. Hashes detect later mutation
and bind citations to exact evidence; they do not make bad data correct. Verify
schema, completeness, provenance, and design meaning separately.

Do not publish prompts, raw model responses, secrets, private game text, host
paths, or private traces. Create a sanitized bundle with the same aggregate and
citation identities.

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

Run `tools/review_build_week_g2.py --skip-commands` or `scripts/preflight`.
The final current-project experiment contains `repair_experiment.json`,
`repair_summary.md`, baseline/patched fixed and holdout snapshots,
`comparison.json`, and `patch.diff`.
