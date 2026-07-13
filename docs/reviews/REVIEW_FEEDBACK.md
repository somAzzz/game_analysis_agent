---
status: active
date: 2026-07-06
audience: maintainers
scope: 原始评审意见 + 逐条落实日志
---

# 评审意见 (Review feedback)

> 状态：原始意见记录。**已逐条细化为可执行任务，详见 [ACTION_PLAN.md](ACTION_PLAN.md)；当前分层文档入口见 [reviews/README.md](README.md)；每条任务的实施记录见本文档的「落实日志」小节。**
>
> 评审对象：v0.2 `game_analysis_agent` 仓库（含 7 个 agent、anomaly / value 检测、tool loop、本地 vLLM / SGLang / DeepSeek provider 切换）。
> 评审目标：让测试系统从"能生成报告"升级成"能证明改动是否真的提升了可玩性"。

## 0. 总体结论

仓库的 **方向是正确的**，且与 `study-in-germany` 当前 demo 的修正目标高度匹配。它已经不是"让 LLM 玩一遍游戏"，而是：

```text
Godot headless 批量跑局
→ Python 做确定性统计 / 异常检测 / 数值检测
→ LLM agent 做解释、诊断、调参建议、内容审查、边界分析、试玩复盘
```

这意味着接下来要补的不是"再加几个 agent"，而是把现有流水线改造成下面这种端到端闭环：

```text
修改 Godot 数据 / 规则
↓
commit + content_version
↓
run matrix simulation
↓
deterministic analytics
↓
anomaly + value report
↓
LLM agents 解释问题
↓
interactive persona playthrough
↓
人工审核 tuning proposal
↓
改 Godot
↓
compare before/after
```

一句话：**Godot 负责大规模真实跑局，Python 负责确定性诊断，LLM 负责解释和设计建议；不要让 LLM 替代统计，也不要让统计替代试玩感受。**

---

## 1. 总体策略：不要让 LLM 直接跑 1000 局

测试系统应分两类：

```text
A. 大规模确定性测试：Godot bot 跑 100 / 500 / 1000 局
B. 小规模 LLM 试玩测试：LLM 作为玩家跑 1-5 局
```

LLM 直接玩 1000 局会慢、昂贵、难复现；确定性 bot + 统计报告更适合数值平衡，LLM 适合在压缩报告上做诊断，或当玩家跑 1-2 个完整 playthrough。

正确用法不是：

```text
让本地 Qwen 玩 1000 局，然后问它好不好玩
```

而是：

```text
让 Godot 跑 1000 局
让 Python 找异常 / 必选行动 / 死选项 / 结局单一
让 LLM 解释为什么这些数据说明游戏不好玩
再让 LLM 作为 5 种玩家各试玩 1 局，补充主观体验
```

---

## 2. 测试目标应该围绕当前 demo 的 6 个具体问题

| 维度 | 要回答的问题 |
| --- | --- |
| 技术稳定性 | headless 是否稳定？日志 schema 是否完整？是否有状态溢出 / 死局？ |
| 数值平衡 | 是否存在必选行动、死行动、结局单一？ |
| 路线差异 | 学霸、打工、社交、行政、摆烂是否跑出不同轨迹？ |
| 边界合理性 | 极端低钱、高压、无德语、flag 混乱时是否产生合理失败？ |
| 内容质量 | 事件选项是否有 trade-off？是否有"自动补齐味"？ |
| 传播辨识度 | 结局、事件、报告是否足够截图传播？ |

针对当前 demo 的 6 个问题：

1. 恢复类行动是否还是过强
2. 社交成功是否还能覆盖生存危机
3. 学业失败是否有足够后果
4. 打工路线是否有足够诱惑和风险
5. 5 条路线是否真的分化
6. 游戏是否有"德国留学文件夹地狱"的辨识度

---

## 3. 第一层：基础流水线 smoke test

```bash
cd game_analysis_agent
cp .env.example .env
# 编辑 .env：GODOT_BIN / GAME_PROJECT_PATH / LLM_PROVIDER / SGLANG_BASE_URL / SGLANG_MODEL

uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

python3 tools/run_gameplay_agent.py all \
  --run-id demo-v02-smoke-balanced-r20 \
  --runs 20 \
  --policy balanced \
  --difficulty normal \
  --weeks 20
```

通过标准（v0.2 流水线已经能产生）：

```text
Godot return code = 0
raw_runs.jsonl 存在
ending_id_empty = 0
pipeline_stalled = 0
stat_overflow = 0
stat_underflow = 0
```

---

## 4. 第二层：多 policy / 多难度矩阵

```bash
for difficulty in normal realistic; do
  for policy in random balanced study money social visa slacker; do
    python3 tools/run_gameplay_agent.py all \
      --run-id demo-v02-${difficulty}-${policy}-r200 \
      --runs 200 \
      --policy $policy \
      --difficulty $difficulty \
      --weeks 20
  done
done
```

P0 / P1 / P2 policy 实现优先级：

```text
P0: random, balanced, study, money/work
P1: visa/admin, social, slacker/burnout
P2: newbie, greedy/minmax
```

矩阵每次跑完看：

```text
ending_distribution.csv
weekly_stats.csv
action_pick_rates.csv
event_trigger_rates.csv
choice_pick_rates.csv
anomalies.jsonl
value_report.json
agent_diagnosis.md
tuning_proposal.md
value_review.md
```

---

