# Demo video script — target 2:55

Status: recorded and published at
https://www.youtube.com/watch?v=62tW2RoFwTo. This remains the canonical
narration and shot plan for the 2:55 public demo.

## Narrative thesis

Playtest Forge is not an autonomous patch generator. It is a Codex-directed
game-QA workflow that combines semantic player behavior, real-engine state,
bounded repair experiments, and deterministic release gates. Its promise is:

> behavior from GPT-5.6, state truth from Godot, experiment direction from
> Codex, and release decisions from evidence.

Target runtime is 2:55, leaving five seconds below the three-minute limit. Use
the English narration below and burn in matching English captions.

## Final 175-second script

### 0:00–0:22 — The QA gap

**Screen**

- Open on a simple two-column chart: `2020 · 9,640` and `2025 · about 21,400`.
- Footer: `Source: SteamDB release summary · accessed 2026-07-20`.
- Cut through three labels: `SCRIPTED BOTS`, `MANUAL PLAYTESTING`, `UNGOVERNED AI AGENTS`.
- Under them show: `rules, not intent`; `slow and hard to reproduce`; `stochastic and hard to trust`.

**Voice**

> SteamDB counts 9,640 Steam releases in 2020 and roughly 21,400 in 2025—more
> than double. As more games compete for attention, small and solo teams need
> scalable QA. Scripted bots cover rules, not player intent. Manual playtesting
> is costly and difficult to reproduce. LLM agents add semantic behavior, but
> remain stochastic and cannot prove a repair on their own.

### 0:22–0:38 — What I built

**Screen**

- Reveal the Playtest Forge Judge hero over the working frontend.
- Animate the product line: `Persona playthroughs → immutable evidence → bounded repair → proof`.

**Voice**

> I built Playtest Forge: a Codex-directed QA workflow that combines diverse
> persona playthroughs with real-engine execution, immutable evidence, and
> fixed plus unseen-holdout gates. Its goal is not to generate more patches. It
> is to make every repair falsifiable and reviewable.

### 0:38–0:52 — Four parts, one loop

**Screen**

- Overlay four nodes on the working UI:
  `CODEX → GPT-5.6 LUNA → GODOT 4.4 → EVIDENCE GATES`.
- Resolve them into: `OBSERVE → HYPOTHESIZE → REPAIR → PROVE`.

**Voice**

> Codex directs the experiment. GPT-5.6 Luna plays distinct personas. Godot is
> the source of truth for state transitions. Evidence gates verify provenance,
> invariants, and unseen holdouts. Together they form one loop: observe,
> hypothesize, repair, and prove.

### 0:52–1:20 — Start from Codex

**Screen**

- Show the primary Codex task and enter a concise request such as:
  `Use $playtest-forge to test this game.`
- Show preflight completing and the frontend URL appearing.
- Show the two required choices and select `Docker Godot` and `OpenAI API` for
  this competition demonstration.
- Show the profile menu and briefly frame all three profiles:
  `one-strategy`, `six-strategy`, and `repair-evidence`.

**Voice**

> I start in Codex by invoking the Playtest Forge Skill. Before any model call,
> it runs preflight, stages signed evidence, and opens a read-only inspector. I
> choose the runtime and provider—in this demo, Docker Godot and the OpenAI
> API—then one of three frozen profiles: one strategy, six strategies, or full
> repair evidence. The profiles are versioned in config; today, only the
> one-strategy persona is interactively overridable.

### 1:20–1:52 — Watch and replay the live campaign

**Screen**

- Cut to Playthrough Inspector while a retained completed OpenAI experiment is
  selected.
- Frame the exact labels: `OPENAI`, `live`, `gpt-5.6-luna`, `real Godot`.
- Show session progress as an example of the live monitoring UI, without
  implying a staged `running` state is completed evidence.
- Switch between two personas and click `W1 Start`, `W3 Attractor`, and
  `W19 Ending`.
- Scroll through `Selected Choice`, `State Delta`, evidence hash, and provenance.

**Voice**

