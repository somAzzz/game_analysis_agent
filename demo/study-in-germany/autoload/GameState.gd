extends Node

signal state_changed

const EconomyRulesRef := preload("res://scripts/simulation/EconomyRules.gd")
const MAX_STAT := 100
const CONTENT_VERSION := "dev-hardcoded-0.1.0"
const RULES_VERSION := "sim-0.2.0"
const BLOCKED_ACCOUNT_REQUIRED_2026 := 11904
const BLOCKED_ACCOUNT_MONTHLY_RELEASE_2026 := 992
const HEALTH_INSURANCE_MONTHLY_ESTIMATE_2026 := 145
const MONTHLY_RENT_ESTIMATE_2026 := 620
const LEGAL_WEEKLY_WORK_HOURS := EconomyRulesRef.LEGAL_WEEKLY_WORK_HOURS
const LEGAL_ANNUAL_HALF_DAYS := EconomyRulesRef.LEGAL_ANNUAL_HALF_DAYS
const LEGAL_WORK_HOURLY_WAGE_2026 := EconomyRulesRef.LEGAL_WORK_HOURLY_WAGE_2026
const ILLEGAL_CASH_WORK_WAGE_RATIO := EconomyRulesRef.ILLEGAL_CASH_WORK_WAGE_RATIO
const GERMANY_MINIMUM_WAGE_2026 := EconomyRulesRef.GERMANY_MINIMUM_WAGE_2026
const ILLEGAL_CASH_WORK_WAGE := EconomyRulesRef.ILLEGAL_CASH_WORK_WAGE

var run_id: int = 0
var seed: int = 0
var content_version: String = CONTENT_VERSION
var rules_version: String = RULES_VERSION
var policy_name: String = ""
var difficulty: String = "normal"
var week: int = -8
var semester: int = 1
var city: String = "Berlin"
var background: String = "ordinary"

var money: int = 500
var blocked_account_balance: int = BLOCKED_ACCOUNT_REQUIRED_2026
var energy: int = 100
var stress: int = 20
var loneliness: int = 30
var hunger: int = 25
var academic_progress: int = 10
var exam_readiness: int = 10
var language: int = 20
var social: int = 15
var visa_progress: int = 15
var career_progress: int = 0
var gpa_score: int = 65
var aps_knowledge: int = 25
var aps_score: int = 0
var university_tier: String = "未定位"
var testdaf_reading: int = 0
var testdaf_listening: int = 0
var testdaf_writing: int = 0
var testdaf_speaking: int = 0
var current_week_work_hours: int = 0
var annual_work_half_days: int = 0
var failed_courses: int = 0
var cash_shortfall_count: int = 0
var arrears_amount: int = 0
var parent_pressure: int = 0
var reciprocity_debt: int = 0
var weekly_paid_social_actions: int = 0
var weekly_free_social_actions: int = 0
var unpaid_social_streak: int = 0
var no_social_streak: int = 0

var flags: Dictionary = {}
var relationships: Dictionary = {}
var completed_events: Array[String] = []
var action_history: Array[Dictionary] = []
var weekly_snapshots: Array[Dictionary] = []
var weekly_action_counts: Dictionary = {}
var weekly_group_counts: Dictionary = {}
var event_log: Array[String] = []
var last_exam_result: Dictionary = {}
var last_ending_id: String = ""

func _ready() -> void:
	reset()

func reset() -> void:
	run_id = 0
	seed = 0
	content_version = CONTENT_VERSION
	rules_version = RULES_VERSION
	policy_name = ""
	difficulty = "normal"
	week = -8
	semester = 1
	city = "Berlin"
	background = "ordinary"
	money = 3500
	blocked_account_balance = BLOCKED_ACCOUNT_REQUIRED_2026
	energy = 100
	stress = 20
	loneliness = 30
	hunger = 25
	academic_progress = 10
	exam_readiness = 10
	language = 20
	social = 15
	visa_progress = 15
	career_progress = 0
	gpa_score = 65
	aps_knowledge = 25
	aps_score = 0
	university_tier = "未定位"
	testdaf_reading = 0
	testdaf_listening = 0
	testdaf_writing = 0
	testdaf_speaking = 0
	current_week_work_hours = 0
	annual_work_half_days = 0
	failed_courses = 0
	cash_shortfall_count = 0
	arrears_amount = 0
	parent_pressure = 0
	reciprocity_debt = 0
	weekly_paid_social_actions = 0
	weekly_free_social_actions = 0
	unpaid_social_streak = 0
	no_social_streak = 0
	flags = {}
	relationships = {}
	completed_events = []
	action_history = []
	weekly_snapshots = []
	weekly_action_counts = {}
	weekly_group_counts = {}
	event_log = []
	last_exam_result = {}
	last_ending_id = ""
	if has_node("/root/DataRegistry"):
		for character in DataRegistry.characters:
			relationships[character.id] = character.starting_relationship.duplicate(true)
	emit_changed()

