# Judge API

The minimal Judge API serves the built frontend and a bounded `/api` surface
from one origin:

```bash
cd frontend && npm run build:public && cd ..
uv run python tools/run_judge_api.py --host 127.0.0.1 --port 8080
```

Or use the default CPU-only container:

```bash
docker compose up -d dashboard
```

## Provider configuration

Replay needs no configuration. To enable the live provider test, set a
restricted server-side environment variable before process startup:

```bash
export OPENAI_API_KEY=...
export OPENAI_PERSONA_MODEL=gpt-5.6-luna
```

The browser never sends, reads, stores, or receives the key. Requests containing
an `api_key` field fail schema validation. `GET /api/provider-status` returns
only a boolean `api_key_configured` flag and the configured model name.

The implementation uses the OpenAI Responses API with `store=False`. The
current OpenAI model guide identifies `gpt-5.6-luna` as the efficient,
high-volume member of the GPT-5.6 family, which fits short persona decisions:

- [Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Current GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model.md)

`POST /api/provider-test` makes one short live request only after an explicit
user action and only when the server key exists. A live campaign additionally
requires a real `GAME_PROJECT_PATH`, Godot runtime, and an enabled governed live
runner. Missing prerequisites return typed `503` errors and never fall back to
Replay while claiming live execution.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/provider-status` | Replay/OpenAI availability without secrets |
| POST | `/api/provider-test` | Explicit Replay verification or short OpenAI probe |
| POST | `/api/campaigns` | Start a bounded Replay or governed live campaign |
| GET | `/api/campaigns/{id}` | Read status and sanitized result |
| GET | `/api/campaigns/{id}/events` | Read ordered server-sent events |
| POST | `/api/campaigns/{id}/cancel` | Request cancellation |
| GET | `/api/experiments/{id}` | Read the one committed public repair experiment |

Campaign requests accept only `provider`, up to three known `personas`, up to
three unique `seeds`, and `max_weeks` from 1 to 5. Bodies are limited to 32 KiB,
at most two jobs may be active, IDs are server generated, and experiment access
is allowlisted to the public bundle.

All failures return:

```json
{
  "error": {
    "code": "stable_machine_code",
    "message": "sanitized explanation",
    "remediation": "specific next action"
  }
}
```

SDK exceptions and environment values are not serialized.

## Frontend states

The root route is the evaluator narrative: Campaign → Repair → Proof. Replay
is the deterministic default; OpenAI is selectable only when the server says
the restricted key and game runtime are ready. The browser has no key input.
Campaign status and typed remediation are announced through an accessible live
region, and pass/fail states use text and symbols in addition to color.

`tools/build_judge_frontend_demo.py` regenerates the sanitized static fixture
from the verified public repair bundle. `npm run prepare:public` copies it into
the build beside the legacy report archive. If `/api/experiments/...` is
unreachable, the UI loads that fixture, labels the page `Static evaluator
copy`, and disables campaign controls rather than simulating success.
