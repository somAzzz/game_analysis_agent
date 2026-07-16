---
status: active
date: 2026-07-16
last_updated: 2026-07-16
requirements_verified: 2026-07-16
audience: maintainers, judges, contributors
scope: OpenAI Build Week 2026 competition implementation and submission plan
---

# Playtest Forge: OpenAI Build Week 2026 Implementation Plan

Execution companion:
[EXECUTION_PLAN.md](EXECUTION_PLAN.md) translates this strategy into ordered
steps, review packets, gate criteria, failure handling, and release decisions.

> Current truth label: the retained 18-cell campaign is real Godot evidence
> driven by a deterministic persona-policy authoring fixture, not a recorded
> OpenAI/LLM playthrough. The OpenAI GPT-5.6 persona path is implemented as a
> separate bounded live mode and remains a release blocker until live evidence
> is imported. See the [reviewer hub](README.md).

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

The Build Week version will use a repository-scoped Codex Skill, an offline
machine-readable evaluator, a portable Replay bundle, and an optional
Dockerized human interface. It will not add an MCP adapter before the existing
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
| Working project | Godot, Python analysis, Judge API, React evidence UI | Offline evaluator plus optional one-command Judge UI |
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
- <https://learn.chatgpt.com/docs/environments/cloud-environment>
- <https://learn.chatgpt.com/docs/cloud/internet-access>
- <https://github.com/openai/codex-universal>

### 2.1 Evaluation-environment evidence boundary

The Build Week brief does **not** publish an automated-preselection runtime,
state that an AI performs the initial review, or guarantee Docker, network,
GPU, browser, writable ports, secrets, or an OpenAI API key. The submission
must not present any such assumption as an official fact.

The deployment design will nevertheless defend against the strictest
reasonable automated-review environment. The closest documented OpenAI
execution reference is Codex cloud: it checks out the repository into an
isolated managed container, runs setup with network access, then runs the agent
phase offline by default; setup secrets are removed before the agent phase.
The public `openai/codex-universal` image approximates this environment but is
explicitly not identical to it.

Therefore automated evaluation is treated as an additional compatibility
target with these conservative assumptions:

- Linux `amd64`, non-interactive, and no TTY;
- repository checkout only, with no sibling game repository;
- no Docker daemon or nested-container privilege;
- no GPU, API key, or secret during the test phase;
- network unavailable after setup and possibly unavailable throughout;
- only repository-local writes, blocked port binding, and a short timeout;
- scoring may use README, source, machine-readable output, committed evidence,
  and the public video without completing the full live campaign.

The design rule is: every deeper runtime layer may add evidence, but failure of
Docker, network, credentials, Godot, or OpenAI must never prevent the evaluator
from validating the committed reference experiment.

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
- The inspected development host is Apple Silicon macOS (`arm64`), but Docker
  is not installed or not on `PATH`; the system Python is 3.9 while the project
  requires Python 3.10 or newer, and the installed native Godot is 4.7 rather
  than the competition target 4.4.
- The current Compose default starts an NVIDIA Blackwell/NVFP4 vLLM service,
  and the `agent` service waits for vLLM health. That path cannot be the macOS,
  Judge, or automated-evaluator default.
- The current `barichello/godot-ci:4.4` image is `linux/amd64` only. It may run
  through Apple Silicon emulation, but that is a best-effort developer fallback
  rather than a supported macOS delivery path.

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

### 4.5 Idea quality and differentiation

The novelty claim is not that language models can play games or that coding
agents can edit game code. The differentiated product is the closed,
auditable experiment that connects those capabilities while preserving game
design intent.

| Approach | Diverse player intent | Reproducible execution | Changes source | Tests causal claim on holdouts | Can reject its own patch |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scripted game bot | Limited | Yes | No | No | No |
| LLM playtest report | Yes | Sometimes | No | No | No |
| General coding agent from a bug report | No | Depends on prompt | Yes | Usually no | Sometimes |
| Playtest Forge | Yes | Yes | Yes, constrained | Yes | Yes, by explicit gates |

This is a conceptual comparison, not a claim that no adjacent product exists.
The competition-worthy idea is the combination of:

- behavioral diversity before diagnosis;
- deterministic evidence instead of model-generated conclusions;
- a design-intent contract that distinguishes desired difficulty from defects;
- one falsifiable repair experiment rather than open-ended auto-balancing;
- acceptance or rejection under both fixed and unseen seeds.

