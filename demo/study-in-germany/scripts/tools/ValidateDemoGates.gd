extends SceneTree

const SUCCESS_ENDINGS := {
	"stable_start": true,
	"high_pressure_top_student": true,
	"social_connector": true,
	"career_launch": true,
	"work_warrior": true
}

const CRISIS_OR_SURVIVAL_ENDINGS := {
	"admin_collapse": true,
	"academic_failure": true,
	"burnout_pause": true,
	"cashflow_collapse": true,
	"forced_departure": true,
	"living_imbalance": true,
	"registration_failure": true,
	"survival_struggle": true,
	"work_law_trouble": true
}

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var config := _parse_args()
	var errors: Array[String] = []
	var warnings: Array[String] = []
	var summary: Dictionary = {}

	var normal_records := _read_jsonl(str(config.get("normal", "reports/gates_balanced_normal.jsonl")))
	var realistic_records := _read_jsonl(str(config.get("realistic", "reports/gates_balanced_realistic.jsonl")))
	var low_money_records := _read_jsonl(str(config.get("low-money", "reports/gates_balanced_low_money.jsonl")))
	var content_validation := _read_json(str(config.get("content-validation", "reports/content_validation.json")))
	var route_validation := _read_json(str(config.get("route-validation", "reports/route_boundary_validation.json")))
	var risk_validation := _read_json(str(config.get("risk-validation", "reports/risk_guidance_validation.json")))

	var min_runs := int(config.get("min-runs", 12))
	var max_top_action_share := float(config.get("max-top-action-share", 0.15))
	var min_normal_ending_types := int(config.get("min-normal-ending-types", 4))
	var min_low_money_crisis_rate := float(config.get("min-low-money-crisis-rate", 0.70))
	var max_content_warnings := int(config.get("max-content-warnings", 20))

	summary["normal"] = _summarize_runs(normal_records)
	summary["realistic"] = _summarize_runs(realistic_records)
	summary["low_money"] = _summarize_runs(low_money_records)
	summary["content_validation"] = content_validation
	summary["route_validation"] = route_validation
	summary["risk_validation"] = risk_validation

	_validate_content_report(content_validation, max_content_warnings, errors, warnings)
	_validate_report("normal", normal_records, min_runs, errors)
	_validate_report("realistic", realistic_records, min_runs, errors)
	_validate_report("low_money", low_money_records, min_runs, errors)
	_validate_no_bad_success("normal", normal_records, errors)
	_validate_no_bad_success("realistic", realistic_records, errors)
	_validate_no_bad_success("low_money", low_money_records, errors)
	_validate_top_action_share("normal", summary["normal"], max_top_action_share, errors)
	_validate_top_action_share("realistic", summary["realistic"], max_top_action_share, errors)
	_validate_normal_ending_variety(summary["normal"], min_normal_ending_types, errors)
	_validate_low_money_crisis_rate(summary["low_money"], min_low_money_crisis_rate, errors)
	_validate_route_report(route_validation, errors, warnings)
	_validate_risk_report(risk_validation, errors, warnings)

	var out_path := str(config.get("out", "reports/demo_gate_validation.json"))
	_write_text(_global_path(out_path), JSON.stringify({
		"errors": errors,
		"warnings": warnings,
		"summary": summary,
		"gates": {
			"min_runs": min_runs,
			"max_top_action_share": max_top_action_share,
			"min_normal_ending_types": min_normal_ending_types,
			"min_low_money_crisis_rate": min_low_money_crisis_rate,
			"max_content_warnings": max_content_warnings
		}
	}, "\t"))

	if not errors.is_empty():
		for error in errors:
			printerr(error)
		for warning in warnings:
			print("Warning: %s" % warning)
		print("Demo gate validation failed: %d errors -> %s" % [errors.size(), _global_path(out_path)])
		quit(1)
		return

	for warning in warnings:
		print("Warning: %s" % warning)
	print("Demo gate validation complete: normal=%d runs, realistic=%d runs, low_money=%d runs -> %s" % [
		normal_records.size(),
		realistic_records.size(),
		low_money_records.size(),
		_global_path(out_path)
	])
	quit(0)

func _validate_report(label: String, records: Array, min_runs: int, errors: Array[String]) -> void:
	if records.size() < min_runs:
		errors.append("%s report has %d runs, expected at least %d" % [label, records.size(), min_runs])
	for record in records:
		if str(record.get("final_ending_id", "")) == "pipeline_stalled":
			errors.append("%s run %s stalled in the pipeline" % [label, str(record.get("run_id", "?"))])

func _validate_content_report(content_validation: Dictionary, max_warnings: int, errors: Array[String], warnings: Array[String]) -> void:
	if content_validation.is_empty():
		warnings.append("content validation report not found; content technical gate was not checked")
		return
	var content_errors: Array = content_validation.get("errors", [])
	if not content_errors.is_empty():
		for error in content_errors:
			errors.append("content validation: %s" % str(error))
	var content_warnings: Array = content_validation.get("warnings", [])
	if content_warnings.size() > max_warnings:
		errors.append("content validation has %d warnings, expected at most %d" % [content_warnings.size(), max_warnings])

func _validate_no_bad_success(label: String, records: Array, errors: Array[String]) -> void:
	for record in records:
		var ending_id := str(record.get("final_ending_id", ""))
		if not SUCCESS_ENDINGS.has(ending_id):
			continue
		var final_state: Dictionary = _dict(record.get("final_state", {}))
		var money := int(final_state.get("money", 0))
		var arrears := int(final_state.get("arrears_amount", 0))
		var hunger := int(final_state.get("hunger", 0))
		var stress := int(final_state.get("stress", 0))
		if arrears >= 1000 and hunger > 80 and stress > 80:
			errors.append("%s run %s resolved to success %s while money=%d arrears=%d hunger=%d stress=%d" % [
				label,
				str(record.get("run_id", "?")),
				ending_id,
				money,
				arrears,
				hunger,
				stress
			])

