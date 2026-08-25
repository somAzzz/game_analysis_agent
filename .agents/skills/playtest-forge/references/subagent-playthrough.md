# Persona and subagent playthroughs

Treat a playthrough agent as a bounded player, not a code reviewer.

## Persona contract

Define each persona by intent, risk tolerance, priorities, forbidden
meta-knowledge, and designed success/failure expectations. Give every worker
only the observable game state, legal actions/choices, recent consequences,
and the typed response schema. Do not reveal source code, target thresholds,
holdout seeds, or the desired bug.

Require structured fields such as selected action, selected choice, brief
intent, confidence, and any perceived blocker. Validate the selected IDs
against the current legal set. Permit at most one bounded schema repair; then
fail the step visibly.

## Run discipline

Select the provider before execution and never change it inside a cohort:

- `replay`: committed deterministic fixture, labelled `prerecorded`;
- `vllm` / `sglang`: fresh local model calls, labelled `local`;
- `openai` / `deepseek`: fresh remote calls, labelled `live`.

For this repository, use `scripts/run-persona-campaign <provider>` for non-Replay full-semester campaigns. It routes through the typed persona campaign service, real Godot probe, sanitized public bundle, and `frontend/public/live-playthrough` view. Use `.agents/skills/playtest-forge/scripts/run-campaign replay` only for the canonical committed Replay campaign.

- Keep steps sequential inside a playthrough; parallelize independent cells.
- Bound personas, seeds, weeks, concurrency, retries, tokens, and wall time.
- Persist actual provider/model, response ID, latency, refusal, retry, usage,
  and error category without storing secrets or raw private prompts publicly.
- Never continue a failed live call with Replay while preserving a `live`
  label.
- Save a decision fixture only after schema and privacy review; hash it for
  later Replay.
- A 20-week request may finish after 19 decisions when the resulting game state is week 20; retain both values explicitly.
- One clean persona validates transport, gameplay, retention, and UI only. It cannot authorize a repair target; require cross-persona evidence for repair selection.

## Interpret behavior

Use persona differences to locate design problems:

- different intentions, same failure state → shared mechanic or forced funnel;
- same situation, implausibly identical choices → prompt/schema affordance or
  insufficient action differentiation;
- repeated stated intent but unavailable action → content/route accessibility;
- legal action with surprising consequence → feedback, copy, or mechanic bug;
- worker confusion with valid state → UX/semantic issue, not automatically a
  numeric balance defect.

Codex must corroborate qualitative explanations with state transitions before
editing. Persona text is an inference source; engine telemetry is state truth.
