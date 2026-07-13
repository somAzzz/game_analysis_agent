extends SceneTree

const SimulationEngineScript := preload("res://scripts/simulation/SimulationEngine.gd")
const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")
const ExamResolverScript := preload("res://scripts/simulation/ExamResolver.gd")
const EndingResolverScript := preload("res://scripts/simulation/EndingResolver.gd")
const RiskEvaluatorScript := preload("res://scripts/simulation/RiskEvaluator.gd")

var game_state: Node
var data_registry: Node

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	game_state = root.get_node("/root/GameState")
	data_registry = root.get_node("/root/DataRegistry")
	var config := _parse_args()
	var plan_path := str(config.get("plan", ""))
	var out_path := str(config.get("out", "res://reports/interactive_trace.json"))
	if plan_path == "":
		printerr("RunInteractiveProbe requires --plan=/path/to/plan.json")
		quit(2)
		return
	var payload := _read_json(plan_path)
	if payload.is_empty():
		printerr("RunInteractiveProbe could not read plan: %s" % plan_path)
		quit(3)
		return
	var trace := _replay(payload)
	_write_json(out_path, trace)
	print("Interactive probe wrote %s" % _global_path(out_path))
	quit(0)

func _replay(payload: Dictionary) -> Dictionary:
	var seed := int(payload.get("seed", 42))
	var difficulty := str(payload.get("difficulty", "normal"))
	var scenario_id := str(payload.get("scenario", "default_first_semester"))
	var force_finish := bool(payload.get("force_finish", false))
	game_state.reset()
	game_state.configure_run({
		"run_id": 1,
		"seed": seed,
		"policy": "interactive_player",
		"difficulty": difficulty,
		"content_version": game_state.CONTENT_VERSION,
		"rules_version": game_state.RULES_VERSION
	})
	var scenario := _load_scenario(scenario_id)
	if not scenario.is_empty():
		game_state.apply_scenario(scenario)

	var engine = SimulationEngineScript.new()
	var plan: Array = payload.get("plan", []) if payload.get("plan", []) is Array else []
	var last_trace := _empty_trace(engine)
	for item in plan:
		if not item is Dictionary:
			continue
		if game_state.last_ending_id != "":
			break
		last_trace = _play_one_week(engine, item)

	if force_finish or game_state.week >= 20 or game_state.last_ending_id != "":
		var final := _finish_now()
		last_trace["finished"] = true
		last_trace["final_ending_id"] = final.get("final_ending_id", "")
		last_trace["final_exam"] = final.get("final_exam", {})
		last_trace["final_state"] = final.get("final_state", {})
	else:
		last_trace["finished"] = false
		last_trace["final_ending_id"] = ""
		last_trace["final_state"] = game_state.export_state_snapshot()
	last_trace["current_state"] = game_state.export_public_stats()
	last_trace["next_available_actions"] = _action_records(engine.get_available_actions(game_state))
	last_trace["final_week"] = game_state.week
	last_trace["contract_version"] = "1.0"
	last_trace["risk_guidance"] = _risk_guidance()
	return last_trace

func _play_one_week(engine, plan_item: Dictionary) -> Dictionary:
	var before_state: Dictionary = game_state.export_public_stats()
	var available_actions: Array = engine.get_available_actions(game_state)
	var available_action_records := _action_records(available_actions)
	var action_ids: Array = plan_item.get("action_ids", []) if plan_item.get("action_ids", []) is Array else []
	var selected_action_ids: Array = engine.set_plan_from_action_ids(action_ids)
	var action_effects := _describe_action_effects(selected_action_ids)
	var event = engine.resolve_week()
	var after_actions_state: Dictionary = game_state.export_public_stats()
	var event_choice_id := ""
	var event_detail: Dictionary = {}
	var event_choices: Array = []
	var defer_event_choice := bool(plan_item.get("defer_event_choice", false))
	if event != null:
		var available_choices := _available_choices(event)
		event_choices = _choice_records(event, available_choices)
		var requested_choice_id := str(plan_item.get("event_choice_id", ""))
		if defer_event_choice and requested_choice_id == "":
			return {
				"week": before_state.get("week", game_state.week),
				"before_state": before_state,
				"available_actions": available_action_records,
				"selected_action_ids": selected_action_ids,
				"action_effects": action_effects,
				"life_drift_effects": engine.last_life_drift_effects,
				"event_pool": engine.last_event_pool,
				"triggered_event_id": event.id,
				"event_choices": event_choices,
				"event_choice_id": "",
				"event_effects": {},
				"event_success": null,
				"pending_event_choice": true,
				"after_actions_and_drift_state": after_actions_state,
				"after_state": after_actions_state,
				"state": after_actions_state,
				"finished": false,
				"final_ending_id": ""
			}
		var choice = _choice_by_id(event, available_choices, requested_choice_id)
		if choice == null and not available_choices.is_empty():
			choice = available_choices[0]
		if choice != null:
			var original_index := _choice_index(event, choice)
			event_choice_id = _choice_id(event, choice, original_index)
			event_detail = EventResolverScript.resolve_choice_detailed(event, choice, game_state)
		else:
			game_state.mark_event_completed(event.id)
	var after_state: Dictionary = game_state.export_public_stats()
	var finished := false
	var final_payload: Dictionary = {}
	if game_state.week >= 20:
		final_payload = _finish_now()
		finished = true
	else:
		engine.finish_week()
	return {
		"week": before_state.get("week", game_state.week),
		"before_state": before_state,
		"available_actions": available_action_records,
		"selected_action_ids": selected_action_ids,
		"action_effects": action_effects,
		"life_drift_effects": engine.last_life_drift_effects,
		"event_pool": engine.last_event_pool,
		"triggered_event_id": event.id if event != null else "",
		"event_choices": event_choices,
		"event_choice_id": event_choice_id,
		"event_effects": event_detail.get("effects", {}),
		"event_success": event_detail.get("success", null),
		"pending_event_choice": false,
		"after_actions_and_drift_state": after_actions_state,
		"after_state": after_state,
		"state": after_state,
		"finished": finished,
		"final_ending_id": final_payload.get("final_ending_id", "")
	}

