# Agent 协作开发路线

## 目标

拆分成两个项目后，游戏模拟器项目的目标是给分析 Agent 系统提供一个稳定、可复现、可观测、可批量运行的实验环境。

核心契约：

```text
给定 seed + 玩家策略 + 场景 + 内容版本 + 规则版本
-> 无 UI 跑完整 20 周
-> 输出完整过程日志、状态变化、事件触发、结局和基础指标
-> Agent 基于输出做平衡分析、内容审查、策略比较和异常定位
```

## 项目边界

### 游戏模拟器项目

负责：

- 维护游戏规则。
- 维护内容数据。
- 执行模拟。
- 提供 headless 批量跑局能力。
- 输出结构化日志和基础统计。
- 提供内容校验和状态快照。

不负责：

- 不使用 LLM 做分析。
- 不自动调参。
- 不生成设计报告。
- 不做自然语言诊断。

### 分析 Agent 系统

负责：

- 读取模拟器输出。
- 汇总统计。
- 分析异常。
- 发现数值问题和内容问题。
- 提出调参建议。
- 生成报告。
- 可选生成 patch。

不负责：

- 不直接执行游戏规则。
- 不自己猜测游戏状态。
- 不绕过模拟器修改运行状态。

两个项目之间的接口是 CLI 命令、JSONL、CSV、JSON 报告和 schema 文档。

## 已落地能力

当前已经实现第一版协作层：

- `autoload/RandomService.gd`：统一随机源，支持 seed 可复现。
- `GameState.configure_run`：记录 `run_id`、`seed`、`policy`、`content_version`、`rules_version`。
- `GameState.export_state_snapshot`：导出可序列化状态快照。
- `SimulationEngine.get_available_actions`：提供 policy 可用行动池。
- `EventResolver.resolve_choice_detailed`：返回事件选项的成功率、结果和效果。
- `DifficultyConfig`：内置 `easy`、`normal`、`hard`、`realistic`，影响生活漂移、事件权重和成功率。
- `scripts/policies/`：内置 `random`、`balanced`、`study` 三种策略。
- `scripts/tools/RunSimulation.gd`：headless 批量跑局。
- `scripts/tools/ValidateContent.gd`：基础内容校验。
- `data/scenarios/`：内置 `default_first_semester`、`low_money_start`、`high_stress_start`。
- `docs/06_agent_simulation_contract.md`：当前稳定 CLI 和输出契约。

已验证：

- headless runner 可跑完整 20 周。
- 同 seed、同 policy、同 runs、同 scenario 输出可复现。
- 内容校验当前为 `0 errors, 0 warnings`。
- 主项目 headless 加载通过。

## 当前稳定命令

批量模拟：

```bash
godot4 --headless \
  --path /Users/bo/projects/study-in-germany \
  -s res://scripts/tools/RunSimulation.gd \
  --runs=1000 \
  --policy=balanced \
  --difficulty=normal \
  --seed=42 \
  --scenario=default_first_semester \
  --weeks=20 \
  --out=reports/runs/balanced_seed42.jsonl
```

内容校验：

```bash
godot4 --headless \
  --path /Users/bo/projects/study-in-germany \
  -s res://scripts/tools/ValidateContent.gd \
  --out=reports/content_validation.json
```

## 输出文件

`RunSimulation.gd` 会在 raw JSONL 同目录生成：

- `summary.json`
- `ending_distribution.csv`
- `weekly_states.csv`
- `action_pick_rates.csv`
- `event_trigger_rates.csv`

Agent 系统优先读取这些文件，不依赖 Godot UI 或 `Main.gd`。

## 难度规则

当前难度配置位于 `autoload/DifficultyConfig.gd`。

难度影响：

- `weekly_drift`：每周自然恢复、压力、孤独和生活费。
- `success_rate_bonus`：事件选项最终成功率的全局偏移。
- `success_rate_min` / `success_rate_max`：事件选项成功率上下限。
- `event_type_weights`：按 `fixed`、`conditional`、`random` 调整事件权重。
- `event_focus_weights`：按事件主题调整权重，如 `stress`、`admin`、`money`、`academic`、`positive`。

事件 trigger 可以使用以下字段限制难度：

- `difficulty`
- `difficulties`
- `min_difficulty`
- `max_difficulty`

Agent 比较难度时，应固定 seed、policy、scenario 和版本，只改变 `difficulty`。

## P0：必须完善

这些能力决定 Agent 系统是否能稳定工作。

- 扩展 policy：`money`、`admin`、`social`、`greedy`、`newbie`。
- 完善 weekly trace：记录 event candidate pool、blocked reason、choice candidate list。
- 增加 effect records：每个属性变化都记录来源、目标、delta、week、reason。
- 增加 replay 文件：保存 action sequence 和 event choice，用于失败局复现。
- 增加基础 invariant check：每周后检查属性范围、week 推进、game over 后不可继续行动。
- 增加更多 scenario：高德语开局、行政困难、慕尼黑高房租、学霸社恐等。

## P1：提高分析质量

- `ExportContentGraph.gd`：导出行动、事件、flag、结局之间的图。
- `ExportContentSummary.gd`：导出内容摘要，方便 Agent 不读源码。
- ending reason codes：结局输出命中条件和实际数值。
- near miss analysis：记录差一点达成的结局和缺口。
- action opportunity logging：区分“不可用”和“可用但没选”。
- event opportunity logging：区分“条件不满足”“条件满足但没抽中”“被固定事件覆盖”。
- metrics target：定义目标区间，如 bad ending rate、avg final stress。

## P2：后续增强

- 外置内容数据到 JSON：`actions.json`、`events.json`、`npcs.json`、`endings.json`。
- JSON schema 校验。
- versioned content pack：支持调参前后对比。
- patch mode：Agent 提供临时 patch，模拟器不改源数据直接测试。
- shell wrapper：提供 `./sim run`、`./sim validate`、`./sim export-graph`。

## 设计原则

后续所有模拟器能力都应服务这六个关键词：

- Deterministic：同 seed、policy、scenario、版本得到同样结果。
- Observable：weekly trace 和 effect records 能解释因果链。
- Controllable：policy、scenario、difficulty、patch 可控制实验条件。
- Serializable：状态、运行、指标、校验都能导出为机器可读文件。
- Validatable：内容和运行状态能被校验。
- Replayable：异常局能通过 seed 和 action sequence 复现。

## 近期建议顺序

1. 补 `money/admin/social` 三个 policy。
2. 增加 effect records，让属性变化可以归因。
3. 增加 replay 输出和 replay runner。
4. 增加 content graph export。
5. 再迁移硬编码内容到 JSON。

当前不建议优先做复杂 UI、美术、动画或大规模内容扩写。先把实验接口稳定下来，再让分析 Agent 基于真实跑局数据发现问题。
