class_name EventResolver
extends RefCounted

static func pick_event(events: Array, state: Node):
	for event in events:
		if event.event_type == "fixed" and event.can_trigger(state):
			return event

	var conditional_candidates: Array = []
	var conditional_total_weight: float = 0.0
	for event in events:
		if event.event_type == "conditional" and event.can_trigger(state):
			conditional_candidates.append(event)
			conditional_total_weight += get_event_weight(event, state)

	if not conditional_candidates.is_empty():
		return _pick_weighted(conditional_candidates, conditional_total_weight, state)

	var candidates: Array = []
	var total_weight: float = 0.0
	for event in events:
		if event.event_type == "random" and event.can_trigger(state):
			candidates.append(event)
			total_weight += get_event_weight(event, state)

	if candidates.is_empty():
		return null

	return _pick_weighted(candidates, total_weight, state)

static func resolve_choice(event, choice, state: Node) -> String:
	var result: Dictionary = resolve_choice_detailed(event, choice, state)
	return str(result.get("message", ""))

static func resolve_choice_detailed(event, choice, state: Node) -> Dictionary:
	if event == null or choice == null:
		return {}
	var final_rate: float = get_success_rate(choice, state)
	var success: bool = _rand_float() <= final_rate
	var effects: Dictionary = choice.success_effects if success else choice.failure_effects
	var effect_summary: Array[String] = state.apply_effects(effects)
	if success and choice.set_flag != "":
		state.set_flag(choice.set_flag)
	state.mark_event_completed(event.id)
	var outcome: String = "成功" if success else "结果不理想"
	var message: String = "%s：%s。%s（成功率 %d%%）" % [event.title, choice.text, outcome, roundi(final_rate * 100.0)]
	if not effect_summary.is_empty():
		message += "（%s）" % ", ".join(effect_summary)
	state.add_log(message)
	return {
		"event_id": event.id,
		"choice_text": choice.text,
		"success": success,
		"success_rate": final_rate,
		"effects": effects.duplicate(true),
		"set_flag": choice.set_flag if success else "",
		"summary": effect_summary,
		"message": message
	}

static func get_success_rate(choice, state: Node) -> float:
	var rate: float = float(choice.success_rate)
	if rate >= 1.0:
		return 1.0
	for stat_name in choice.success_modifiers.keys():
		var modifier: float = float(choice.success_modifiers[stat_name])
		rate += _stat_value(state, str(stat_name)) * modifier
	rate += _difficulty_success_bonus(state)
	return clampf(rate, _difficulty_success_min(state), _difficulty_success_max(state))

static func describe_success_rate(choice, state: Node) -> String:
	var parts: Array[String] = []
	for stat_name in choice.success_modifiers.keys():
		var modifier: float = float(choice.success_modifiers[stat_name])
		var sign: String = "+" if modifier >= 0.0 else ""
		parts.append("%s %s%.3f" % [state.stat_label(str(stat_name)), sign, modifier])
	if parts.is_empty():
		return "固定检定"
	return "受 %s 影响" % "、".join(parts)

static func describe_event_pool(events: Array, state: Node) -> Dictionary:
	var fixed: Array = []
	var conditional: Array = []
	var random: Array = []
	for event in events:
		if not event.can_trigger(state):
			continue
		var entry: Dictionary = {
			"event_id": event.id,
			"base_weight": event.weight,
			"weight": get_event_weight(event, state),
			"focus": _event_focus(event),
			"type": event.event_type
		}
		match event.event_type:
			"fixed":
				fixed.append(entry)
			"conditional":
				conditional.append(entry)
			"random":
				random.append(entry)
	return {
		"fixed": fixed,
		"conditional": conditional,
		"random": random
	}