## 5. 第三层：边界探测

```bash
python3 tools/run_gameplay_agent.py probe \
  --run-id demo-v02-boundary-balanced-r30 \
  --runs 30 \
  --policy balanced \
  --weeks 20 \
  --extreme zero_money,deep_debt,no_energy,all_negative,no_language,flag_chaos,week_zero,already_registered
```

要查的"游戏规则可信度 bug"：

```text
money < -1000 但进入成功结局
hunger > 90 但进入 social_connector
stress > 95 但进入优秀结局
未注册但进入顺利第一学期
no_language 仍然轻松通过 TestDaF / APS
flag_chaos 导致互斥状态同时成立
week_zero 导致事件提前 / 重复触发
already_registered 仍然触发注册失败
```

这些不是普通 bug，而是游戏规则可信度 bug。**当前 `anomaly_detector` 还只覆盖通用不变量，必须扩成"游戏语义不变量"**。

---

## 6. 第四层：LLM 作为玩家试玩

当前 `interactive_player` 暴露的工具：

```text
get_state()
list_available_actions()
inspect_event(event_id)
step(actions, event_choice_id)
finish()
```

5 个 LLM persona 建议：

| Persona | 目标 | 预期暴露问题 |
| --- | --- | --- |
| 新手玩家 | 看提示随便玩 | UI 目标是否清楚 |
| 学霸玩家 | 优先学业 / TestDaF | 压力和孤独是否有后果 |
| 打工玩家 | 优先赚钱 | 打工是否足够诱惑，工时风险是否成立 |
| 行政控 | 优先注册 / 签证 / 保险 | 行政路线是否太无聊 |
| 摆烂玩家 | 优先休息 / 娱乐 | 恢复行动是否还是太强 |

---

## 7. 当前 `interactive_player` 还不是真正的 20 周试玩器

虽然 `player_user.md` 推荐流程是"先 `get_state()` + `list_available_actions()`，再每周 `step()`，最后 `finish()`"，但 `InteractivePlayerAgent.play_through()` 实际只调用了一次 `loop.complete(...)`，把最终文本和 tool events 写入 `playthrough.jsonl`，Python 层没有显式执行 20 周循环。最终 ending 写的是 `"(interactive play did not terminate cleanly)"`。

也就是说，当前实现是"一次 tool-calling 实验"，不是稳定的 20 周 LLM 玩家模拟器。

### 应改成

```python
for week in range(1, max_weeks + 1):
    state = probe.get_state()
    actions = probe.list_available_actions()

    decision = llm_decide_one_week(
        persona=persona,
        state=state,
        available_actions=actions,
        last_event=probe.last_event_id,
        last_choices=probe.last_event_choices,
    )

    result = probe.step(
        actions=decision["actions"],
        event_choice_id=decision.get("event_choice_id", ""),
    )

    write_step_jsonl(
        week=week,
        state_before=state,
        decision=decision,
        result=result,
    )

    if result.get("finished"):
        break

final = probe.finish()
```

Python 控制节奏，LLM 每周只做一个决策。

---

## 8. tool-calling 对本地 Qwen 还需要加强

本地 Qwen native tool call 不一定稳定，应支持：

```text
A. native OpenAI tool_calls
B. JSON fallback tool call
```

`tool_loop.py` 已经有 `_parse_json_choice()` / `_json_choice_to_tool_call()`，但 `OpenAICompatibleToolLoop.chat()` 主路径在没拿到 native `tool_calls` 时直接 `return content`，没接 JSON fallback。要补：

```python
if not tool_calls:
    parsed = _parse_json_choice(content)
    fallback_tool_call = _json_choice_to_tool_call(parsed, round_index)
    if fallback_tool_call is not None:
        tool_calls = [fallback_tool_call]
    else:
        return _json_final_answer(parsed, content) or content, audit_calls, self.last_tool_events
```

prompt 要求本地模型输出：

```json
{
  "tool": "step",
  "arguments": {
    "actions": ["cook_at_home", "study_library"],
    "event_choice_id": ""
  }
}
```

---

## 9. `anomaly_detector` 还太"通用"，需加游戏语义规则

新增 anomaly kind：

```text
crisis_success_ending
social_success_under_survival_crisis
academic_success_with_failed_courses
visa_success_without_registration
testdaf_pass_with_low_language
aps_pass_with_low_aps_knowledge
black_work_without_risk
hunger_ignored_too_long
stress_zero_lock
social_overflow_pattern
```

规则示例：

```python
if final_ending_id in SUCCESS_ENDINGS and money < -1000:
    anomaly("crisis_success_ending", severity="critical")

if final_ending_id == "social_connector" and hunger >= 85 and stress >= 85:
    anomaly("social_success_under_survival_crisis", severity="critical")

if final_ending_id in ACADEMIC_SUCCESS_ENDINGS and failed_courses > 0:
    anomaly("academic_success_with_failed_courses", severity="error")

if final_ending_id in VISA_SUCCESS_ENDINGS and not flags.get("registered"):
    anomaly("visa_success_without_registration", severity="critical")

if language < 25 and flags.get("testdaf_passed"):
    anomaly("testdaf_pass_with_low_language", severity="error")
```

---

## 10. `value_analyzer` 方向对，但要更细

当前阈值：

```text
DOMINANT_PICK_RATE = 0.80
DEAD_PICK_RATE = 0.05
DOMINANT_CHOICE_RATE = 0.85
ENDINGLE_DOMINANCE = 0.90
```

