# Interactive Playtest Execution Plan

## P0 当前执行

### Step 1. Godot 交互 runner

交付：

- 新增 `study-in-germany/scripts/tools/RunInteractiveProbe.gd`。
- 支持 `--plan=/path/plan.json` 和 `--out=/path/trace.json`。
- replay plan 内的每周 action/event choice，并返回最后一周 trace。

验收：

```bash
godot --headless --path /home/bo/projects/python/study-in-germany \
  -s res://scripts/tools/RunInteractiveProbe.gd \
  --plan=/tmp/plan.json \
  --out=/tmp/trace.json
```

`trace.json` 包含 `after_state`、`available_actions`、`event_choices`、`final_ending_id`。

### Step 2. Pydantic 决策与上下文

交付：

- `StateSummary`
- `ActionBrief`
- `EventChoiceBrief`
- `RiskBrief`
- `PlayMemory`
- `WeekContext`
- `PlayerDecision`
- `DecisionValidation`

验收：

- LLM 输出非法 action 时进入 repair。
- repair 两次失败后 deterministic fallback。
- `playthrough.jsonl` 写出结构化 validation 信息。

### Step 3. Persona 策略配置

交付：

- 新增 `config/player_personas.yaml`。
- system prompt 拼入 persona priorities、risk tolerance、hard avoid。

验收：

- `newbie/study/money/social/visa/slacker` 都可通过 CLI 选择。
- prompt 不再只是一句 persona 描述。

### Step 4. 完整 ActionBrief

交付：

- `list_available_actions()` 返回或导出 action 的 cost/effects/tags。
- 每周 prompt 不再只给 action id。

验收：

- `WeekContext.available_actions[*]` 包含 id/name/cost/effects/requirements/tags/risk_tags。

### Step 5. 真实 playthrough 验证

交付：

```bash
python tools/run_gameplay_agent.py play \
  --report-dir reports/play/v03-money \
  --weeks 20 \
  --persona money \
  --difficulty normal \
  --seed 42
```

验收：

- `playthrough.jsonl` 接近 20 行，除非游戏提前结束。
- `playthrough_summary.md` 包含 final ending 和每周决策表。
- 结局按 `config/gates.yaml` 的 `outcomes` 分类为 success、recovery/mixed、designed failure 或 invalid。
- designed failure 不自动算作测试失败；只有 `unknown`、`pipeline_stalled`、语义矛盾或不可复现才是 hard failure。
- 全量 persona 测试需要覆盖不同失败/成功/恢复类别，不能只优化成单一成功路径。

## P1 后续

- 结构化 `RiskEvaluator`，替代当前 Python 侧启发式风险。
- `inspect_action(action_id)` / `inspect_ending(ending_id)` 工具。
- semantic anomaly：`success_under_deep_debt`、`visa_success_without_registration`、`recovery_action_spam` 等。
- `compare_reports.py` 联动 playthrough before-after。

## P2 后续

- HTML dashboard。
- replay viewer。
- 自动 patch proposal。
- CI regression gates。
