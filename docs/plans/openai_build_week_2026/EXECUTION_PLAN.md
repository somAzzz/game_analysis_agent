---
status: active
date: 2026-07-16
last_updated: 2026-07-16
audience: maintainers, builders, reviewers
scope: stepwise delivery and review gates for the OpenAI Build Week 2026 submission
parent_plan: IMPLEMENTATION_PLAN.md
---

# Playtest Forge: Stepwise Execution and Review Plan

## 0. Current implementation update — embedded demo and change visibility

The competition baseline is now the complete pinned `study-in-germany` demo at
`demo/study-in-germany` (commit
`348b9fd5501e71ebc7142e10f9068fc1490b5124`). It is a demo, not a claim of a
complete game. The source marker inventories all 80 upstream files; Judge
Inspect hashes the marker plus every file. CI, macOS, Linux Godot, Live OpenAI,
and the native Judge API now prepare writable verified copies without a sibling
checkout or `STUDY_IN_GERMANY_TOKEN`.

Runtime integration follows this boundary:

```text
embedded canonical demo (read-only, exact pin)
  -> verified writable runtime copy
  -> audited Agent probe overlay
  -> Godot execution and evidence
  -> candidate patch in isolated experiment only
```

The canonical demo never receives the rejected repair. Presentation is divided
by evaluator need:

| Surface | Show | Do not show |
| --- | --- | --- |
| Judge frontend | changed files/lines, exact expandable diff, base commit, patch hash, focused-test statement, fixed/holdout results, accepted/rejected disposition | API keys, raw prompts/model output, unbounded logs, or a rejected patch presented as merged |
| Judge API | verified public experiment, full bounded diff, hashes, cohort and gate records | arbitrary filesystem reads or non-allowlisted experiments |
| Repository/backend | complete canonical demo, evidence bundles, Skill, manifests, tests and runtime-overlay provenance | generated caches or secret configuration |

This is more judgeable than hiding the source change, while keeping the front
page focused on the causal decision rather than turning it into a general code
browser. Commits `9159f23`, `f8333c4`, `ca0ae77`, `01b711c`, and `c48d651`
implement the source bundle, runtime copy, default execution paths, Judge image
inventory, and exact-diff UI respectively.

Verification completed on this revision family:

- embedded source verification and replacement-safety tests passed;
- Judge Inspect passes with 121 hash-pinned artifacts;
- Python Judge/API/runtime tests and all 15 frontend tests passed;
- the public frontend build passed and the same-origin route was visually
  checked at desktop and 390px width;
- Docker could not be rerun on this macOS host because the executable is
  unavailable. Because the delivery fingerprint changed, macOS acceptance,
  Linux amd64/Godot, Linux arm64, and the published multi-arch image evidence
  must be refreshed before G4 can pass;
- `live_openai_campaign` still requires a restricted server-side OpenAI key;
- the final repository license remains a G5 maintainer decision.

### 2026-07-16 dual-audit remediation update

Two independent full-branch reviews are recorded in
[`BRANCH_AUDITS.md`](../../reviews/openai_build_week_2026/BRANCH_AUDITS.md).
They found and closed stale-row platform proof, self-attested full-demo pinning,
unsafe runtime replacement, incomplete runtime provenance, canonical write
risk, unbounded Replay semantics, misleading Replay origin labels, and missing
GPT-5.6 release evidence gates. Commits `d88158f`, `4749467`, `3be84c2`,
`afac6b3`, `733e4e1`, and `88537b6` implement those changes with focused tests.

The remaining execution order is now:

1. regenerate the Judge manifest and macOS P4 evidence from a clean revision;
2. push PR #5 and make required PR checks green;
3. dispatch the Linux official-Godot job and import same-contract artifacts;
4. publish and execute the digest-pinned multi-architecture image;
5. run live OpenAI only with GPT-5.6-family evidence;
6. close the human/license/video/URL items in G5.

## 1. Purpose

This document turns the competition strategy in
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) into an executable delivery
sequence. It answers four operational questions for every step:

1. What must be true before work starts?
2. What exact change and artifact must be produced?
3. How is the result verified without trusting the builder's explanation?
4. Who or what may authorize the next dependent step?

The execution target is one complete and judgeable path:

```text
persona campaign
  -> cited failure cluster
  -> one Codex hypothesis
  -> one constrained patch
  -> fixed-seed replay
  -> holdout replay
  -> accepted or rejected experiment
  -> offline evaluator + human evidence UI
```

The plan deliberately prioritizes evidence integrity and evaluator access over
feature breadth. MCP, multiple games, automatic merge, and general automatic
balancing remain out of scope.

## 2. Status at plan creation

