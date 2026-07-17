# Run the complete agent project

The frontend is the evidence viewer, not the agent runtime. Full 20-week
campaigns run through the typed Python service and real Godot probe. The
frontend then reads the sanitized view published by that service. Codex can
orchestrate the same service through the `playtest-forge` skill.

## One-time setup

From the repository root:

```bash
uv sync --locked
cd frontend
npm ci
cd ..
docker compose up -d godot vllm
```

Keep provider credentials and model settings in the ignored root `.env`. The
browser must never receive an API key.

## Run one complete local campaign

Start with one persona before spending OpenAI credit:

```bash
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

The wrapper verifies the 80-file canonical game snapshot, prepares a writable
runtime, applies the audited bilingual game overlay, runs real Godot, retains
raw and sanitized evidence, and publishes the frontend view. A completed
semester normally contains 19 decisions and ends with game state week 20.

Use `scripts/run-persona-campaign --help` for all options. The six-persona and
live OpenAI commands are in
[PERSONA_CAMPAIGN_RUNBOOK.md](PERSONA_CAMPAIGN_RUNBOOK.md).

## View the retained result

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173/#/playthrough-inspector
```

The inspector prefers `frontend/public/live-playthrough` when a generated
campaign exists. Its truth label must remain `local-vllm`, `local-sglang`,
`live-openai`, or `live-deepseek`; it never relabels local evidence as live.
The EN/中文 control changes event copy only and defaults to English. During a running campaign, the Codex playtest session card polls sanitized weekly progress every 1.5 seconds; completed paths replace prior generated evidence only after final gates pass.

## Run through Codex

Ask Codex to use `$playtest-forge`, for example:

```text
Use $playtest-forge to preflight and run one complete 20-week local-vllm
Newbie campaign, retain the evidence, and verify Playthrough Inspector.
```

First inspect the same frozen menu that Codex uses:

```bash
.agents/skills/playtest-forge/scripts/session-options --provider vllm --json
```

After the user confirms profile, provider, and optional persona, Codex starts
the frontend and executes the emitted command. Local and API providers use the
same typed service, budgets, Godot probe, weekly progress publisher, view, and
gates; only gateway credentials, endpoint, model, and truth label differ.

The equivalent skill execution entry point is:

```bash
.agents/skills/playtest-forge/scripts/run-campaign vllm \
  --persona newbie --seed 42 --max-weeks 20 --no-resume
```

The skill governs preflight, evidence truth, target selection, repair, and
fixed/holdout acceptance. It does not execute inside React and it does not
replace the typed campaign service.

## Judge API and packaged UI

For a single-origin local evaluator build:

```bash
cd frontend
npm run build:public
cd ..
uv run python tools/run_judge_api.py --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/`. The Judge API's interactive browser campaign is
intentionally bounded and is not the full 20-week retention path; use the CLI
or skill command above for complete campaigns.
