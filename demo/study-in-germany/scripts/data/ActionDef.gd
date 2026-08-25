class_name ActionDef
extends Resource

@export var id: String = ""
@export var name: String = ""
@export_multiline var description: String = ""
@export var cost_energy: int = 0
@export var cost_money: int = 0
@export var cost_slots: int = 1
@export var effects: Dictionary = {}
@export var requirements: Dictionary = {}
@export var tags: Array = []
@export var risk_tags: Array = []
@export var set_flag: String = ""
@export var cooldown_group: String = ""
@export var max_per_week: int = 0
@export var diminishing_window: int = 0
@export var diminishing_factor: float = 1.0

func can_use(state: Node) -> bool:
	if state.week <= 0 and not tags.has("application"):
		return false
	if state.week >= 1 and tags.has("application"):
		return false
	for key in requirements.keys():
		var value = requirements[key]
		if key == "min_week" and state.week < int(value):
			return false
		if key == "max_week" and state.week > int(value):
			return false
		if key == "min_money" and state.money < int(value):
			return false
		if key == "max_parent_pressure" and state.parent_pressure > int(value):
			return false
		if key == "min_social" and state.social < int(value):
			return false
		if key == "max_reciprocity_debt" and state.reciprocity_debt > int(value):
			return false
		if key == "max_energy" and state.energy > int(value):
			return false
		if key == "min_energy" and state.energy < int(value):
			return false
		if key == "min_stress" and state.stress < int(value):
			return false
		if key == "max_hunger" and state.hunger > int(value):
			return false
		if key == "min_hunger" and state.hunger < int(value):
			return false
		if key == "min_language" and state.language < int(value):
			return false
		if key == "min_gpa_score" and state.gpa_score < int(value):
			return false
		if key == "min_aps_knowledge" and state.aps_knowledge < int(value):
			return false
		if key == "min_aps_score" and state.aps_score < int(value):
			return false
		if key == "flag" and not state.flags.has(str(value)):
			return false
		if key == "missing_flag" and state.flags.has(str(value)):
			return false
	if cost_money > 0 and not allows_cash_shortfall() and not state.can_afford(cost_money):
		return false
	if max_per_week > 0 and state.get_weekly_action_count(id) >= max_per_week:
		return false
	if cooldown_group != "" and max_per_week > 0 and state.get_weekly_group_count(cooldown_group) >= max_per_week:
		return false
	return true

func disabled_reason(state: Node) -> String:
	if can_use(state):
		return ""
	if state.week <= 0 and not tags.has("application"):
		return "申请季不可用"
	if state.week >= 1 and tags.has("application"):
		return "申请季已结束"
	for key in requirements.keys():
		var value = requirements[key]
		if key == "min_week" and state.week < int(value):
			return "第 %s 周后可用" % value
		if key == "max_week" and state.week > int(value):
			return "当前阶段已错过"
		if key == "min_money" and state.money < int(value):
			return "钱不够"
		if key == "max_parent_pressure" and state.parent_pressure > int(value):
			return "家庭压力太高"
		if key == "min_social" and state.social < int(value):
			return "社交基础不足"
		if key == "max_reciprocity_debt" and state.reciprocity_debt > int(value):
			return "人情债太高"
		if key == "max_energy" and state.energy > int(value):
			return "精力已足够"
		if key == "min_energy" and state.energy < int(value):
			return "精力不足"
		if key == "min_stress" and state.stress < int(value):
			return "压力还不高"
		if key == "max_hunger" and state.hunger > int(value):
			return "饥饿太高"
		if key == "min_hunger" and state.hunger < int(value):
			return "还不饿"
		if key == "min_language" and state.language < int(value):
			return "德语不足"
		if key == "min_gpa_score" and state.gpa_score < int(value):
			return "大学成绩不足"
		if key == "min_aps_knowledge" and state.aps_knowledge < int(value):
			return "专业复习不足"
		if key == "min_aps_score" and state.aps_score < int(value):
			return "APS 分数不足"
		if key == "flag" and not state.flags.has(str(value)):
			return "需要前置事件"
		if key == "missing_flag" and state.flags.has(str(value)):
			return "已完成"
	if cost_money > 0 and not allows_cash_shortfall() and not state.can_afford(cost_money):
		return "钱不够"
	if max_per_week > 0 and state.get_weekly_action_count(id) >= max_per_week:
		return "本周已用"
	if cooldown_group != "" and max_per_week > 0 and state.get_weekly_group_count(cooldown_group) >= max_per_week:
		return "同类行动本周已满"
	return "条件不足"

func allows_cash_shortfall() -> bool:
	return bool(requirements.get("allow_arrears", false)) or bool(requirements.get("allow_debt", false)) or tags.has("arrears") or tags.has("debt")
