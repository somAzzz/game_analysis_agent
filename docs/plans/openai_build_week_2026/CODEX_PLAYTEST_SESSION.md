---
status: implemented
updated: 2026-07-18
audience: Build Week evaluators, maintainers, Codex operators
scope: Codex-first full-semester playtest orchestration
---

# Codex-first playtest session

This update turns `playtest-forge` into the primary operator interface for a
complete agent-project validation. The user opens Codex, selects the Skill,
and receives a read-only evidence viewer before choosing local or Docker Godot
and OpenAI API, local vLLM, or no LLM. Model-backed runs connect the governed
API only after all required choices are frozen, then publish each completed
week to the same viewer. The goal is to prove the agent project can test and
repair a game; it is not a mandate to polish the demo.

## User flow

1. Open this repository in Codex and select `$playtest-forge`.
2. Ask to start a game test.
3. Codex runs offline preflight, starts the read-only Vite evidence viewer, and
   gives the URL. This stage does not start Judge API, Godot, or an LLM.
4. Codex asks two required questions: local or Docker Godot, then OpenAI API,
   local vLLM, or no LLM.
5. Codex probes only the selected paths without a provider call. No LLM keeps
   the static viewer open, routes to deterministic automation plus committed
   Replay, and skips persona profiles.
6. For a model-backed run, Codex presents the three frozen profiles below. The
   user confirms the profile and the persona for a one-strategy run.
7. With every choice frozen, Codex starts Judge API using the selected
   `GODOT_BIN`, asks the user to refresh the existing viewer, and executes the
   exact generated campaign command.
8. The inspector updates the sanitized session card after every completed
   weekly decision. Codex also reports meaningful progress during long runs.
9. Only after final bundle and view gates pass does the complete campaign
   replace the previous generated evidence.
10. Codex reports what the run proved and offers the next bounded choice. It
    never changes runtime/provider, spends more credit, or edits the game
    without a new user decision.

Frontend URL:

```text
http://127.0.0.1:5173/#/playthrough-inspector
```

## Frozen profiles

| Profile | Personas and seeds | Duration | Worst case | Cap | Decision boundary |
| --- | --- | ---: | ---: | ---: | --- |
| `one-strategy` | one chosen persona, seed 42 | 20 weeks | 40 calls | 50 | validates provider, agent, real Godot, retention, UI; no repair target |
| `six-strategy` | all six personas, seed 42 | 20 weeks each | 240 calls | 260 | compares strategies and may expose a cross-persona cluster; not multi-seed repair proof |
| `repair-evidence` | all six personas, seeds 42/43/44 | 20 weeks each | 720 calls | 760 | fixed evidence adequate to freeze one repair target before holdout A/B |

Two model calls per week is the conservative bound: one weekly action decision
and one event choice. A 20-week campaign can legitimately contain 19 decisions
when the last transition produces state week 20.

The source of truth is
[`config/playtest_session_profiles.json`](../../../config/playtest_session_profiles.json).
Codex reads it through:

```bash
.agents/skills/playtest-forge/scripts/session-options --choices-only --json
.agents/skills/playtest-forge/scripts/session-options \
  --godot-runtime docker-godot \
  --llm-provider local-vllm \
  --json
```

## One pipeline for local and API models

Local and API execution are deliberately isomorphic:

```text
frozen profile
  -> CampaignRequest
  -> run_persona_campaign(...)
  -> governed provider gateway
  -> InteractivePlayerAgent
  -> real Godot probe
  -> raw cell evidence + sanitized public evidence
  -> session.json + final Playthrough Inspector view
```

`vllm`, `sglang`, `openai`, and `deepseek` select only endpoint, credentials,
model, provider mode, and truth label. They do not get separate campaign logic,
budgets, frontend writers, or evidence gates. This makes a local rehearsal a
valid pipeline rehearsal for an API campaign without misrepresenting provider
provenance.

Truth labels remain explicit:

- `local-vllm-real-godot`;
- `local-sglang-real-godot`;
- `live-openai-real-godot`;
- `live-deepseek-real-godot`.

Keys, raw prompts, and raw model responses remain server-side. The browser gets
only whitelisted per-week state and choice identifiers. A provider error fails
the campaign; it never silently becomes Replay or another provider.

## Live update contract

During execution, the service atomically writes:

```text
frontend/public/live-playthrough/session.json
```

The frontend polls it every 1.5 seconds and renders campaign status, provider,
model, cells, recorded weeks, persona, seed, current week, phase, event ID, and
truth label. States have strict meaning:

- `running`: weekly progress, not final evidence;
- `finalizing`: campaign cells stopped, gates still running;
- `completed`: final evidence verified and ready;
- `failed`: sanitized terminal failure, no fallback.

The previous verified generated campaign remains available while a new session
runs. Final playthrough files are rebuilt only after campaign completeness and
public-bundle validation.

## Repair boundary

A single strategy is intentionally sufficient for the first local or OpenAI API
validation requested for the exhibition. It is not enough to choose a game
repair. Repair selection requires the 6 x 3 fixed matrix and a cross-persona
failure cluster. Repair acceptance still requires baseline/patched A/B on fixed
seeds 42/43/44 and unseen holdouts 1042/1043/1044, plus protected invariants,
persona preservation, designed-failure, and provider-health gates.

## Implemented modules

- `src/game_analysis_agent/playtest_session.py`: validates frozen profiles and
  emits exact provider-preserving commands.
- `tools/describe_playtest_session.py` and Skill `scripts/session-options`:
  no-spend conversational menu adapter.
- `src/game_analysis_agent/persona_campaign_service.py`: shared local/API
  campaign pipeline and thread-safe sanitized progress publisher.
- `src/game_analysis_agent/build_week_campaign.py`: forwards interactive weekly
  progress without changing campaign evidence semantics.
- `frontend/src/lib/livePlaythrough.ts` and Playthrough Inspector: no-store
  session polling and completed-evidence handoff.
- `.agents/skills/playtest-forge/references/codex-session-orchestration.md`:
  mandatory Codex conversation, execution, monitoring, and stop rules.

Generated campaign evidence remains ignored by Git. Retained evidence must be
reviewed, sanitized, and intentionally promoted; a live session file is never a
substitute for the signed manifest and gate reports.
