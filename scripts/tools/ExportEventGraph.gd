extends SceneTree

# Export the static event + action catalog so the Python agent can read
# events, choices, triggers, and action definitions without spinning up a
# game instance.

const PlayerPolicyScript := preload("res://scripts/policies/PlayerPolicy.gd")

func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var data_registry: Node = root.get_node("/root/DataRegistry")
	var game_state: Node = root.get_node("/root/GameState")
	var args: Dictionary = _parse_args()
	var events_path: String = _global_path(args.get("out", "res://event_graph.json"))
	var actions_path: String = events_path.get_base_dir() + "/action_catalog.json"

	var events_payload := []
	for event in data_registry.events:
		var choices_payload := []
		for choice in event.choices:
			choices_payload.append({
				"text": choice.text,
				"success_rate": choice.success_rate,
				"success_effects": choice.success_effects.duplicate(true),
				"failure_effects": choice.failure_effects.duplicate(true),
				"success_modifiers": choice.success_modifiers.duplicate(true),
				"requirements": choice.requirements.duplicate(true),
				"set_flag": choice.set_flag,
			})
		events_payload.append({
			"id": event.id,
			"title": event.title,
			"body": event.body,
			"event_type": event.event_type,
			"trigger": event.trigger.duplicate(true),
			"weight": event.weight,
			"repeatable": event.repeatable,
			"choices": choices_payload,
		})

	var actions_payload := []
	for action in data_registry.actions:
		actions_payload.append({
			"id": action.id,
			"name": action.name,
			"description": action.description,
			"cost_energy": action.cost_energy,
			"cost_money": action.cost_money,
			"cost_slots": action.cost_slots,
			"effects": action.effects.duplicate(true),
			"requirements": action.requirements.duplicate(true),
			"tags": Array(action.tags),
			"risk_tags": Array(action.risk_tags),
			"set_flag": action.set_flag,
			"cooldown_group": action.cooldown_group,
			"max_per_week": action.max_per_week,
		})

	var endings_payload := []
	for ending in data_registry.endings:
		endings_payload.append({
			"id": ending.id,
			"title": ending.title,
			"description": ending.description,
			"priority": ending.priority,
			"conditions": ending.conditions.duplicate(true),
		})

	var payload := {
		"version": "0.2.0",
		"exported_at": Time.get_datetime_string_from_system(true),
		"events": events_payload,
		"actions": actions_payload,
		"endings": endings_payload,
	}

	_write_json(events_path, payload)
	_write_json(actions_path, {"actions": actions_payload})

	print(
		(
			"Exported %d events, %d actions, %d endings -> %s + %s"
			% [events_payload.size(), actions_payload.size(), endings_payload.size(), events_path, actions_path]
		)
	)
	quit(0)


func _write_json(path: String, data) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(data, "\t"))
		file.close()


func _global_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://") or path.begins_with("/"):
		if path.begins_with("res://") or path.begins_with("user://"):
			return ProjectSettings.globalize_path(path)
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