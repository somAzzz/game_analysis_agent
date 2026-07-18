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

### 1. Run preflight and open the read-only evidence viewer

From the repository root, run:

```bash
.agents/skills/playtest-forge/scripts/preflight
.agents/skills/playtest-forge/scripts/session-options --choices-only --json
```

These commands must not start Godot or call a model. Inspect `.env` by field
presence only and inspect any retained `frontend/public/live-playthrough`
session without printing secret values.

Immediately stage the committed public evidence and start Vite in a persistent
terminal:

```bash
npm --prefix frontend run prepare:public
npm --prefix frontend run dev -- --host 127.0.0.1
```

Give the user this URL before asking either mandatory choice:

```text
http://127.0.0.1:5173/#/playthrough-inspector
```

At this stage the browser is a read-only view of retained signed/local evidence.
Do not start `scripts/run-judge-dev`: doing so would load a Godot default before
the user chooses a runtime. Provider-backed actions remain unavailable until
the governed API is connected. Starting this viewer must not probe Godot or
call a model.

### 2. Ask the two mandatory choices

The first user-facing menu must ask and wait for both answers:

1. Godot runtime:
   - `local-godot` — use a host Godot 4.4 executable;
   - `docker-godot` — use `scripts/godot-docker-wrapper`.
2. LLM:
   - `openai-api` — live OpenAI persona decisions and possible API cost;
   - `local-vllm` — fresh local vLLM persona decisions;
   - `none` — deterministic automation and committed Replay, zero model calls.

Do not preselect either answer because a binary, Docker daemon, endpoint, or key
is present. Availability is readiness evidence, not user authorization.

### 3. Probe only the selected runtime and provider

For `local-godot`, resolve `GODOT_BIN`, then run `"$GODOT_BIN" --version`.
Require the pinned Godot 4.4 family before a fresh real-game run. Do not silently
fall back to Docker.

For `docker-godot`, verify Docker, then run:

```bash
scripts/godot-docker-wrapper --version
```

Require the pinned Godot 4.4 family. Do not silently fall back to a host binary.

For `openai-api`, check server-side `OPENAI_API_KEY` and model fields without
printing their values. Do not call the API during readiness. For `local-vllm`,
check the configured endpoint/model and generation-health readiness without
starting a campaign. For `none`, perform no provider check.

A selected path that is unavailable is `unsupported`. Ask the user to choose a
different path or remediate it; do not switch automatically.

### 4. Branch on the LLM choice

#### No LLM

Run the planner only to freeze the runtime and truth boundary:

```bash
.agents/skills/playtest-forge/scripts/session-options \
  --godot-runtime docker-godot \
  --llm-provider none \
  --json
```

Use `--godot-runtime local-godot --godot-bin /resolved/godot4` for a local
binary. Then read `references/automated-testing.md` and ask which deterministic
matrix, focused test, boundary sweep, or Replay inspection the user wants.

This route has zero model calls and no persona campaign profiles. Keep the
static viewer open for retained evidence. Fresh Godot automation may create new
state evidence; committed Replay only proves reproducibility. Neither is fresh
persona-worker evidence, and a deterministic run is not automatically a live
persona campaign in the viewer.

#### OpenAI API or local vLLM

After the two initial choices are confirmed, present the frozen profiles:

| Profile | Matrix | Worst-case calls | Operational cap | What it can prove |
| --- | ---: | ---: | ---: | --- |
| `one-strategy` | chosen persona x seed 42 x 20 weeks | 40 | 50 | provider, agent, Godot, retention, weekly UI |
| `six-strategy` | 6 personas x seed 42 x 20 weeks | 240 | 260 | same-seed behavioral divergence and possible cross-persona target eligibility |
| `repair-evidence` | 6 personas x seeds 42/43/44 x 20 weeks | 720 | 760 | fixed evidence adequate to select one repair target |

A complete 20-week request can end after 19 decisions when the resulting state
is week 20. Say this before execution.

Ask for the profile and, for `one-strategy`, the persona. The user has already
selected the Godot runtime and LLM, so do not ask those questions again unless
readiness failed or the user changes scope. Never infer permission to spend API
credit from the presence of a key.

Use the planner with all confirmed values. Examples:

```bash
.agents/skills/playtest-forge/scripts/session-options \
  --godot-runtime docker-godot \
  --llm-provider openai-api \
  --profile one-strategy \
  --persona newbie \
  --json
```

```bash
.agents/skills/playtest-forge/scripts/session-options \
  --godot-runtime local-godot \
  --godot-bin /resolved/godot4 \
  --llm-provider local-vllm \
  --profile six-strategy \
  --json
```

Local and API providers must keep the same matrix, limits, evidence service,
and frontend path.

### 5. Connect the Judge API after the runtime is frozen

Keep the Vite process from step 1 running. After Godot, LLM, profile, and any
required persona are confirmed, start the governed API in a separate persistent
terminal with the selected runtime:

```bash
GODOT_BIN=/resolved/godot4 \
  scripts/run-judge-dev --host 127.0.0.1 --port 8080
```

Use this form for Docker Godot:

```bash
GODOT_BIN="$PWD/scripts/godot-docker-wrapper" \
  scripts/run-judge-dev --host 127.0.0.1 --port 8080
```

An explicit `GODOT_BIN` must win over `.env`. `scripts/run-judge-dev` still
loads provider configuration server-side and enables the governed Judge
adapter. Vite proxies only `/api` to port 8080; no credential is exposed to the
browser. Ask the user to refresh the already-open page after the API starts.
Never run a Judge action campaign concurrently with the full campaign command.

Now run the planner-emitted environment and campaign command exactly. The
browser polls `frontend/public/live-playthrough/session.json` every 1.5 seconds.
Local and API campaigns publish through the same campaign service. The previous
verified experiment remains selectable until the new campaign passes every
final gate.

### 6. Execute and monitor

Run one emitted campaign command in a persistent terminal. Monitor process
output and `session.json`, and report when cells start, weekly records advance,
final validation begins, or a failure occurs. During long calls, provide a
concise progress update at least every 60 seconds.

Treat session states as follows:

- `running`: weekly UI telemetry only;
- `finalizing`: all cells stopped; bundle and view gates are still running;
- `completed`: final sanitized evidence passed and can be cited;
- `failed`: stop; report the sanitized error and do not silently fall back.

Never cite `session.json` as completed repair evidence. Cite the final campaign
manifest, gate report, cell rows, and hashes only after `completed`.

### 7. Close the conversational loop

After completion, report:

- selected Godot runtime and resolved executable/wrapper;
- LLM choice, provider, model, mode, and exact truth label;
- completed cells, recorded decisions/weeks, calls used, endings, and gate;
- frontend evidence URL and retained bundle paths;
- whether `repair_target_eligible` is true;
- what the selected route/profile cannot prove.

Then offer the next bounded choice. Do not automatically change runtime or
provider, start another cohort, spend API credit, choose a repair, edit the
game, or merge anything.

## Repair boundary

`one-strategy` validates the project pipeline only. `six-strategy` may expose a
cross-persona cluster but has only one fixed seed. Use `repair-evidence` before
freezing a repair target, then follow `repair-protocol.md`: preserve fixed seeds
42/43/44, use unseen holdouts 1042/1043/1044, change one mechanism in an
isolated game worktree, and accept or reject against all protected gates.
