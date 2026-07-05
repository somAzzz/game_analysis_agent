# 数据与报告契约

本文档描述所有 `reports/` 下的文件格式。schemas 是稳定可复现的；任何破坏 schema 的改动都必须先在 `docs/` 下增补一节。

## 1. raw_runs.jsonl

每行是一局。`study-in-germany` 的 v0.2 输出结构如下：

```json
{
  "run_id": 0,
  "seed": 42,
  "policy": "balanced",
  "difficulty": "normal",
  "scenario": "",
  "content_version": "dev-hardcoded-0.1.0",
  "rules_version": "sim-0.2.0",
  "max_weeks": 20,
  "final_ending_id": "academic_success",
  "final_exam": {},
  "final_state": {
    "week": 20,
    "money": 820,
    "energy": 55,
    "stress": 48,
    "loneliness": 30,
    "academic_progress": 76,
    "language": 62,
    "social": 44,
    "visa_progress": 70,
    "career_progress": 18,
    "gpa_score": 70,
    "aps_score": 0
  },
  "weekly_log": [
    {
      "week": 1,
      "available_action_ids": ["study_library", "rest_at_home", "..."],
      "selected_action_ids": ["study_library", "rest_at_home"],
      "before_state": {"week": 1, "money": 950, "...": "..."},
      "after_state": {"week": 1, "money": 950, "...": "..."},
      "triggered_event_id": "first_lecture",
      "event_choice_id": "first_lecture.choice_01_ask_question",
      "event_effects": {"language": 3},
      "event_success": true,
      "life_drift_effects": {"energy": 32, "stress": 2}
    }
  ],
  "action_sequence": [
    {"week": 1, "actions": ["study_library", "rest_at_home"], "event_choice": "first_lecture.choice_01_ask_question"}
  ]
}
```

向后兼容：v0.1 schema 的 `actions` / `event_id` / `choice_id` / `state` 也会被
`game_analysis_agent.analytics` / `anomaly_detector` 接受。

### 必需字段

局级字段：

- `run_id`
- `policy`
- `seed`
- `final_ending_id`（或 `ending_id`，兼容旧版）
- `final_state`
- `weekly_log`

周级字段（v0.2）：

- `week`
- `selected_action_ids`（或 `actions`，兼容）
- `triggered_event_id`（或 `event_id`，兼容）
- `event_choice_id`（或 `choice_id`，兼容）
- `after_state`（或 `state`，兼容）

### 核心 stat

详见 `study-in-germany/autoload/GameState.gd`。最常用的：

- `money`
- `energy`
- `stress`
- `loneliness`
- `hunger`
- `academic_progress`（也写作 `academic`，兼容）
- `exam_readiness`
- `language`（也写作 `german`，兼容）
- `social`
- `visa_progress`（也写作 `admin`，兼容）
- `career_progress`
- `gpa_score`
- `aps_knowledge`
- `aps_score`

## 2. 统计输出

### summary.json

```json
{
  "total_runs": 1000,
  "policies": {"balanced": 1000},
  "top_events": {"first_lecture": 980, "...": "..."},
  "generated_files": ["ending_distribution.csv", "..."]
}
```

### ending_distribution.csv

```text
policy,ending_id,count,rate
balanced,academic_success,410,0.41
```

### weekly_stats.csv

```text
policy,week,metric,mean,median,p10,p90,min,max
balanced,10,stress,55.2,54,37,78,10,100
```

### action_pick_rates.csv

```text
policy,action_id,count,rate_per_run
balanced,study_library,620,0.62
```

### event_trigger_rates.csv

```text
policy,event_id,count,rate_per_run
balanced,visa_delay,140,0.14
```

### choice_pick_rates.csv

```text
policy,event_id,choice_id,count,rate_per_event
balanced,visa_delay,email_foreigners_office,90,0.64
```

## 3. 检测器输出（v0.2）

### anomalies.jsonl

