class_name SimulationEngine
extends RefCounted

const ActionResolverScript := preload("res://scripts/simulation/ActionResolver.gd")
const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")
const MAX_ACTION_SLOTS := 4

var planned_actions: Array = []
var last_week_summary: Array = []
var last_event_pool: Dictionary = {}
var last_life_drift_effects: Dictionary = {}

func _state() -> Node:
	return Engine.get_main_loop().root.get_node("/root/GameState")

func _data_registry() -> Node:
	return Engine.get_main_loop().root.get_node("/root/DataRegistry")

func _event_bus() -> Node:
	return Engine.get_main_loop().root.get_node("/root/EventBus")

func used_slots() -> int:
	var total: int = 0
	for action in planned_actions:
		total += action.cost_slots
	return total

func can_add_action(action) -> bool:
	return ActionResolverScript.can_add_action(action, planned_actions, _state(), MAX_ACTION_SLOTS)

func get_available_actions(state: Node = null) -> Array:
	var target_state = state if state != null else _state()
	var available: Array = []
	for action in _data_registry().actions:
		if ActionResolverScript.can_add_action(action, planned_actions, target_state, MAX_ACTION_SLOTS):
			available.append(action)
	return available

func add_action(action) -> bool:
	if not can_add_action(action):
		return false
	planned_actions.append(action)
	return true

func add_action_by_id(action_id: String) -> bool:
	var action = _data_registry().get_action_by_id(action_id)
	return add_action(action)

func set_plan_from_action_ids(action_ids: Array) -> Array:
	clear_plan()
	var accepted: Array = []
	for action_id in action_ids:
		if add_action_by_id(str(action_id)):
			accepted.append(str(action_id))
	return accepted

func remove_action(index: int) -> void:
	if index >= 0 and index < planned_actions.size():
		planned_actions.remove_at(index)

func clear_plan() -> void:
	planned_actions.clear()

func resolve_week():
	var week_summary: Array[String] = []
	var state: Node = _state()
	for action in planned_actions:
		var action_summary: Array = ActionResolverScript.resolve_action(action, state)
		week_summary.append("%s：%s" % [action.name, ", ".join(action_summary)])
	last_life_drift_effects = state.get_weekly_drift_effects()
	var released_amount: int = state.get_blocked_account_release_for_week()
	if released_amount > 0:
		last_life_drift_effects["money"] = int(last_life_drift_effects.get("money", 0)) + released_amount
	var drift: Array = state.apply_weekly_drift()
	week_summary.append("生活开销与自然恢复：%s" % ", ".join(drift))
	planned_actions.clear()
	last_week_summary = week_summary
	_event_bus().week_resolved.emit(week_summary)
	last_event_pool = EventResolverScript.describe_event_pool(_data_registry().events, state)
	var event = EventResolverScript.pick_event(_data_registry().events, state)
	if event != null:
		_event_bus().event_ready.emit(event)
	return event

func finish_week() -> void:
	var state: Node = _state()
	if state.week < 20:
		state.advance_week()
		_event_bus().week_started.emit(state.week)
