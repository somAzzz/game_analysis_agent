class_name EventDef
extends Resource

@export var id: String = ""
@export var title: String = ""
@export_multiline var body: String = ""
@export_enum("fixed", "conditional", "random") var event_type: String = "random"
@export var trigger: Dictionary = {}
@export var weight: float = 1.0
@export var repeatable: bool = false
@export var source_order: int = 0
@export var choices: Array = []

func can_trigger(state: Node) -> bool:
	if not repeatable and state.completed_events.has(id):
		return false
	for key in trigger.keys():
		var value = trigger[key]
		if key == "week" and state.week != int(value):
			return false
		if key == "min_week" and state.week < int(value):
			return false
		if key == "max_week" and state.week > int(value):
			return false
		if key == "min_stress" and state.stress < int(value):
			return false
		if key == "max_stress" and state.stress > int(value):
			return false
		if key == "min_loneliness" and state.loneliness < int(value):
			return false
		if key == "min_hunger" and state.hunger < int(value):
			return false
		if key == "max_hunger" and state.hunger > int(value):
			return false
		if key == "max_money" and state.money > int(value):
			return false
		if key == "min_money" and state.money < int(value):
			return false
		if key == "max_visa" and state.visa_progress > int(value):
			return false
		if key == "min_visa" and state.visa_progress < int(value):
			return false
		if key == "max_academic" and state.academic_progress > int(value):
			return false
		if key == "min_academic" and state.academic_progress < int(value):
			return false
		if key == "max_exam_readiness" and state.exam_readiness > int(value):
			return false
		if key == "min_exam_readiness" and state.exam_readiness < int(value):
			return false
		if key == "min_language" and state.language < int(value):
			return false
		if key == "min_gpa_score" and state.gpa_score < int(value):
			return false
		if key == "min_aps_knowledge" and state.aps_knowledge < int(value):
			return false
		if key == "min_aps_score" and state.aps_score < int(value):
			return false
		if key == "max_aps_score" and state.aps_score > int(value):
			return false
		if key == "min_social" and state.social < int(value):
			return false
		if key == "min_current_week_work_hours" and state.current_week_work_hours < int(value):
			return false
		if key == "min_annual_work_half_days" and state.annual_work_half_days < int(value):
			return false
		if key == "min_failed_courses" and state.failed_courses < int(value):
			return false
		if key == "max_failed_courses" and state.failed_courses > int(value):
			return false
		if key == "flag" and not state.flags.has(str(value)):
			return false
		if key == "missing_flag" and state.flags.has(str(value)):
			return false
		if key == "missing_flags":
			for flag_name in value:
				if state.flags.has(str(flag_name)):
					return false
		if key == "difficulty" and str(value) != state.difficulty:
			return false
		if key == "difficulties" and not value.has(state.difficulty):
			return false
		if key == "min_difficulty" and _difficulty_rank(state.difficulty) < _difficulty_rank(str(value)):
			return false
		if key == "max_difficulty" and _difficulty_rank(state.difficulty) > _difficulty_rank(str(value)):
			return false
	return true

func _difficulty_rank(value: String) -> int:
	match value:
		"easy":
			return 0
		"normal":
			return 1
		"hard":
			return 2
		"realistic":
			return 3
	return 1
