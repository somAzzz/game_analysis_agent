class_name RandomPolicy
extends "res://scripts/policies/PlayerPolicy.gd"

func choose_actions(_state: Dictionary, available_actions: Array, slots: int) -> Array:
	var pool: Array = available_actions.duplicate()
	var selected: Array = []
	var used_slots: int = 0
	while not pool.is_empty() and used_slots < slots:
		var index: int = _rand_int(0, pool.size() - 1)
		var action = pool[index]
		pool.remove_at(index)
		if used_slots + action.cost_slots <= slots:
			selected.append(action.id)
			used_slots += action.cost_slots
	return selected

func choose_event_option(_state: Dictionary, _event, available_choices: Array) -> int:
	if available_choices.is_empty():
		return -1
	return _rand_int(0, available_choices.size() - 1)

func _rand_int(min_value: int, max_value: int) -> int:
	var main_loop = Engine.get_main_loop()
	if main_loop is SceneTree and main_loop.root.has_node("/root/RandomService"):
		return main_loop.root.get_node("/root/RandomService").rand_int(min_value, max_value)
	return randi_range(min_value, max_value)
