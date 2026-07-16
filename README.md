# game_analysis_agent

## Judge / automated evaluator quickstart

The primary review path is repository-only and offline:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

Inspect needs only Python 3.9+ and validates 22 committed artifact hashes,
schemas, provenance gates, and six exact public claim references. Replay adds
the locked `uv` environment and consumes hash-pinned persona fixtures; it does
not need Godot, Docker, a GPU, network, an API key, a browser, or the private
game checkout. Both commands print one `judge-result-v1` JSON object. Expected
status is `passed`; `failed` and `unsupported` are never fallback successes.

The committed case is explicitly **prerecorded Replay evidence**: Codex formed
and implemented a bounded repair hypothesis, then rejected the candidate after
fixed and holdout cohorts both failed to improve the target cluster. It is not
presented as a fresh OpenAI call or a successful game fix. See [JUDGE.md](JUDGE.md)
for the evidence map, commands, exit codes, and limitations.

Development-side AI agent pipeline for simulation games. The current reference
integration is the Godot `study-in-germany` demo, but the project is structured
as a reusable game QA agent framework for balance testing, boundary probing,
bug discovery, value analysis, quality gates, and interactive LLM playtesting.

## Live Demo

**Open the public dashboard:**  
**[https://somazzz.github.io/game_analysis_agent/](https://somazzz.github.io/game_analysis_agent/)**

The GitHub Pages demo uses sanitized report data, so reviewers can inspect the
dashboard and decision-graph experience without running Godot, local LLMs, or
private game assets.

The agent is not embedded in the game runtime as an NPC. Instead, it runs beside
the game as a QA and design-review system:

```text
Godot headless game runners
  ├─ Monte Carlo simulation
  ├─ boundary/extreme-state probes
  ├─ event/action/ending graph export
  └─ interactive probe driven by an LLM player
        │
        ▼
Python analysis layer
  ├─ ending, weekly metric, action, event, and choice statistics
  ├─ anomaly and invariant detection
  ├─ value/playability analysis
  ├─ quality gates
  └─ traceable report manifests
        │
        ▼
LLM agent layer
  ├─ balance
  ├─ content_qa
  ├─ event_graph
  ├─ bug_hunter
  ├─ boundary_prober
  ├─ value_reviewer
  └─ interactive_player
        │
        ▼
Reports and dashboard
  ├─ Markdown / JSON / CSV reports
  ├─ report_manifest.json + reports/report_index.json
  ├─ static HTML dashboard
  └─ React + React Flow dashboard
```

The default local LLM backend is an OpenAI-compatible vLLM server. The Docker
Compose stack is configured for NVIDIA's Qwen3.6 27B NVFP4 checkpoint with
ModelOpt quantization, Qwen3 reasoning parsing, and optional MTP speculative
decoding. You can also point the client at SGLang or DeepSeek-compatible
endpoints.

中文说明保留在 [README.zh-CN.md](README.zh-CN.md).

## Current Status

- Python package: `game-analysis-agent` (`pyproject.toml` version `0.2.0`).
- Main orchestration CLI: `tools/run_gameplay_agent.py`.
- Analysis agents: `balance`, `content_qa`, `event_graph`, `bug_hunter`,
  `boundary_prober`, `value_reviewer`, and `interactive_player`.
- Supported orchestration subcommands: `sim`, `analyze`, `probe`, `export`,
  `validate`, `matrix`, `compare-matrix`, `index`, `gates`, `eval`, `qa`,
  `play`, and `all`.
- Report outputs are designed to be traceable through `run_id`,
  `report_manifest.json`, and `reports/report_index.json`.
- Frontend dashboard tests use Vitest, jsdom, and Testing Library; production
  builds use Vite.
- Python tests use pytest and the whole repository is checked by Ruff.

## Requirements

For the full end-to-end workflow:

- Python 3.10 or newer.
- `uv` or a standard virtualenv/pip setup.
- Godot 4 headless CLI (`godot4`) for real game runs.
- A checkout of the target game project, for example:
  `/home/bo/projects/python/study-in-germany`.
- One LLM endpoint:
  - local vLLM,
  - local SGLang,
  - or DeepSeek-compatible cloud endpoint.

The pure Python analyzers and tests can run without Godot or a live LLM.

## Quick Start A: No Godot, No LLM

Use this path to inspect the project shape, run tests, and build a dashboard
from committed sample reports.

```bash
cp .env.example .env
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
uv run pytest -q -ra
uv run ruff check .
uv run python tools/build_dashboard.py all --reports examples/sample_reports
```

Open:

```text
examples/sample_reports/index.html
```

The richer React demo dataset lives under `frontend/public-demo/` and is safe to
show publicly because private raw runs, complete event graphs, and gameplay text
are withheld.

## Quick Start B: With Local LLM

Edit `.env` for an OpenAI-compatible local endpoint:

```bash
LLM_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=local-dev-token
LLM_MODEL=nvidia/Qwen3.6-27B-NVFP4
LLM_SERVED_MODEL_NAME=qwen3.6-27b-nvfp4
```

Run LLM review agents against a report directory:

```bash
uv run python tools/run_gameplay_agent.py qa \
  --report-dir examples/sample_reports/balance/sample_balance_report
```

Or run only one agent:

```bash
uv run python tools/run_agent.py balance \
  examples/sample_reports/balance/sample_balance_report
```

## Quick Start C: Full Godot Integration

Set the target game project and Godot CLI:

```bash
GAME_PROJECT_PATH=/path/to/study-in-germany
GODOT_BIN=godot4
```

Run the main CLI help:

```bash
uv run python tools/run_gameplay_agent.py --help
```

Run the simple end-to-end path:

```bash
uv run python tools/run_gameplay_agent.py all --runs 20 --policy balanced
```

`all` runs simulation/analysis, catalog export, all Godot validators, the LLM
QA agents, and quality gates in that order. Use `--skip-qa` when a live model
endpoint is unavailable; deterministic validation and gates still run.

## Quick Start: Docker + vLLM

Start the local vLLM service and persistent Godot sidecar:

```bash
cp .env.example .env
# Edit .env: HF_TOKEN, GAME_PROJECT_PATH, CUDA_VISIBLE_DEVICES, etc.
docker compose pull vllm
docker compose up -d vllm godot
docker compose logs -f vllm
docker compose ps
```

Wait until both services are healthy. Run gameplay commands from the host so
the repository wrapper can execute Godot inside the sidecar:

```bash
uv run python tools/run_gameplay_agent.py play \
  --report-dir reports/play/local-smoke \
  --persona newbie --weeks 5 --seed 42
```

The opt-in `agent` container is for pure-Python analysis and QA of existing
reports. It intentionally cannot execute commands in the Godot sidecar.

See [docs/operations/DOCKER.md](docs/operations/DOCKER.md) and
[docs/operations/VLLM_QWEN_LOCAL_AGENT.md](docs/operations/VLLM_QWEN_LOCAL_AGENT.md) for deployment
details.

For the future MCP surface, follow the
[service-first MCP migration plan](docs/architecture/MCP_MIGRATION_PLAN.md). The existing
CLI must be refactored onto typed services before any MCP wrapper is added.

## Common Workflows

Run Monte Carlo simulation through the Godot project:

```bash
uv run python tools/run_gameplay_agent.py sim --runs 100 --policy balanced
```

Analyze an existing `raw_runs.jsonl` report directory:

```bash
uv run python tools/run_gameplay_agent.py analyze \
  --report-dir reports/balance/<run_id>
```

Run boundary probes:

```bash
uv run python tools/run_gameplay_agent.py probe \
  --extreme "zero_money,deep_debt,flag_chaos"
```

Export the game event/action/ending catalog:

```bash
uv run python tools/run_gameplay_agent.py export
```

Run all six Godot validators (`content`, `json-content`, `economy`, `risk`,
`route`, and `demo`):

```bash
uv run python tools/run_gameplay_agent.py validate \
  --report-dir reports/validation/<run_id>
```

Route and demo prerequisite traces are generated fresh by default. Existing
inputs are reused only with the explicit `--reuse-inputs` option. Use repeated
`--check` options to select a subset.

Evaluate quality gates:

```bash
uv run python tools/run_gameplay_agent.py gates \
  --report-dir reports/balance/<run_id>
```

Run LLM QA agents for a report:

```bash
uv run python tools/run_gameplay_agent.py qa \
  --report-dir reports/balance/<run_id>
```

Run only one LLM agent:

```bash
uv run python tools/run_agent.py balance reports/balance/<run_id>
```

Drive the game with the interactive LLM player:

```bash
uv run python tools/run_gameplay_agent.py play \
  --report-dir reports/play/<run_id> --weeks 20
```

Evaluate an already recorded playthrough without contacting Godot or an LLM:

```bash
uv run python tools/run_gameplay_agent.py eval \
  --report-dir reports/play/<run_id>
```

This writes `agent_eval.json` with decision validity, fallback/repair, illegal
action, event-choice, anomaly, risk acknowledgement, persona alignment, and LLM
error/latency metrics. Weekly prompts prefer the producer-native
`RiskEvaluator.get_top_risks` payload; missing, malformed, or stale guidance
uses a compatibility fallback whose source and reason remain in the trace.

Capture the producer-native interactive snapshot without an LLM:

```bash
uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/<run_id>
```

This command fails if the game omits the versioned
`RiskEvaluator.get_top_risks` guidance.

Plan or execute the strict test matrix:

```bash
# Validate and enumerate the plan without running its cells.
uv run python tools/run_gameplay_agent.py matrix --dry-run --jobs 4

# Execute cells concurrently; a later invocation can resume completed cells.
uv run python tools/run_gameplay_agent.py matrix --jobs 4
uv run python tools/run_gameplay_agent.py matrix --jobs 4 --resume
```

The committed `config/matrix.yaml` expands to 140 stable cells: 126 simulation
cells (difficulty x policy x scenario x seed), 8 boundary cells, and 6 persona
play cells. Matrix state is written atomically to `matrix_manifest.json`,
`matrix_summary.json`, and per-cell `cell_manifest.json` files. The strict YAML
schema rejects unknown or invalid keys before any cell runs.
Every matrix and cell manifest also records an exact runtime-source SHA-256;
`--resume` reruns prior successes whenever executable Agent bytes changed.

Run and compare a fixed-seed before/after experiment. Each `--out` directory
owns isolated cell report directories, so the second execution cannot overwrite
the first:

```bash
uv run python tools/run_gameplay_agent.py matrix \
  --out reports/matrix/before --jobs 4

# Apply the code change under test; keep config/matrix.yaml unchanged.
uv run python tools/run_gameplay_agent.py matrix \
  --out reports/matrix/after --jobs 4

uv run python tools/run_gameplay_agent.py compare-matrix \
  --before reports/matrix/before \
  --after reports/matrix/after \
  --out reports/compare/matrix
```

`compare-matrix` fails closed unless both executions are complete, non-dry-run,
and matching in config hash, cell set, parameters, commands, and seeds. It
independently revalidates simulation, boundary, and persona evidence, including
CSV schemas, coverage/catalog consistency, trace contracts, report source
fingerprints, and recomputed Agent metrics. Artifact content may differ and is
exactly what the per-cell diff and `matrix_compare_summary.json` record.

Build the report index:

```bash
uv run python tools/run_gameplay_agent.py index
```

Run the simple end-to-end path:

```bash
uv run python tools/run_gameplay_agent.py all --runs 20 --policy balanced
```

## Adapting to Another Game

The reference game is `study-in-germany`, but the expected integration surface
is intentionally small:

1. Export the game's actions, events, endings, and state metrics.
2. Implement a headless simulation command for repeatable runs.
3. Emit `raw_runs.jsonl` with weekly state, actions, events, choices, and final
   ending.
4. Configure `config/gates.yaml` for project-specific quality thresholds.
5. Run the Python analyzers and LLM review agents.
6. Build the static or React dashboard for reviewers.

## Reports and Traceability

Report directories live under `reports/`, usually grouped by kind:

```text
reports/
  balance/<run_id>/
  boundary/<run_id>/
  play/<run_id>/
  browse/
  index.html
  manifest.json
  report_index.json
```

Typical balance report files include:

```text
raw_runs.jsonl
summary.json
ending_distribution.csv
weekly_stats.csv
action_pick_rates.csv
event_trigger_rates.csv
choice_pick_rates.csv
anomalies.jsonl
bugs.jsonl
bugs_summary.md
value_report.json
route_report.json
coverage_report.json
gate_report.json
agent_diagnosis.md
tuning_proposal.md
content_issues.md
event_graph_report.md
bug_diagnosis.md
boundary_report.md
value_review.md
report_manifest.json
```

Interactive playtest reports also include:

```text
playthrough.jsonl
playthrough_summary.md
playthrough_agent_report.json
agent_eval.json
report_manifest.json
```

The `trace-manifest-v2` `report_manifest.json` records the report-level
`run_id`, command parameters, source/generated files, hashes, modification
times, and trace indexes back to JSONL line numbers. Its provenance block also
captures the agent and game Git commits/dirty state, Python/platform/Godot
versions or availability, an exact runtime-source SHA-256 that distinguishes
different dirty worktrees, and config/prompt tree hashes. Frontends should use
`reports/report_index.json` for list views and open each report's manifest for
drill-down.

## Test System

If the host has no `godot4` binary, use the cached Docker image through the
repository wrapper. It preserves absolute host paths and runs as the current
user, so reports are not root-owned:

```bash
export GAME_PROJECT_PATH=/home/bo/projects/python/study-in-germany
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"
docker compose up -d godot vllm
"$GODOT_BIN" --version

uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/docker-smoke
```

The wrapper reuses the compose `godot` service and falls back to a one-shot
container when the service is not running. The default image is
`barichello/godot-ci:4.4`; override it with `GODOT_DOCKER_IMAGE`. See
[AGENTS.md](AGENTS.md) for mount and CI-integrity details.

### Real local-LLM agent testing

The most direct end-to-end test lets the local LLM choose actions while the
real Godot project advances. First verify the producer-native game contract
without contacting the model:

```bash
docker compose up -d vllm godot
docker compose ps

uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/local-smoke
```

Then run a short LLM smoke test and independently evaluate the recorded
evidence:

```bash
uv run python tools/run_gameplay_agent.py play \
  --report-dir reports/play/local-newbie-smoke \
  --persona newbie \
  --difficulty normal \
  --scenario default_first_semester \
  --seed 42 \
  --weeks 5

uv run python tools/run_gameplay_agent.py eval \
  --report-dir reports/play/local-newbie-smoke

uv run python -m json.tool \
  reports/play/local-newbie-smoke/agent_eval.json
```

For a release-sized playthrough, change `--weeks` to `20`. Available
personas are `newbie`, `study`, `money`, `social`, `visa`, and
`slacker`. A clean result has `valid: true`, `strict_passed: true`, empty
`errors` and `quality_errors` lists,
`final_valid_rate >= 0.95`, `fallback_rate <= 0.05`,
`illegal_action_rate == 0`, `llm_error_rate <= 0.05`, and
`anomaly_rate_per_5_weeks <= 1`. Also review `persona_alignment_rate` and
`risk_acknowledgement_rate`; they measure behavioral quality rather than
basic trace validity.

To make the review agents inspect fresh real-game data, build the evidence in
one directory and then run `qa`:

```bash
REPORT=reports/balance/local-real-42

uv run python tools/run_gameplay_agent.py sim \
  --report-dir "$REPORT" --runs 200 --weeks 20 \
  --policy balanced --difficulty normal --seed 42
uv run python tools/run_gameplay_agent.py export --report-dir "$REPORT"
uv run python tools/run_gameplay_agent.py probe \
  --report-dir "$REPORT" --runs 30 --weeks 20 \
  --policy balanced --seed 42 \
  --extreme "zero_money,deep_debt,no_energy,flag_chaos"
uv run python tools/run_gameplay_agent.py qa --report-dir "$REPORT"
uv run python tools/run_gameplay_agent.py gates --report-dir "$REPORT"
```

`play` writes `playthrough.jsonl`, `playthrough_summary.md`,
`playthrough_agent_report.json`, `agent_eval.json`, and
`report_manifest.json`. Run `eval` even though `play` already writes the
evaluation: the separate command gives invalid recorded evidence a non-zero
exit status. The current game demo has three known balance failures, so the
monolithic `all` command can correctly stop at validation before model QA;
the modular sequence above keeps those stages independently inspectable.

Run the deterministic local checks from the repository root:

```bash
uv sync --extra dev --locked
uv run pytest -q -ra
uv run ruff check .

cd frontend
npm ci
npm test
npm run test:coverage
npm run build
```

Pull requests and pushes run the Python suite, full-repository Ruff, frontend
coverage floors, the public production build, and a strict dry-run of all 140
matrix cells. The scheduled/manual real-Godot job checks out a pinned private
`study-in-germany` revision, verifies the official Godot archive checksum,
generates and analyzes a fresh trace, runs all six validators with fresh
prerequisites, enforces deterministic smoke gates, validates the cross-repo
contracts, captures canonical interactive risk guidance, and uploads the
evidence. See [Game artifact contract
testing](docs/operations/GAME_CONTRACT_TESTING.md).

## Dashboards

Build the static HTML dashboard and frontend manifests:

```bash
uv run python tools/build_dashboard.py all
```

Build it from the committed sample reports:

```bash
uv run python tools/build_dashboard.py all --reports examples/sample_reports
```

This writes:

```text
reports/index.html
reports/browse/<kind>/<id>/index.html
reports/browse/decision_graph/<issue_id>/<run_id>/index.html
reports/manifest.json
reports/browse/<kind>/<id>/manifest.json
reports/browse/decision_graph/<issue_id>/<run_id>/manifest.json
```

Render one decision graph:

```bash
uv run python tools/build_dashboard.py decision-graph \
  --report-dir reports/balance/<run_id> --run-id 0
```

Use the React + React Flow dashboard:

```bash
uv run python tools/build_dashboard.py emit-frontend-manifest \
  --reports reports --frontend-public frontend/public

cd frontend
npm ci
npm test
npm run test:coverage
npm run dev
npm run build
```

Development server:

```text
http://localhost:5173
```

Production build output:

```text
frontend/dist/
```

## Project Layout

```text
config/
  agent_profiles.yaml       Agent prompt/profile definitions
  gates.yaml                Quality gate thresholds
  matrix.yaml               Executable strict scenario/persona test matrix
  player_personas.yaml      Interactive player personas

docs/
  README.md                   Audience-keyed index — start here
  architecture/               Developer + reviewer reference (evergreen)
  operations/                 Docker + vLLM + contract test plans
  portfolio/                  Public / portfolio summary
  reviews/                    Date-sorted audits and gap analyses
  plans/                      WIP designs and design iterations
  legacy/                     Superseded docs (not linked from README)
  assets/                     Preview images and PDFs

examples/
  sample_reports/           Tiny sanitized reports for dashboard demos

frontend/
  React + Vite dashboard with React Flow decision graphs

prompts/
  System and user prompts for each LLM agent

scripts/tools/
  Godot helper scripts and lightweight validation/probe utilities

src/game_analysis_agent/
  analytics.py
  agent_eval.py
  anomaly_detector.py
  anomaly_semantics.py
  bug_summarizer.py
  contracts.py
  coverage.py
  env.py
  game_tools.py
  llm_client.py
  quality_gates.py
  report_bundle.py
  report_manifest.py
  schemas.py
  settings.py
  test_matrix.py
  tool_loop.py
  value_analyzer.py
  agents/

tools/
  analyze_balance.py
  build_dashboard.py
  compare_matrix.py
  compare_reports.py
  emit_manifest.py
  generate_agent_prompt.py
  run_agent.py
  run_balance_sim.sh
  run_gameplay_agent.py
  run_vllm_qwen.sh

tests/
  Unit tests and smoke tests
```

## Documentation

Start at [docs/README.md](docs/README.md) — audience-keyed index.

Selected entry points:

- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Data Contracts](docs/architecture/DATA_CONTRACTS.md)
- [Gameplay Agent](docs/architecture/GAMEPLAY_AGENT.md)
- [Godot Integration](docs/architecture/GODOT_INTEGRATION.md)
- [Integration with study-in-germany](docs/architecture/INTEGRATION_WITH_STUDY_IN_GERMANY.md)
- [Service-first MCP Migration Plan](docs/architecture/MCP_MIGRATION_PLAN.md)
- [Docker Deployment](docs/operations/DOCKER.md)
- [Local vLLM + Qwen](docs/operations/VLLM_QWEN_LOCAL_AGENT.md)
- [Game artifact contract testing](docs/operations/GAME_CONTRACT_TESTING.md)
- [Portfolio Notes](docs/portfolio/PORTFOLIO.md)
- [Local LLM Real-Game Audit (2026-07-13)](docs/reviews/LOCAL_LLM_GAME_SYSTEM_AUDIT_20260713.md)
- [Interactive Playtest Plan](docs/plans/interactive_playtest/README.md)
- [Review Documents](docs/reviews/README.md)

## Current Limitations

The deterministic Python/frontend suites do not need Godot or an LLM. Real
simulation, validators, and live interactive play still require a compatible
Godot 4 binary and a `study-in-germany` checkout exposing the expected scripts
and contracts; live persona evaluation additionally requires an LLM endpoint.
The reference game repository is private, so scheduled CI also requires the
`STUDY_IN_GERMANY_TOKEN` secret. This development machine can run the real
Godot and local-vLLM tier through Docker; other environments may be limited to
fixtures and orchestration when those prerequisites are unavailable.

## Notes

- Success is not the only valid game outcome. Designed failure, recovery, and
  mixed endings are part of the review standard, and the test matrix reflects
  that.
- The default vLLM context length is configured by `LLM_MAX_MODEL_LEN`
  (`32768` by default). Do not reduce it only to make tests faster if the goal
  is realistic LLM playtesting.
- Generated reports, frontend build output, caches, and local dependencies are
  intentionally ignored by git.
