---
status: active
date: 2026-07-16
audience: OpenAI Build Week judges, automated evaluators, maintainers
scope: authoritative Playtest Forge competition entrypoint
---

# Playtest Forge — Build Week 2026 reviewer hub

This is the single authoritative entrypoint for the competition branch. The
project is a focused developer tool: Codex acts as the Repair Director over
real Godot automation, persona-policy evidence, one bounded repair mechanism,
and fixed plus unseen-holdout verification. The committed repair is deliberately
**rejected** because it did not causally reduce the selected failure cluster.

The embedded `study-in-germany` project is a demo, not a complete game. It is
the exact public reference workload used to make Codex's inspected files,
candidate diff, and real engine evidence visible in one repository. MCP is not
part of this submission; the service-first migration remains future work.

## Automated evaluator path

Run from the repository root:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

Then follow `AGENTS.md` and load the checked-in `playtest-forge` Skill. Inspect
uses Python 3.9+ only. Replay uses the locked `uv` environment. Neither path
needs network, Docker, Godot, a model key, or a sibling game checkout.

## Evidence truth labels

| Capability | What is actually proven |
| --- | --- |
| Automated play | Real Godot 4.4 simulation and validators on the embedded demo |
| Persona Replay | Deterministically authored persona-policy fixture over retained real-Godot rows; not a recorded LLM playthrough |
| OpenAI live | Optional bounded live persona provider; remains blocked until GPT-5.6 response evidence is imported |
| Repair | Codex-directed isolated candidate change, fixed and holdout A/B proof, explicit rejection, no automatic merge |
| Skill | Transferable facts → inference → one mechanism → fixed/holdout → accept/reject workflow |

## Documents in review order

1. [Implementation plan](IMPLEMENTATION_PLAN.md) — product thesis, scope, architecture, and competition mapping.
2. [Stepwise execution plan](EXECUTION_PLAN.md) — P0–P5 tasks and gate order. Older status tables are plan-time snapshots unless explicitly dated current.
3. [Competition product-design review](product_design/COMPETITION_PRODUCT_DESIGN_REVIEW.md) — frontend audit, four-role critique, game-native interaction direction, and prioritized acceptance criteria.
4. [Product-design evidence](product_design/README.md) — evaluator UI screenshots for visual review and demo/video planning.
5. [Two independent branch audits](../../reviews/openai_build_week_2026/BRANCH_AUDITS.md) — findings, remediation commits, and unresolved limits.
6. [Judge guide](../../../JUDGE.md) — exact offline commands, exit behavior, capability labels, and central result.
7. [P4/G4 Linux closeout](../../operations/LINUX_P4_G4_CLOSEOUT.md) — Docker, pinned Linux Godot, arm64, registry, and evidence import.
8. [Platform review JSON](../../reviews/openai_build_week_2026/P4-platform-delivery.review.json) — current fail-closed machine ledger.
9. [G4 review](../../reviews/openai_build_week_2026/G4-evaluator.md) and [G5 review](../../reviews/openai_build_week_2026/G5-final-release.md) — release gates.
10. [Submission directory](../../../submission/build-week-2026/) — claim ledger, Devpost draft, video script, and external closeout records.

## Current implementation limits

- The native Judge API is a localhost demo. It has bounded request bodies and
  active-job concurrency, but not hosted multi-tenant authentication, quotas,
  job TTL, or billing governance. Do not expose it directly to the public web.
- The canonical embedded demo is read-only by policy. All Godot runs use a
  verified writable runtime copy with one audited interactive-probe overlay.
- The demo intentionally retains three declared balance findings. Linux CI
  accepts only that exact pin-bound finding set while requiring the other five
  Godot validators to pass; changed findings fail closed.
- Linux/Docker/multi-architecture claims must be regenerated whenever the
  delivery fingerprint changes; old passing rows are marked stale.
- Live OpenAI evidence must prove the GPT-5.6 model family. DeepSeek can test
  OpenAI-compatible wiring but cannot close the OpenAI competition gate.
- G5 remains blocked by an explicit repository license choice, live model
  evidence, non-builder clean-room/manual comparison, final video, and final
  published URLs/assets. A Codex task id alone does not prove its model.

## Platform handoff

macOS completed offline Judge, native API/UI, embedded runtime preparation, and
pinned Godot 4.4 execution. This host has no Docker executable, so workflow run
`29531033847` completed native Linux amd64, Docker clean-room, official Linux
Godot, native arm64, and the registry manifest proof. Live OpenAI still needs a
restricted server-side key. Missing external evidence remains a failed or stale
gate; it is never promoted from source inspection.