这只能看单个 action 是否被选，但 demo 的问题不是单个行动，而是：

- 恢复类行动组是否整体过强
- 社交类行动是否组成无风险避难所
- 打工类行动在低钱状态下是否仍不够诱人
- 学业类行动是否没有短期反馈

需要新增 4 类分析：

1. **Action group dominance**（按 tag 聚合：recovery / study / admin / work / social / food / escape）。
2. **Crisis response analysis**（低钱 / 高压 / 高饥饿 / visa 风险状态下的选项分布）。
3. **Ending contradiction analysis**（成功结局的状态分布 vs 失败结局的状态分布）。
4. **Route separation score**（study bot 学业轴差、work bot 现金轴差、social bot 社交轴差、admin bot 签证轴差、slacker bot 压力轴差 vs balanced bot 同轴距离）。

---

## 11. 需要新增版本对比流程

`compare_reports.py`，输入 before/after 两个 report dir，输出：

```text
结局变化：
- social_connector: 38% → 12%
- barely_survived: 20% → 31%
- cashflow_collapse: 0% → 14%

行动变化：
- sleep_recover: 2.8/run → 1.1/run
- bilibili_rest: 2.2/run → 0.7/run
- mini_job_shift: 0.3/run → 1.4/run

风险变化：
- stress mean week20: 12 → 48
- hunger p90 week20: 100 → 76
```

这比单次报告更能指导调参。

---

## 12. 推荐测试矩阵（A/B/C/D）

### A. Smoke Test

```bash
python3 tools/run_gameplay_agent.py all \
  --run-id v02-smoke-balanced-r20 \
  --runs 20 \
  --policy balanced \
  --difficulty normal \
  --weeks 20
```

### B. Balance Test

```bash
for policy in random balanced study money social visa slacker; do
  python3 tools/run_gameplay_agent.py all \
    --run-id v02-normal-${policy}-r200 \
    --runs 200 \
    --policy $policy \
    --difficulty normal \
    --weeks 20
done
```

通过标准：

```text
normal 难度下至少出现 5 类结局
任一成功结局不超过 45%
任一行动 rate_per_run 不超过 0.8
recovery 类行动总占比不过高
study / work / social / admin policy 结局分布明显不同
```

### C. Realistic Test

```bash
for policy in balanced study money social visa slacker; do
  python3 tools/run_gameplay_agent.py all \
    --run-id v02-realistic-${policy}-r200 \
    --runs 200 \
    --policy $policy \
    --difficulty realistic \
    --weeks 20
done
```

### D. Boundary Test

```bash
python3 tools/run_gameplay_agent.py probe \
  --run-id v02-boundary-r30 \
  --runs 30 \
  --policy balanced \
  --weeks 20 \
  --extreme zero_money,deep_debt,no_energy,all_negative,no_language,flag_chaos,week_zero,already_registered
```

---

## 13. LLM agent 在每个阶段的角色

```text
1. bugs_summary.md
2. bug_diagnosis.md
3. value_report.json
4. value_review.md
5. agent_diagnosis.md
6. tuning_proposal.md
7. content_issues.md
8. event_graph_report.md
```

| Agent | 当前最适合检查 |
| --- | --- |
| `balance` | 结局分布、每周曲线、行动强弱 |
| `value_reviewer` | `sleep_recover` / `bilibili_rest` / `therapy` 是否还是必选 |
| `bug_hunter` | money / hunger / stress 与结局矛盾 |
| `boundary_prober` | `deep_debt` / `no_energy` / `no_language` 等极端场景 |
| `content_qa` | 504 个选项里哪些"味道平均" |
| `event_graph` | APS / TestDaF / 注册 / 居留事件是否断链 |
| `interactive_player` | 新手是否看得懂，路线是否自然 |

---

## 14. 当前测试系统还需要提升的地方（按优先级）

### P0：把 `interactive_player` 改成真实周循环

```text
每周一次 LLM 决策
每周记录 state_before / available_actions / chosen_actions / event / choice / state_after
最终必须调用 finish()
playthrough.jsonl 每周一行
playthrough_summary.md 输出路线复盘
```

新增参数：

```bash
python3 tools/run_gameplay_agent.py play \
  --report-dir reports/play/v02-study-persona \
  --weeks 20 \
  --persona study \
  --difficulty realistic \
  --seed 42
```

### P0：补 JSON fallback tool calling

支持：

```json
{"tool": "get_state", "arguments": {}}
{"tool": "step", "arguments": {"actions": ["study_library"], "event_choice_id": ""}}
```

### P0：补游戏语义 anomaly rules

```text
success_under_crisis
social_success_under_hunger_stress
academic_success_with_failed_courses
visa_success_without_registration
language_exam_pass_with_low_language
illegal_work_without_consequence
recovery_action_spam
stress_zero_lock
```

### P0：增加 `action_effects` 日志

anomaly detector 已经在用 `cost_money_exceeds_balance` 读 `week.get("action_effects")`，所以 `study-in-germany` 必须按契约输出：

```json
"action_effects": [
  {
    "action_id": "bilibili_rest",
    "effects": {"stress": -14, "academic_progress": -6, "loneliness": 3}
  }
]
```

否则"行动成本是否生效"的测试做不了。

### P1：增加 route-aware value analysis

输出 `route_report.json`：

