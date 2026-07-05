# 数据与报告契约

## 1. raw_runs.jsonl

每行是一局：

```json
{
  "run_id": 0,
  "policy": "balanced",
  "seed": 42,
  "ending_id": "academic_success",
  "final_state": {
    "week": 20,
    "money": 820,
    "energy": 55,
    "stress": 48,
    "loneliness": 30,
    "academic": 76,
    "german": 62,
    "social": 44,
    "admin": 70,
    "career": 18
  },
  "weekly_log": [
    {
      "week": 1,
      "actions": ["study_library", "rest_at_home"],
      "event_id": "first_lecture",
      "choice_id": "ask_question",
      "state": {
        "week": 1,
        "money": 950,
        "energy": 82,
        "stress": 20,
        "loneliness": 35,
        "academic": 12,
        "german": 8,
        "social": 4,
        "admin": 15,
        "career": 0
      }
    }
  ]
}
```

## 2. 必需字段

局级字段：

- `run_id`
- `policy`
- `seed`
- `ending_id`
- `final_state`
- `weekly_log`

周级字段：

- `week`
- `actions`
- `event_id`
- `choice_id`
- `state`

核心属性：

- `money`
- `energy`
- `stress`
- `loneliness`
- `academic`
- `german`
- `social`
- `admin`
- `career`

## 3. 统计输出

`summary.json`：

- 总局数。
- policy 列表。
- 结局分布。
- 高频事件。
- 低频事件。
- 异常摘要。

`ending_distribution.csv`：

```text
policy,ending_id,count,rate
balanced,academic_success,410,0.41
```

`weekly_stats.csv`：

```text
policy,week,metric,mean,median,p10,p90,min,max
balanced,10,stress,55.2,54,37,78,10,100
```

`action_pick_rates.csv`：

```text
policy,action_id,count,rate_per_run
balanced,study_library,620,0.62
```

`event_trigger_rates.csv`：

```text
policy,event_id,count,rate_per_run
balanced,visa_delay,140,0.14
```

`choice_pick_rates.csv`：

```text
policy,event_id,choice_id,count,rate_per_event
balanced,visa_delay,email_foreigners_office,90,0.64
```
