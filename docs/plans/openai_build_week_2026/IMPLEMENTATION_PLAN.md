---
status: active
date: 2026-07-16
audience: maintainers, judges, contributors
scope: OpenAI Build Week 2026 competition implementation and submission plan
---

# Playtest Forge: OpenAI Build Week 2026 Implementation Plan

## 1. Executive decision

The project will enter the **Developer Tools** track under the working name
**Playtest Forge**.

Playtest Forge is a Codex-led, evidence-gated game QA and repair workflow. It
uses OpenAI API persona workers to play a deterministic Godot game, converts
their traces into reproducible evidence, asks Codex with GPT-5.6 to diagnose
one causal failure mode, applies one constrained change in an isolated Git
worktree, and accepts or rejects that change after fixed-seed and holdout-seed
replay.

The competition claim is intentionally narrow:

> Codex can lead one complete, auditable game repair experiment—from diverse
> player behavior to a verified patch—without confusing designed failure with
> a software or balance defect.

The Build Week version will use a repository-scoped Codex Skill and Dockerized
execution environment. It will not add an MCP adapter before the existing
service-layer acceptance gates are complete.

## 2. Competition requirements and design response

The official OpenAI Build Week page and Devpost brief establish the following
requirements:

- The project must use Codex with GPT-5.6.
- It must fit one of four tracks; Developer Tools explicitly includes testing,
  DevOps, and agentic workflows.
- The submission must include a working project, category, description,
  public YouTube demo under three minutes, and a testable code repository.
- The video narration must explain how Codex and GPT-5.6 were used.
- The repository must include setup instructions, sample data where needed,
  and clear run instructions.
- The submission must provide the `/feedback` Codex Session ID for the session
  in which most core functionality was built.
- A developer tool must include installation instructions, supported
  platforms, and a way to test it without rebuilding from scratch.
- Judging covers technological implementation, design, potential impact, and
  quality/novelty of the idea.
- The submission deadline is July 21, 2026 at 5:00 PM PT.

Playtest Forge responds as follows:

| Requirement or criterion | Project response | Evidence for judges |
| --- | --- | --- |
| Codex + GPT-5.6 | Codex is the Repair Director; GPT-5.6 API workers generate persona decisions | Codex session, decision log, model audit |
| Working project | Dockerized Godot, Python analysis, Judge API, React evidence UI | One-command Judge Mode |
| Non-trivial implementation | Real game execution, typed decisions, deterministic gates, counterfactual replay | Source, tests, manifests, before/after artifacts |
| Complete design | One golden path: Campaign -> Diagnose -> Repair -> Prove | Three-stage UI and demo |
| Real impact | Reduces repetitive playtesting and regression analysis for small game teams | Measured case study |
| Novel idea | Local/cloud persona scale plus Codex-led, evidence-gated repair | Accepted or rejected patch with holdout proof |
| Easy evaluation | Cloud API Judge Mode plus replay fallback; no GPU required | Prebuilt image and sanitized demo bundle |
| Submission traceability | README, `/feedback` ID, exact commits, model/provider audit | Submission appendix |

Official sources:

- <https://openai.com/build-week/>
- <https://openai.devpost.com/>
- <https://developers.openai.com/api/docs/models>
- <https://developers.openai.com/api/docs/guides/structured-outputs>
- <https://learn.chatgpt.com/docs/build-skills>

## 3. Current project baseline

### 3.1 Capabilities already present

The repository already provides substantial competition-ready engineering:

- A real Godot reference integration (`study-in-germany`).
- Monte Carlo simulation, boundary probes, graph export, validators, and
  interactive LLM play.
- Seven agents: balance, content QA, event graph, bug hunter, boundary prober,
  value reviewer, and interactive player.
- Six configured personas: newbie, study, money, social, visa, and slacker.
- A 140-cell deterministic policy/difficulty/scenario matrix definition.
- Pydantic report contracts, manifests, source fingerprints, anomalies, value
  analysis, quality gates, and before/after comparison.
