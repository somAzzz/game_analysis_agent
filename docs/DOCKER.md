# Docker setup

The pipeline comes with a `docker-compose.yml` that orchestrates two
services: a vLLM inference server (GPU) and an opt-in agent CLI
container (CPU-only). Everything wires together through
`docker-compose.yml` + `.env`, mirroring the well-tested setup in
[fintext_llm/docker-compose.yml](../../fintext_llm/docker-compose.yml)
so the two projects can share a machine without port collisions.

## 1. Prerequisites

- Docker Engine 24+ with the `nvidia-container-toolkit` installed.
- An NVIDIA Blackwell card (RTX PRO 6000 / RTX 5070 / B200). NVFP4
  requires `sm_100` or `sm_120` — it **will not** run on H100 / A100 /
  older.
- ~70 GB of free disk for the Qwen3.6 27B NVFP4 weights (cached under
  `~/.cache/huggingface/`).
- A working `study-in-germany` Godot project if you want the agent to
  drive `run_gameplay_agent.py sim` / `play` end-to-end. (`probe`,
  `export`, `analyze`, `qa --report-dir=...` work without Godot.)

## 2. One-time setup

```bash
cp .env.example .env
# Edit .env:
#   - HF_TOKEN (if your model is auth-gated — the official NVFP4 quant
#     does not require a token at the moment).
#   - GAME_PROJECT_PATH=/abs/path/to/study-in-germany
#   - VLLM_BIND_PORT=8000 (already the default).
```

## 3. Start vLLM

```bash
docker compose up vllm -d
docker compose logs -f vllm     # tail the server boot
docker compose ps                # confirm ``vllm`` is healthy
```

Once the container reports `Application startup complete`, the
endpoint is `http://localhost:8000/v1`. Sanity check:

```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer local-dev-token"
```

You should see `nvidia/Qwen3.6-27B-NVFP4` (or whatever you set
`LLM_MODEL=` to).

## 4. Run the agent CLI

```bash
# Quick help
docker compose --profile cli run --rm agent

# 100-run baseline + analysis + every agent
docker compose --profile cli run --rm agent \
  all --runs 100 --policy balanced

# Boundary probe (requires GAME_PROJECT_PATH to point at study-in-germany)
docker compose --profile cli run --rm agent \
  probe --extreme "zero_money,deep_debt,flag_chaos"

# Interactive playthrough driven by the LLM
docker compose --profile cli run --rm agent \
  play --report-dir reports/play/test
```

The agent container binds `./reports` back to the host so artifacts
land under `reports/<subdir>/` on your machine for inspection.

## 5. Without Docker (host-native)

The pipeline still runs natively if you have the Python deps installed
and a vLLM server reachable at `VLLM_BASE_URL`:

```bash
python3 tools/run_gameplay_agent.py all --runs 100 --policy balanced
```

The Docker setup is purely a convenience for users who want a
containerized vLLM alongside the CLI.

## 6. Configurable knobs

All knobs live in `.env`:

| Env var | Purpose | Default |
|---|---|---|
| `LLM_MODEL` | HF repo id or local path served by vLLM | `nvidia/Qwen3.6-27B-NVFP4` |
| `LLM_MAX_MODEL_LEN` | Context length passed to vLLM | `32768` |
| `LLM_ENABLE_MTP` | Qwen3.6 ships with MTP weights; keep `1`, set `0` only for checkpoints without them | `1` |
| `HF_TOKEN` | Auth to gated HuggingFace repos | (empty) |
| `VLLM_BIND_PORT` | Host port the container binds to | `8000` |
| `CUDA_VISIBLE_DEVICES` | GPU index (or `all`) | `0` |

## 7. Version pinning

`vllm/vllm-openai:v0.24.0` is the latest stable tag (as of 2026-07-04)
with NVFP4 + MTP validated against Qwen3.6 27B NVFP4. Bump quarterly;
see fintext_llm for the same pinning rationale.

## 8. Troubleshooting

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