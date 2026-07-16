# Docker setup

The default Compose path is a CPU-only, read-only dashboard. Offline Replay,
Godot tooling, the legacy CLI, and NVIDIA vLLM are separate opt-in profiles, so
an evaluator never downloads a model or reserves a GPU by running bare
`docker compose up`.

## 1. Prerequisites

- Docker Engine 24+ for the dashboard or Judge image.
- NVIDIA Container Toolkit and a Blackwell card only for the optional
  `local-nvidia` profile. NVFP4
  requires `sm_100` or `sm_120` — it **will not** run on H100 / A100 /
  older.
- ~70 GB of free disk for the Qwen3.6 27B NVFP4 weights (cached under
  `~/.cache/huggingface/`).
- A working `study-in-germany` Godot project for `sim`, `probe`, `export`,
  `validate`, `interactive-probe`, or `play`. Pure `analyze`, recorded `eval`,
  and report QA do not invoke Godot.

## 2. CPU-only Judge dashboard and Replay

```bash
docker compose up -d dashboard
docker compose --profile judge run --rm replay
```

The dashboard listens on `http://127.0.0.1:8080` by default. Replay has no
network, runs read-only as an unprivileged user, and needs no API key. The
multi-architecture source is `Dockerfile.judge`; its official Python base is
pinned by image-index digest and does not force an amd64 platform on Apple
Silicon.

The image is not claimed as published until `tools/build_judge_image.sh` has
produced registry metadata for both `linux/amd64` and `linux/arm64`.

## 3. Optional local game and model setup

```bash
cp .env.example .env
# Edit .env:
#   - HF_TOKEN (if your model is auth-gated — the official NVFP4 quant
#     does not require a token at the moment).
#   - GAME_PROJECT_PATH=/abs/path/to/study-in-germany
#   - GODOT_DOCKER_MOUNT_ROOT=/shared/parent/of/both/checkouts
#   - VLLM_BIND_PORT=8000 (already the default).
```

## 4. Start optional vLLM and Godot

```bash
docker compose --profile local-nvidia --profile game-tools up -d vllm godot
docker compose logs -f vllm     # tail the server boot
docker compose ps                # confirm ``vllm`` and ``godot`` are healthy
```

The Godot service is an idle tool sidecar; the repository wrapper executes
commands inside it. To use only Godot without reserving the GPU, run
`docker compose --profile game-tools up -d godot`.

Once the container reports `Application startup complete`, the
endpoint is `http://localhost:8000/v1`. Sanity check:

```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer local-dev-token"
```

You should see `nvidia/Qwen3.6-27B-NVFP4` (or whatever you set
`LLM_MODEL=` to).

## 5. Run the agent CLI

Run gameplay commands from the host and point `GODOT_BIN` at the wrapper. It
reuses the compose sidecar and reaches vLLM through the published host port:

```bash
export GAME_PROJECT_PATH=/abs/path/to/study-in-germany
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"

uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/compose-smoke
uv run python tools/run_gameplay_agent.py play \
  --report-dir reports/play/compose-live
```

The opt-in `agent` container is for pure-Python analysis/QA; it intentionally
does not mount the Docker socket or execute processes in the Godot sidecar:

```bash
# Quick help
docker compose --profile cli run --rm agent

# Analyze existing trace data
docker compose --profile cli run --rm agent \
  analyze --report-dir reports/balance/test
```

The agent container binds `./reports` back to the host so artifacts
land under `reports/<subdir>/` on your machine for inspection.

## 6. Without Docker (host-native)

The pipeline still runs natively if you have the Python deps installed
and a vLLM server reachable at `VLLM_BASE_URL`:

```bash
python3 tools/run_gameplay_agent.py all --runs 100 --policy balanced
```

The Docker setup keeps both external runtimes available while the Python CLI
remains easy to run and debug on the host.

## 7. Configurable knobs

All knobs live in `.env`:

| Env var | Purpose | Default |
|---|---|---|
| `LLM_MODEL` | HF repo id or local path served by vLLM | `nvidia/Qwen3.6-27B-NVFP4` |
| `LLM_MAX_MODEL_LEN` | Context length passed to vLLM | `32768` |
| `LLM_ENABLE_MTP` | Qwen3.6 ships with MTP weights; keep `1`, set `0` only for checkpoints without them | `1` |
| `HF_TOKEN` | Auth to gated HuggingFace repos | (empty) |
| `VLLM_BIND_PORT` | Host port the container binds to | `8000` |
| `CUDA_VISIBLE_DEVICES` | GPU index (or `all`) | `0` |
| `GODOT_DOCKER_IMAGE` | Godot sidecar/fallback image | `barichello/godot-ci:4.4` |
| `GAME_PROJECT_PATH` | Absolute checkout mounted at the identical container path | `/home/bo/projects/python/study-in-germany` |
| `GODOT_DOCKER_MOUNT_ROOT` | Shared parent of Agent and game checkouts, mounted at the same path | `/home/bo/projects/python` |

## 8. Version pinning

`vllm/vllm-openai:v0.25.0` is the latest stable tag (as of 2026-07-13)
with NVFP4 + MTP validated against Qwen3.6 27B NVFP4. Bump quarterly;
see fintext_llm for the same pinning rationale.

## 9. Troubleshooting

**`error: failed to inspect docker image`** — your `vllm/vllm-openai`
image isn't pulled yet. Run `docker compose pull vllm` first.

**`CUDA out of memory`** — drop `--gpu-memory-utilization 0.9` to
`0.8` in the compose file's `command:` (or set `LLM_GPU_MEMORY_UTILIZATION`
if you wire it through). For Qwen3.6 27B NVFP4, 24-32 GB of VRAM is
the recommended floor.

**`--speculative-config` complains about missing MTP weights** —
your checkpoint is Qwen3.5 or earlier; set `LLM_ENABLE_MTP=0` in
`.env`.

**`HF_TOKEN` not set on a gated repo** — fix the env var, then
`docker compose restart vllm`. The token is forwarded only for
authenticated model downloads.

**Godot sidecar is not running** — start it with
`docker compose --profile game-tools up -d godot`. The wrapper automatically falls back to a
one-shot `docker run --rm` when the compose service is absent.
