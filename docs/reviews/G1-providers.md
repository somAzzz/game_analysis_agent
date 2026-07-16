---
status: passed
date: 2026-07-16
audience: maintainers, OpenAI Build Week judges
scope: persona provider correctness, failure truthfulness, and secret boundary
---

# G1 review — persona providers and security

**Decision:** Passed on 2026-07-16, with the submission-only OpenAI live smoke
explicitly recorded as `not_run`.

Replay is now a complete no-network/no-key path, OpenAI behavior is covered by
mocked Responses API tests, and the existing local providers share the same
typed decision boundary. A live campaign cannot silently change to Replay
after an OpenAI failure. The one-call live smoke remains a release prerequisite
and can be run only when a restricted submission key is supplied explicitly.

## Reviewed revisions

- G1 review base: `201e4a6` (post-G0 documentation correction).
- P1 implementation range: `0631b06` through `1bd5965`.
- Reviewed head: `1bd59658de0a0ac23246d0e5a117b6ec2da9028c`.
- Replay fixture SHA-256:
  `c180208d4c3bb6278e68b03d3c23c22e204ab526339f2b93a0ad6f55d218dea8`.

## Exact review command

```bash
. .tools/build-week/env.sh
export GAME_PROJECT_PATH="$PWD/reports/build-week-2026/game-source"
uv run python tools/review_build_week_g1.py --json
```

The machine-readable result is written to the ignored evidence path
`reports/build-week-2026/reviews/G1-provider-security.json`.

## Automated result

The G1 reviewer reported 9 checks: 8 passed, 0 failed, and 1 `not_run`.

- Provider-focused suite: 34 passed.
- Full Python suite with the real game contract: 335 passed, zero skipped.
- Ruff: passed.
- Frontend public production build: passed with Vite 8.1.5.
- Replay manifest and fixture hash: passed.
- Browser boundary: 49 source files checked, zero server-key references.
- Secret scan: the complete P1 Git diff, command output, Build Week reports,
  and built frontend were checked; 87 artifact files produced zero findings.
- OpenAI live smoke: `not_run` because no restricted submission key was
  supplied. The reviewer exposes an explicit `--live-smoke` one-request path
  and never spends an ambient key automatically.

The first secret-scan trial correctly exposed an over-broad detector rather
than a credential: minified CSS identifiers containing `mask-...` matched a
naive `sk-` expression. The detector now requires a token boundary and
high-entropy key length, with regression tests covering both real signatures
and this CSS false-positive class.

## Independent review answers

- **Is an OpenAI key accepted by or returned to the browser?** No. It is read
  only by server-side `PersonaRuntimeSettings`, excluded from serialization,
  absent from frontend source/bundle settings, and never written to provider
  result envelopes.
- **Can an API error become a false passing Replay result?** No. `auto` resolves
  once before execution. The factory constructs one provider and installs no
  fallback branch. Timeouts, rate limits, refusals, malformed output, budget
  exhaustion, and cancellation remain typed failures under the original
  provider/mode.
- **Do local and OpenAI workers share the contract?** Yes. Replay, OpenAI mock,
  and vLLM integration tests pass the same `WeekContext` through
  `PersonaDecisionGateway` and produce the same legal action and event choice.
- **Are repairs and retries bounded?** Yes. Provider schema repair is limited
  to one attempt; runtime transport retries are independently capped at three
  by validation and default to one. Call count, runs, weeks, concurrency, and
  backoff all have hard validated maxima.
- **Are refusals visible?** Yes. OpenAI refusal content becomes a sanitized
  `refusal` failure and is retained in provider metadata; it is never converted
  to a completed decision.

## OpenAI API design basis

The adapter follows the official Responses API structured-output pattern used
by the Python SDK: Pydantic schemas are passed to `responses.parse`, parsed
values are read from the response, and refusal output is handled explicitly.
Provider response ID, actual model, usage, cumulative latency, parse/repair
status, and sanitized refusal are preserved without allowing SDK objects across
the shared contract.

## Remaining release condition

Before G5, run the following only with a restricted competition key and retain
the resulting response ID/model/usage evidence. The command performs exactly
one stored-disabled structured request and never records response text or the
key.

```bash
OPENAI_API_KEY=... uv run python tools/review_build_week_g1.py --live-smoke --json
```

This missing external credential does not weaken or block Replay, local mocks,
P2 campaign work, or the passed G1 safety claims. It does block the final claim
that the submission's live OpenAI path was exercised against the service.
