class_name DataLoader
extends RefCounted

const ActionDefScript := preload("res://scripts/data/ActionDef.gd")
const EventChoiceDefScript := preload("res://scripts/data/EventChoiceDef.gd")
const EventDefScript := preload("res://scripts/data/EventDef.gd")
const CharacterDefScript := preload("res://scripts/data/CharacterDef.gd")
const EndingDefScript := preload("res://scripts/data/EndingDef.gd")

static func load_json_array(path: String) -> Array:
	var file = FileAccess.open(path, FileAccess.READ)
	if file == null:
		return []
	var parsed = JSON.parse_string(file.get_as_text())
	if parsed is Array:
		return parsed
	if parsed is Dictionary and parsed.has("items"):
		var items = parsed["items"]
		if items is Array:
			return items
	return []

static func load_actions(path: String) -> Array:
	var records := load_json_array(path)
	var loaded: Array = []
	for record in records:
		if record is Dictionary:
			loaded.append(action_from_dict(record))
	return loaded

static func load_events(path: String) -> Array:
	var records := load_json_array(path)
	var loaded: Array = []
	for record in records:
		if record is Dictionary:
			loaded.append(event_from_dict(record))
	return loaded

static func load_events_from_paths(paths: Array) -> Array:
	var loaded: Array = []
	for path in paths:
		for event in load_events(str(path)):
			loaded.append(event)
	loaded.sort_custom(func(a, b): return int(a.source_order) < int(b.source_order))
	return loaded

static func load_characters(path: String) -> Array:
	var records := load_json_array(path)
	var loaded: Array = []
	for record in records:
		if record is Dictionary:
			loaded.append(character_from_dict(record))
	return loaded

static func load_endings(path: String) -> Array:
	var records := load_json_array(path)
	var loaded: Array = []
	for record in records:
		if record is Dictionary:
			loaded.append(ending_from_dict(record))
	return loaded

static func action_from_dict(record: Dictionary):
	var action = ActionDefScript.new()
	action.id = str(record.get("id", ""))
	action.name = str(record.get("name", ""))
	action.description = str(record.get("description", ""))
	action.cost_energy = int(record.get("cost_energy", 0))
	action.cost_money = int(record.get("cost_money", 0))
	action.cost_slots = int(record.get("cost_slots", 1))
	action.effects = _dict(record.get("effects", {}))
	action.requirements = _dict(record.get("requirements", {}))
	action.tags = _array(record.get("tags", []))
	action.risk_tags = _array(record.get("risk_tags", []))
	action.set_flag = str(record.get("set_flag", ""))
	action.cooldown_group = str(record.get("cooldown_group", ""))
	action.max_per_week = int(record.get("max_per_week", 0))
	action.diminishing_window = int(record.get("diminishing_window", 0))
	action.diminishing_factor = float(record.get("diminishing_factor", 1.0))
	return action

static func event_from_dict(record: Dictionary):
	var event = EventDefScript.new()
	event.id = str(record.get("id", ""))
	event.title = str(record.get("title", ""))
	event.body = str(record.get("body", ""))
	event.event_type = str(record.get("event_type", "random"))
	event.trigger = _dict(record.get("trigger", {}))
	event.weight = float(record.get("weight", 1.0))
	event.repeatable = bool(record.get("repeatable", false))
	event.source_order = int(record.get("source_order", 0))
	event.choices = []
	for choice_record in _array(record.get("choices", [])):
		if choice_record is Dictionary:
			event.choices.append(choice_from_dict(choice_record))
	return event

static func choice_from_dict(record: Dictionary):
	var choice = EventChoiceDefScript.new()
	choice.text = str(record.get("text", ""))
	choice.requirements = _dict(record.get("requirements", {}))
	choice.success_rate = float(record.get("success_rate", 1.0))
	choice.success_modifiers = _dict(record.get("success_modifiers", {}))
	choice.success_effects = _dict(record.get("success_effects", {}))
	choice.failure_effects = _dict(record.get("failure_effects", {}))
	choice.set_flag = str(record.get("set_flag", ""))
	choice.next_event_id = str(record.get("next_event_id", ""))
	return choice

static func character_from_dict(record: Dictionary):
	var character = CharacterDefScript.new()
	character.id = str(record.get("id", ""))
	character.name = str(record.get("name", ""))
	character.role = str(record.get("role", ""))
	character.description = str(record.get("description", ""))
	character.starting_relationship = _dict(record.get("starting_relationship", {}))
	return character

static func ending_from_dict(record: Dictionary):
	var ending = EndingDefScript.new()
	ending.id = str(record.get("id", ""))
	ending.title = str(record.get("title", ""))
	ending.description = str(record.get("description", ""))
	ending.priority = int(record.get("priority", 0))
	ending.conditions = _dict(record.get("conditions", {}))
	return ending

static func action_to_dict(action) -> Dictionary:
	return {
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
		"set_flag": action.set_flag,
		"cooldown_group": action.cooldown_group,
		"max_per_week": action.max_per_week,
		"diminishing_window": action.diminishing_window,
		"diminishing_factor": action.diminishing_factor
	}

static func event_to_dict(event) -> Dictionary:
	var choices: Array = []
	for choice in event.choices:
		choices.append(choice_to_dict(choice))
	return {
		"id": event.id,
		"title": event.title,
		"body": event.body,
		"event_type": event.event_type,
		"trigger": event.trigger,
		"weight": event.weight,
		"repeatable": event.repeatable,
		"source_order": event.source_order,
		"choices": choices
	}

static func choice_to_dict(choice) -> Dictionary:
	return {
		"text": choice.text,
		"requirements": choice.requirements,
		"success_rate": choice.success_rate,
		"success_modifiers": choice.success_modifiers,
		"success_effects": choice.success_effects,
		"failure_effects": choice.failure_effects,
		"set_flag": choice.set_flag,
		"next_event_id": choice.next_event_id
	}

static func character_to_dict(character) -> Dictionary:
	return {
		"id": character.id,
		"name": character.name,
		"role": character.role,
		"description": character.description,
		"starting_relationship": character.starting_relationship
	}

static func ending_to_dict(ending) -> Dictionary:
	return {
		"id": ending.id,
		"title": ending.title,
		"description": ending.description,
		"priority": ending.priority,
		"conditions": ending.conditions
	}

static func _dict(value) -> Dictionary:
	if value is Dictionary:
		return value.duplicate(true)
	return {}

static func _array(value) -> Array:
	if value is Array:
		return value.duplicate(true)
	return []
