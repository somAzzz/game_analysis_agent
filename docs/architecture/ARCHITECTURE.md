# 系统架构

## 1. 分层

```text
Game Project (Godot)
  SimulationEngine
  DataRegistry
  GameState
  RunSimulation.gd               (Monte Carlo)
  scripts/tools/AnomalyCollector.gd
  scripts/tools/ExportEventGraph.gd
  scripts/tools/RunBoundaryProbe.gd
  scripts/tools/RunInteractiveProbe.gd

Analysis Project (this repo)
  raw log contract
  deterministic analytics        (game_analysis_agent.analytics)
  anomaly detection              (game_analysis_agent.anomaly_detector)
  value analysis                 (game_analysis_agent.value_analyzer)
  bug summarizer                 (game_analysis_agent.bug_summarizer)
  prompt generation              (game_analysis_agent.report_bundle)
  LLM client                     (game_analysis_agent.llm_client)
  tool loop                      (game_analysis_agent.tool_loop)
  game tools                     (game_analysis_agent.game_tools)
  agents                         (game_analysis_agent.agents)
  proposal artifacts             (markdown + jsonl)

Local Model Runtime
  vLLM OpenAI-compatible server   (default)
  SGLang OpenAI-compatible server (alternative)
  DeepSeek public API             (cloud fallback)
  Qwen3.6 NVFP4 checkpoint       (target)
```

## 2. 关键边界

### Godot 负责

- 按 seed 跑完整游戏。
- 选择 policy 行动。
- 输出完整但结构稳定的 JSONL。
- 保证同 seed 同数据同结果。
- 暴露事件、行动、终局定义（用于 `ExportEventGraph.gd`）。

### Python 分析层负责

- 汇总结局分布。
- 统计每周属性曲线。
- 统计行动、事件、选项频率。
- 不变量检测 + 重复事件检测 + 死局检测 + 突变检测。
- 必选 / 死选 / 偏向 / 终局单一化检测。
- 生成 anomaly report / value report。
- 压缩 Agent 输入。

### LLM Agent 负责

- 解释报告。
- 找设计问题。
- 提调参建议。
- 标注风险。
- 生成最小 patch proposal。
- 当玩家"试玩"并记录决策合理性。

### 人类负责

- 审核建议。
- 决定是否改数据。
- 评价改动是否符合设计意图。

## 3. 为什么不让 LLM 直接跑局

LLM 直接玩 1000 局会慢、昂贵、难复现，并且判断容易被单局叙事带偏。确定性 bot 加统计
报告更适合数值平衡；LLM 最适合在压缩报告上做诊断和建议。但 LLM *可以* 当玩家跑一
两个完整 playthrough —— 这正是 `interactive_player` agent 的角色。

## 4. 目录职责

```text
config/
  Agent 配置、角色定义、policy 元信息。

docs/
  项目规划、接口、数据契约、新 agent 类型说明。

prompts/
  各类 Agent 的 system / user prompt 模板。

scripts/tools/
  放入 Godot 项目的 GDScript 工具（RunBoundaryProbe / ExportEventGraph /
  RunInteractiveProbe / AnomalyCollector / RunBalanceSim stub）。

src/game_analysis_agent/
  Python agent client、分析、报告读取逻辑。

tools/
  可直接运行的 CLI 脚本（run_gameplay_agent.py / run_agent.py /
  analyze_balance.py / generate_agent_prompt.py / run_balance_sim.sh /
  run_vllm_qwen.sh）。

reports/
  模拟输出和 Agent 输出。
```

## 5. 安全策略

- 默认不自动写游戏项目文件。
- Agent 输出 proposal，不直接 patch。
- raw log 不进模型，只进统计层。
- 所有报告目录带 run id，方便回滚和对比。
- 本地 vLLM 只绑定本机或内网可信地址。
- `interactive_player` 通过 subprocess 调用 Godot runner，不直接写游戏项目源码。