# Playtest Forge

> A Codex-directed game QA agent that turns automated tests and persona
> playthroughs into bounded repair experiments—and rejects patches when fixed
> and unseen-holdout evidence does not support them.

[Open the public Judge experience](https://somazzz.github.io/game_analysis_agent/)
· [Watch the 2:55 demo](https://www.youtube.com/watch?v=62tW2RoFwTo)
· [Evaluator guide](JUDGE.md)
· [Developer guide](docs/DEVELOPER_GUIDE.md)
· [中文说明](README.zh-CN.md)

Playtest Forge is an OpenAI Build Week 2026 developer-tool submission. The
reference integration tests the embedded Godot demo **Study in Germany**, but
the workflow is designed around reusable contracts: typed gameplay steps,
swappable persona providers, immutable evidence, bounded source changes, and
machine plus human review.

![Playtest Forge Judge Mission showing the Campaign, Repair, and Proof ledger](docs/plans/openai_build_week_2026/product_design/audit-90s-2026-07-17/01-judge-start.png)

The central result is intentionally not a perfect game patch. Codex proposed
plausible changes, ran real-game fixed and unseen-holdout experiments, and
rejected both candidates because the player-level failure cluster did not
improve. Preventing an unsupported repair from shipping is the demonstrated
agent capability.

Before provisioning Docker or authorizing API usage, judges can verify the
committed project and Replay evidence without rebuilding anything:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

## Competition deployment: Docker Godot + OpenAI API

The primary full-fidelity Build Week deployment is deliberately hybrid:

```text
Host Codex + governed Judge API
        │
        ├── Docker Godot 4.4 sidecar
        ├── OpenAI Responses API (`gpt-5.6-luna`)
        └── local Vite Playthrough Inspector
```

Docker supplies the reproducible game runtime; OpenAI supplies live persona
decisions. Codex remains the host-side repair director, and the OpenAI key stays
in the server environment. The browser never receives it. The CPU-only
`dashboard` image is a judge/evidence surface—not a controller for the sibling
Godot container—so fresh campaigns use the host scripts below.

This is the recommended competition demo path on Linux `amd64` with Docker
Engine 24+ and Compose. Docker Desktop can provide the same interface on macOS,
but the Godot image may require `amd64` emulation; always require the wrapper to
report Godot 4.4 before spending API credit. Python 3.10+, `uv`, Node 20, Docker,
and an authorized server-side OpenAI API key are required.

### 1. Install and configure

```bash
cp .env.example .env

# Edit the ignored .env file. Never commit the key.
OPENAI_API_KEY=...
OPENAI_PERSONA_MODEL=gpt-5.6-luna
GODOT_DOCKER_MOUNT_ROOT=/absolute/path/to/parent/of/game_analysis_agent

# Locked Python/frontend install, public sample build, Inspect, and Replay.
scripts/setup-evaluator
```

The embedded, hash-inventoried game under `demo/study-in-germany` is the sample
data; no sibling/private game checkout is required.

### 2. Verify Docker Godot before any model call

```bash
docker version
docker compose --profile game-tools up -d godot

export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"
"$GODOT_BIN" --version
docker compose ps
```

Both Docker Client and Server must be available, the `godot` service must be
healthy, and the wrapper must report the Godot 4.4 family. An unavailable
selected runtime is `unsupported`; the workflow never silently switches to a
host Godot binary.

### 3. Start the viewer and governed API

Keep these in separate terminals from the repository root:

```bash
# Terminal 1: live-updating evidence viewer
npm --prefix frontend run prepare:public
npm --prefix frontend run dev -- --host 127.0.0.1
```

```bash
# Terminal 2: server-side API and campaign controls
GODOT_BIN="$PWD/scripts/godot-docker-wrapper" \
  scripts/run-judge-dev --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:5173/#/playthrough-inspector` and refresh after the API
connects. Provider readiness checks inspect configuration and health without
printing the key or making a model call.

### 4. Run the bounded OpenAI smoke campaign

Start with the one-persona profile before authorizing a larger cohort:

```bash
.agents/skills/playtest-forge/scripts/session-options \
  --godot-runtime docker-godot \
  --llm-provider openai-api \
  --profile one-strategy \
  --persona newbie \
  --json
```

After reviewing the emitted limits and approving API usage, run its frozen
command:

```bash
GODOT_BIN="$PWD/scripts/godot-docker-wrapper" \
PERSONA_MAX_RUNS=1 \
PERSONA_MAX_WEEKS=20 \
PERSONA_MAX_CONCURRENCY=1 \
PERSONA_MAX_CALLS=50 \
  scripts/run-persona-campaign openai \
    --persona newbie --seed 42 --max-weeks 20 --concurrency 1 --no-resume
```

This profile permits at most 40 decision/event calls under a 50-call operational
cap. It validates the live provider, real Godot steps, evidence retention, and
weekly UI, but it cannot select or prove a repair. The six-persona and
three-seed profiles are offered only after this path succeeds.

Every live run is fail-closed: partial cells, provider errors, runtime errors,
or fallback weeks reject the campaign. `session.json` is progress telemetry;
only a `completed` campaign whose public bundle and gates verify is citable
evidence. Raw cells remain under `reports/persona-campaigns/`, while only the
sanitized view is published to `frontend/public/live-playthrough/`.

This deployment supports the Build Week Developer Tools requirements for clear
installation, supported platforms, sample data, and a runnable test path. The
public demo and offline evaluator below remain the no-secret, no-rebuild judge
path required when Docker or an API key is unavailable. See the
[official rules](https://openai.devpost.com/rules) and
[Build Week FAQ](https://openai.devpost.com/details/faqs).

## Evaluate in 60 seconds

From the repository root:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

Expected results:

- **Inspect:** `passed`; every artifact and public claim listed in the committed
  Judge manifest is hash/schema verified.
- **Replay:** `passed`; campaign, exact persona Replay, deterministic fixture,
  designed-failure, and rejected-repair gates rechecked.

Inspect needs Python 3.9+ only. Replay additionally uses `uv` and the committed
lockfile. Neither path needs Godot, Docker, a GPU, network, an API key, a
browser, an open port, or a sibling game checkout. `failed` and `unsupported`
are non-success states; the evaluator does not convert missing capabilities
into passes.

## What judges can inspect

The Judge page uses one evidence model for machine evaluation and Human Review.
Its static selector exposes intentionally curated records with explicit
lifecycle labels:

| Evidence set | Observation source | Proof | Decision |
| --- | --- | --- | --- |
| Signed reference | Prerecorded deterministic Replay over committed real-Godot-derived evidence | Fixed and unseen-holdout rejection proof | **Rejected** |
| OpenAI six-persona campaign | Live `gpt-5.6-luna`, real Godot 4.4, seed 42, 20-week cap | Campaign gate and per-persona replay; repair proof has not run | **Campaign only** |
| Bilingual choice identity | Deterministic Godot 4.4, zero model calls | Fixed 42/43/44 and holdout 1042/1043/1044 semantic preservation | **Accepted** |

Raw local-vLLM A/B campaigns are development evidence, not submission assets.
They are excluded from the static experiment index, public frontend bundle, and
Git tracking. Fresh local or OpenAI campaigns can still appear dynamically when
the localhost Judge API is running, with their exact provider labels.

## Explore the evidence

The static frontend is a no-key, no-rebuild evaluator surface:

- `/#/` — Campaign → Repair → Proof → Human Review Judge ledger.
- `/#/playthrough-inspector` — signed strategy, seed, week, state, action,
  event, and provenance review.
- `/#/reports` — report and issue archive.

The exact signed patch diff, fixed and holdout cohorts, evidence fingerprint,
machine recommendation, and `candidate_not_merged` disposition remain visible.
The accepted bilingual correctness record exposes its exact diff and hash-bound
deterministic proof without depending on private local-model traces.

Human Review does not create a second evidence system. A reviewer can inspect
the complete evidence and diff, see the machine recommendation, choose
Approve / Reject / Needs more evidence, add a note, and export
`human_review.json`. It never merges automatically. Static hosting is read-only;
durable review records require the Judge API.

## Internal local-model evidence

The local-vLLM A/B runs remain useful internal diagnosis: they confirmed the
pressure/burnout observation and rejected two ineffective bounded candidates.
Only their concise review report is retained for project history; raw campaign,
repair, and playthrough logs stay operator-local and are not published in the
frontend.

See the [A/B proof closeout](docs/reviews/openai_build_week_2026/LOCAL_VLLM_AB_REPAIR_PROOF_2026-07-17.md)
for the summarized hypotheses and gate outcomes.

## How Codex, GPT-5.6, and humans are used

### Codex

Codex is the repair director. It loads the repository Skill, freezes the test
contract before source inspection, cites campaign facts, selects one mechanism,
creates an isolated game worktree, makes an allowlisted candidate change, runs
focused plus fixed/holdout proof, and writes the machine recommendation.

Codex officially supports repository Skills under `.agents/skills` and loads a
selected Skill through progressive disclosure; see the [official Codex Skills
guide](https://learn.chatgpt.com/docs/build-skills). Launch Codex from this repository
root, then explicitly invoke the checked-in workflow:

```text
Use $playtest-forge to review the committed automated and persona-playthrough
evidence, explain the rejected candidate, and propose the next bounded experiment.
```

Repository guidance in [AGENTS.md](AGENTS.md) requires the two offline Judge
commands first and routes game testing, diagnosis, balance, and repair work to
[`playtest-forge`](.agents/skills/playtest-forge/SKILL.md). If a non-Codex
evaluator does not expose Skills, it can read the tracked, hash-verified
`SKILL.md` directly.

### GPT-5.6

GPT-5.6 is implemented as the optional live Persona action provider. It shares
the same typed campaign service, real-Godot step contract, frozen profile,
limits, progress records, public bundle, frontend view, and evidence gates as
local vLLM. Credentials remain server-side.

The retained live campaign used OpenAI `gpt-5.6-luna` with real Godot 4.4:
all six personas at seed 42 completed, producing 114 gameplay records and 228
sanitized provider-call records with 100% valid decisions, 0% fallback, and 0%
provider errors. Its public bundle passed provenance, schema, hash, and privacy
gates. The static Judge and Playthrough Inspector expose this record as
**CAMPAIGN ONLY** because no patch, fixed cohort, unseen holdout, or repair
decision was produced from it.

### Humans

Humans choose scope, provider, frozen profile, and whether a machine
recommendation should be approved. They can request more evidence and leave a
durable note, but they cannot mutate the underlying experiment through the
review interface. Game patches are never auto-merged.

## System shape

```text
Codex + playtest-forge
        │ freezes scope, evidence contract, gates, and change budget
        ▼
Typed campaign / gameplay services
        │
        ├── deterministic Replay
        ├── local vLLM / SGLang
        └── live OpenAI / DeepSeek
        │
        ▼
Real Godot probe → raw cells → sanitized public bundle
        │
        ▼
Failure clusters → one bounded candidate → fixed + unseen proof
        │
        ▼
Machine recommendation → Judge UI → Human Review
```

The CLI, future MCP adapter, Judge API, and Skill are not allowed to duplicate
gameplay logic. Transport-independent services remain the architectural source
of truth. MCP is not required for the Build Week delivery.

## Run the evaluator UI

### Static, read-only mode

```bash
cd frontend
npm ci
npm run prepare:public
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Static mode exposes the curated signed,
deterministic, and sanitized live-OpenAI records; it cannot run providers or
persist Human Review. Private local-model logs and private OpenAI traces are not
copied into this build.

Build the GitHub Pages artifact with:

```bash
cd frontend
npm ci
npm run build:public
```

The output is `frontend/dist/`. Pushes to `main` or
`OpenAI-build-week-2026` trigger the Pages workflow; until deployment completes,
the repository evidence and local build are the source of truth.

### Judge API mode

```bash
cd frontend && npm run build:public && cd ..
uv run python tools/run_judge_api.py \
  --host 127.0.0.1 \
  --port 8080 \
  --frontend frontend/dist
```

Open `http://127.0.0.1:8080/`. This mode enables the same experiment registry,
durable Human Review, and bounded provider readiness actions. API keys are read
only by the server process and are never entered in the browser.

### Docker evaluator

```bash
docker compose up -d dashboard
docker compose --profile judge run --rm replay
```

The Judge image runs unprivileged. Offline Replay has no network and a read-only
root filesystem. The evaluator image contains only curated signed and
deterministic static evidence; private local-model logs are excluded. No new
immutable multi-architecture digest is claimed until the final image is
published. This CPU-only evaluator is intentionally separate from the primary
Docker-Godot + OpenAI campaign deployment above and cannot launch the Godot
sidecar by itself.

## Start a Codex-guided playtest

Do not begin with an API call. From the repository root:

```bash
.agents/skills/playtest-forge/scripts/preflight
.agents/skills/playtest-forge/scripts/session-options --choices-only --json
```

Codex then stages committed evidence and starts the read-only viewer before
asking either question:

```bash
npm --prefix frontend run prepare:public
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/#/playthrough-inspector`. At this point Vite has not
started Judge API, selected Godot, or called a model; it only shows retained
public evidence.

Codex next asks two required questions:

1. Godot runtime: local Godot 4.4 or the Docker Godot wrapper.
2. LLM: OpenAI API, local vLLM, or no LLM.

No LLM means deterministic automation plus committed Replay, with zero model
calls and no new persona evidence. For a model-backed run, Codex then offers
three frozen 20-week profiles:

| Profile | Matrix | Worst-case calls | What it proves |
| --- | ---: | ---: | --- |
| `one-strategy` | chosen persona × seed 42 | 40 | Provider, agent, Godot, retention, weekly UI |
| `six-strategy` | six personas × seed 42 | 240 | Same-seed persona divergence |
| `repair-evidence` | six personas × seeds 42/43/44 | 720 | Evidence adequate to select one repair target |

The user confirms Godot and LLM before choosing a profile and—when
applicable—persona. Local and API providers execute through the same service. A
one-strategy or one-seed run can validate the agent but cannot prove a repair.

The Vite viewer remains running while choices are made. After Godot, LLM,
profile, and any required persona are frozen, start the governed API in a
second terminal with the selected runtime:

```bash
# Local Godot
GODOT_BIN=/resolved/godot4 \
  scripts/run-judge-dev --host 127.0.0.1 --port 8080

# Docker Godot
GODOT_BIN="$PWD/scripts/godot-docker-wrapper" \
  scripts/run-judge-dev --host 127.0.0.1 --port 8080
```

Refresh the already-open inspector after the API connects. Codex executes the
exact command emitted by `session-options`, monitors weekly progress, verifies
the completed public bundle and frontend view, and does not edit the game or
spend API credit without explicit approval.

For real-game authoring without a host Godot binary, use the repository Docker
wrapper described in the [Developer Guide](docs/DEVELOPER_GUIDE.md) and
[Docker Guide](docs/operations/DOCKER.md).

## Supported delivery paths

| Path | Requirements | Model/key required |
| --- | --- | --- |
| GitHub Pages | Current desktop/mobile browser | No |
| `judge --mode inspect` | Python 3.9+ | No |
| `judge --mode replay` | Linux/macOS + locked `uv` environment | No |
| Judge dashboard/container | Docker Engine 24+; linux/amd64 or linux/arm64 | No |
| **Competition live path** | **Host Codex + Linux amd64 Docker Godot 4.4 + Python 3.10+/Node 20** | **Server-side OpenAI key; `gpt-5.6-luna`** |
| Real-game authoring | Host Codex + Godot 4.4 or Docker wrapper | No model for automation |
| Local persona campaign | Host Codex + Godot + local vLLM/SGLang | Local model |
| OpenAI persona campaign | Host Codex + Godot runtime | Server-side API key |

The competition delivery is deliberately hybrid: Codex runs on the host while
Docker can supply Godot and local-vLLM sidecars. The Judge image is an evaluator
surface, not an all-in-one autonomous repair container, and it never receives a
Docker socket.

## Verification

```bash
uv run ruff check .
uv run pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build:public
```

Latest local closeout on 2026-07-18:

- Python: 511 passed, 1 declared environment skip; Ruff passed.
- Frontend: 28 passed; the production Pages build completed.
- Judge Inspect: 206 hash/schema artifacts and 9 exact claims passed; Replay
  passed.
- The current local linux/amd64 Judge image passed no-network, read-only,
  drop-all-capabilities Inspect/Replay and read-only Dashboard/API checks.
- Private local-vLLM A/B logs, OpenAI session files, prompts, and model response
  bodies are excluded from Git and the static frontend.

## Build Week scope

Build Week work added the governed Codex Skill, shared persona-provider
contract, real-Godot campaign services, frozen repair protocol, signed evaluator,
embedded demo, experiment registry, scalable persona/seed replay, exact patch
evidence, Human Review layer, static Judge experience, and restricted Docker
delivery.

The project existed before Build Week. The exact prior-versus-new boundary is
documented in
[`PRIOR_VS_BUILD_WEEK.md`](submission/build-week-2026/PRIOR_VS_BUILD_WEEK.md).
The project is MIT licensed; third-party and generated-asset provenance is in
[ATTRIBUTION.md](ATTRIBUTION.md).

## Current limitations and submission status

- Local A/B candidates were rejected and not merged. Their raw logs remain
  operator-local; only summarized findings are retained in documentation. This
  is not a claim that the demo's pressure/cashflow balance is fixed.
- The retained OpenAI campaign is observation evidence, not completed repair
  proof; no OpenAI-derived game patch is accepted or merged.
- The public [2:55 demo video](https://www.youtube.com/watch?v=62tW2RoFwTo) is
  published. Final Devpost team checks, non-builder manual/clean-room review,
  and any claim of a newly published current-revision image remain owner/release
  actions. `/feedback/` exports are submission metadata only and remain
  intentionally ignored by Git.
- The embedded Study in Germany project is a competition demo, not a complete
  commercial game.
- Live persona work requires a compatible model endpoint; real gameplay still
  requires Godot 4.4 or the Docker wrapper.
- Full campaign authoring is a host-Codex plus runtime-sidecar workflow, not an
  all-container path.

See the
[submission compliance audit](docs/reviews/openai_build_week_2026/SUBMISSION_COMPLIANCE_AUDIT_2026-07-17.md)
for the fail-closed checklist based on the
[official Build Week rules](https://openai.devpost.com/rules) and
[event page](https://openai.com/build-week/).

## Repository map

```text
.agents/skills/playtest-forge/    Reusable Codex workflow and references
config/                           Frozen profiles, targets, gates, contracts
demo/study-in-germany/            Embedded, pinned Godot baseline
examples/build_week_2026/         Sanitized signed campaign and repair evidence
frontend/                         Judge, Playthrough Inspector, reports, review UI
game-overlays/                    Audited runtime-only demo probe overlays
src/game_analysis_agent/          Typed services, providers, analysis, registry
tools/ and scripts/               CLI adapters, evaluators, Docker/Godot helpers
docs/                             Architecture, operations, reviews, developer guide
judge + judge-manifest.json       Offline evaluator and signed table of contents
```

## Documentation

- [Evaluator guide](JUDGE.md)
- [Complete developer guide](docs/DEVELOPER_GUIDE.md)
- [Build Week reviewer hub](docs/plans/openai_build_week_2026/README.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Docker and local-vLLM delivery](docs/operations/DOCKER.md)
- [Service-first MCP migration plan](docs/architecture/MCP_MIGRATION_PLAN.md)
- [Review index](docs/reviews/README.md)
- [Chinese README](README.zh-CN.md)
