# 20-week persona campaign runbook

This is the pre-release path for testing the agent project against the embedded
real Godot game. It is not a game-polish loop. A run proves that a governed
persona provider can make legal weekly decisions, retain auditable evidence,
and publish the actual path to Playthrough Inspector.

## Evidence rules

- Provider identity is frozen before the first call. Replay, local vLLM, and
  live OpenAI are never relabelled as one another.
- Every campaign uses a hash-pinned writable copy of the embedded game.
- The agent worktree must be clean so the recorded commit/tree identity is
  truthful. Commit the implementation under test before starting a retained
  campaign.
- No fallback week is accepted as a completed campaign.
- One persona is enough to validate transport, gameplay, retention, and UI.
  It is not enough to authorize a repair target. Target selection still
  requires at least two runs across at least two personas.
- `max_weeks=20` means the complete first-semester cap. The game may finish on
  the nineteenth decision while the resulting state is week 20; that is a
  complete semester, not a truncated smoke test.

## Frozen menu

Codex and manual operators must derive commands from the same profile catalog:

```bash
.agents/skills/playtest-forge/scripts/session-options --provider vllm --json
.agents/skills/playtest-forge/scripts/session-options --provider openai --json
```

The outputs preserve the same personas, seeds, duration, budgets, service,
Godot probe, progress publishing, and gates. They differ only by provider
command and truth. A configured key does not authorize a call; the user must
confirm provider and profile first.

## 1. Local preflight: one strategy

Start the real Godot sidecar and local model, then run Newbie with seed 42:

```bash
docker compose up -d godot vllm
PERSONA_MAX_RUNS=1 \
PERSONA_MAX_WEEKS=20 \
PERSONA_MAX_CONCURRENCY=1 \
PERSONA_MAX_CALLS=50 \
scripts/run-persona-campaign vllm \
  --persona newbie \
  --seed 42 \
  --max-weeks 20 \
  --no-resume
```

The command fails before gameplay if the configured model is not exposed by
`VLLM_BASE_URL`, the call budget is below the 40-call decision-plus-event
worst case, the worktree is dirty, or the game runtime is not hash-pinned.
The retained source label is `local-vllm-real-godot`.

## 2. Inspect retained evidence

A successful run writes:

- raw cell records under `reports/persona-campaigns/<campaign>/cells/`;
- a sanitized public bundle under
  `reports/persona-campaigns/<campaign>/public/`;
- frontend-ready views under `frontend/public/live-playthrough/`;
- a sanitized `session.json` updated after each completed weekly decision and
  polled by the frontend every 1.5 seconds;
- `repair_eligibility.json`, which is expected to say `eligible: false` for
  the single-persona preflight.

Run the frontend and open `/playthrough-inspector`. It automatically prefers
Latest campaign when generated evidence exists and retains Signed Replay as a
manual fallback.

```bash
cd frontend
npm run dev
```

## 3. Full six-strategy local rehearsal

After the single strategy passes, use all six personas. The worst-case call
budget is `6 × 20 × 2 = 240`; 260 leaves a small operational margin.

```bash
PERSONA_MAX_RUNS=6 \
PERSONA_MAX_WEEKS=20 \
PERSONA_MAX_CONCURRENCY=4 \
PERSONA_MAX_CALLS=260 \
scripts/run-persona-campaign vllm \
  --persona newbie \
  --persona study \
  --persona money \
  --persona social \
  --persona visa \
  --persona slacker \
  --seed 42 \
  --max-weeks 20 \
  --concurrency 4 \
  --no-resume
```

A repair target is emitted only if the resulting cluster actually satisfies
the cross-persona contract. The service does not weaken that rule to make a
demo look successful.

## 4. Live OpenAI validation

Only after the local campaign and all offline gates pass, run the same Newbie
cell with the configured server-side key and Luna model:

```bash
PERSONA_MAX_RUNS=1 \
PERSONA_MAX_WEEKS=20 \
PERSONA_MAX_CONCURRENCY=1 \
PERSONA_MAX_CALLS=50 \
scripts/run-persona-campaign openai \
  --persona newbie \
  --seed 42 \
  --max-weeks 20 \
  --no-resume
```

The browser never receives the key, prompts, or raw model outputs. Public call
records contain only sanitized metadata, usage, status, and bounded errors.
The retained source label is `live-openai-real-godot`.

Do not run the six-strategy OpenAI campaign until the single live cell passes.
If it is later required, use the same six-persona command as the local rehearsal
with provider `openai` and the 260-call cap.
