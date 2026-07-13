# 本地 vLLM + Qwen3.6 NVFP4 接入

## 1. 运行方式

本项目通过 vLLM 的 OpenAI-compatible HTTP server 调用本地模型。vLLM 文档说明该 server 支持 `/v1/chat/completions` 等 OpenAI 风格接口，并可通过 `vllm serve` 启动。

参考：

- vLLM OpenAI-Compatible Server: https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/
- vLLM Quantization: https://docs.vllm.ai/en/latest/features/quantization/

## 2. 推荐环境变量

```bash
export MODEL_ID=/models/qwen3.6-nvfp4
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_API_KEY=local-dev-token
```

`MODEL_ID` 应使用你本机真实存在的 Hugging Face repo id 或本地模型路径。Qwen3.6 NVFP4 的公开仓库名、分支和量化格式可能随发布渠道变化；这里不在代码中硬编码不可验证的模型地址。

## 3. 启动服务

```bash
MODEL_ID=/models/qwen3.6-nvfp4 ./tools/run_vllm_qwen.sh
```

脚本默认参数：

```text
host: 127.0.0.1
port: 8000
dtype: auto
max model len: 32768
gpu memory utilization: 0.9
generation config: vllm
```

## 4. NVFP4 注意事项

- NVFP4 主要面向支持 FP4 的新 GPU，尤其是 NVIDIA Blackwell 级别硬件。
- 若当前 vLLM 版本或硬件不支持目标 checkpoint，可先用 BF16、FP8、AWQ、GPTQ 或 MXFP4 兼容模型跑通流程。
- Agent 管线本身和量化格式解耦，只要求 endpoint 兼容 `/v1/chat/completions`。

## 5. Agent 调用协议

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