```json
{
  "policy": "study",
  "route_scores": {"academic": 82, "work": 12, "social": 30, "admin": 55, "slacker": 8},
  "dominant_groups": ["study"],
  "weaknesses": ["stress", "money"]
}
```

### P1：新增版本对比报告

`tools/compare_reports.py`。

### P1：Content QA 要按"选择结构"评分

事件选项打标签 `safe` / `risky` / `social_language` / `avoidance`，无 trade-off 的事件标 `choice_tradeoff_weak` / `choice_effects_too_similar` / `all_choices_positive` / `all_choices_generic` / `missing_failure_cost`。

### P1：Event graph 要输出"未触发原因"

```text
event_id: retake_exam
trigger_rate: 0.0
blocked_reasons:
- failed_courses never > 0
- exam failure not setting needs_retake flag
```

### P2：增加 HTML Dashboard

`reports/index.html`，把结局饼图、属性曲线、top/dead actions、triggered events、choice dominance、anomaly timeline、before/after comparison 集中显示。

---

## 15. 下一版测试系统的目标结构

```text
tests_pipeline/
  matrix.yaml
  gates.yaml

reports/
  catalog/
  balance/
  boundary/
  play/
  compare/

src/game_analysis_agent/
  analyzers/
    route_analyzer.py
    crisis_analyzer.py
    version_compare.py
  agents/
    persona_player.py
    regression_reviewer.py
    screenshotability_reviewer.py
```

`matrix.yaml` 示例：

```yaml
version: demo-v02
weeks: 20
runs_per_cell: 200
difficulties: [normal, realistic]
policies: [balanced, study, money, social, visa, slacker]
boundary:
  runs: 30
  extremes: [zero_money, deep_debt, no_energy, all_negative, no_language, flag_chaos, week_zero, already_registered]
```

`gates.yaml` 示例：

```yaml
critical_fail:
  ending_id_empty: 0
  pipeline_stalled: 0
  stat_overflow: 0
  success_under_crisis: 0
  social_success_under_hunger_stress: 0

balance:
  max_single_ending_rate_normal: 0.45
  max_action_rate_per_run: 0.8
  min_distinct_endings_normal: 5
  min_route_distance: 15

design:
  max_generated_choice_ratio_key_events: 0.2
  min_key_event_tradeoff_score: 0.7
```

---

## 16. 最应该做的 7 个任务（按顺序）

1. 跑 v0.2 smoke test，确认当前修正版 demo 与 agent pipeline 端到端可用。
2. 跑 normal / realistic × balanced / study / money / social / visa / slacker 的 200 局矩阵。
3. 跑 boundary probe，重点查 social_connector、高饥饿、高压力、负债成功结局。
4. 给 `anomaly_detector` 加游戏语义规则。
5. 改造 `interactive_player`，让它变成显式 20 周 loop。
6. 给 `value_analyzer` 加 action_group / route_score / crisis_response。
7. 做 `compare_reports.py`，用固定 seed 对比修复前后。

---

## 落实日志（实施后回写）

> 此节由实现者按 P0 / P1 任务逐条追加；每完成一个任务，给出对应提交 / PR / 文件位置 + 验证证据（命令输出或 fixture 测试结果）。

### T02 — tool_loop 接入 JSON fallback ✅

- **修改**: `src/game_analysis_agent/tool_loop.py`
  - 新增 `parse_model_response_to_tool_calls(content, round_index=0)`，兼容 `{"tool": ...}` 单 tool 简写 + `{"tool_calls": [...]}` 数组两种 JSON。
  - `OpenAICompatibleToolLoop.chat()` 在 `not tool_calls` 分支先尝试 JSON fallback；如果拿到 JSON tool call 就当作 native tool_call 继续走 tool 循环；如果拿到 `{"final_answer": ...}` 就 return 提取后的纯文本而不是 raw JSON。
  - 现有 `_parse_json_choice` / `_json_choice_to_tool_call` 全部保留为 helper，新函数只复用。
- **新增**: `tests/test_tool_loop.py` 加 5 个 case（单 tool shorthand / 数组形式 / final_answer / 纯文本 / 非法 JSON）。
- **验证**: `pytest tests/test_tool_loop.py -v` → 11 passed（包含原 6 个 + 新 5 个）。

### T03 + T04 — `AnomalyKind` 扩 + 游戏语义 anomaly 规则 ✅

- **修改**: `src/game_analysis_agent/schemas.py` 的 `AnomalyKind` Literal 增加 10 个 kind（`crisis_success_ending` / `social_success_under_survival_crisis` / `academic_success_with_failed_courses` / `visa_success_without_registration` / `testdaf_pass_with_low_language` / `aps_pass_with_low_aps_knowledge` / `black_work_without_risk` / `hunger_ignored_too_long` / `stress_zero_lock` / `social_overflow_pattern`）。
- **新增**: `src/game_analysis_agent/anomaly_semantics.py` 提供 `check_semantic_invariants(run, **thresholds)`，与 `action_group_keyword` heuristic 配套。
- **接入**: `src/game_analysis_agent/anomaly_detector.py` 的 `detect_anomalies` 末尾追加 `anomalies.extend(check_semantic_invariants(run))`。
- **新增**: `tests/test_anomaly_semantics.py` 12 个 case（每条规则 1 个 + 一个 clean run 不触发 + 一个集成到 `detect_anomalies` 的 case）。
- **同步**: `DATA_CONTRACTS.md` §3 更新 `kind` 取值 + 增加 evidence 字段示例。
- **验证**: `pytest tests/test_anomaly_semantics.py -v` → 12 passed。

