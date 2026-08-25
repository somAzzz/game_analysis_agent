# 技术架构

## Godot 结构

- `autoload/GameState.gd`：单例状态、效果应用、存档序列化。
- `autoload/EventBus.gd`：UI 与模拟逻辑信号。
- `autoload/DataRegistry.gd`：加载行动、事件、角色、结局数据，并提供查询 facade。
- `autoload/RandomService.gd`：统一随机源，用于 seed 可复现的 UI 和 headless 模拟。
- `autoload/DifficultyConfig.gd`：难度配置，影响生活漂移、事件权重和事件选项成功率。
- `scripts/data/`：Resource 数据定义。
- `scripts/simulation/`：行动、事件、考试、结局、存档解析。
- `scripts/simulation/EconomyRules.gd`：集中维护德国最低工资、合法/黑工时薪比例、工时上限和按小时计算收入的公式。
- `scripts/simulation/RiskEvaluator.gd`：计算 top 3 当前风险和建议行动，供 UI 与后续报告使用。
- `scripts/policies/`：Agent 批量实验使用的玩家策略。
- `scripts/tools/`：headless runner、内容校验等 Agent 协作命令。
- `data/scenarios/`：headless 实验使用的开局场景。
- `data/actions/`, `data/events/`, `data/endings/`, `data/characters/`：Phase 1 数据迁移 JSON 输出目录。当前 actions、events、characters 和 endings 已由 JSON 运行时加载；`DataRegistry.gd` 仍保留 hardcoded fallback。
- `scenes/main/Main.tscn`：当前 Demo 主场景。
- `scenes/ui/`：后续可拆分的 UI 场景占位。

## 数据流

### 数据迁移桥

Phase 1 增加 `scripts/data/DataLoader.gd` 作为从 hardcoded 内容迁移到 JSON 内容的桥。它可以把 actions、events、choices、endings 和 characters 的 JSON 记录读回现有 Resource 类，也可以把现有 Resource 导出为 Dictionary。`scripts/tools/ExportContentJson.gd` 负责生成 JSON 快照，`scripts/tools/SplitEventsJsonByGroup.gd` 负责把事件拆为 application/admin/academic/life/work/relationship/random 分组文件，`scripts/tools/ValidateJsonContent.gd` 负责读回 smoke validation。`DataRegistry` 现在优先从 `data/actions/generated_actions.json` 加载行动卡、从 7 个 `data/events/*_events.json` 分组文件加载事件、从 `data/characters/npcs.json` 加载 NPC、并从 `data/endings/generated_endings.json` 加载结局，失败时回退到 hardcoded 数据；`PrintDataSources.gd` 可打印当前数据来源。事件记录带 `source_order`，分组加载后按原始顺序排序，避免改变 fixed/conditional 事件的触发优先级。`ValidateContent.gd` / `ValidateJsonContent.gd` 会硬检查 Phase 5 mainline event id 是否真实存在；`ValidateRouteBoundaries.gd`、`ValidateRiskGuidance.gd` 和 `ValidateDemoGates.gd` 负责把内容质量、路线差异、top action 占比、低钱危机率、normal 结局多样性和 top risk 建议行动有效性转成可重复的 headless gate。

### UI 数据流

1. `Main` 从 `DataRegistry` 获取行动和事件。
2. 玩家选择行动后，`SimulationEngine` 调用 `ActionResolver` 结算。
3. `GameState` 应用效果并发出 `state_changed`。
4. `EventResolver` 在周结算时选择事件。
5. 事件选项通过 `GameState.apply_effects` 改变状态。
6. 第 20 周后 `ExamResolver` 和 `EndingResolver` 生成结果。

### Headless 数据流

1. `RunSimulation.gd` 读取 CLI 参数：`runs`、`policy`、`seed`、`scenario`、`weeks`、`out`。
2. `GameState.reset` 初始化状态，`configure_run` 写入 `run_id`、`seed`、版本和 policy。
3. `RandomService.set_seed` 设置统一随机源。
4. `DifficultyConfig` 根据 `difficulty` 调整生活漂移、事件权重和事件选项成功率。
5. `data/scenarios/*.json` 可覆盖初始状态和 flags。
6. policy 从 `SimulationEngine.get_available_actions` 返回的行动池中选择行动。
7. `SimulationEngine.resolve_week` 结算行动、生活漂移、事件池和触发事件。
8. policy 选择事件选项，`EventResolver.resolve_choice_detailed` 返回成功率、成功/失败和效果。
9. runner 记录 weekly trace、action sequence、final state、exam 和 ending。
10. runner 输出 JSONL，并生成 CSV 指标供分析 Agent 读取。

## Agent 协作边界

本项目负责：

- 游戏规则和状态结算。
- 内容数据和场景配置。
- 可复现随机数。
- headless 批量跑局。
- JSONL/CSV/JSON 报告。
- 内容校验。

分析 Agent 系统负责：

- 读取模拟器输出。
- 汇总统计和异常分析。
- 比较策略和场景。
- 生成调参建议或补丁。

分析 Agent 不应该直接执行游戏规则，也不应该绕过 `RunSimulation.gd` 修改运行状态。

## 存档

存档写入 `user://savegame.json`。保存字段包括周数、学期、城市、属性、`exam_readiness`、`failed_courses`、TestDaF 四项小分、冻结账户余额、本周工时、年度半天数、flags、关系、已完成事件、行动历史、本周行动/行动组计数和最后考试结果。

考试结算由 `scripts/simulation/ExamResolver.gd` 负责。它读取 `academic_progress`、`exam_readiness`、`language`、`energy`、`stress` 和随机波动，写入 `last_exam_result`；未通过时设置 `needs_retake` 并增加 `failed_courses`。结局判定由 `EndingResolver` 在考试后执行，因此 `academic_failure` 和成功类结局可以直接读取挂科结果。

每周结算会写入 `weekly_snapshots`，用于期末报告。`scripts/simulation/SemesterReportBuilder.gd` 从行动历史、已完成事件、flags、每周快照和最终状态生成“第一学期报告”，并同时用于 UI 结局页和模拟输出的 `final_report` 字段。

自动模拟由 `scripts/tools/RunSimulation.gd` 驱动。runner 有迭代保护：如果策略在 APS/注册管线长期无法推进，会设置 `pipeline_stalled` 并退出，防止测试进程无限循环。
