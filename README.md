# game_analysis_agent

面向 Godot 数值模拟游戏的开发侧 AI Agent 流水线。本项目把"试玩 / 边界 / Bug / 数值"分析自动化：
让 LLM 在压缩报告、异常检测和工具调用之上产生诊断，而不是把 LLM 塞进游戏运行时当 NPC。

```text
Godot headless simulation
  ├─ RunSimulation.gd           (Monte Carlo via study-in-germany)
  ├─ RunBoundaryProbe.gd        (extreme-scenario probing)
  ├─ ExportEventGraph.gd        (event / action / ending catalog)
  └─ RunInteractiveProbe.gd     (driven by the interactive player)
        │
        ▼
Python analysis layer
  ├─ analytics.py               (ending / weekly / pick / event / choice stats)
  ├─ anomaly_detector.py        (invariant + repeat + dead-state + spike detection)
  ├─ value_analyzer.py          (dominant / dead actions, choice bias, ending lock-in)
  └─ bug_summarizer.py          (anomaly → markdown)
        │
        ▼
LLM agent layer (provider: vllm | sglang | deepseek)
  ├─ balance                    (existing) — diagnose ending distribution + tuning
  ├─ content_qa                 (existing) — review event text + choices
  ├─ event_graph                (existing) — audit trigger graph
  ├─ bug_hunter                 (new) — review anomalies + raw runs → bug_diagnosis.md
  ├─ boundary_prober            (new) — review extreme runs → boundary_report.md
  ├─ value_reviewer             (new) — review value_report.json → value_review.md
  └─ interactive_player         (new) — drive the simulator with tool calls
```

默认 LLM 通过 vLLM OpenAI-compatible server 接入，模型目标为 Qwen3.6 NVFP4。实际仓库名
或本地路径通过环境变量配置，方便替换为你机器上已经下载好的 checkpoint。

## 快速开始

### 方式 A：Docker（推荐，vLLM + agent 一体化）

```bash
cp .env.example .env
# 编辑 .env 填 HF_TOKEN / GAME_PROJECT_PATH 等
docker compose pull vllm
docker compose up vllm -d
docker compose logs -f vllm           # 等待 "Application startup complete"
docker compose --profile cli run --rm agent all --runs 20 --policy balanced
```

详见 [docs/DOCKER.md](docs/DOCKER.md)。该方式会在本地启动一个
vLLM v0.24.0 容器（默认服务 NVIDIA 官方 Qwen3.6 27B NVFP4 + MTP
投机解码），然后按需启动一个不带 GPU 的 agent CLI 容器跑流水线。

### 方式 B：本地 Python + 已有 vLLM endpoint

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 安装依赖（推荐使用 `uv` / `pip` + virtualenv）：

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

3. 启动本地 vLLM 服务（如果你用的是 `deepseek` 则可跳过）：

```bash
MODEL_ID=/path/to/qwen3.6-nvfp4 ./tools/run_vllm_qwen.sh
```

4. 一键跑通整个流水线（跑 20 局 + 分析 + 全部 agent）：

```bash
python3 tools/run_gameplay_agent.py all --runs 20 --policy balanced
```

   这条命令会输出到：

   ```text
   reports/balance/<run_id>/raw_runs.jsonl
   reports/balance/<run_id>/summary.json
   reports/balance/<run_id>/ending_distribution.csv
   reports/balance/<run_id>/weekly_stats.csv
   reports/balance/<run_id>/action_pick_rates.csv
   reports/balance/<run_id>/event_trigger_rates.csv
   reports/balance/<run_id>/choice_pick_rates.csv
   reports/balance/<run_id>/anomalies.jsonl
   reports/balance/<run_id>/bugs.jsonl
   reports/balance/<run_id>/bugs_summary.md
   reports/balance/<run_id>/value_report.json
   reports/balance/<run_id>/agent_diagnosis.md
   reports/balance/<run_id>/tuning_proposal.md
   reports/balance/<run_id>/content_issues.md
   reports/balance/<run_id>/event_graph_report.md
   reports/balance/<run_id>/bug_diagnosis.md
   reports/balance/<run_id>/value_review.md
   ```

5. 单独运行其它子命令：

