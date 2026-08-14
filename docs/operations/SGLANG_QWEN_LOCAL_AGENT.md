# Local SGLang + Qwen3.8-27B NVFP4

SGLang is the primary local inference backend. vLLM remains a separately
profiled baseline and fallback; both expose the same OpenAI-compatible served
model alias so campaign evidence records the provider change without changing
the model identity.

## Start

```bash
cp .env.example .env
docker compose pull sglang
docker compose --profile local-nvidia up -d sglang
docker compose logs -f sglang
```

The Day-0 image contains the matching SGLang runtime, not the model weights.
On first start, the container downloads both `RadixArk/Qwen3.8-27B-NVFP4`
(about 21.9 GB) and `RadixArk/Qwen3.8-27B-DSpark` (about 2.7 GB). They are
persisted in the host's `~/.cache/huggingface` bind mount, so normal container
recreation does not download them again. Pre-downloading is optional.

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
SGLANG_MODEL=qwen3.8-27b
SGLANG_BASE_URL=http://localhost:30000/v1
SGLANG_API_KEY=local-dev-token

SGLANG_MEM_FRACTION_STATIC=0.85
SGLANG_ATTENTION_BACKEND=flashinfer
SGLANG_CHUNKED_PREFILL_SIZE=2048
SGLANG_ENABLE_APC=1
SGLANG_MAMBA_CACHE_STRATEGY=extra_buffer_lazy
SGLANG_ENABLE_DSPARK=1
SGLANG_DRAFT_MODEL_PATH=RadixArk/Qwen3.8-27B-DSpark
```

APC is implemented by SGLang's Unified Radix Cache and is enabled unless
`SGLANG_ENABLE_APC=0` adds `--disable-radix-cache`. The
`extra_buffer_lazy` strategy reduces the hybrid GDN state cost while preserving
branching-point caching. DSpark loads its trained draft checkpoint separately
and runs with `--speculative-algorithm DSPARK`.

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
SGLANG_ENABLE_DSPARK=0 docker compose --profile local-sglang up -d --force-recreate sglang
```

To return to the vLLM baseline:

```bash
docker compose stop sglang
LLM_PROVIDER=vllm docker compose --profile local-vllm up -d vllm
```

Do not relabel older `local-vllm-real-godot` evidence. Fresh SGLang runs use
the existing `local-sglang-real-godot` truth label.
