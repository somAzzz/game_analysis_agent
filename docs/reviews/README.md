# Reviews

Date-sorted audit and feedback material. Markdown audits normally use YAML
frontmatter; machine-readable gate records use versioned JSON schemas.

For the current competition state, start with the
[Build Week reviewer hub](../plans/openai_build_week_2026/README.md).

Read in date order, not position order. Newest first.

## 2026-07-17

- [openai_build_week_2026/FULL_CAMPAIGN_REVIEW_REMEDIATION_REVIEW.md](openai_build_week_2026/FULL_CAMPAIGN_REVIEW_REMEDIATION_REVIEW.md) — *implemented* — shared provider execution, exact-path replay, large-batch evidence indexing, Judge updates, and remaining follow-ups
- [openai_build_week_2026/HUMAN_DECISION_FRONTEND_INTEGRATION_REVIEW.md](openai_build_week_2026/HUMAN_DECISION_FRONTEND_INTEGRATION_REVIEW.md) — *implemented* — Human Decision information architecture, design-language audit, interaction boundaries, and before/after visual evidence
- [openai_build_week_2026/local-vllm-25-seed-audit-2026-07-17/README.md](openai_build_week_2026/local-vllm-25-seed-audit-2026-07-17/README.md) — *completed* — 150-cell real-Godot local-vLLM audit, agent/game reports, and pressure-burnout cross-check

## 2026-07-16

- [openai_build_week_2026/P3-skill-transfer.md](openai_build_week_2026/P3-skill-transfer.md) — *passed* — fresh-context Unity scenario validates transferable automated/persona evidence-to-change reasoning without claiming runtime support
- [openai_build_week_2026/BRANCH_AUDITS.md](openai_build_week_2026/BRANCH_AUDITS.md) — *active* — two independent branch reviews, remediation trace, and platform handoff
- [openai_build_week_2026/G4-evaluator.md](openai_build_week_2026/G4-evaluator.md) — *failed closed* — evaluator and UI pass; platform execution and published multi-arch image remain blockers
- [openai_build_week_2026/P4-platform-delivery.md](openai_build_week_2026/P4-platform-delivery.md) — *partial* — macOS native path verified; Docker/Linux/live rows explicitly pending or not run
- [G1-providers.md](G1-providers.md) — *passed* — provider correctness, failure truthfulness, shared contract, and secret-boundary gate; live smoke recorded as `not_run`
- [G0-baseline.md](G0-baseline.md) — *passed* — OpenAI Build Week canonical baseline, reproducibility, provenance, and clean-room gate

## 2026-07-13

- [LOCAL_LLM_GAME_SYSTEM_AUDIT_20260713.md](LOCAL_LLM_GAME_SYSTEM_AUDIT_20260713.md) — *active* — baseline audit of real-game + local vLLM end-to-end path
- [REAL_TEST_GAP_ANALYSIS.md](REAL_TEST_GAP_ANALYSIS.md) — *superseded* — pre-embedded-game test-system snapshot

## 2026-07-06 (initial review remediation cycle)

- [REVIEW_FEEDBACK.md](REVIEW_FEEDBACK.md) — *active* — original review + per-task implementation log
- [ACTION_PLAN.md](ACTION_PLAN.md) — *active* — T01–T13 task plan and status
- [ALIGNMENT_AUDIT.md](ALIGNMENT_AUDIT.md) — *superseded* — pre-remediation alignment audit
- [DETAILED_EXECUTION_PLAN.md](DETAILED_EXECUTION_PLAN.md) — *superseded* — patch plan for the pre-remediation gaps

## How to use this folder

- Start with the newest `active` or `passed` audit for the current state of the system.
- `superseded` documents describe earlier points in time and should not be used to judge the current codebase.
- Gate reviews must identify exact commands, machine-readable evidence, fail-closed criteria, and any non-blocking limitation.
- The implementation log lives in [REVIEW_FEEDBACK.md](REVIEW_FEEDBACK.md) ("落实日志" section); the structured task list lives in [ACTION_PLAN.md](ACTION_PLAN.md).