func _validate_top_action_share(label: String, summary: Dictionary, max_share: float, errors: Array[String]) -> void:
	var top_actions: Array = summary.get("top_actions", [])
	if top_actions.is_empty():
		errors.append("%s report has no action picks" % label)
		return
	var top := _dict(top_actions[0])
	var share := float(top.get("share", 0.0))
	if share > max_share:
		errors.append("%s top action %s share %.3f exceeds %.3f" % [label, str(top.get("action_id", "")), share, max_share])

func _validate_normal_ending_variety(summary: Dictionary, min_types: int, errors: Array[String]) -> void:
	var ending_counts: Dictionary = summary.get("ending_counts", {})
	if ending_counts.keys().size() < min_types:
		errors.append("normal scenario has %d ending types, expected at least %d" % [ending_counts.keys().size(), min_types])

func _validate_low_money_crisis_rate(summary: Dictionary, min_rate: float, errors: Array[String]) -> void:
	var run_count := int(summary.get("runs", 0))
	if run_count <= 0:
		errors.append("low_money report is empty")
		return
	var crisis_count := 0
	var ending_counts: Dictionary = summary.get("ending_counts", {})
	for ending_id in ending_counts.keys():
		if CRISIS_OR_SURVIVAL_ENDINGS.has(str(ending_id)):
			crisis_count += int(ending_counts[ending_id])
	var rate := float(crisis_count) / float(run_count)
	if rate < min_rate:
		errors.append("low_money crisis/survival rate %.3f is below %.3f" % [rate, min_rate])

func _validate_route_report(route_validation: Dictionary, errors: Array[String], warnings: Array[String]) -> void:
	if route_validation.is_empty():
		warnings.append("route validation report not found; route boundary gate was not checked")
		return
	var route_errors: Array = route_validation.get("errors", [])
	if not route_errors.is_empty():
		for error in route_errors:
			errors.append("route boundary: %s" % str(error))

func _validate_risk_report(risk_validation: Dictionary, errors: Array[String], warnings: Array[String]) -> void:
	if risk_validation.is_empty():
		warnings.append("risk guidance validation report not found; top risk experience gate was not checked")
		return
	var risk_errors: Array = risk_validation.get("errors", [])
	if not risk_errors.is_empty():
		for error in risk_errors:
			errors.append("risk guidance: %s" % str(error))

func _summarize_runs(records: Array) -> Dictionary:
	var ending_counts: Dictionary = {}
	var action_counts: Dictionary = {}
	var bad_success_count := 0
	var final_money_total := 0
	var final_stress_total := 0
	var final_hunger_total := 0

	for record in records:
		var ending_id := str(record.get("final_ending_id", "unknown"))
		ending_counts[ending_id] = int(ending_counts.get(ending_id, 0)) + 1
		var final_state: Dictionary = _dict(record.get("final_state", {}))
		final_money_total += int(final_state.get("money", 0))
		final_stress_total += int(final_state.get("stress", 0))
		final_hunger_total += int(final_state.get("hunger", 0))
		if SUCCESS_ENDINGS.has(ending_id) and int(final_state.get("arrears_amount", 0)) >= 1000 and int(final_state.get("hunger", 0)) > 80 and int(final_state.get("stress", 0)) > 80:
			bad_success_count += 1
		for week in record.get("action_sequence", []):
			if not week is Dictionary:
				continue
			for action_id in week.get("actions", []):
				action_counts[str(action_id)] = int(action_counts.get(str(action_id), 0)) + 1

	var total_actions := 0
	for action_id in action_counts.keys():
		total_actions += int(action_counts[action_id])

	return {
		"runs": records.size(),
		"ending_counts": ending_counts,
		"ending_type_count": ending_counts.keys().size(),
		"bad_success_count": bad_success_count,
		"avg_money": _avg_int(final_money_total, records.size()),
		"avg_stress": _avg_int(final_stress_total, records.size()),
		"avg_hunger": _avg_int(final_hunger_total, records.size()),
		"top_actions": _top_actions(action_counts, total_actions, 8)
	}

func _top_actions(counts: Dictionary, total: int, limit: int) -> Array:
	var entries: Array = []
	for action_id in counts.keys():
		var count := int(counts[action_id])
		entries.append({
			"action_id": action_id,
			"count": count,
			"share": float(count) / max(1.0, float(total))
		})
	entries.sort_custom(func(a, b): return int(a["count"]) > int(b["count"]))
	return entries.slice(0, mini(limit, entries.size()))

func _read_jsonl(path: String) -> Array:
	var normalized := _resource_path(path)
	var file = FileAccess.open(normalized, FileAccess.READ)
	if file == null:
		return []
	var records: Array = []
	while not file.eof_reached():
		var line := file.get_line().strip_edges()
		if line == "":
			continue
		var parsed = JSON.parse_string(line)
		if parsed is Dictionary:
			records.append(parsed)
	return records

func _read_json(path: String) -> Dictionary:
	var normalized := _resource_path(path)
	if not FileAccess.file_exists(normalized):
		return {}
	var file = FileAccess.open(normalized, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	if parsed is Dictionary:
		return parsed
	return {}

func _dict(value) -> Dictionary:
	if value is Dictionary:
		return value
	return {}

func _avg_int(total: int, count: int) -> int:
	return int(round(float(total) / max(1.0, float(count))))

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

func _resource_path(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://") or path.begins_with("/"):
		return path
	return "res://%s" % path

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