func configure_run(config: Dictionary) -> void:
	run_id = int(config.get("run_id", run_id))
	seed = int(config.get("seed", seed))
	content_version = str(config.get("content_version", CONTENT_VERSION))
	rules_version = str(config.get("rules_version", RULES_VERSION))
	policy_name = str(config.get("policy", policy_name))
	difficulty = _normalize_difficulty(str(config.get("difficulty", difficulty)))
	if seed != 0 and has_node("/root/RandomService"):
		RandomService.set_seed(seed)
	randomize_initial_profile()
	emit_changed()

func randomize_initial_profile() -> void:
	var profile: Dictionary = _difficulty_initial_profile()
	money = _rand_range(profile.get("money", [2500, 7500]))
	gpa_score = _rand_range(profile.get("gpa_score", [58, 82]))
	language = _rand_range(profile.get("language", [20, 45]))
	_estimate_initial_testdaf()
	aps_knowledge = _rand_range(profile.get("aps_knowledge", [25, 45]))
	academic_progress = clampi(int(roundi(float(gpa_score) * 0.25)), 8, 25)
	exam_readiness = clampi(int(roundi(float(gpa_score) * 0.18)), 6, 20)
	stress = _rand_range(profile.get("stress", [18, 35]))
	loneliness = _rand_range(profile.get("loneliness", [20, 38]))
	hunger = _rand_range(profile.get("hunger", [15, 35]))
	social = _rand_range(profile.get("social", [10, 25]))
	visa_progress = 8
	aps_score = 0
	university_tier = "未定位"
	flags.erase("aps_passed")
	flags.erase("testdaf_passed")

func _estimate_initial_testdaf() -> void:
	testdaf_reading = _testdaf_level_from_language(language + _rand_range([-8, 8]))
	testdaf_listening = _testdaf_level_from_language(language + _rand_range([-10, 6]))
	testdaf_writing = _testdaf_level_from_language(language + _rand_range([-7, 7]))
	testdaf_speaking = _testdaf_level_from_language(language + _rand_range([-9, 9]))
	if has_testdaf_4x4():
		set_flag("testdaf_passed")

func _rand_range(range_value) -> int:
	if range_value is Array and range_value.size() >= 2:
		var low := int(range_value[0])
		var high := int(range_value[1])
		if has_node("/root/RandomService"):
			return RandomService.rand_int(low, high)
		return randi_range(low, high)
	return int(range_value)

func apply_scenario(scenario: Dictionary) -> void:
	var initial_state: Dictionary = scenario.get("initial_state", {})
	for key in initial_state.keys():
		set_stat_value(str(key), int(initial_state[key]))
	for flag_name in scenario.get("flags", {}).keys():
		if bool(scenario["flags"][flag_name]):
			flags[str(flag_name)] = true
	city = str(scenario.get("city", city))
	background = str(scenario.get("background", background))
	clamp_state()
	emit_changed()

func apply_effects(effects: Dictionary) -> Array[String]:
	var summary: Array[String] = []
	for key in effects.keys():
		if str(key).begins_with("_"):
			continue
		var amount := int(effects[key])
		match key:
			"money":
				amount = apply_money_delta(amount, str(effects.get("_semantic", "支出")))
			"energy":
				energy += amount
			"stress":
				stress += amount
			"loneliness":
				loneliness += amount
			"hunger":
				hunger += amount
			"academic_progress":
				academic_progress += amount
			"exam_readiness":
				exam_readiness += amount
			"language":
				language += amount
			"social":
				social += amount
			"visa_progress":
				visa_progress += amount
			"career_progress":
				career_progress += amount
			"gpa_score":
				gpa_score += amount
			"aps_knowledge":
				aps_knowledge += amount
			"aps_score":
				aps_score += amount
			"testdaf_reading":
				testdaf_reading += amount
			"testdaf_listening":
				testdaf_listening += amount
			"testdaf_writing":
				testdaf_writing += amount
			"testdaf_speaking":
				testdaf_speaking += amount
			"cash_shortfall_count":
				cash_shortfall_count = maxi(0, cash_shortfall_count + amount)
			"arrears_amount":
				arrears_amount = maxi(0, arrears_amount + amount)
				_update_cashflow_flags()
			"parent_pressure":
				parent_pressure = clampi(parent_pressure + amount, 0, MAX_STAT)
			"reciprocity_debt":
				reciprocity_debt = maxi(0, reciprocity_debt + amount)
			"work_hours":
				var income := apply_work_hours(amount)
				if income != 0:
					summary.append("%s %+d" % [stat_label("money"), income])
			"illegal_work_hours":
				var income := apply_illegal_work_hours(amount)
				if income != 0:
					summary.append("%s %+d" % [stat_label("money"), income])
			_:
				continue
		summary.append("%s %+d" % [stat_label(key), amount])
	clamp_state()
	emit_changed()
	return summary

