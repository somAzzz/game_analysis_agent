extends SceneTree

# Interactive playthrough runner.
#
# Reads a JSON plan written by game_analysis_agent.game_tools:
#   {
#     "command": "step" | "export",
#     "weeks": N,
#     "plan": [{"week": 1, "action_ids": [...], "event_choice_id": "..."}, ...],
#     "force_finish": false
#   }
#
# Replays the plan from the initial state and writes a trace JSON to
# `--out` containing the latest after-state, triggered event id, event
# choices, and a `finished` flag.

const SimulationEngineScript := preload("res://scripts/simulation/SimulationEngine.gd")
const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")
const PlayerPolicyScript := preload("res://scripts/policies/PlayerPolicy.gd")
const BalancedPolicyScript := preload("res://scripts/policies/BalancedPolicy.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var game_state: Node = root.get_node("/root/GameState")
	var data_registry: Node = root.get_node("/root/DataRegistry")
	var args: Dictionary = _parse_args()
	var plan_path: String = _global_path(args.get("plan", "res://_plan.json"))
	var out_path: String = _global_path(args.get("out", "res://_trace.json"))

	if not FileAccess.file_exists(plan_path):
		printerr("Missing plan file: %s" % plan_path)
		quit(1)
		return

	var plan_text: String = FileAccess.get_file_as_string(plan_path)
	var plan = JSON.parse_string(plan_text)
	if typeof(plan) != TYPE_DICTIONARY:
		printerr("Plan must be a JSON object: %s" % plan_path)
		quit(1)
		return

	game_state.reset()
	game_state.configure_run({
		"run_id": 0,
		"seed": 42,
		"policy": "player",
		"difficulty": "normal",
	})

	var weekly_plan: Array = plan.get("plan", [])
	var engine = SimulationEngineScript.new()
	var policy = BalancedPolicyScript.new()
	var final_week: int = 0
	var last_after_state: Dictionary = game_state.export_public_stats()
	var last_triggered_event_id: String = ""
	var last_event_choices: Array = []
	var finished: bool = false
	var final_ending_id: String = ""

	for step_record in weekly_plan:
		var week: int = int(step_record.get("week", 0))
		var action_ids: Array = step_record.get("action_ids", [])
		var event_choice_id: String = str(step_record.get("event_choice_id", ""))

		var available_actions: Array = engine.get_available_actions(game_state)
		var chosen: Array = []
		for action in available_actions:
			if action_ids.has(action.id):
				chosen.append(action)
		chosen = engine.set_plan_from_action_ids(
			[str(a.id) for a in chosen]
		)
		# Anything missing? Fall back to a balance fill.
		if chosen.size() < min(SimulationEngineScript.MAX_ACTION_SLOTS, action_ids.size()):
			var filler: Array = engine.get_available_actions(game_state)
			for action in filler:
				if chosen.size() >= SimulationEngineScript.MAX_ACTION_SLOTS:
					break
				if action.id in chosen:
					continue
				if engine.add_action(action):
					chosen.append(action.id)

		var event = engine.resolve_week()
		var after_state: Dictionary = game_state.export_public_stats()
		last_after_state = after_state
		final_week = week
		if event != null:
			last_triggered_event_id = event.id
			var available_choices: Array = _available_choices(event)
			last_event_choices = available_choices
			var chosen_index: int = _resolve_choice_index(
				event,
				event_choice_id,
				available_choices,
			)
			if chosen_index >= 0 and chosen_index < available_choices.size():
				EventResolverScript.resolve_choice_detailed(
					event,
					available_choices[chosen_index],
					game_state,
				)
		if game_state.week >= int(plan.get("weeks", 20)) and not finished:
			final_ending_id = "max_weeks_reached"
			finished = true
			break
		engine.finish_week()

	if bool(plan.get("force_finish", false)) and not finished:
		if game_state.last_ending_id == "":
			game_state.last_ending_id = "manually_finished"
		final_ending_id = game_state.last_ending_id
		finished = true

	var trace: Dictionary = {
		"finished": finished or bool(plan.get("force_finish", false)),
		"final_week": final_week,
		"triggered_event_id": last_triggered_event_id,
		"event_choices": last_event_choices,
		"after_state": last_after_state,
		"final_ending_id": final_ending_id,
		"final_state": game_state.export_state_snapshot(),
	}

	_write_json(out_path, trace)
	print("Interactive probe trace -> %s" % out_path)
	quit(0)


func _available_choices(event) -> Array:
	var choices: Array = []
	for choice in event.choices:
		if choice.is_available(root.get_node("/root/GameState")):
			choices.append(choice)
	return choices


func _resolve_choice_index(
	event,
	event_choice_id: String,
	available_choices: Array,
) -> int:
	if event_choice_id == "" or available_choices.is_empty():
		return 0
	for index in range(event.choices.size()):
		var choice = event.choices[index]
		var safe_text: String = str(choice.text).to_lower().replace(" ", "_")
		var expected: String = "%s.choice_%02d_%s" % [event.id, index + 1, safe_text]
		if expected == event_choice_id:
			# Translate from event.choices index to available_choices index.
			return _index_in(choice, available_choices)
		if str(choice.text) == event_choice_id:
			return _index_in(choice, available_choices)
	return 0


func _index_in(needle, haystack: Array) -> int:
	for index in range(haystack.size()):
		if haystack[index] == needle:
			return index
	return -1


func _write_json(path: String, data) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(data))
		file.close()


func _global_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	if path.begins_with("/"):
		return path
	return ProjectSettings.globalize_path("res://%s" % path)


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