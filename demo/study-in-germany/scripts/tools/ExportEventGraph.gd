extends SceneTree

const DataLoaderScript := preload("res://scripts/data/DataLoader.gd")

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var config := _parse_args()
	var out_path := str(config.get("out", "res://event_graph.json"))
	var data_registry: Node = root.get_node("/root/DataRegistry")
	var event_records: Array = []
	for index in range(data_registry.events.size()):
		var event = data_registry.events[index]
		var record: Dictionary = DataLoaderScript.event_to_dict(event)
		record["source_order"] = index
		record["choice_count"] = event.choices.size()
		event_records.append(record)
	var action_records: Array = []
	for action in data_registry.actions:
		action_records.append(DataLoaderScript.action_to_dict(action))
	_write_json(out_path, {
		"events": event_records,
		"event_count": event_records.size(),
		"action_count": action_records.size()
	})
	_write_json(out_path.get_base_dir().path_join("action_catalog.json"), {
		"actions": action_records,
		"action_count": action_records.size()
	})
	print("Event graph exported: %d events, %d actions -> %s" % [
		event_records.size(),
		action_records.size(),
		_global_path(out_path)
	])
	quit(0)

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
	if file == null:
		push_error("Cannot write %s" % path)
		return
	file.store_string(JSON.stringify(payload, "\t"))
	file.store_string("\n")
	file.close()

func _global_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	if path.begins_with("/"):
		return path
	return ProjectSettings.globalize_path("res://%s" % path)
