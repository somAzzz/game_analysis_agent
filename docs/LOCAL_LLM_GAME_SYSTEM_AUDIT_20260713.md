# 本地 LLM 游戏系统真实测试报告（2026-07-13）

> 状态：基线审计完成；P0 Agent 可靠性修复已在后续修复分支实现。
> 测试对象：`game_analysis_agent` + `study-in-germany` Godot 游戏。
> 推理后端：本地 vLLM，实际 served model 为 `qwen3.6-27b-nvfp4`。
> 游戏运行时：Docker 中的 Godot `4.4.stable`。

## 1. 目的和结论

本轮测试的目标不是只验证命令能否退出，而是确认本地 LLM 是否真的参与决策、
Godot 是否真的推进游戏、报告是否能审计每次模型调用，以及自动诊断是否与原始
trace 一致。

结论：端到端链路可以运行。修正模型请求名称后，真实 LLM 决策格式合法率为
100%，没有非法动作或 LLM 调用错误；但游戏结果明显收敛到资金崩溃/过劳暂停，
Agent 侧同时存在默认模型名错误、失败调用丢失、相对路径错误、异常检测假阳性、
质量门禁单位不一致和评估指标失真等问题。因此当前 LLM 生成的 QA Markdown
只能作为线索，不能直接作为修复依据。

### 1.1 P0 修复进展

基线报告提交后已完成：

- 统一 `LLM_SERVED_MODEL_NAME`，并在 `play`/`qa` 前校验 `/v1/models`；
- 失败聊天请求携带并持久化 `LLMCall`；
- `sim` 在调用 Godot 前把 `report_dir` 规范化为绝对路径；
- 用 `before_state` 检测资金 shortfall，并区分计划效果与已执行效果；
- 增加 `strict_passed`，全 fallback、无 LLM 审计、错误率超限或非法决策返回非零；
- Bug Hunter 在存在 raw trace 时重算派生异常，避免读取 stale `anomalies.jsonl`。

修复后重新读取原始 50 局 trace：`cost_money_exceeds_balance` 从 482 降为 0；
另保留 82 条 `planned_cost_exceeds_balance` info，表示同周动作计划累计费用可能超过
余额，但不声称这些动作已经执行或产生负资金。

真实默认配置 smoke 结果：`strict_passed=true`、2 次 LLM 调用、0 错误、
0 fallback。全量验证为 256 个 pytest 通过、Ruff 通过、Compose 配置通过。

## 2. 测试环境

```text
game_analysis_agent: /home/bo/projects/python/game_analysis_agent
game project:        /home/bo/projects/python/study-in-germany
vLLM endpoint:       http://127.0.0.1:8000/v1
served model:        qwen3.6-27b-nvfp4
Godot:               4.4.stable.official.4c311cbee
scenario:            default_first_semester
difficulty:          normal
seed:                42
```

`docker compose ps` 显示 `vllm` 和 `godot` 均为 healthy。Godot 通过仓库的
`scripts/godot-docker-wrapper` 在容器内执行，宿主机不要求安装 Godot。

## 3. 执行范围

### 3.1 游戏契约预检

```bash
uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/local-llm-audit-20260713 \
  --difficulty normal \
  --scenario default_first_semester \
  --seed 42
```

结果：通过。Godot 的 start、state、actions、step 和 finish 数据契约可以被 Agent
消费。

### 3.2 真实 LLM 试玩

先执行 5 周 `newbie` smoke test，再执行三个 20 周上限的角色测试：

- `study`
- `visa`
- `slacker`

为避免默认模型名错误，真实成功运行使用：

```bash
LLM_SERVED_MODEL_NAME=qwen3.6-27b-nvfp4 \
  uv run python tools/run_gameplay_agent.py play ...
```

### 3.3 Monte Carlo、QA 和规则验证

- 50 局、20 周上限、`balanced` policy；
- 本地 LLM `balance` QA Agent；
- 本地 LLM `bug_hunter` QA Agent；
- deterministic quality gates；
- Godot economy validator；
- Godot risk validator。

## 4. 结果摘要

| 测试 | 结果 |
|---|---|
| vLLM 健康检查 | 通过，实际模型 ID 为 `qwen3.6-27b-nvfp4` |
| Godot 容器 | 通过 |
| 交互契约预检 | 通过 |
| `newbie` 5 周 | 10 次真实 LLM 调用，0 错误，最终决策合法率 100% |
| `study` 19 周 | 38 次调用，0 错误，最终决策合法率 100% |
| `visa` 19 周 | 38 次调用，0 错误，最终决策合法率 100% |
| `slacker` 19 周 | 38 次调用，0 错误，最终决策合法率 100% |
| 50 局 Monte Carlo | 完成，只有 2 种结局 |
| economy validator | 通过 |
| risk validator | 通过 |
| deterministic gates | 9 failures、3 warnings；其中部分是证据缺失或指标单位问题 |

三个完整角色测试的平均 LLM 延迟约为 6.4 到 6.7 秒/次，每个角色消耗约
25 万 prompt tokens。每周固定调用两次：一次选择行动，一次选择事件。

