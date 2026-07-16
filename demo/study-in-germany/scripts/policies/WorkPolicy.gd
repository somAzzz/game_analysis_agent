class_name WorkPolicy
extends "res://scripts/policies/PlayerPolicy.gd"

const EconomyRulesRef := preload("res://scripts/simulation/EconomyRules.gd")

func choose_actions(state: Dictionary, available_actions: Array, slots: int) -> Array:
	var selected: Array = []
	var used_slots := 0
	var planned_work_hours := int(state.get("current_week_work_hours", 0))
	var arrears := int(state.get("arrears_amount", 0))
	var scored: Array = []
	for action in available_actions:
		scored.append({"action": action, "score": score_action(action, state)})
	scored.sort_custom(func(a, b) -> bool: return float(a["score"]) > float(b["score"]))
	for entry in scored:
		var action = entry["action"]
		if used_slots + action.cost_slots > slots:
			continue
		var action_work_hours := int(action.effects.get("work_hours", 0))
		if action_work_hours > 0 and planned_work_hours + action_work_hours > 20 and arrears <= 0:
			continue
		selected.append(action.id)
		used_slots += action.cost_slots
		planned_work_hours += action_work_hours
		if used_slots >= slots:
			break
	return selected

func score_action(action, state: Dictionary) -> float:
	var score: float = _weighted_effect_score(action.effects)
	var flags: Dictionary = state.get("flags", {})
	var work_hours := int(action.effects.get("work_hours", 0))
	var arrears := int(state.get("arrears_amount", 0))
	var work_income := float(EconomyRulesRef.legal_work_income_for_hours(work_hours))
	score += float(action.effects.get("career_progress", 0)) * 1.4
	score += work_income * 0.08
	score += float(action.effects.get("money", 0)) * 0.04
	score -= action.cost_energy * 0.1
	score -= action.cost_money * 0.012
	if action.tags.has("career") or action.tags.has("money"):
		score += 18.0
	if action.id == "part_time_job":
		score += 85.0
	if action.id == "mini_job_extra" and int(state.get("current_week_work_hours", 0)) <= 2:
		score += 55.0
	if action.id == "apply_howi":
		score += 52.0
	if action.id == "cv_workshop":
		score += 34.0
	if action.id == "budget_call":
		score -= 42.0
		if arrears > 0:
			score += 20.0
	if int(state.get("week", 0)) <= 0:
		if action.id == "organize_aps_documents" and not flags.has("aps_documents_ready"):
			score += 95.0
		if action.id == "aps_interview" and flags.has("aps_documents_ready"):
			score += 150.0
		if action.id == "testdaf_prep_china" and not flags.has("testdaf_passed"):
			score += 42.0
		if action.id == "testdaf_exam_china" and int(state.get("language", 0)) >= 58:
			score += 95.0
		if action.id == "review_university_courses" and int(state.get("aps_knowledge", 0)) < 45:
			score += 40.0
	if int(state.get("week", 0)) >= 1 and not flags.has("testdaf_passed"):
		if action.id == "language_school_germany":
			score += 70.0
		if action.id == "testdaf_exam_germany" and int(state.get("language", 0)) >= 58:
			score += 95.0
	if int(state.get("money", 0)) < 900 and (work_hours > 0 or action.effects.get("money", 0) > 0):
		score += 18.0
	if arrears > 0 and (work_hours > 0 or action.effects.get("money", 0) > 0 or action.id == "rent_talk_extension"):
		score += 22.0
	if int(state.get("current_week_work_hours", 0)) + work_hours > 20:
		score -= 42.0
	if int(state.get("current_week_work_hours", 0)) >= 10 and work_hours > 0:
		score -= 24.0
	if flags.has("work_law_violation") and work_hours > 0:
		score -= 30.0
	if action.id == "international_office" and (flags.has("work_limit_exceeded") or flags.has("work_law_violation")):
		score += 45.0
	if action.id == "visa_appointment" and int(state.get("week", 0)) >= 8 and not flags.has("visa_valid"):
		score += 75.0
	if action.id == "school_registration" and not flags.has("school_registered"):
		score += 70.0
	return score
