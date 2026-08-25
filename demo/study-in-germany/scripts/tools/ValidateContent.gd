extends SceneTree

var data_registry: Node

const MAINLINE_EVENT_IDS := {
	"aps_start": true,
	"arrival": true,
	"first_lecture": true,
	"wg_interview": true,
	"legal_work_limit_notice": true,
	"anmeldung_deadline": true,
	"exam_registration": true,
	"midterm_pressure": true,
	"group_invite": true,
	"exercise_sheet_warning": true,
	"visa_status_hidden_check": true,
	"klausur_countdown": true,
	"exam_week": true,
	"semester_wrap": true,
	"termin_missing": true,
	"deportation_risk_notice": true,
	"rent_pressure": true,
	"job_study_conflict": true,
	"lonely_christmas": true,
	"relationship_support_exam": true
}

const GENERIC_OPTION_TEXTS := {
	"稳妥处理": true,
	"寻求帮助": true,
	"冒险推进": true,
	"暂时回避": true
}

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	data_registry = root.get_node("/root/DataRegistry")
	var config: Dictionary = _parse_args()
	var out_path: String = str(config.get("out", "reports/content_validation.json"))
	var report: Dictionary = validate_content()
	_write_text(_global_path(out_path), JSON.stringify(report, "\t"))
	var error_count: int = report["errors"].size()
	var warning_count: int = report["warnings"].size()
	print("Content validation complete: %d errors, %d warnings -> %s" % [error_count, warning_count, _global_path(out_path)])
	quit(1 if error_count > 0 else 0)

func validate_content() -> Dictionary:
	var errors: Array = []
	var warnings: Array = []
	var event_ids: Dictionary = _collect_ids(data_registry.events, "event", errors)
	_validate_mainline_ids_exist(event_ids, errors)
	_collect_ids(data_registry.actions, "action", errors)
	_collect_ids(data_registry.characters, "character", errors)
	_collect_ids(data_registry.endings, "ending", errors)

	var set_flags: Dictionary = {}
	var required_flags: Dictionary = {}
	var valid_stats: Dictionary = {
		"money": true,
		"blocked_account_balance": true,
		"energy": true,
		"stress": true,
		"loneliness": true,
		"hunger": true,
		"academic_progress": true,
		"exam_readiness": true,
		"language": true,
		"social": true,
		"visa_progress": true,
		"career_progress": true,
		"gpa_score": true,
		"aps_knowledge": true,
		"aps_score": true,
		"testdaf_reading": true,
		"testdaf_listening": true,
		"testdaf_writing": true,
		"testdaf_speaking": true,
		"work_hours": true,
		"illegal_work_hours": true,
		"current_week_work_hours": true,
		"annual_work_half_days": true,
		"failed_courses": true
	}

	for action in data_registry.actions:
		_validate_effects(action.effects, valid_stats, "action", action.id, "", warnings)
		_collect_required_flag(action.requirements, required_flags, "action:%s" % action.id)
		if action.set_flag != "":
			set_flags[action.set_flag] = true
		if action.id == "aps_interview":
			set_flags["aps_passed"] = true
		if action.id == "testdaf_exam_china" or action.id == "testdaf_exam_germany":
			set_flags["testdaf_passed"] = true
	set_flags["work_limit_exceeded"] = true
	set_flags["annual_work_limit_exceeded"] = true

	for event in data_registry.events:
		if event.choices.size() < 2:
			warnings.append({"type": "few_event_choices", "event_id": event.id, "choice_count": event.choices.size()})
		if MAINLINE_EVENT_IDS.has(event.id) and event.choices.size() < 4:
			warnings.append({"type": "mainline_event_needs_four_choices", "event_id": event.id, "choice_count": event.choices.size()})
		if event.trigger.is_empty():
			warnings.append({"type": "event_without_trigger", "event_id": event.id})
		_collect_required_flag(event.trigger, required_flags, "event:%s" % event.id)
		var choice_signatures: Dictionary = {}
		for index in range(event.choices.size()):
			var choice = event.choices[index]
			var choice_id: String = "choice_%02d" % [index + 1]
			_validate_effects(choice.success_effects, valid_stats, "event_choice_success", event.id, choice_id, warnings)
			_validate_effects(choice.failure_effects, valid_stats, "event_choice_failure", event.id, choice_id, warnings)
			if MAINLINE_EVENT_IDS.has(event.id):
				_validate_mainline_choice(choice, event.id, choice_id, warnings)
				var signature := _choice_signature(choice)
				if choice_signatures.has(signature):
					warnings.append({
						"type": "duplicate_mainline_choice_effects",
						"event_id": event.id,
						"choice_id": choice_id,
						"duplicates": choice_signatures[signature]
					})
				else:
					choice_signatures[signature] = choice_id
			_collect_required_flag(choice.requirements, required_flags, "event:%s.%s" % [event.id, choice_id])
			if choice.set_flag != "":
				set_flags[choice.set_flag] = true
			if choice.next_event_id != "" and not event_ids.has(choice.next_event_id):
				errors.append({
					"type": "missing_next_event",
					"event_id": event.id,
					"choice_id": choice_id,
					"next_event_id": choice.next_event_id
				})

	for flag_name in required_flags.keys():
		if not set_flags.has(flag_name):
			warnings.append({
				"type": "required_flag_never_set",
				"flag": flag_name,
				"used_by": required_flags[flag_name]
			})

	return {
		"errors": errors,
		"warnings": warnings,
		"summary": {
			"actions": data_registry.actions.size(),
			"events": data_registry.events.size(),
			"characters": data_registry.characters.size(),
			"endings": data_registry.endings.size()
		}
	}

