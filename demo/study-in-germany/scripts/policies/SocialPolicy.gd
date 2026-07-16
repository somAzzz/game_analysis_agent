class_name SocialPolicy
extends "res://scripts/policies/PlayerPolicy.gd"

func score_action(action, state: Dictionary) -> float:
	var score: float = _weighted_effect_score(action.effects)
	var flags: Dictionary = state.get("flags", {})
	score += float(action.effects.get("social", 0)) * 2.1
	score -= float(action.effects.get("loneliness", 0)) * 1.2
	score += float(action.effects.get("language", 0)) * 0.9
	score -= float(action.effects.get("hunger", 0)) * 0.65
	score -= action.cost_energy * 0.1
	score -= action.cost_money * 0.012
	if action.tags.has("social") or action.tags.has("family"):
		score += 24.0
	if int(state.get("week", 0)) <= 0:
		if action.id == "organize_aps_documents" and not flags.has("aps_documents_ready"):
			score += 95.0
		if action.id == "aps_interview" and flags.has("aps_documents_ready"):
			score += 145.0
		if action.id == "testdaf_prep_china" and not flags.has("testdaf_passed"):
			score += 46.0
		if action.id == "testdaf_exam_china" and int(state.get("language", 0)) >= 58:
			score += 95.0
		if action.id == "review_university_courses" and int(state.get("aps_knowledge", 0)) < 45:
			score += 38.0
	if int(state.get("week", 0)) >= 1 and not flags.has("testdaf_passed"):
		if action.id == "language_school_germany":
			score += 70.0
		if action.id == "testdaf_exam_germany" and int(state.get("language", 0)) >= 58:
			score += 95.0
	if action.tags.has("life") and int(state.get("hunger", 0)) >= 45:
		score += 12.0
	if int(state.get("loneliness", 0)) >= 60 and action.effects.get("loneliness", 0) < 0:
		score += 18.0
	if int(state.get("money", 0)) < 150 and action.cost_money > 0:
		score -= 18.0
	if action.id == "school_registration" and not flags.has("school_registered"):
		score += 80.0
	if action.id == "visa_appointment" and int(state.get("week", 0)) >= 8 and not flags.has("visa_valid"):
		score += 65.0
	return score