func _finish_now() -> Dictionary:
	var exam := ExamResolverScript.resolve_exam(game_state)
	var ending = EndingResolverScript.resolve_ending(data_registry.endings, game_state)
	if ending == null:
		ending = data_registry.get_ending_by_id("stable_start")
	game_state.last_ending_id = ending.id
	return {
		"final_ending_id": ending.id,
		"final_exam": exam,
		"final_state": game_state.export_state_snapshot()
	}

func _empty_trace(engine) -> Dictionary:
	return {
		"week": game_state.week,
		"before_state": game_state.export_public_stats(),
		"available_actions": _action_records(engine.get_available_actions(game_state)),
		"selected_action_ids": [],
		"action_effects": [],
		"life_drift_effects": {},
		"triggered_event_id": "",
		"event_choices": [],
		"event_choice_id": "",
		"event_effects": {},
		"after_state": game_state.export_public_stats(),
		"state": game_state.export_public_stats(),
		"finished": false,
		"final_ending_id": ""
	}

func _risk_guidance() -> Dictionary:
	return {
		"contract_version": "1.0",
		"source": "game_risk_evaluator",
		"evaluator": "RiskEvaluator.get_top_risks",
		"generated_for_week": game_state.week,
		"top_risks": RiskEvaluatorScript.get_top_risks(game_state, 3)
	}

func _action_records(actions: Array) -> Array:
	var records: Array = []
	for action in actions:
		records.append({
			"id": action.id,
			"name": action.name,
			"description": action.description,
			"cost_energy": action.cost_energy,
			"cost_money": action.cost_money,
			"cost_slots": action.cost_slots,
			"effects": action.effects,
			"requirements": action.requirements,
			"tags": action.tags,
			"risk_tags": action.risk_tags,
			"cooldown_group": action.cooldown_group,
			"max_per_week": action.max_per_week
		})
	return records

func _describe_action_effects(action_ids: Array) -> Array:
	var records: Array = []
	for action_id in action_ids:
		var action = data_registry.get_action_by_id(str(action_id))
		if action == null:
			continue
		var effects: Dictionary = action.effects.duplicate(true)
		effects["energy"] = int(effects.get("energy", 0)) - action.cost_energy
		effects["money"] = int(effects.get("money", 0)) - action.cost_money
		records.append({"action_id": action.id, "effects": effects})
	return records

func _available_choices(event) -> Array:
	var choices: Array = []
	for choice in event.choices:
		if choice.is_available(game_state):
			choices.append(choice)
	return choices

func _choice_records(event, choices: Array) -> Array:
	var records: Array = []
	for choice in choices:
		var index := _choice_index(event, choice)
		records.append({
			"choice_id": _choice_id(event, choice, index),
			"text": choice.text,
			"success_rate": EventResolverScript.get_success_rate(choice, game_state),
			"requirements": choice.requirements,
			"success_effects": choice.success_effects,
			"failure_effects": choice.failure_effects,
			"set_flag": choice.set_flag,
			"next_event_id": choice.next_event_id
		})
	return records

func _choice_by_id(event, choices: Array, choice_id: String):
	if choice_id == "":
		return null
	for choice in choices:
		if _choice_id(event, choice, _choice_index(event, choice)) == choice_id:
			return choice
	return null

func _choice_index(event, choice) -> int:
	for index in range(event.choices.size()):
		if event.choices[index] == choice:
			return index
	return -1

func _choice_id(event, choice, index: int) -> String:
	var safe_text := str(choice.text).to_lower().replace(" ", "_")
	return "%s.choice_%02d_%s" % [event.id, index + 1, safe_text]

func _load_scenario(scenario_id: String) -> Dictionary:
	var scenario_path := scenario_id
	if not scenario_path.ends_with(".json"):
		scenario_path = "data/scenarios/%s.json" % scenario_id
	if not scenario_path.begins_with("res://") and not scenario_path.begins_with("user://") and not scenario_path.begins_with("/"):
		scenario_path = "res://%s" % scenario_path
	if not FileAccess.file_exists(scenario_path):
		return {}
	var file = FileAccess.open(scenario_path, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if parsed is Dictionary else {}

func _read_json(path: String) -> Dictionary:
	var normalized := path
	if not normalized.begins_with("res://") and not normalized.begins_with("user://") and not normalized.begins_with("/"):
		normalized = "res://%s" % normalized
	if not FileAccess.file_exists(normalized):
		return {}
	var file = FileAccess.open(normalized, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if parsed is Dictionary else {}

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

func _write_json(path: String, payload: Dictionary) -> void:
	var global_path := _global_path(path)
	DirAccess.make_dir_recursive_absolute(global_path.get_base_dir())
	var file = FileAccess.open(global_path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(payload, "\t"))
		file.store_string("\n")
		file.close()

func _global_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	if path.begins_with("/"):
		return path
	return ProjectSettings.globalize_path("res://%s" % path)
