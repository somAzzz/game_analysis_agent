# P1/P2 Agent 修复与游戏平衡实验状态（2026-07-13）

## 决策摘要

本轮提交只交付 `game_analysis_agent` 的 P1/P2 可靠性修复。游戏仓库
`study-in-germany` 中已经进行的实验保留在当前工作区，但停止继续调参，也不混入
analysis agent 的 PR。大规模蒙特卡洛平衡修复留到后续独立任务。

## Analysis agent 已完成的修复

### P1：评估与证据可信度

- 风险意识不再以“字段非空”判定。输出必须命中当前周真实的 risk ID；无法匹配的内容
  计入 `unmatched_risk_awareness_count`。
- persona 对齐改用显式 action tag / action ID 映射。newbie 可以按游戏提供的
  `suggested_action_ids` 做风险引导，不再依赖容易误判的字符串包含关系。
- 新增 `persona_alignment_opportunities`，避免只报告命中次数而没有机会数。
- action dominance 的门禁单位由“每局选择次数”改为全部 action picks 中的
  `pick_share`；同时输出 `run_presence_rate`，保留旧字段用于兼容。
- QA 子命令为每个 agent 保存独立的 `*_agent_report.json`，包含 provider、model、
  prompt、response、latency、error 和输出文件。失败调用也进入审计，agent 失败时返回
  非零退出码。
- 未结束的 interactive probe 不再错误地产生 `ending_id_empty`。
- Balance Agent 拆分输出时保证 `# Tuning Proposal` 标题格式稳定。

### P2：真实交互运行能力

- 事件选择使用独立的紧凑提示，只发送事件、候选项、当前状态、已选行动和 risk IDs，
  不再重复整份 WeekContext。
- 事件选择限制为 192 output tokens，并使用独立的
  `week-N-event[-repair]` 调用审计名。
- playthrough 增加逐周进度事件，包括 phase、week、elapsed 和 ETA。
- playthrough 增加取消检查，可在每周开始或事件选择阶段安全终止。
- CLI 会实时打印交互进度，长时间本地模型调用不再表现为无响应。

## 测试证据

- P1/P2 目标测试：69 passed。
- 完整 Python 测试集：264 passed。
- Repository-wide Ruff：通过。
- 新增回归覆盖：
  - 精确 risk ID 与错误 risk 文本；
  - persona 显式 action 映射；
  - action pick share 门禁；
  - QA LLM provenance；
  - 紧凑事件提示；
  - progress / cancellation；
  - 未结束 probe 的 ending anomaly；
  - Balance Agent 标题拆分。

真实本地回归也已完成：compose 中的
`qwen3.6-27b-nvfp4` + Godot sidecar 运行 2 周 newbie playthrough，退出码为 0，
`strict_passed=true`。两周决策和两次事件选择均一次通过，没有 fallback、非法行动、
无效事件选择、LLM error 或 anomaly；risk acknowledgement 和 persona alignment 均为
1.0。

真实审计共保存 4 次 LLM call。周决策提示分别为 10,899 / 11,655 字符，事件提示为
1,797 / 1,965 字符，证明事件选择没有重复发送整份 WeekContext；事件调用延迟约
529 / 533 ms。报告 manifest 状态为 `completed`，并记录全部四个输出文件的大小、
SHA-256 和修改时间。

## 游戏仓库中保留的实验

这些修改位于 `/home/bo/projects/python/study-in-germany`，不属于本次 analysis agent
PR：

- `scripts/simulation/ActionResolver.gd`：周计划校验累计现金成本。
- `autoload/GameState.gd`：正收入优先偿还 arrears，并同步现金流风险 flags。
- `scripts/policies/PlayerPolicy.gd`：为确定性测试策略预留现金、饥饿、压力和精力的
  危机行动。
- `scripts/policies/WorkPolicy.gd`：接入同一危机行动选择逻辑。
- `scripts/tools/ValidateEconomyRules.gd`：累计成本与 arrears 偿还回归。
- `scripts/tools/RunInteractiveProbe.gd`：风险指导 contract；这是进入本轮前已经存在的
  工作区改动，应继续保留。

Godot economy validator 在当前收入偿还实现下通过。最新 policy 预选逻辑也通过真实
Godot smoke test，但平衡结果尚未达到可提交标准。

## 平衡实验结果

### 原始 300 局基线

normal / default_first_semester，每种策略 50 局：

| Policy | 结局 |
| --- | --- |
| balanced | 52% cashflow collapse，48% burnout |
| study | 100% cashflow collapse |
| work | 100% burnout |
| admin | 100% cashflow collapse |
| social | 100% cashflow collapse |
| slacker | 100% cashflow collapse |

共同症状：第 20 周 stress 接近 100，hunger 约 82。六种策略共出现 2020 次
`cost_money_exceeds_balance`。

### 累计计划成本修复

相同 300 局矩阵中，`cost_money_exceeds_balance` 从 2020 次降为 0，但结局分布几乎
没有变化。这证明规划器 invariant 修复有效，但它不是平衡崩溃的唯一原因。

### arrears 与策略危机实验

收入优先偿还 arrears 后，work 路线的平均期末 arrears 从约 225 EUR 降到约 26 EUR，
50 局中 34 局清零；其他路线因为没有稳定选择收入行动，仍会进入危机。

加入“一种危机只预留一个行动”的策略实验后，20 局/策略的校准结果为：

| Policy | 最新实验结局 |
| --- | --- |
| balanced | 95% burnout，5% academic failure |
| study | 80% burnout，20% admin collapse |
| work | 100% burnout |
| admin | 100% burnout |
| social | 100% burnout |
| slacker | 75% academic failure，25% burnout |

现金崩溃明显减少，但 stress 仍然饱和，且路线目标被生存行动挤压。因此当前实验不能被
描述为“平衡修复完成”。

## 后续蒙特卡洛任务

后续应单独建立 game-balance PR，并按以下顺序执行：

1. 先为经济状态机、恢复递减和 policy 行动预留建立确定性 invariant tests。
2. 固定 seeds，对 policy × difficulty × scenario 建立基线矩阵。
3. 为结局多样性、危机率、路线目标、最终状态和 action pick share 定义有置信区间的
   gates。
4. 每次只改变一类机制，运行 before/after 同 seed 对照。
5. normal 达标后再校准 hard / realistic，避免用统一数值掩盖难度差异。
6. 最后再使用本地 LLM personas 验证真实玩家 agent，而不是用 LLM 结果反向替代确定性
   平衡基线。

在该任务开始前，不应继续修改游戏数值或声称当前平衡问题已经修复。
