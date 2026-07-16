# Evidence contract

Use only committed, hash-verified campaign evidence for baseline facts:

- `examples/build_week_2026/campaign-v1/campaign_manifest.json`
- `examples/build_week_2026/campaign-v1/campaign_summary.json`
- `examples/build_week_2026/campaign-v1/persona_runs.jsonl`
- `examples/build_week_2026/campaign-v1/agent_eval.jsonl`
- `examples/build_week_2026/campaign-v1/llm_calls.jsonl`
- `examples/build_week_2026/campaign-v1/failure_clusters.json`
- `examples/build_week_2026/campaign-v1/gate_report.json`
- `config/build_week_2026_target.json`

Run `tools/review_build_week_g2.py --skip-commands` or the Skill preflight
before citing these files. Each factual claim must identify an artifact and a
field or JSONL line. For row claims, verify the citation's canonical row hash.

The final experiment directory must contain:

- `repair_experiment.json`: typed plan, patch, all four metric snapshots,
  comparison, gates, decision, and Codex provenance.
- `repair_summary.md`: facts, inference, predicted effect, actual results, and
  accepted/rejected reason.
- `baseline/fixed.json` and `baseline/holdout.json`.
- `patched/fixed.json` and `patched/holdout.json`.
- `comparison.json`.
- `patch.diff` and its SHA-256.

Do not commit prompts, model response bodies, secrets, private game text, host
paths, or raw private traces into a public experiment bundle.