func can_afford(amount: int) -> bool:
	return amount <= 0 or money >= amount

func apply_money_delta(amount: int, semantic: String = "支出") -> int:
	if amount >= 0:
		money += amount
		return amount
	var cost := -amount
	if money >= cost:
		money -= cost
		return amount
	var paid := maxi(0, money)
	var missing := cost - paid
	money = 0
	arrears_amount += missing
	cash_shortfall_count += 1
	_update_cashflow_flags()
	add_log("现金不足：%s 需要 %d EUR，只支付 %d EUR，%d EUR 进入逾期。当前逾期 %d EUR。" % [
		semantic,
		cost,
		paid,
		missing,
		arrears_amount
	])
	return -paid

func _update_cashflow_flags() -> void:
	if cash_shortfall_count > 0:
		set_flag("cash_shortfall")
	if arrears_amount > 0:
		set_flag("arrears")
	if arrears_amount >= 600:
		set_flag("cashflow_warning")
	if arrears_amount >= 1000 or cash_shortfall_count >= 3:
		set_flag("cashflow_crisis")

func apply_weekly_drift() -> Array[String]:
	var effects := get_weekly_drift_effects()
	var released_amount := get_blocked_account_release_for_week()
	if released_amount > 0:
		blocked_account_balance = maxi(0, blocked_account_balance - released_amount)
		effects["money"] = int(effects.get("money", 0)) + released_amount
		add_log("冻结账户释放 %d EUR。本年剩余冻结余额：%d EUR。" % [released_amount, blocked_account_balance])
	var rent_due := get_monthly_rent_due_for_week()
	if rent_due > 0:
		effects["money"] = int(effects.get("money", 0)) - rent_due
		effects["_semantic"] = "生活开销与月租"
		set_flag("housing_contract_active")
		add_log("月租到期：%d EUR。" % rent_due)
	return apply_effects(effects)

func get_blocked_account_release_for_week() -> int:
	if week < 1:
		return 0
	if blocked_account_balance <= 0:
		return 0
	if week == 1 or (week - 1) % 4 == 0:
		return mini(BLOCKED_ACCOUNT_MONTHLY_RELEASE_2026, blocked_account_balance)
	return 0

func get_monthly_rent_due_for_week() -> int:
	if week < 1:
		return 0
	if week == 1 or (week - 1) % 4 == 0:
		return MONTHLY_RENT_ESTIMATE_2026
	return 0

func get_weekly_drift_effects() -> Dictionary:
	if week <= 0:
		var application_effects := {"energy": 30, "stress": 3, "money": -55}
		if money < 300:
			application_effects["stress"] = 8
		return application_effects
	var effects: Dictionary = _difficulty_weekly_drift()
	if money < 0:
		arrears_amount += -money
		money = 0
		cash_shortfall_count += 1
		_update_cashflow_flags()
	if arrears_amount > 0:
		effects["stress"] = int(effects.get("stress", 0)) + _difficulty_negative_money_stress()
		effects["hunger"] = int(effects.get("hunger", 0)) + 12
	if arrears_amount >= 500 or cash_shortfall_count >= 2:
		effects["stress"] = int(effects.get("stress", 0)) + 8
		effects["hunger"] = int(effects.get("hunger", 0)) + 10
		effects["energy"] = int(effects.get("energy", 0)) - 8
	if stress > 75:
		effects["academic_progress"] = _difficulty_high_stress_academic_penalty()
	if loneliness > 75:
		effects["energy"] = _difficulty_high_loneliness_energy()
	if hunger > 70:
		effects["energy"] = int(effects.get("energy", 0)) - 8
		effects["stress"] = int(effects.get("stress", 0)) + 5
		effects["academic_progress"] = int(effects.get("academic_progress", 0)) - 2
	if hunger > 90:
		effects["academic_progress"] = int(effects.get("academic_progress", 0)) - 3
	_apply_social_maintenance_effects(effects)
	return effects

func record_social_action(action_id: String, spent_money: bool) -> void:
	if spent_money:
		weekly_paid_social_actions += 1
	else:
		weekly_free_social_actions += 1

