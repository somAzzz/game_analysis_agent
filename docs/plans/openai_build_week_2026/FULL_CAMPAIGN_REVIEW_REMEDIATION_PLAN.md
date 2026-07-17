# Full-campaign review remediation plan

Date: 2026-07-17
Status: implementation baseline
Scope: agent evidence, local/API parity, Playthrough Inspector, Judge Mission,
and the minimal human decision layer on the shared experiment model
and human repair review

## 1. Confirmed findings

The reported problems are reproducible in the current implementation.

| ID | Finding | Evidence | Competition relevance |
| --- | --- | --- | --- |
| A-01 | All 150 structured campaign outcomes are `unknown`, although every cell summary contains a real ending. | The final ending is learned by the Godot probe but is not returned in the weekly structured result consumed by aggregation. | P0. A judge cannot audit outcome distributions from the structured bundle. The defect is shared by local and API providers. |
| A-02 | Resume telemetry initializes retained completed cells as `pending`; a running cell can be labelled `completed` before campaign validation. | `_CampaignSessionPublisher` starts from an empty view and maps `finished=true` directly to `completed`. | P0. The UI can misstate evidence status. The defect is shared by local and API providers. |
| A-03 | `calls_used` only reports calls made after the most recent resume. | The value comes from the newly constructed gateway counter. | P0 before paid API campaigns. Cost and provider-health accounting must include retained calls. |
| A-04 | Judge Mode offers Replay and OpenAI only, while the normal campaign path supports vLLM/SGLang/DeepSeek. Its OpenAI runner also bypasses the common publication service. | `JudgeProvider` and `JudgeService` are two-provider contracts; `judge_live_campaign.py` has a separate OpenAI-only runner. | P0. It violates the frozen provider-parity contract and explains why an Action provider cannot represent the local rehearsal. |
| UI-01 | Playthrough Inspector exposes an Events language switch that is not required. | Local state renders EN/中文 buttons although English is already the default evidence copy. | P2. Remove the control and retain English evidence copy. |
| UI-02 | A specific strategy + seed cannot be replayed. | All cell files are published, but the loader fetches only `request.seeds[0]` and stores one cell per persona. | P0. The 54-cell latest cohort is present on disk but 48 paths are unreachable from the UI. |
| UI-03 | Judge Mission remains on the signed 18-cell Replay after a new campaign completes. | `JudgeMissionExperience` imports only `competitionPlaythrough`. | P0 for the live demo. Keep Replay available, but show Latest as a separately labelled source. |
| UI-04 | Judge exposes machine evidence but no final human disposition. | The page renders the Codex recommendation and evidence but has no durable reviewer decision/note/export path. | P1. Add minimal Human Review to the same Judge experiment; do not create a second review module or auto-merge. |
| UI-05 | Large batches lack a review index. | The public manifest lists large artifacts, but there is no lightweight cell catalog, URL-addressable filter state, or lazy detail fetch. | P1. A 25-seed audit should not require loading or manually locating every large cell file. |
| UI-06 | Completed 20-week campaigns can display 95% progress. | The game records 19 decisions to move state to week 20, while the UI divides by requested weeks. | P1. Completion should be driven by validated cells and terminal session state, not a nominal week denominator. |

The vLLM CUDA Graph crash remains a provider-specific deployment follow-up.
The former `/models`-only readiness check is repaired here: Judge provider test
must complete a bounded generation before reporting `passed`.

## 2. Target architecture

One typed campaign service remains authoritative for vLLM, SGLang, OpenAI, and
DeepSeek. Provider adapters may select endpoint, credentials, model, mode, and
truth label only. Every provider must then use the same real-Godot execution,
resume validation, sanitized bundle, playthrough publisher, frontend view, and
evidence gates.

The frontend uses a two-level evidence model:

1. a lightweight, hash-bound cell index for campaign-level filtering and
   review; and
2. one lazily loaded cell trace for week-by-week inspection.

The URL owns evidence source, persona, and seed. This makes every review path
shareable and restores browser history without loading an entire batch.

Judge Mission presents two explicit sources:

- **Latest campaign**: the most recently completed and verified local/API
  campaign published by the common service;
- **Signed Replay**: the frozen competition baseline.

Neither source may inherit the other's truth label.

## 3. Phased implementation

### Phase 1 — repair shared evidence truth