- LLM call provenance, persona-alignment metrics, risk acknowledgement,
  progress reporting, cancellation, and strict evaluation.
- A public sanitized React dashboard and decision-graph experience.
- An OpenAI-compatible model layer for vLLM, SGLang, and DeepSeek.
- A documented real local-Qwen/Godot strict playthrough and a prior 300-run
  balance baseline.

### 3.2 Verified readiness gaps

The current state is not yet judge-ready:

- The active `study-in-germany` checkout is on
  `feature/realistic-germany-pipeline`, while the required interactive,
  boundary, and graph runners exist on `origin/main`.
- The current local test invocation passed 261 tests but failed the real-game
  contract test because the active game checkout had no generated simulation
  trace; two frontend-dependent tests were skipped.
- The inspected environment did not expose Docker, Ruff, or installed frontend
  test dependencies, so a clean reproducibility claim is not yet proven.
- The React application is currently a static report viewer and has no Judge
  API for starting or monitoring campaigns.
- The provider registry does not yet include OpenAI.
- `tools/run_gameplay_agent.py` is 1,651 lines and the interactive player is
  1,379 lines; a rushed MCP wrapper would amplify existing coupling.
- No repository Skill currently exposes the competition workflow.
- No single command currently performs campaign, diagnosis, isolated repair,
  fixed replay, holdout replay, and final acceptance.

These gaps are release blockers, not details to hide in the submission.

## 4. Product definition

### 4.1 Target user

The primary user is an indie or small-studio game developer building a
simulation, narrative, strategy, or systems-heavy game without a large QA
department.

### 4.2 User problem

Traditional automated bots find mechanical failures but do not represent how
different players interpret incomplete information, tolerate risk, or pursue
conflicting goals. Manual playtests are slow and hard to replay exactly.
General coding agents can patch code, but they can overfit one failure trace or
optimize away intentional failure states.

### 4.3 Product promise

Playtest Forge combines:

1. **Persona behavior**: typed OpenAI API or local-model decisions.
2. **Deterministic execution**: Godot state transitions and fixed seeds.
3. **Evidence compression**: Python statistics, anomalies, and representative
   counterexamples instead of dumping raw logs into a model.
4. **Codex repair leadership**: repository inspection, hypothesis formation,
   constrained editing, test execution, and final judgment.
5. **Counterfactual proof**: baseline and patched game replayed under the same
   seeds plus unseen holdouts.
6. **Human control**: accepted patches remain reviewable and are never merged
   automatically.

### 4.4 Golden demo problem

The competition demo will focus on one observed game problem:

> On normal difficulty, several non-failure-intent strategies converge on
> burnout or cashflow collapse, and stress behaves like a difficult-to-recover
> attractor.

The system will not claim to solve the entire game balance. It will prove that
one failure mode can be diagnosed and one mechanism can be changed without
breaking critical invariants or erasing the deliberately failure-seeking
`slacker` persona.

Fallback by July 18: if no stable stress-attractor improvement can be proven,
the demo will use one previously observed and reproducible invariant defect.
The fallback must still run through the same repair protocol and may not be an
artificially injected bug.

## 5. System architecture

```text
Codex + repository Skill
  |-- reads AGENTS.md, design contract, campaign evidence, and source
  |-- creates/uses isolated worktree
  |-- plans one causal experiment
  |-- edits one allowlisted mechanism
  `-- accepts or rejects the patch
             |
             v
Campaign and verification services
  |-- OpenAI persona gateway (Judge Mode)
  |-- replay gateway (zero-key fallback)
  |-- vLLM/SGLang gateway (self-hosted mode)
  |-- Godot runner
  |-- analytics, anomaly, eval, and gates
  `-- repair experiment writer
             |
             v
React evidence console
  |-- Campaign
  |-- Repair
  `-- Proof
