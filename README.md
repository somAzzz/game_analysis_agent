# Playtest Forge

Playtest Forge is a Codex-directed game QA system that combines deterministic
simulation, persona playthroughs, evidence-backed diagnosis, and bounded repair
experiments. A candidate change is accepted only when fixed and unseen-holdout
evidence supports it.

[Developer guide](docs/DEVELOPER_GUIDE.md) ·
[Architecture](docs/architecture/ARCHITECTURE.md) ·
[Docker guide](docs/operations/DOCKER.md) ·
[中文说明](README.zh-CN.md)

The reference integration uses the embedded Godot demo **Study in Germany**,
but the workflow is built around reusable typed services and contracts rather
than game-specific shell scripts.

## Capabilities

- Run deterministic simulations, boundary probes, validators, and difficulty
  matrices against Godot.
- Run persona campaigns through recorded Replay, local SGLang/vLLM, OpenAI, or
  another OpenAI-compatible provider.
- Preserve provider identity, source fingerprints, weekly decisions, game
  state, and failure clusters in auditable reports.
- Compare bounded candidate changes against fixed and unseen holdouts.
- Reject changes that improve a headline metric by weakening invariants,
  designed failures, persona alignment, or evidence completeness.
- Browse campaigns, decisions, reports, and human review records in the React
  dashboard.

## Quick start

Install the locked Python and frontend environments:

```bash
uv sync --extra dev --locked
npm --prefix frontend ci
```

Run the deterministic checks that do not require Godot or an LLM:

```bash
uv run pytest -q
uv run ruff check .
npm --prefix frontend run test:coverage
npm --prefix frontend run build:public
```

Start the read-only dashboard:

```bash
npm --prefix frontend run prepare:public
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. To enable the local API and durable human-review
records, build the frontend and start the server:

```bash
npm --prefix frontend run build:public
uv run python tools/judge/run_judge_api.py \
  --host 127.0.0.1 \
  --port 8080 \
  --frontend frontend/dist
```

Open `http://127.0.0.1:8080/`. Provider credentials remain in the server
environment and are never entered in the browser.

## Godot runtime

The repository includes an embedded reference game under
`demo/study-in-germany`. If no host `godot` binary is available, use the Docker
wrapper:

```bash
uv run python tools/build_week/prepare_embedded_demo.py \
  --output reports/local-game-runtime --replace --json
export GAME_PROJECT_PATH="$PWD/reports/local-game-runtime"
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"
export GODOT_DOCKER_MOUNT_ROOT="$(cd .. && pwd)"
docker compose --profile game-tools up -d godot
"$GODOT_BIN" --version
```

The wrapper reuses the long-running sidecar when available and otherwise runs
an equivalent one-shot container. Both paths preserve absolute host paths and
the current UID/GID.

Run a deterministic simulation and analysis:

```bash
uv run python tools/gameplay/run_gameplay_agent.py sim \
  --run-id smoke --runs 12 --policy balanced \
  --difficulty normal --seed 4242 \
  --scenario default_first_semester --weeks 20

uv run python tools/gameplay/run_gameplay_agent.py analyze \
  --report-dir reports/balance/smoke
```

## Local SGLang

The primary local profile uses Qwen3.8-27B NVFP4 with DFlash2 speculative
decoding. DSpark and target-only profiles are retained as explicit rollbacks.

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.sglang-dflash2.yml build sglang
docker compose --env-file .env --env-file config/sglang/dflash2.env \
  --profile local-sglang up -d sglang
docker compose logs -f sglang
```

See [SGLANG_QWEN_LOCAL_AGENT.md](docs/operations/SGLANG_QWEN_LOCAL_AGENT.md)
for model pins, profiles, health checks, and rollback commands.

## Codex-guided playtesting

The checked-in `playtest-forge` Skill governs gameplay judgments and repair
experiments. Start with its read-only preflight and session choices:

```bash
.agents/skills/playtest-forge/scripts/preflight
.agents/skills/playtest-forge/scripts/session-options --choices-only --json
```

The workflow freezes the game runtime, provider, difficulty, personas, seeds,
duration, protected metrics, and evidence contract before execution. Starting
a provider, spending API credit, or editing the game still requires the
corresponding user authorization.

For deterministic matrices, use the governed matrix command rather than direct
Godot loops:

```bash
uv run python tools/gameplay/run_gameplay_agent.py matrix \
  --config config/matrix.normal.yaml --dry-run --jobs 4 \
  --out reports/matrix-normal
```

Difficulty lanes are isolated in `config/matrix.easy.yaml`,
`config/matrix.normal.yaml`, `config/matrix.hard.yaml`, and
`config/matrix.realistic.yaml`.

## System shape

```text
Codex + playtest-forge
        │ freezes scope, evidence contract, and change budget
        ▼
Typed campaign / gameplay services
        │
        ├── deterministic Replay
        ├── local SGLang / vLLM
        └── OpenAI-compatible providers
        ▼
Godot probe → raw cells → sanitized bundle
        ▼
Failure clusters → bounded candidate → fixed + unseen proof
        ▼
Machine recommendation → dashboard → human decision
```

The CLI, dashboard API, and future MCP adapter share transport-independent
services. See the
[service-first MCP migration plan](docs/architecture/MCP_MIGRATION_PLAN.md)
before adding an MCP wrapper.

## Reports and storage

Runtime reports belong under `reports/` and are ignored by Git. Governed
matrices seal completed JSONL cells automatically. For other terminal report
trees, use the lossless archive service:

```bash
uv run python tools/reports/archive_jsonl.py archive \
  <terminal-report-dir> --apply --replace
```

The archive command deletes a source only after the Zstandard output
decompresses, reparses, and matches the original record count, byte count, and
SHA-256. See [REPORT_ARCHIVES.md](docs/operations/REPORT_ARCHIVES.md).

## Repository map

```text
.agents/skills/playtest-forge/    Codex workflow and evidence protocol
config/                           Profiles, targets, gates, and contracts
demo/study-in-germany/            Embedded Godot reference game
examples/                         Sanitized campaign and repair fixtures
frontend/                         Dashboard, inspector, reports, human review
game-overlays/                    Runtime-only reference-game adapters
src/game_analysis_agent/          Typed services, providers, and analysis
tools/ and scripts/               CLI adapters and runtime helpers
docs/                             Architecture, operations, plans, and reviews
```

## Current limitations

- Real gameplay requires Godot 4.4 or the Docker wrapper.
- Live persona campaigns require a compatible model endpoint.
- The dashboard API is intended for trusted local use; it is not a hosted
  multi-tenant service with authentication, quotas, TTLs, or billing controls.
- The embedded game is a reference fixture, not a complete commercial game.
- Human review records never merge a candidate automatically.

The project is MIT licensed. Third-party and generated-asset provenance is in
[ATTRIBUTION.md](ATTRIBUTION.md).
