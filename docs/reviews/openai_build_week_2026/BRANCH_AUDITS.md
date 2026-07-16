---
status: active
date: 2026-07-16
audience: OpenAI Build Week judges, maintainers
scope: two independent full-branch audits and remediation trace
---

# Build Week branch audits

Two independent read-only reviews were run from the competition branch. The
goal-alignment audit used the request-start snapshot `b8d3d6b`; the
implementation/platform audit consolidated at `d88158f`. Both ran offline
Inspect, offline Replay, and the `playtest-forge` preflight and reviewed the
demo pin, runtime preparation, Judge API/UI, G0–G5 gates, CI, Docker, docs, and
submission records.

Both audits concluded that the product direction remains aligned: Codex is the
Repair Director, facts are separated from inference, one candidate mechanism
is evaluated in isolation, fixed and unseen holdout cohorts decide the result,
the ineffective patch stays rejected, and MCP has not bypassed the service-first
architecture. Embedding the demo improves reviewability and does not change the
product into a game submission.

## Findings and disposition

| Priority | Finding | Disposition |
| --- | --- | --- |
| P0 | G4 could retain old passed platform rows after a contract change | Fixed in `d88158f`; G4 now validates every row and its evidence payload |
| P0 | Full 80-file embedded snapshot was self-attested by its marker | Fixed in `4749467`; independent pin now anchors the portable content-tree digest |
| P1 | Canonical verifier allowed extras/mode drift; runtime replace trusted a minimal forged marker | Fixed in `4749467`; exact file set, executable semantics, full runtime/overlay validation, and generated-file allowlist |
| P1 | Platform evidence only checked for a 40-character game commit | Fixed in `3be84c2`; pin fields, overlay hashes, game/runtime/execution fingerprints are required |
| P1 | Delivery fingerprint omitted toolchain/game pins, runtime preparers, and frontend build configuration | Fixed in `3be84c2`; mutation tests cover the added inputs |
| P1 | Linux Godot redirected before creating its output directory | Fixed in `3be84c2` with a static regression test |
| P1 | Balance wrapper could write `.godot` and output into canonical demo | Fixed in `afac6b3`; default is a prepared runtime and canonical path is refused |
| P1 | Replay ignored requested personas, seeds, and week bound | Fixed in `733e4e1`; it slices verified retained rows and fails on unavailable cells |
| P1 | UI wording could imply Replay was a live LLM playthrough | Fixed in `733e4e1`; it is labeled a deterministic persona-policy fixture |
| P1 | G5 could pass without model evidence | Fixed in `88537b6`; live OpenAI and Codex release metadata require GPT-5.6-family proof |
| P1 | Judge image omitted the runtime probe required by API auto-preparation | Fixed in `02b09e1`; Docker/static coverage updated |
| P1 | Linux real-Godot CI treated the declared three-finding demo balance defect as infrastructure failure | Replaced by an exact pin-bound expected-failure gate; all five contract validators must still pass and any finding drift fails closed |
| P1/P2 | Docs mixed the new embedded bundle with old private-token/sibling-checkout steps | Remediated in the reviewer hub and current runbooks; historical audits are labeled snapshots |

## Deliberately unresolved or external

- Docker is unavailable on the audited macOS host. Linux CI must prove native
  amd64/container, pinned official Godot, native arm64, and the published image
  manifest at the final delivery fingerprint.
- Live OpenAI is not run without a restricted server-side key. DeepSeek does
  not substitute for this claim.
- The local API is not a hosted multi-tenant service. Public static Judge Mode
  is safe; hosted execution requires authentication, quotas, retention limits,
  Origin/CSRF controls, and billing governance beyond the competition scope.
- G5 correctly remains blocked for license selection, independent review,
  manual comparison, final video/URLs, live GPT-5.6 evidence, and refreshed
  registry assets.
- The current secret scan is a bounded repository check, not a replacement for
  a mature credential scanner. The final release should add a hosted scanner.

## Verification policy

Every remediation above has a focused regression test and its own Git commit.
The final macOS P4 rerun passed from a clean worktree at contract `6fd5874d` and
was imported alongside completed Linux amd64 and official-Godot job artifacts.
PR #5 remains the delivery channel; Linux results are accepted only from
completed jobs and downloaded artifacts at the same contract fingerprint.
Skipped optional jobs are recorded as skipped, not passed.