Rejection is a successful product outcome. Preventing an attractive but
overfit patch from reaching a human review is as valuable as generating a
valid patch, and makes the tool credible for real repositories.

### 4.6 Why Codex is indispensable

Persona workers know only the public decision schema and current game state.
They cannot inspect the repository, select an implementation mechanism, edit
source, run repository-specific validation, or judge a Git diff. Codex can
connect all of those contexts through the repository Skill. Removing Codex
would leave a useful playtest report but eliminate the core product promise:
turning evidence into a bounded, reviewable, and proven repair experiment.

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

| Mode | Persona source | Docker | GPU | API key | Purpose |
| --- | --- | ---: | ---: | ---: | --- |
| Automated/Inspect | Committed manifests and repair evidence | No | No | No | Sub-minute schema, hash, provenance, and claim validation |
| Automated/Replay | Small committed real-trace fixture | No | No | No | Non-interactive replay smoke test and machine-readable result |
| Judge/Replay | Sanitized full recorded traces | Optional | No | No | Guaranteed human evaluator experience and full evidence replay |
| Judge/OpenAI | `gpt-5.6-luna` through backend | Optional | No | Yes, server-side | Short live campaign and official-model demonstration |
| Self-hosted/NVIDIA | Qwen through vLLM/SGLang | Yes | Yes | No cloud key | Optional Linux privacy and scale path |
| Self-hosted/Mac | MLX-optimized model through native vLLM-Metal | No | Apple Metal | No cloud key | Experimental developer option, never a judge dependency |

The repository-level `judge` entrypoint must select Automated/Inspect when no
mode is given. The interactive application must select Replay when no OpenAI
key is configured. Missing credentials may disable live persona generation but
must not prevent any evaluator from inspecting and replaying the case study.
No local-model service may be started implicitly.

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

## 8. Portable deployment and Docker packaging

### 8.1 Repository layout

The submission should present one cloneable top-level repository experience:

