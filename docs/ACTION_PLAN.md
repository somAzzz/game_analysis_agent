# 行动计划 (Action Plan)

> 来自评审 [docs/REVIEW_FEEDBACK.md](REVIEW_FEEDBACK.md)。每条任务都有：
> - **目标**：评审里到底要解决什么
> - **实现位置**：文件 / 函数
> - **验证手段**：单元测试 / 命令 / 期望输出
> - **回写**：完成时把 commit / 路径 / 验证结果写到 [REVIEW_FEEDBACK.md 的落实日志](REVIEW_FEEDBACK.md#落实日志实施后回写)
>
> 优先级 P0 = 必须做；P1 = 强烈建议；P2 = 锦上添花。
> 实施顺序按依赖关系排，跨任务的依赖会显式标注。

## 总览

| ID | 优先级 | 任务 | 涉及文件 | 依赖 |
| --- | --- | --- | --- | --- |
| T01 | P0 | 跑 v0.2 smoke test，确认端到端流水线 | 仅命令 | — |
| T02 | P0 | 给 `tool_loop` 接入 JSON fallback | `src/game_analysis_agent/tool_loop.py`, `tests/test_tool_loop.py` | — |
| T03 | P0 | 在 `schemas.AnomalyKind` 增补游戏语义 kind | `src/game_analysis_agent/schemas.py` | — |
| T04 | P0 | `anomaly_detector` 加游戏语义规则 | `src/game_analysis_agent/anomaly_detector.py`, `tests/test_anomaly_detector.py`, `tests/fixtures/anomaly_runs.jsonl` | T03 |
| T05 | P0 | `interactive_player` 改为显式周循环 | `src/game_analysis_agent/agents/interactive_player.py`, `tools/run_gameplay_agent.py`, `prompts/player_user.md`, `tests/test_runner.py` | T02 |
| T06 | P0 | `value_analyzer` 加 action group / crisis / ending contradiction / route separation | `src/game_analysis_agent/value_analyzer.py`, `tests/test_value_analyzer.py` | T03 |
| T07 | P0 | 新增 `tools/compare_reports.py` | `tools/compare_reports.py` | T04, T06 |
| T08 | P1 | `config/matrix.yaml` + `config/gates.yaml` | `config/matrix.yaml`, `config/gates.yaml` | — |
| T09 | P1 | `event_graph` agent 输出"未触发原因" | `src/game_analysis_agent/agents/event_graph.py`, `prompts/event_graph_agent_user.md` | — |
| T10 | P1 | `content_qa` agent 按"选择结构"评分 | `src/game_analysis_agent/agents/content_qa.py`, `prompts/content_qa_agent_user.md` | — |
| T11 | P1 | `play` CLI 支持 `--persona` / `--difficulty` / `--seed` | `tools/run_gameplay_agent.py` | T05 |
| T12 | P2 | 跑全量矩阵（balance + boundary）记录到 reports/ | 命令 | T01, T04, T06 |
| T13 | P2 | HTML dashboard | `tools/build_dashboard.py` | T07 |

---

## T01. 跑 v0.2 smoke test（P0，无代码改动）

### 目标
确认 `study-in-germany` + `game_analysis_agent` 端到端流水线能产出全部 12 类报告。

### 步骤
1. `cp .env.example .env`，按本地环境填 `GAME_PROJECT_PATH` / `LLM_PROVIDER` / `*_BASE_URL` / `*_MODEL`。
2. 准备 Python 虚拟环境：`uv venv .venv && source .venv/bin/activate && uv pip install -e ".[dev]"`。
3. 启动本地 LLM（vLLM / SGLang 任一），`curl $VLLM_BASE_URL/models` 验证。
4. 跑：

   ```bash
   python3 tools/run_gameplay_agent.py all \
     --run-id v02-smoke-balanced-r20 \
     --runs 20 --policy balanced --difficulty normal --weeks 20
   ```

### 验证
- Godot return code = 0
- `reports/balance/v02-smoke-balanced-r20/` 下存在 12 个预期文件
- `bugs.jsonl` 0 行 `pipeline_stalled` / `ending_id_empty`

### 失败处置
- Godot 找不到：检查 `GODOT_BIN` / `GAME_PROJECT_PATH`，并确认 `study-in-germany/scripts/tools/RunSimulation.gd` 存在。
- LLM 调用失败：检查 base_url / api_key，把 `AGENT_TEMPERATURE` 降到 0.0 复测一次。

---

## T02. `tool_loop` 接入 JSON fallback（P0）

### 目标
当本地 Qwen 没返回 native `tool_calls` 时，从 `content` JSON 兜底解析；支持 `{"tool": ..., "arguments": ...}` 与 `{"tool_calls": [...]}` 两种 JSON 模式。这能解决评审第 8 节的问题。

### 设计
- 在 `OpenAICompatibleToolLoop.chat()` 主路径的 `if not tool_calls: return content, ...` 之前，插入 JSON fallback 解析。
- 用现有的 `_parse_json_choice()` / `_json_choice_to_tool_call()`。
- 如果 JSON 中同时存在 `tool` 字段和 `final_answer` 字段，优先把 `tool` 当作 tool call，把 `final_answer` 留到下一轮；不要让"我打算回答 X"和"我要调用 tool"混在同一句 JSON 里。
- 新增公共函数 `parse_model_response_to_tool_calls(content, round_index) -> list[dict]`，让 `chat()` / `complete()` 共用。

### 实现位置
- `src/game_analysis_agent/tool_loop.py`：新增 `parse_model_response_to_tool_calls`；修改 `chat()` 的 early return。
- `tests/test_tool_loop.py`：加 3 个 case：
  1. 仅有 `{"tool": "foo", "arguments": {...}}` → 走 JSON fallback。
  2. 仅有 `{"tool_calls": [{"name": "foo", "arguments": {...}}]}` → 走 JSON fallback（兼容部分模型只写 `tool_calls`）。
  3. 仅有 `{"final_answer": "..."}` → 当成 final，return content。

### 验证
- `pytest tests/test_tool_loop.py -v` 全绿。
- 现有 `test_executes_registered_tool_and_finishes` 等不破坏。

---

## T03. `schemas.AnomalyKind` 增补游戏语义 kind（P0）

### 目标
扩 enum，给 T04 用。

### 实现
- 修改 `src/game_analysis_agent/schemas.py` 的 `AnomalyKind`：

  ```python
  AnomalyKind = Literal[
      # 已有
      "negative_money", "stat_overflow", "stat_underflow",
      "non_repeatable_event_repeated", "dead_state", "week_overflow",
      "single_week_spike", "cost_money_exceeds_balance",
      "pipeline_stalled", "ending_id_empty",
      # 新增 (T03)
      "crisis_success_ending",
      "social_success_under_survival_crisis",
      "academic_success_with_failed_courses",
      "visa_success_without_registration",
      "testdaf_pass_with_low_language",
      "aps_pass_with_low_aps_knowledge",
      "black_work_without_risk",
      "hunger_ignored_too_long",
      "stress_zero_lock",
      "social_overflow_pattern",
  ]
  ```

- 同步更新 `docs/DATA_CONTRACTS.md` §3 的 `kind` 取值列表。

### 验证
- `pytest tests/` 现有全部测试通过（enum 扩展向后兼容）。

---

## T04. `anomaly_detector` 加游戏语义规则（P0）

### 目标
解决评审第 9 节：当前的 10 条规则都是通用不变量，缺游戏语义。`anomaly_detector.detect_anomalies(runs)` 末尾对每个 run 跑一组新的"语义检查"。

### 设计
- 新增文件 `src/game_analysis_agent/anomaly_semantics.py`：

  ```python
  from typing import Final
  SUCCESS_ENDING_PREFIXES: Final = ("success", "scholarship_", "academic_", "smooth_first_")
  ACADEMIC_SUCCESS_ENDINGS: Final = {"academic_success", "scholarship_path"}
  VISA_SUCCESS_ENDINGS: Final = {"smooth_first_semester", "schengen_granted"}

  def check_semantic_invariants(run) -> list[Anomaly]: ...
  ```

  内部根据 `run["final_ending_id"]` / `run["final_state"]` / `run["weekly_log"]` 触发对应 kind。

- 在 `anomaly_detector.py` 的 `detect_anomalies()` 末尾追加 `anomalies.extend(check_semantic_invariants(run))`。

- 规则集（与评审完全一致）：

  | kind | severity | 触发条件 |
  | --- | --- | --- |
  | `crisis_success_ending` | critical | ending ∈ SUCCESS_ENDING_* 且 `money < -1000` |
  | `social_success_under_survival_crisis` | critical | ending == `social_connector` 且末周 `hunger ≥ 85` 且 `stress ≥ 85` |
  | `academic_success_with_failed_courses` | error | ending ∈ ACADEMIC_SUCCESS 且 `failed_courses > 0` |
  | `visa_success_without_registration` | critical | ending ∈ VISA_SUCCESS 且 flags `registered` / `school_registered` 未设 |
  | `testdaf_pass_with_low_language` | error | flag `testdaf_passed` 但 `language < 25` |
  | `aps_pass_with_low_aps_knowledge` | error | flag `aps_passed` 但 `aps_knowledge < 25` |
  | `black_work_without_risk` | warning | flag `illegal_work_taken` 且最终 `visa_progress` 仍 ≥ 70（无任何签证风险） |
  | `hunger_ignored_too_long` | warning | 连续 ≥ 6 周 `hunger ≥ 85` |
  | `stress_zero_lock` | info | 连续 ≥ 4 周 `stress ≤ 1` |
  | `social_overflow_pattern` | info | 社交类行动 tag 在最后 8 周内占比 ≥ 0.7 |

  末周 / 连续窗口通过扫 `weekly_log[i].after_state` 实现。

### 实现位置
- 新文件 `src/game_analysis_agent/anomaly_semantics.py`。
- `src/game_analysis_agent/anomaly_detector.py`：`detect_anomalies` 末尾加一行 `anomalies.extend(_semantic.check_semantic_invariants(run))`。
- `tests/fixtures/anomaly_runs.jsonl`：加 2 条分别触发 `crisis_success_ending` 和 `social_success_under_survival_crisis` 的 run。
- `tests/test_anomaly_detector.py`：加 6 个 case 覆盖新增 kind（每个 case 一条 fixture run）。
- `docs/DATA_CONTRACTS.md` §3 更新 `kind` 列表 + 增加每个新 kind 的 evidence 字段示例。

### 验证
- `pytest tests/test_anomaly_detector.py -v` 全绿。
- `pytest tests/` 全部绿。
- 手工检查：用 `tests/fixtures/anomaly_runs.jsonl` 跑 `python -m game_analysis_agent.anomaly_detector`，确认 10 条新 kind 都出现。

---

## T05. `interactive_player` 改成显式周循环（P0）

### 目标
解决评审第 7 节：当前 `play_through()` 只调一次 `loop.complete()`，并把 ending 写成 stub。要改成"Python 控节奏，LLM 每周只做一个决策"。

### 设计
`InteractivePlayerAgent.play_through()` 主循环：

```python
for week in range(1, self.max_weeks + 1):
    state = probe.get_state()
    decision = self._decide_one_week(probe, persona_prompt)
    result = probe.step(actions=decision["actions"], event_choice_id=decision.get("event_choice_id", ""))
    self._append_step_jsonl(week, state, decision, result)
    if result.get("finished"):
        break
final = probe.finish()
self._write_summary(steps, final)
return result, paths
```

关键点：
- `_decide_one_week()` 调一次 `llm.complete()`（单轮 prompt，不走 tool loop），要求模型输出 JSON：

  ```json
  {"actions": ["cook_at_home"], "event_choice_id": "", "rationale": "..."}
  ```

  这样可以彻底绕开"LLM 不会自己跑 20 周 tool loop"的问题。
- 每周调用前先做 `probe.list_available_actions()` 把可用行动塞进 system 上下文（避免 LLM 选到不存在的 action）。
- 每周调用后调 `probe.detect_anomalies()`，把异常附加到 `playthrough.jsonl` 这一行；不立即终止游戏。
- 终止条件优先用 `result["finished"]`；若 LLM 一直不调用 `finish`，第 N 周强制 break 并写 `final_ending = "(truncated, max_weeks reached without finish call)"`。

### 现有 `OpenAICompatibleToolLoop` 的用途变化
- 主路径改成单轮 chat（`_decide_one_week`），`tool_loop` 仍保留并用于 `_select_event_choice_via_tools` 这种小工具场景（如可选时让 LLM 走 tool 路径）。
- `player_user.md` 模板增加 `{{PERSONA}}` / `{{WEEK}}` / `{{AVAILABLE_ACTIONS}}` / `{{STATE_JSON}}` 四个变量。
- `prompts/player_user.md` 调整。

### 实现位置
- `src/game_analysis_agent/agents/interactive_player.py`：重写 `play_through()`；新增 `_decide_one_week` / `_append_step_jsonl` / `_write_summary`。
- `tools/run_gameplay_agent.py::cmd_play`：保留现有签名；允许 `--persona study|money|social|visa|slacker|newbie`、`--difficulty`、`--seed`。
- `prompts/player_user.md`：增加变量说明。
- `tests/test_runner.py` 或新增 `tests/test_interactive_player.py`：用 mock LLM client 验证 5 周内：
  1. 调了 5 次 `decide_one_week`。
  2. `playthrough.jsonl` 有 5 行 + 1 行 finish。
  3. `playthrough_summary.md` 含 5 个 step summary。

### 验证
- `pytest tests/test_interactive_player.py -v` 全绿。
- 现有 `test_runner.py` 不破坏。

---

## T06. `value_analyzer` 加 action group / crisis / ending contradiction / route separation（P0）

### 目标
解决评审第 10 节：现有规则只看单个 action / choice / ending 的占比，看不到"恢复类整体过强"、"低钱状态不打工"、"study bot 学业轴没拉开"等结构性失衡。

### 设计
- `action_catalog.json` 已经有 `tags` 字段（`study` / `work` / `social` / `admin` / `food` / `escape` / `recovery` ...）。
- 在 `value_analyzer.py` 末尾增加 4 个新分析器，写到 `route_report.json`：

  1. **Action group dominance**

     ```python
     @dataclass
     class GroupFinding:
         policy: str
         group: str            # e.g. "recovery"
         picks_per_run: float  # = group_actions_count / total_runs
         threshold: float      # 默认 recovery > 2.5
     ```

  2. **Crisis response**（每 policy × 每 crisis 状态一行）

     触发条件：run 内某周 `after_state.money < 200` / `stress > 80` / `hunger > 80` / `visa_risk > 70`（`visa_risk = 100 - visa_progress`）中的至少一个，统计该周 policy 实际选了什么 action group。

     期望：

     ```text
     low_money → 应当 work / budget_call / cheap_food
     high_stress → 应当 rest / therapy
     high_hunger → 应当 food
     high_visa_risk → 应当 admin
     ```

     如果对应 group 的 pick rate < 0.4，标 `severity = warning`；< 0.2 标 `error`。

  3. **Ending contradiction**

     对每个 (policy, ending_id) 计算末周 `after_state` 的"失败指标分"（`hunger + stress + max(0, -money) + max(0, 50 - academic_progress)`）。分越低越像"成功"。

     若 ending 名是 `success` 类但分 ≥ 100 → anomaly（类似 `crisis_success_ending` 在 value 维度的镜像）；若 ending 名是 `failure` 类但分 ≤ 30 → 也标 anomaly。

  4. **Route separation score**

     给每个 policy 计算 5 个 route axis 的最终值（取末周 `after_state`）：

     ```python
     ROUTE_AXES = {
         "academic": "academic_progress",
         "work": "money",
         "social": "social",
         "admin": "visa_progress",
         "slacker": "stress",   # 越低越摆
     }
     ```

     对每个 axis，以 balanced policy 的均值为锚点，计算 (study_axis - balanced_axis)² + (money_axis - balanced_axis)² ... 的相对距离。若任一 axis 与 balanced 的相对差 < `0.15`，标 warning。

- 把 4 个分析器结果合并写到 `route_report.json`（同 `value_report.json` 风格，结构化 + by_kind + findings）。

### 实现位置
- `src/game_analysis_agent/value_analyzer.py`：新增 `analyze_routes()` / `analyze_crisis_response()` / `analyze_ending_contradictions()` / `analyze_action_groups()`。
- `analyze_and_write()` 顺带写 `route_report.json`。
- `tests/test_value_analyzer.py`：为每个新分析器加 1-2 个 case。
- `tests/fixtures/`：扩一个 `anomaly_runs.jsonl` 的小样本，验证 crisis response 触发。

### 验证
- `pytest tests/test_value_analyzer.py -v` 全绿。
- 现有 `test_value_analyzer.py` 的 5 个 case 继续通过。

---

## T07. `tools/compare_reports.py`（P0）

### 目标
解决评审第 11 节：单一 run 报告无法说明改动是否真的有用。`compare_reports.py` 把 before / after 两个 report dir 横向 diff。

### 设计
- CLI：

  ```bash
  python3 tools/compare_reports.py \
    --before reports/balance/v01-normal-balanced-r200 \
    --after  reports/balance/v02-normal-balanced-r200 \
    --out    reports/compare/v01-v02-balanced.md
  ```

- 对比维度：
  1. **ending_distribution.csv** → `(ending_id, rate) before/after`，输出差值表。
  2. **action_pick_rates.csv** → 同 action_id 的 rate 差。
  3. **weekly_stats.csv** → 同 (policy, week, metric) 的 mean 差。
  4. **anomalies.jsonl** → 同 kind 的计数差。
  5. **value_report.json** / **route_report.json** → `finding_count` 差 + 按 `finding_id` 前缀统计新增/消除。

- 输出：
  - `compare_summary.md`：人类可读的总结（按维度分段、列 top 5 升降）。
  - `compare_diff.json`：机器可读，每个维度的 dict 形式。

- 复用：`analytics.py` 已经会写 4 个 CSV，compare 工具只读不写。

### 实现位置
- 新文件 `tools/compare_reports.py`。
- 复用 `game_analysis_agent.analytics.load_runs()`。
- `tests/test_compare_reports.py`：在 `tests/fixtures/` 加 `before/` `after/` 两个 mini report dir，跑 `compare_reports.compare_reports(before, after, out_dir)`，断言 markdown 包含至少 5 个数值差行。

### 验证
- `pytest tests/test_compare_reports.py -v` 全绿。
- 手工验证：用 `reports/balance/v02-smoke-balanced-r20` 自比一次，输出能正常生成。

---

## T08. `config/matrix.yaml` + `config/gates.yaml`（P1）

### 目标
让矩阵和通过标准有版本可寻的描述文件，方便后续在 CI / README 引用。

### 设计
- `config/matrix.yaml`：

  ```yaml
  version: demo-v02
  weeks: 20
  runs_per_cell: 200
  seeds: [42, 43, 44]
  difficulties: [normal, realistic]
  policies: [random, balanced, study, money, social, visa, slacker]
  boundary:
    runs: 30
    seed: 42
    weeks: 20
    extremes:
      [zero_money, deep_debt, no_energy, all_negative, no_language, flag_chaos, week_zero, already_registered]
  ```

- `config/gates.yaml`：

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

- 在 `tools/run_gameplay_agent.py` 不强制读；先用 `pytest` 验证 YAML 可被 `yaml.safe_load` 解析。后续可让 `qa` 子命令打印 gates，但本期不动 CLI 行为。

### 验证
- `python -c "import yaml; yaml.safe_load(open('config/matrix.yaml'))"` 不抛错。
- `python -c "import yaml; yaml.safe_load(open('config/gates.yaml'))"` 不抛错。

---

## T09. `event_graph` agent 输出"未触发原因"（P1）

### 目标
让 `event_graph_report.md` 不仅说 `event_rare`，还说为什么没触发。

### 设计
- 复用 `event_graph.json` 的 `events[*].trigger` 字段（既有），扫所有 `raw_runs.jsonl` 的 `weekly_log`：
  - 对每个 event_id，统计实际触发率。
  - 若触发率 < 0.005，从 trigger 表达式反推"未触发原因"（先做粗粒度：根据 trigger 中出现的 flag / metric，扫一遍 raw_runs 看这个 flag/metric 在所有 run 中是否被设 / 是否达到阈值）。
- 在 `EventGraphAgent` 的 user prompt 末尾追加 `## Untriggered Events\n{{BLOCK}}` 段。

### 实现位置
- `src/game_analysis_agent/agents/event_graph.py`：新增 `build_untriggered_block(raw_runs, event_graph)`。
- `prompts/event_graph_agent_user.md`：增加 `{{UNTRIGGERED_EVENTS}}` 占位（替换 `{{REPORT_BUNDLE}}` 之前的 `{{UNTRIGGERED_EVENTS}}`）。
- `tests/test_agents_registry.py`：加 1 个 case，断言 `event_graph_report.md` 含 `untriggered_events` 段。

### 验证
- `pytest tests/test_agents_registry.py -v` 全绿。

---

## T10. `content_qa` agent 按"选择结构"评分（P1）

### 目标
不再只查文案相似度，还要查"4 个选项全是正向"或"全是 generic"。

### 设计
- 读 `event_graph.json` 的每个 event 的 `choices[]`：
  - 每条 choice 看 `success_effects` / `failure_effects`：
    - 都为正 → `all_choices_positive`。
    - 都为空 → `missing_failure_cost`。
    - 4 条 choice 的 effects 数值相似度 > 0.9 → `choice_effects_too_similar`。
  - choice 文本是否含 "避难" / "回避" 等关键词 → 打 `avoidance` 标签。
- 输出 `content_issues.md` 中追加 `## Choice Structure Issues` 段，列出 event_id + issue。

### 实现位置
- `src/game_analysis_agent/agents/content_qa.py`：新增 `score_choice_structure(event_graph) -> list[Finding]`。
- `prompts/content_qa_agent_user.md`：增加 `{{CHOICE_STRUCTURE_FINDINGS}}` 占位。
- `tests/test_agents_registry.py`：加 1 个 case，断言 `content_issues.md` 含 `choice_structure` 段。

### 验证
- `pytest tests/test_agents_registry.py -v` 全绿。

---

## T11. `play` CLI 加 `--persona` / `--difficulty` / `--seed`（P1）

### 目标
让 `play` 子命令能选 persona，并固定 seed 复现 T05 改造后的 LLM 试玩器。

### 实现
- `tools/run_gameplay_agent.py::build_parser` 的 `play_p` 增加 3 个 argument。
- `cmd_play()` 把 `persona` 透传给 `InteractivePlayerAgent.play_through()` 的 `context`。
- `prompts/player_user.md` 增加 `{{PERSONA}}` 模板变量。

### 验证
- `python tools/run_gameplay_agent.py play --help` 能看到新 flag。

---

## T12. 跑全量矩阵（P2，纯命令）

### 步骤
1. 先按 T04 / T06 跑一次 smoke，确认新检测器 / 新分析器不误伤。
2. 跑：

   ```bash
   for d in normal realistic; do
     for p in random balanced study money social visa slacker; do
       python3 tools/run_gameplay_agent.py all \
         --run-id v02-${d}-${p}-r200 --runs 200 --policy $p --difficulty $d --weeks 20
     done
   done
   python3 tools/run_gameplay_agent.py probe \
     --run-id v02-boundary-r30 --runs 30 --policy balanced --weeks 20 \
     --extreme zero_money,deep_debt,no_energy,all_negative,no_language,flag_chaos,week_zero,already_registered
   ```

3. 跑 `python3 tools/compare_reports.py --before <v01> --after <v02> --out ...`（如果 v01 报告还在）。

### 验证
- 每个 run dir 的 `bugs.jsonl` 至少 1 条新 kind。
- `route_report.json` 不为空。
- `compare_summary.md` 至少 10 行差值。

---

## T13. HTML dashboard（P2）

### 目标
评审第 14 节 P2：把 `reports/balance/<run>/` 集中到一个 `index.html`，便于人眼看。

### 设计
- `tools/build_dashboard.py`：扫 `reports/balance/*/` 用 `summary.json` / 4 个 CSV 渲染：
  - 结局饼图（SVG 内联）
  - 每周属性均值曲线（4 条：stress / hunger / money / academic_progress）
  - top 10 actions
  - anomaly 计数柱图
- 不引入额外依赖，SVG 全部手写。

### 实现位置
- 新文件 `tools/build_dashboard.py`。
- `tests/`：加 1 个 case 验证生成的文件存在且长度 > 1KB。

### 验证
- `python tools/build_dashboard.py --reports reports/balance --out reports/index.html` 成功，文件可被浏览器打开。

---

## 风险与回滚

- T02 / T04 / T06 都会扩展 enum / 数据结构；旧 fixture 必须保持可读。回滚手段：保留新逻辑在 `anomaly_semantics.py` / `value_analyzer` 子函数里，主函数名不变，旧测试无破坏。
- T05 的 interactive_player 是最大改动；保留 `loop.complete()` 路径作为 `_legacy_play_through()` 备用，CLI 不暴露，CI 不调用。
- T07 compare_reports 是新文件，没有"破坏"语义。

## 实施后回写

完成每条任务后，按 [REVIEW_FEEDBACK.md 落实日志](REVIEW_FEEDBACK.md#落实日志实施后回写) 模板回写：

```text
- [Txx] <一句话结论>
  - 文件: <path>
  - 验证: <pytest 输出关键行 / 命令输出>
  - 未完成项: <如有>
```

最新对齐审计和补齐计划见 [docs/review/](review/README.md)。

## 真实测试场景补齐（2026-07-06）

来自 [docs/review/REAL_TEST_GAP_ANALYSIS.md](review/REAL_TEST_GAP_ANALYSIS.md)。

- `sim/all` 支持 `--scenario`，默认 `default_first_semester`。
- CLI policy alias：`money -> work`，`visa -> admin`，避免与 Godot route 名称漂移。
- `validate` 子命令接入 Godot validators：content / json-content / economy / risk，支持显式选择 route / demo。
- `gates` 子命令执行 `config/gates.yaml` 并写 `gate_report.json`。
- `analyze` 现在生成 `coverage_report.json`，记录 scenario / policy / crisis regime / event coverage。
- `anomalies.jsonl` 的 evidence 增加 replay context：seed、policy、difficulty、scenario、week、actions、event、choice。

验证：

```text
uv run ruff check <touched files>
uv run pytest tests/ -q
113 passed in 0.58s
```