func _apply_social_maintenance_effects(effects: Dictionary) -> void:
	if weekly_paid_social_actions > 0:
		unpaid_social_streak = 0
		no_social_streak = 0
		return
	if weekly_free_social_actions > 0:
		unpaid_social_streak += 1
		no_social_streak = 0
		if unpaid_social_streak >= 5:
			effects["social"] = int(effects.get("social", 0)) - 4
			effects["loneliness"] = int(effects.get("loneliness", 0)) + 3
			set_flag("no_close_friends")
			add_log("社交关系变浅：连续多周只参加不用花钱的社交，朋友开始觉得关系不对等。")
		elif unpaid_social_streak >= 3:
			effects["social"] = int(effects.get("social", 0)) - 2
			effects["loneliness"] = int(effects.get("loneliness", 0)) + 2
			set_flag("shallow_friendships")
			add_log("社交关系变浅：总是不花钱参与社交，关系维护开始出现压力。")
		return
	no_social_streak += 1
	unpaid_social_streak = 0
	if no_social_streak >= 2:
		effects["social"] = int(effects.get("social", 0)) - 2
		effects["loneliness"] = int(effects.get("loneliness", 0)) + 3

func advance_week() -> void:
	if week == 0 and not flags.has("aps_passed"):
		emit_changed()
		return
	current_week_work_hours = 0
	weekly_paid_social_actions = 0
	weekly_free_social_actions = 0
	weekly_action_counts.clear()
	weekly_group_counts.clear()
	if week == 0 and flags.has("aps_passed"):
		week = 1
	else:
		week += 1
	if week > 20:
		week = 20
	emit_changed()

func apply_work_hours(hours: int) -> int:
	if hours <= 0:
		return 0
	current_week_work_hours += hours
	annual_work_half_days += ceili(float(hours) / 4.0)
	var income := legal_work_income_for_hours(hours)
	money += income
	if week >= 1 and current_week_work_hours > LEGAL_WEEKLY_WORK_HOURS:
		set_flag("work_limit_exceeded")
		add_log("本周合法打工时长风险：%d 小时，已超过学期内 20 小时红线。" % current_week_work_hours)
	if annual_work_half_days > LEGAL_ANNUAL_HALF_DAYS:
		set_flag("annual_work_limit_exceeded")
		add_log("年度打工额度风险：已累计 %d 个半天，超过 280 个半天上限。" % annual_work_half_days)
	return income

func apply_illegal_work_hours(hours: int) -> int:
	if hours <= 0:
		return 0
	var income := illegal_work_income_for_hours(hours)
	money += income
	return income

func legal_work_income_for_hours(hours: int) -> int:
	return EconomyRulesRef.legal_work_income_for_hours(hours)

func illegal_work_income_for_hours(hours: int) -> int:
	return EconomyRulesRef.illegal_work_income_for_hours(hours)

func resolve_aps_result() -> Dictionary:
	var roll := 0
	if has_node("/root/RandomService"):
		roll = RandomService.rand_int(-6, 6)
	else:
		roll = randi_range(-6, 6)
	var score := int(round(gpa_score * 0.42 + language * 0.22 + aps_knowledge * 0.30 + visa_progress * 0.06 - stress * 0.08 + roll))
	aps_score = clampi(score, 0, MAX_STAT)
	if aps_score >= 50:
		set_flag("aps_passed")
		university_tier = university_tier_from_aps_score(aps_score)
		if week < 0:
			week = 0
		add_log("APS 通过：综合评分 %d。可申请档位：%s。" % [aps_score, university_tier])
	else:
		flags.erase("aps_passed")
		university_tier = "未通过"
		add_log("APS 未通过：综合评分 %d。需要继续补德语、复习专业课或整理材料。" % aps_score)
	emit_changed()
	return {"score": aps_score, "tier": university_tier, "passed": flags.has("aps_passed")}

func resolve_testdaf_result(in_germany: bool = false) -> Dictionary:
	var stress_penalty := 0
	if stress >= 75:
		stress_penalty = 8
	elif stress >= 55:
		stress_penalty = 4
	var location_bonus := 3 if in_germany else 0
	testdaf_reading = _roll_testdaf_component(8 + location_bonus - stress_penalty)
	testdaf_listening = _roll_testdaf_component(location_bonus - stress_penalty)
	testdaf_writing = _roll_testdaf_component(4 + location_bonus - stress_penalty)
	testdaf_speaking = _roll_testdaf_component(-2 + location_bonus - stress_penalty)
	if has_testdaf_4x4():
		set_flag("testdaf_passed")
		add_log("TestDaF 达标：%s。满足 4x4 入学语言要求。" % testdaf_label())
	else:
		flags.erase("testdaf_passed")
		add_log("TestDaF 未达标：%s。需要继续语言学习，尤其补最低小分。" % testdaf_label())
	emit_changed()
	return {"passed": has_testdaf_4x4(), "label": testdaf_label()}

