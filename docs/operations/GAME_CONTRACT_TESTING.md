# Game artifact contract testing

The Python package validates artifacts from `study-in-germany` against contract
revision `1.0`. The revision covers six stable boundaries:

- batch simulation rows (`raw_runs.jsonl`)
- boundary-probe rows (`boundary_runs.jsonl`)
- `action_catalog.json`
- `event_graph.json`
- the common validator report envelope (`errors`, `summary`, and optional
  `warnings`)
- interactive snapshots and canonical `RiskEvaluator` guidance

Current Godot exports do not embed a schema version. Consumers select revision
`1.0`; producers may add `"contract_version": "1.0"`, in which case a mismatch
is rejected. Unknown top-level and nested fields are allowed so additive game
changes remain compatible. Required fields, declared counts, unique IDs, core
state fields, JSON/JSONL syntax, and clean validator reports are fail-closed.

## Local checks

The complete deterministic suite does not require Godot or an LLM:

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

To run only the committed contract fixtures:

```bash
uv run pytest tests/test_game_contract.py -m "not game_contract"
```

Prepare the exact-pinned embedded demo into a writable runtime before a real
producer smoke. The canonical embedded tree is never used as a writable Godot
project:

```bash
uv run python tools/prepare_embedded_demo.py \
  --output reports/contract-game-runtime --replace --json
export GAME_PROJECT_PATH="$PWD/reports/contract-game-runtime"
export GODOT_BIN=godot4
uv run pytest tests/test_game_contract.py -m game_contract -ra
```

An external checkout may still be supplied as a developer override, but it is
not part of the evaluator or CI contract.

Individual artifacts can be checked without pytest:

```bash
uv run python -m game_analysis_agent.contracts trace reports/raw_runs.jsonl
uv run python -m game_analysis_agent.contracts validator_report \
  reports/content_validation.json --require-clean
uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/smoke
```

## CI tiers

`.github/workflows/test.yml` has two deterministic pull-request/push jobs:

- Python: locked dependency install, the full pytest suite, full-repository
  Ruff, and a strict dry-run of all 140 matrix cells.
- Frontend: `npm ci`, Vitest with coverage floors, and the public production
  build.

The real Godot contract job runs nightly and through `workflow_dispatch`. It
verifies the embedded game against the pinned upstream content-tree digest,
creates a writable runtime, downloads an official Godot build, verifies
the published SHA-512 before installing it, and then generates and analyzes a
fresh deterministic trace. It exports the catalogs, runs all six Godot
validators with fresh route/demo prerequisites, enforces
`config/ci_gates.yaml`, installs the versioned integration probe into the
pinned checkout, captures canonical interactive risk guidance, and validates
the cross-repository artifacts against contract revision `1.0`. The generated
Agent and game evidence is uploaded
even when validation fails. The job never treats reports already present in
the game checkout as test results.

The current game ref is pinned to
`348b9fd5501e71ebc7142e10f9068fc1490b5124`. No game-repository token or sibling
checkout is required. Manual runs may select another official Godot build tag;
changing the embedded game pin is a reviewed source change, not a workflow input.

## Environment boundary

Fixture contracts, parser failures, orchestration behavior, manifests, and
frontend behavior are locally testable without external services. A machine
without a compatible Godot CLI cannot independently reproduce the real-game
producer checks. Live interactive-player evaluation additionally needs an LLM
endpoint. These are explicit integration tiers, not skipped assertions in the
deterministic test jobs.
