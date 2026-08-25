class_name EndingDef
extends Resource

@export var id: String = ""
@export var title: String = ""
@export_multiline var description: String = ""
@export var priority: int = 0
@export var conditions: Dictionary = {}

func matches(state: Node) -> bool:
	for key in conditions.keys():
		var value = conditions[key]
		if key == "max_stress" and state.stress > int(value):
			return false
		if key == "min_stress" and state.stress < int(value):
			return false
		if key == "max_loneliness" and state.loneliness > int(value):
			return false
		if key == "min_loneliness" and state.loneliness < int(value):
			return false
		if key == "max_hunger" and state.hunger > int(value):
			return false
		if key == "min_hunger" and state.hunger < int(value):
			return false
		if key == "max_energy" and state.energy > int(value):
			return false
		if key == "min_energy" and state.energy < int(value):
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
		if key == "max_failed_courses" and state.failed_courses > int(value):
			return false
		if key == "min_failed_courses" and state.failed_courses < int(value):
			return false
		if key == "max_arrears" and state.arrears_amount > int(value):
			return false
		if key == "min_arrears" and state.arrears_amount < int(value):
			return false
		if key == "max_cash_shortfall_count" and state.cash_shortfall_count > int(value):
			return false
		if key == "min_cash_shortfall_count" and state.cash_shortfall_count < int(value):
			return false
		if key == "max_parent_pressure" and state.parent_pressure > int(value):
			return false
		if key == "min_parent_pressure" and state.parent_pressure < int(value):
			return false
		if key == "max_reciprocity_debt" and state.reciprocity_debt > int(value):
			return false
		if key == "min_reciprocity_debt" and state.reciprocity_debt < int(value):
			return false
		if key == "min_money" and state.money < int(value):
			return false
		if key == "max_money" and state.money > int(value):
			return false
		if key == "min_language" and state.language < int(value):
			return false
		if key == "min_social" and state.social < int(value):
			return false
		if key == "min_career" and state.career_progress < int(value):
			return false
		if key == "max_career" and state.career_progress > int(value):
			return false
		if key == "min_annual_work_half_days" and state.annual_work_half_days < int(value):
			return false
		if key == "max_annual_work_half_days" and state.annual_work_half_days > int(value):
			return false
		if key == "flag" and not state.flags.has(str(value)):
			return false
		if key == "missing_flag" and state.flags.has(str(value)):
			return false
		if key == "flags":
			for flag_name in value:
				if not state.flags.has(str(flag_name)):
					return false
		if key == "missing_flags":
			for flag_name in value:
				if state.flags.has(str(flag_name)):
					return false
	return true