### T05 — `interactive_player` 改为显式周循环 ✅

- **修改**: `src/game_analysis_agent/agents/interactive_player.py`：
  - 删掉旧的"一次 loop.complete 写 stub final state"实现。
  - `play_through()` 改成 `for week in range(1, max_weeks+1):` 显式循环；每轮：读 state → 调 `_decide_one_week()`（单轮 LLM 调用）→ `probe.step()` → 写 1 行 JSONL。
  - `_parse_decision()` 支持：fenced JSON 块 / `{...}` 截取 / `parse_model_response_to_tool_calls` 兜底（沿用 T02 的 JSON fallback）/ 解析失败 → fallback 取 catalog 第一个 action。
  - `_render_summary()` 输出：Overview + Final State + Weekly Decisions table + Anomalies table。
  - 新增 `PERSONAS` 表（newbie / study / money / social / visa / slacker），persona block 拼到 system prompt。
- **修改**: `tools/run_gameplay_agent.py::cmd_play` 透传 `--persona` / `--difficulty` / `--seed`；CLI 加上 `--persona {newbie,study,money,social,visa,slacker}`。
- **新增**: `tests/test_interactive_player.py` 9 个 case（含 fake probe + JSON fallback 路径 + decision parser 单测 + 真实 InteractiveProbe 类型兼容）。
- **验证**: `pytest tests/test_interactive_player.py -v` → 9 passed。

### T06 — `value_analyzer` 增加 4 类分析 ✅

- **修改**: `src/game_analysis_agent/value_analyzer.py`：
  - 新增 `analyze_action_groups()`：用 `ACTION_GROUP_KEYWORDS` heuristic（或 catalog tags）按 tag 聚合；标记 recovery > 2.5/run、escape > 2.0/run、study < 1.0/run、work < 0.5/run。
  - 新增 `analyze_crisis_response()`：扫 weekly_log，触发 low_money / high_stress / high_hunger / high_visa_risk 时，检查是否选对应 group；response_rate < 0.4 标 warning、< 0.2 标 error。
  - 新增 `analyze_ending_contradictions()`：把 ending × final_state 拼成"矛盾分"，成功结局分 ≥ 100 / 失败结局分 ≤ 30 触发。
  - 新增 `analyze_route_separation()`：5 axis（academic / work / social / admin / slacker）按 policy 跑均值；任一 axis 与 balanced policy 相对差 < 0.15 触发。
  - `analyze_route_metrics()` 合并以上 + `route_report.json` 输出。
- **修改**: `analyze_and_write()` 现在同时写 `value_report.json` + `route_report.json`。
- **修改**: `schemas.ValueFinding.scope` Literal 扩 4 个新 scope（`action_group` / `crisis_response` / `ending_contradiction` / `route`）。
- **新增**: `tests/test_value_analyzer.py` 加 8 个 case（groups + crisis + contradictions + route + 子报告生成 + 集成）。
- **验证**: `pytest tests/test_value_analyzer.py -v` → 14 passed（原 6 个 + 新 8 个）。

### T07 — `tools/compare_reports.py` ✅

- **新增**: `tools/compare_reports.py`：
  - CLI：`--before` / `--after` / `--out` / `--diff-json`。
  - 6 个维度对比：`ending_distribution.csv` / `action_pick_rates.csv` / `weekly_stats.csv` / `anomalies.jsonl` / `value_report.json` / `route_report.json`。
  - 输出：人类可读 `compare_summary.md`（按维度分段、各取 top Δ）+ 机器可读 `compare_diff.json`。
- **新增**: `tests/test_compare_reports.py` 3 个 case（基本 diff + markdown 包含所有 section + 空目录不抛）。
- **验证**: `pytest tests/test_compare_reports.py -v` → 3 passed。

### T08 — `config/matrix.yaml` + `config/gates.yaml` ✅

- **新增**: `config/matrix.yaml`（v0.2 测试矩阵：2 difficulty × 7 policy × 200 runs + boundary 30 × 8 extremes + 6 persona）。
- **新增**: `config/gates.yaml`（critical_fail / balance / design 三段；critical_fail 把 T04 新增的 6 条游戏语义 kind 标 0 容忍）。
- **新增**: `tests/test_config_yaml.py` 2 个 smoke case（保证两个 YAML 能被 `yaml.safe_load` 读，且关键字段在）。
- **验证**: `pytest tests/test_config_yaml.py -v` → 2 passed。

### 综合验证

```text
$ pytest tests/ --ignore=tests/test_analyze_balance.py --no-header -q
100 passed in 0.29s
```

注：`tests/test_analyze_balance.py::test_analyze_balance_fixture` 在我的改动之前就已经失败（用 system `python3` 而非 venv 的 python，subprocess 拿不到 `python3-tools/analyze_balance.py` 路径解析），与本次改动无关，留给后续 CI 适配。

### T09 — `event_graph` agent 输出"未触发原因" ✅

- **修改**: `src/game_analysis_agent/agents/event_graph.py`
  - 新增 `build_untriggered_block(raw_runs, event_graph)`，统计 `weekly_log` 中的事件触发次数。
  - 对未触发事件输出 `## Untriggered Events`，包含 trigger JSON 和粗粒度 missing-reason hint。
