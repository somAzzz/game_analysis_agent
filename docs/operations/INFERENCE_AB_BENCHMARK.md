# APC-only versus MTP3-only inference benchmark

Status: server profiles and experiment contract are tracked; the runner and renderer are the
next implementation unit. This plan does not restart the current GPU service by itself.

## Decision and scope

Keep this benchmark in the current repository. The comparison depends on this project's exact
chat template inputs, persona history order, JSON validation, repair behavior, Docker image pin,
and campaign scheduling. Moving it to another repository would duplicate those contracts and
make prompt or runtime drift likely.

Add a separate repository only if the benchmark becomes a general product with its own release
cycle, supports unrelated models/engines/games, or needs an independently deployed Prometheus and
Grafana stack. None of those conditions applies to the first APC/MTP decision.

The recommended code boundary is an isolated package rather than more logic in the persona
gateway:

```text
src/game_analysis_agent/inference_benchmark/
  contracts.py       # immutable plan, run manifest, request and summary schemas
  trace.py           # capture/redact/hash exact serialized chat requests
  runner.py          # profile restart, health gate, scheduling and collection
  metrics.py         # request, Prometheus and nvidia-smi normalization
  analysis.py        # paired deltas, percentiles and bootstrap intervals
  render.py          # self-contained HTML plus SVG charts
tools/run_inference_ab.py
tools/render_inference_ab.py
tests/test_inference_benchmark_*.py
```

The runner should call transport-independent functions from that package. It must not put
benchmark branches in `LocalChatPersonaGateway` or change production prompt content.

## Tracked server profiles

Arm A, APC-only:

```bash
docker compose \
  --env-file config/inference_ab/apc_only.env \
  --profile local-nvidia up -d --force-recreate vllm
```

```text
enable_prefix_caching = true
mamba_cache_mode = align
prefix_match_unit = 16
MTP = false
```

Arm B, MTP3-only:

```bash
docker compose \
  --env-file config/inference_ab/mtp3_only.env \
  --profile local-nvidia up -d --force-recreate vllm
```

```text
enable_prefix_caching = false
MTP = true
num_speculative_tokens = 3
```

Every other server parameter is identical: vLLM 0.26.0, Qwen3.6 27B NVFP4, ModelOpt,
`max_model_len=65536`, `max_num_seqs=4`, GPU memory utilization 0.9, one GPU, and the
same generation parameters. The Compose and host launchers both read
`LLM_MTP_NUM_SPECULATIVE_TOKENS`; the default remains 3.

Never run the two profiles at the same time on one GPU. Restart between arms so Prometheus
counters, KV state, allocator state, and model mode do not leak across observations.

## What the A/B result means

APC and MTP optimize different stages:

- APC avoids repeated prefill work and should primarily improve warm-prefix TTFT and prompt
  throughput.
- MTP speculates multiple decode tokens and should primarily improve TPOT, inter-token latency,
  and generation throughput when enough output tokens are produced and drafts are accepted.

Therefore there is no workload-independent answer to "which is faster." The primary decision is:

> Which mutually exclusive profile completes more governed persona weeks per wall-clock hour in
> each long-horizon scenario without violating structured-output and gameplay-contract guardrails?

The two-arm result chooses the operational default. If causal attribution is required, add a
diagnostic third arm with both APC and MTP disabled. That control estimates each optimization's
gain over the same base engine, but is not required to choose between A and B.

## Experimental design

The machine-readable source of truth is
`config/inference_ab/plan.yaml`.

### 1. Freeze the environment

Record in `manifest.json`:

- repository commit and dirty status;
- Docker image id/digest and full resolved vLLM command;
- model id and revision;
- GPU model, driver, CUDA, clocks, power limit and persistence mode;
- common server parameters and profile env-file SHA-256;
- request-trace SHA-256;
- start/end timestamps and arm order.

Use the GPU exclusively. Do not run a campaign, browser GPU workload, or another inference
service during measurement. Do not change clocks or power limit between arms.

### 2. Use balanced ordering and restarts

The live decision workload has two separate scheduling scenarios:

