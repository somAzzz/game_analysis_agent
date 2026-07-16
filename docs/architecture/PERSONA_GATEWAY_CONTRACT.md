---
status: active
date: 2026-07-16
audience: maintainers, OpenAI Build Week judges
scope: provider-neutral interactive persona decision boundary
---

# Persona gateway contract

P1 keeps one gameplay decision contract while allowing Replay, OpenAI, and the
existing local providers to supply decisions. Provider SDK objects, HTTP
payloads, UI state, and CLI namespaces stop at their adapters.

## Existing provider-call inventory

| Call site | Current call | Required gateway operation |
| --- | --- | --- |
| `InteractivePlayerAgent._decide_one_week` | `LocalLLMClient.chat` returning JSON text | `PersonaDecisionGateway.decide` returning `PlayerDecision` |
| `InteractivePlayerAgent._decide_event_choice` | `LocalLLMClient.chat` returning `event_choice_id` JSON | `PersonaDecisionGateway.choose_event` returning `PersonaEventChoice` |
| Non-interactive QA agents | `LocalLLMClient.chat` | Out of P1 gateway scope; retained for existing local analysis |
| Legacy `tools/run_agent.py` fallback | `LegacyLocalLLMClient.chat` | Out of Judge/Persona path; retained only for compatibility |

The narrow seam is the interactive player. P1 does not refactor general QA,
CLI orchestration, Godot execution, or create an MCP adapter.

## Shared types

- `WeekContext`, `PlayerDecision`, and `DecisionValidation` remain the gameplay
  source of truth.
- `PersonaDecisionRequest` binds the context to a canonical state hash.
- `PersonaEventChoiceRequest` additionally binds the already selected actions.
- Request fingerprints cover decision kind, request ID, persona, seed, week,
  state hash, event ID, available event-choice IDs, and selected actions.
- `PersonaDecisionResult` and `PersonaEventChoiceResult` expose the same status,
  error, usage, latency, parse, refusal, provider, model, and response ID fields.

Replay fixtures and live responses must validate into these types before they
reach gameplay. A completed result always has a typed value and no error; a
failed or cancelled result always has a typed sanitized error and no value.

## Error categories

The stable categories are configuration, authentication, refusal, timeout,
rate limit, transport, malformed response, invalid decision, budget exhausted,
cancelled, and fixture mismatch. Adapters may retain provider details in local
debugging, but reports receive only the sanitized common error.

## Boundary rules

1. No OpenAI SDK response, local backend response, `argparse.Namespace`, or UI
   object crosses `PersonaDecisionGateway`.
2. API keys and authorization headers are not contract fields.
3. Replay is explicitly `provider=replay, mode=replay`; it cannot be reported
   as a live success.
4. OpenAI is explicitly `provider=openai, mode=live`; a failed live request is
   a failed live result, not an implicit Replay decision.
5. Local providers are `mode=local` and must use the same `PlayerDecision` and
   event-choice validation semantics.

## Runtime selection and limits

`PERSONA_PROVIDER=auto` is resolved once before campaign execution: a usable
server-side `OPENAI_API_KEY` selects OpenAI, otherwise hash-pinned Replay is
selected. Explicit `openai` or `deepseek` selection without its required key
fails preflight. A live timeout, rate limit, refusal, or malformed result never
causes an in-progress campaign to change providers.

`GovernedPersonaGateway` applies validated caps for runs, weeks, concurrency,
provider calls, retries, and exponential backoff. Its cancellation token is
cooperative, and call budget/concurrency counters are thread-safe. Retryable
calls retain their original provider/mode metadata; exhausted budgets and
cancellation produce typed failures without invoking the provider. API keys
are excluded from serialized settings and common key/header forms are redacted
before provider failures reach reports.

## Interactive-player integration

The interactive player now depends on `PersonaDecisionGateway` only at its two
decision points. `LocalChatPersonaGateway` adapts the existing vLLM, SGLang,
and DeepSeek clients, while Replay and OpenAI use their native adapters. Each
adapter gets one structured-output repair and then returns a typed failure;
the player may keep the Godot loop moving with a deterministic action, but
records that action as `fallback_used=true` and preserves the failed provider
metadata in `playthrough.jsonl`. Provider construction happens once through
`build_persona_gateway`, which wraps the selected adapter with the P1.4 runtime
limits and never installs a secondary provider.