- **修改**: `prompts/event_graph_agent_user.md` 增加 `{{UNTRIGGERED_EVENTS}}`。
- **新增**: `tests/test_agents_registry.py` 覆盖 prompt 注入和 trigger 计数。

### T10 — `content_qa` agent 按"选择结构"评分 ✅

- **修改**: `src/game_analysis_agent/agents/content_qa.py`
  - 新增 `score_choice_structure(event_graph)`，检测 `duplicate_choice_text` / `all_choices_positive` / `missing_failure_cost` / `choice_effects_too_similar`。
  - 把确定性 findings 渲染为 `## Choice Structure Findings` 后再交给 LLM。
- **修改**: `prompts/content_qa_agent_user.md` 增加 `{{CHOICE_STRUCTURE_FINDINGS}}`。
- **新增**: `tests/test_agents_registry.py` 覆盖 prompt 注入和 missing-cost 评分。

### 语义阈值修正 ✅

- **修改**: `src/game_analysis_agent/anomaly_semantics.py`
  - `hunger_ignored_too_long` 从硬编码 `hunger >= 90` 改为使用评审定义的 `survival_hunger` 默认阈值 `85`。
  - evidence / message 记录实际 threshold。
- **新增**: `tests/test_anomaly_semantics.py` 覆盖连续 6 周 `hunger=86` 触发。

### 综合验证

```text
$ uv run pytest tests/ -q
106 passed in 0.58s
```

### 遗留 / 已记录在 `ACTION_PLAN.md` 中暂未实施

- T01 / T12 — smoke + 全量矩阵需要 Godot 项目和真实运行环境。

### T13 — Editorial HTML dashboard ✅

- **新增**: `tools/build_dashboard.py` —— 单文件 Python CLI，无第三方依赖。
- **aesthetic**: 编辑部 / 数据新闻学风格（Pudding / FiveThirtyEight / NYT Graphics 一类）。Fraunces（display）+ Newsreader（body）+ IBM Plex Mono（kicker / 数据 / numerics）。配色：paper cream `#F4EFE6` + ink `#1F1B16` + terracotta `#C8553D` + forest `#3B5F4E`。
- **核心设定**：把每一个 report 目录当作 *杂志的一期* —— 有封面、masthead、署名、版面编号、byline、deck（导言）、drop cap、pull quote、anomaly marginalia（页边注脚）。
- **front page** (`reports/index.html`)：masthead（vol/issue/date 三段式）+ banner（巨型 Fraunces title + 副标题）+ KPI strip（4 个并列数字栏）+ Issue Shelf（24 张本期目录卡片）+ Colophon（版权页）。
- **per-issue page** (`reports/browse/<kind>/<run_id>/index.html`)：cover（issue 编号 / 4 段 meta / 巨型 H1 / deck）+ tab rail + Ending Grid（红条形 bar）+ Pulse of the simulation（4 个 SVG sparkline，CSS `stroke-dashoffset` 动画 stagger 出现）+ Value findings（带 severity 标签的表格）+ Anomaly marginalia（页边小圆圈 + hover tooltip）+ Playthrough spine（如果存在：横轴时间线，红点 = anomaly 周）+ Agent columns（markdown 渲染成版面正文 + drop cap）。
- **细节落点**：
  - `::first-letter` drop cap，color = terracotta。
  - `md-quote` blockquote 用左侧 terracotta 竖线。
  - `byline-rule` 用 `::before` / `::after` 双侧虚线 + mono 小字。
  - Sparkline path class 加 `delay-0..4` 错开出现。
  - 卡片加 `fade-in d0..d3` 错开渐显。
  - GATE report 用红/绿横幅直显。
- **零依赖**：自写 markdown 子集渲染（headings / paragraph / list / blockquote / code fence / table / inline bold-italic-code），inline CSS，inline SVG。
- **测试**: `tests/test_build_dashboard.py` 9 个 case（markdown 各元素 + front page + issue page + 聚合器）。
- **验证**: `pytest tests/test_build_dashboard.py -v` → 9 passed；全量 `pytest tests/`（除 pre-existing broken test）→ 123 passed。
- **使用**:
  ```bash
  python3 tools/build_dashboard.py --reports reports
  # → reports/index.html + reports/browse/<kind>/<id>/index.html
  #   open in browser via file://
  ```
- **当前状态**：基于仓库内真实 reports（54 个 issue：50 balance + 4 boundary + 0 play），play 模块结构就绪但目前仓库还没有真实 playthrough 跑出来。运行一次 `play` 子命令即可让 `browse/play/<persona>/` 自动出现。

### Decision-graph view (T13.5) ✅