1. Return the real Godot ending in the structured terminal step and fail closed
   when a normally finished campaign still has an unknown ending.
2. Hydrate resume telemetry from compatible completed cell results as
   `retained`, then promote them to `completed` only during final validation.
3. Count provider calls retained in completed cells and add new gateway calls
   to produce cumulative `calls_used`.
4. Treat `finished` during execution as `game_finished_pending_validation`.
5. Make terminal `completed` sessions render 100%, while keeping recorded
   decisions separate from requested state weeks.

Acceptance: focused Python tests prove structured endings, resume hydration,
truthful status transitions, and cumulative call accounting.

### Phase 2 — unify Action provider execution

1. Extend Judge contracts to local vLLM without exposing credentials in the
   browser.
2. Replace the OpenAI-only Judge runner with an adapter over
   `run_persona_campaign(...)` for both vLLM and OpenAI.
3. Publish the completed Judge campaign into the same
   `frontend/public/live-playthrough` location and return the same result
   schema.
4. Keep Replay as a separate prerecorded path and fail closed when a requested
   provider is unavailable.

Acceptance: service tests demonstrate that vLLM and OpenAI create equivalent
campaign requests and both delegate to the common service; no fallback is
installed.

### Phase 3 — scalable path review

1. Emit `index.json` with one small, hash-bound record per cell: persona, seed,
   path, ending, weeks, stop reason, and attractor count.
2. Load the index once and fetch only the selected cell JSON.
3. Add strategy and seed controls, with `source`, `persona`, and `seed` in the
   URL.
4. Remove the event-language tab; render the default English evidence copy.
5. Add campaign totals and selected-path position so reviewers can tell which
   member of a large cohort is open.

Acceptance: frontend tests open two different seeds for the same strategy,
assert the deep link, and prove unselected cell traces are not fetched.

### Phase 4 — update Judge Mission and the shared Human Review layer

1. Let Judge Mission select Latest or Signed Replay explicitly; default to
   Latest only when a completed verified bundle is available.
2. Link persona evidence to the exact source/persona/seed path.
3. Keep one Judge experiment/evidence model for machine and human review. Add
   Human Review as a full-width stage 04 after Proof, not as a nested panel or a
   second module. Proof owns the immutable machine recommendation; Human owns
   the final disposition and links back to the complete evidence and patch diff.
4. Begin with no preselected decision to avoid anchoring. Allow exactly
   `Approve`, `Reject`, or `Needs more evidence`, require a reviewer note, and bind the decision to the current evidence fingerprint.
5. Persist and export `human_review.json` with the machine recommendation,
   human decision, note, reviewer timestamp, evidence fingerprint, and
   `merge_performed: false`. Human approval may disagree with the machine
   recommendation, but it does not mutate gates, relabel evidence, change the
   candidate patch, or trigger merge.

Acceptance: tests cover latest/replay labels, exact links, all three human
choices, required note, stale-fingerprint rejection, durable/exportable review
output, static-mode unavailability messaging, and the absence of any merge
instruction.

### Phase 5 — large-batch follow-up

The current 100-cell execution cap should remain. Cross-cohort audits require a
separate parent manifest that references child campaign fingerprints and
computes deterministic combined aggregates. It should add cohort selection,
pagination or virtualization for lists above 50 visible rows, issue
dispositions, and reviewer queues. This phase is intentionally separate from
the cell-index fix: it must not weaken per-campaign limits or silently combine
incompatible sources.

## 4. Review gates

- Python contract, service, Judge API, and playthrough-view tests pass.
- Frontend typecheck, component tests, and production build pass.
- Existing signed Replay hashes and labels remain unchanged unless an explicit
  regeneration task is approved.
- No API key, prompt, raw response, or private host path enters public assets.
- Local and OpenAI providers reach the same common campaign service.
- A human decision may override the machine recommendation only as an explicit,
  separately recorded final judgment; it cannot mutate deterministic gates or
  automatically merge the patch.
- `git diff --check` passes and generated local campaign evidence is not added
  to the commit.

## 5. Explicit non-goals

- Tuning the game to make the demo “perfect”.
- Treating the 25-seed local run as live OpenAI evidence.
- Automatically accepting or merging a repair.
- Removing the 100-cell safety cap.
- Building an MCP or argparse-wrapper shortcut.