```

### 5.1 Boundary decisions

- Codex runs on the host and edits host-mounted source.
- Docker is an execution appliance, not an opaque source archive.
- The browser never calls OpenAI directly and never stores an API key.
- The backend owns provider calls, concurrency, retries, cancellation, audit,
  and budget enforcement.
- OpenAI API persona calls are called **persona workers**, not Codex
  subagents. Codex subagents may independently review evidence and regression
  risk, but only Codex makes repository changes.
- Statistics and gate decisions remain deterministic.
- No patch is automatically merged.

## 6. Runtime modes

| Mode | Persona source | GPU | API key | Purpose |
| --- | --- | ---: | ---: | --- |
| Judge/OpenAI | `gpt-5.6-luna` through backend | No | Yes, server-side | Short live campaign and official-model demonstration |
| Judge/Replay | Sanitized, real recorded traces | No | No | Guaranteed evaluator experience and full evidence replay |
| Self-hosted | Qwen through vLLM/SGLang | Yes | No cloud key | Privacy and scale story after the demo |

The application must start in Replay mode when no OpenAI key is configured.
Missing credentials may disable live persona generation but must not prevent a
judge from inspecting and replaying the complete case study.

## 7. OpenAI model and API strategy

### 7.1 Model assignment

- `gpt-5.6-luna`: high-volume weekly and event persona decisions.
- `gpt-5.6-terra`: optional bounded campaign summarization if needed.
- `gpt-5.6` in Codex: hypothesis, code reasoning, patch, verification, and
  final accept/reject decision.
- Qwen/vLLM: optional self-hosted persona workers.

Codex must remain the only component responsible for code-level diagnosis and
repair. A second API planner would dilute the Build Week story and duplicate
work.

### 7.2 Provider interface

Introduce a narrow, typed boundary rather than replacing every existing model
call at once:

```python
class PersonaDecisionGateway(Protocol):
    def decide_week(self, request: WeekDecisionRequest) -> PlayerDecision: ...
    def choose_event(self, request: EventDecisionRequest) -> EventChoiceDecision: ...
```

Implementations:

- `OpenAIResponsesPersonaGateway`
- `OpenAICompatiblePersonaGateway`
- `RecordedPersonaGateway`

The OpenAI implementation will use Responses API Structured Outputs with the
existing Pydantic `PlayerDecision` and event-choice models. The local gateway
keeps the JSON fallback required by OpenAI-compatible local models.

### 7.3 Key handling

- Never place `OPENAI_API_KEY` in React state, JavaScript bundles, browser
  storage, API responses, logs, reports, or Git.
- Local Judge Mode reads `.env.local` or a Docker secret.
- Hosted demonstration uses a deployment secret manager and a dedicated,
  restricted project key.
- The UI exposes only provider, model, configured status, estimated call count,
  campaign limits, and connection-test status.
- Hosted runs have per-session rate limits, hard maximum weeks/runs, and a
  campaign budget ceiling.
- Rotate the hosted key after judging.

### 7.4 Concurrency and failure behavior

- Weeks remain sequential inside one playthrough.
- Different playthroughs may run concurrently, default 3 and maximum 4 in
  Judge Mode.
- Retry only transport, rate-limit, and recoverable provider errors with
  bounded exponential backoff.
- One schema repair is permitted for an invalid decision; continued invalidity
  fails the playthrough and remains visible.
- API failure cannot silently become a passing fallback run.
- Persist provider, actual model, response ID, token usage, latency, refusal,
  retry count, and error category.

## 8. Docker packaging

### 8.1 Repository layout

The submission should present one cloneable top-level repository experience:

```text
game_analysis_agent/
  .agents/skills/playtest-forge/SKILL.md
  app/
  config/
  docs/
  frontend/
  reports/demo/
  study-in-germany/        # pinned subtree or initialized submodule
  docker-compose.yml
  Dockerfile.judge
