# 评审意见 (Review feedback)

> 状态：原始意见记录。**已逐条细化为可执行任务，详见 [docs/ACTION_PLAN.md](ACTION_PLAN.md)；当前分层文档入口见 [docs/review/README.md](review/README.md)；每条任务的实施记录见本文档的「落实日志」小节。**
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
- **同步**: `docs/DATA_CONTRACTS.md` §3 更新 `kind` 取值 + 增加 evidence 字段示例。
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

### 遗留 / 已记录在 `docs/ACTION_PLAN.md` 中暂未实施

- T01 / T12 — smoke + 全量矩阵需要 Godot 项目和真实运行环境；
- T13 — HTML dashboard（P2）。
