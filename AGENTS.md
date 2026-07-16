# Repository agent notes

## Automated evaluator: run this first

From the repository root, use the offline paths before attempting Docker,
Godot, a browser, or any model provider:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

`inspect` uses only the Python standard library and verifies the committed
`judge-manifest.json`, 22 artifact hashes/schemas, and six claim-to-evidence
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
export GAME_PROJECT_PATH=/home/bo/projects/python/study-in-germany
export GODOT_BIN=/home/bo/projects/python/game_analysis_agent/scripts/godot-docker-wrapper
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
- `GODOT_DOCKER_MOUNT_ROOT` selects the shared parent of both repositories.
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

For a request to diagnose, repair, evaluate, or judge the committed Build Week
persona campaign, run `.agents/skills/playtest-forge/scripts/preflight` before
inspecting candidate game changes. Then use the repository Skill at
`.agents/skills/playtest-forge/SKILL.md`. It requires facts before inference,
one mechanism, an isolated game worktree, budgeted allowlisted edits, fixed and
unseen-holdout verification, and an explicit accepted/rejected record. Never
edit the canonical baseline bundle under `reports/build-week-2026/game-source`
in place and never merge a repair automatically.
