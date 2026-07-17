# Codex-guided playtest session

Use this route when a user selects Playtest Forge and asks to test the game.
The outcome is a governed conversation around one shared campaign pipeline,
not a hidden one-shot script and not a game-polish mandate.

## Non-negotiable provider parity

`vllm`, `sglang`, `openai`, and `deepseek` differ only at the persona gateway.
They must share all of the following:

- `persona_campaign_service.run_persona_campaign(...)`;
- the same frozen profile, personas, seeds, 20-week duration, call accounting,
  concurrency cap, retry rules, cancellation, and no-fallback policy;
- the same hash-pinned writable game, runtime overlay, and real Godot probe;
- the same raw-cell retention, sanitized public bundle, repair eligibility,
  weekly `session.json`, and final Playthrough Inspector view;
- the same validation and evidence gates.

Provider-specific code may select credentials, endpoint, model, provider mode,
and truth label only. Credentials stay server-side. Never write prompts, raw
responses, keys, or private traces to `session.json` or frontend assets.

## Conversation protocol

### 1. Readiness without spend

From the repository root, run:

```bash
.agents/skills/playtest-forge/scripts/preflight
.agents/skills/playtest-forge/scripts/session-options --provider vllm --json
```

Also inspect `.env` by field presence only, Docker/Godot availability, local
model availability, and any existing `frontend/public/live-playthrough`
session. Do not echo secret values. These checks must not call a model.

### 2. Present the frozen menu

Offer the following choices, including their purpose and upper bounds:

| Profile | Matrix | Worst-case calls | Operational cap | What it can prove |
| --- | ---: | ---: | ---: | --- |
| `one-strategy` | chosen persona x seed 42 x 20 weeks | 40 | 50 | provider, agent, Godot, retention, weekly UI |
| `six-strategy` | 6 personas x seed 42 x 20 weeks | 240 | 260 | same-seed behavioral divergence and possible cross-persona target eligibility |
| `repair-evidence` | 6 personas x seeds 42/43/44 x 20 weeks | 720 | 760 | fixed evidence adequate to select one repair target |

A complete 20-week request can end after 19 decisions when the resulting state
is week 20. Say this before execution so the user does not misread it as an
incomplete run.

Ask the user to choose:

1. profile;
2. provider: local `vllm`/`sglang` or API `openai`/`deepseek`;
3. persona when `one-strategy` is selected.

Recommend `one-strategy` with local vLLM first. If that succeeds, recommend
`six-strategy` locally. Use the API only when the user explicitly selects it.
Never infer permission to consume API credit from the presence of a key.

Use the planner again with the confirmed values, for example:

```bash
.agents/skills/playtest-forge/scripts/session-options \
  --provider openai --profile one-strategy --persona newbie --json
```

Run the emitted environment and command exactly. Do not hand-maintain a second
OpenAI command or change the matrix between local and API comparisons.

### 3. Start the viewer first

Start the frontend in a persistent terminal:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1
```

Give the user this URL before the campaign begins:

```text
http://127.0.0.1:5173/#/playthrough-inspector
```

The browser polls `frontend/public/live-playthrough/session.json` every 1.5
seconds. Each completed weekly decision updates the session card. The previous
verified campaign remains selectable until the new campaign completes all
gates; then the complete sanitized paths replace it atomically.

### 4. Execute and monitor

Run one campaign command in a persistent terminal. Monitor both process output
and `session.json`, and tell the user when cells start, weekly records advance,
final validation begins, or a failure occurs. During long calls, provide a
concise progress update at least every 60 seconds.

Treat these session states as follows:

- `running`: weekly UI telemetry only;
- `finalizing`: all cells stopped; bundle and view gates are still running;
- `completed`: final sanitized evidence passed and can be cited;
- `failed`: stop; report the sanitized error and do not silently fall back.

Never cite `session.json` as completed repair evidence. Cite the final campaign
manifest, gate report, cell rows, and their hashes only after `completed`.

### 5. Close the conversational loop

After completion, report:

- provider, model, mode, and exact truth label;
- completed cells, recorded decisions/weeks, calls used, endings, and gate;
- frontend evidence URL and retained bundle paths;
- whether `repair_target_eligible` is true;
- what the selected profile cannot prove.

Then offer the next bounded choice. Do not automatically start another cohort,
spend API credit, choose a repair, edit the game, or merge anything.

## Repair boundary

`one-strategy` validates the project pipeline only. `six-strategy` may expose a
cross-persona cluster but has only one fixed seed. Use `repair-evidence` before
freezing a repair target, then follow `repair-protocol.md`: preserve fixed seeds
42/43/44, use unseen holdouts 1042/1043/1044, change one mechanism in an
isolated game worktree, and accept or reject against all protected gates.
