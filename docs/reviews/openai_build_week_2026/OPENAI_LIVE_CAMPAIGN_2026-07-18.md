# Live OpenAI campaign review — 2026-07-18

Status: **verified campaign; repair proof not run**

## Frozen contract

- Provider/model: OpenAI Responses API, `gpt-5.6-luna`
- Runtime: real Godot 4.4 through the Docker Godot wrapper
- Personas: newbie, study, money, social, visa, slacker
- Seed: 42
- Horizon: 20-week cap
- Truth label: `live-openai-real-godot`
- Source agent revision: `fb1a09ac14b35396c7424b5066c28196a7896889`
- Canonical game revision: `348b9fd5501e71ebc7142e10f9068fc1490b5124`

## Result

The campaign gate passed. All 6/6 cells completed with 114 retained gameplay
records and 228 sanitized provider-call records. Valid decision rate was 1.0;
fallback and provider-error rates were both 0.0. Mean maximum stress was 100.0.
All six personas entered both the cashflow/stress attractor and burnout-risk
clusters. This independently agrees with the earlier pressure/burnout finding;
it does not prove a fix.

## Public evidence and UI

The committed campaign bundle is under
`examples/build_week_2026/experiments/openai-all-six-seed-42-20w/campaign`.
The replayable derived views are under the sibling `playthrough` directory.
The experiment registry verifies the public campaign gate and every published
derived-view hash before listing the experiment. The static builder copies it
to the Judge selector and per-experiment Playthrough Inspector path.

Published records contain aggregate/persona gameplay facts, call status,
latency, usage, model, and response identifiers. They do not contain prompts,
model response bodies, API keys, authorization headers, private session files,
or the raw generated runtime/cell directories.

## Decision boundary

The Judge intentionally displays this experiment as **CAMPAIGN ONLY**. The run
is sufficient to demonstrate the live provider, real-game integration,
retention, public-gate, and replay UI. It is not a repair experiment: no bounded
patch, fixed cohort, unseen holdout cohort, machine repair recommendation, or
human decision was produced. No game change is accepted or merged from this
campaign.
