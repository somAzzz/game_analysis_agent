# Demo video recording plan — target 2:55

Status: recording-ready script; public YouTube URL and final signed-out review
remain open release items. This is the canonical video plan. The implementation
and product-design plans should link here instead of maintaining another timing
table.

## Story and evidence boundary

The video tells one story:

> GPT-5.6 personas play the real Godot game; Codex turns their evidence into one
> bounded repair experiment; fixed and unseen-holdout gates decide whether the
> candidate is safe to ship.

The retained OpenAI campaign is **live campaign evidence only**. The rejected
cashflow repair is a separate, hash-pinned **prerecorded Replay proof** over
real-Godot-derived evidence. The accepted bilingual choice-identity repair is
**deterministic Godot evidence with zero model calls**. Do not join these three
records into one purported live repair run.

Target runtime is 2:55, leaving five seconds below the three-minute limit.
Voiceover and burned-in captions must be English. Every number below is backed
by the committed claim ledger and currently passing Inspect/Replay evidence.

## 175-second shot list and narration

| Time | Purpose | Screen and camera direction | Interaction | English narration |
| --- | --- | --- | --- | --- |
| 0:00–0:12 | Hook | Start tightly cropped on the Playthrough Inspector W3 attractor, then hard-cut to the Judge `REJECTED` stamp. Overlay: `A safer game agent knows when not to ship.` | No scrolling. One deliberate cut at 0:06. | “Game agents can propose fixes. The harder problem is knowing when not to ship them.” |
| 0:12–0:28 | Product and audience | Full-frame title, then a four-node overlay: `Codex → GPT-5.6 personas → Godot 4.4 → evidence gates`. Keep the working UI visible beneath the overlay. | Fade the architecture overlay in and out; do not open source files yet. | “Playtest Forge is a developer tool for game teams. It connects semantic player simulation, a real game runtime, bounded code changes, and release-grade proof.” |
| 0:28–1:05 | Working GPT-5.6 playthrough | Open the retained OpenAI experiment in Playthrough Inspector. Hold briefly on `OPENAI`, `live`, `gpt-5.6-luna`, and `real Godot`; then show the persona rail, actual route, event choice, state delta, evidence hash, and provenance. | Switch between two or three visibly different personas. On one path click `W1 Start`, `W3 Attractor`, and `W19 Ending`; scroll once to `Selected Choice` and `State Delta`, then once to provenance. | “GPT-5.6 receives typed game state, legal actions, event choices, and a persona intent. It chooses; Godot executes the transition. The retained live campaign completed six personas with 114 gameplay records and 228 sanitized provider-call records: one hundred percent valid decisions, zero fallback, and zero provider errors.” |
| 1:05–1:30 | Honest campaign status | Return to Judge Mode and select `OpenAI · all six personas · seed 42 · 20 weeks`. Frame the completed campaign metrics and the visible `CAMPAIGN ONLY` or pending repair stages. | Pause on the six-persona metric cards; do not click `Run bounded campaign`. | “This is observation evidence, not a claimed repair. The interface keeps repair and proof visibly pending because one seed can validate the integration but cannot prove a change.” |
| 1:30–1:55 | Codex contribution | Show the primary Codex task for eight to ten seconds: cited failure cluster, one falsifiable hypothesis, frozen fixed and holdout seeds, two-file allowlist, and bounded patch. Then cut to the Judge exact-diff summary. | Highlight the evidence citation, then the plan limits, then `2 files · +35 / −5`. Avoid long terminal output. | “Codex was the repair director, not just a code generator. It separated facts from hypothesis, froze seeds, thresholds and an eighty-line budget, changed one mechanism in an isolated worktree, and required proof before merge.” |
| 1:55–2:30 | Core proof: reject the tempting fix | Select `Signed cashflow repair replay`. Show the focused validator pass, fixed comparison, holdout comparison, failed `fixed_target` and `holdout_target` gates, and final `REJECTED` stamp. Crop so the baseline and patched numbers remain readable. | Reveal fixed first, then holdout, then the failed gates. End on `candidate_not_merged`. | “The patch was legal, and mean final cash rose from zero to about eighteen on fixed seeds and sixty-one on holdouts. But target membership stayed eighteen of eighteen and maximum stress stayed one hundred. Both causal gates failed, so Codex rejected the candidate and did not merge it.” |
| 2:30–2:48 | Prove that gates can accept | Switch to `Accepted · bilingual choice identity repair`. Show the accepted diff summary, fixed and holdout semantic-preservation proof, and `ACCEPTED`. Overlay: `Accept only when every required gate passes.` | One dropdown change and one short scroll; no detailed code reading. | “The gates are not biased toward rejection. A separate bilingual choice-identity repair passed its fixed, holdout, invariant, and regression evidence, so it was accepted.” |
| 2:48–2:55 | Impact and call to action | End on the Judge overview with the product name, public demo URL, repository URL, and small footer: `Inspect · Replay · Docker Godot · OpenAI GPT-5.6`. | Hold the final card for seven seconds. | “Playtest Forge turns AI playthroughs into evidence-backed release decisions: observe, repair, prove—and keep permission to say no.” |

## Capture order

Preload these views before recording; record them as short clips and edit them
to the timing table instead of performing a fresh campaign during the take:

1. `/#/playthrough-inspector?experiment=openai-all-six-seed-42-20w`
2. Judge experiment `openai-all-six-seed-42-20w`
3. The primary Codex task with private values and unrelated history hidden
4. Judge experiment `cashflow-drift-repair-v1`
5. Judge experiment `localization-choice-identity-v1`
6. The final product/repository card

The OpenAI clip must show the retained completed public bundle. Do not spend API
credit or risk a partial campaign merely to capture footage. If a fresh run is
recorded separately, label it with its actual provider/runtime/session status
and do not substitute it for the retained proof records.

## Recording and edit rules

- Capture at 1920×1080, 30 fps, with browser zoom chosen before recording so
  metric cards and provenance remain readable at normal YouTube size.
- Hide the browser bookmarks bar, desktop notifications, unrelated tabs, local
  usernames, absolute host paths, keys, tokens, raw model responses, prompts,
  and private traces.
- Use deliberate cursor movement, cuts, and digital crops. Do not make the
  viewer watch dependency installation, Docker image pulls, a full campaign,
  or long terminal commands.
- Burn in accurate English captions. Use no unlicensed music or unrelated
  third-party branding.
- Never animate or edit a status in a way that changes its meaning. `running`
  and `finalizing` are telemetry, not completed evidence; failed or partial
  sessions remain failed or partial.
- Keep `live OpenAI campaign`, `prerecorded Replay repair proof`, and
  `deterministic zero-model correctness proof` visible and verbally distinct.

## Final review gate

Before publishing, verify:

- encoded duration is below 3:00 and the final five-second buffer survives the
  YouTube upload;
- voiceover and captions explicitly explain what the project does, how Codex
  was used, and what GPT-5.6 does at runtime;
- all displayed numbers, model/runtime labels, decisions, URLs, and commit
  references match the final public repository revision;
- YouTube playback is public and works signed out at 1080p with intelligible
  audio and captions;
- the video contains no secrets, private evidence, unsupported live claims,
  copyrighted music, or misleading cuts.
