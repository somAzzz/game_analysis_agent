# Operations

Deployment and runtime docs for operators. All evergreen.

1. [RUN_PROJECT.md](RUN_PROJECT.md) — complete local agent, frontend viewer, Codex skill, and dashboard API paths
2. [JUDGE_API.md](JUDGE_API.md) — bounded Replay/OpenAI dashboard API and secret boundary
3. [DOCKER.md](DOCKER.md) — CPU dashboard and opt-in runtime profiles
4. [SGLANG_QWEN_LOCAL_AGENT.md](SGLANG_QWEN_LOCAL_AGENT.md) — primary local SGLang + Qwen3.8 hybrid APC/DFlash2 deployment with DSpark rollback
5. [SGLANG_DFLASH2_MIGRATION_2026-08-20.md](SGLANG_DFLASH2_MIGRATION_2026-08-20.md) — accepted DFlash2 migration pins, benchmark, contract checks, and rollback record
6. [VLLM_QWEN_LOCAL_AGENT.md](VLLM_QWEN_LOCAL_AGENT.md) — retained vLLM baseline and fallback
7. [INFERENCE_AB_BENCHMARK.md](INFERENCE_AB_BENCHMARK.md) — APC-only versus MTP3-only benchmark and visualization plan
8. [PERSONA_CAMPAIGN_RUNBOOK.md](PERSONA_CAMPAIGN_RUNBOOK.md) — 20-week local rehearsal, live provider validation, retained UI evidence
9. [GAME_CONTRACT_TESTING.md](GAME_CONTRACT_TESTING.md) — embedded-demo contract and real Godot smoke
10. [REPORTS_FORMAT.md](REPORTS_FORMAT.md) — locked `reports/` layout, manifest schemas, validator, and cleanup workflow

These docs describe how to run the agent against a real Godot project and
how to keep the local inference stack reproducible. See [../README.md](../README.md)
for the audience-keyed top-level index.
