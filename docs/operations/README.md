# Operations

Start with the [Build Week reviewer hub](../plans/openai_build_week_2026/README.md)
for the current platform ledger and known blockers.

Deployment and runtime docs for operators. All evergreen.

1. [RUN_PROJECT.md](RUN_PROJECT.md) — complete local agent, frontend viewer, Codex skill, and Judge API paths
2. [JUDGE_API.md](JUDGE_API.md) — bounded Replay/OpenAI Judge API and secret boundary
3. [DOCKER.md](DOCKER.md) — CPU Judge default and opt-in runtime profiles
4. [LINUX_P4_G4_CLOSEOUT.md](LINUX_P4_G4_CLOSEOUT.md) — native Linux, Docker, Godot, arm64 image, live OpenAI, and evidence import
5. [LIVE_OPENAI_EVIDENCE.md](LIVE_OPENAI_EVIDENCE.md) — `.env`, Responses API, restricted-key run, and public-evidence redaction
6. [VLLM_QWEN_LOCAL_AGENT.md](VLLM_QWEN_LOCAL_AGENT.md) — local vLLM + Qwen model config, JSON fallback
7. [PERSONA_CAMPAIGN_RUNBOOK.md](PERSONA_CAMPAIGN_RUNBOOK.md) — 20-week local rehearsal, live OpenAI validation, retained UI evidence
8. [GAME_CONTRACT_TESTING.md](GAME_CONTRACT_TESTING.md) — embedded-demo contract and real Godot smoke

These docs describe how to run the agent against a real Godot project and
how to keep the local inference stack reproducible. See [../README.md](../README.md)
for the audience-keyed top-level index.
