class_name SlackerPolicy
extends "res://scripts/policies/PlayerPolicy.gd"

func score_action(action, state: Dictionary) -> float:
	var score: float = 0.0
	score += float(action.effects.get("energy", 0)) * 1.5
	score -= float(action.effects.get("stress", 0)) * 1.6
	score -= float(action.effects.get("loneliness", 0)) * 0.7
	score -= float(action.effects.get("hunger", 0)) * 0.8
	score -= action.cost_energy * 0.05
	score -= action.cost_money * 0.018
	if action.tags.has("mental") or action.tags.has("life"):
		score += 28.0
	if action.id == "sleep_recover" or action.id == "bilibili_rest" or action.id == "cook_at_home":
		score += 35.0
	if int(state.get("stress", 0)) >= 65 and action.effects.get("stress", 0) < 0:
		score += 18.0
	if int(state.get("hunger", 0)) >= 60 and action.effects.get("hunger", 0) < 0:
		score += 16.0
	if action.tags.has("study") or action.tags.has("exam") or action.tags.has("admin") or action.tags.has("application"):
		score -= 18.0
	if int(state.get("week", 0)) <= 0 and action.id == "aps_interview":
		score += 80.0
	if int(state.get("week", 0)) >= 1 and action.id == "school_registration" and not state.get("flags", {}).has("school_registered"):
		score += 55.0
	if int(state.get("week", 0)) >= 8 and action.id == "visa_appointment" and not state.get("flags", {}).has("visa_valid"):
		score += 55.0
	return score
