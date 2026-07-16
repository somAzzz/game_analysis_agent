extends SceneTree

const SimulationEngineScript := preload("res://scripts/simulation/SimulationEngine.gd")
const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")
const ExamResolverScript := preload("res://scripts/simulation/ExamResolver.gd")
const EndingResolverScript := preload("res://scripts/simulation/EndingResolver.gd")
const PlayerPolicyScript := preload("res://scripts/policies/PlayerPolicy.gd")
const RandomPolicyScript := preload("res://scripts/policies/RandomPolicy.gd")
const BalancedPolicyScript := preload("res://scripts/policies/BalancedPolicy.gd")
const StudyPolicyScript := preload("res://scripts/policies/StudyPolicy.gd")
const WorkPolicyScript := preload("res://scripts/policies/WorkPolicy.gd")
const AdminPolicyScript := preload("res://scripts/policies/AdminPolicy.gd")
const SocialPolicyScript := preload("res://scripts/policies/SocialPolicy.gd")
const SlackerPolicyScript := preload("res://scripts/policies/SlackerPolicy.gd")

var game_state: Node
var data_registry: Node

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	game_state = root.get_node("/root/GameState")
	data_registry = root.get_node("/root/DataRegistry")
	var config := _parse_args()
	var runs := int(config.get("runs", 3))
	var base_seed := int(config.get("seed", 42))
	var policy_name := str(config.get("policy", "balanced"))
	var max_weeks := int(config.get("weeks", 12))
	var out_path := str(config.get("out", "res://boundary_runs.jsonl"))
	var extremes := _extremes(str(config.get("extreme", "zero_money")))
	var out_file = _open_write(out_path)
	if out_file == null:
		printerr("Failed to open output: %s" % out_path)
		quit(1)
		return
	var total := 0
	for extreme in extremes:
		for run_index in range(runs):
			var run_seed := base_seed + run_index
			var record := _simulate_boundary_run(run_index + 1, run_seed, policy_name, max_weeks, str(extreme))
			out_file.store_line(JSON.stringify(record))
			total += 1
	out_file.close()
	print("Boundary probe complete: %d runs -> %s" % [total, _global_path(out_path)])
	quit(0)

func _simulate_boundary_run(run_id: int, run_seed: int, policy_name: String, max_weeks: int, extreme: String) -> Dictionary:
	game_state.reset()
	game_state.configure_run({
		"run_id": run_id,
		"seed": run_seed,
		"policy": policy_name,
		"difficulty": "realistic",
		"content_version": game_state.CONTENT_VERSION,
		"rules_version": game_state.RULES_VERSION
	})
	game_state.apply_scenario(_boundary_scenario(extreme))
	var policy = _make_policy(policy_name)
	var engine = SimulationEngineScript.new()
	var weekly_log: Array = []
	var action_sequence: Array = []
	var exam: Dictionary = {}
	var ending = null
	var guard_iterations := 0
	var guard_limit: int = maxi(60, max_weeks + 30)

	while game_state.week <= max_weeks and game_state.last_ending_id == "":
		guard_iterations += 1
		if guard_iterations > guard_limit:
			game_state.set_flag("pipeline_stalled")
			game_state.last_ending_id = "pipeline_stalled"
			break
		var week: int = game_state.week
		var before_state: Dictionary = game_state.export_public_stats()
		var available_actions: Array = engine.get_available_actions(game_state)
		var selected_action_ids: Array = policy.choose_actions(before_state, available_actions, SimulationEngineScript.MAX_ACTION_SLOTS)
		selected_action_ids = _fill_action_plan(selected_action_ids, available_actions, SimulationEngineScript.MAX_ACTION_SLOTS)
		selected_action_ids = engine.set_plan_from_action_ids(selected_action_ids)
		var event = engine.resolve_week()
		var event_choice_id := ""
		var event_detail: Dictionary = {}
		if event != null:
			var available_choices := _available_choices(event)
			var chosen_choice_index: int = policy.choose_event_option(game_state.export_public_stats(), event, available_choices)
			if chosen_choice_index >= 0 and chosen_choice_index < available_choices.size():
				var choice = available_choices[chosen_choice_index]
				event_choice_id = "%s.choice_%02d" % [event.id, _choice_index(event, choice) + 1]
				event_detail = EventResolverScript.resolve_choice_detailed(event, choice, game_state)
		var after_state: Dictionary = game_state.export_public_stats()
		weekly_log.append({
			"week": week,
			"available_action_ids": _action_ids(available_actions),
			"selected_action_ids": selected_action_ids,
			"before_state": before_state,
			"triggered_event_id": event.id if event != null else "",
			"event_choice_id": event_choice_id,
			"event_effects": event_detail.get("effects", {}),
			"event_success": event_detail.get("success", null),
			"after_state": after_state
		})
		action_sequence.append({"week": week, "actions": selected_action_ids, "event_choice": event_choice_id})
		if game_state.week >= max_weeks:
			exam = ExamResolverScript.resolve_exam(game_state)
			ending = EndingResolverScript.resolve_ending(data_registry.endings, game_state)
			if ending == null:
				ending = data_registry.get_ending_by_id("stable_start")
			game_state.last_ending_id = ending.id
			break
		engine.finish_week()

	var final_ending_id: String = game_state.last_ending_id
	if final_ending_id == "" and ending != null:
		final_ending_id = ending.id
	if final_ending_id == "":
		final_ending_id = "unknown"
	return {
		"run_id": run_id,
		"seed": run_seed,
		"policy": policy_name,
		"difficulty": game_state.difficulty,
		"extreme": extreme,
		"max_weeks": max_weeks,
		"final_week": game_state.week,
		"final_ending_id": final_ending_id,
		"final_exam": exam,
		"final_state": game_state.export_state_snapshot(),
		"weekly_log": weekly_log,
		"action_sequence": action_sequence
	}

