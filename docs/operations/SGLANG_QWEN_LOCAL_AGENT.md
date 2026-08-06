# Local SGLang + Qwen3.6 NVFP4

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

The host endpoint is `http://localhost:30000/v1`. The `agent` container uses
`http://sglang:30000/v1`; keep these addresses separate because `localhost`
inside a container refers to that container itself.

```bash
curl http://localhost:30000/v1/models \
  -H 'Authorization: Bearer local-dev-token'
```

Expected served model: `qwen3.6-27b-nvfp4`.

## Primary configuration

```env
LLM_PROVIDER=sglang
LLM_MODEL=nvidia/Qwen3.6-27B-NVFP4
LLM_SERVED_MODEL_NAME=qwen3.6-27b-nvfp4
SGLANG_MODEL=qwen3.6-27b-nvfp4
SGLANG_BASE_URL=http://localhost:30000/v1
SGLANG_API_KEY=local-dev-token

SGLANG_MAMBA_CACHE_STRATEGY=extra_buffer
SGLANG_PAGE_SIZE=64
SGLANG_ENABLE_MTP=1
SGLANG_SPEC_NUM_STEPS=3
SGLANG_SPEC_TOPK=1
SGLANG_SPEC_NUM_DRAFT_TOKENS=4
```

Radix prefix caching is enabled by default in SGLang. `extra_buffer` provides
the hybrid Mamba/GDN state tracking required for overlap scheduling and
branching-point caching. Qwen3.6's built-in MTP head is selected with NEXTN;
no external draft checkpoint is loaded.

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
SGLANG_ENABLE_MTP=0 docker compose --profile local-sglang up -d --force-recreate sglang
```

To return to the vLLM baseline:

```bash
docker compose stop sglang
LLM_PROVIDER=vllm docker compose --profile local-vllm up -d vllm
```

Do not relabel older `local-vllm-real-godot` evidence. Fresh SGLang runs use
the existing `local-sglang-real-godot` truth label.
