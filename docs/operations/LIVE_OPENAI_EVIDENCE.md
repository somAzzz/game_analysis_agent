# Live OpenAI evidence run

This run is optional for local development but required before claiming the
Build Week `live_openai_campaign` row. It uses the official OpenAI Responses
API from the server process and never sends a credential to the browser.

## Configure

Create a local ignored file:

```bash
cp .env.example .env
```

Set only these competition values:

```dotenv
PERSONA_PROVIDER=openai
OPENAI_API_KEY=your-restricted-project-key
OPENAI_PERSONA_MODEL=gpt-5.6-luna
```

`OPENAI_API_KEY` is the standard variable read by the OpenAI SDK. The official
endpoint is `POST https://api.openai.com/v1/responses`; no base-URL override is
needed. Do not create `VITE_OPENAI_API_KEY`, put the key in frontend code, paste
it into screenshots, or pass it in a Judge API request body.

Run from a clean `OpenAI-build-week-2026` worktree:

```bash
scripts/run-p4-live-openai
```

The script loads the repository-root `.env`, prepares an isolated writable copy
of the embedded game when needed, runs one bounded Persona/seed campaign, and
writes private runtime artifacts below `reports/platform-live-openai/`. The
entire `reports/` tree is ignored by Git.

## What may be retained publicly

The generated platform-evidence record may retain only:

- provider and exact returned model family;
- response IDs sufficient for audit;
- completed call/cell/week counts;
- aggregate input, output, and total token usage;
- aggregate latency, retry, refusal, parse, and error categories when present;
- source revision, delivery-contract hash, timestamps, and artifact hashes.

Do not publish:

- API keys, authorization headers, organization/project secrets, or `.env`;
- raw system/user prompts or raw model responses;
- private game text, complete private traces, or unbounded logs;
- absolute host paths, usernames, IP addresses, or unrelated environment data;
- screenshots of terminals or dashboards that expose any of the above.

The committed platform evidence is produced by
`tools/record_platform_evidence.py`. It rejects obvious key material, requires
`mode=live`, a GPT-5.6-family model, completed provider calls and response IDs,
and an explicit `outputs_recorded=false`. It never relabels Replay as live.

Before staging any evidence, inspect it and run the repository secret gate:

```bash
jq . reports/platform-live-openai/evidence.json
uv run python tools/review_build_week_g1.py --json
uv run python tools/review_build_week_g4.py --json
```

Only copy/import the sanitized evidence record into
`docs/reviews/openai_build_week_2026/platform-evidence/`. Keep the raw run under
ignored `reports/`, then review `git diff --cached` before committing.

Official references:

- [Create a response](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [API key safety](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)
