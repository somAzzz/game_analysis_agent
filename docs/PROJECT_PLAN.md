# 项目规划：开发侧 AI Agent 流水线

## 1. 项目定位

本项目建立一套服务于游戏研发的本地 AI Agent 流水线。Agent 的职责是：

1. 驱动 Godot 跑大量 Monte Carlo 模拟。
2. 探测游戏边界（极端初始状态）。
3. 自动找 bug（不变量 / 重复 / 死局 / 突变）。
4. 分析数值合理性（必选 / 死选 / 偏向 / 终局单一化）。
5. 让 LLM 当玩家"试玩"，发现隐藏路径。
6. 输出人类可读的 Markdown 诊断 + 机器可读的 JSONL 工件。

Agent **不是**游戏运行时 NPC。本项目不修改 `study-in-germany` 的运行时，只读 + 报告。

核心原则：

- 先跑确定性模拟 + 确定性检测，再让 LLM 分析压缩报告。
- LLM 不直接消费全量 raw log，避免上下文浪费和不稳定判断。
- Agent 默认只输出建议，不自动修改游戏数据。
- 每次调参必须能 before/after 对比。
- 研发数据优先使用 JSONL、JSON、CSV、Markdown，方便 Python、LLM、Git diff 和人工审查。

## 2. 总体流水线

```text
study-in-germany/RunSimulation.gd
-> reports/balance/<run_id>/raw_runs.jsonl
-> tools/analyze_balance.py
-> summary.json / csv / anomaly_report.md
-> tools/run_gameplay_agent.py analyze
-> anomalies.jsonl / bugs.jsonl / bugs_summary.md / value_report.json
-> tools/run_gameplay_agent.py qa
-> agent_diagnosis.md / tuning_proposal.md
-> bug_diagnosis.md / boundary_report.md / value_review.md
-> content_issues.md / event_graph_report.md
```

`interactive_player` 走另一条路：直接调 `RunInteractiveProbe.gd`，边玩边写 `playthrough.jsonl` + `playthrough_summary.md`。

## 3. Agent 类型

| Agent | 职责 | 输入 | 输出 |
|---|---|---|---|
| Balance | 分析不同 bot policy 的结局分布，找过强 / 过弱 / 必选 / 无价值行动，找属性曲线异常，判断多路线可行性，输出带证据的调参建议。 | `summary.json` + CSVs | `agent_diagnosis.md`, `tuning_proposal.md` |
| Content QA | 检查事件文本、选项重复、语气不一致、德国留学语境错误，检查奖励惩罚是否和选项描述匹配。 | 事件文本 + CSVs | `content_issues.md` |
| Event Graph | 检查 `next_event_id` 是否存在，找不可达事件、断链、循环、条件矛盾。 | `event_graph.json` + CSVs | `event_graph_report.md` |
| Bug Hunter | 读 `anomalies.jsonl` + raw runs，把异常聚类转成疑似 bug 列表 + 复现路径 + 最小修复。 | `anomalies.jsonl` + raw runs | `bug_diagnosis.md` |
| Boundary Prober | 读 `boundary_runs.jsonl`（每个 extreme 标签下的多局结果），输出哪些极端状态导致 game_state 卡死、哪些数据漂移过大、哪些 flag 组合让 ending 不可达。 | `boundary_runs.jsonl` + CSVs | `boundary_report.md` |
| Value Reviewer | 读 `value_report.json`（必选 / 死选 / 选择偏向 / 终局单一化），输出带证据的最小调参建议 + 误判 case。 | `value_report.json` + CSVs | `value_review.md` |
| Interactive Player | 让 LLM 当玩家，通过 tool calling 一周一周地推游戏。 | (实时调 Godot) | `playthrough.jsonl`, `playthrough_summary.md` |

## 4. 里程碑

### Phase 0：项目骨架 ✅

- 项目文档。
- 本地 vLLM 接入脚本。
- Agent Prompt 模板（balance / content_qa / event_graph）。
- 分析脚本。
- 报告目录规范。

### Phase 1：纯模拟接口 ✅

`study-in-germany` 提供：

```gdscript
func start_new_run(seed_value: int) -> void
func get_available_actions() -> Array
func simulate_week(action_ids: Array, event_choice_policy := "auto") -> Dictionary
func resolve_event_choice(event_id: String, choice_id: String) -> Dictionary
func is_finished() -> bool
func get_final_ending() -> Variant
func export_state_snapshot() -> Dictionary
```

### Phase 2：Monte Carlo 跑局 ✅

已实现 4 个 policy（random / balanced / study / money），可跑 200-1000 局。

### Phase 3：数值报告 ✅

生成：

- `summary.json`
- `ending_distribution.csv`
- `weekly_stats.csv`
- `action_pick_rates.csv`
- `event_trigger_rates.csv`
- `choice_pick_rates.csv`

### Phase 4：本地 LLM Agent ✅

`run_agent.py <agent> <report_dir>` 可读取报告并写出诊断。

### Phase 5：回归对比 ✅

Before/after 比较：把 `reports/balance/baseline` 和 `reports/balance/after_*` 复制到同一个 diff 工具下对比 CSV 即可。

### Phase 6：内容与事件图 QA ✅

`content_qa` + `event_graph` agents 可扫描事件文本 / 触发器图。

### Phase 7：试玩 / 边界 / Bug / 数值 ✅ (v0.2)

新增 `bug_hunter` / `boundary_prober` / `value_reviewer` / `interactive_player` 四个 agent，
以及对应的 `anomaly_detector` / `value_analyzer` / `bug_summarizer` / `game_tools` /
`RunBoundaryProbe.gd` / `RunInteractiveProbe.gd` / `ExportEventGraph.gd` 工具链。

## 5. 项目节奏

历史 Sprint：

- Sprint 1：完成 Godot 纯模拟接口；接入 `RunSimulation.gd`；跑通 `random` 和 `balanced`。
- Sprint 2：完成 Python 统计脚本；输出第一版 baseline 报告；接入 Balance Agent。
- Sprint 3：扩充 persona policies；增加 action / event / choice 统计；生成 tuning proposal。
- Sprint 4：数据外置为 JSON；接 Content QA 和 Event Graph QA；建立 before/after 回归机制。

新增 Sprint：

- Sprint 5：补 anomaly / value / bug 三个 Python 模块 + 7 个 agent 统一基类；引入 tool loop + OpenAI-compatible providers 切换（vLLM / SGLang / DeepSeek）。
- Sprint 6：补 RunBoundaryProbe / RunInteractiveProbe / ExportEventGraph 三个 Godot runner；接入 `interactive_player` agent；写 `run_gameplay_agent.py all` 一键 CLI。

## 6. 成功指标

工程指标：

- 一条命令跑完 baseline（`run_gameplay_agent.py all`）。
- 报告可复现（统计 + 检测层确定性）。
- Agent 输出可追溯到具体数字（每条结论都有证据链接）。
- 调参前后可以量化比较（CSV diff）。
- 62 个单元测试通过（pytest tests/）。

游戏设计指标：

- `BalancedBot` 好结局率合理。
- `RandomBot` 不应轻松通关。
- 专精策略有优势也有代价。
- 没有单一行动成为永久必选项。
- 事件触发覆盖率持续提高。
- 结局覆盖率从低覆盖逐步提高到主要结局都可达。
- 极端初始状态（zero_money / all_negative / flag_chaos）不能导致游戏引擎直接卡死。