```

Preferred game packaging order:

1. Pinned subtree or competition bundle if repository ownership/licensing
   permits.
2. Pinned Git submodule with automatic bootstrap and a clear commit lock.
3. Never clone an unpinned remote branch during the Docker build.

### 8.2 Compose services and profiles

Core/Judge profile:

- `godot`: pinned Godot runtime.
- `api`: Python Judge API, campaign orchestration, report access.
- `dashboard`: static React application or API-served assets.

Optional local-model profile:

- `vllm`: GPU-backed local persona provider.

The API service must not depend on a healthy vLLM service in Judge/OpenAI or
Replay mode.

### 8.3 Source and artifact mounts

- Host source is mounted read/write into the runner used by the local Codex
  task so edits persist and remain visible in Git.
- Reports are mounted to a host directory and owned by the current UID/GID.
- The judge image pins dependencies but does not conceal source code.
- Publish a prebuilt image by digest and retain the Dockerfile for inspection.
- Judge/Replay should support `linux/amd64`; Apple Silicon compatibility is a
  target for Judge/Replay even if the optional vLLM profile remains NVIDIA
  Linux only.

### 8.4 Doctor check

A preflight command must report, without leaking secrets:

- platform and architecture;
- image and source revisions;
- game runner availability;
- report-directory writability;
- OpenAI provider configured/unconfigured;
- optional GPU availability;
- selected runtime mode;
- expected live campaign cost class and enforced limits.

## 9. Codex Skill and repair protocol

### 9.1 Repository Skill location

```text
.agents/skills/playtest-forge/
  SKILL.md
  references/
    design-contract.md
    evidence-contract.md
    repair-protocol.md
  scripts/
    preflight
    run-campaign
    verify-repair