func _collect_ids(items: Array, item_type: String, errors: Array) -> Dictionary:
	var ids: Dictionary = {}
	for item in items:
		if str(item.id) == "":
			errors.append({"type": "missing_id", "item_type": item_type})
			continue
		if ids.has(item.id):
			errors.append({"type": "duplicate_id", "item_type": item_type, "id": item.id})
		ids[item.id] = true
	return ids

func _validate_mainline_ids_exist(event_ids: Dictionary, errors: Array) -> void:
	for event_id in MAINLINE_EVENT_IDS.keys():
		if not event_ids.has(event_id):
			errors.append({
				"type": "missing_mainline_event",
				"event_id": event_id
			})

func _validate_effects(effects: Dictionary, valid_stats: Dictionary, source_type: String, source_id: String, choice_id: String, warnings: Array) -> void:
	for key in effects.keys():
		if not valid_stats.has(str(key)):
			warnings.append({
				"type": "unknown_effect_stat",
				"source_type": source_type,
				"source_id": source_id,
				"choice_id": choice_id,
				"stat": str(key)
			})

func _validate_mainline_choice(choice, event_id: String, choice_id: String, warnings: Array) -> void:
	var has_effect: bool = not choice.success_effects.is_empty() or not choice.failure_effects.is_empty()
	var has_gate: bool = not choice.requirements.is_empty() or not choice.success_modifiers.is_empty()
	var has_story_state: bool = choice.set_flag != "" or choice.next_event_id != ""
	if GENERIC_OPTION_TEXTS.has(choice.text):
		warnings.append({
			"type": "generic_mainline_choice_text",
			"event_id": event_id,
			"choice_id": choice_id,
			"text": choice.text
		})
	if not has_effect and not has_story_state:
		warnings.append({
			"type": "mainline_choice_without_effect_or_flag",
			"event_id": event_id,
			"choice_id": choice_id,
			"text": choice.text
		})
	if choice.success_rate < 1.0 and choice.failure_effects.is_empty():
		warnings.append({
			"type": "risky_mainline_choice_without_failure_effect",
			"event_id": event_id,
			"choice_id": choice_id,
			"text": choice.text
		})
	if not has_gate and choice.success_rate < 1.0:
		warnings.append({
			"type": "risky_mainline_choice_without_stat_modifier",
			"event_id": event_id,
			"choice_id": choice_id,
			"text": choice.text
		})

func _choice_signature(choice) -> String:
	return JSON.stringify({
		"success": choice.success_effects,
		"failure": choice.failure_effects,
		"flag": choice.set_flag,
		"next": choice.next_event_id
	})

func _collect_required_flag(requirements: Dictionary, required_flags: Dictionary, source_id: String) -> void:
	if not requirements.has("flag"):
		return
	var flag_name: String = str(requirements["flag"])
	if not required_flags.has(flag_name):
		required_flags[flag_name] = []
	required_flags[flag_name].append(source_id)

func _parse_args() -> Dictionary:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		args = OS.get_cmdline_args()
	var parsed: Dictionary = {}
	var index: int = 0
	while index < args.size():
		var arg: String = str(args[index])
		if arg.begins_with("--"):
			var body: String = arg.substr(2)
			var equals_index: int = body.find("=")
			if equals_index >= 0:
				parsed[body.substr(0, equals_index)] = body.substr(equals_index + 1)
			elif index + 1 < args.size() and not str(args[index + 1]).begins_with("--"):
				parsed[body] = str(args[index + 1])
				index += 1
			else:
				parsed[body] = true
		index += 1
	return parsed

func _write_text(path: String, text: String) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file = FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(text)
		file.close()

func _global_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	if path.begins_with("/"):
		return path
	return ProjectSettings.globalize_path("res://%s" % path)
