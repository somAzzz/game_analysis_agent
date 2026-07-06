# Demo v0.3 可解释失败修复计划

## 1. 目标

本轮修复不把游戏调简单，而是把失败从“数值把玩家推死”改成“玩家看得见风险、做过取舍、最后承担结果”。

目标版本定义为：

```text
Demo v0.3: 可解释失败版本
```

核心标准：

1. 玩家可以失败，但不能不知道为什么失败。
2. 玩家可以没钱，但不能没钱还被系统强行扣钱。
3. 玩家可以压力崩，但必须经历明显的预警链。
4. 玩家可以走偏路，但不同路线应该死法不同、活法也不同。
5. 玩家可以重复做恢复动作，但重复做要产生边际收益下降和长期代价。
6. 每条主路线都要有成功结局、混合结局、失败结局。

## 2. 当前证据

证据来自真实报告：

- `reports/play/full-demo-20260706-211249/*/playthrough_summary.md`
- `reports/balance/full-20260706-*/ending_distribution.csv`
- `reports/balance/full-20260706-*/anomalies.jsonl`
- `reports/balance/full-20260706-*/gate_report.json`
- `reports/boundary/*/boundary_runs.jsonl`

### 2.1 可玩性已成立

6 个 persona 都能跑到 19 周并产生结局：

| persona | ending |
| --- | --- |
| money | `burnout_pause` |
| newbie | `registration_failure` |
| slacker | `registration_failure` |
| social | `social_connector` |
| study | `registration_failure` |
| visa | `burnout_pause` |

说明核心循环已经成立：行动选择、事件触发、状态变化、结局解析都能跑通。

### 2.2 主要问题

| 问题 | 当前证据 | 影响 |
| --- | --- | --- |
| 普通行动/事件可把钱扣成无语义负数 | `cost_money_exceeds_balance: 16788`, `negative_money: 12101` | 经济系统像漏洞，不像可玩的压力 |
| 失败结局过度集中 | `cashflow_collapse: 359`, `burnout_pause: 340` / 840 runs | 失败像默认出口，路线重玩价值下降 |
| gate 全面失败 | 42 个 full balance gate 全失败 | 平衡性未达标 |
| 动作必选感过强 | `cook_at_home`, `budget_call`, `international_office` 等每 run 过高 | 每周选择变窄 |
| 危机响应不足 | `high_visa_risk response_rate: 0%`, `high_stress response_rate: 0%` | 玩家看到风险但缺少有效反制 |
| 边界脆弱 | `single_week_spike`, `non_repeatable_event_repeated` | 极端状态会炸穿体验 |

## 3. 修复原则

### 3.1 失败保留

保留：

- `cashflow_collapse`
- `burnout_pause`
- `registration_failure`
- `academic_failure`

但失败必须：

- 可预警
- 可应对
- 可解释
- 可复盘
- 按路线分化

### 3.2 经济失败语义化

普通消费不能直接把 `money` 扣成大负数。现金不足时应变成：

- 行动不可用
- 或进入显式债务/逾期/危机 flag
- 或触发低钱专属事件

短期实现先采用保守结构：

```text
普通行动 cost_money > money -> action disabled
事件扣钱导致 money < 0 -> clamp 到 0，并记录 unpaid/arrears flag 和日志
必要支出不足 -> 进入 arrears/financial_warning，而不是静默负数
```

后续再扩展为完整字段：

- `debt`
- `arrears`
- `rent_arrears`
- `insurance_arrears`
- `food_insecurity`

## 4. 分层执行方案

## P0. 经济系统止血

### 目标

消除普通消费导致的无语义负钱，让现金流失败从“数值漏洞”变成“危机状态”。

### 实现点

`study-in-germany`：

- `scripts/data/ActionDef.gd`
- `scripts/simulation/ActionResolver.gd`
- `autoload/GameState.gd`
- `scripts/tools/ValidateEconomyRules.gd`
- `data/actions/generated_actions.json`

### 修改项

1. `ActionDef.can_use()` 增加 affordability 判断：
   - `cost_money <= 0` 可用。
   - `state.money >= cost_money` 可用。
   - 有 `allow_debt` / `allow_arrears` requirement 或 tag 的特殊行动可用。
   - 其他普通消费不可用。

2. `ActionResolver.resolve_action()` 不再无条件扣钱：
   - 普通行动现金不足时返回日志，不应用效果，不记录为成功行动。
   - 允许债务/逾期的行动调用 `GameState.apply_semantic_money_delta()`。

