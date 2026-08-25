# Docker setup

The default Compose path is a CPU-only, read-only dashboard. Godot tooling, the
legacy CLI, and NVIDIA inference are separate opt-in profiles, so a dashboard
user never downloads a model or reserves a GPU by running bare
`docker compose up`.

## 1. Prerequisites

- Docker Engine 24+ for the dashboard image.
- NVIDIA Container Toolkit and a Blackwell card only for the optional
  `local-nvidia` profile. NVFP4
  requires `sm_100` or `sm_120` — it **will not** run on H100 / A100 /
  older.
- ~70 GB of free disk for the Qwen3.6 27B NVFP4 weights (cached under
  `~/.cache/huggingface/`).
- The embedded `study-in-germany` demo is included. Godot commands prepare a
  writable copy under `reports/`; pure `analyze`, recorded `eval`, and report
  QA do not invoke Godot.

## 2. CPU-only dashboard

```bash
docker compose up -d dashboard
```

The dashboard listens on `http://127.0.0.1:8080` by default. It runs read-only
as an unprivileged user and needs no API key for recorded evidence. The image
source is `Dockerfile.dashboard`; its official Python base is pinned by
image-index digest and does not force an amd64 platform on Apple Silicon.

## 3. Optional local game and model setup

```bash
cp .env.example .env
# Edit .env:
#   - HF_TOKEN (if your model is auth-gated — the official NVFP4 quant
#     does not require a token at the moment).
#   - GODOT_DOCKER_MOUNT_ROOT=/absolute/parent/of/this/repository
#   - SGLANG_BIND_PORT=30000 (already the default).
```

## 4. Start the primary SGLang backend and Godot

```bash
docker compose --profile local-nvidia --profile game-tools up -d sglang godot
docker compose logs -f sglang   # tail the server boot
docker compose ps               # confirm ``sglang`` and ``godot`` are healthy
```

The Godot service is an idle tool sidecar; the repository wrapper executes
commands inside it. To use only Godot without reserving the GPU, run
`docker compose --profile game-tools up -d godot`.

Once the container is healthy, the endpoint is
`http://localhost:30000/v1`. Sanity check:

```bash
curl http://localhost:30000/v1/models \
  -H "Authorization: Bearer local-dev-token"
```

You should see the stable alias `qwen3.6-27b-nvfp4`. To use the retained vLLM
baseline instead, run `docker compose --profile local-vllm up -d vllm` and set
`LLM_PROVIDER=vllm`.

## 5. Run the agent CLI

Run gameplay commands from the host and point `GODOT_BIN` at the wrapper. It
reuses the compose sidecar and reaches SGLang through the published host port:

