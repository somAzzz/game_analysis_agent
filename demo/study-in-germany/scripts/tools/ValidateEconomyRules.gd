extends SceneTree

const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var game_state: Node = root.get_node("/root/GameState")
	var errors: Array[String] = []
	var legal_wage: float = float(game_state.LEGAL_WORK_HOURLY_WAGE_2026)
	var illegal_wage: float = float(game_state.ILLEGAL_CASH_WORK_WAGE)
	var legal_10h: int = game_state.legal_work_income_for_hours(10)
	var illegal_10h: int = game_state.illegal_work_income_for_hours(10)

	if not is_equal_approx(legal_wage, 13.90):
		errors.append("legal hourly wage should be 13.90 EUR in 2026, got %.2f" % legal_wage)
	if illegal_wage >= legal_wage:
		errors.append("illegal cash work wage %.2f must be lower than legal wage %.2f" % [illegal_wage, legal_wage])
	if legal_10h <= illegal_10h:
		errors.append("10h legal income %d must be higher than 10h illegal income %d" % [legal_10h, illegal_10h])
	if not is_equal_approx(float(illegal_wage), legal_wage * game_state.ILLEGAL_CASH_WORK_WAGE_RATIO):
		errors.append("illegal cash work wage should follow the configured ratio %.2f" % game_state.ILLEGAL_CASH_WORK_WAGE_RATIO)

	_validate_runtime_work_income(game_state, errors)
	_validate_cashflow_guardrails(game_state, errors)
	_validate_monthly_rent(game_state, errors)
	_validate_social_maintenance(game_state, errors)
	_validate_friend_borrowing(game_state, errors)
	_validate_content_work_effects(errors)

	if not errors.is_empty():
		for error in errors:
			printerr(error)
		quit(1)
		return

	print("Economy rules validation complete: legal %.2f EUR/h -> %d EUR per 10h; illegal %.2f EUR/h -> %d EUR per 10h" % [
		legal_wage,
		legal_10h,
		illegal_wage,
		illegal_10h
	])
	quit(0)

func _validate_runtime_work_income(game_state: Node, errors: Array[String]) -> void:
	game_state.reset()
	var start_money: int = game_state.money
	var legal_income: int = game_state.apply_work_hours(8)
	if legal_income != game_state.legal_work_income_for_hours(8):
		errors.append("apply_work_hours(8) returned %d, expected %d" % [legal_income, game_state.legal_work_income_for_hours(8)])
	if game_state.money - start_money != legal_income:
		errors.append("legal work should add income to money exactly once")
	if game_state.current_week_work_hours != 8:
		errors.append("legal work should record 8 weekly hours, got %d" % game_state.current_week_work_hours)

	start_money = game_state.money
	var illegal_income: int = game_state.apply_illegal_work_hours(8)
	if illegal_income != game_state.illegal_work_income_for_hours(8):
		errors.append("apply_illegal_work_hours(8) returned %d, expected %d" % [illegal_income, game_state.illegal_work_income_for_hours(8)])
	if game_state.money - start_money != illegal_income:
		errors.append("illegal work should add income to money exactly once")
	if game_state.current_week_work_hours != 8:
		errors.append("illegal cash work should not increase legal weekly hours")

func _validate_cashflow_guardrails(game_state: Node, errors: Array[String]) -> void:
	var registry: Node = root.get_node("/root/DataRegistry")
	game_state.reset()
	game_state.week = 1
	game_state.money = 5
	var cook_action = registry.get_action_by_id("cook_at_home")
	if cook_action == null:
		errors.append("cook_at_home action should exist for affordability validation")
	elif cook_action.can_use(game_state):
		errors.append("ordinary paid action cook_at_home should be unavailable when money is below cost")

	game_state.reset()
	game_state.week = 1
	game_state.money = 10
	game_state.apply_effects({"money": -50, "_semantic": "测试必要支出"})
	if game_state.money != 0:
		errors.append("cash shortfall should leave money at 0, got %d" % game_state.money)
	if game_state.arrears_amount != 40:
		errors.append("cash shortfall should create 40 EUR arrears, got %d" % game_state.arrears_amount)
	if not game_state.flags.has("arrears") or not game_state.flags.has("cash_shortfall"):
		errors.append("cash shortfall should set arrears and cash_shortfall flags")

func _validate_monthly_rent(game_state: Node, errors: Array[String]) -> void:
	game_state.reset()
	game_state.week = 1
	game_state.money = 200
	game_state.blocked_account_balance = 0
	game_state.apply_weekly_drift()
	if game_state.money != 0:
		errors.append("monthly rent shortfall should leave money at 0, got %d" % game_state.money)
	if game_state.arrears_amount <= 0:
		errors.append("monthly rent shortfall should create arrears")
	if not game_state.flags.has("housing_contract_active"):
		errors.append("monthly rent should activate housing contract flag")

