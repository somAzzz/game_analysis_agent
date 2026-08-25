class_name StudyPolicy
extends "res://scripts/policies/PlayerPolicy.gd"

func score_action(action, state: Dictionary) -> float:
	var score: float = _weighted_effect_score(action.effects)
	score += float(action.effects.get("academic_progress", 0)) * 2.1
	score += float(action.effects.get("exam_readiness", 0)) * 1.4
	score += float(action.effects.get("language", 0)) * 0.8
	score -= action.cost_energy * 0.08
	score -= action.cost_money * 0.008
	var flags: Dictionary = state.get("flags", {})
	if int(state.get("week", 0)) <= 0:
		if action.id == "organize_aps_documents" and not flags.has("aps_documents_ready"):
			score += 90.0
		if action.id == "aps_interview" and flags.has("aps_documents_ready"):
			score += 110.0
		if action.id == "testdaf_prep_china" and not flags.has("testdaf_passed"):
			score += 55.0
		if action.id == "testdaf_exam_china" and int(state.get("language", 0)) >= 58:
			score += 80.0
		if action.id == "review_university_courses" and int(state.get("aps_knowledge", 0)) < 55:
			score += 45.0
	if int(state.get("week", 0)) >= 1 and not flags.has("school_registered"):
		if action.id == "school_registration":
			score += 95.0
		if action.id == "language_school_germany" and not flags.has("testdaf_passed"):
			score += 75.0
		if action.id == "testdaf_exam_germany" and int(state.get("language", 0)) >= 58:
			score += 90.0
	if int(state.get("stress", 0)) >= 78 and action.effects.get("stress", 0) < 0:
		score += 10.0
	if int(state.get("visa_progress", 0)) < 35 and action.effects.has("visa_progress"):
		score += 4.0
	return score
