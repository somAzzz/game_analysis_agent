extends SceneTree

# Boundary probe runner.
#
# For each `--extreme` label, this script resets the GameState, applies a
# deliberately degenerate scenario, then runs the simulation for N weeks
# with a chosen policy. The per-run trace is appended to `--out` (JSONL).
#
# Defaults cover the corners the agent harness cares about. Adding new
# extremes is one entry in `_EXTREMES`.

const SimulationEngineScript := preload("res://scripts/simulation/SimulationEngine.gd")
const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")
const PlayerPolicyScript := preload("res://scripts/policies/PlayerPolicy.gd")
const RandomPolicyScript := preload("res://scripts/policies/RandomPolicy.gd")
const BalancedPolicyScript := preload("res://scripts/policies/BalancedPolicy.gd")

const AnomalyDetectorScript := preload("res://scripts/tools/AnomalyCollector.gd")

var run_records: Array = []
var ending_counts: Dictionary = {}


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var game_state: Node = root.get_node("/root/GameState")
	var data_registry: Node = root.get_node("/root/DataRegistry")
	var config: Dictionary = _parse_args()
	var runs: int = int(config.get("runs", 3))
	var base_seed: int = int(config.get("seed", 42))
	var policy_name: String = str(config.get("policy", "random"))
	var max_weeks: int = int(config.get("weeks", 12))
	var out_path: String = str(config.get("out", "user://boundary_runs.jsonl"))
	var extremes: Array = _parse_extremes(str(config.get("extreme", "zero_money,no_energy,all_negative,no_language,flag_chaos,week_zero")))
	var out_file = _open_write(out_path)
	if out_file == null:
		printerr("Failed to open output: %s" % out_path)
		quit(1)
		return

	for extreme in extremes:
		var scenario: Dictionary = _scenario_for(extreme)
		for run_index in range(runs):
			var run_id: int = run_index + 1
			var run_seed: int = base_seed + run_index
			var record: Dictionary = _simulate_run(
				game_state,
				data_registry,
				run_id,
				run_seed,
				policy_name,
				max_weeks,
				extreme,
				scenario,
			)
			run_records.append(record)
			out_file.store_line(JSON.stringify(record))
	out_file.close()

	print("Boundary probe complete: %d extremes × %d runs -> %s" % [extremes.size(), runs, _global_path(out_path)])
	quit(0)


func _simulate_run(
	game_state: Node,
	data_registry: Node,
	run_id: int,
	run_seed: int,
	policy_name: String,
	max_weeks: int,
	extreme: String,
	scenario: Dictionary,
) -> Dictionary:
	game_state.reset()
	game_state.configure_run({
		"run_id": run_id,
		"seed": run_seed,
		"policy": policy_name,
		"difficulty": "realistic",
	})
	if not scenario.is_empty():
		game_state.apply_scenario(scenario)

	var policy = _make_policy(policy_name)
	var engine = SimulationEngineScript.new()
	var weekly_log: Array = []
	var guard_iterations: int = 0
	var guard_limit: int = maxi(60, max_weeks + 20)

	while game_state.week <= max_weeks and game_state.last_ending_id == "":
		guard_iterations += 1
		if guard_iterations > guard_limit:
			game_state.set_flag("pipeline_stalled")
			game_state.last_ending_id = "pipeline_stalled"
			break
		var week: int = game_state.week
		var before_state: Dictionary = game_state.export_public_stats()
		var available_actions: Array = engine.get_available_actions(game_state)
		var available_action_ids: Array = _action_ids(available_actions)
		var selected_action_ids: Array = policy.choose_actions(before_state, available_actions, SimulationEngineScript.MAX_ACTION_SLOTS)
		selected_action_ids = _fill_action_plan(selected_action_ids, available_actions, SimulationEngineScript.MAX_ACTION_SLOTS)
		selected_action_ids = engine.set_plan_from_action_ids(selected_action_ids)
		var event = engine.resolve_week()
		var after_actions_and_drift: Dictionary = game_state.export_public_stats()
		var event_choice_id: String = ""
		var event_choices: Array = []
		if event != null:
			var available_choices: Array = _available_choices(event)
			event_choices = available_choices
			var chosen_index: int = policy.choose_event_option(after_actions_and_drift, event, available_choices)
			if chosen_index >= 0 and chosen_index < available_choices.size():
				var choice = available_choices[chosen_index]
				event_choice_id = _choice_id(event, choice, chosen_index)
				EventResolverScript.resolve_choice_detailed(event, choice, game_state)
		var after_state: Dictionary = game_state.export_public_stats()
		weekly_log.append({
			"week": week,
			"available_action_ids": available_action_ids,
			"selected_action_ids": selected_action_ids,
			"before_state": before_state,
			"after_state": after_state,
			"triggered_event_id": event.id if event != null else "",
			"event_choice_id": event_choice_id,
		})
		if game_state.week >= max_weeks:
			game_state.last_ending_id = "max_weeks_reached"
			break
		engine.finish_week()

	return {
		"run_id": run_id,
		"seed": run_seed,
		"policy": policy_name,
		"extreme": extreme,
		"max_weeks": max_weeks,
		"final_ending_id": game_state.last_ending_id or "unknown",
		"final_week": game_state.week,
		"final_state": game_state.export_state_snapshot(),
		"weekly_log": weekly_log,
		"anomalies": AnomalyDetectorScript.collect(weekly_log, game_state.export_state_snapshot()),
	}