3. `GameState.apply_effects()` 对负 money effect 走统一函数：
   - 普通负 money 不让 `money < 0`。
   - 不足部分记录 `flags["arrears"]` / `flags["cash_shortfall"]`。
   - `event_log` 记录清晰原因。

4. 加基础经济字段或 flag：
   - `cash_shortfall_count`
   - `arrears_amount`
   - `food_insecurity`
   - `used_debt`

### 验收指标

短期：

```text
cost_money_exceeds_balance 显著下降
negative_money 显著下降
普通 action 不再产生 money < 0
```

目标：

```text
cost_money_exceeds_balance = 0
uncontrolled negative_money = 0
cashflow_collapse 仍存在，但不再统治所有结局
```

## P1. 危机响应动作

### 目标

高风险状态下，玩家有明确、强力、但有代价的应对动作。

### 实现点

- `data/actions/generated_actions.json`
- `scripts/simulation/RiskEvaluator.gd`
- `scripts/tools/ValidateRiskGuidance.gd`
- 各 policy：`scripts/policies/*.gd`

### 新增或重调动作

压力：

- `take_a_real_break`
- `ask_for_deadline_extension`
- `call_family_honestly`
- 调整 `therapy` 为危机专用，冷却 4 周。

饥饿：

- `cheap_noodle_week`
- `mensa_coupon`
- `skip_meal`
- `classmate_meal` 加社交债务/冷却。

行政/签证：

- `emergency_international_office`
- `write_formal_email_to_abh`
- `ask_senior_student_for_template`
- `panic_refresh_termin`

低钱：

- `rent_talk_extension`
- `short_term_cash_shift`
- `family_budget_call`
- `sell_unused_stuff`

### 验收指标

```text
high_visa_risk response_rate > 50%
high_stress response_rate > 50%
high_hunger response_rate > 60%
money <= 200 时至少有 2 个可用应对行动
```

## P2. 降低必选动作倾向

### 目标

保留主题动作，但让它们不再成为所有路线的万能答案。

### 重点动作

- `budget_call`
- `cook_at_home`
- `classmate_meal`
- `international_office`
- `therapy`
- `bilibili_rest`
- `sleep_recover`

### 修改项

1. `budget_call`
   - 冷却 4 周。
   - 收益递减。
   - 增加 `parent_pressure` 或 flag。
   - 多次使用触发家庭冲突事件。

2. `cook_at_home`
   - 保留低成本稳定降饥饿。
   - 降低其他附带收益。
   - `max_per_week = 2` 或 `cooldown_group = food`.

3. `classmate_meal`
   - 加关系条件。
   - 加 `reciprocity_debt`。
   - 冷却 3 周。

4. `international_office`
   - 普通状态收益降低。
   - 高行政风险时收益提高但压力上升。
   - 冷却 2-3 周。

### 验收指标

```text
没有普通行动 > 10/run
recovery_action_share <= 30%
admin_action_share <= 35%
balanced top actions 不再全是恢复/生存动作
```

## P3. 结局分布重构

### 目标

失败类型更丰富，每条路线都有正向、混合、失败出口。

### 新增/拆分结局

| 路线 | 正向结局 | 混合结局 | 失败结局 |
| --- | --- | --- | --- |
| 学业 | `study_stable` | `high_score_burnout` | `academic_failure` |
| 金钱 | `work_survivor` | `work_trap` | `cashflow_collapse` |
| 社交 | `social_connector` | `socially_saved_barely` | `network_without_grounding` |
| 行政 | `admin_survivor` | `paperwork_stable_life_empty` | `registration_failure` |
| 摆烂 | `barely_survived` | `late_wakeup` | `deadline_cascade` |
| 签证 | `visa_safe` | `temporary_extension_stress` | `visa_crisis` |

### 实现点

- `data/endings/generated_endings.json`
- `scripts/data/EndingDef.gd`
- `scripts/simulation/EndingResolver.gd`
- `scripts/simulation/SemesterReportBuilder.gd`

### 验收指标

Normal:

```text
distinct_endings >= 6
max_single_ending_rate <= 35%
failure_total_rate 45%-75%
success_total_rate 15%-35%
mixed_total_rate 15%-35%
```

Realistic:

```text
distinct_endings >= 5
max_single_ending_rate <= 40%
failure_total_rate 55%-80%
```

## P4. 预警链和边界稳定

### 目标

重大失败至少经过：

```text
warning -> crisis -> collapse
```

### 修改项

