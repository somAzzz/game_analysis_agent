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
