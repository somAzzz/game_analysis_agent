# Interactive LLM Playtest

## 1. 目标

`interactive_player` 的目标不是让 LLM 随便试玩一局，而是把 LLM 变成可复现的设计测试仪器：

- 像真实玩家一样逐周读取状态、选择行动、承担后果。
- 每个选择都有结构化理由、风险意识和收益代价判断。
- 只能基于 Godot 暴露的 action / event / choice 决策，不能幻觉。
- 保留 32K 本地 vLLM 上下文窗口，但用结构化上下文包减少无效 token。
- 支持不同 persona，用同一 seed/scenario 做 before-after 对比。

## 2. 分层架构

### 2.1 Godot 交互层

- `RunSimulation.gd`：Monte Carlo 批量模拟。
- `RunBoundaryProbe.gd`：极端边界状态模拟。
- `RunInteractiveProbe.gd`：按 JSON plan replay 单局互动试玩。
- `ExportEventGraph.gd`：导出 action/event catalog。
- `Validate*.gd`：确定性质量门禁。

### 2.2 Python 控制层

- `InteractiveProbe` 维护一局试玩的 plan、状态和历史。
- `InteractivePlayerAgent` 控制显式周循环：构建上下文、请求 LLM、校验决策、推进 Godot、写审计日志。
- `WeekContext` 和 `PlayerDecision` 用 Pydantic 固化输入/输出契约。

### 2.3 LLM 决策层

每周只把必要信息给模型：

- 当前核心状态。
- 当前 top risks。
- 合法 action 的 id/name/cost/effects/tags。
- 当前事件 choices 的 success/failure effects。
- persona 策略。
- 最近 5 周压缩记忆。

不每周塞入：

- 全部 raw logs。
- 全部 CSV。
- 全部 agent 报告。
- 全部事件原文。

## 3. 上下文长度原则

当前 vLLM 以 `--max-model-len 32768` 启动。这个窗口不应为了测试方便被缩短。

`AGENT_MAX_TOKENS` 是输出 token 上限，不是输入 context 上限。若发生 context overflow，应优先压缩无效输入，例如全量 anomalies/raw logs，而不是降低模型可见的关键上下文。

## 4. 验收标准

- `python tools/run_gameplay_agent.py play --persona money --weeks 20` 能产出每周一行 `playthrough.jsonl`。
- 每周记录 `week_context`、`decision`、`validation`、`state_before`、`state_after`、`delta`。
- 非法 action/choice 会触发 repair；repair 失败才 fallback。
- `RunInteractiveProbe.gd` 输出包含 `before_state`、`after_state`、`available_actions`、`selected_action_ids`、`action_effects`、`event_choices`、`final_ending_id`。
- 同一 seed/persona/scenario 能复现相同 plan 约束下的 Godot replay。

## 5. 失败结局审核标准

失败也是游戏的一部分。`interactive_player` 的目标不是强行让每个 persona 通关，而是验证不同策略是否会产生可解释、可复现、符合设计意图的结果。

### 5.1 合法失败

以下情况不应自动判定为测试失败：

- `burnout_pause`、`mental_crash`：长期高压、恢复不足、风险忽视造成的状态崩盘。
- `registration_failure`、`delayed_enrollment`、`admin_collapse`：错过注册/行政窗口后的设计内后果。
- `cashflow_collapse`、`survival_struggle`：现金流和生存资源被策略消耗拖垮。
- `academic_failure`：学习投入、考试准备或状态管理不足导致的失败。
- `work_law_trouble`：打工策略越过合规边界。

这些结局只有在 `playthrough.jsonl` 能解释“玩家如何一步步走到这里”时才算健康失败。

### 5.2 非法失败

以下情况仍然是 gate failure：

- `unknown`、`pipeline_stalled`、空 ending。
- 成功结局和核心语义冲突，例如 `visa_success_without_registration`。
- 数值溢出、负数状态越界、Godot replay 不可复现。
- LLM 决策大量 fallback，导致结果不是 Agent 自己玩出来的。

### 5.3 审核口径

- 单个 persona 不要求成功；它应该代表一种玩家策略。
- 全矩阵应覆盖成功、混合恢复、设计内失败三类结果。
- 如果所有 persona 都集中到同一个失败结局，这是 balance/design warning，不是“失败结局不允许”。
- 失败路线应检查提示是否足够清晰、补救路径是否可见、代价是否和叙事一致。