```text
game_analysis_agent/
  .agents/skills/playtest-forge/SKILL.md
  AGENTS.md
  JUDGE.md
  judge                       # non-interactive offline entrypoint
  judge-manifest.json
  app/
  config/
  docs/
  frontend/
  reports/demo/
  study-in-germany/        # pinned subtree or initialized submodule
  docker-compose.yml
  Dockerfile.judge
  scripts/setup-evaluator
  scripts/judge-smoke-test
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

- `vllm`: GPU-backed local persona provider under an explicit
  `local-nvidia` profile.

The API service must not depend on a healthy vLLM service in Judge/OpenAI or
Replay mode. A bare `docker compose up` must not start vLLM. Native
vLLM-Metal on macOS, if configured, connects through the same
`OpenAICompatiblePersonaGateway` URL and remains outside the Judge Compose
dependency graph.

### 8.3 Source and artifact mounts

- Host source is mounted read/write into the runner used by the local Codex
  task so edits persist and remain visible in Git.
- Reports are mounted to a host directory and owned by the current UID/GID.
- The judge image pins dependencies but does not conceal source code.
- Publish prebuilt API/dashboard/replay Judge images by digest for
  `linux/amd64` and `linux/arm64` and retain the Dockerfile for inspection.
- The API/dashboard/replay image must be natively multi-architecture. It may
  not rely on Apple Silicon emulation of an `amd64` image.
- Linux `amd64` may continue using the pinned Godot container after clean-room
  verification. macOS Apple Silicon uses an official pinned native Godot 4.4
  executable for real game runs until a verified ARM64 Godot image exists.
- Every runtime path must compare Godot version, project version, and report
  contract before accepting evidence.

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

The doctor command must have both human text and JSON output. An unsupported
optional capability is a warning; a missing requirement for the selected mode
is a typed failure with a remediation command.

### 8.5 macOS Apple Silicon implementation contract

All competition-critical development and demonstration work can run on macOS,
provided the NVIDIA path is treated as optional:

- pin Python 3.12 in a project environment rather than using system Python;
- pin Node.js 20 for frontend build and tests;
- install and verify native Godot 4.4 for real gameplay execution;
- run the real-game Python worker and Godot natively together on macOS; the
  ARM64 Docker path guarantees Replay/UI portability and does not pretend to
  contain a verified ARM64 Godot runtime;
- use Docker Desktop only for the containerized Judge/Replay compatibility
  path, not as a requirement for offline evidence inspection;
- run OpenAI persona workers from the backend with a server-side key;
- default to Replay when the key is absent;
- use native vLLM-Metal with an MLX-optimized model only as an experimental
  self-hosted provider, never as parity with the NVIDIA NVFP4 configuration;
- prohibit hard-coded `/home/...` paths and normalize paths, UID ownership,
  executable bits, and line endings across macOS and Linux.

The required macOS acceptance run is:

1. fresh Apple Silicon user account;
2. pinned Python/Node/Godot versions installed by documented commands;
3. Automated/Inspect and Automated/Replay without Docker;
4. Judge/Replay through Docker Desktop using native ARM64 images;
5. one native-Godot deterministic playthrough;
6. one Judge/OpenAI short campaign;
7. fixed/holdout repair verification and artifact-hash comparison against the
   Linux reference run.

### 8.6 Unknown automated-evaluator deployment ladder

An AI evaluator should discover one obvious command in `AGENTS.md`, the README,
`JUDGE.md`, and the root directory. The entrypoint must be deterministic,
non-interactive, offline-first, and layered:

| Tier | Command contract | Dependencies | Maximum expected time | Result |
| --- | --- | --- | --- | --- |
| 0: Inspect | `./judge --mode inspect --offline --json` | Python standard library only | 30 seconds | Validate manifest, schemas, hashes, provenance, claim references |
| 1: Replay smoke | `./judge --mode replay-smoke --offline --json` | Locked Python environment | 120 seconds | Replay a small real fixture and evaluate representative gates |
| 2: Full replay | `./judge --mode replay --offline --json` | Locked Python environment; Docker optional | 5 minutes | Validate the complete committed reference experiment |
| 3: Interactive | Docker dashboard or native local services | Browser and optional Docker | 5 minutes to first result | Human Campaign/Repair/Proof experience |
| 4: Live OpenAI | `OPENAI_API_KEY` available to backend | Network and secret | Optional | Short fresh persona campaign |

Tier 0 must not import project packages that trigger unavailable optional
dependencies. Tier 1 must use only committed fixtures and lockfiles. Tiers 0-2
must not bind a port, launch a browser, call GitHub, pull an image, download a
model, use a sibling checkout, or require approval. Tier 4 is never used to
decide whether the submission is basically runnable.

`scripts/setup-evaluator` is an idempotent, non-root setup-phase helper. It
installs only locked Python and frontend dependencies, verifies hashes, and
does not start services or require secrets. A corresponding maintenance check
updates the environment only when lockfiles change. This matches the documented
Codex cloud split between networked setup and an offline agent phase without
claiming that Build Week uses Codex cloud for judging.

### 8.7 AI-readable repository interface

`AGENTS.md` must place the evaluator quickstart before developer-only Godot and
vLLM instructions. `JUDGE.md` must contain:

- the one-sentence product claim and Developer Tools category;
- the exact Tier 0 and Tier 1 commands;
- expected exit code, duration, and output path;
- links from every claim to a committed artifact and field;
- the Docker and macOS paths as optional deeper validation;
- explicit limitations and which evidence is prerecorded;
- instructions for interpreting accepted, rejected, partial, and unavailable
  states.

`judge-manifest.json` must be the machine-readable table of contents. It records
schema version, source/game/image revisions, platform matrix, commands,
timeouts, fixture hashes, experiment IDs, expected gate outcomes, public demo
URL, and documentation paths. A model should not have to infer the canonical
command from prose or search across historical reports.

For Codex-based review, the root `AGENTS.md` must route matching game-test and
repair tasks to the repository-scoped `$playtest-forge` Skill after offline
Inspect/Replay. README must provide the exact explicit invocation. The manifest
must name and hash the Skill directory. Because the external judging surface is
not guaranteed to expose Codex Skill selectors, the same instructions must
require direct reading of `.agents/skills/playtest-forge/SKILL.md` as a
functionally equivalent fallback; do not claim universal auto-loading outside
documented Codex environments.

### 8.8 Automated-deployment failure protocol

The root entrypoint writes `artifacts/judge-result.json` atomically when the
selected output directory is writable and always emits the same compact JSON
object on stdout. `--output-dir -` is explicit stdout-only mode. Required
fields are `status`, `stage`, `mode`, `platform`, `duration_ms`, `checks`,
`artifacts`, `limitations`, `error_code`, and `remediation`. Logs go to stderr.
No ANSI control sequences, progress spinners, prompts, or background processes
are allowed in JSON mode.

Stable exit-code families:

- `0`: selected mode completed and all required checks passed;
- `2`: invalid invocation;
- `10`: unsupported platform or runtime;
- `11`: missing or incompatible dependency;
- `12`: missing, stale, or hash-invalid evidence;
- `13`: deterministic test or gate failure;
- `14`: timeout, cancellation, or external provider failure;
- `15`: internal harness error.

Fallback changes capability, never truth. For example, a missing API key may
select Replay before a live run begins, but an OpenAI call that fails mid-run
must produce `status: failed`, not silently reuse recorded output.

| Likely automated-test failure | Required behavior |
| --- | --- |
| Docker daemon/socket unavailable | Continue with Tiers 0-2; mark Docker unavailable, not project failure |
| `amd64`/`arm64` image mismatch | Use native offline path; never start emulation implicitly |
| Network disabled or DNS blocked | Use committed fixtures and locks; print no retry storm |
| API key/secret absent | Select Replay before execution and state that live mode was not tested |
| Sibling game repo or submodule unavailable | Use the pinned competition bundle; fail artifact hash validation if absent |
| Godot unavailable | Complete evidence inspection/replay; identify real-game execution as unverified |
| Port binding/browser unavailable | Produce JSON and static HTML artifacts without starting the dashboard |
| Workspace read-only | Support `--output-dir` and stdout-only mode; never write outside the workspace |
| CPU/RAM/time limit | Use bounded fixture sizes and hard child-process timeouts; preserve partial diagnostics |
| Interrupted or orphaned process | Trap signals, terminate process groups, and write an incomplete result atomically |
| Dependency install failure | Report package, lock hash, command, and setup-stage failure without ad hoc upgrades |
| OpenAI quota, rate limit, or schema error | Fail live mode visibly; keep the separately labeled Replay path available |

The evaluator compatibility test must run with network disabled, no secrets,
no Docker socket, no GPU device, no TTY, and a temporary repository-local output
directory. It must also be exercised in the public `openai/codex-universal`
image for `linux/amd64`. Because that image is only an approximation, passing
it is evidence of portability rather than proof of the undisclosed judging
environment.

## 9. Codex Skill and repair protocol

### 9.1 Repository Skill location

```text
.agents/skills/playtest-forge/
  SKILL.md
  agents/openai.yaml
  references/
    design-contract.md
    evidence-contract.md
    repair-protocol.md
    test-strategy.md
    automated-testing.md
    subagent-playthrough.md
    evidence-to-parameters.md
    scenario-balance-economy.md
    scenario-content-flow.md
    scenario-boundary-robustness.md
    migration-guide.md
    session-case-study.md
  scripts/
    preflight
    run-campaign
    verify-repair