> Historical planning snapshot. It is retained to show delivery order, not the
> current implementation state. Use [this plan's current update](#0-current-implementation-update--embedded-demo-and-change-visibility)
> and the [reviewer hub](README.md) for present status.

| Phase | Current state | Immediate blocker |
| --- | --- | --- |
| P0 Canonical baseline | Partial | Active game checkout and generated real trace are not canonical |
| P1 Persona providers | Not started | Provider registry has no OpenAI or recorded gateway |
| P2 Campaign evidence | Partial foundation | Existing matrix is not the focused Build Week campaign contract |
| P3 Codex repair protocol | Not started | No repository Skill or repair experiment record |
| P4 Evaluator and Judge Mode | Not started | Current Compose is NVIDIA-first and frontend is report-only |
| P5 Submission | Not started | No final measured case, video, `/feedback` ID, or clean-room release |

Existing analytics, contracts, gates, personas, matrix, Godot runners, report
frontend, and 261 passing tests are inputs, not proof that any phase below is
complete.

## 3. Execution rules

### 3.1 Roles

One person may perform all roles, but the review role must use a fresh Codex
task or fresh context that does not inherit the builder's conclusions.

| Role | Responsibility | May approve own work? |
| --- | --- | ---: |
| Builder | Implements one bounded step and produces evidence | No |
| Automated verifier | Runs deterministic checks and writes machine-readable results | Not applicable |
| Gate reviewer | Reviews diff, artifacts, failures, and criterion-specific risks | No |
| Maintainer | Resolves product choices and authorizes gate transition | Yes, after evidence and review |

The builder may be Codex, but deterministic scripts—not model confidence—decide
schema, hash, test, and quality-gate results.

### 3.2 Change and commit protocol

- Work only on `OpenAI-build-week-2026` or an isolated worktree based on it.
- One execution step should produce one reviewable commit where practical.
- Commit subjects begin with the step ID, for example
  `BW-P1.3: add structured OpenAI persona decisions`.
- Never combine a gate/test weakening with the feature it would allow to pass.
- Do not rewrite a reviewed commit. Corrections use a new commit and the gate
  review records the complete reviewed range.
- Do not advance a dependent step while its prerequisite gate is `failed` or
  `blocked`.
- No review process automatically merges a repair or competition change.

### 3.3 Review states

Every gate ends in exactly one state:

- `passed`: all required evidence exists and no stop condition remains;
- `conditional`: non-critical follow-up is recorded with owner and deadline;
- `failed`: evidence disproves the claim or a required check fails;
- `blocked`: an external input or maintainer choice is required.

`Conditional` may advance only when the condition is unrelated to the next
phase's correctness. Missing canonical evidence, security failures, stale
artifacts, and unsupported claims can never be conditional.

### 3.4 Evidence locations

Each phase writes a review packet during implementation:

```text
docs/reviews/openai_build_week_2026/
  G0-baseline.md
  G1-providers.md
  G2-campaign.md
  G3-repair.md
  G4-evaluator.md
  G5-release.md

reports/build-week-2026/
  baseline/
  campaigns/
  experiments/
  evaluator/
  release/
```

Each `G*.md` records reviewed commit SHA/range, commands, exit codes, artifact
paths and hashes, findings by severity, decision, conditions, reviewer, and
timestamp. A sibling `review.json` is required for G2-G5 so the final release
check can reject a missing or failed gate automatically.

### 3.5 Existing versus target commands

Commands labeled **existing** are available in the current repository.
Commands labeled **target** are interface contracts that must be implemented
and tested before documentation presents them as runnable.

## 4. Critical path and calendar

| Date | Critical path | Gate due | Parallel work allowed |
| --- | --- | --- | --- |
| July 16 | P0 canonical source, toolchain, baseline | G0 | P1 contract design only |
| July 17 | P1 Replay/OpenAI provider boundary | G1 | P4 offline evaluator schema |
| July 18 | P2 complete campaign and target selection | G2 | P4 static UI preparation |
| July 19 | P3 Codex repair and fixed/holdout proof | G3 | P4 Docker/API scaffolding |
| July 20 | P4 evaluator, portability, UI, clean-room run | G4 | P5 description and video draft |
| July 21 | P5 claims, video, repository, Devpost | G5 | Submission-only fixes |

Critical dependency chain:

```text
P0 -> P1 -> P2 -> P3 -> P4 release evidence -> P5
```

P4's standard-library Inspect skeleton may start after P0. Its final manifest
and expected outcomes cannot be frozen before G3.

## 5. Global definition of done

The project is submission-ready only when all statements are true:

- G0-G5 are `passed`; no critical condition remains.
- One canonical game revision and one analysis revision identify all evidence.
- One real failure target is supported by run/week-level references.
- Codex produced one falsifiable hypothesis and one constrained repair
  experiment in the recorded core task.
- Fixed seeds and unseen holdout seeds support an honest accept/reject result.
- Critical invariants, designed-failure behavior, and persona alignment pass.
- `./judge --mode inspect --offline --json` passes in a repository-only clone.
- Replay smoke passes without network, secret, Docker, GPU, TTY, browser, port,
  or sibling checkout.
- Apple Silicon and Linux compatibility claims have dated evidence.
- The public video is under three minutes and explains both Codex and GPT-5.6.
- Every public numerical claim resolves to a committed artifact and field.
- The repository, README, sample evidence, licensing, and `/feedback` Session ID
  meet the published submission requirements.

## 6. Standard step workflow

Use this loop for every numbered step:

1. **Ready check**: confirm dependencies and cleanly record pre-existing
   failures; do not repair unrelated work silently.
2. **Bound work**: state intended files, behavior, and prohibited changes.
3. **Implement**: make the smallest change satisfying the step.
4. **Self-check**: run focused tests and inspect artifacts.
5. **Commit**: create a step-scoped commit only after focused checks pass.
6. **Independent review**: give a fresh reviewer the commit/diff, requirements,
   and raw evidence—not the builder's desired verdict.
7. **Remediate**: fix findings in new commits and rerun affected checks.
8. **Gate decision**: record pass/fail/blocked state and authorize or stop the
   next dependent work.

Minimum independent-review prompt:

```text
Review <commit range> for execution step <ID>. Read AGENTS.md and the Build Week
implementation/execution plans. Verify the claimed behavior from source,
commands, and artifacts. Look specifically for stale evidence, hidden fallback,
weakened tests/gates, secret exposure, platform assumptions, and claims not
supported by fixed and holdout results. Do not modify files. Return findings by
severity, commands checked, missing evidence, and pass/fail recommendation.
```

## 7. P0 — Restore and freeze the canonical baseline

### P0.1 Freeze competition scope and inventory

**Depends on:** none.

**Actions**

- Record analysis repository SHA, branch, dirty state, game repository branch
  and SHA, host architecture, and available Python/Node/Godot/Docker versions.
- Confirm the golden demo target and the non-artificial fallback defect.
- Create a machine-readable baseline inventory with `unknown` values instead of
  guessing unavailable tools.
- Declare the exact files/repositories included in the submission and their
  licensing status.

**Outputs**

- `reports/build-week-2026/baseline/inventory.json`.
- Scope/licensing decision recorded in G0.

**Review**

- Re-run inventory from a fresh shell.
- Reject absolute developer-only paths, uncommitted evidence, or an unowned
  game dependency.

### P0.2 Pin and package `study-in-germany`

**Depends on:** P0.1.

**Actions**

- Select the canonical commit containing simulation, interactive, boundary,
  and graph runners.
- Choose a pinned subtree or competition bundle if licensing permits; use a
  pinned submodule only if clean automated checkout is proven.
- Verify that the packaged game includes every runner and referenced resource.
- Record the game tree hash independently of Git metadata.

**Focused verification**

- **Existing:** `uv run pytest tests/test_game_contract.py -m game_contract -q -ra`.
- **Existing:** run `scripts/godot-docker-wrapper --version` when Docker is
  available, otherwise run the pinned native Godot 4.4 executable.
- Confirm the packaged path works without `/home/bo/...` or a sibling checkout.

**Stop conditions**

- Licensing is unresolved.
- Required runners differ from the revision used to create demo evidence.
- The package cannot be initialized non-interactively.

### P0.3 Pin macOS and Linux toolchains

**Depends on:** P0.1.

**Actions**

- Pin Python 3.12 and Node 20; create/update lockfiles without unrelated
  dependency upgrades.
- Pin native Godot 4.4 for Apple Silicon and the verified Linux Godot runtime.
- Document Docker Desktop as optional for macOS offline inspection and required
  only for the containerized Replay/UI path.
- Keep NVIDIA vLLM behind an explicit `local-nvidia` profile.

**Focused verification**

```bash
# Existing repository checks once the pinned environment is active
uv sync --extra dev
uv run python --version
uv run pytest -q -ra
uv run ruff check .

cd frontend
npm ci
npm test
npm run build
```

Record skipped tests and unavailable tools; a skip is not a pass.

### P0.4 Generate the canonical real baseline

**Depends on:** P0.2, P0.3.

**Actions**

- Generate a real 20-week trace from the packaged game with fixed seed and
  canonical normal/default configuration.
- Run export, validation, analytics, anomalies, agent evaluation where
  applicable, gates, and report manifest generation.
- Fail closed if any artifact predates the source/config revision.

**Existing command family**

```bash
uv run python tools/run_gameplay_agent.py sim <pinned arguments>
uv run python tools/run_gameplay_agent.py export --report-dir <baseline>
uv run python tools/run_gameplay_agent.py validate --report-dir <baseline>
uv run python tools/run_gameplay_agent.py gates --report-dir <baseline>
```

Exact arguments and outputs must be copied into G0, not represented by the
placeholders above.

### P0.5 Gate G0 — Baseline reproducibility review

**Automated review**

- Full pytest and Ruff.
- Frontend test and build.
- Real game contract.
- Baseline manifest/hash validation.
- Repeat the fixed-seed baseline and compare canonical outputs.

**Independent review questions**

- Is every artifact from the declared game/source/config revision?
- Can a clean macOS setup and Linux setup locate the same packaged game?
- Are missing tools, skips, or contract failures incorrectly labeled as pass?
- Does the fallback demo problem come from observed evidence?

**G0 pass criteria**

- Required runners exist and real contract passes.
- Baseline is reproducible and provenance-complete.
- No critical test failure or unexplained skip.
- Licensing and packaging path are decided.

## 8. P1 — Add Replay and OpenAI persona gateways

### P1.1 Freeze the shared decision contract

**Depends on:** G0.

**Actions**

- Inventory every current local-provider call and the Pydantic decision models.
- Define `PersonaDecisionGateway` without changing gameplay semantics.
- Preserve one shared `PlayerDecision` and event-choice contract for all
  providers.
- Add typed provider error categories and a provider-neutral result envelope.

**Review focus:** no `argparse.Namespace`, UI object, SDK response object, or
provider-specific JSON leaks across the gateway boundary.

### P1.2 Implement `RecordedPersonaGateway`

**Depends on:** P1.1.

**Actions**

- Read only committed, hash-verified fixtures.
- Match requests to recorded decisions by persona, seed, week, state hash, and
  event context.
- Reject missing or mismatched entries; never choose a nearby decision.
- Record that the provider is Replay in every output and UI surface.

**Tests**

- Exact lookup, exhausted fixture, state mismatch, corrupted hash, partial
  fixture, and cross-persona leakage.

### P1.3 Implement `OpenAIResponsesPersonaGateway`

**Depends on:** P1.1.

**Actions**

- Use the Responses API with Structured Outputs mapped from existing Pydantic
  schemas.
- Use `gpt-5.6-luna` for bounded persona decisions unless official availability
  or the plan's verified model mapping changes.
- Keep prompts focused on persona decisions; do not ask this worker to inspect
  or patch source.
- Capture provider response ID, actual model, token usage, latency, refusal,
  and parse status.

**Tests**

- Mock successful structured decision, refusal, timeout, rate limit, malformed
  result, unknown action, and one permitted schema repair.

### P1.4 Implement provider selection, budgets, and failure truthfulness

**Depends on:** P1.2, P1.3.

**Actions**

- Add `openai`, `replay`, and existing local providers to validated settings.
- Select Replay before execution when no key exists.
- Once a live campaign starts, never replace a failed call with Replay while
  reporting live success.
- Add maximum runs/weeks/concurrency, call budget, bounded backoff, cancellation,
  and secret redaction.
- Remove the assumption that `vllm` is the default provider for Judge Mode.

### P1.5 Integrate the gateways with interactive gameplay

**Depends on:** P1.4.

**Actions**

- Replace provider selection at the narrow interactive-player seam.
- Avoid broad CLI refactoring and do not create MCP code.
- Verify identical legal-action and event-choice semantics across Replay,
  OpenAI mocks, and the existing local gateway.

### P1.6 Gate G1 — Provider correctness and security review

**Automated review**

- Provider/settings unit tests.
- Full pytest and Ruff.
- Secret scan of Git diff, reports, frontend bundle, logs, and exceptions.
- Replay fixture hash test.
- Optional one-call live smoke test with a restricted key; its absence does not
  fail Replay but must be recorded as `not_run`.

**Independent review questions**

- Is the OpenAI key ever accepted by or returned to the browser?
- Can an API error become a false passing Replay result?
- Are local and OpenAI workers genuinely using the same typed decision contract?
- Are retries bounded and refusals visible?

**G1 pass criteria**

- Replay passes without network/key.
- OpenAI behavior is fully mock-tested and one live smoke is evidenced before
  the final submission.
- No secret exposure or hidden fallback.
- Existing local-provider tests remain green.

## 9. P2 — Build the focused campaign and select the repair target

### P2.1 Define campaign request, result, and cell contracts

**Depends on:** G1.

**Actions**

- Define personas, seeds, weeks, difficulty, scenario, provider, concurrency,
  and report root as typed inputs.
- Define cell states: queued, running, completed, failed, cancelled, partial.
- Make source/game/config/provider revisions mandatory result fields.

### P2.2 Implement isolated scheduling and resume

**Depends on:** P2.1.

**Actions**

- Give every persona/seed cell an isolated output directory and deterministic
  ID.
- Keep weeks sequential within a playthrough; run cells concurrently with a
  Judge maximum of four.
- Resume only cells whose input and source hashes match.
- Propagate cancellation and terminate child processes.

### P2.3 Implement aggregation and failure clustering

**Depends on:** P2.2.

**Actions**

- Aggregate outcome, stress, cashflow, burnout, validity, fallback, error, and
  persona-alignment measures.
- Identify first entry into the suspected failure attractor.
- Generate representative run/week references for each cluster.
- Keep statistical calculations deterministic; Codex may interpret but may not
  manufacture cluster membership.

### P2.4 Build the public-safe campaign bundle

**Depends on:** P2.3.

**Outputs**

- `campaign_manifest.json`.
- `campaign_summary.json`.
- `persona_runs.jsonl`.
- `agent_eval.jsonl`.
- `llm_calls.jsonl` with secrets/prompts sanitized as required.
- `failure_clusters.json`.
- `gate_report.json`.

Validate every file against schema and hash before marking the campaign
complete.

### P2.5 Run the evidence campaign and choose exactly one target

**Depends on:** P2.4.

**Actions**

- Run the planned six-persona, three-seed, twenty-week audited campaign.
- Keep a small OpenAI live campaign separate from the full recorded bundle.
- Apply the selection rubric: reproducible, causally plausible, user-relevant,
  one-mechanism repairable, invariant-safe, and visually explainable.
- Select the stress/cashflow attractor only if evidence supports it; otherwise
  select the previously observed real invariant fallback.
- Freeze fixed and unseen holdout seed lists before patching.

### P2.6 Gate G2 — Campaign evidence review

**Automated review**

- All expected cells present or campaign fails closed.
- Manifest, schema, and source hashes valid.
- Aggregates recompute from raw rows.
- Fixed/holdout seed lists are disjoint and frozen.
- No private or licensed content leaks into the public bundle.

**Independent review questions**

- Does the selected target exist across more than one relevant run/persona?
- Are designed-failure outcomes being mistaken for defects?
- Can each headline number be recomputed from committed evidence?
- Was the target selected before viewing patched results?

**G2 pass criteria**

- Complete auditable campaign or explicit non-submittable failure.
- Exactly one target with run/week references.
- Frozen hypothesis inputs and holdouts.
- Public-safe bundle approved.

## 10. P3 — Execute the Codex repair experiment

### P3.1 Write the design-intent contract

**Depends on:** G2.

**Actions**

- Record designed-failure personas/outcomes, critical invariants, target
  metric, protected metrics, non-goals, and allowed mechanism classes.
- Review the contract before Codex sees candidate source changes.
- Hash the approved contract into the experiment.

### P3.2 Implement repair experiment and evidence schemas

**Depends on:** P3.1.

**Actions**

- Define experiment ID, evidence citations, hypothesis, predicted effect,
  allowlist, change budget, source revisions, fixed/holdout seeds, focused
  tests, comparison metrics, gates, and final decision.
- Require `accepted` or `rejected`; incomplete evidence cannot be accepted.

### P3.3 Create the repository Skill

**Depends on:** P3.1, P3.2.

**Target files**

```text
.agents/skills/playtest-forge/SKILL.md
.agents/skills/playtest-forge/references/design-contract.md
.agents/skills/playtest-forge/references/evidence-contract.md
.agents/skills/playtest-forge/references/repair-protocol.md
.agents/skills/playtest-forge/references/test-strategy.md
.agents/skills/playtest-forge/references/automated-testing.md
.agents/skills/playtest-forge/references/subagent-playthrough.md
.agents/skills/playtest-forge/references/evidence-to-parameters.md
.agents/skills/playtest-forge/references/scenario-balance-economy.md
.agents/skills/playtest-forge/references/scenario-content-flow.md
.agents/skills/playtest-forge/references/scenario-boundary-robustness.md
.agents/skills/playtest-forge/references/migration-guide.md
.agents/skills/playtest-forge/references/session-case-study.md
.agents/skills/playtest-forge/scripts/preflight
.agents/skills/playtest-forge/scripts/run-campaign
.agents/skills/playtest-forge/scripts/verify-repair
```

The Skill must enforce preflight, facts-before-inference, one hypothesis, one
mechanism, allowlisted edits, fixed replay, holdout replay, and explicit
accept/reject. It must not wrap CLI `cmd_*` functions as MCP tools.

### P3.4 Enforce isolated worktree and change budget

**Depends on:** P3.2.

**Actions**

- Create/use an isolated worktree for the candidate patch.
- Validate changed paths, maximum files/lines, forbidden test/gate/config
  weakening, and one mechanism class.
- Save `patch.diff` before verification.

### P3.5 Implement fixed and holdout verification

**Depends on:** P3.2, P3.4.

**Actions**

- Run focused tests first.
- Replay baseline and patch under identical fixed seeds.
- Replay the patch on frozen unseen holdouts.
- Evaluate critical, balance, and persona-preservation gates.
- Write comparison and decision atomically; reject on missing evidence,
  regression, or overfit.

### P3.6 Run the core Codex task

**Depends on:** P3.3, P3.5.

**Actions**

- Start one traceable Codex task using GPT-5.6 and `$playtest-forge`.
- Let Codex cite facts, form the hypothesis, inspect source, make the bounded
  change, run verification, and decide accept/reject.
- Do not coach the task toward acceptance.
- Retain task/session reference, commit range, artifacts, and `/feedback`
  Session ID.

### P3.6a Generalize the Skill from retained test/repair evidence

**Depends on:** P3.6 and the completed fixed/holdout experiment.

**Actions**

- Encode how deterministic automation, live persona/subagent playthroughs, and
  Replay contribute different evidence without mixing truth labels.
- Encode symptom → causal mechanic → parameter selection, including when not
  to change a global parameter.
- Add routed scenarios for balance/economy, content flow, and
  boundary/invariant review.
- Preserve the rejected cashflow repair as a concrete lesson: a focused test
  and improved cash metric did not prove target repair.
- Move game/engine-specific assumptions into a project profile and define the
  adapter contract for migration to another game.
- Validate the Skill structure, metadata, reference routing, project scripts,
  and one fresh-context transfer task.

**Completion checkpoint (2026-07-16): complete.** The Skill now provides a
generic test-to-change controller with scenario references while retaining
`study-in-germany` only as the current project profile and case study. A
fresh-context, read-only Unity city-builder test passed truth-label separation,
candidate rejection, next-experiment selection, fixed/holdout gates, and
migration-gap detection. This validates reasoning transfer, not Unity runtime
support; the limitation is retained in the transfer review.

### P3.7 Gate G3 — Causal repair and Codex-centrality review

**Automated review**

- Repair schema and evidence citations valid.
- Diff inside allowlist and change budget.
- No tests/gates weakened.
- Fixed and holdout reports complete.
- Critical/persona gates pass for an accepted patch.

**Independent review questions**

- Did Codex genuinely own hypothesis, source reasoning, patch, and judgment?
- Is the predicted mechanism consistent with the actual diff?
- Do holdouts confirm direction rather than merely repeat fixed seeds?
- Would rejection have been recorded honestly?
- Does the patch preserve intentionally difficult/failing play styles?

**G3 pass criteria**

- One complete real experiment, accepted or rejected.
- Every Codex claim cites evidence and every public metric is reproducible.
- A rejected experiment may prove safety, but the final demo still needs a
  clear useful outcome; the maintainer decides whether to run one additional
  separately recorded experiment.
- Core Codex Session ID is retained.

## 11. P4 — Build the offline evaluator and human Judge Mode

### P4.1 Implement Tier 0 `judge` Inspect

**Depends on:** G0; finalize expectations after G3.

**Actions**

- Add an executable root `judge` entrypoint using Python standard library only
  for Inspect.
- Validate `judge-manifest.json`, schema versions, file hashes, provenance, and
  claim-to-artifact references.
- Emit pure JSON on stdout, logs on stderr, stable exit codes, and optional
  stdout-only mode.
- Do not import optional project packages in Tier 0.

### P4.2 Implement Tier 1 Replay smoke and result protocol

**Depends on:** P1.2, P4.1.

**Actions**

- Replay a small real committed fixture using locked Python dependencies.
- Evaluate representative deterministic, persona, and designed-failure gates.
- Write `judge-result.json` atomically with status, stage, duration, checks,
  artifacts, limitations, error code, and remediation.
- Enforce 120-second timeout and process-group cleanup.

### P4.3 Add AI-readable evaluator documentation

**Depends on:** P4.1, P4.2.

**Actions**

- Put the canonical offline commands first in `AGENTS.md`, README, and
  `JUDGE.md`.
- Make `judge-manifest.json` the single machine-readable table of contents.
- Label prerecorded evidence, live capability, unsupported capability, and
  failure distinctly.
- Ensure no evaluator must infer commands from historical docs.
- Put mandatory `$playtest-forge` routing in the root `AGENTS.md`, which Codex
  loads before work, and the exact explicit prompt in README.
- Hash the complete repository Skill in `judge-manifest.json`. If Skill
  injection is unavailable, require direct `SKILL.md` reading as the evaluator
  fallback instead of silently skipping the workflow.

### P4.4 Test the restricted environment and injected failures

**Depends on:** P4.3.

**Required scenarios**

- No network, Docker socket, GPU, secret, TTY, browser, or available port.
- Repository-only checkout and no sibling game directory.
- Read-only output with `--output-dir -`.
- Missing/corrupt artifact, wrong hash, unsupported Python, timeout, signal,
  dependency failure, absent API key, mid-run provider failure.
- `linux/amd64` run inside pinned `openai/codex-universal` approximation.

Each case asserts exit code, status, stderr diagnosis, remediation, cleanup,
and absence of false success.

### P4.5 Decouple Compose and build portable Replay images

**Depends on:** P1.4.

**Actions**

- Move NVIDIA vLLM behind `local-nvidia` and remove it from default startup.
- Remove `agent -> vllm` health dependency for Replay/OpenAI.
- Build digest-pinned `linux/amd64` and `linux/arm64` API/dashboard/replay
  images.
- Do not use implicit amd64 emulation for Apple Silicon support.

### P4.6 Add the minimal Judge API

**Depends on:** P2.4, P3.5.

**Target surface**

```text
GET  /api/provider-status
POST /api/provider-test
POST /api/campaigns
GET  /api/campaigns/{id}
GET  /api/campaigns/{id}/events
POST /api/campaigns/{id}/cancel
GET  /api/experiments/{id}
```

No endpoint accepts or returns a key. Add request limits, path isolation,
cancellation, error typing, and public-bundle-only defaults.

### P4.7 Build Campaign, Repair, and Proof UI states

**Depends on:** P4.6.

**Actions**

- Reuse the existing visual identity and report components.
- Show facts before Codex inference, baseline/patch symmetry, fixed/holdout
  labels, partial/error states, and accepted/rejected decisions.
- Avoid color-only status and provide text summaries.
- Keep one primary action per stage.

**Implementation checkpoint (2026-07-16): complete.** The root evaluator route
now renders the verified public experiment as Campaign → Repair → Proof, with a
same-origin Replay/OpenAI provider control, typed campaign status, static
GitHub Pages fallback, explicit prerecorded/live labels, fixed/holdout
comparisons, and non-color gate states. The legacy report archive moved to
`/reports`. Acceptance evidence: 15 frontend tests, TypeScript lint, public
production build, API/UI HTTP smoke, 416 Python tests passed with one optional
skip, and both offline Judge modes passed. P4.8 remains the next step.

### P4.8 Validate macOS and Linux delivery

**Depends on:** P4.5-P4.7.

**macOS path**

- Fresh Apple Silicon account with Python 3.12, Node 20, native Godot 4.4.
- Offline Inspect/Replay without Docker.
- Native Python worker + native Godot for one real run and one short OpenAI
  campaign.

**Linux path**

- Repository-only restricted evaluator.
- Hardened digest-pinned amd64 Replay/UI image and native arm64 image execution.
- Pinned real-Godot 4.4 path on Linux amd64.

Docker evidence is deliberately owned by the Linux delivery path. Docker
Desktop on macOS remains an optional developer convenience and is not a
substitute for native Linux container evidence.

Compare artifact contracts and fixed-seed results across platforms; document
legitimate platform metadata differences.

**Implementation checkpoint (2026-07-16): partial.** macOS arm64 native
Inspect, Replay, idempotent offline setup, static build, and Judge UI/API are
verified. The repository-local pinned Godot 4.4 toolchain is installed, but its
P4 acceptance row still needs a fresh release-revision run. A Linux amd64 job
now exercises native and hardened container paths and uploads evidence, but it
has not run for the local unpushed commit. Linux pinned-Godot 4.4, Linux arm64,
and a server OpenAI campaign are also untested. See the P4 platform delivery
review. P4.8 and G4 remain open until dated run evidence replaces the pending
rows.

### P4.9 Gate G4 — Automated evaluator and judge-experience review

**Automated review**

- Tier 0 under 30 seconds and Tier 1 under 120 seconds.
- Offline/restricted/failure-injection suite.
- API unit/integration tests and key redaction.
- Frontend test/build and accessibility smoke.
- amd64/arm64 image manifest and digest verification.
- macOS and Linux clean-room records.

**Independent review questions**

- Can an AI find and run the primary test without guessing?
- Does Docker/network/key failure still leave trustworthy evidence inspection?
- Can unsupported capability be confused with project failure or success?
- Can a human understand Campaign -> Repair -> Proof in five minutes?
- Are macOS claims native rather than hidden amd64 emulation?

**G4 pass criteria**

- Repository-only evaluator passes with machine-readable output.
- Full reference case is inspectable without rebuild, GPU, or key.
- macOS and Linux supported paths are evidenced.
- Human UI makes the central claim and limitations clear.

**Gate execution (2026-07-16): failed closed.** Six of eight checks passed:
the restricted evaluator, human Judge UI contract, both offline modes,
frontend tests, and public build. `platform_delivery` and
`published_multiarch_image` failed because dated container/Linux evidence and
a registry image-index digest do not exist yet. The generated G4 JSON is the
authoritative blocker list; P5 release claims must not advance as though G4
passed.

## 12. P5 — Produce submission evidence and release

**Pre-release preparation (2026-07-16): complete but blocked.** A Devpost
draft, 2:40 video script, release checklist, and machine-verified claim ledger
now use only exact committed evidence. Unknown URLs, live runs, platform/image
proof, manual timing, and clean-room review remain explicit placeholders or
pending claims. The submission-asset reviewer passes the draft while returning
`release_status: blocked`; this preparation does not satisfy the G4 dependency
or authorize P5 release claims.

**Fail-closed G5 tooling (2026-07-16): implemented.**
`tools/review_build_week_g5.py --json` now verifies G0-G4, the claim ledger,
release URLs, manual comparison, independent clean-room review, video checks,
published image digest, license, privacy status, and tracked-file secret scan.
The committed templates contain `not_run`/`blocked` states, and the reviewer
has both a current-project failure test and a synthetic all-evidence pass test.
It cannot pass merely by replacing placeholders or changing one status field.

### P5.1 Freeze the measured case study

**Depends on:** G3, G4.

**Actions**

- Record runtime, calls, tokens, bounded cost, valid/fallback/error rates,
  clusters, hypotheses, patches, fixed/holdout changes, and gates.
- Run the manual-versus-Playtest-Forge timed comparison.
- Have at least one non-builder complete the clean-room path.
- Advance public claims only to the completed impact-claim level.

### P5.2 Finalize repository documentation and access

**Depends on:** P5.1.

**Actions**

- Finalize README, `JUDGE.md`, architecture, install paths, supported platforms,
  sample evidence, security, limitations, and OpenAI/Codex roles.
- Add exact image digests, tested dates, commands, expected durations, and
  cleanup.
- Confirm public licensing or grant private access to the required Devpost and
  OpenAI judge accounts.
- Verify all links from Devpost text to durable public locations.

### P5.3 Record and review the video

**Depends on:** P5.1, P5.2.

**Actions**

- Record the planned sub-three-minute golden path.
- Include audio and captions explaining distinct Codex and GPT-5.6 roles.
- Show a working command, evidence, constrained patch, fixed/holdout result,
  limitations, and reproducibility path.
- Do not represent Replay as a fresh live run.

**Video review**

- Duration check below 3:00.
- Public/unlisted YouTube accessibility from signed-out browser.
- Audio/caption intelligibility.
- No secret, private content, unsupported number, copyrighted music, or hidden
  edit that changes the meaning of the result.

### P5.4 Prepare and cross-check the Devpost submission

**Depends on:** P5.2, P5.3.

**Required fields/evidence**

- Developer Tools category.
- Focused project description and measured impact.
- Public YouTube URL.
- Judge-accessible repository URL.
- `/feedback` Session ID from the core build task.
- Clear locations showing where Codex accelerated work and made decisions.
- Installation, supported platforms, sample data, and no-rebuild test path.

Use a claim ledger: each sentence containing a number, capability, platform,
or causal statement maps to an artifact field or documented observation.

### P5.5 Gate G5 — Final release and submission review

**Automated review**

- G0-G4 review JSON all passed.
- Fresh clone Tier 0/Tier 1.
- Prebuilt image pull/run by digest.
- Full Python/Ruff/frontend/real-contract suites.
- Secret, license, privacy, broken-link, artifact-hash, and repository-access
  checks.
- Video duration and public availability.

**Independent judge simulation**

Give a fresh reviewer only the Devpost draft, video, and repository URL. Allow
at most twelve minutes. Ask the reviewer to:

1. state the product and target user in one sentence;
2. identify distinct Codex and GPT-5.6 roles;
3. run the first documented command;
4. locate evidence for the headline before/after claim;
5. explain why the patch was accepted or rejected;
6. score technical implementation, design, impact, and idea quality;
7. list any reason to disqualify, distrust, or stop testing.

Any inability to complete items 1-5 is a release blocker.

**Maintainer final authorization**

- Confirm no stop-ship item remains.
- Record final commit SHA, repository URL, image digests, video URL, Session ID,
  submission timestamp, and Devpost confirmation.
- Submit before July 21, 2026 at 5:00 PM PT; do not use the deadline as the
  first full-system test.

## 13. Review finding severity and response time

| Severity | Example | Response |
| --- | --- | --- |
| Critical | Secret leak, fabricated/stale evidence, inaccessible repo, false live claim | Stop all dependent work; fix and repeat full gate |
| High | Hidden fallback, broken clean-room path, holdout regression, unsupported platform claim | Fix before gate pass; rerun affected and downstream checks |
| Medium | Confusing UI state, incomplete remediation, missing non-critical test | Fix before release or record a truly non-blocking condition |
| Low | Wording, minor organization, optional polish | Batch only after critical path is safe |

Reviewers must report findings, not general approval language. “Looks good” is
not a gate result without commands, evidence, and criterion-specific reasoning.

## 14. Failure and rollback policy

- If G0 fails, stop all real-campaign and patch claims; repair the baseline.
- If the OpenAI live path fails but Replay passes, continue development and
  record live mode as unavailable; G1 cannot finally pass without one evidenced
  live smoke before submission.
- If the full campaign is incomplete, do not patch from partial aggregates.
- If the intended balance target is ambiguous, switch to the predeclared real
  invariant fallback before patching; never inject a demo defect.
- If a patch fails fixed or holdout gates, record it as rejected and revert only
  the candidate worktree, not the evidence.
- If Docker or the dashboard slips, preserve Tier 0/Tier 1, static evidence,
  public video, and the native macOS repair workflow.
- If ARM64 Docker cannot be proven, remove the support claim; do not use
  emulation and call it native.
- If time runs short, cut hosted execution, optional summarization, local-model
  demo, extra personas, and extra views in that order. Never cut evidence
  provenance, fixed/holdout proof, offline evaluation, or submission compliance.

## 15. First executable work queue

Run these in order when implementation begins:

1. P0.1 inventory and scope record.
2. P0.2 canonical game commit/licensing/package decision.
3. P0.3 Python 3.12, Node 20, Godot 4.4, and Docker availability record.
4. P0.4 real fixed-seed baseline generation.
5. P0.5 G0 review in a fresh task.
6. P1.1 shared decision contract.
7. P1.2 Replay gateway and fixtures.
8. P1.3 OpenAI gateway with mocked structured-output tests.
9. P1.4 provider selection, budgets, and truthful fallback.
10. P1.5 integration and G1 review.

Do not start UI redesign, MCP work, local-model optimization, or video polish
before G2 has selected a real target and G3 has produced a complete experiment.

## 16. Maintainer gate checklist

At each gate, the maintainer answers yes or no:

- Is the reviewed commit range fixed and recorded?
- Did automated checks run from the documented environment?
- Are raw outputs and hashes available, not just summaries?
- Did a fresh reviewer inspect the diff and evidence?
- Are all critical/high findings closed?
- Are failures and skips visible?
- Can the next phase rely on this result without an unstated assumption?
- Is the gate decision recorded in both Markdown and machine-readable form where
  required?

Any `no` means the dependent phase remains unauthorized.