## 5. 游戏系统问题

### GAME-P0-01：结局和策略路线严重收敛

50 局 `balanced/normal` 模拟只有两种结局：

- `cashflow_collapse`：26/50，52%；
- `burnout_pause`：24/50，48%。

三个真实 LLM 角色也全部在第 19 周进入 `cashflow_collapse`。不同 persona 选择了
明显不同的动作，但仍汇聚到相同失败结局，说明策略差异没有充分映射为结果差异。

### GAME-P0-02：资源压力形成难以恢复的吸引子

三个角色的资金都在第 3 周左右触底，压力随后快速接近 100。即使频繁使用恢复
动作也无法脱离压力饱和：

- `study`：`take_a_real_break` 14 次；
- `visa`：`take_a_real_break` 15 次；
- `slacker`：`go_running` 18 次，`take_a_real_break` 11 次。

需要联合检查固定生活成本、事件压力、每周 drift、恢复收益和动作递减机制，不能
只提高单个动作数值。

### GAME-P1-03：动作高度集中

50 局模拟中每局平均选择：

- `take_a_real_break`：14.54 次；
- `sell_unused_stuff`：12.8 次；
- `library_day`：5.36 次。

动作集中是真实观测，但当前 Gate 对它的阈值计算另有单位问题，见
`AGENT-P1-07`。

### GAME-P1-04：饥饿风险需要专项验证

模拟产生 49 次 `hunger_ignored_too_long`，完整角色测试也反复出现相关 warning。
当前证据不能区分以下原因：

- 食物/做饭动作收益不足；
- Agent 没有正确理解饥饿风险；
- 饥饿状态更新或触发阈值错误。

应使用固定初始状态和固定动作序列建立独立的 Godot 回归，不应直接认定为游戏
Bug。

## 6. game_analysis_agent 问题

### AGENT-P0-01：默认模型名与 vLLM served model 不一致

当前示例配置请求 `nvidia/Qwen3.6-27B-NVFP4`，容器实际暴露
`qwen3.6-27b-nvfp4`。第一次 5 周测试的请求全部返回 404，但 `play` 静默使用
fallback，最终仍退出 0。

修复要求：

1. Compose、`.env.example` 和客户端共用同一个 served model 变量；
2. `play`/`qa` 前查询 `/v1/models`；
3. 配置模型不存在时 fail closed；
4. 提供明确的 fallback opt-in，而不是默认静默降级。

### AGENT-P0-02：失败 LLM 调用没有进入审计报告

第一次测试实际发生了约 10 次 404，但报告显示：

```text
llm_call_count = 0
llm_error_rate = null
```

失败调用发送给可选 sink 后立即抛出，而交互播放器没有配置 sink；播放器只收集
成功返回的 `LLMCall`。因此最需要审计的失败调用反而从报告中消失。

### AGENT-P0-03：相对 `report_dir` 被 Godot 解析到游戏仓库

使用相对路径运行 `sim` 时，Agent 期待输出位于自身仓库，Godot 却按 `res://`
把输出写到：

```text
/home/bo/projects/python/study-in-germany/reports/balance/local-llm-audit-20260713
```

随后 Agent 报告 `balance_runs.jsonl` prerequisite 缺失。把同一 report directory
改为绝对路径后测试通过。

修复要求：所有 Service 和 CLI 入口在启动 Godot 前统一 `resolve()`，manifest
只记录规范化路径，并对路径根目录做约束。

### AGENT-P0-04：资金异常检测使用了错误的状态时点

`cost_money_exceeds_balance` 共出现 482 次。检测器先把 `state` 设为动作后的
`after_state`，随后又把动作成本应用一次。

示例：

```text
真实动作前资金：500
动作成本：       420
动作后资金：     197
检测器计算：     197 - 420 = -223
```

游戏实际 50 局最小资金为 0，没有负资金；economy validator 也通过。该假阳性
随后误导 `bug_hunter` 声称游戏允许无限透支。

### AGENT-P0-05：失败运行仍可能显示 `valid: true`

`agent_eval.valid` 当前主要验证报告结构和内部一致性。首次全 fallback 运行仍得到
`valid: true`，虽然 `final_valid_rate=0`、`fallback_rate=1`。

需要分开：

- artifact/contract valid；
- LLM transport healthy；
- decision quality passed；
- gameplay quality passed。

CLI strict mode 应在任一必要维度失败时返回非零。

### AGENT-P1-06：persona 和风险指标不能测量目标行为

persona 配置使用 `academic_progress`、`deadline_safety`、
`stress_reduction` 等状态目标；动作标签则是 `study`、`admin`、`mental`、
`life`。当前实现直接求交集，导致：

- `study` persona alignment：0.105263；
- `visa` persona alignment：0；
- `slacker` persona alignment：0。

风险认可率只检查 `risk_awareness` 列表是否非空，没有验证 Agent 是否引用了当前
真正存在的 risk id、属性或后果。

### AGENT-P1-07：动作 Gate 的指标和阈值单位不一致

