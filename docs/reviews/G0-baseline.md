---
status: passed
date: 2026-07-16
audience: maintainers, OpenAI Build Week judges
scope: canonical Build Week baseline and G0 reproducibility gate
---

# G0 review — canonical Build Week baseline

**Decision:** Passed on 2026-07-16.

The P0 baseline is reproducible, provenance-complete, contract-valid, and
packaged independently of the maintainer's sibling checkout. The declared
quality defect is observed evidence and is not treated as a pipeline failure.

## Reviewed revisions

- P0 implementation range: `827c223` through `34e4895`.
- Canonical baseline Agent revision: `b6e22daa0e7340836019294bb0ad76bf4522069f`.
- Canonical game revision: `348b9fd5501e71ebc7142e10f9068fc1490b5124`.
- Canonical game tree: `225cd5451d09bb92da674234a79ecaf8db4beb3a`.
- Game archive SHA-256:
  `2ee8ed13121a35597cad69f6fa5b03c57bfe2c3565d0dfb9f0def284110f610d`.

The baseline was generated from a clean Agent revision. Later P0 commits add
the dependency security upgrade and G0 reviewer without changing the pinned
game trace.

## Exact preparation and baseline commands

```bash
scripts/setup-build-week-toolchain --json
. .tools/build-week/env.sh
export GAME_PROJECT_PATH="$PWD/reports/build-week-2026/game-source"

uv run python tools/generate_build_week_baseline.py --replace
uv run python tools/generate_build_week_baseline.py \
  --output "$PWD/reports/build-week-2026/baseline/repro-canonical-normal-seed-42" \
  --replace \
  --compare-to "$PWD/reports/build-week-2026/baseline/canonical-normal-seed-42" \
  --json

uv run python tools/review_build_week_g0.py --json
```

The baseline generator expands the tracked declaration in
`config/build_week_2026_baseline.json` into the following real pipeline:

1. 100 balanced runs, seed 42, 20 weeks, normal difficulty, and
   `default_first_semester`.
2. Event graph and action catalog export from Godot.
3. Analytics, anomaly, value, route, and coverage generation.
4. Clean content, JSON content, economy, risk, and route validators.
5. Separate demo-quality observation.
6. Universal invariant gates from `config/ci_gates.yaml`.

## Automated result

The machine review is written to the ignored competition evidence path
`reports/build-week-2026/reviews/G0-baseline.json` and reported:

- G0 checks: 15 passed, 0 failed.
- Python: 299 passed, 0 skipped.
- Frontend: 11 passed; Vite 8.1.5 public production build passed.
- Dependency audit: 0 vulnerabilities.
- Ruff: passed.
- Real trace/catalog consistency: passed.
- Clean real-game validators: 5 passed.
- Canonical artifacts: 20 present and hash-verified.
- Independent fixed-seed reproduction: 20 of 20 SHA-256 values identical.
- Sanitized metadata files: no absolute user path found.

## Observed demo problem

The demo validator deliberately exits non-zero in the isolated
`quality-observation` directory. The baseline generator accepts that exit only
when all three predeclared evidence signatures are present:

- Normal `take_a_real_break` share is 0.199, above 0.150.
- Realistic `take_a_real_break` share is 0.217, above 0.150.
- Normal runs produce two ending types instead of at least four.

The main baseline still passes every universal invariant and clean contract
validator. This separation prevents both false pipeline failures and false
claims that the product-quality gate already passes.

## Independent review answers

- **Are artifacts tied to declared source/config revisions?** Yes. The report
  records the Agent commit, game commit/tree/archive, runtime/config/prompt
  fingerprints, Godot 4.4 version, and per-artifact SHA-256 values.
- **Can a clean setup locate the packaged game without a sibling checkout?**
  Yes. The managed path is `reports/build-week-2026/game-source`, and the
  inventory recognizes its verified provenance marker.
- **Are unavailable tools or skips called passes?** No. The final test run has
  no skips. Docker is recorded as one optional warning, not as available.
- **Does the demo target come from observed evidence?** Yes. It reproduces
  byte-for-byte across two independent real Godot runs.
- **Is distribution authorized?** Yes. The maintainer confirmed full ownership
  of both projects and approved the private competition bundle.

## Platform boundary

The real G0 run was executed on Apple Silicon macOS with the pinned native
Godot 4.4 binary. The same repository-relative game bundle is platform-neutral;
checksum-pinned native assets exist for macOS ARM64 and Linux AMD64. Linux
path discovery and packaging are covered here, but native Linux execution is
not claimed from this macOS host. Linux ARM64 uses Replay or an externally
provided Godot runtime because the official pinned native asset is unavailable.

Docker remains optional at G0 and its unavailable daemon is recorded as a
warning. Containerized Replay/UI verification belongs to the later deployment
gate.
