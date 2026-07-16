class_name EventChoiceDef
extends Resource

@export var text: String = ""
@export var requirements: Dictionary = {}
@export var success_rate: float = 1.0
@export var success_modifiers: Dictionary = {}
@export var success_effects: Dictionary = {}
@export var failure_effects: Dictionary = {}
@export var set_flag: String = ""
@export var next_event_id: String = ""

func is_available(state: Node) -> bool:
	for key in requirements.keys():
		var value = requirements[key]
		if key == "min_money" and state.money < int(value):
			return false
		if key == "min_language" and state.language < int(value):
			return false
		if key == "min_social" and state.social < int(value):
			return false
		if key == "flag" and not state.flags.has(str(value)):
			return false
	return true