`action_pick_rates.csv` 的 `rate_per_run` 是“每局平均选择次数”，可以大于 1；
配置中的 `max_action_rate_per_run=0.80` 看起来却是比例阈值。把 14.54 次与 0.80
直接比较没有一致量纲。

建议同时输出：

- `count_per_run`；
- `share_of_all_action_picks`；
- `weekly_presence_rate`。

Gate 必须明确选择其中一种，并使用同单位阈值。

### AGENT-P1-08：LLM QA 缺少调用级 provenance

`qa` 只保存最终 Markdown，没有保存 provider、model、prompt hash、原始响应、
token、延迟、错误和重试。它生成的以下结论已确认错误：

- “起始资金为 197”：真实起始资金为 500，197 是第一周动作后资金；
- “存在负资产/无限透支”：50 局 trace 没有负资金；
- 只测试 `balanced` policy，却推断“所有策略都不可行”。

QA 输出必须能回溯到具体 artifact、字段、run/week 和调用记录，并把“观测事实”
与“模型推断”分开。

### AGENT-P2-09：每周两次完整上下文调用造成浪费

事件选择继续使用完整的 week decision prompt，而且两个调用使用相同 step name。
19 周产生 38 次调用和约 25 万 prompt tokens。应给事件选择独立的小 schema 和
精简上下文，或在协议允许时把行动与事件选择合并。

### AGENT-P2-10：长任务缺少进度和取消能力

多个真实 play 并行运行时，数分钟内没有逐周进度、当前 LLM 调用、ETA 或取消
状态。后续 Service Layer 应提供 progress callback 和 cancellation token。

### AGENT-P2-11：报告噪声和 Markdown 拼接错误

- 未结束的逐周 trace 会产生 `ending_id_empty` info；该检查应只在 finish 后执行；
- `BalanceAgent._split_outputs()` 缺少换行，生成
  `# Tuning Proposal## Minimal Parameter Changes`。

## 7. 已排除或尚未证实的问题

以下内容不能作为当前修复结论：

1. **负资金/无限透支**：已被原始 trace 和 economy validator 否定；
2. **起始资金为 197**：原始 trace 显示所有 50 局起始资金均为 500；
3. **所有 policy 都不可行**：本轮 Monte Carlo 只覆盖 `balanced` policy；
4. **100% 触发的核心事件一定是 Bug**：可能是设计的固定入场事件，需要设计
   规格确认；
5. **饥饿异常一定是状态机 Bug**：需要固定状态的专项测试。

## 8. 修复优先级和实施顺序

按照既定的 service-first 原则执行，不先写 MCP wrapper。

### Phase 1：让测试结果可信

1. 修正模型名来源并增加模型预检；
2. 记录所有成功和失败 LLM 调用；
3. 修正相对 report path；
4. 修正资金异常检测器；
5. 增加 strict execution/evaluation gate。

### Phase 2：让质量指标可信

1. 重构 persona alignment 映射；
2. 校验风险 ID/属性/后果，而不是非空字符串；
3. 统一动作 dominance 的指标单位；
4. 给 QA 增加结构化证据引用和调用 provenance。

### Phase 3：抽 Service Layer

1. `simulation_service.run(...)`：绝对路径、Godot runner、产物和错误；
2. `report_service.read(...)`：安全解析、schema、分页和 provenance；
3. `gameplay_service.step(...)`：session、调用审计、进度和取消；
4. CLI 改为这些 Service 的薄 adapter；
5. Service 回归全部通过后再开始 MCP。

### Phase 4：游戏专项平衡

Agent 侧假阳性修复后，重新运行至少：

- 6 个 persona 的固定 seed 试玩；
- 多 policy × 多 difficulty 的 Monte Carlo matrix；
- 资金、压力、饥饿的固定状态转移测试；
- economy/risk validators；
- 新旧 baseline compare。

只有这样才能确定应调整哪些游戏参数，而不是根据错误的 LLM QA 报告直接改数值。

## 9. 证据目录

```text
reports/interactive/local-llm-audit-20260713/
reports/play/local-llm-newbie-smoke-20260713/
reports/play/local-llm-newbie-real-20260713/
reports/play/local-llm-study-real-20260713/
reports/play/local-llm-visa-real-20260713/
reports/play/local-llm-slacker-real-20260713/
reports/balance/local-llm-audit-20260713/
reports/validation/local-llm-audit-20260713/
```

这些运行产物用于本地审计，不应在没有体积和隐私检查的情况下整体提交。提交到
仓库的是本报告中的可复核摘要、修复优先级和复现命令。

## 10. 验收标准

完成 P0 修复后，至少满足：

- 配置模型不存在时，在游戏开始前返回非零；
- 失败调用的数量、错误类型和延迟进入 agent report；
- 全 fallback 运行不能通过 strict eval；
- 相对和绝对 report directory 产生相同规范化位置；
- 资金异常检测使用 `before_state`，实际透支误报归零，计划超支单独标记；
- LLM QA 中每个关键数值都能引用到 report artifact 和字段；
- unit tests、Ruff、Godot contract smoke、economy/risk validators 通过。
