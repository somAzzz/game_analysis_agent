# Local SGLang + Qwen3.8-27B NVFP4 + DFlash2

SGLang with DFlash2 is the primary local inference backend. DSpark remains a
one-command rollback, and vLLM remains a separately
profiled baseline and fallback; both expose the same OpenAI-compatible served
model alias so campaign evidence records the provider change without changing
the model identity.

## Start

```bash
cp .env.example .env
docker pull lmsysorg/sglang@sha256:d6e7288627be8b02be88e4bba38e73f6d50e2826869f753c13a4c4385ab3eda9
docker compose --env-file .env --env-file config/sglang/dflash2.env \
  --profile local-sglang up -d sglang
docker compose logs -f sglang
```

The Day-0 image contains the matching SGLang runtime, not the model weights.
On first DFlash2 start, the container downloads `incoai/Qwen3.8-27B-DFlash2`
in addition to the existing `RadixArk/Qwen3.8-27B-NVFP4` target. They are
persisted in the host's `~/.cache/huggingface` bind mount, so normal container
recreation does not download them again. Pre-downloading is optional.

SGLang PRs #35371 and #35496 are merged. The primary profile uses the official
multi-architecture DFlash2 image pinned by
`sha256:d6e7288627be8b02be88e4bba38e73f6d50e2826869f753c13a4c4385ab3eda9`
in `config/sglang/dflash2.env`. The retired local bridge remains documented in
the dated migration record only; normal startup no longer builds it.

The host endpoint is `http://localhost:30000/v1`. The `agent` container uses
`http://sglang:30000/v1`; keep these addresses separate because `localhost`
inside a container refers to that container itself.

```bash
curl http://localhost:30000/v1/models \
  -H 'Authorization: Bearer local-dev-token'
```

Expected served model: `qwen3.8-27b`.

## Primary configuration

```env
LLM_PROVIDER=sglang
SGLANG_MODEL_PATH=RadixArk/Qwen3.8-27B-NVFP4
SGLANG_MODEL_REVISION=554ebba9b5f1b79dc11246341960360e6ef05ef4
SGLANG_MODEL=qwen3.8-27b
SGLANG_BASE_URL=http://localhost:30000/v1
SGLANG_API_KEY=local-dev-token

SGLANG_MEM_FRACTION_STATIC=0.80
SGLANG_ATTENTION_BACKEND=flashinfer
SGLANG_CHUNKED_PREFILL_SIZE=2048
SGLANG_ENABLE_APC=1
SGLANG_MAMBA_CACHE_STRATEGY=extra_buffer_lazy
SGLANG_SPECULATIVE_ALGORITHM=DFLASH
SGLANG_DRAFT_MODEL_PATH=incoai/Qwen3.8-27B-DFlash2
SGLANG_DRAFT_MODEL_REVISION=dedf8df68adfb1afeaf7b7480c0a0243108177b4
SGLANG_NUM_DRAFT_TOKENS=8
SGLANG_ENABLE_METRICS=1
```

APC is implemented by SGLang's Unified Radix Cache and is enabled unless
`SGLANG_ENABLE_APC=0` adds `--disable-radix-cache`. The
`extra_buffer_lazy` strategy reduces the hybrid GDN state cost while preserving
branching-point caching. DFlash2 uses block size 8 and the upstream selector
implementation required by the quantized NVFP4 target `lm_head`. The 0.80
static-memory fraction leaves the host headroom required on a 128GB DGX Spark.

The application keeps one provider-independent prompt/context contract. Local
Qwen thinking uses the same `chat_template_kwargs`, and event-choice
`structured_outputs` are translated to SGLang's escaped regex constraint while
vLLM retains its native choice constraint. Trace, parsing, repair, and audit
records therefore keep the same application-level shape across both engines.

## Safe rollout and fallback

Before retaining gameplay evidence, verify model identity, short non-thinking
JSON decisions, thinking-mode decisions, tool calls, a repeated-prefix soak,
and concurrency 4. Compare legality/parse/repair rates as well as latency.

To isolate speculative decoding without abandoning SGLang:

```bash
docker compose --env-file .env --env-file config/sglang/target-only.env \
  --profile local-sglang up -d --force-recreate sglang
```

To roll back to the pinned DSpark image and model:

```bash
docker compose --env-file .env --env-file config/sglang/dspark.env \
  --profile local-sglang up -d --force-recreate sglang
```

To restore DFlash2:

```bash
docker compose --env-file .env --env-file config/sglang/dflash2.env \
  --profile local-sglang up -d --force-recreate sglang
```

To return to the vLLM baseline:

```bash
docker compose stop sglang
LLM_PROVIDER=vllm docker compose --profile local-vllm up -d vllm
```

Do not relabel older `local-vllm-real-godot` evidence. Fresh SGLang runs use
the existing `local-sglang-real-godot` truth label.