func _scenario_for(extreme: String) -> Dictionary:
	match extreme:
		"zero_money":
			return {"initial_state": {"money": 0}, "flags": {}}
		"deep_debt":
			return {"initial_state": {"money": -1200}, "flags": {}}
		"no_energy":
			return {"initial_state": {"energy": 0, "stress": 95}, "flags": {}}
		"all_negative":
			return {"initial_state": {"money": 0, "energy": 0, "stress": 100, "loneliness": 100, "hunger": 100, "social": 0, "language": 0}, "flags": {}}
		"no_language":
			return {"initial_state": {"language": 0, "aps_knowledge": 0}, "flags": {}}
		"flag_chaos":
			return {"initial_state": {"money": 500, "energy": 50, "stress": 30}, "flags": {"testdaf_passed": true, "aps_passed": true, "school_registered": true, "visa_valid": true, "work_limit_exceeded": true, "illegal_work_taken": true}}
		"week_zero":
			return {"initial_state": {"week": -8, "money": 500, "energy": 100, "stress": 20}, "flags": {}}
		"already_registered":
			return {"initial_state": {"money": 4500, "energy": 80, "stress": 25, "academic_progress": 40}, "flags": {"aps_passed": true, "testdaf_passed": true, "school_registered": true, "visa_valid": true}}
	return {}


func _parse_extremes(raw: String) -> Array:
	var parts: Array = raw.split(",")
	var result: Array = []
	for part in parts:
		var label: String = part.strip()
		if label != "":
			result.append(label)
	return result


func _make_policy(policy_name: String):
	match policy_name:
		"random":
			return RandomPolicyScript.new()
		"balanced":
			return BalancedPolicyScript.new()
	return PlayerPolicyScript.new()


func _fill_action_plan(action_ids: Array, available_actions: Array, slots: int) -> Array:
	var data_registry: Node = root.get_node("/root/DataRegistry")
	var selected: Array = action_ids.duplicate()
	var used_slots: int = 0
	for action_id in selected:
		var action = data_registry.get_action_by_id(str(action_id))
		if action != null:
			used_slots += action.cost_slots
	for action in available_actions:
		if used_slots >= slots:
			break
		if selected.has(action.id):
			continue
		if used_slots + action.cost_slots <= slots:
			selected.append(action.id)
			used_slots += action.cost_slots
	return selected


func _available_choices(event) -> Array:
	var choices: Array = []
	for choice in event.choices:
		if choice.is_available(root.get_node("/root/GameState")):
			choices.append(choice)
	return choices


func _action_ids(actions: Array) -> Array:
	var ids: Array = []
	for action in actions:
		ids.append(action.id)
	return ids


func _choice_id(event, choice, index: int) -> String:
	var safe_text: String = str(choice.text).to_lower().replace(" ", "_")
	return "%s.choice_%02d_%s" % [event.id, index + 1, safe_text]


func _parse_args() -> Dictionary:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		args = OS.get_cmdline_args()
	var parsed: Dictionary = {}
	var index: int = 0
	while index < args.size():
		var arg: String = str(args[index])
		if arg.begins_with("--"):
			var body: String = arg.substr(2)
			var equals_index: int = body.find("=")
			if equals_index >= 0:
				parsed[body.substr(0, equals_index)] = body.substr(equals_index + 1)
			elif index + 1 < args.size() and not str(args[index + 1]).begins_with("--"):
				parsed[body] = str(args[index + 1])
				index += 1
			else:
				parsed[body] = true
		index += 1
	return parsed


func _open_write(path: String):
	var global_path: String = _global_path(path)
	DirAccess.make_dir_recursive_absolute(global_path.get_base_dir())
	return FileAccess.open(global_path, FileAccess.WRITE)


func _global_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	if path.begins_with("/"):
		return path
	return ProjectSettings.globalize_path("res://%s" % path)