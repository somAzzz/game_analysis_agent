class_name PlayerPolicy
extends RefCounted

func choose_actions(_state: Dictionary, available_actions: Array, slots: int) -> Array:
	var selected: Array = []
	var used_slots: int = 0
	var scored: Array = []
	for action in available_actions:
		scored.append({"action": action, "score": score_action(action, _state)})
	scored.sort_custom(func(a, b) -> bool: return float(a["score"]) > float(b["score"]))
	for entry in scored:
		var action = entry["action"]
		if used_slots + action.cost_slots <= slots:
			selected.append(action.id)
			used_slots += action.cost_slots
		if used_slots >= slots:
			break
	return selected

func choose_event_option(state: Dictionary, event, available_choices: Array) -> int:
	if available_choices.is_empty():
		return -1
	var best_index: int = 0
	var best_score: float = -INF
	for index in range(available_choices.size()):
		var score: float = score_choice(available_choices[index], state)
		if score > best_score:
			best_score = score
			best_index = index
	return best_index

func score_action(action, _state: Dictionary) -> float:
	return _weighted_effect_score(action.effects) - action.cost_energy * 0.15 - action.cost_money * 0.01

func score_choice(choice, _state: Dictionary) -> float:
	return _weighted_effect_score(choice.success_effects) * float(choice.success_rate) + _weighted_effect_score(choice.failure_effects) * (1.0 - float(choice.success_rate))

func _weighted_effect_score(effects: Dictionary) -> float:
	var score: float = 0.0
	for key in effects.keys():
		var amount: float = float(effects[key])
		match str(key):
			"money":
				score += amount * 0.03
			"energy":
				score += amount * 0.45
			"stress":
				score -= amount * 0.8
			"loneliness":
				score -= amount * 0.55
			"hunger":
				score -= amount * 0.55
			"academic_progress":
				score += amount * 1.0
			"exam_readiness":
				score += amount * 1.1
			"language":
				score += amount * 0.85
			"social":
				score += amount * 0.7
			"visa_progress":
				score += amount * 1.0
			"career_progress":
				score += amount * 0.75
			"gpa_score":
				score += amount * 0.55
			"aps_knowledge":
				score += amount * 0.9
			"aps_score":
				score += amount * 1.2
			"work_hours", "current_week_work_hours":
				score += amount * 0.05
			"illegal_work_hours":
				score -= amount * 0.25
			"annual_work_half_days":
				score -= amount * 0.08
			"failed_courses":
				score -= amount * 14.0
	return score