func _boundary_scenario(extreme: String) -> Dictionary:
	var state := {
		"week": 1,
		"money": 500,
		"blocked_account_balance": game_state.BLOCKED_ACCOUNT_REQUIRED_2026,
		"energy": 80,
		"stress": 35,
		"loneliness": 35,
		"hunger": 35,
		"academic_progress": 10,
		"language": 20,
		"social": 15,
		"visa_progress": 10,
		"career_progress": 0
	}
	var flags := {}
	match extreme:
		"zero_money":
			state["money"] = 0
		"deep_debt":
			state["money"] = -2500
			state["stress"] = 80
			state["hunger"] = 75
		"no_energy":
			state["energy"] = 0
			state["stress"] = 85
		"all_negative":
			state["money"] = -1500
			state["energy"] = 0
			state["stress"] = 95
			state["loneliness"] = 95
			state["hunger"] = 95
			state["academic_progress"] = 0
			state["language"] = 0
			state["social"] = 0
			state["visa_progress"] = 0
		"no_language":
			state["language"] = 0
		"flag_chaos":
			flags = {"aps_passed": true, "testdaf_passed": true, "registered_city": true, "insurance_ready": true}
			state["visa_progress"] = 5
		"week_zero":
			state["week"] = 0
		"already_registered":
			flags = {"registered_city": true, "insurance_ready": true, "bank_ready": true}
			state["visa_progress"] = 65
	return {"id": extreme, "initial_state": state, "flags": flags}

func _make_policy(policy_name: String):
	match policy_name:
		"random":
			return RandomPolicyScript.new()
		"study":
			return StudyPolicyScript.new()
		"work":
			return WorkPolicyScript.new()
		"admin":
			return AdminPolicyScript.new()
		"social":
			return SocialPolicyScript.new()
		"slacker":
			return SlackerPolicyScript.new()
		"balanced":
			return BalancedPolicyScript.new()
	return PlayerPolicyScript.new()

func _fill_action_plan(action_ids: Array, available_actions: Array, slots: int) -> Array:
	var selected := action_ids.duplicate()
	var used_slots := 0
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
		if choice.is_available(game_state):
			choices.append(choice)
	return choices

func _choice_index(event, choice) -> int:
	for index in range(event.choices.size()):
		if event.choices[index] == choice:
			return index
	return -1

func _action_ids(actions: Array) -> Array:
	var ids: Array = []
	for action in actions:
		ids.append(action.id)
	return ids

func _extremes(raw: String) -> Array:
	var values: Array = []
	for item in raw.split(",", false):
		var value := str(item).strip_edges()
		if value != "":
			values.append(value)
	return values if not values.is_empty() else ["zero_money"]

func _parse_args() -> Dictionary:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		args = OS.get_cmdline_args()
	var parsed: Dictionary = {}
	var index := 0
	while index < args.size():
		var arg := str(args[index])
		if arg.begins_with("--"):
			var body := arg.substr(2)
			var equals_index := body.find("=")
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
	var global_path := _global_path(path)
	DirAccess.make_dir_recursive_absolute(global_path.get_base_dir())
	return FileAccess.open(global_path, FileAccess.WRITE)

func _global_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	if path.begins_with("/"):
		return path
	return ProjectSettings.globalize_path("res://%s" % path)
