# game_analysis_agent documentation

> Start here. Pick the audience that matches you.

## For new contributors / developers

Read these in order:

1. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — complete setup, CLI, testing, and workflow guide
2. [architecture/README.md](architecture/README.md) — how the reference docs fit together
3. [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) — component map and data flow
4. [architecture/DATA_CONTRACTS.md](architecture/DATA_CONTRACTS.md) — report and manifest schema
5. [architecture/GAMEPLAY_AGENT.md](architecture/GAMEPLAY_AGENT.md) — what each LLM agent does
6. [architecture/GODOT_INTEGRATION.md](architecture/GODOT_INTEGRATION.md) + [INTEGRATION_WITH_STUDY_IN_GERMANY.md](architecture/INTEGRATION_WITH_STUDY_IN_GERMANY.md) — how to plug in the reference game
7. [architecture/MCP_MIGRATION_PLAN.md](architecture/MCP_MIGRATION_PLAN.md) — service-first MCP roadmap

## For operators / deployment

1. [operations/README.md](operations/README.md) — Docker + vLLM as one story
2. [operations/DOCKER.md](operations/DOCKER.md) — compose stack, sidecars, Godot wrapper
3. [operations/VLLM_QWEN_LOCAL_AGENT.md](operations/VLLM_QWEN_LOCAL_AGENT.md) — model config + JSON fallback
4. [operations/GAME_CONTRACT_TESTING.md](operations/GAME_CONTRACT_TESTING.md) — cross-repo contract test plan

## For portfolio / public readers

1. [portfolio/README.md](portfolio/README.md) — live demo link + scope
2. [portfolio/PORTFOLIO.md](portfolio/PORTFOLIO.md) — scope and limitations

## For maintainers

1. [plans/README.md](plans/README.md) — WIP rulebook
2. [plans/PROJECT_PLAN.md](plans/PROJECT_PLAN.md) — overall roadmap
3. [plans/interactive_playtest/](plans/interactive_playtest/) — playtest design
4. [plans/playability_fix/](plans/playability_fix/) — specific design iterations

## For reviewers / auditors

1. [plans/openai_build_week_2026/README.md](plans/openai_build_week_2026/README.md) — authoritative Build Week reviewer hub
2. [../JUDGE.md](../JUDGE.md) — canonical offline commands and evidence map
3. [reviews/README.md](reviews/README.md) — date-sorted audit index
4. [reviews/REVIEW_FEEDBACK.md](reviews/REVIEW_FEEDBACK.md) — original feedback
5. [reviews/ACTION_PLAN.md](reviews/ACTION_PLAN.md) — T01–T13 task plan
6. [reviews/LOCAL_LLM_GAME_SYSTEM_AUDIT_20260713.md](reviews/LOCAL_LLM_GAME_SYSTEM_AUDIT_20260713.md) — latest real-game audit
7. Older audits: [ALIGNMENT_AUDIT.md](reviews/ALIGNMENT_AUDIT.md), [DETAILED_EXECUTION_PLAN.md](reviews/DETAILED_EXECUTION_PLAN.md), [REAL_TEST_GAP_ANALYSIS.md](reviews/REAL_TEST_GAP_ANALYSIS.md)

Dated docs in `reviews/` and `plans/` have YAML frontmatter
(`status`, `date`, `audience`, `scope`) — read in date order, not position order.

## About this index

`legacy/` contains superseded docs and is intentionally not linked.
Last updated: 2026-07-18.