func _roll_testdaf_component(offset: int) -> int:
	var roll := _rand_range([-8, 8])
	return _testdaf_level_from_language(language + offset + roll)

func _testdaf_level_from_language(value: int) -> int:
	if value >= 84:
		return 5
	if value >= 58:
		return 4
	if value >= 38:
		return 3
	return 2

func has_testdaf_4x4() -> bool:
	return testdaf_reading >= 4 and testdaf_listening >= 4 and testdaf_writing >= 4 and testdaf_speaking >= 4

func testdaf_label() -> String:
	return "%d/%d/%d/%d" % [testdaf_reading, testdaf_listening, testdaf_writing, testdaf_speaking]

func university_tier_from_aps_score(score: int) -> String:
	if score >= 84:
		return "精英/TU9 冲刺"
	if score >= 72:
		return "研究型大学"
	if score >= 60:
		return "综合大学/应用科学大学"
	if score >= 50:
		return "保底项目/预科或受限专业谨慎"
	return "未通过"

func mark_event_completed(event_id: String) -> void:
	if not completed_events.has(event_id):
		completed_events.append(event_id)
	emit_changed()

func set_flag(flag_name: String) -> void:
	if flag_name != "":
		flags[flag_name] = true
		emit_changed()

func add_action_history(action_id: String, action_type: String = "", cooldown_group: String = "") -> void:
	action_history.append({
		"week": week,
		"action_id": action_id,
		"type": action_type,
		"cooldown_group": cooldown_group
	})
	weekly_action_counts[action_id] = int(weekly_action_counts.get(action_id, 0)) + 1
	if cooldown_group != "":
		weekly_group_counts[cooldown_group] = int(weekly_group_counts.get(cooldown_group, 0)) + 1
	if action_history.size() > 80:
		action_history.pop_front()

func record_week_snapshot(label: String = "week_end") -> void:
	var pressure_score: int = stress + hunger + int(arrears_amount / 20) + maxi(0, 50 - energy)
	weekly_snapshots.append({
		"label": label,
		"week": week,
		"money": money,
		"energy": energy,
		"stress": stress,
		"loneliness": loneliness,
		"hunger": hunger,
		"academic_progress": academic_progress,
		"exam_readiness": exam_readiness,
		"language": language,
		"social": social,
		"visa_progress": visa_progress,
		"career_progress": career_progress,
		"current_week_work_hours": current_week_work_hours,
		"annual_work_half_days": annual_work_half_days,
		"failed_courses": failed_courses,
		"cash_shortfall_count": cash_shortfall_count,
		"arrears_amount": arrears_amount,
		"parent_pressure": parent_pressure,
		"reciprocity_debt": reciprocity_debt,
		"weekly_paid_social_actions": weekly_paid_social_actions,
		"weekly_free_social_actions": weekly_free_social_actions,
		"unpaid_social_streak": unpaid_social_streak,
		"no_social_streak": no_social_streak,
		"pressure_score": pressure_score,
		"flags": flags.duplicate(true)
	})
	if weekly_snapshots.size() > 40:
		weekly_snapshots.pop_front()

func get_weekly_action_count(action_id: String) -> int:
	return int(weekly_action_counts.get(action_id, 0))

func get_weekly_group_count(cooldown_group: String) -> int:
	return int(weekly_group_counts.get(cooldown_group, 0))

func get_recent_group_count(cooldown_group: String, window: int) -> int:
	if cooldown_group == "" or window <= 0:
		return 0
	var count := 0
	for item in action_history:
		if str(item.get("cooldown_group", "")) != cooldown_group:
			continue
		var action_week := int(item.get("week", -999))
		if week - action_week <= window:
			count += 1
	return count

func add_log(message: String) -> void:
	event_log.append(message)
	if event_log.size() > 80:
		event_log.pop_front()
	EventBus.add_log(message)

func clamp_state() -> void:
	if money < 0:
		arrears_amount += -money
		money = 0
		cash_shortfall_count += 1
		_update_cashflow_flags()
	energy = clampi(energy, 0, MAX_STAT)
	stress = clampi(stress, 0, MAX_STAT)
	loneliness = clampi(loneliness, 0, MAX_STAT)
	hunger = clampi(hunger, 0, MAX_STAT)
	academic_progress = clampi(academic_progress, 0, MAX_STAT)
	exam_readiness = clampi(exam_readiness, 0, MAX_STAT)
	language = clampi(language, 0, MAX_STAT)
	social = clampi(social, 0, MAX_STAT)
	visa_progress = clampi(visa_progress, 0, MAX_STAT)
	career_progress = clampi(career_progress, 0, MAX_STAT)
	gpa_score = clampi(gpa_score, 0, MAX_STAT)
	aps_knowledge = clampi(aps_knowledge, 0, MAX_STAT)
	aps_score = clampi(aps_score, 0, MAX_STAT)
	testdaf_reading = clampi(testdaf_reading, 0, 5)
	testdaf_listening = clampi(testdaf_listening, 0, 5)
	testdaf_writing = clampi(testdaf_writing, 0, 5)
	testdaf_speaking = clampi(testdaf_speaking, 0, 5)