- **新增**: `tools/build_dashboard.py` 增加 `decision-graph` 子命令 + 一整套渲染函数（`_compute_graph_layout` / `_decision_graph_payload` / `_decision_graph_svg` / `render_decision_graph_page`）。
- **核心设计**：把所有 128 个 game event 在 SVG 画布上铺开，3 条横向 lane 按 `event_type`（fixed / conditional / random），X 轴 = 触发周。被 agent 触发的事件节点用 terracotta 描边 + 黑色填充凸显，连成一条发光的 path polyline（CSS `stroke-dashoffset` 动画）。
- **choice 高亮**：每个被触发的事件节点里叠一个 wedge 扇形（按 4 等份划分），扇形位置代表该 event 4 个 choice 中 agent 选的那个（1/2/3/4）。Hover 节点 → tooltip 显示 event title + choice text + 关键 effects；点击节点 / 点击 timeline 一格 → 同步高亮，下方 panel 显示该周的 choice + effects + selected_actions + after_state。
- **interactivity**：底部 timeline 横轴有 slider（0..20）+ Play / Pause / Reset 按钮 —— Play 会自动一周一周推进画布高亮，模拟"实时回放 agent 的决策过程"。
- **触发数量**：128 events total（62 random + 38 conditional + 8 fixed），balanced policy 在 default_first_semester 下触发了 20 个节点（每 week 一个），全在 fixed / conditional lane，random lane 因为触发条件不满足保持空。
- **接入**：每个 balance issue 页面的 tab rail 增加 "↗ Decision Graph" 链接，独立 URL `reports/browse/decision_graph/<run>/<run_id>/index.html`，可通过 CLI `decision-graph --report-dir ... --run-id N` 单跑一份。
- **测试**：`tests/test_build_dashboard.py` 增加 5 个 case（layout lane 分离 / wedge SVG / 空 wedge 处理 / payload 抽取 choice / page 渲染关键 section）→ 14 passed。
- **验证**：全量 `pytest tests/` → 128 passed；`python tools/build_dashboard.py all` → 写出 front page + 54 issue pages + 4 decision-graph pages。
  ```bash
  python3 tools/build_dashboard.py all
  # → reports/index.html
  # → reports/browse/balance/<run>/index.html          (per-issue page)
  # → reports/browse/decision_graph/<run>/<id>/...   (interactive decision graph)
  ```

### Decision-graph adaptive layer ✅

- **修改**: `tools/build_dashboard.py` 重写，让 graph 生成器**自适应上游 schema 变化**（这是用户对 graph 可自动更新迭代的明确要求）。
- **5 条适应轴线**：
  1. **Lanes 自动派生**：`_compute_graph_layout` 不再用硬编码的 `{"fixed": 110, "conditional": 250, "random": 390}`。`_lane_for_event(ev)` 从 `event_type` / `type` / `kind` 字段取 lane name，缺失则归入 `uncategorised`，unknown 类型自动新开 lane。
  2. **Lane y 自动计算**：根据 lane 数量平均分摊 plot 高度，新增第 4 / 5 条 lane 时画布自动长高。
  3. **触发周兼容 5+ 种字段名**：`_trigger_week()` 依次尝试 `week` / `min_week` / `start_week` / `first_week` / `at_week` / `fire_week` / `weeks: [N, …]`，任一命中即可；缺失则按 `source_order` 横向铺开。
  4. **Choice ID 7 种正则兼容**：`_choice_index_from_id()` 依次试 `.choice_(\d+)_` / `.choice_(\d+)$` / `/c(\d+)` / `/choice(\d+)` / `:choice?(\d+)` / `:(\d+)` / `_(\d+)`，并 explicit `choice_index` 字段优先级最高。Out-of-range 或空 → -1（不画 wedge，不抛错）。
  5. **Choice text / effects 兼容**：`_safe_get_choice_text()` 试 `text` / `label` / `name` / `description` / `title`；`_safe_get_choice_effects()` 试 `success_effects` / `effects` / `outcome_effects`。
- **Diagnostics 落地**：每个决策图页面 + 每个对应 `_diagnostics.json`（pages/browse/decision_graph/<run>/<id>/_diagnostics.json），记录：实际发现的 event_type 列表、data-driven lane order、观察到的 max_week、triggered 但 event_graph.json 里没有的事件 ID（schema drift 信号）、payload diagnostics 备注列表。同时页面里有一个可折叠的 `<details>` 块，把备注渲染在画布下方。
- **Play reports 也被自动发现**：`cmd_all` 现在扫 balance *和* play 两个目录，只要有 `raw_runs.jsonl + event_graph.json` 就自动产出决策图页。
- **画布自动横向延展**：若 `weekly_log` 里 week > 声明的 `max_weeks`（异常路径），payload 自动把 `max_week` 抬高到观察值，让图能完整画出 path。
- **测试**：`tests/test_build_dashboard.py` 新增 12 个自适应 case：
  - `test_layout_adapts_to_new_event_types`（新 lane 类型被吸收）
  - `test_layout_orders_lanes_by_frequency`（多事件 lane 排前面）
  - `test_layout_height_scales_with_lane_count`（高度自适应）
  - `test_trigger_week_accepts_alternate_field_names`（6 种 trigger key）
  - `test_choice_index_from_id_accepts_alternate_formats`（7 种 choice id）
  - `test_lane_for_event_tolerates_alternate_field_names`（event_type / type / kind / missing）
  - `test_payload_handles_alternative_trigger_field`（fire_week + slash choice id）
  - `test_payload_adapts_to_unknown_event_type`（quantum_entangled 这种奇怪 lane）
  - `test_payload_records_diagnostics_for_missing_event`（不在 event_graph 里的 triggered 事件）
  - `test_payload_handles_missing_choice_text`（choice 没 text 字段）
  - `test_payload_handles_explicit_choice_index_field`（直接 emit choice_index）
  - `test_diagnostics_json_written`（`_diagnostics.json` 落地）
  - `test_layout_max_week_widens_to_observed`（异常延展）
