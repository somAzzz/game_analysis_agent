# analyse_agent

面向 Godot 数值模拟游戏的开发侧 AI Agent 流水线。

本项目的目标不是把 LLM 放进游戏运行时当 NPC，而是建立一条研发外循环：

```text
Godot headless simulation
-> JSONL / CSV reports
-> deterministic analytics
-> local LLM agent review
-> diagnosis and tuning proposal
-> human review
```

本地 LLM 默认按 vLLM OpenAI-compatible server 接入，模型目标为 Qwen3.6 NVFP4。实际模型仓库名或本地路径通过环境变量配置，方便替换为你机器上已经下载好的 checkpoint。

## 快速开始

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 启动本地 vLLM 服务：

```bash
MODEL_ID=/path/to/qwen3.6-nvfp4 ./tools/run_vllm_qwen.sh
```

3. 从 Godot 项目导出跑局日志，目标格式见 [docs/GODOT_INTEGRATION.md](/Users/bo/projects/analyse_agent/docs/GODOT_INTEGRATION.md)。

4. 分析原始日志：

```bash
python3 tools/analyze_balance.py reports/balance/baseline/raw_runs.jsonl reports/balance/baseline
```

5. 生成 Agent 输入：

```bash
python3 tools/generate_agent_prompt.py reports/balance/baseline
```

6. 调用本地 LLM Agent：

```bash
python3 tools/run_agent.py balance reports/balance/baseline
```

输出会写入：

```text
reports/balance/baseline/agent_diagnosis.md
reports/balance/baseline/tuning_proposal.md
```

## 项目文档

- [完整项目规划](/Users/bo/projects/analyse_agent/docs/PROJECT_PLAN.md)
- [系统架构](/Users/bo/projects/analyse_agent/docs/ARCHITECTURE.md)
- [本地 vLLM + Qwen 接入](/Users/bo/projects/analyse_agent/docs/VLLM_QWEN_LOCAL_AGENT.md)
- [Godot 接入规范](/Users/bo/projects/analyse_agent/docs/GODOT_INTEGRATION.md)
- [数据与报告规范](/Users/bo/projects/analyse_agent/docs/DATA_CONTRACTS.md)

## 当前状态

这是 Agent 流水线项目骨架。它已经包含规划、配置、Prompt、分析脚本和本地 LLM 调用器；Godot 侧需要在你的游戏项目内实现 `SimulationEngine` 纯模拟接口和 `RunBalanceSim.gd`。
