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

If an adjacent `../study-in-germany` checkout exists, the marked smoke test also
validates its real generated reports. A checkout elsewhere can be selected
explicitly:

```bash
GAME_PROJECT_PATH=/path/to/study-in-germany \
  uv run pytest tests/test_game_contract.py -m game_contract -ra
```

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
checks out a pinned game revision, downloads an official Godot build, verifies
the published SHA-512 before installing it, and then generates and analyzes a
fresh deterministic trace. It exports the catalogs, runs all six Godot
validators with fresh route/demo prerequisites, enforces
`config/ci_gates.yaml`, installs the versioned integration probe into the
pinned checkout, captures canonical interactive risk guidance, and validates
the cross-repository artifacts against contract revision `1.0`. The generated
Agent and game evidence is uploaded
even when validation fails. The job never treats reports already present in
the game checkout as test results.

Because `somAzzz/study-in-germany` is private, the repository must define the
`STUDY_IN_GERMANY_TOKEN` Actions secret with read access to that repository.
The default game ref is pinned to
`348b9fd5501e71ebc7142e10f9068fc1490b5124`; manual runs can deliberately test
another repository, ref, or official Godot build tag through workflow inputs.

## Environment boundary

Fixture contracts, parser failures, orchestration behavior, manifests, and
frontend behavior are locally testable without external services. A machine
without a compatible Godot CLI cannot independently reproduce the real-game
producer checks. Live interactive-player evaluation additionally needs an LLM
endpoint. These are explicit integration tiers, not skipped assertions in the
deterministic test jobs.