static func _stat_value(state: Node, stat_name: String) -> float:
	match stat_name:
		"money":
			return clampf(float(state.money) / 35.0, -50.0, 100.0)
		"energy":
			return float(state.energy)
		"stress":
			return float(state.stress)
		"loneliness":
			return float(state.loneliness)
		"hunger":
			return float(state.hunger)
		"academic_progress":
			return float(state.academic_progress)
		"exam_readiness":
			return float(state.exam_readiness)
		"language":
			return float(state.language)
		"social":
			return float(state.social)
		"visa_progress":
			return float(state.visa_progress)
		"career_progress":
			return float(state.career_progress)
		"gpa_score":
			return float(state.gpa_score)
		"aps_knowledge":
			return float(state.aps_knowledge)
		"aps_score":
			return float(state.aps_score)
		"current_week_work_hours", "work_hours":
			return float(state.current_week_work_hours)
		"annual_work_half_days":
			return float(state.annual_work_half_days)
		"failed_courses":
			return float(state.failed_courses)
	return 0.0

static func get_event_weight(event, state: Node) -> float:
	var weight: float = float(event.weight)
	weight *= _difficulty_event_type_weight(state, event.event_type)
	weight *= _difficulty_event_focus_weight(state, _event_focus(event))
	return maxf(0.0, weight)

static func _pick_weighted(candidates: Array, total_weight: float, state: Node):
	if candidates.is_empty():
		return null
	if total_weight <= 0.0:
		return candidates.front()
	var roll: float = _rand_float() * total_weight
	var current: float = 0.0
	for event in candidates:
		current += get_event_weight(event, state)
		if roll <= current:
			return event
	return candidates.back()

static func _event_focus(event) -> String:
	var text: String = "%s %s %s" % [event.id, event.title, event.body]
	if event.trigger.has("min_hunger") or text.contains("饥饿") or text.contains("吃饭") or text.contains("喝酒") or text.contains("食堂") or text.contains("做饭"):
		return "life"
	if event.trigger.has("min_stress") or text.contains("压力") or text.contains("孤独") or text.contains("burnout") or text.contains("心理") or text.contains("失眠") or text.contains("感冒"):
		return "stress"
	if event.trigger.has("max_visa") or event.trigger.has("min_visa") or text.contains("签证") or text.contains("行政") or text.contains("Termin") or text.contains("Anmeldung") or text.contains("银行") or text.contains("保险"):
		return "admin"
	if event.trigger.has("max_money") or event.trigger.has("min_money") or text.contains("房租") or text.contains("工资") or text.contains("账户") or text.contains("费用") or text.contains("退款") or text.contains("金钱") or text.contains("打工") or text.contains("工时"):
		return "money"
	if event.trigger.has("max_academic") or event.trigger.has("min_academic") or text.contains("考试") or text.contains("课程") or text.contains("Klausur") or text.contains("作业") or text.contains("Presentation"):
		return "academic"
	if text.contains("顺利") or text.contains("退款") or text.contains("帮助") or text.contains("好消息") or text.contains("掌声"):
		return "positive"
	return "neutral"

static func _difficulty_success_bonus(state: Node) -> float:
	var config = _difficulty_config()
	if config != null:
		return config.get_success_rate_bonus(state.difficulty)
	return 0.0

static func _difficulty_success_min(state: Node) -> float:
	var config = _difficulty_config()
	if config != null:
		return config.get_success_rate_min(state.difficulty)
	return 0.05

static func _difficulty_success_max(state: Node) -> float:
	var config = _difficulty_config()
	if config != null:
		return config.get_success_rate_max(state.difficulty)
	return 0.9

static func _difficulty_event_type_weight(state: Node, event_type: String) -> float:
	var config = _difficulty_config()
	if config != null:
		return config.get_event_type_weight(state.difficulty, event_type)
	return 1.0

static func _difficulty_event_focus_weight(state: Node, focus: String) -> float:
	var config = _difficulty_config()
	if config != null:
		return config.get_event_focus_weight(state.difficulty, focus)
	return 1.0

static func _difficulty_config():
	var main_loop = Engine.get_main_loop()
	if main_loop is SceneTree and main_loop.root.has_node("/root/DifficultyConfig"):
		return main_loop.root.get_node("/root/DifficultyConfig")
	return null

static func _rand_float() -> float:
	var main_loop = Engine.get_main_loop()
	if main_loop is SceneTree and main_loop.root.has_node("/root/RandomService"):
		return main_loop.root.get_node("/root/RandomService").rand_float()
	return randf()
