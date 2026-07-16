class_name AdminPolicy
extends "res://scripts/policies/PlayerPolicy.gd"

func score_action(action, state: Dictionary) -> float:
	var score: float = _weighted_effect_score(action.effects)
	var flags: Dictionary = state.get("flags", {})
	score += float(action.effects.get("visa_progress", 0)) * 2.0
	score += float(action.effects.get("language", 0)) * 0.6
	score -= action.cost_energy * 0.1
	score -= action.cost_money * 0.008
	if action.tags.has("admin") or action.tags.has("support") or action.tags.has("application"):
		score += 24.0
	if int(state.get("week", 0)) <= 0:
		if action.id == "organize_aps_documents" and not flags.has("aps_documents_ready"):
			score += 95.0
		if action.id == "aps_interview" and flags.has("aps_documents_ready"):
			score += 100.0
		if action.id == "testdaf_prep_china" and not flags.has("testdaf_passed"):
			score += 45.0
		if action.id == "testdaf_exam_china" and int(state.get("language", 0)) >= 58:
			score += 95.0
	if int(state.get("week", 0)) >= 1:
		if action.id == "bank_account":
			score += 45.0
		if action.id == "insurance_paperwork":
			score += 50.0
		if action.id == "school_registration" and not flags.has("school_registered"):
			score += 110.0
		if action.id == "next_semester_registration" and not flags.has("school_registered"):
			score += 90.0
		if action.id == "anmeldung":
			score += 55.0
		if action.id == "visa_appointment" and not flags.has("visa_valid"):
			score += 105.0
		if action.id == "international_office" and int(state.get("visa_progress", 0)) < 60:
			score += 38.0
		if action.id == "language_school_germany" and not flags.has("testdaf_passed") and int(state.get("language", 0)) < 65:
			score += 55.0
		if action.id == "testdaf_exam_germany" and not flags.has("testdaf_passed") and int(state.get("language", 0)) >= 58:
			score += 105.0
		if action.id == "language_school_germany" and int(state.get("language", 0)) >= 70:
			score -= 35.0
	if int(state.get("money", 0)) < 600:
		if action.id == "budget_call":
			score += 45.0
		if action.id == "scholarship":
			score += 24.0
		if action.id == "part_time_job" and int(state.get("week", 0)) >= 6:
			score += 26.0
	if int(state.get("arrears_amount", 0)) > 0:
		if action.id == "budget_call":
			score += 50.0
		if action.cost_money > 0:
			score -= 24.0
	if int(state.get("stress", 0)) >= 85 and action.effects.get("stress", 0) < 0:
		score += 14.0
	return score