```bash
# 仅模拟 + 分析（不调 LLM）
python3 tools/run_gameplay_agent.py sim --runs 100 --policy random
python3 tools/run_gameplay_agent.py analyze --report-dir reports/balance/baseline

# 边界探测（需要 Godot + GAME_PROJECT_PATH 指向 study-in-germany）
python3 tools/run_gameplay_agent.py probe --extreme "zero_money,deep_debt,flag_chaos"

# 让 LLM 当玩家试玩
python3 tools/run_gameplay_agent.py play --report-dir reports/play/test --weeks 20

# 仅跑某个 agent（如果只想看一份诊断）
python3 tools/run_agent.py balance reports/balance/baseline
```

## 目录结构

```text
config/
  agent_profiles.yaml           — agent 配置（system_prompt / user_prompt / output_files / temperature）

docs/
  ARCHITECTURE.md
  DATA_CONTRACTS.md
  GAMEPLAY_AGENT.md             — 新 agent 类型说明
  GODOT_INTEGRATION.md
  INTEGRATION_WITH_STUDY_IN_GERMANY.md
  PROJECT_PLAN.md
  VLLM_QWEN_LOCAL_AGENT.md

prompts/
  balance_agent_{system,user}.md
  bug_hunter_{system,user}.md
  boundary_prober_{system,user}.md
  content_qa_agent_{system,user}.md
  event_graph_agent_{system,user}.md
  player_{system,user}.md
  value_reviewer_{system,user}.md

scripts/tools/
  RunBalanceSim.gd              — deprecated stub; 真实跑局见 study-in-germany/RunSimulation.gd
  AnomalyCollector.gd           — 镜像 Python 不变量检测，给 boundary_runs 附带轻量标记

src/game_analysis_agent/
  __init__.py
  env.py                        — .env loader
  settings.py                   — Settings dataclass + get_settings()
  schemas.py                    — Pydantic LLMCall / Anomaly / Finding
  llm_client.py                 — OpenAI-compatible client with provider switching + audit
  tool_loop.py                  — OpenAI-compatible tool-calling loop
  analytics.py                  — 纯统计函数
  anomaly_detector.py           — 不变量 / 重复 / 死局 / 突变检测
  value_analyzer.py             — 必选 / 死选 / 偏向 / 终局单一化检测
  bug_summarizer.py             — anomalies → Markdown
  game_tools.py                 — OpenAI tools + Godot subprocess wrappers
  agents/
    base.py                     — Agent 抽象基类
    balance.py
    content_qa.py
    event_graph.py
    bug_hunter.py
    boundary_prober.py
    value_reviewer.py
    interactive_player.py

tests/                          — 单元测试 + fixture
tools/
  analyze_balance.py            — CLI 入口，拆出业务逻辑到 analytics.py
  generate_agent_prompt.py
  run_agent.py                  — 单个 agent CLI
  run_balance_sim.sh            — 包装 study-in-germany 的 RunSimulation.gd
  run_gameplay_agent.py         — 一站式 orchestration CLI
  run_vllm_qwen.sh
```

## 项目文档

- [完整项目规划](docs/PROJECT_PLAN.md)
- [系统架构](docs/ARCHITECTURE.md)
- [新 agent 类型说明](docs/GAMEPLAY_AGENT.md)
- [与 study-in-germany 的集成约定](docs/INTEGRATION_WITH_STUDY_IN_GERMANY.md)
- [Docker 部署](docs/DOCKER.md)
- [Godot 接入规范](docs/GODOT_INTEGRATION.md)
- [本地 vLLM + Qwen 接入](docs/VLLM_QWEN_LOCAL_AGENT.md)
- [数据与报告规范](docs/DATA_CONTRACTS.md)

## 当前状态

- ✅ Settings + 三 provider 切换（vllm / sglang / deepseek）
- ✅ Pydantic 审计 + 不变量 / 重复 / 死局 / 突变检测
- ✅ 7 个 agent（balance, content_qa, event_graph, bug_hunter, boundary_prober,
  value_reviewer, interactive_player）
- ✅ Tool-calling loop（OpenAI 兼容 + JSON fallback helper）
- ✅ 3 个新 Godot 工具（RunBoundaryProbe / ExportEventGraph / RunInteractiveProbe）
- ✅ 一键 `run_gameplay_agent.py all` orchestration CLI
- ✅ 62 个单元测试 + fixtures

要真正跑通端到端流水线，需要：

1. 一台能跑 Godot 4 的机器（`godot4 --headless`）。
2. 一份 `study-in-germany` checkout（GAME_PROJECT_PATH）。
3. 本地 vLLM / SGLang / DeepSeek 任意一个 endpoint。

缺任何一个，Python 侧仍然能跑：analytics / anomaly_detector / value_analyzer / tests
全部基于本地 fixture 自测。