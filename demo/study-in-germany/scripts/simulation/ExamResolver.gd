class_name ExamResolver
extends RefCounted

static func resolve_exam(state: Node) -> Dictionary:
	var stress_modifier: float = -max(0, state.stress - 55) * 0.35
	var energy_modifier: float = (state.energy - 50) * 0.08
	var language_modifier: float = state.language * 0.10
	var raw_score: float = state.academic_progress * 0.35 + state.exam_readiness * 0.40 + language_modifier + energy_modifier + stress_modifier + _rand_float_range(-8.0, 8.0)
	raw_score = clampf(raw_score, 0.0, 100.0)
	var grade: float = _score_to_grade(raw_score)
	var passed := grade < 5.0
	var result: Dictionary = {
		"score": roundi(raw_score),
		"grade": grade,
		"passed": passed,
		"summary": _grade_summary(grade),
		"academic_progress": state.academic_progress,
		"exam_readiness": state.exam_readiness,
		"stress": state.stress,
		"energy": state.energy,
		"failed_courses": state.failed_courses
	}
	state.last_exam_result = result
	if not passed:
		state.failed_courses += 1
		state.set_flag("needs_retake")
		state.apply_effects({"stress": 15, "exam_readiness": -10})
		result["failed_courses"] = state.failed_courses
		state.last_exam_result = result
		state.add_log("Klausur 未通过：需要补考/重修，压力上升，备考信心下降。")
	else:
		state.apply_effects({"stress": -4})
		result["stress_after"] = state.stress
		state.last_exam_result = result
		state.add_log("Klausur 通过：成绩 %s，第一学期最硬的一关落地。" % grade)
	return result

static func _score_to_grade(score: float) -> float:
	if score >= 92:
		return 1.0
	if score >= 86:
		return 1.3
	if score >= 80:
		return 1.7
	if score >= 74:
		return 2.0
	if score >= 68:
		return 2.3
	if score >= 61:
		return 2.7
	if score >= 54:
		return 3.0
	if score >= 48:
		return 3.3
	if score >= 42:
		return 3.7
	if score >= 36:
		return 4.0
	return 5.0

static func _grade_summary(grade: float) -> String:
	if grade <= 1.3:
		return "Sehr gut"
	if grade <= 2.3:
		return "Gut"
	if grade <= 3.3:
		return "Befriedigend"
	if grade <= 4.0:
		return "Ausreichend"
	return "Nicht bestanden"

static func _rand_float_range(min_value: float, max_value: float) -> float:
	var main_loop = Engine.get_main_loop()
	if main_loop is SceneTree and main_loop.root.has_node("/root/RandomService"):
		return main_loop.root.get_node("/root/RandomService").rand_float_range(min_value, max_value)
	return randf_range(min_value, max_value)