每行一个 `Anomaly`：

```json
{
  "kind": "negative_money",
  "severity": "critical",
  "run_id": 0,
  "week": 5,
  "policy": "balanced",
  "evidence": {"metric": "money", "value": -150.0},
  "message": "`money` went negative (-150.0)."
}
```

`kind` 取值：`negative_money` / `stat_overflow` / `stat_underflow` /
`non_repeatable_event_repeated` / `dead_state` / `week_overflow` /
`single_week_spike` / `cost_money_exceeds_balance` / `pipeline_stalled` /
`ending_id_empty`。

### bugs.jsonl

与 `anomalies.jsonl` 同 schema（每个 `Anomaly` 一行）。由
`game_analysis_agent.bug_summarizer.write_bug_summary` 同时写出
`bugs_summary.md` 给人类看。

### value_report.json

```json
{
  "finding_count": 12,
  "by_kind": {"action_dominant": 3, "action_dead": 4, "ending_dominant": 1, "...": 0},
  "findings": [
    {
      "finding_id": "action_dominant-0001",
      "scope": "action",
      "target_id": "balanced:study_library",
      "severity": "warning",
      "metric": "rate_per_run",
      "value": 0.92,
      "threshold": 0.8,
      "description": "Action `study_library` (policy=balanced) is picked 92% of runs — probable 'must-pick'."
    }
  ],
  "meta": {"generated_by": "game_analysis_agent.value_analyzer.analyze_and_write"}
}
```

## 4. 边界探测（v0.2）

### boundary_runs.jsonl

每行一局。`scripts/tools/RunBoundaryProbe.gd` 输出，结构与 `raw_runs.jsonl`
相似但附加：

```json
{
  "run_id": 1,
  "seed": 43,
  "policy": "balanced",
  "extreme": "zero_money",
  "max_weeks": 12,
  "final_ending_id": "pipeline_stalled",
  "final_week": 5,
  "final_state": {...},
  "weekly_log": [...],
  "anomalies": [
    {"kind": "pipeline_stalled", "week": -1}
  ]
}
```

`extreme` 取值：`zero_money` / `deep_debt` / `no_energy` / `all_negative` /
`no_language` / `flag_chaos` / `week_zero` / `already_registered`。

## 5. 事件 / 行动目录（v0.2）

### event_graph.json

```json
{
  "version": "0.2.0",
  "exported_at": "2026-07-05T12:34:56",
  "events": [
    {
      "id": "first_lecture",
      "title": "第一次上课",
      "body": "...",
      "event_type": "fixed",
      "trigger": {"week": 3, "flag": "school_registered"},
      "weight": 1.0,
      "repeatable": false,
      "choices": [
        {
          "text": "硬着头皮记笔记",
          "success_rate": 0.75,
          "success_effects": {"academic_progress": 5, "stress": 3},
          "failure_effects": {"stress": 4},
          "success_modifiers": {},
          "requirements": {},
          "set_flag": ""
        }
      ]
    }
  ],
  "actions": [...],
  "endings": [...]
}
```

### action_catalog.json

```json
{
  "actions": [
    {
      "id": "study_library",
      "name": "图书馆自习",
      "description": "...",
      "cost_energy": 20,
      "cost_money": 0,
      "cost_slots": 1,
      "effects": {"academic_progress": 10, "loneliness": 2},
      "requirements": {},
      "tags": ["study"],
      "risk_tags": [],
      "set_flag": "",
      "cooldown_group": "",
      "max_per_week": 0
    }
  ]
}
```

## 6. 试玩产物（v0.2）

### playthrough.jsonl

每行一个 step，包含 model 决策、tool 调用结果与状态变化。详见
`game_analysis_agent.game_tools.InteractiveProbe.step`。

### playthrough_summary.md

由 `InteractivePlayerAgent` 生成，包含工具调用次数、LLM 调用次数、最终
状态片段。