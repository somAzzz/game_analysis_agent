class_name RiskEvaluator
extends RefCounted

static func get_top_risks(state: Node, limit: int = 3) -> Array[Dictionary]:
	var risks: Array[Dictionary] = []
	_add_risk(risks, _aps_risk(state))
	_add_risk(risks, _application_testdaf_risk(state))
	_add_risk(risks, _registration_risk(state))
	_add_risk(risks, _money_risk(state))
	_add_risk(risks, _academic_risk(state))
	_add_risk(risks, _stress_risk(state))
	_add_risk(risks, _hunger_risk(state))
	_add_risk(risks, _visa_risk(state))
	_add_risk(risks, _testdaf_risk(state))
	_add_risk(risks, _work_risk(state))
	risks.sort_custom(func(a, b) -> bool: return int(a["score"]) > int(b["score"]))
	return risks.slice(0, mini(limit, risks.size()))

static func _add_risk(risks: Array[Dictionary], risk: Dictionary) -> void:
	if not risk.is_empty() and int(risk.get("score", 0)) > 0:
		risks.append(risk)

static func _risk(id: String, title: String, score: int, body: String, actions: Array[String]) -> Dictionary:
	return {
		"id": id,
		"title": title,
		"score": clampi(score, 0, 100),
		"body": body,
		"suggested_actions": actions
	}

static func _aps_risk(state: Node) -> Dictionary:
	if state.week > 0 or state.flags.has("aps_passed"):
		return {}
	var score := 45
	var blockers: Array[String] = []
	if not state.flags.has("aps_documents_ready"):
		score += 18
		blockers.append("材料未齐")
	if state.aps_knowledge < 45:
		score += 18
		blockers.append("专业复习 %d/45" % state.aps_knowledge)
	if state.language < 30:
		score += 10
		blockers.append("语言表达 %d/30" % state.language)
	if state.money < 250:
		score += 12
		blockers.append("审核费用不足")
	var body := "APS 是申请季显性门槛。"
	if not blockers.is_empty():
		body += " 当前卡点：%s。" % "、".join(blockers)
	return _risk("aps", "APS 审核", score, body, ["organize_aps_documents", "review_university_courses", "aps_language_course"])

static func _application_testdaf_risk(state: Node) -> Dictionary:
	if state.week > 0 or state.flags.has("testdaf_passed"):
		return {}
	var current_label: String = state.testdaf_label()
	var score := 50
	if state.language < 45:
		score += 12
	if state.language >= 55:
		score += 8
	return _risk("testdaf_application", "出国前 TestDaF", score, "当前 TestDaF %s。出国前没过 4x4，德国读语言和重考会显著增加生活成本。" % current_label, ["testdaf_prep_china", "testdaf_exam_china"])

static func _registration_risk(state: Node) -> Dictionary:
	if state.week <= 0 or state.flags.has("school_registered"):
		return {}
	if state.week <= 6:
		var weeks_left: int = maxi(0, 6 - state.week)
		var score: int = 45 + state.week * 7
		if not state.flags.has("testdaf_passed"):
			score += 25
		return _risk("registration", "学校注册窗口", score, "还剩 %d 周。没有 TestDaF 4x4 或注册材料，本学期会被拖后。" % weeks_left, ["school_registration", "insurance_paperwork", "testdaf_exam_germany"])
	return _risk("registration_delayed", "注册已延期", 82, "正常注册窗口已错过，只能准备下学期注册并控制生活成本。", ["next_semester_registration", "international_office"])

static func _money_risk(state: Node) -> Dictionary:
	if state.money >= 900 and state.arrears_amount <= 0:
		return {}
	var score: int = 40
	if state.money < 500:
		score = 58
	if state.arrears_amount > 0 or state.cash_shortfall_count > 0:
		score = 78
	if state.arrears_amount >= 1000 or state.flags.has("cashflow_crisis"):
		score = 96
	var actions: Array[String] = ["rent_talk_extension", "budget_call", "part_time_job", "sell_unused_stuff", "cook_at_home"]
	if state.week <= 0:
		actions = ["aps_part_time_job", "organize_aps_documents", "review_university_courses"]
	return _risk("money", "现金流", score, "当前可支配现金 %d EUR，逾期 %d EUR。逾期会推高压力和饥饿，并诱发黑工选择。" % [state.money, state.arrears_amount], actions)

static func _academic_risk(state: Node) -> Dictionary:
	if state.week < 8 or (state.academic_progress >= 45 and state.exam_readiness >= 45):
		return {}
	var weakest: int = mini(state.academic_progress, state.exam_readiness)
	var score: int = 45 + (45 - weakest)
	if state.week >= 16:
		score += 15
	return _risk("academic", "学业/考试", score, "学业进度 %d，备考 %d。考试周越近，补掌握度的成本越高。" % [state.academic_progress, state.exam_readiness], ["attend_lecture", "problem_set", "office_hour"])

static func _stress_risk(state: Node) -> Dictionary:
	if state.stress < 60:
		return {}
	var score: int = state.stress
	return _risk("stress", "压力", score, "压力 %d。高压会拖累学业和考试，并可能覆盖普通成功结局。" % state.stress, ["take_a_real_break", "therapy", "sleep_recover", "go_running"])

static func _hunger_risk(state: Node) -> Dictionary:
	if state.hunger < 65:
		return {}
	var score: int = state.hunger
	return _risk("hunger", "饥饿/生活", score, "饥饿 %d。吃饭问题会持续扣精力、加压力、拖学业。" % state.hunger, ["cook_at_home", "cheap_noodle_week", "mensa_coupon", "classmate_meal", "wg_dinner"])

static func _visa_risk(state: Node) -> Dictionary:
	if state.week < 10 or state.flags.has("visa_valid"):
		return {}
	var score: int = 55
	if state.week >= 14:
		score = 82
	if state.visa_progress < 45:
		score += 10
	return _risk("visa", "居留许可", score, "居留状态还没确认。Termin、材料和学校支持要尽快接上。", ["emergency_international_office", "write_formal_email_to_abh", "visa_appointment", "international_office"])

static func _testdaf_risk(state: Node) -> Dictionary:
	if state.week <= 0 or state.flags.has("testdaf_passed"):
		return {}
	var score: int = 70
	if state.week >= 4:
		score += 12
	return _risk("testdaf", "TestDaF 4x4", score, "当前 TestDaF %s。没过 4x4 会卡注册并增加语言班成本。" % state.testdaf_label(), ["language_school_germany", "testdaf_exam_germany"])

static func _work_risk(state: Node) -> Dictionary:
	if state.current_week_work_hours <= state.LEGAL_WEEKLY_WORK_HOURS and not state.flags.has("work_limit_exceeded"):
		return {}
	var score: int = 55
	if state.current_week_work_hours > state.LEGAL_WEEKLY_WORK_HOURS:
		score = 85
	if state.flags.has("work_law_violation"):
		score = 96
	return _risk("work", "打工合规", score, "本周合法工时 %d 小时。超过 20 小时会进入合规和居留解释风险。" % state.current_week_work_hours, ["international_office", "write_formal_email_to_abh", "apply_howi"])
