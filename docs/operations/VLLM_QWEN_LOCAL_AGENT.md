# 本地 vLLM + Qwen3.6 NVFP4 接入

## 1. 运行方式

本项目通过 vLLM 的 OpenAI-compatible HTTP server 调用本地模型。vLLM 文档说明该 server 支持 `/v1/chat/completions` 等 OpenAI 风格接口，并可通过 `vllm serve` 启动。

参考：

- vLLM OpenAI-Compatible Server: https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/
- vLLM Quantization: https://docs.vllm.ai/en/latest/features/quantization/

## 2. 推荐环境变量

```bash
export MODEL_ID=nvidia/Qwen3.6-27B-NVFP4
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_API_KEY=local-dev-token
```

`MODEL_ID` 应使用你本机真实存在的 Hugging Face repo id 或本地模型路径。Qwen3.6 NVFP4 的公开仓库名、分支和量化格式可能随发布渠道变化；这里不在代码中硬编码不可验证的模型地址。

## 3. 启动服务

```bash
MODEL_ID=nvidia/Qwen3.6-27B-NVFP4 ./tools/run_vllm_qwen.sh
```

脚本默认参数：

```text
host: 127.0.0.1
port: 8000
dtype: auto
max model len: 65536
max sequences per scheduler iteration: 4
prefix caching: enabled
hybrid Mamba cache mode: align
prefix match unit: 16
MTP speculative decoding: disabled by default
text-only model path: enabled
gpu memory utilization: 0.9
generation config: vllm
```

## 4. 项目默认容量与并行语义

当前默认运行档位是：

```text
model native context: 262144
operational max model len: 65536
continuous-batching max sequences: 4
tensor / pipeline / data parallel: 1 / 1 / 1
KV cache dtype: vLLM auto（当前 Blackwell 实例解析为 fp8_e4m3）
prefix caching: enabled
hybrid prefix match unit: 16
MTP speculative decoding: disabled
max num batched tokens: auto
```

`--max-model-len` 同时包含 prompt 与 output。`--max-num-seqs=4` 是单个 vLLM engine 每次调度可处理的最大序列数，不是四份模型，也不是 TP/PP/DP。`--max-num-batched-tokens` 是单次 scheduler iteration 的处理预算，不等于单请求上下文；项目默认留空，由 vLLM 调整，需要吞吐基准时再单独覆盖。

建议档位：

| 用途 | max model len | max sequences |
|---|---:|---:|
| 常规 persona campaign | 65536 | 4 |
| 长历史深度审计 | 131072 | 2 |
| 极端单请求诊断 | 262144 | 1 |

项目只有文本 persona 输入，因此启用 `--language-model-only`，跳过视觉编码器与多模态 profiling，把显存留给 KV cache。

本机 RTX PRO 6000 Blackwell 96GB 实测：text-only 后 GPU KV cache 为 1,403,172 tokens，65,536-token 请求的 vLLM 理论最大并发为 21.41；四个互不共享前缀的 24,022-token 请求在 23.52 秒内全部完成。这个 smoke test 证明当前 4 × 24K 档位可运行，但不是 4 × 64K 的延迟 SLA。

## 5. Thinking、最终选择和历史边界

本地 Qwen persona 的第一次决策调用开启 thinking；`reasoning` 与 `message.content` 分开读取。系统只对最终 `content` 做 JSON 提取、Pydantic 校验和合法 id 校验。若模型只产生 reasoning、没有最终 JSON，会执行唯一一次有界 repair，并在 repair 中关闭 thinking。默认预算为：

- 每周动作决策：2048 output tokens（包含 reasoning 与最终 JSON）
- 事件选择：768 output tokens（包含 reasoning 与最终 JSON）

原始 reasoning 不写入 playthrough、不进入下一周上下文，也不参与判分；审计只保留是否存在、字符数和 SHA-256。这样可以观测 thinking 是否发生，又不会把私有推理当成游戏动作或改变后续测试。

每周决策会看到全部可观察历史：历周状态前后快照、实际动作、事件选项和结果，再看到本周当前状态。完整历史能保留跨周策略、失败恢复和路径依赖；只给当前状态会把 persona 降成无记忆贪心策略。

本地 chat template 序列化前的逻辑顺序固定为：

```text
稳定 system 指令
稳定全局规则 + PlayerDecision/event 输出 schema
persona strategy
不可变、只追加的历周 history
当前 memory summary + week/state/risks/event
本周 max_action_slots + 当前合法 action/choice 完整对象
本轮任务
```

APC 比较 chat template 产生的最终 token 前缀；message 数量本身不是命中条件，但 role 和 message 边界也会产生 token。vLLM 的 block key 同时依赖当前 token 块及其父前缀，因此前面第一次变化以后，后面即使重新出现相同 JSON 也不能越过分叉点复用。把固定 schema 放在最前面，使所有 persona 先共享规则；把 history 放在每周重算的 summary/state 之前，使同一 persona 的下一周能复用先前不可变的历史 token。

`available_actions` 和 `event_choices` 必须是本轮实际合法、可观察的完整对象，并故意放在动态后缀。不能为了制造更长缓存前缀而改成全局 action catalog：全局 catalog 可能暴露未解锁 action、requirements 或未来路线，改变 persona 的长期规划和 risk awareness，导致新的 playthrough 与既有 evidence contract 不再可比。这个布局只改变序列位置，不增加或删减模型可观察事实；服务端合法 id 校验仍以同一个 `WeekContext` 为准。

项目固定到 vLLM 0.26.0，并显式使用 `--mamba-cache-mode align --prefix-match-unit 16`。细粒度 match unit 允许命中物理 hybrid cache block 内的共享前缀，缓解旧版本短前缀因大块对齐而完全不命中的问题。GDN/Mamba APC 在上游仍标记为 experimental，因此它只是经过监控的 prefill 优化，不是 correctness 或容量前提；APC 开关不得改变合法选择或测试结果。

评估这项布局时不能只看 APC hit ratio。固定内容变长会机械性提高 cached-token 占比；验收必须在相同请求顺序下同时比较 prompt tokens、未缓存 prefill、TTFT、prefill/E2E latency、KV eviction、JSON repair/fallback 和 persona 选择。命中率提升没有预设的 30%–50% 保证。

事件选择采用同一原则：固定 event 输出规则在前，persona/history 居中，当前 event choices 放在最后。事件 prompt 较短，所以它的优化优先级低于每周 action decision。

MTP 默认关闭。现有本地证据中，5,700 次成功调用消耗 11,109,541 input tokens、335,195 output tokens，且最终输出是短 JSON，因此常规 campaign 优先减少重复 prefill。只有长输出专项基准才应设置 `LLM_ENABLE_MTP=1`，并先完成 APC/MTP 分离 A/B、结构化输出一致性检查和持续负载测试。

## 6. NVFP4 注意事项

- NVFP4 主要面向支持 FP4 的新 GPU，尤其是 NVIDIA Blackwell 级别硬件。
- 若当前 vLLM 版本或硬件不支持目标 checkpoint，可先用 BF16、FP8、AWQ、GPTQ 或 MXFP4 兼容模型跑通流程。
- Agent 管线本身和量化格式解耦，只要求 endpoint 兼容 `/v1/chat/completions`。

## 7. Agent 调用协议

请求：

```json
{
  "model": "${MODEL_ID}",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.2,
  "max_tokens": 4096
}
```

输出文件：

```text
agent_diagnosis.md
tuning_proposal.md
content_issues.md
event_graph_report.md
```
