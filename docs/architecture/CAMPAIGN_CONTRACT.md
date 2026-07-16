---
status: active
date: 2026-07-16
audience: maintainers, OpenAI Build Week judges
scope: deterministic persona campaign inputs, cell lifecycle, provenance, and citations
---

# Campaign evidence contract

P2 turns persona playthroughs into a fixed matrix whose results can be resumed,
aggregated, and cited without relying on filenames or a builder's explanation.

## Request identity

`CampaignRequest` fixes the campaign ID, ordered unique personas and seeds,
week limit, difficulty, scenario, already-resolved provider, concurrency, and a
repository-relative report root. `auto` is deliberately not accepted: provider
selection belongs to P1 preflight and the selected provider is part of the
campaign fingerprint. Judge concurrency cannot exceed four.

The canonical Build Week request is tracked in
`config/build_week_2026_campaign.json`: six personas, seeds 42/43/44, twenty
weeks, normal difficulty, the first-semester scenario, Replay, and concurrency
four. Changing any field changes the request fingerprint and every cell ID.

## Cell isolation and lifecycle

`build_campaign_cells` creates the persona × seed Cartesian product in stable
order. Each ID exposes persona and seed and ends in a hash-derived suffix; each
cell owns one isolated output directory. Weeks stay sequential inside a cell.

The allowed states are `queued`, `running`, `completed`, `failed`, `cancelled`,
and `partial`. State/stop reason/timestamp/week/error combinations validate
fail-closed. In particular, a failure after at least one completed week is
`partial`, never `completed`; a pre-evidence failure is `failed`; and a
cancelled cell is not a successful cell.

## Mandatory provenance

Every manifest and cell result embeds full Agent commit/tree, canonical game
commit/tree/archive hash, campaign-config hash, provider/mode, and provider
revision. Dirty Agent revisions are rejected. Provider mode is derived from
provider identity, so Replay cannot claim `live`, OpenAI cannot claim `replay`,
and local vLLM/SGLang cannot claim a cloud execution mode.

Resume is deliberately strict: only a completed result with byte-identical
cell request and source fingerprints may be reused. Partial, failed, cancelled,
changed-config, changed-game, changed-code, or changed-provider cells rerun.

## Evidence citations

`CampaignCitation` binds campaign, cell, persona, seed, week, relative artifact
path, JSONL line number, and canonical row hash. A result rejects citations
from another cell or from a week beyond its completed evidence. Later cluster
membership and Codex hypotheses must use these citations; prose-only examples
are not campaign evidence.

## Scheduler and Resume

`CampaignRunner` expands the frozen matrix, creates one output directory per
cell, and uses a thread pool capped by the request's Judge concurrency (never
above four). It writes the manifest, per-cell state, and run summary with
same-directory temporary files followed by atomic replacement. Executors own
one cell and therefore keep weeks sequential; the scheduler never interleaves
weeks from the same playthrough.

On Resume, a Pydantic-valid `cell_result.json` is reused only when both exact
request and exact source identities match and the prior state is `completed`.
Every other cell directory is removed and rebuilt so stale rows cannot mix with
new evidence. A completed campaign is `submittable` only when every expected
cell is completed.

Cancellation is shared with provider workers and a thread-safe child-process
registry. Registered Godot or helper processes receive terminate, a bounded
grace period, and then kill if needed. Cells cancelled before evidence remain
`cancelled`; cells with flushed weeks retain contiguous citations without being
mislabeled as completed. Executor exceptions before any row are `failed`, while
exceptions after valid rows are `partial`.

## Deterministic aggregation and clusters

P2.3 aggregation rereads every cell's `playthrough.jsonl` and verifies each row
against its stored citation hash before calculating anything. It reports cell
and campaign outcome, minimum/final money, maximum stress, cashflow/burnout
weeks, decision validity, fallback, provider error, and persona-alignment
rates. Re-running aggregation over identical rows produces byte-identical JSON.

Cluster membership is controlled only by the tracked
`config/build_week_2026_failure_rules.json`. The initial rules detect sustained
cashflow-plus-stress pressure, sustained burnout risk, and provider fallback.
Consecutive-week thresholds identify the first week of the qualifying streak.
Each member is that exact cell/week citation; representatives are the first
three members in stable persona/seed/week order. Codex may explain or prioritize
these clusters later, but cannot add members, move first-entry weeks, or replace
the rules fingerprint.

## Public-safe bundle

P2.4 emits exactly the review-facing manifest, campaign summary, normalized
weekly persona rows, per-cell evaluations, sanitized provider-call metadata,
failure clusters, and gate report. It never copies prompts, response text,
authorization fields, raw game state, or event/dialogue content. Provider calls
retain provider/mode/model/usage/status and sanitized typed errors only.

`persona_runs.jsonl` is the public citation source: one normalized row per
cell/week with money, stress, validity, fallback, provider-error, ending, and
the private source-row hash. Cluster citations are rewritten to its public line
number and canonical row hash, so a reviewer can resolve evidence without the
private game bundle. All six evidence files are reparsed against Pydantic
schemas and SHA-256 hashed before `gate_report.json` may say `passed`; any
missing cell, non-completed cell, identity mismatch, forbidden field, secret
signature, or later file mutation fails verification.
