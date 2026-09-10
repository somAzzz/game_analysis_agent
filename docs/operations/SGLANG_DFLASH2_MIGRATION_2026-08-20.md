# SGLang DFlash2 migration record — 2026-08-20

> **2026-09-10 follow-up:** SGLang v0.5.19 includes merged PRs #35371 and #35496. Active
> configuration now uses the official multi-architecture image pinned at
> `lmsysorg/sglang@sha256:d6e7288627be8b02be88e4bba38e73f6d50e2826869f753c13a4c4385ab3eda9`
> with a DGX Spark-safe static memory fraction of `0.80`. The local bridge and
> the `0.85` measurements below are retained as historical acceptance evidence.

## Decision

DFlash2 is accepted as the primary local speculative-decoding backend for
`RadixArk/Qwen3.8-27B-NVFP4`. DSpark remains the pinned one-command rollback,
and target-only SGLang remains the failure-isolation profile.

The migration passed the project acceptance rule: no request or API-contract
regressions and more than 3% improvement on the same frozen workload. The
measured end-to-end wall time fell by 16.8%, while completion-token throughput
rose by 20.4%.

## Immutable inputs

- Target model: `RadixArk/Qwen3.8-27B-NVFP4` at
  `554ebba9b5f1b79dc11246341960360e6ef05ef4`
- DFlash2 draft: `incoai/Qwen3.8-27B-DFlash2` at
  `dedf8df68adfb1afeaf7b7480c0a0243108177b4`
- DSpark draft: `RadixArk/Qwen3.8-27B-DSpark` at
  `85ef153be924f17ce4bf62726954eeaa4a73e854`
- SGLang base image:
  `lmsysorg/sglang@sha256:febfb971c7352570fc445c466ebd6ffc9d896024958e544a60f2137fd85856b1`
- Temporary DFlash2 bridge: [SGLang PR #35496](https://github.com/sgl-project/sglang/pull/35496)
  head `28198c8289f6ad59775f37d3bd9c9de67732c368`
- Accepted local image:
  `game-analysis-agent/sglang-dflash2@sha256:433a632aca8933497290e3ebde2f73b518b239f8ecb6b73c525648c4dc096b12`
- Frozen trace SHA-256:
  `c4e451cf5ec920d72052246f5c100f300efc6b109946daf10dfdae2bd0070a46`

The Docker build checks the exact PR commit before completing. The profile
pins the accepted local image digest on this host. On a clean host, build the
tag first, verify the resulting image, and update the accepted digest in
`config/sglang/dflash2.env` if the local content digest differs.

## Runtime configuration

Both measured arms used the same target, context length `262144`, maximum
running requests `4`, static memory fraction `0.85`, FlashInfer attention,
chunked prefill `2048`, Unified Radix Cache, and
`extra_buffer_lazy`. DFlash2 used block/draft length `8` and metrics enabled.

Startup verified all of the following:

- the NVFP4 target and BF16 DFlash2 draft loaded successfully;
- the quantized selector decode path was folded into the draft CUDA graph;
- target prefill, target verify, and draft verify CUDA graphs were captured;
- post-graph available GPU memory was about 11.75 GiB;
- `max_total_num_tokens` was 842,730 at the retained configuration;
- the container reached Docker `healthy` status.

For comparison, the previous DSpark runtime exposed about 3.14 GiB after its
startup path. The migration therefore increased operational memory headroom
despite adding the DFlash2 draft KV cache.

## Frozen-trace result

The replay command was identical for both arms except for the selected
SGLang env profile. Each arm processed 152 cold and 152 warm requests at
concurrency 4.

| Arm | Pass | Requests | Failures | Prompt tokens | Completion tokens | Wall time | Completion throughput |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DSpark | cold | 152 | 0 | 791,998 | 208,567 | 464.31 s | 449.2 tok/s |
| DFlash2 | cold | 152 | 0 | 791,998 | 207,592 | 381.34 s | 544.3 tok/s |
| DSpark | warm | 152 | 0 | 791,998 | 207,870 | 460.27 s | 451.6 tok/s |
| DFlash2 | warm | 152 | 0 | 791,998 | 209,594 | 387.80 s | 540.5 tok/s |
| DSpark | total | 304 | 0 | 1,583,996 | 416,437 | 924.58 s | 450.4 tok/s |
| DFlash2 | total | 304 | 0 | 1,583,996 | 417,186 | 769.14 s | 542.4 tok/s |

DFlash2 reduced cold wall time by 17.9%, warm wall time by 15.7%, and total
wall time by 16.8%. Its total completion throughput was 20.4% higher. Token
counts are reported rather than assumed identical because model generation is
not byte-deterministic across speculative implementations; both arms consumed
the exact same prompt trace and completed without HTTP failures.

The raw JSONL and summaries are local, ignored benchmark artifacts under
`reports/inference-ab/20260820-dflash2-migration/`. They can be regenerated
from the tracked trace and immutable inputs above.

## Contract and rollback verification

The retained DFlash2 service passed:

- `/v1/models` with served alias `qwen3.8-27b`;
- non-streaming and streaming chat completions;
- project-style regex-constrained choice output;
- thinking enabled and disabled with reasoning separated from final content;
- native Qwen tool-call parsing with valid function arguments;
- `/metrics`, including speculative verify counters;
- the complete 304-request cold/warm replay with zero failures.

The target-only profile was also recreated from its pinned base image, reached
`healthy`, and returned `TARGET_OK` through the external OpenAI-compatible API.
The DSpark rollback arm produced the baseline in the table before the switch.
After those checks, DFlash2 was restored and verified `healthy` using the
accepted image digest.

## Operations

Pull the official replacement:

```bash
docker pull lmsysorg/sglang@sha256:d6e7288627be8b02be88e4bba38e73f6d50e2826869f753c13a4c4385ab3eda9
```

Start or restore DFlash2:

```bash
docker compose --env-file .env --env-file config/sglang/dflash2.env \
  --profile local-sglang up -d --force-recreate --no-build sglang
```

Roll back to DSpark:

```bash
docker compose --env-file .env --env-file config/sglang/dspark.env \
  --profile local-sglang up -d --force-recreate --no-build sglang
```

Isolate speculative decoding:

```bash
docker compose --env-file .env --env-file config/sglang/target-only.env \
  --profile local-sglang up -d --force-recreate --no-build sglang
```

Do not use `docker compose down` for these transitions. Recreate only the
`sglang` service so unrelated project services remain untouched.

## Official-image acceptance gate

The source and image replacement is complete. Before treating new performance
evidence as equivalent to the historical local-bridge benchmark, rerun:

1. the focused upstream DFlash2 selector tests;
2. the repository Docker-runtime and LLM-client tests;
3. all API-contract smokes above;
4. the same frozen 304-request cold/warm replay;
5. an explicit rollback and restore check.
