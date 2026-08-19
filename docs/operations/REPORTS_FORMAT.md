# Reports directory format

> **Audience**: anyone running the agent, generating reports, or shipping
> new evidence into `reports/`. The goal of this document is to make
> every report directory produced by the project look the same: one
> manifest schema per layout, a fixed minimal file set, and a single
> validation entry point.

## 1. Top-level layout

`reports/` is a **runtime artifact directory** (gitignored except for
`.gitkeep`). Only the top-level subdirectories below are part of the
project's "latest standard":

| Subdirectory | Purpose | Default generator |
| --- | --- | --- |
| `reports/inference-ab/<experiment-root>/` | APC vs MTP and similar local-inference A/B benchmark outputs | `tools/inference_ab/generate_inference_ab_report.py` |
| `reports/inference-ab/smoke/`, `reports/inference-ab/fixtures/` | Diagnostic smoke runs and frozen persona traces used by the benchmark | `tools/inference_ab/run_inference_ab_benchmark.py` |
| `reports/persona-campaigns/<campaign-id>/` | Persona campaign evidence (cells, public bundle) | `tools/persona/run_persona_campaign.py` + `persona_campaign_service` |
| `reports/persona-runtime/<name>/` | Godot runtime overlay (the materialized game + overlay metadata) | `tools/persona/run_persona_campaign.py` |
| `reports/playtests/<name>/` | Playtest contract evidence | Playtest tools |
| `reports/repair-experiments/<experiment-id>/{private,public}/` | Repair experiment records (PRIVATE) | `tools/repair_*` |
| `reports/private-local-vllm/<cohort>/{campaign,repair}/` | Offline vLLM cohort evidence (PRIVATE) | Cohort tools |

**Forbidden** at the top level:

- `reports/index.html` and `reports/manifest.json` — they are
  *regenerated* by `tools/dashboard/build_dashboard.py` and
  `tools/dashboard/emit_manifest.py`. Hand-editing them is a no-op and they
  should be deleted before committing if they ever appear.
- Any directory that is not listed in the table above. The cleanup
  tool `tools/reports/prune_expired_reports.py` removes everything that is not
  in this layout.

## 2. Locked manifest schemas

Every report directory that has a manifest **must** declare a
`schema_version` that matches the canonical string for its layout. The
canonical strings are:

| Layout | Manifest file | Required `schema_version` | Source |
| --- | --- | --- | --- |
| Generic report (any other report) | `report_manifest.json` | `trace-manifest-v2` | `src/game_analysis_agent/report_manifest.py:25` |
| Persona campaign | `campaign_manifest.json` | `persona-campaign-manifest-v1` | `src/game_analysis_agent/campaign_contract.py:16-18` |
| Inference A/B benchmark | `manifest.json` | `inference-ab-report-manifest-v1` | `tools/inference_ab/generate_inference_ab_report.py:763` |
| Repair experiment public bundle | `gate_report.json` | `repair-bundle-gate-v1` | `src/game_analysis_agent/repair_bundle.py` |

> Adding a new manifest schema? Bump the source-of-truth constant in
> the corresponding module **first**, then mirror the new string in
> `tools/reports/validate_reports.py` (`SCHEMAS`).

## 3. Required file inventory per layout

The current generators emit the following minimum file set. New
generators **must** emit at least these files for their layout so
downstream tooling (and `tools/reports/validate_reports.py`) can find the
expected evidence.

### 3.1 Inference A/B benchmark (`reports/inference-ab/<root>/`)

- `manifest.json` (`inference-ab-report-manifest-v1`)
- `summary.json` (`inference-ab-summary-v1`)
- `summary.csv`
- `requests.jsonl`
- `server-metrics.jsonl`
- `gpu-metrics.csv`
- `comparison.html`
- `charts/*.svg` (at least one chart)

### 3.2 Persona campaign (`reports/persona-campaigns/<id>/`)

- `campaign_manifest.json` (`persona-campaign-manifest-v1`)
- `campaign_run_summary.json`
- `cells/<cell-id>/...` (per-cell evidence)
- `public/campaign_manifest.json` (mirror)
- `public/campaign_summary.json`
- `public/agent_eval.jsonl`
- `public/persona_runs.jsonl`
- `public/llm_calls.jsonl`
- `public/failure_clusters.json`
- `public/gate_report.json`
- `public/repair_eligibility.json`

### 3.3 Repair experiment public bundle (`reports/repair-experiments/<id>/public/`)

- `gate_report.json` (`repair-bundle-gate-v1`)
- `repair_experiment.json` (`repair-experiment-record-v1`)
- `comparison.json`
- `repair_summary.md`

### 3.4 Persona runtime overlay (`reports/persona-runtime/<name>/`)

- `.playtest-forge-runtime-overlay.json`
  (`build-week-game-runtime-overlay-v1`)
- `.playtest-forge-source.json`
  (`build-week-game-materialized-v1`)

### 3.5 Playtests (`reports/playtests/<name>/`)

- `contract.json` or other domain contract — see
  `reports/persona-runtime/study-four-semester-20260803/docs/testing/report_contracts.md`
  for the current contract list.

## 4. Validation workflow

A single validator enforces the contract above:

```bash
python tools/reports/validate_reports.py                # default: --root reports
python tools/reports/validate_reports.py --root reports --strict
python tools/reports/validate_reports.py --root reports --json
```

Behaviour:

- Walks the configured root and applies the rules in
  [`tools/reports/validate_reports.py`](../../tools/reports/validate_reports.py).
- Returns exit code `0` on success and `1` on the first schema/file
  violation.
- `--json` emits one machine-readable record per directory (pass or
  fail). Use it from CI to surface the full error list.
- `--strict` additionally fails on top-level directories that are not
  in the locked layout (the same set `tools/reports/prune_expired_reports.py`
  treats as expired).

Before opening a PR that adds a new report directory or changes a
generator, run the validator with `--strict` and confirm it passes.

## 5. Cleanup workflow

When the layout itself changes (e.g. a new report type replaces an
old one), update both the locked table above *and* the
`EXPIRED_*` constants in `tools/reports/prune_expired_reports.py`. The
script is intentionally data-driven so that a re-run of
`tools/reports/prune_expired_reports.py --apply` clears the old layout.

```bash
python tools/reports/prune_expired_reports.py          # dry-run
python tools/reports/prune_expired_reports.py --apply  # actually delete
```

Large immutable JSONL evidence is retained losslessly as verified Zstandard
archives. Standard matrices seal each cell after its evidence checks pass;
first-party readers re-analyze the archive directly. See
`docs/operations/REPORT_ARCHIVES.md`.

`reports/` is gitignored, so the deleted artifacts will not appear in
`git status`. The script prints every path it would remove so the
operation is auditable.