| Scenario | Cells in each arm | Question isolated |
|---|---:|---|
| same persona, multiple seeds | newbie × seeds 42, 43, 44, 45 | How much does APC gain when persona policy is shared but histories diverge? |
| different personas, one seed | newbie, study, money, social × seed 42 | How much reuse survives when persona policy and history differ? |

Newbie is the project's configured default persona, so it anchors the repeated-persona scenario.
Social remains in the diverse cohort and covers the longest prompt/output tail seen in the retained
six-persona campaign.

Newbie/seed 42 is logically present in both scenarios, so there are seven unique persona/seed
pairs per arm. It must still run twice because its neighboring requests and cache state differ;
the physical workload is eight semester cells per arm and sixteen per repetition.

The project defines the complete first-semester cap as `max_weeks=20`, commonly with 19 decisions
before the resulting state reaches week 20. The user requirement is enforced as
`minimum_completed_weeks=18`; a shorter cell invalidates that paired repetition and is never
silently replaced.

Run each scenario three times with opposite ordering:

```text
same persona:       A→B, B→A, A→B
different personas: B→A, A→B, B→A
```

For each scenario/arm session:

1. force-recreate vLLM and reset all counters and cache state;
2. wait for health and capture the resolved configuration;
3. send 20 excluded warmups whose prefix cannot match measured prompts;
4. run the four cells at concurrency 4, sequential within each cell;
5. snapshot Prometheus, GPU and sanitized campaign evidence before the next restart.

This is twelve server sessions. The worst-case budget is
`8 cells/arm × 2 arms × 20 weeks × 2 calls/week × 3 repetitions = 1,920 model calls`.

### 3. Frozen-trace causal control

Fresh temperature-0.3 campaigns can take different legal actions in the two arms. That divergence
is valid operational evidence, but later requests are no longer byte-identical and cannot isolate
engine performance by themselves.

Capture sanitized, post-chat-template requests from the completed long-horizon campaign, freeze
their JSONL hash, and replay the identical bodies through both arms. Preserve per-cell order.
Measure concurrency 1 and 4 and cold/warm passes. The trace never replaces the fresh Godot
campaign and must be labelled a performance replay, not fresh gameplay evidence.

The frozen trace is the request-level paired proof; the live campaign remains the default decision.

### 4. Diagnostic matrix

Use deterministic synthetic prompts to explain the production result:

| Parameter | Values |
|---|---|
| Prompt tokens | 512, 2048, 4096 |
| Forced output tokens | 32, 96, 256, 768 |
| Concurrency | 1, 4 |
| Requests per cell | 20 |
| Temperature | 0 |
| Seed | 42 |
| EOS | ignored for fixed output length |