```

`AGENTS.md` retains durable repository architecture and verification rules.
The Skill contains the focused, repeatable competition workflow.

Automated inspection must not require an evaluator to know or explicitly
invoke the Skill. `AGENTS.md` routes any “test”, “evaluate”, or “judge” task to
the root offline entrypoint first; the Skill is then the deeper Codex repair
workflow after evidence validity is established.

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

### 9.3 Transferable test-to-change guidance

The Skill is a reusable game-review method, not only a wrapper around the
retained Build Week campaign. Its core routes Codex among deterministic
automation, live persona/subagent playthroughs, Replay, evidence-to-parameter
reasoning, balance/economy review, content-flow review, and
boundary/invariant review. Engine- and game-specific commands, personas,
paths, and thresholds live in a project profile.

The default causal sequence is automation discovers → persona workers expose
intent → Codex cites and hypothesizes → one parameter/mechanism changes →
focused tests establish legality → fixed and holdout automation decides →
persona/design gates preserve intended behavior. Persona workers never inspect
private source or modify code. Replay remains a reproducibility mode, not a
fresh subagent result.

Migration to another game requires only an adapter for reset/observe/step,
catalog export, validators, isolated reports, focused tests, and diffs plus a
new project profile. Acceptance requires at least one baseline, one behavioral
or explicitly automation-only campaign, one rejected candidate, unseen
holdouts, and invariant-preserving evidence.

### 9.4 Three locks against unsafe optimization

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

### 11.3 Judge-visible design principles

- **Progressive disclosure**: the first screen answers what failed, what
  changed, and whether the proof passed; raw traces remain one level deeper.
- **Evidence before explanation**: measured facts and trace references appear
  before the Codex hypothesis.
- **Uncertainty is visible**: partial campaigns, API errors, missing evidence,
  and rejected patches cannot render as success.
- **Before/after symmetry**: baseline and patched views use the same metrics,
  seed groups, and visual scales.
- **One focal action**: each stage has one primary next step—run, inspect, or
  verify—so a judge can follow the golden path without learning the framework.
- **Accessible proof**: status is never encoded by color alone; tables and
  charts include text labels and keyboard-readable summaries.

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
| 0:20-0:45 | One offline command validates the evidence bundle, then the dashboard starts a short live OpenAI campaign |
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

- Add root `judge`, `JUDGE.md`, `judge-manifest.json`, offline fixtures, stable
  JSON output, and documented exit codes.
- Add idempotent evaluator setup and maintenance checks with locked
  dependencies.
- Build native `linux/amd64` and `linux/arm64` CPU-only
  API/dashboard/replay Judge images and a Compose profile.
- Remove forced dependency on vLLM.
- Add provider status, campaign, progress, cancellation, and experiment APIs.
- Add Campaign/Repair/Proof UI states.
- Add the native pinned-Godot macOS path and test it against Linux evidence.
- Publish pinned prebuilt images and test clean clones on Linux and macOS.
- Run the offline evaluator with network, secrets, Docker, GPU, TTY, and port
  binding unavailable; repeat in `openai/codex-universal` `linux/amd64`.

Exit gate: an unknown restricted evaluator gets a machine-readable result in
under two minutes, and a human judge without GPU gets the full case in under
five minutes.

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
- frontend API decoding and Campaign/Repair/Proof states;
- judge-manifest schema, artifact traversal protection, and hash validation;
- JSON stdout purity, atomic result writes, stable exit codes, and remediation
  fields;
- preselected Replay behavior when credentials are absent and visible live-run
  failure after a provider call begins;
- hard timeouts, signal cleanup, and stdout-only/read-only operation.

### 15.2 Integration tests

- Dockerized Godot version and runner health;
- full fixed-seed baseline;
- one OpenAI short playthrough;
- one replay full campaign;
- fixed and holdout comparison;
- critical validators and quality gates;
- clean-clone Judge Mode on a supported CPU platform;
- native macOS Godot 4.4 result compared with the Linux reference;
- native ARM64 Judge/Replay through Docker Desktop;
- offline Inspect/Replay with Docker socket, network, secrets, GPU, TTY, and
  port binding removed;
- `openai/codex-universal` `linux/amd64` compatibility run with pinned Python
  3.12 and Node 20.

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
- Tier 0 succeeds from a repository-only checkout without setup, Docker,
  network, secrets, sibling repositories, or imported optional packages.
- Tier 1 completes under its documented timeout in an offline locked
  environment.
- Machine-readable mode contains no prompts, spinners, ANSI output, or mixed
  stdout logs.
- Every unsupported capability is distinguished from a failed required check.

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

### 16.1 Minimum impact experiment

The submission should include one small but honest workflow comparison using
the same failure target:

1. Record the time and manual steps required to locate the failure cluster
   from raw playthrough output and prepare a reproducible developer report.
2. Run Playtest Forge from the committed campaign bundle and record time to
   cited hypothesis, time to candidate patch, and time to accept/reject proof.
3. Report compute/API cost, failures, and human interventions for both the
   live and replay paths.
4. Ask at least one developer who did not build the workflow to complete the
   clean-clone judge path and record setup time, points of confusion, and
   whether the final decision was independently understandable.

This is not a statistically significant user study. It is a concrete case
study that tests the claimed value and exposes setup or comprehension costs.

### 16.2 Impact claim ladder

Claims must advance only as evidence becomes available:

| Level | Permitted claim | Required evidence |
| --- | --- | --- |
| 0 | The architecture is designed to reduce repetitive QA work | Plan and contracts |
| 1 | The reference case is reproducible | Clean clone, replay bundle, artifact hashes |
| 2 | One real repair was accepted or rejected correctly | Full fixed/holdout experiment record |
| 3 | The workflow reduced time or effort in this case | Timed comparison and intervention log |
| 4 | Another developer could use and understand it | Independent clean-room test |

The Devpost text and video may use only the highest level actually completed.

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
| Automated evaluator cannot use Docker/network/secrets | Critical | Standard-library Inspect plus offline Replay and typed JSON result |
| Apple Silicon uses slow/unstable emulation | High | Native ARM64 replay image and native pinned Godot for real runs |
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

## 20. Submission and judge-readiness contract

This section distinguishes required final behavior from evidence that exists
today. Nothing marked `planned`, `unverified`, or `missing` may be described as
complete in the submission.

### 20.1 Clean-room judge path

The final repository README must expose the following stable interface. These
commands are a target contract and do not yet constitute a verified quickstart:

```bash
git clone <submission-repository-url>
cd game_analysis_agent
./judge --mode inspect --offline --json
./judge --mode replay-smoke --offline --json
```

Those two commands are the primary automated-evaluator path. The optional
human interface continues with:

```bash
docker compose --profile judge pull
PLAYTEST_FORGE_MODE=replay docker compose --profile judge up -d
./scripts/judge-smoke-test
```

The offline output must report the product claim, evidence status, artifact
paths, limitations, and next optional command. Docker startup must print the
dashboard URL, expected image digest, source revision, demo-bundle revision,
and the command that stops the stack. The evaluator should then be able to:

1. validate hashes, provenance, and the central claim in under 30 seconds;
2. replay a representative real fixture in under two minutes;
3. inspect Campaign, Repair, and Proof without an API key, GPU, or rebuild;
4. optionally use the digest-pinned dashboard when Docker is available;
5. optionally add `OPENAI_API_KEY` to an ignored server-side `.env.local` and
   start the bounded live campaign;
6. open the repository in Codex and invoke `$playtest-forge` against the
   included evidence bundle to reproduce the repair judgment.

The README must also include a source-build path for maintainers. That path is
secondary to the prebuilt, digest-pinned judge path required by the challenge.

### 20.2 Supported-platform statement

Only tested combinations may be listed as supported:

| Platform | Offline Inspect/Replay | Dashboard Replay | Judge/OpenAI | Self-hosted local model |
| --- | --- | --- | --- | --- |
| Restricted Linux `amd64` container | Required | Not assumed | Not assumed | Not supported |
| Linux `amd64` + Docker | Required | Required | Required | Optional, NVIDIA only |
| Linux `arm64` + Docker | Required | Required | Required | Not supported |
| macOS Apple Silicon | Required | Required through Docker Desktop | Required | Experimental vLLM-Metal |
| Other platforms | Best effort, not advertised until tested | Best effort | Best effort | Not supported |

The final compatibility table must replace `target` with a tested image
digest, test date, and result. Browser support should name the exact versions
used for Chrome, Firefox, and Safari smoke tests.

### 20.3 Submission compliance ledger

| Deliverable | Status on July 16 | Completion evidence | Stop-ship owner |
| --- | --- | --- | --- |
| Developer Tools category | Decided | Devpost category selection | Maintainer |
| Working project | Partial | Clean-clone replay plus optional live run | P0-P4 |
| Project description | Planned | Final Devpost text with measured claims | P5 |
| Public YouTube demo under 3 minutes | Missing | Public URL, audio, captions, duration check | P5 |
| Video explains both Codex and GPT-5.6 | Planned | Narration transcript and final video | P5 |
| Judge-accessible code repository | Pending packaging decision | Public licensed repo, or private access granted to required judge accounts | P0/P5 |
| README setup, sample data, and run guide | Partial | Clean-room-tested README | P4/P5 |
| Codex decisions and acceleration highlighted | Planned | Session references, decision log, README section | P3/P5 |
| `/feedback` core Codex Session ID | Missing | ID captured from the core implementation task and entered in Devpost | P3/P5 |
| Installation instructions | Planned | Prebuilt and source-build paths | P4/P5 |
| Supported platforms | Unverified | Dated compatibility matrix | P4 |
| Test without rebuilding | Planned | Pinned image plus replay bundle and smoke test | P4 |
| AI-readable offline evaluator path | Planned | Tier 0/1 JSON results under restricted-environment test | P4 |
| Secret, privacy, and license review | Missing | Signed release checklist and scan results | P5 |
| Submission before deadline | Scheduled | Devpost confirmation before July 21, 5:00 PM PT | Maintainer |

If the repository remains private, it must be shared with
`testing@devpost.com` and `build-week-event@openai.com`, as specified by the
challenge page. The maintainer must separately confirm eligibility and the
official rules; this engineering plan is not a legal eligibility review.

### 20.4 Judge time budget

| Elapsed time | Expected proof |
| --- | --- |
| 0-30 seconds | Offline Inspect validates manifest, hashes, provenance, and claim references |
| 30 seconds-2 minutes | Replay smoke validates a real fixture and representative gates |
| 2-5 minutes | Optional full replay/dashboard makes the problem and repair decision understandable |
| 5-8 minutes, optional | Small OpenAI persona campaign completes under hard limits |
| 8-12 minutes, optional | Smoke test and artifact references verify the displayed claim |

Failure of either mandatory offline step is a release blocker. Docker, browser,
live-provider latency, or quota must not make the offline path unavailable.

### 20.5 Final stop-ship checklist

Do not submit until all of the following are true:

- the canonical game commit contains every required runner and passes its real
  contract tests;
- the root offline entrypoint succeeds without network, secrets, Docker, GPU,
  TTY, port binding, or a sibling checkout;
- an AI can discover the canonical command from `AGENTS.md`, README,
  `JUDGE.md`, and `judge-manifest.json` without guessing;
- a clean machine can use the pinned image and replay bundle without a GPU,
  OpenAI key, or local build;
- the demo bundle hashes match the source, game, configuration, and image
  revisions displayed in the UI;
- the repair record contains fixed and holdout evidence and an honest
  accept/reject result;
- no secret, private prompt, unlicensed asset, or inaccessible dependency is
  included;
- the public video is under three minutes, has audio, and visibly explains the
  distinct roles of Codex and GPT-5.6;
- the repository is accessible to judges for the full judging period;
- the `/feedback` Session ID comes from the task where the majority of core
  functionality was built;
- every numerical Devpost or video claim resolves to a committed artifact;
- the Devpost submission confirmation is recorded before the deadline.

### 20.6 Internal shortlist scorecard

The official criteria are not assigned weights on the public brief, so this
is a readiness rubric rather than a prediction of judge scoring:

At the July 16 verification, Devpost displayed 19,688 registered participants
and only first- and second-place awards for Developer Tools. Registrations are
not the same as completed submissions, but the visible competition level means
functional completeness alone is not a shortlist strategy.

| Official criterion | Shortlist-level proof | Current decisive risk |
| --- | --- | --- |
| Technological implementation | Real Godot run, typed OpenAI decisions, Codex patch, deterministic fixed/holdout gates | Integration remains unbuilt |
| Design and user experience | One understandable Campaign -> Repair -> Proof journey in under five minutes | Current frontend is report-only |
| Potential impact | Timed case study and independent clean-room use with bounded cost | No measured comparison yet |
| Quality of idea | Intent-aware closed-loop repair, including credible rejection of overfit patches | Novelty exists only on paper until demonstrated |

A polished video cannot compensate for a broken judge path, and a large code
base cannot compensate for an unclear before/after claim. The strongest
submission is the smallest complete version that clears all four rows.

## 21. Judge review log

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

### Review Pass 2: Quality of idea, product design, and potential impact

**Review question**

Would a judge remember this as a focused product with a defensible idea and
measurable value, rather than as a collection of technically impressive game
analysis scripts?

**Findings before revision**

1. The golden path was focused, but the novelty claim still sounded like a
   loose combination of LLM playtesting and an autonomous coding agent.
2. The plan did not explain what remains impossible if Codex is removed.
3. A successful accepted patch was treated as the main payoff; the safety and
   product value of rejecting an overfit patch were underdeveloped.
4. The UI named three screens but did not state design rules that help a judge
   understand evidence quickly or distinguish failure from success.
5. The impact section listed telemetry but did not define an experiment that
   could substantiate a time/effort claim.
6. The plan risked turning targets into marketing claims before the final
   campaign existed.

**Changes applied in this revision**

- Added a careful conceptual comparison across scripted bots, LLM playtest
  reports, general coding agents, and Playtest Forge.
- Defined the core invention as an intent-aware, evidence-gated repair
  experiment with holdout proof and first-class rejection.
- Added a “Why Codex is indispensable” boundary test.
- Added judge-visible interaction, uncertainty, accessibility, and evidence
  presentation principles.
- Added a minimum impact experiment, an independent clean-room task, and a
  claim ladder that prevents unsupported submission language.

**Pass 2 verdict**

Conditional pass. The idea is now focused and explainable in one sentence,
with meaningful differentiation and an honest impact-validation path. The
remaining risk is execution: without a real experiment record and a judge
path that works from a clean machine, the differentiation remains a design
claim rather than demonstrated product quality.

### Review Pass 3: Judge usability, compliance, and submission credibility

**Review question**

Can an unfamiliar judge verify the central claim quickly, without a GPU,
local model, repository rebuild, private knowledge, or trust in an edited
video—and does the submission satisfy every explicit developer-tool item?

**Findings before revision**

1. Requirements were listed near the start, but completion status and
   stop-ship evidence were distributed across the plan.
2. “One-command Judge Mode” was a promise without a precise clean-room command
   surface or time budget.
3. Supported platforms mixed targets with proven compatibility.
4. The plan did not explicitly protect against submitting a private repository
   without granting the two required judge accounts access.
5. The video, `/feedback` Session ID, public licensing, secret review, and
   no-rebuild path had no single blocking ledger.
6. The plan described strong engineering but lacked a final rubric connecting
   each official judging criterion to judge-visible proof.

**Changes applied in this revision**

- Added a target clean-room command contract with a no-key, no-GPU replay path
  and an optional backend-only OpenAI path.
- Added a five-minute mandatory judge journey and optional deeper checks.
- Separated platform targets from dated, digest-specific validation.
- Added a submission ledger with current status, evidence, and responsible
  phase, including the required private-repository access addresses.
- Added explicit security, licensing, artifact-traceability, video, repository,
  deadline, and `/feedback` stop-ship gates.
- Added a non-weighted shortlist scorecard mapping all four official criteria
  to concrete proof and current risk.

**Pass 3 verdict**

Plan-level pass. The proposed submission is focused, auditable, and aligned
with every published Build Week deliverable and judging criterion. It has a
credible shortlist shape if P0-P5 produce one real repair experiment and the
five-minute clean-room path. It should not be submitted as a finished product
if either proof is missing; those two artifacts are the difference between a
strong architecture proposal and a competition-ready developer tool.

### Review Pass 4: macOS delivery and unknown automated evaluation

**Review question**

Can the project be built completely on Apple Silicon macOS and still produce
useful, trustworthy results when an unknown AI evaluator receives only a
restricted repository checkout?

**Evidence boundary**

The published Build Week materials do not confirm an AI preselection stage or
specify its virtual environment. The deployment cannot depend on that theory.
The documented Codex cloud environment is used only as a conservative
compatibility reference: isolated checkout, networked setup, offline agent by
default, and no setup secrets during the agent phase.

**Findings before revision**

1. The plan correctly removed local vLLM from the judge-critical path, but the
   repository's current Compose file still defaults to an NVIDIA-only NVFP4
   service and makes the agent wait for it.
2. The selected Godot 4.4 container is `linux/amd64` only, so its use through
   Apple Silicon emulation would not justify a macOS support claim.
3. The current Mac has native Godot 4.7 and system Python 3.9, not the pinned
   Godot 4.4 and Python 3.10+ environment required by the plan.
4. The prior quickstart started with Docker, which may be unavailable inside a
   sandboxed or nested virtual environment.
5. A live OpenAI path may be impossible when network is disabled or secrets
   disappear before the test phase.
6. Human-oriented logs and fallback behavior were not precise enough for an
   automated grader to distinguish unsupported, failed, partial, and passed.

**Changes applied in this revision**

- Added a complete macOS contract using pinned Python 3.12, Node 20, native
  Godot 4.4, backend OpenAI calls, Replay default, and optional native
  vLLM-Metal.
- Required native multi-architecture API/dashboard/replay images and prohibited
  implicit `amd64` emulation as the Apple Silicon delivery strategy.
- Added Tier 0 Inspect and Tier 1 Replay commands that need no Docker, GPU,
  API key, port, browser, sibling checkout, or interactive approval.
- Added `AGENTS.md`, `JUDGE.md`, `judge-manifest.json`, setup, and root-command
  contracts so an AI can discover and interpret the test deterministically.
- Added JSON result fields, stable exit-code families, atomic output, strict
  timeout/signal cleanup, and a failure-response matrix.
- Added restricted-environment, macOS, ARM64 Docker, cross-platform artifact,
  and `openai/codex-universal` compatibility tests.
- Separated official competition facts from the unverified automated-review
  hypothesis throughout the plan.

**Pass 4 verdict**

Plan-level pass. The competition-critical system is fully implementable on
Apple Silicon macOS without making NVIDIA inference part of the promise. The
new deployment ladder is robust to a plausible AI preselection environment,
but the repository is not yet compliant: the root evaluator, portable bundle,
multi-architecture image, native Godot pin, and restricted-environment tests
still have to be implemented and evidenced before submission.
