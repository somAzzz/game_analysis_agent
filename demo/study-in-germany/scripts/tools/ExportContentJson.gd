extends SceneTree

const DataLoaderScript := preload("res://scripts/data/DataLoader.gd")

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var data_registry: Node = root.get_node("/root/DataRegistry")
	_write_json("res://data/actions/generated_actions.json", _action_records(data_registry.actions))
	_write_json("res://data/events/generated_events.json", _event_records(data_registry.events))
	_write_json("res://data/endings/generated_endings.json", _ending_records(data_registry.endings))
	_write_json("res://data/characters/npcs.json", _character_records(data_registry.characters))
	print("Exported JSON content: %d actions, %d events, %d endings, %d characters" % [
		data_registry.actions.size(),
		data_registry.events.size(),
		data_registry.endings.size(),
		data_registry.characters.size()
	])
	quit(0)

func _action_records(items: Array) -> Array:
	var records: Array = []
	for item in items:
		records.append(DataLoaderScript.action_to_dict(item))
	return records

func _event_records(items: Array) -> Array:
	var records: Array = []
	for index in range(items.size()):
		var record: Dictionary = DataLoaderScript.event_to_dict(items[index])
		record["source_order"] = index
		records.append(record)
	return records

func _ending_records(items: Array) -> Array:
	var records: Array = []
	for item in items:
		records.append(DataLoaderScript.ending_to_dict(item))
	return records

func _character_records(items: Array) -> Array:
	var records: Array = []
	for item in items:
		records.append(DataLoaderScript.character_to_dict(item))
	return records

func _write_json(path: String, records: Array) -> void:
	var global_path := ProjectSettings.globalize_path(path)
	DirAccess.make_dir_recursive_absolute(global_path.get_base_dir())
	var file = FileAccess.open(global_path, FileAccess.WRITE)
	if file == null:
		push_error("Cannot write %s" % path)
		return
	file.store_string(JSON.stringify({"items": records}, "\t"))
	file.store_string("\n")
	file.close()