func emit_changed() -> void:
	state_changed.emit()
	if has_node("/root/EventBus"):
		EventBus.state_changed.emit()

func export_state_snapshot() -> Dictionary:
	return {
		"run_id": run_id,
		"seed": seed,
		"content_version": content_version,
		"rules_version": rules_version,
		"policy": policy_name,
		"difficulty": difficulty,
		"week": week,
		"semester": semester,
		"city": city,
		"background": background,
		"money": money,
		"blocked_account_balance": blocked_account_balance,
		"energy": energy,
		"stress": stress,
		"loneliness": loneliness,
		"hunger": hunger,
		"academic_progress": academic_progress,
		"exam_readiness": exam_readiness,
		"language": language,
		"social": social,
		"visa_progress": visa_progress,
		"career_progress": career_progress,
		"gpa_score": gpa_score,
		"aps_knowledge": aps_knowledge,
		"aps_score": aps_score,
		"university_tier": university_tier,
		"testdaf_reading": testdaf_reading,
		"testdaf_listening": testdaf_listening,
		"testdaf_writing": testdaf_writing,
		"testdaf_speaking": testdaf_speaking,
		"current_week_work_hours": current_week_work_hours,
		"annual_work_half_days": annual_work_half_days,
		"failed_courses": failed_courses,
		"cash_shortfall_count": cash_shortfall_count,
		"arrears_amount": arrears_amount,
		"parent_pressure": parent_pressure,
		"reciprocity_debt": reciprocity_debt,
		"weekly_paid_social_actions": weekly_paid_social_actions,
		"weekly_free_social_actions": weekly_free_social_actions,
		"unpaid_social_streak": unpaid_social_streak,
		"no_social_streak": no_social_streak,
		"flags": flags.duplicate(true),
		"relationships": relationships.duplicate(true),
		"completed_events": completed_events.duplicate(),
		"weekly_snapshots": weekly_snapshots.duplicate(true),
		"last_exam_result": last_exam_result.duplicate(true),
		"last_ending_id": last_ending_id,
		"rng_state": RandomService.get_rng_state() if has_node("/root/RandomService") else 0
	}

func export_public_stats() -> Dictionary:
	return {
		"week": week,
		"flags": flags.duplicate(true),
		"money": money,
		"blocked_account_balance": blocked_account_balance,
		"energy": energy,
		"stress": stress,
		"loneliness": loneliness,
		"hunger": hunger,
		"academic_progress": academic_progress,
		"exam_readiness": exam_readiness,
		"language": language,
		"social": social,
		"visa_progress": visa_progress,
		"career_progress": career_progress,
		"gpa_score": gpa_score,
		"aps_knowledge": aps_knowledge,
		"aps_score": aps_score,
		"university_tier": university_tier,
		"testdaf_reading": testdaf_reading,
		"testdaf_listening": testdaf_listening,
		"testdaf_writing": testdaf_writing,
		"testdaf_speaking": testdaf_speaking,
		"current_week_work_hours": current_week_work_hours,
		"annual_work_half_days": annual_work_half_days,
		"failed_courses": failed_courses,
		"cash_shortfall_count": cash_shortfall_count,
		"arrears_amount": arrears_amount,
		"parent_pressure": parent_pressure,
		"reciprocity_debt": reciprocity_debt,
		"weekly_paid_social_actions": weekly_paid_social_actions,
		"weekly_free_social_actions": weekly_free_social_actions,
		"unpaid_social_streak": unpaid_social_streak,
		"no_social_streak": no_social_streak
	}