1. 现金流链：
   - `cashflow_warning`
   - `rent_arrears_notice`
   - `cashflow_collapse`

2. 压力链：
   - `stress_warning`
   - `burnout_crisis`
   - `burnout_pause`

3. 行政链：
   - `registration_deadline_warning`
   - `registration_last_call`
   - `registration_failure`

4. 学业链：
   - `academic_warning`
   - `exam_registration_crisis`
   - `academic_failure`

5. 边界 guard：
   - 单周 delta guard。
   - non-repeatable event lock。
   - repeatable event cooldown。

### 验收指标

```text
single_week_spike 显著下降
non_repeatable_event_repeated = 0
重大失败前至少有 1-2 个对应 warning/crisis event 或 flag
```

## 5. Gate 调整

失败不是 gate 失败，单一失败、不可解释失败才是 gate 失败。

### 经济 gate

```text
cost_money_exceeds_balance = 0
unsemantic_negative_money = 0
debt_or_arrears_state_used_when_cash_insufficient > 0
```

### 结局 gate

```text
distinct_endings >= 6 normal / >= 5 realistic
max_single_ending_rate <= 35% normal / <= 40% realistic
cashflow_related_rate <= 50% in low_money_start
```

### 行动 gate

```text
max_normal_action_rate_per_run <= 10
same_action_consecutive_weeks <= 3
recovery_action_share <= 30%
```

## 6. 验证命令

### 快速 deterministic 验证

```bash
cd /home/bo/projects/python/game_analysis_agent
export GODOT_BIN=/tmp/godot-docker-wrapper
export GAME_PROJECT_PATH=/home/bo/projects/python/study-in-germany

uv run pytest tests -q
uv run python tools/run_gameplay_agent.py validate --report-dir reports/validation/v03 --check economy --check risk
```

### 小矩阵验证

```bash
for policy in balanced study work admin social slacker; do
  uv run python tools/run_gameplay_agent.py sim \
    --run-id v03-${policy}-normal-r12 \
    --runs 12 --policy "$policy" --difficulty normal --weeks 20
done
```

### 边界验证

```bash
uv run python tools/run_gameplay_agent.py probe \
  --run-id v03-boundary-r3 \
  --runs 3 --policy balanced --weeks 12 \
  --extreme "zero_money,deep_debt,no_energy,all_negative,no_language,flag_chaos"
```

### LLM 游玩验证

```bash
uv run python tools/run_gameplay_agent.py play \
  --report-dir reports/play/v03-smoke-newbie \
  --weeks 20 --persona newbie --difficulty normal --scenario default_first_semester --seed 42
```

## 7. 第一轮实施范围

本轮先完成 P0 + P1 的最小可验证闭环：

1. 普通 action affordability。
2. 事件/漂移负钱语义化，不再静默扣成大负数。
3. `budget_call`, `cook_at_home`, `classmate_meal`, `international_office`, `therapy` 初步冷却/递减/条件化。
4. 增加高压力、高饥饿、高行政风险、低钱响应动作。
5. 跑小矩阵和边界报告，对比异常数量和结局集中度。

P2-P4 在第一轮验证后继续推进，避免一次性重写过多系统导致无法定位回归。

## 8. 第一轮执行记录

执行日期：2026-07-06

### 8.1 已落地范围

已完成 P0 + P1 的最小闭环，并补了一部分 P2/P3 口径迁移：

1. 经济系统止血
   - `GameState` 增加 `cash_shortfall_count`, `arrears_amount`, `parent_pressure`, `reciprocity_debt`。
   - `apply_effects({"money": negative})` 统一转入 `apply_money_delta()`。
   - 普通负钱不再让 `money < 0`，不足部分进入 `arrears_amount`，并设置 `cash_shortfall` / `arrears` / `cashflow_warning` / `cashflow_crisis`。
   - 每周漂移从负现金惩罚迁移为逾期惩罚。

2. 普通行动可负担性
   - `ActionDef.can_use()` 增加 `cost_money` affordability 判断。
   - 普通付费行动现金不足时不可用。
   - 保留 `allow_arrears` / `allow_debt` / `arrears` / `debt` 作为必要支出扩展口径。

3. 危机响应动作
   - 新增 `sell_unused_stuff`。
   - 新增 `rent_talk_extension`。
   - 新增 `cheap_noodle_week`。
   - 新增 `mensa_coupon`。
   - 新增 `emergency_international_office`。
   - 新增 `write_formal_email_to_abh`。
   - 新增 `take_a_real_break`。

