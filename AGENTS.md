# Repository agent notes

## Godot execution

The host may not expose a `godot` or `godot4` binary. Before declaring real
Godot tests unavailable, check Docker. This machine has used the cached image
`barichello/godot-ci:4.4` through the repository wrapper:

```bash
export GAME_PROJECT_PATH=/home/bo/projects/python/study-in-germany
export GODOT_BIN=/home/bo/projects/python/game_analysis_agent/scripts/godot-docker-wrapper
"$GODOT_BIN" --version
```

`docker compose up -d godot vllm` starts the Godot tool sidecar and LLM
together. The wrapper first reuses that running sidecar with
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
