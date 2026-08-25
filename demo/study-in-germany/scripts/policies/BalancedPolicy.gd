class_name BalancedPolicy
extends "res://scripts/policies/PlayerPolicy.gd"

const EconomyRulesRef := preload("res://scripts/simulation/EconomyRules.gd")

func score_action(action, state: Dictionary) -> float:
	var score: float = _weighted_effect_score(action.effects)
	var flags: Dictionary = state.get("flags", {})
	var gpa := int(state.get("gpa_score", 65))
	var low_gpa_work_route := gpa <= 60
	var stable_route := gpa > 60 and gpa <= 65
	var social_route := gpa > 65 and gpa <= 72
	var career_route := gpa > 72
	var arrears := int(state.get("arrears_amount", 0))
	var estimated_work_income: float = float(EconomyRulesRef.legal_work_income_for_hours(int(action.effects.get("work_hours", 0))))
	score -= action.cost_energy * 0.12
	score -= action.cost_money * 0.01
	score += estimated_work_income * 0.03
	if int(state.get("stress", 0)) >= 65 and action.effects.get("stress", 0) < 0:
		score += 12.0
	if action.id == "sleep_recover" and int(state.get("stress", 0)) < 60:
		score -= 8.0
	if action.id == "sleep_recover" and int(state.get("energy", 0)) > 45:
		score -= 6.0
	if action.id == "sleep_recover" and arrears > 0:
		score -= 5.0
	if action.id == "sleep_recover" and arrears > 500:
		score -= 6.0
	if action.id == "sleep_recover" and int(state.get("hunger", 0)) > 75:
		score -= 6.0
	if action.id == "go_running" and int(state.get("hunger", 0)) > 70:
		score -= 14.0
	if action.id == "go_running" and arrears > 0:
		score -= 5.0
	if action.id == "go_running" and int(state.get("stress", 0)) < 55 and int(state.get("energy", 0)) > 40:
		score -= 18.0
	if action.id == "bilibili_rest" and int(state.get("stress", 0)) < 55 and int(state.get("energy", 0)) > 45:
		score -= 8.0
	if action.id == "library_day" and int(state.get("academic_progress", 0)) >= 75 and int(state.get("exam_readiness", 0)) >= 70:
		score -= 20.0
	if action.id == "problem_set" and int(state.get("academic_progress", 0)) >= 80 and int(state.get("exam_readiness", 0)) >= 78:
		score -= 12.0
	if action.id == "write_hausarbeit" and int(state.get("academic_progress", 0)) >= 85 and int(state.get("exam_readiness", 0)) >= 80:
		score -= 8.0
	if action.id == "office_hour" and int(state.get("academic_progress", 0)) >= 60 and int(state.get("exam_readiness", 0)) >= 60:
		score -= 10.0
	if action.id == "office_hour" and arrears > 0 and int(state.get("hunger", 0)) > 70:
		score -= 8.0
	if int(state.get("energy", 0)) <= 35 and action.effects.get("energy", 0) > 0:
		score += 10.0
	if int(state.get("hunger", 0)) >= 65 and action.effects.get("hunger", 0) < 0:
		score += 10.0
	if int(state.get("hunger", 0)) <= 30 and action.effects.get("hunger", 0) < 0:
		score -= 14.0
	if int(state.get("money", 0)) < 100 and (action.id == "classmate_meal" or action.id == "wg_dinner"):
		score -= 10.0
	if arrears > 0 and (action.id == "classmate_meal" or action.id == "wg_dinner"):
		score -= 10.0
	if action.id == "school_registration" and not flags.has("school_registered"):
		score += 85.0
	if action.id == "next_semester_registration" and not flags.has("school_registered"):
		score += 80.0
	if int(state.get("current_week_work_hours", 0)) >= 10 and action.effects.get("work_hours", 0) > 0:
		score -= 16.0
	if int(state.get("current_week_work_hours", 0)) >= 18 and action.effects.get("work_hours", 0) > 0:
		score -= 32.0
	if int(state.get("stress", 0)) >= 90 and int(state.get("hunger", 0)) >= 90 and action.effects.get("work_hours", 0) > 0:
		score -= 18.0
	if int(state.get("stress", 0)) >= 90 and int(state.get("hunger", 0)) >= 90 and action.id == "bilibili_rest":
		score -= 20.0
	if action.id == "visa_appointment" and int(state.get("week", 0)) >= 8 and not flags.has("visa_valid"):
		score += 75.0
	if int(state.get("week", 0)) <= 0:
		if action.id == "aps_interview":
			score += 100.0
		if action.id == "organize_aps_documents" and not flags.has("aps_documents_ready"):
			score += 70.0
		if int(state.get("language", 0)) < 30 and action.id == "aps_language_course":
			score += 45.0
		if not flags.has("testdaf_passed") and action.id == "testdaf_prep_china":
			score += 62.0
		if not flags.has("testdaf_passed") and int(state.get("language", 0)) >= 58 and action.id == "testdaf_exam_china":
			score += 88.0
		if int(state.get("aps_knowledge", 0)) < 45 and action.id == "review_university_courses":
			score += 50.0
		if int(state.get("money", 0)) < 450 and action.id == "aps_part_time_job":
			score += 50.0
	if int(state.get("week", 0)) >= 1 and not flags.has("testdaf_passed"):
		if action.id == "language_school_germany":
			score += 80.0
		if int(state.get("language", 0)) >= 60 and action.id == "testdaf_exam_germany":
			score += 92.0
		if int(state.get("money", 0)) < 500 and action.id == "language_school_germany":
			score -= 26.0
		if arrears > 0 and action.id == "language_school_germany":
			score -= 34.0
		if int(state.get("money", 0)) < 360 and action.id == "testdaf_exam_germany":
			score -= 20.0
	if int(state.get("visa_progress", 0)) < 50 and action.effects.has("visa_progress"):
		score += 8.0
	if int(state.get("academic_progress", 0)) < 55 and action.effects.has("academic_progress"):
		score += 6.0
	if int(state.get("week", 0)) >= 8 and int(state.get("exam_readiness", 0)) < 55 and action.effects.get("exam_readiness", 0) > 0:
		score += 16.0
	if int(state.get("week", 0)) >= 15 and int(state.get("exam_readiness", 0)) < 70 and action.effects.get("exam_readiness", 0) > 0:
		score += 12.0
	if int(state.get("failed_courses", 0)) > 0 and action.effects.get("exam_readiness", 0) > 0:
		score += 18.0
	if low_gpa_work_route and int(state.get("week", 0)) >= 6:
		if action.id == "part_time_job":
			score += 70.0
		if action.id == "mini_job_extra" and int(state.get("current_week_work_hours", 0)) <= 2:
			score += 28.0
		if action.id == "cv_workshop":
			score += 22.0
		if action.id == "apply_howi":
			score += 28.0
		if action.id == "budget_call":
			score -= 18.0
		if ["library_day", "problem_set", "write_hausarbeit", "language_tandem", "student_club", "date_night"].has(action.id):
			score -= 16.0
	if stable_route and int(state.get("week", 0)) >= 8:
		if ["language_tandem", "student_club", "date_night", "cv_workshop", "apply_howi"].has(action.id):
			score -= 10.0
		if ["international_office", "office_hour", "cook_at_home"].has(action.id):
			score += 8.0
	if social_route and int(state.get("week", 0)) >= 8 and int(state.get("social", 0)) < 72:
		if action.id == "language_tandem":
			score += 18.0
		if action.id == "student_club":
			score += 16.0
		if action.id == "group_project":
			score += 10.0
		if action.id == "date_night":
			score += 8.0
	if career_route and int(state.get("week", 0)) >= 9 and int(state.get("career_progress", 0)) < 75:
		if action.id == "cv_workshop":
			score += 24.0
		if action.id == "apply_howi":
			score += 20.0
		if action.id == "scholarship":
			score += 8.0
	if not career_route and int(state.get("week", 0)) >= 9 and ["cv_workshop", "apply_howi"].has(action.id):
		score -= 8.0
	if int(state.get("week", 0)) >= 7 and int(state.get("visa_progress", 0)) < 55:
		if action.id == "international_office":
			score += 14.0
		if action.id == "visa_appointment":
			score += 18.0
	if int(state.get("money", 0)) < 900 and (action.effects.get("money", 0) > 0 or estimated_work_income > 0.0):
		score += 8.0
	if arrears > 0 and (action.effects.get("money", 0) > 0 or estimated_work_income > 0.0 or action.id == "rent_talk_extension"):
		score += 24.0
	if flags.has("family_support_low") and action.id == "budget_call":
		score -= 28.0
	if arrears > 0 and action.id == "cook_at_home":
		score -= 4.0
	if arrears > 0 and action.cost_money > 0:
		score -= 10.0
	return score
