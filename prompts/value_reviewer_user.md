Read the value-review report bundle below.

The Python analyzer has already produced:

- `value_report.json` — structured findings grouped by kind
  (`action_dominant`, `action_dead`, `choice_dominant`, `event_rare`,
  `ending_dominant`) with `target_id`, `value`, `threshold`, `description`.
- The standard balance bundle (`summary.json`,
  `ending_distribution.csv`, `weekly_stats.csv`,
  `action_pick_rates.csv`, `event_trigger_rates.csv`,
  `choice_pick_rates.csv`, `anomaly_report.md`).

Your job:

1. Explain WHY each finding is interesting. Tie it back to the game's
   design (留学第一学期: APS / TestDaF / 学校注册 / 打工时长 / 居留许可 / 食堂
   / WG / 考试 / 心情).
2. Recommend the minimum-impact parameter change (effect sign / magnitude,
   cost_money, cooldown, availability window, success_rate, weight).
3. Flag any case where the data is misleading because the policy never
   explored the right regime (e.g. an action only relevant when
   `money < 500` will look "dead" for a `BalancedPolicy` that always
   keeps money healthy).

Required output structure:

# Value Review

## Top 10 Tuning Proposals

For each:
- target_id (action / event / ending)
- issue
- evidence
- proposed_fix
- expected_metric_movement
- rollback_criteria

## Cases Where Data Misleads

Report bundle:

{{REPORT_BUNDLE}}