extends SceneTree

const RiskEvaluatorScript := preload("res://scripts/simulation/RiskEvaluator.gd")

var game_state: Node
var data_registry: Node

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	game_state = root.get_node("/root/GameState")
	data_registry = root.get_node("/root/DataRegistry")
	var config := _parse_args()
	var errors: Array[String] = []
	var summary: Dictionary = {}

	for scenario in _risk_scenarios():
		var result := _validate_scenario(scenario, errors)
		summary[str(scenario["id"])] = result

	var out_path := str(config.get("out", "reports/risk_guidance_validation.json"))
	_write_text(_global_path(out_path), JSON.stringify({
		"errors": errors,
		"summary": summary
	}, "\t"))

	if not errors.is_empty():
		for error in errors:
			printerr(error)
		print("Risk guidance validation failed: %d errors -> %s" % [errors.size(), _global_path(out_path)])
		quit(1)
		return

	print("Risk guidance validation complete: %d scenarios -> %s" % [_risk_scenarios().size(), _global_path(out_path)])
	quit(0)

func _validate_scenario(scenario: Dictionary, errors: Array[String]) -> Dictionary:
	_apply_risk_state(scenario)
	var risks: Array = RiskEvaluatorScript.get_top_risks(game_state, 3)
	var expected_id := str(scenario.get("expected_risk", ""))
	var risk_ids: Array[String] = []
	for risk in risks:
		var risk_id := str(risk.get("id", ""))
		risk_ids.append(risk_id)
		_validate_risk_shape(str(scenario["id"]), risk, errors)
		_validate_suggested_actions(str(scenario["id"]), risk, errors)
	if expected_id != "" and not risk_ids.has(expected_id):
		errors.append("%s expected risk %s in top risks, got %s" % [str(scenario["id"]), expected_id, ",".join(risk_ids)])
	return {
		"top_risks": risk_ids,
		"expected_risk": expected_id,
		"state": game_state.export_public_stats()
	}

func _validate_risk_shape(scenario_id: String, risk: Dictionary, errors: Array[String]) -> void:
	for key in ["id", "title", "score", "body", "suggested_actions"]:
		if not risk.has(key):
			errors.append("%s risk missing key %s" % [scenario_id, key])
	if str(risk.get("title", "")).strip_edges() == "":
		errors.append("%s risk %s has empty title" % [scenario_id, str(risk.get("id", ""))])
	if str(risk.get("body", "")).strip_edges() == "":
		errors.append("%s risk %s has empty body" % [scenario_id, str(risk.get("id", ""))])
	var score := int(risk.get("score", 0))
	if score <= 0 or score > 100:
		errors.append("%s risk %s has invalid score %d" % [scenario_id, str(risk.get("id", "")), score])

func _validate_suggested_actions(scenario_id: String, risk: Dictionary, errors: Array[String]) -> void:
	var actions: Array = risk.get("suggested_actions", [])
	if actions.is_empty():
		errors.append("%s risk %s has no suggested actions" % [scenario_id, str(risk.get("id", ""))])
		return
	var has_existing_action := false
	var has_currently_available_action := false
	for action_id_value in actions:
		var action_id := str(action_id_value)
		var action = data_registry.get_action_by_id(action_id)
		if action == null:
			errors.append("%s risk %s suggests missing action %s" % [scenario_id, str(risk.get("id", "")), action_id])
			continue
		has_existing_action = true
		if action.can_use(game_state):
			has_currently_available_action = true
	if not has_existing_action:
		errors.append("%s risk %s has no valid suggested actions" % [scenario_id, str(risk.get("id", ""))])
	if not has_currently_available_action:
		errors.append("%s risk %s has no currently available suggested actions" % [scenario_id, str(risk.get("id", ""))])

func _risk_scenarios() -> Array[Dictionary]:
	return [
		{
			"id": "application_aps_blocked",
			"expected_risk": "aps",
			"state": {"week": -8, "money": 180, "language": 20, "aps_knowledge": 25, "stress": 20},
			"flags": {}
		},
		{
			"id": "application_testdaf_pending",
			"expected_risk": "testdaf_application",
			"state": {"week": -4, "money": 900, "language": 56, "aps_knowledge": 50, "stress": 25},
			"flags": {"aps_documents_ready": true, "aps_passed": true}
		},
		{
			"id": "registration_window",
			"expected_risk": "registration",
			"state": {"week": 4, "money": 1800, "language": 65, "visa_progress": 30, "stress": 35},
			"flags": {"aps_passed": true, "testdaf_passed": true}
		},
		{
			"id": "cashflow_crisis",
			"expected_risk": "money",
			"state": {"week": 9, "money": -1200, "hunger": 70, "stress": 70, "language": 70},
			"flags": {"aps_passed": true, "testdaf_passed": true, "school_registered": true}
		},
		{
			"id": "academic_warning",
			"expected_risk": "academic",
			"state": {"week": 16, "money": 1200, "academic_progress": 25, "exam_readiness": 30, "stress": 45, "language": 70},
			"flags": {"aps_passed": true, "testdaf_passed": true, "school_registered": true}
		},
		{
			"id": "stress_warning",
			"expected_risk": "stress",
			"state": {"week": 12, "money": 1500, "stress": 88, "energy": 55, "language": 70},
			"flags": {"aps_passed": true, "testdaf_passed": true, "school_registered": true}
		},
		{
			"id": "hunger_warning",
			"expected_risk": "hunger",
			"state": {"week": 12, "money": 1500, "hunger": 86, "stress": 30, "language": 70},
			"flags": {"aps_passed": true, "testdaf_passed": true, "school_registered": true}
		},
		{
			"id": "visa_warning",
			"expected_risk": "visa",
			"state": {"week": 14, "money": 1500, "visa_progress": 30, "stress": 35, "language": 70},
			"flags": {"aps_passed": true, "testdaf_passed": true, "school_registered": true}
		},
		{
			"id": "work_limit_warning",
			"expected_risk": "work",
			"state": {"week": 12, "money": 1500, "current_week_work_hours": 24, "stress": 35, "language": 70},
			"flags": {"aps_passed": true, "testdaf_passed": true, "school_registered": true, "visa_valid": true}
		}
	]

func _apply_risk_state(scenario: Dictionary) -> void:
	game_state.reset()
	var state: Dictionary = scenario.get("state", {})
	for key in state.keys():
		game_state.set_stat_value(str(key), int(state[key]))
	var flags: Dictionary = scenario.get("flags", {})
	for flag_name in flags.keys():
		if bool(flags[flag_name]):
			game_state.set_flag(str(flag_name))
	game_state.clamp_state()

func _parse_args() -> Dictionary:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		args = OS.get_cmdline_args()
	var parsed: Dictionary = {}
	var index := 0
	while index < args.size():
		var arg := str(args[index])
		if arg.begins_with("--"):
			var body := arg.substr(2)
			var equals_index := body.find("=")
			if equals_index >= 0:
				parsed[body.substr(0, equals_index)] = body.substr(equals_index + 1)
			elif index + 1 < args.size() and not str(args[index + 1]).begins_with("--"):
				parsed[body] = str(args[index + 1])
				index += 1
			else:
				parsed[body] = true
		index += 1
	return parsed

func _global_path(path: String) -> String:
	if path.begins_with("/"):
		return path
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	return ProjectSettings.globalize_path("res://%s" % path)

func _write_text(path: String, text: String) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file = FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(text)
		file.close()