```

`AGENTS.md` retains durable repository architecture and verification rules.
The Skill contains the focused, repeatable competition workflow.

### 9.2 Skill workflow

The `$playtest-forge` Skill must instruct Codex to:

1. Run preflight and stop on missing canonical game/runtime evidence.
2. Read the design contract before inspecting outcomes.
3. Run or load the baseline persona campaign.
4. Check evidence completeness and fail closed on stale or partial artifacts.
5. Separate observed facts from model inference.
6. Select one causal failure cluster and cite representative runs/weeks.
7. Form one falsifiable hypothesis.
8. Create or use an isolated worktree.
9. Restrict edits to the allowlist and one mechanism class.
10. Run focused deterministic tests.
11. Replay the fixed baseline seeds.
12. Replay unseen holdout seeds.
13. Evaluate critical, persona, and balance gates.
14. Accept or reject the patch with an explicit reason.
15. Generate the final experiment record and human-readable summary.

### 9.3 Three locks against unsafe optimization

**Intent lock**

- `design_contract.yaml` states designed failure personas/outcomes, invariants,
  target metrics, and non-goals.

**Change lock**

- one mechanism per experiment;
- allowlisted files;
- maximum changed files and lines;
- no gate/test weakening;
- no automatic merge.

**Verification lock**

- same-seed replay;
- persona-preserving comparison;
- holdout replay;
- deterministic contract and validator suite;
- explicit rejection on overfit, missing evidence, or regression.

## 10. Evidence and artifact contracts

Every competition campaign must produce:

```text
campaign_manifest.json
campaign_summary.json
persona_runs.jsonl
agent_eval.jsonl
llm_calls.jsonl
failure_clusters.json
gate_report.json
```

Every repair experiment must produce:

```text
repair_experiment.json
repair_summary.md
baseline/
patched/
comparison.json
patch.diff
```

Minimum `repair_experiment.json` fields:

- experiment ID and timestamps;
- source, game, config, Skill, prompt, and image revisions;
- objective and design-contract hash;
- fixed and holdout seed lists;
- baseline facts with artifact/field/run/week references;
- Codex hypothesis and predicted effect;
- allowlist and modified files;
- focused test results;
- before/after/holdout metrics;
- critical gate results;
- persona alignment and designed-failure checks;
- provider/model/call provenance;
- final `accepted` or `rejected` decision and reason.

Raw prompts and game text in public bundles must be reviewed for private or
licensed content. Public evidence should be sanitized without removing the
numbers required to verify the claim.

## 11. Judge API and frontend

### 11.1 Minimal Judge API

The static frontend needs a small backend surface:

```text
GET  /api/provider-status
POST /api/provider-test
POST /api/campaigns
GET  /api/campaigns/{id}
GET  /api/campaigns/{id}/events
POST /api/campaigns/{id}/cancel
GET  /api/experiments/{id}
```

No endpoint accepts or returns an API key. Local configuration occurs before
startup through an ignored environment file or Docker secret.

### 11.2 Three-stage evidence console

**Campaign**

- active personas, seeds, weeks, model, progress, ETA, failures;
- persona-by-ending heat map;
- first entry into a failure attractor;
- decision validity and fallback/error rates.

**Repair**

- observed facts versus Codex hypothesis;
- referenced trace and source locations;
- predicted effect, allowlist, and patch diff;
- current fixed/holdout verification phase.

**Proof**

- baseline, patched fixed-seed, and holdout comparisons;
- critical, balance, and persona gates;
- accepted/rejected decision;
- complete provenance and reproducibility command.

The existing editorial visual identity should be preserved. New UI work is
limited to these three states; a general dashboard redesign is out of scope.

## 12. Golden demo execution

### 12.1 Live versus recorded work

The three-minute video will not run all 18 full playthroughs live.

- Live proof: two personas, one seed, three to five weeks through OpenAI API.
- Full evidence: a precomputed but fully audited campaign of six personas,
  three seeds, and twenty weeks.
- Codex proof: one continuous Codex task diagnoses the full campaign, changes
  one mechanism, and verifies the patch.

The recorded campaign must be generated by the same code, image, game commit,
personas, and schemas delivered to judges.

### 12.2 Success metrics

The demo may claim only measured results. Target gates are planning goals, not
facts until the final campaign exists.

- All critical invariants remain zero.
- No illegal action or unknown/pipeline-stalled ending is introduced.
- Fixed-seed target failure concentration improves.
- Holdout seeds confirm direction without material regression.
- Persona alignment does not materially decline.
- Non-failure-intent personas improve without requiring the slacker persona to
  win.
- The final patch is accepted only if every required evidence dimension is
  present and valid.

### 12.3 Demonstration storyboard

Provisional video allocation:

| Time | Content |
| --- | --- |
| 0:00-0:20 | Problem: small game teams cannot cheaply replay diverse human behavior |
| 0:20-0:45 | One command starts Dockerized Judge Mode and a short live OpenAI campaign |
| 0:45-1:10 | Persona differences and the shared failure attractor appear |
| 1:10-1:40 | Codex reads evidence, cites source, and states one falsifiable hypothesis |
| 1:40-2:10 | Codex applies one constrained patch in an isolated worktree |
| 2:10-2:40 | Same-seed and holdout proof; gates; accepted or rejected result |
| 2:40-3:00 | Impact, reproducibility, and self-hosted local-model option |

The final cut must remain under three minutes and explicitly narrate how Codex
and GPT-5.6 are used.

## 13. Implementation work breakdown

### P0: Restore a canonical baseline

- Select and pin the canonical `study-in-germany` commit containing all
  required runners and validator contracts.
- Choose subtree/submodule/bundle packaging and verify licensing.
- Generate a real 20-week baseline trace.
- Run Python, Ruff, frontend, build, Godot contract, economy, risk, route, and
  demo validation from a clean environment.
- Record exact command output and revisions.

Exit gate: no stale or missing runner/report evidence; all required baseline
checks pass or have an explicit blocking owner.

### P1: Add cloud and replay persona gateways

- Add `openai` and `replay` providers without breaking local backends.
- Implement typed Responses API decisions with Pydantic Structured Outputs.
- Add provider response provenance and refusal/error handling.
- Add bounded concurrency, retry, cancellation, and cost limits.
- Test cloud gateway with mocked SDK and replay gateway with committed fixtures.

Exit gate: identical `PlayerDecision`/event contracts feed the interactive
player for OpenAI, replay, and local providers.

### P2: Build Campaign orchestration

- Add typed campaign request/result models.
- Run persona/seed cells with isolated report directories.
- Support resume and explicit partial/failure status.
- Aggregate campaign metrics and failure clusters.
- Generate the campaign manifest and public-safe bundle.

Exit gate: `6 personas x 3 seeds x 20 weeks` produces complete, auditable
evidence or fails closed with the exact incomplete cells.

### P3: Build repair experiment protocol and Skill

- Add design, evidence, and repair schemas.
- Add repository Skill and reference files.
- Implement allowlist and change-budget validation.
- Implement fixed/holdout comparison and patch decision writer.
- Run the core implementation in one traceable Codex task and retain the
  `/feedback` Session ID.

Exit gate: Codex can accept or reject one real patch with field-level evidence.

### P4: Package Judge Mode

- Build CPU-only Judge image and Compose profile.
- Remove forced dependency on vLLM.
- Add provider status, campaign, progress, cancellation, and experiment APIs.
- Add Campaign/Repair/Proof UI states.
- Publish a pinned prebuilt image and test a clean clone.

Exit gate: a judge without GPU can inspect the full case and see a first result
within five minutes.

### P5: Submission assets

- Finalize README quickstart, supported platforms, architecture, test path,
  sample data, security, limitations, and exact OpenAI/Codex role.
- Produce measured case-study numbers.
- Record and caption the under-three-minute YouTube video.
- Capture screenshots and a concise Devpost description.
- Add `/feedback` Session ID and repository access instructions.
- Perform secret, license, privacy, and clean-clone checks.

## 14. Schedule and ownership

| Date | Mandatory outcome |
| --- | --- |
| July 16 | Canonical game/runtime decision, plan approved, branch ready |
| July 17 | Baseline clean run; OpenAI/replay gateway; credits requested before cutoff |
| July 18 | Complete persona campaign and selected repair target |
| July 19 | Codex repair protocol, fixed/holdout proof, first accepted/rejected experiment |
| July 20 | Judge image, three-stage UI, clean-clone test, video rough cut |
| July 21 | Submission-only fixes, final recording, README, Devpost before 5:00 PM PT |

If schedule slips, cut in this order:

1. Hosted public execution; keep local Judge Mode and public static evidence.
2. Terra campaign summarization; Codex reads deterministic evidence directly.
3. Local vLLM live demo; retain documented self-hosted mode.
4. Extra personas and scenarios; never cut fixed/holdout proof.
5. Additional dashboard views; never cut the one golden path.

## 15. Test and acceptance matrix

### 15.1 Unit and contract tests

- settings/provider selection and missing-key behavior;
- Responses API structured decision and refusal/error mapping;
- replay gateway fixture integrity;
- persona alignment and designed-failure logic;
- campaign isolation, resume, cancellation, partial failure, and aggregation;
- repair schema, allowlist, change budget, and accept/reject logic;
- key redaction from logs, APIs, artifacts, and frontend bundles;
- frontend API decoding and Campaign/Repair/Proof states.

### 15.2 Integration tests

- Dockerized Godot version and runner health;
- full fixed-seed baseline;
- one OpenAI short playthrough;
- one replay full campaign;
- fixed and holdout comparison;
- critical validators and quality gates;
- clean-clone Judge Mode on a supported CPU platform.

### 15.3 Release gates

- No committed secret or browser-accessible key.
- No missing/stale artifacts presented as valid.
- No undocumented failure fallback.
- No auto-merge.
- No evidence claim without source artifact and field reference.
- No result claimed from a different game/config/model revision.
- Under-five-minute first judge result.
- Under-three-minute narrated public video.
- Repository and prebuilt test path available through the judging period.

## 16. Impact measurement

The final submission will report measured, not estimated, values for:

- campaign runtime and provider-call count;
- input/output tokens and bounded cost;
- valid-decision, fallback, error, and persona-alignment rates;
- unique failure clusters and representative counterexamples;
- Codex hypotheses attempted;
- patches rejected and accepted;
- before/after fixed and holdout outcome metrics;
- deterministic gates preserved;
- clean-clone setup and time-to-first-result.

The case study must state its limits: one reference game and one validated
repair do not prove universal game compatibility.

## 17. Risks and mitigations

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Codex appears incidental | Critical | Codex owns hypothesis, source edit, verification, and final decision |
| Demo requires GPU | Critical | OpenAI Judge Mode plus replay fallback |
| Browser/API key leak | Critical | Backend-only secret, redaction tests, no key endpoint |
| Game repo mismatch | Critical | Pin canonical commit and verify runner contracts first |
| Balance fix is ambiguous | High | Design contract, one mechanism, same seeds, holdouts, explicit rejection |
| Campaign too slow for video | High | Short live run plus complete precomputed audited campaign |
| Local/cloud behaviors differ | High | Shared typed decision contract and provider-specific eval metrics |
| Project feels like a framework, not product | High | One golden path and three-stage evidence console |
| Too much refactoring | High | No MCP; narrow persona gateway and campaign boundary |
| Overclaiming impact | Medium | One measured case study with explicit limits |
| Judge cannot rebuild | High | Prebuilt pinned image and replay bundle |
| Public bundle leaks game content | High | Sanitization review and public manifest |

## 18. Explicit non-goals for Build Week

- MCP adapter or remote authenticated MCP service.
- Full service-layer migration of all 14 CLI commands.
- Unity or Unreal integration.
- General automatic game balancing.
- Automatic merge or production deployment.
- New personas beyond the existing six.
- A complete dashboard redesign.
- A multi-game benchmark.
- Replacing deterministic gates with model judgment.

## 19. Post-competition path

After the Build Week submission:

1. Complete the existing service-first migration for simulation, reports,
   gameplay, and validation.
2. Make both CLI and Skill call the typed services.
3. Pass service-layer security, isolation, and compatibility gates.
4. Add an MCP adapter only after those gates pass.
5. Expand the repair protocol to additional games and engines.

## 20. Judge review log

### Review Pass 1: Technological implementation and Codex centrality

**Review question**

Does the plan use Codex deeply and skillfully, and does it describe a working,
non-trivial implementation rather than a project merely authored with Codex?

**Initial findings**

1. A generic project-audit Skill would make Codex look like documentation
   tooling rather than the product's decision-maker.
2. Requiring local Qwen/vLLM would make the strongest code path difficult for
   judges to run and would under-emphasize GPT-5.6.
3. A frontend API-key field would create an unacceptable client-side secret
   boundary.
4. Calling API persona workers “Codex subagents” would blur the actual product
   architecture.
5. A rushed MCP adapter would violate the repository's service-first rule and
   spend the deadline on plumbing instead of a proven repair.
6. A patch without fixed/holdout replay would be an unverified coding-agent
   demo, not an evidence-gated developer tool.

**Changes applied in this revision**

- Defined Codex as the sole Repair Director for hypothesis, code changes,
  verification, and final decision.
- Split Judge/OpenAI, Judge/Replay, and self-hosted runtime modes.
- Added a backend-only key boundary and explicit redaction tests.
- Defined persona workers separately from Codex subagents.
- Preserved the service-first MCP rule and made MCP a post-competition step.
- Added intent, change, and verification locks with fixed and holdout seeds.
- Added typed gateway, artifact, Skill, Docker, UI, and acceptance contracts.

**Pass 1 verdict**

Conditional pass. The plan now demonstrates deep Codex/GPT-5.6 integration
and non-trivial engineering. It is not competition-ready until the canonical
game baseline, one real repair experiment, and clean Judge Mode are proven.

