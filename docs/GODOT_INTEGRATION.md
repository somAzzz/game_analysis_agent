# Godot 接入规范

## 1. 目标

Godot 项目需要提供一个 headless runner，让游戏可以无 UI 批量跑局，并输出结构化日志。

推荐命令：

```bash
godot4 --headless \
  --path /Users/bo/projects/study-in-germany \
  -s res://scripts/tools/RunBalanceSim.gd \
  --runs=1000 \
  --policy=balanced \
  --seed=42 \
  --out=res://reports/balance/baseline/raw_runs.jsonl
```

## 2. SimulationEngine 纯模拟接口

建议在游戏项目中形成这些接口：

```gdscript
func start_new_run(seed_value: int) -> void
func get_available_actions() -> Array
func simulate_week(action_ids: Array, event_choice_policy := "auto") -> Dictionary
func resolve_event_choice(event_id: String, choice_id: String) -> Dictionary
func is_finished() -> bool
func get_final_ending() -> Variant
func export_state_snapshot() -> Dictionary
```

## 3. Policy

第一批实现：

- `random`：随机选择合法行动。
- `balanced`：尽量平衡学业、金钱、行政、压力。
- `study`：学业优先，忽略部分压力。
- `money`：金钱低时高优先打工。

第二批实现：

- `visa`
- `social`
- `burnout`
- `greedy`
- `newbie`

## 4. Runner 示例

示例脚本放在 [scripts/tools/RunBalanceSim.gd](/Users/bo/projects/analyse_agent/scripts/tools/RunBalanceSim.gd)。

这是一个集成模板，不会直接知道你的游戏类名。落地时需要把 `preload` 路径和 action 字段映射改成你项目里的实际结构。