func _validate_social_maintenance(game_state: Node, errors: Array[String]) -> void:
	game_state.reset()
	game_state.week = 1
	game_state.social = 40
	game_state.record_social_action("language_tandem", false)
	game_state.apply_weekly_drift()
	game_state.advance_week()
	game_state.record_social_action("language_tandem", false)
	game_state.apply_weekly_drift()
	game_state.advance_week()
	game_state.record_social_action("language_tandem", false)
	game_state.apply_weekly_drift()
	if game_state.unpaid_social_streak < 3:
		errors.append("free-only social streak should reach 3 after three free social weeks")
	if not game_state.flags.has("shallow_friendships"):
		errors.append("free-only social streak should set shallow_friendships")
	game_state.advance_week()
	game_state.record_social_action("classmate_meal", true)
	game_state.apply_weekly_drift()
	if game_state.unpaid_social_streak != 0:
		errors.append("paid social should reset free-only social streak")

func _validate_friend_borrowing(game_state: Node, errors: Array[String]) -> void:
	var registry: Node = root.get_node("/root/DataRegistry")
	var event = _find_event(registry, "semester_fee_due")
	if event == null:
		errors.append("semester_fee_due should exist for friend borrowing validation")
		return
	var borrow_choice = _find_choice(event, "找朋友周转学期费")
	if borrow_choice == null:
		errors.append("semester_fee_due should include friend borrowing choice")
		return
	game_state.reset()
	game_state.week = 16
	game_state.social = 20
	if borrow_choice.is_available(game_state):
		errors.append("friend borrowing should not be available with low social")
	game_state.social = 80
	game_state.stress = 20
	if not borrow_choice.is_available(game_state):
		errors.append("friend borrowing should be available with high social")
	var high_social_rate: float = EventResolverScript.get_success_rate(borrow_choice, game_state)
	game_state.social = 45
	var threshold_rate: float = EventResolverScript.get_success_rate(borrow_choice, game_state)
	if high_social_rate <= threshold_rate:
		errors.append("friend borrowing success rate should improve with social: high %.2f threshold %.2f" % [high_social_rate, threshold_rate])

func _find_event(registry: Node, event_id: String):
	for event in registry.events:
		if event.id == event_id:
			return event
	return null

func _find_choice(event, text: String):
	for choice in event.choices:
		if choice.text == text:
			return choice
	return null

func _validate_content_work_effects(errors: Array[String]) -> void:
	var registry: Node = root.get_node("/root/DataRegistry")
	for action in registry.actions:
		var action_context := "%s %s %s" % [action.id, action.name, action.description]
		_validate_effect_record("action:%s" % action.id, action.effects, errors, action_context)
	for event in registry.events:
		for choice in event.choices:
			var choice_context: String = choice.text
			_validate_effect_record("event:%s choice:%s success" % [event.id, choice.text], choice.success_effects, errors, choice_context)
			_validate_effect_record("event:%s choice:%s failure" % [event.id, choice.text], choice.failure_effects, errors, choice_context)

func _validate_effect_record(label: String, effects: Dictionary, errors: Array[String], context: String = "") -> void:
	var legal_hours := int(effects.get("work_hours", 0))
	var illegal_hours := int(effects.get("illegal_work_hours", 0))
	var money_delta := int(effects.get("money", 0))
	if legal_hours > 0 and illegal_hours > 0:
		errors.append("%s mixes legal and illegal work hours in one effect" % label)
	if legal_hours > 0 and money_delta > 0:
		errors.append("%s has work_hours and positive money; wage should be derived from hours" % label)
	if illegal_hours > 0 and money_delta > 0:
		errors.append("%s has illegal_work_hours and positive money; cash wage should be derived from hours" % label)
	if money_delta > 0 and legal_hours <= 0 and illegal_hours <= 0 and _looks_like_work_income(context):
		errors.append("%s looks like work income but uses positive money instead of work_hours or illegal_work_hours" % label)

func _looks_like_work_income(context: String) -> bool:
	var lowered := context.to_lower()
	var work_tokens := [
		"打工",
		"黑工",
		"现金工",
		"上班",
		"接更多班",
		"多打一班",
		"排班",
		"试工",
		"job",
		"work",
		"shift"
	]
	for token in work_tokens:
		if lowered.contains(token):
			return true
	return false