> After confirmation, Codex starts the frozen campaign. The frontend follows
> cells and weeks in near real time. GPT-5.6 receives typed game state, legal
> actions, choices, and persona intent; Godot executes each transition. After
> the campaign and public gates complete, I can replay the actual live path,
> inspect choices and state deltas, and trace every row to its hash. The
> pipeline writes the summary, evidence, and final states; Codex reports them
> without automatically editing the game.

### 1:52–2:19 — Hypothesize, repair, prove

**Screen**

- Return to Codex and show: cited facts → one hypothesis → fixed seeds → unseen
  holdouts → file/line budget.
- Cut to Judge experiment `cashflow-drift-repair-v1`.
- Show the two-file `+35 / −5` diff, focused validator pass, fixed/holdout
  comparison, failed target gates, and `REJECTED`.

**Voice**

> Only the full three-seed profile is ready to freeze a repair target. Codex
> cites exact rows, states one hypothesis, limits files and lines, and tests the
> patch in an isolated worktree. In this signed case, final cash improved, but
> all 18 cells still entered the cashflow-stress attractor and maximum stress
> remained 100. The causal gates failed, so the patch was rejected and never
> merged.

### 2:19–2:45 — The unexpected accepted repair

**Screen**

- Select `Accepted · bilingual choice identity repair`.
- Show the two baseline identity errors, the exact accepted diff, fixed and
  holdout semantic-preservation gates, and `ACCEPTED`.
- Highlight the repaired choice labels rather than scrolling through all code.

**Voice**

> The biggest surprise came when Codex traced choice identity: one borrowing
> option was missing, and another was mislabeled “Take the cash job.” Codex
> made Chinese source text the stable identity and English display-only. Errors
> fell from two to zero; fixed and holdout paths stayed identical, so the gates
> accepted it. I was not looking for this bug—and that is why it excited me.

### 2:45–2:55 — Close

**Screen**

- End on the Judge overview and product name.
- Footer: `Inspect · Replay · Docker Godot · OpenAI GPT-5.6`.
- Show the public demo URL and repository URL.

**Voice**

> Playtest Forge makes AI playtesting trustworthy: behavior from GPT-5.6,
> state from Godot, reasoning from Codex, and release decisions from evidence,
> not confidence.

## Accuracy notes

- SteamDB currently reports 9,640 releases for 2020 and 21,391 for 2025. Use
  “roughly 21,400” because retrospective catalog changes can move the count.
  The release count does not itself prove a change in developer team sizes.
- The retained live OpenAI campaign used `gpt-5.6-luna`, real Godot 4.4, six
  personas, seed 42, and a 20-week cap. It produced 114 gameplay records and
  228 sanitized provider-call records with 100% valid decisions, zero fallback,
  and zero provider errors. It is campaign-only evidence, not repair proof.
- `one-strategy` validates the pipeline; `six-strategy` checks same-seed persona
  divergence; `repair-evidence` supplies all six personas across seeds 42, 43,
  and 44 and is the only current profile marked repair-decision ready.
- Profiles are loaded from `config/playtest_session_profiles.json`. The current
  interactive planner supports selecting one of the three frozen profiles and
  overriding the persona only for `one-strategy`; arbitrary per-run profile
  editing is not exposed as an interactive option.
- Campaign completion does not authorize a repair. Codex must receive separate
  user direction before creating an isolated repair experiment, and no patch is
  merged automatically.
- The bilingual choice-identity repair was found and proved through a
  Codex-directed deterministic validation path with zero provider calls. Do not
  attribute that accepted decision to the live GPT-5.6 campaign.

## Capture and publication rules

- Record at 1920×1080, 30 fps. Preload the retained experiments instead of
  spending API credit or waiting for a fresh campaign during the take.
- Hide keys, tokens, raw model responses, prompts, private traces, usernames,
  absolute host paths, unrelated tabs, and desktop notifications.
- Burn in accurate English captions; use no unlicensed music.
- Keep `live OpenAI campaign`, `prerecorded Replay repair proof`, and
  `deterministic zero-model correctness proof` visibly distinct.
- Verify the encoded video remains below 3:00 and works publicly on YouTube
  while signed out.
