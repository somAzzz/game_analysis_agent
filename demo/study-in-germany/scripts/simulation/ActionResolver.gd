class_name ActionResolver
extends RefCounted

static func can_add_action(action, planned_actions: Array, state: Node, max_slots: int) -> bool:
	if action == null or not action.can_use(state):
		return false
	var used_slots := 0
	var planned_action_count := 0
	var planned_group_count := 0
	for planned in planned_actions:
		used_slots += planned.cost_slots
		if planned.id == action.id:
			planned_action_count += 1
		if action.cooldown_group != "" and planned.cooldown_group == action.cooldown_group:
			planned_group_count += 1
	if action.max_per_week > 0:
		if state.get_weekly_action_count(action.id) + planned_action_count >= action.max_per_week:
			return false
		if action.cooldown_group != "" and state.get_weekly_group_count(action.cooldown_group) + planned_group_count >= action.max_per_week:
			return false
	return used_slots + action.cost_slots <= max_slots

static func resolve_action(action, state: Node) -> Array[String]:
	if action == null or not action.can_use(state):
		var reason: String = action.disabled_reason(state) if action != null else "行动不存在"
		if action != null:
			state.add_log("本周行动：%s（未执行：%s）" % [action.name, reason])
		return ["未执行：%s" % reason]
	var effects: Dictionary = action.effects.duplicate(true)
	effects = _apply_diminishing_returns(effects, action, state)
	effects["energy"] = int(effects.get("energy", 0)) - action.cost_energy
	effects["money"] = int(effects.get("money", 0)) - action.cost_money
	effects["_semantic"] = action.name
	var summary: Array[String] = state.apply_effects(effects)
	if action.set_flag != "":
		state.set_flag(action.set_flag)
	if action.tags.has("social") and int(action.effects.get("social", 0)) > 0:
		var spent_money: bool = action.cost_money > 0 or int(action.effects.get("money", 0)) < 0
		state.record_social_action(action.id, spent_money)
	var action_type := str(action.tags[0]) if not action.tags.is_empty() else ""
	state.add_action_history(action.id, action_type, action.cooldown_group)
	if action.id == "aps_interview":
		var aps_result: Dictionary = state.resolve_aps_result()
		summary.append("APS %d（%s）" % [int(aps_result.get("score", 0)), str(aps_result.get("tier", "未定位"))])
	if action.id == "testdaf_exam_china" or action.id == "testdaf_exam_germany":
		var testdaf_result: Dictionary = state.resolve_testdaf_result(action.id == "testdaf_exam_germany")
		summary.append("TestDaF %s" % str(testdaf_result.get("label", "-")))
	state.add_log("本周行动：%s（%s）" % [action.name, ", ".join(summary)])
	return summary

static func _apply_diminishing_returns(effects: Dictionary, action, state: Node) -> Dictionary:
	if action.cooldown_group == "" or action.diminishing_window <= 0 or action.diminishing_factor >= 1.0:
		return effects
	var recent_count: int = state.get_recent_group_count(action.cooldown_group, action.diminishing_window)
	if recent_count <= 0:
		return effects
	var factor := pow(action.diminishing_factor, recent_count)
	var adjusted := effects.duplicate(true)
	for key in ["energy", "stress", "loneliness", "hunger"]:
		if not adjusted.has(key):
			continue
		var amount := int(adjusted[key])
		if _is_restorative_effect(str(key), amount):
			adjusted[key] = int(round(float(amount) * factor))
	return adjusted

static func _is_restorative_effect(key: String, amount: int) -> bool:
	if key == "energy" and amount > 0:
		return true
	if ["stress", "loneliness", "hunger"].has(key) and amount < 0:
		return true
	return false