4. 必选动作初步降权
   - `budget_call` 增加 `family_support` 冷却组、收益递减、`parent_pressure` 和 `max_parent_pressure`。
   - `cook_at_home` 降低收益并保留 meal 冷却。
   - `classmate_meal` 增加 `min_social` 与 `reciprocity_debt`。
   - `international_office` 加入每周上限，并拆出高风险专用 `emergency_international_office`。
   - `therapy` 提高启用压力阈值，增强效果但增加学业机会成本。

5. 结局与 gate 口径
   - `cashflow_collapse` / `living_imbalance` 从负现金条件迁移为逾期/现金短缺条件。
   - 成功结局增加 `max_arrears`，避免“表面成功但账单爆炸”。
   - `ValidateDemoGates` 的坏成功判断改用 `arrears_amount`。

6. 自动策略口径
   - `BalancedPolicy`, `AdminPolicy`, `WorkPolicy` 从 `money < 0` 迁移到 `arrears_amount > 0`。
   - 风险建议中低钱、压力、饥饿、行政风险均指向新增危机响应动作。

### 8.2 已修改的核心文件

`study-in-germany`：

- `autoload/GameState.gd`
- `autoload/DataRegistry.gd`
- `data/actions/generated_actions.json`
- `data/endings/generated_endings.json`
- `scripts/data/ActionDef.gd`
- `scripts/data/EndingDef.gd`
- `scripts/simulation/ActionResolver.gd`
- `scripts/simulation/RiskEvaluator.gd`
- `scripts/simulation/SemesterReportBuilder.gd`
- `scripts/policies/AdminPolicy.gd`
- `scripts/policies/BalancedPolicy.gd`
- `scripts/policies/WorkPolicy.gd`
- `scripts/tools/ValidateDemoGates.gd`
- `scripts/tools/ValidateEconomyRules.gd`

### 8.3 验证结果

已通过：

```bash
/tmp/godot-docker-wrapper --headless --path /home/bo/projects/python/study-in-germany -s res://scripts/tools/ValidateEconomyRules.gd
/tmp/godot-docker-wrapper --headless --path /home/bo/projects/python/study-in-germany -s res://scripts/tools/ValidateJsonContent.gd
/tmp/godot-docker-wrapper --headless --path /home/bo/projects/python/study-in-germany -s res://scripts/tools/ValidateRiskGuidance.gd
```

结果：

```text
Economy rules validation complete
JSON content validation complete: 50 actions, 128 events, 17 endings, 5 characters
Risk guidance validation complete: 9 scenarios
```

小型模拟通过：

```bash
/tmp/godot-docker-wrapper --headless --path /home/bo/projects/python/study-in-germany -s res://scripts/tools/RunSimulation.gd -- --runs=4 --seed=7300 --policy=balanced --difficulty=normal --weeks=20 --out=reports/v03_balanced_runs.jsonl
/tmp/godot-docker-wrapper --headless --path /home/bo/projects/python/study-in-germany -s res://scripts/tools/RunSimulation.gd -- --runs=4 --seed=7400 --policy=admin --difficulty=normal --weeks=20 --out=reports/v03_admin_runs.jsonl
/tmp/godot-docker-wrapper --headless --path /home/bo/projects/python/study-in-germany -s res://scripts/tools/RunSimulation.gd -- --runs=4 --seed=7600 --policy=work --difficulty=normal --weeks=20 --out=reports/v03_work_runs.jsonl
```

抽样结果：

| policy | endings | min_money | max_arrears |
| --- | --- | ---: | ---: |
| balanced | `career_launch`, `social_connector`, `stable_start`, `work_warrior` | 1003 | 0 |
| admin | `burnout_pause` x4 | 1124 | 0 |
| work | `burnout_pause` x4 | 6774 | 0 |

### 8.4 剩余风险

1. `admin` 策略仍高度偏向 `international_office` / `emergency_international_office`，说明 P2 还需要进一步做跨周冷却、事件化反噬或策略侧“已处理行政风险”记忆。
2. 低钱/逾期危机在当前小样本中没有自然出现，说明经济止血已生效，但还需要专门跑 `zero_money` / `deep_debt` 边界场景验证失败链。
3. `food_insecurity` / `used_debt` 仍未拆为独立字段，本轮先用 `cash_shortfall_count` + `arrears_amount` + flags 承载。
4. P4 的 warning -> crisis -> collapse 事件链仍需下一轮专项补齐。