func set_stat_value(key: String, value: int) -> void:
	match key:
		"week":
			week = value
		"semester":
			semester = value
		"money":
			money = value
		"blocked_account_balance":
			blocked_account_balance = maxi(0, value)
		"energy":
			energy = value
		"stress":
			stress = value
		"loneliness":
			loneliness = value
		"hunger":
			hunger = value
		"academic", "academic_progress":
			academic_progress = value
		"exam_readiness":
			exam_readiness = value
		"german", "language":
			language = value
		"social":
			social = value
		"admin", "visa_progress":
			visa_progress = value
		"career", "career_progress":
			career_progress = value
		"gpa", "gpa_score":
			gpa_score = value
		"aps_knowledge":
			aps_knowledge = value
		"aps_score":
			aps_score = value
		"testdaf_reading":
			testdaf_reading = value
		"testdaf_listening":
			testdaf_listening = value
		"testdaf_writing":
			testdaf_writing = value
		"testdaf_speaking":
			testdaf_speaking = value
		"current_week_work_hours":
			current_week_work_hours = value
		"annual_work_half_days":
			annual_work_half_days = value
		"failed_courses":
			failed_courses = value
		"cash_shortfall_count":
			cash_shortfall_count = maxi(0, value)
		"arrears_amount":
			arrears_amount = maxi(0, value)
			_update_cashflow_flags()
		"parent_pressure":
			parent_pressure = clampi(value, 0, MAX_STAT)
		"reciprocity_debt":
			reciprocity_debt = maxi(0, value)
		"weekly_paid_social_actions":
			weekly_paid_social_actions = maxi(0, value)
		"weekly_free_social_actions":
			weekly_free_social_actions = maxi(0, value)
		"unpaid_social_streak":
			unpaid_social_streak = maxi(0, value)
		"no_social_streak":
			no_social_streak = maxi(0, value)

func to_save_data() -> Dictionary:
	return {
		"run_id": run_id,
		"seed": seed,
		"content_version": content_version,
		"rules_version": rules_version,
		"policy": policy_name,
		"difficulty": difficulty,
		"week": week,
		"semester": semester,
		"city": city,
		"background": background,
		"money": money,
		"blocked_account_balance": blocked_account_balance,
		"energy": energy,
		"stress": stress,
		"loneliness": loneliness,
		"hunger": hunger,
		"academic_progress": academic_progress,
		"exam_readiness": exam_readiness,
		"language": language,
		"social": social,
		"visa_progress": visa_progress,
		"career_progress": career_progress,
		"gpa_score": gpa_score,
		"aps_knowledge": aps_knowledge,
		"aps_score": aps_score,
		"university_tier": university_tier,
		"testdaf_reading": testdaf_reading,
		"testdaf_listening": testdaf_listening,
		"testdaf_writing": testdaf_writing,
		"testdaf_speaking": testdaf_speaking,
		"current_week_work_hours": current_week_work_hours,
		"annual_work_half_days": annual_work_half_days,
		"failed_courses": failed_courses,
		"cash_shortfall_count": cash_shortfall_count,
		"arrears_amount": arrears_amount,
		"parent_pressure": parent_pressure,
		"reciprocity_debt": reciprocity_debt,
		"weekly_paid_social_actions": weekly_paid_social_actions,
		"weekly_free_social_actions": weekly_free_social_actions,
		"unpaid_social_streak": unpaid_social_streak,
		"no_social_streak": no_social_streak,
		"flags": flags,
		"relationships": relationships,
		"completed_events": completed_events,
		"action_history": action_history,
		"weekly_snapshots": weekly_snapshots,
		"weekly_action_counts": weekly_action_counts,
		"weekly_group_counts": weekly_group_counts,
		"event_log": event_log,
		"last_exam_result": last_exam_result,
		"last_ending_id": last_ending_id
	}