```bash
uv run python tools/build_week/prepare_embedded_demo.py \
  --output reports/docker-game-runtime --replace --json
export GAME_PROJECT_PATH="$PWD/reports/docker-game-runtime"
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"

uv run python tools/gameplay/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/compose-smoke
uv run python tools/gameplay/run_gameplay_agent.py play \
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
and the selected OpenAI-compatible server reachable at its configured base URL:

```bash
python3 tools/gameplay/run_gameplay_agent.py all --runs 100 --policy balanced
```

The Docker setup keeps both external runtimes available while the Python CLI
remains easy to run and debug on the host.

## 7. Dashboard and Codex communication model

The supported development topology is deliberately hybrid:

- GitHub Pages and the dashboard image are evidence surfaces; they need no model,
  game checkout, API key, or Docker socket.
- Codex runs on the host, discovers `.agents/skills/playtest-forge`, and calls
  the repository services/scripts through its shell tool. MCP is not required.
- The Godot wrapper communicates with the `godot` sidecar through
  `docker compose exec`; if the sidecar is absent it uses a bounded one-shot
  container with identical absolute mounts.
- Local SGLang (or the vLLM fallback) is reached through its published
  OpenAI-compatible host endpoint.
  The OpenAI provider uses the same campaign request, progress, aggregation, and
  experiment-registry contracts, with the key retained server-side.

The dashboard image contains `game-overlays/` plus curated deterministic static
experiment fixtures. Raw local-model logs are excluded from both the image and
Git. `Dockerfile.dashboard` packages only the public fixture set. The `agent`
container is not a controller for sibling containers.

## 8. Configurable knobs

All knobs live in `.env`:

| Env var | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | Active local/cloud provider | `sglang` |
| `LLM_MODEL` | HF repo id or local path served by the local engine | `nvidia/Qwen3.6-27B-NVFP4` |
| `LLM_MAX_MODEL_LEN` | Operational prompt + output context limit | `65536` |
| `LLM_MAX_NUM_SEQS` | Maximum continuously batched sequences per scheduler iteration | `4` |
| `LLM_MAX_NUM_BATCHED_TOKENS` | Optional tokens processed per scheduler iteration; blank uses vLLM tuning | (empty) |
| `LLM_ENABLE_PREFIX_CACHING` | Reuse exact shared prefixes during prefill | `1` |
| `LLM_MAMBA_CACHE_MODE` | Hybrid GDN/Mamba cache coordination mode | `align` |
| `LLM_PREFIX_MATCH_UNIT` | Fine-grained hybrid prefix match boundary in tokens | `16` |
| `LLM_ENABLE_MTP` | Opt in to three-token MTP speculative decoding for bounded long-output tests | `0` |
| `SGLANG_BIND_PORT` | Host port for the primary SGLang server | `30000` |
| `SGLANG_MAMBA_CACHE_STRATEGY` | Hybrid Mamba radix-cache scheduler | `extra_buffer` |
| `SGLANG_PAGE_SIZE` | Radix cache page size | `64` |
| `SGLANG_ENABLE_MTP` | Enable Qwen3.6 native MTP/NEXTN | `1` |
| `SGLANG_SPEC_NUM_STEPS` | MTP draft depth | `3` |
| `SGLANG_SPEC_TOPK` | MTP branching factor | `1` |
| `SGLANG_SPEC_NUM_DRAFT_TOKENS` | MTP verification capacity | `4` |
| `HF_TOKEN` | Auth to gated HuggingFace repos | (empty) |
| `VLLM_BIND_PORT` | Host port the container binds to | `8000` |
| `CUDA_VISIBLE_DEVICES` | GPU index (or `all`) | `0` |
| `GODOT_DOCKER_IMAGE` | Godot sidecar/fallback image | `barichello/godot-ci:4.4` |
| `GAME_PROJECT_PATH` | Writable prepared demo runtime mounted at the identical container path | `reports/docker-game-runtime` after preparation |
| `GODOT_DOCKER_MOUNT_ROOT` | Parent of this repository, mounted at the same absolute path | wrapper-detected repository parent |

## 9. Version pinning

`lmsysorg/sglang:v0.5.16-cu130-runtime` is the primary pin. Qwen3.6 uses
ModelOpt FP4, Radix cache with `extra_buffer`, and optional NEXTN/MTP. The
fallback `vllm/vllm-openai:v0.26.0` remains pinned as of 2026-07-31 and adds fine-grained
prefix-cache hits for aligned attention/Mamba hybrid models. Hybrid APC is
still experimental: treat it only as a prefill optimization, never as a
correctness or context-capacity guarantee.

## 10. Troubleshooting

**`error: failed to inspect docker image`** — pull the selected engine first:
`docker compose pull sglang` or `docker compose pull vllm`.

**`CUDA out of memory`** — lower `SGLANG_MEM_FRACTION_STATIC`, reduce
`LLM_MAX_NUM_SEQS`, or temporarily set `SGLANG_ENABLE_MTP=0`. On WSL2,
Blackwell GPU passthrough may reserve substantial memory outside PyTorch.

**`--speculative-config` complains about missing MTP weights** —
disable the opt-in with `LLM_ENABLE_MTP=0`. The project default is already
APC-only.

**Need to isolate APC or MTP behavior** — keep all other flags fixed and set
exactly one of `LLM_ENABLE_PREFIX_CACHING=1` or `LLM_ENABLE_MTP=1`. Re-run
the same serialized requests and compare validity plus latency; never infer a
game result from whether a prefix-cache hit occurred.

**`HF_TOKEN` not set on a gated repo** — fix the env var, then restart the
selected backend. The token is forwarded only for
authenticated model downloads.

**Godot sidecar is not running** — start it with
`docker compose --profile game-tools up -d godot`. The wrapper automatically falls back to a
one-shot `docker run --rm` when the compose service is absent.
