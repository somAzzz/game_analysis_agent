# Actual Playthrough evidence v1

This directory is the frontend data source for the competition Playthrough
Inspector. It was generated from a fresh real-Godot 4.4 execution using the
hash-pinned deterministic Replay fixture. It is prerecorded evidence, not a
live OpenAI run.

## Proven result

- campaign: `playthrough-evidence-full-v1`
- matrix: 6 Personas × seeds 42/43/44
- terminal cells: 18/18 completed
- actual weekly nodes: 342
- actual state-transition edges: 324
- legal event choices retained: 1,336
- partial/fallback/provider errors: 0/0/0
- final ending: 18/18 `cashflow_collapse`
- selected failure cluster: `cashflow-stress-attractor` (18 members)

## Layout

- `manifest.json` — hashes, identities, aggregate checks, and derived artifact list.
- `personas.json` — static Persona contracts plus observed three-seed behavior.
- `cells/*.json` — frontend-ready actual path views.
- `source/` — retained raw traces, cell results, summaries, public campaign gate,
  failure clusters, Persona config, and action catalog.

Actual edges are measured state transitions. Unselected event choices are
retained as legal option stubs only; the data does not claim unexecuted future
states or a complete counterfactual branch graph.

## Rebuild and verify

```bash
uv run python tools/build_playthrough_views.py \
  --source-root examples/build_week_2026/playthrough-v1/source \
  --campaign-manifest examples/build_week_2026/playthrough-v1/source/reports/playthrough-evidence/campaigns/playthrough-evidence-full-v1/campaign_manifest.json \
  --failure-clusters examples/build_week_2026/playthrough-v1/source/public/failure_clusters.json \
  --public-gate examples/build_week_2026/playthrough-v1/source/public/gate_report.json \
  --output examples/build_week_2026/playthrough-v1

uv run python tools/verify_playthrough_views.py
uv run pytest -q tests/test_playthrough_view.py
```