The long-horizon campaign decides the default; the synthetic matrix only shows where the crossover
between prefill and decode occurs. vLLM's benchmark client already reports TTFT, TPOT, ITL and
E2E percentiles and can support this diagnostic sweep. See the official
[vLLM bench serve reference](https://docs.vllm.ai/en/v0.26.0/cli/bench/serve/).

### 5. Optional expansion gates

Do not pay for the larger matrix by default. If the two core scenarios disagree or the practical
effect interval includes zero, run one 4-persona × 4-seed crossed confirmation per arm
(32 physical cells across both arms, 1,280 worst-case calls). This reduces dependence on choosing
Newbie and seed 42 as the two anchors.

If a repository-wide default survives the core and frozen-trace gates, run a final edge-persona
holdout with Visa and Slacker over seeds 1042 and 2042 (eight physical cells across both arms,
320 worst-case calls). Visa exercises administration-heavy choices; Slacker preserves a designed
failure style. This holdout checks robustness and does not replace the core performance estimate.

## Metrics

### Primary and latency metrics

| Metric | Use |
|---|---|
| Completed persona weeks per wall-clock hour | Primary operational winner, reported per scenario |
| Semester wall time per physical cell | Paired long-horizon effect |
| Request throughput and goodput | Capacity under concurrency 4 |
| TTFT p50/p90/p95/p99 | Prefill and queueing effect |
| TPOT p50/p90/p95/p99 | Decode efficiency |
| Inter-token latency p50/p95/p99 | Streaming smoothness |
| E2E p50/p90/p95/p99 | User-visible latency |
| Prompt and generation tokens/s | Stage-specific throughput |
| TTFT/E2E slope by week | Whether growing history strengthens APC over weeks 1–20 |
| Wh per completed semester | Energy efficiency including both prefill and decode |

### Mechanism utilization

For APC, collect queried tokens, cached tokens, locally computed prompt tokens, hit ratio, and hit
ratio by cold/warm pass. Do not use hit ratio alone as the winner metric.

For MTP, collect accepted tokens, drafted tokens, drafts, per-position acceptance and:

```text
acceptance_rate = accepted_tokens / drafted_tokens
mean_acceptance_length = 1 + accepted_tokens / drafts
```

These are the formulas documented by the official
[vLLM speculative-decoding metrics](https://docs.vllm.ai/en/stable/api/vllm/v1/spec_decode/metrics/).

Also sample KV-cache usage, running/waiting requests, preemptions, GPU utilization, memory,
power, SM clock and integrated energy. vLLM exposes its server counters from `/metrics`, which
is intended for Prometheus-style collection and visualization; see
[vLLM metrics](https://docs.vllm.ai/en/stable/design/metrics/).

### Correctness guardrails

Performance results are invalid unless:

- request success rate is 100%;
- final valid structured-decision rate is 100%;
- every cell completes at least 18 weeks and the completed-cell rate is 100%;
- provider error rate is zero;
- fallback and schema-repair rates are zero;
- legal-action violation rate is zero;
- length-finished responses are at most 0.5%;
- frozen-trace arms use exact request fingerprints and token budgets.

Do not require identical natural-language reasoning at temperature 0.3. Compare contract
validity, legal ids, finish reasons and length distributions. Pair fresh campaigns by scenario,
persona, seed and repetition; pair frozen traces by request fingerprint. The deterministic
diagnostic track uses temperature 0 and may additionally compare exact output hashes.

## Statistics and winner rule

For fresh campaigns, pair by scenario/persona/seed/repetition and report absolute values, paired
percentage deltas and a hierarchical 95% bootstrap interval across repetitions and cells. For the
frozen trace, pair by request fingerprint. Also report:

- `same_persona_speedup` and `different_persona_speedup` separately;
- their difference-in-differences interaction, which estimates how much extra benefit comes from
  same-persona prefix similarity;
- latency and mechanism utilization by week, phase and output-length bucket.

Choose one repository-wide default only when every correctness guardrail passes, both live
scenarios point in the same direction with at least 5% practical improvement, the frozen-trace 95%
interval excludes zero in that direction, and no p95 latency or energy guardrail materially
regresses. If the two scenarios disagree, publish scenario-specific winners and report no global
winner.

Otherwise report "no practical winner" and retain stage-specific findings such as "APC improves
warm TTFT while MTP improves long-output TPOT." This is more useful than forcing one global
conclusion from a mixed workload.

## Required visualization

Generate one self-contained `comparison.html` plus SVG charts:

1. campaign throughput by scenario: weeks/hour and semester wall time with paired cell lines;
2. week trend: TTFT, TPOT and E2E from week 1 through 20 for both scenarios;
3. latency percentiles: grouped p50/p95/p99 TTFT, TPOT and E2E;
4. stage decomposition: TTFT versus decode time, split by scenario, phase and concurrency;
5. workload heatmap: B-versus-A E2E delta across prompt/output-length cells;
6. mechanism utilization: APC cached-token ratio and MTP acceptance by week/output length;
7. quality guardrails: completion, valid, repair, fallback, error and length-finish rates;
8. resource timeline: GPU utilization, power, energy, KV usage, running and waiting requests.

Every chart must show units, sample count, arm configuration, repetition spread and confidence
interval where applicable. Write raw request rows, normalized summaries and chart-ready CSV next
to the HTML under `reports/inference-ab/<run-id>/`; reports remain local and ignored by Git.

## Implementation order

1. Land and validate the two profile files and the plan contract.
2. Implement immutable Pydantic contracts and exact request-trace capture.
3. Implement the runner with restart, health, Prometheus and GPU collection.
4. Implement paired aggregation and guardrail evaluation.
5. Implement HTML/SVG rendering.
6. Run a 2-cell smoke, then one repetition of both scenarios, then the full twelve-session
   experiment only if every long-horizon completeness gate passes.
7. Freeze the report manifest before interpreting the result.