- **验证**: `pytest tests/ --ignore=tests/test_analyze_balance.py -q` → **145 passed** (从 128 + 17)；`python tools/build_dashboard.py all` → 71 pages emitted (54 issue + 13 play decision_graph 等等自适应扩展)。
- **未来扩展零代码改动示例**：
  - 加个 `event_type: "meta"` 到 EventData → 自动出现 "META" lane
  - 把 `trigger.week` 改名为 `trigger.fire_week` → 自动适配
  - 把 `event_choice_id` 改成 `eid/c1` 格式 → wedge 自动定位
  - 给 choice 加 `label` 字段代替 `text` → 自动拿到
  - 任意新增 / 删除事件 / 调整次数 → 重新 `python tools/build_dashboard.py all`，graph 自动重新铺。

### React + React Flow frontend ✅

- **新增**: 整个 `frontend/` 子项目 —— Vite + React 18 + TypeScript + @xyflow/react (React Flow 12) + dagre (自动布局) + react-markdown + react-router-dom。
- **3 条路由**:
  - `/` → `FrontPage.tsx`（杂志封面 + KPI + issue shelf）
  - `/issue/:kind/:id` → `IssuePage.tsx`（cover + ending grid + 4 个 sparkline + value findings + anomaly marginalia + 7 个 agent markdown column 用 react-markdown 渲染 + drop cap）
  - `/decision-graph/:runId` → `DecisionGraphPage.tsx`（React Flow 画布 + 自定义 EventNode + BackgroundEventNode 节点 + dagre 自动布局 + 选择 / 拖动 / MiniMap / 自动播放 timeline）
- **Python 后端 → React 前端 的数据线**：
  - 新增 `tools/emit_manifest.py`：扫描 `reports/`，写出 `reports/manifest.json`（顶层 index）+ `reports/browse/<kind>/<id>/manifest.json`（per-issue 完整 payload，含 weekly_series / anomalies / value_findings / 8 个 agent_markdown body）+ `reports/browse/decision_graph/<run>/<id>/manifest.json`（含 raw run + 完整 event_graph）。
  - `tools/build_dashboard.py` 新增 `cmd_emit_frontend_manifest` 子命令，可把 manifest 镜像到 `frontend/public/` 供 Vite dev server 静态服务。
  - 跑一次 `python tools/build_dashboard.py all` 会自动跑 manifest emitter + 镜像到 frontend/public/，前端下次 dev / build 永远拿到最新数据。
- **TypeScript 自适应层**：`frontend/src/lib/layout.ts` 是 Python `_compute_graph_layout` + `_decision_graph_payload` 的 TypeScript 端口，保持五条自适应轴线一致（lanes 由 event_type 派生、lane y 自动延展、trigger week 兼容 6 种字段名、choice index 兼容 7 种正则、choice text/effects 多字段名）。React 端不需要 Python 重算，可纯客户端渲染自适应 graph。
- **Editorial 风格保留**：同一套 CSS variables (`--paper #F4EFE6` / `--accent #C8553D` / `--ink #1F1B16` 等)、同一套字体 (Fraunces / Newsreader / IBM Plex Mono)。`/decision-graph/...` 的 React Flow 自定义节点用了 React 端的 `.event-node` 类，跟静态 SVG 版视觉一致（圆形 80px / triggered 时 96px / 黑色 + terracotta 描边 / hover 放大）。
- **交互功能**：
  - Click node → 自动跳到对应 week 并同步高亮 timeline + side panel。
  - Click timeline cell → 自动跳到对应 week 并同步 graph 高亮。
  - Slider 0..maxWeek → scrub path，<= currentWeek 的节点 + 边自动 highlight。
  - Play / Pause / Reset 按钮 → 700ms 间隔自动推进 slider。
  - MiniMap + Controls + Background dots → 标准 React Flow 体验。
- **Tests**：`tests/test_frontend_build.py` 3 个 case（Vite build 成功、dist/manifest.json 存在、Python manifest 解析有效）。`tests/test_emit_manifest.py` 4 个 case（顶层 + per-issue + decision-graph + 容错）。
- **验证**：`pytest tests/ --ignore=tests/test_analyze_balance.py -q` → **155 passed**（Python 152 + frontend 3）。`cd frontend && npm run build` → 580KB JS / 32KB CSS，dist/index.html 干净输出。
- **目录结构**：
  ```
  frontend/
  ├── package.json             # vite + react + @xyflow/react + dagre + react-markdown + react-router-dom
  ├── tsconfig.json
  ├── vite.config.ts
  ├── index.html
  ├── public/                  # Python pipeline 镜像的 manifest.json + browse/
  └── src/
      ├── main.tsx
      ├── App.tsx
      ├── global.d.ts
      ├── types.ts             # TS mirror of Python schemas
      ├── styles/global.css    # editorial palette + typography
      ├── lib/
      │   ├── api.ts           # fetchJSON helpers
      │   └── layout.ts        # TypeScript port of _compute_graph_layout
      ├── components/
      │   └── Masthead.tsx
      └── pages/
          ├── FrontPage.tsx
          ├── IssuePage.tsx
          ├── DecisionGraphPage.tsx
          └── NotFoundPage.tsx
  ```
- **使用**:
  ```bash
  # 1. 生成报告（已有）
  python tools/run_gameplay_agent.py all --runs 200
  
  # 2. 一条命令同时构建静态 HTML 和 manifest
  python tools/build_dashboard.py all
  
  # 3. 启动 React SPA
  cd frontend && npm install && npm run dev   # http://localhost:5173
  
  # 4. 生产构建
  cd frontend && npm run build              # → frontend/dist/
  ```