func from_save_data(data: Dictionary) -> void:
	run_id = int(data.get("run_id", 0))
	seed = int(data.get("seed", 0))
	content_version = str(data.get("content_version", CONTENT_VERSION))
	rules_version = str(data.get("rules_version", RULES_VERSION))
	policy_name = str(data.get("policy", ""))
	difficulty = _normalize_difficulty(str(data.get("difficulty", "normal")))
	week = int(data.get("week", -8))
	semester = int(data.get("semester", 1))
	city = str(data.get("city", "Berlin"))
	background = str(data.get("background", "ordinary"))
	money = int(data.get("money", 500))
	blocked_account_balance = int(data.get("blocked_account_balance", BLOCKED_ACCOUNT_REQUIRED_2026))
	energy = int(data.get("energy", 100))
	stress = int(data.get("stress", 20))
	loneliness = int(data.get("loneliness", 30))
	hunger = int(data.get("hunger", 25))
	academic_progress = int(data.get("academic_progress", 10))
	exam_readiness = int(data.get("exam_readiness", 10))
	language = int(data.get("language", 20))
	social = int(data.get("social", 15))
	visa_progress = int(data.get("visa_progress", 15))
	career_progress = int(data.get("career_progress", 0))
	gpa_score = int(data.get("gpa_score", 65))
	aps_knowledge = int(data.get("aps_knowledge", 25))
	aps_score = int(data.get("aps_score", 0))
	university_tier = str(data.get("university_tier", "未定位"))
	testdaf_reading = int(data.get("testdaf_reading", 0))
	testdaf_listening = int(data.get("testdaf_listening", 0))
	testdaf_writing = int(data.get("testdaf_writing", 0))
	testdaf_speaking = int(data.get("testdaf_speaking", 0))
	current_week_work_hours = int(data.get("current_week_work_hours", 0))
	annual_work_half_days = int(data.get("annual_work_half_days", 0))
	failed_courses = int(data.get("failed_courses", 0))
	cash_shortfall_count = int(data.get("cash_shortfall_count", 0))
	arrears_amount = int(data.get("arrears_amount", 0))
	parent_pressure = int(data.get("parent_pressure", 0))
	reciprocity_debt = int(data.get("reciprocity_debt", 0))
	weekly_paid_social_actions = int(data.get("weekly_paid_social_actions", 0))
	weekly_free_social_actions = int(data.get("weekly_free_social_actions", 0))
	unpaid_social_streak = int(data.get("unpaid_social_streak", 0))
	no_social_streak = int(data.get("no_social_streak", 0))
	flags = data.get("flags", {})
	relationships = data.get("relationships", {})
	completed_events = []
	for item in data.get("completed_events", []):
		completed_events.append(str(item))
	action_history = []
	for item in data.get("action_history", []):
		action_history.append(item)
	weekly_snapshots = []
	for item in data.get("weekly_snapshots", []):
		weekly_snapshots.append(item)
	weekly_action_counts = data.get("weekly_action_counts", {})
	weekly_group_counts = data.get("weekly_group_counts", {})
	event_log = []
	for item in data.get("event_log", []):
		event_log.append(str(item))
	last_exam_result = data.get("last_exam_result", {})
	last_ending_id = str(data.get("last_ending_id", ""))
	clamp_state()
	emit_changed()

func stat_label(key: String) -> String:
	var labels := {
		"money": "金钱",
		"blocked_account_balance": "冻结余额",
		"energy": "精力",
		"stress": "压力",
		"loneliness": "孤独",
		"hunger": "饥饿",
		"academic_progress": "学业",
		"exam_readiness": "备考",
		"language": "德语",
		"social": "社交",
		"visa_progress": "行政",
		"career_progress": "职业",
		"gpa_score": "大学成绩",
		"aps_knowledge": "专业复习",
		"aps_score": "APS",
		"testdaf_reading": "TestDaF 阅读",
		"testdaf_listening": "TestDaF 听力",
		"testdaf_writing": "TestDaF 写作",
		"testdaf_speaking": "TestDaF 口语",
		"work_hours": "本周工时",
		"illegal_work_hours": "黑工工时",
		"current_week_work_hours": "本周工时",
		"annual_work_half_days": "年度半天",
		"failed_courses": "挂科",
		"cash_shortfall_count": "现金短缺",
		"arrears_amount": "逾期金额",
		"parent_pressure": "家庭压力",
		"reciprocity_debt": "人情债",
		"weekly_paid_social_actions": "付费社交",
		"weekly_free_social_actions": "免费社交",
		"unpaid_social_streak": "免费社交连续周",
		"no_social_streak": "无社交连续周",
	}
	return labels.get(key, key)

func _normalize_difficulty(value: String) -> String:
	if has_node("/root/DifficultyConfig"):
		return DifficultyConfig.normalize(value)
	if ["easy", "normal", "hard", "realistic"].has(value):
		return value
	return "normal"

func _difficulty_weekly_drift() -> Dictionary:
	if has_node("/root/DifficultyConfig"):
		return DifficultyConfig.get_weekly_drift(difficulty)
	return {"energy": 32, "stress": 2, "loneliness": 1, "money": -110}

func _difficulty_initial_profile() -> Dictionary:
	if has_node("/root/DifficultyConfig"):
		return DifficultyConfig.get_initial_profile(difficulty)
	return {"money": [2500, 7500], "gpa_score": [58, 82], "language": [20, 45], "aps_knowledge": [25, 45], "stress": [18, 35], "loneliness": [20, 38], "hunger": [15, 35], "social": [10, 25]}

func _difficulty_negative_money_stress() -> int:
	if has_node("/root/DifficultyConfig"):
		return DifficultyConfig.get_negative_money_stress(difficulty)
	return 8

func _difficulty_high_stress_academic_penalty() -> int:
	if has_node("/root/DifficultyConfig"):
		return DifficultyConfig.get_high_stress_academic_penalty(difficulty)
	return -2

func _difficulty_high_loneliness_energy() -> int:
	if has_node("/root/DifficultyConfig"):
		return DifficultyConfig.get_high_loneliness_energy(difficulty)
	return 20
