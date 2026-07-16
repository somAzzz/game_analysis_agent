extends SceneTree

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var data_registry: Node = root.get_node("/root/DataRegistry")
	var action_ids: Array[String] = []
	for action in data_registry.actions:
		action_ids.append(action.id)
	var event_ids: Array[String] = []
	for event in data_registry.events:
		event_ids.append(event.id)
	var character_ids: Array[String] = []
	for character in data_registry.characters:
		character_ids.append(character.id)
	print("Data sources: actions=%s; action_count=%d; first_actions=%s; events=%s; event_count=%d; first_events=%s; characters=%s; ids=%s; endings=%s; ending_count=%d" % [
		data_registry.action_source,
		data_registry.actions.size(),
		",".join(action_ids.slice(0, mini(5, action_ids.size()))),
		data_registry.event_source,
		data_registry.events.size(),
		",".join(event_ids.slice(0, mini(5, event_ids.size()))),
		data_registry.character_source,
		",".join(character_ids),
		data_registry.ending_source,
		data_registry.endings.size()
	])
	quit(0)
