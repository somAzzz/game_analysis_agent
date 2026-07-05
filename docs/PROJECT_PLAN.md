# 项目规划：开发侧 AI Agent 流水线

## 1. 项目定位

本项目建立一套服务于游戏研发的本地 AI Agent 流水线。Agent 的职责是读模拟报告、找数值和内容问题、提出调参建议，而不是在游戏运行时扮演 NPC。

核心原则：

- 先跑确定性模拟，再让 LLM 分析压缩后的报告。
- LLM 不直接消费全量 raw log，避免上下文浪费和不稳定判断。
- Agent 默认只输出建议，不自动修改游戏数据。
- 每次调参必须能 before/after 对比。
- 研发数据优先使用 JSONL、JSON、CSV、Markdown，方便 Python、LLM、Git diff 和人工审查。

## 2. 总体流水线

```text
Godot SimulationEngine
-> scripts/tools/RunBalanceSim.gd
-> reports/balance/<run_id>/raw_runs.jsonl
-> tools/analyze_balance.py
-> summary.json / csv / anomaly_report.md
-> tools/generate_agent_prompt.py
-> reports/balance/<run_id>/agent_prompt.md
-> tools/run_agent.py
-> agent_diagnosis.md / tuning_proposal.md
```

## 3. Agent 类型

### Balance Agent

职责：

- 分析不同 bot policy 的结局分布。
- 找过强、过弱、必选、无价值行动。
- 找属性曲线异常，例如压力无法回落、金钱过早崩盘。
- 判断是否存在多路线可行性。
- 输出带证据的调参建议。

输入：

- `summary.json`
- `ending_distribution.csv`
- `weekly_stats.csv`
- `action_pick_rates.csv`
- `event_trigger_rates.csv`
- `choice_pick_rates.csv`
- `anomaly_report.md`

输出：

- `agent_diagnosis.md`
- `tuning_proposal.md`

### Persona Agent

职责：

- 用玩家画像解释模拟结果。
- 判断学霸型、打工型、行政优先型、摆烂型等策略是否都有合理结局空间。
- 发现“唯一正确玩法”。

第一阶段先并入 Balance Agent，第二阶段拆独立报告。

### Content QA Agent

职责：

- 检查事件文本、选项重复、语气不一致、德国留学语境错误。
- 检查奖励惩罚是否和选项描述匹配。
- 输出事件级问题表。

### Event Graph Agent

职责：

- 检查 `next_event_id` 是否存在。
- 找不可达事件、断链、循环、条件矛盾。
- 输出 `event_graph_report.md`。

### Patch Suggestion Agent

职责：

- 基于诊断生成最小调参方案。
- 默认只生成 Markdown proposal。
- 只有显式授权时才生成 patch。

## 4. 里程碑

### Phase 0：项目骨架

交付物：

- 项目文档。
- 本地 vLLM 接入脚本。
- Agent Prompt 模板。
- 分析脚本。
- 报告目录规范。

完成标准：

- 可以在没有 Godot 项目的情况下阅读规划并运行 Python 脚本帮助信息。
- vLLM endpoint、model id、采样参数都可通过环境变量配置。

### Phase 1：纯模拟接口

Godot 项目需要提供：

```gdscript
func start_new_run(seed_value: int) -> void
func get_available_actions() -> Array
func simulate_week(action_ids: Array, event_choice_policy := "auto") -> Dictionary
func resolve_event_choice(event_id: String, choice_id: String) -> Dictionary
func is_finished() -> bool
func get_final_ending() -> Variant
func export_state_snapshot() -> Dictionary
```

完成标准：

```bash
godot4 --headless --path <game_project> -s res://scripts/tools/RunBalanceSim.gd --runs=10 --policy=random
```

能完整输出 JSONL。

### Phase 2：Monte Carlo 跑局

先实现 4 个 policy：

- `random`
- `balanced`
- `study`
- `money`

完成标准：

- 每个 policy 可跑 200-1000 局。
- 每局包含 `run_id`、`policy`、`seed`、`ending_id`、`final_state`、`weekly_log`。

### Phase 3：数值报告

生成：

- `summary.json`
- `ending_distribution.csv`
- `weekly_stats.csv`
- `action_pick_rates.csv`
- `event_trigger_rates.csv`
- `choice_pick_rates.csv`
- `anomaly_report.md`

完成标准：

- 不依赖 LLM 也能发现明显异常。
- 报告可以稳定复现。

### Phase 4：本地 LLM Agent

使用 vLLM + Qwen3.6 NVFP4 提供 OpenAI-compatible API。

完成标准：

- `tools/run_agent.py balance <report_dir>` 能读取报告并写出诊断。
- Agent 输出必须包含证据、建议、风险和最小改动方案。

### Phase 5：回归对比

完成 before/after 比较：

```text
baseline -> after_stress_patch -> after_admin_patch
```

完成标准：

- 每次调参都有版本化报告目录。
- 能输出关键指标变化。

### Phase 6：内容与事件图 QA

完成标准：

- 能扫描 `data/events.json` 或导出的事件图。
- 输出不可达事件、断链、循环、重复文本、dominant choice。

## 5. 项目节奏

推荐两周 Sprint：

### Sprint 1

- 完成 Godot 纯模拟接口。
- 接入 `RunBalanceSim.gd`。
- 跑通 `random` 和 `balanced`。

### Sprint 2

- 完成 Python 统计脚本。
- 输出第一版 baseline 报告。
- 接入 Balance Agent。

### Sprint 3

- 扩充 persona policies。
- 增加 action/event/choice 统计。
- 生成 tuning proposal。

### Sprint 4

- 数据外置为 JSON。
- 接 Content QA 和 Event Graph QA。
- 建立 before/after 回归机制。

## 6. 成功指标

工程指标：

- 一条命令跑完 baseline。
- 报告可复现。
- Agent 输出可追溯到具体数字。
- 调参前后可以量化比较。

游戏设计指标：

- `BalancedBot` 好结局率合理。
- `RandomBot` 不应轻松通关。
- 专精策略有优势也有代价。
- 没有单一行动成为永久必选项。
- 事件触发覆盖率持续提高。
- 结局覆盖率从低覆盖逐步提高到主要结局都可达。
