# Repository agent notes

## Codex Skill discovery and mandatory routing

Launch Codex from this repository root. Codex scans
`$REPO_ROOT/.agents/skills`, so the checked-in `playtest-forge` metadata is
available for implicit selection. `AGENTS.md` is loaded before work; the full
Skill uses progressive disclosure and is read after selection.

For any request involving game testing, judging, diagnosis, balance, economy,
content routes, boundaries, persona/subagent playthroughs, parameter tuning, or
game repair, **use `$playtest-forge`** after the two offline evaluator commands
below. Read `.agents/skills/playtest-forge/SKILL.md` completely, then read only
the scenario references it routes to. A canonical explicit evaluator prompt is:

```text
Use $playtest-forge to review the committed automated and persona-playthrough
evidence, explain the rejected candidate, and propose the next bounded experiment.
```

If the evaluator does not expose a Skill selector, does not inject a Skill
list, or is not Codex, treat direct reading of
`.agents/skills/playtest-forge/SKILL.md` as the mandatory fallback. Do not infer
that the full Skill was loaded merely because this `AGENTS.md` was loaded. The
repository guarantees a tracked, hash-verified Skill and this routing rule; it
does not claim that an undisclosed third-party evaluator implements Codex Skill
discovery.

## Automated evaluator: run this first

From the repository root, use the offline paths before attempting Docker,
Godot, a browser, or any model provider:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

`inspect` uses only the Python standard library and verifies the committed
`judge-manifest.json`, 123 artifact hashes/schemas (including the embedded
demo), and six claim-to-evidence
references. `replay` additionally requires `uv` and the locked environment; it
consumes exact hash-pinned persona fixtures and rechecks representative persona,
determinism, designed-failure, and rejected-repair gates. Neither command needs
network, Docker, GPU, API key, TTY, browser, open port, or a sibling game
checkout. Treat `failed` and `unsupported` as non-success states. See `JUDGE.md`
for exit codes, limitations, and remediation.

## Godot execution

The host may not expose a `godot` or `godot4` binary. Before declaring real
Godot tests unavailable, check Docker. This machine has used the cached image
`barichello/godot-ci:4.4` through the repository wrapper:

```bash
uv run python tools/prepare_embedded_demo.py \
  --output reports/local-game-runtime --replace --json
export GAME_PROJECT_PATH="$PWD/reports/local-game-runtime"
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"
"$GODOT_BIN" --version
```

`docker compose --profile game-tools up -d godot` starts the Godot tool
sidecar. Add `--profile local-nvidia vllm` only when local NVIDIA inference is
explicitly required. The wrapper first reuses the running Godot sidecar with
`docker compose exec`; if it is not running, it falls back to a one-shot
`docker run`. Both paths keep absolute host paths identical in the container
and execute Godot with the current UID/GID, so `--path`/`--out` arguments work
without creating root-owned reports.

Environment overrides:

- `GODOT_DOCKER_IMAGE` selects another image.
- `GODOT_DOCKER_MOUNT_ROOT` selects the parent of this repository.
- `GODOT_DOCKER_HOME` selects the mapped temporary Godot home.
- `GODOT_COMPOSE_SERVICE` selects the compose service name (default `godot`).

Use the Docker wrapper for routine local real-game tests. The scheduled/manual
CI job deliberately downloads and SHA-512-verifies its pinned official Godot
build, so do not replace that CI integrity check with an unverified image.

## MCP migration order

Before implementing any MCP wrapper, read
`docs/architecture/MCP_MIGRATION_PLAN.md`. The hard architectural rule is:

1. Extract transport-independent services first:
   `simulation_service.run(...)`, `report_service.read(...)`, and
   `gameplay_service.step(...)`.
2. Make the existing argparse CLI a thin adapter over those services.
3. Complete the service-layer acceptance gates and regressions.
4. Only then add the MCP adapter.

Do not register `tools/run_gameplay_agent.py` `cmd_*` functions as MCP
tools, construct `argparse.Namespace` inside MCP code, or duplicate
Godot/contract/report logic in an MCP package. CLI and MCP must share the same
typed request/result services.

## Build Week repair workflow

For the committed Build Week persona campaign, run
`.agents/skills/playtest-forge/scripts/preflight` before inspecting candidate
game changes. The Skill requires facts before inference, one mechanism, an
isolated game worktree, budgeted allowlisted edits, fixed and unseen-holdout
verification, and an explicit accepted/rejected record. Never edit the
canonical baseline bundle under `demo/study-in-germany` in place
and never merge a repair automatically.
