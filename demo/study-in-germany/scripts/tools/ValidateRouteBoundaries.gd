extends SceneTree

const POLICIES := ["study", "work", "admin", "social", "slacker"]
const DEFAULT_REPORT_TEMPLATE := "reports/route_audit_%s.jsonl"
const DEFAULT_ADMIN_REPORT := "reports/route_audit_admin_after_fix.jsonl"
const TOP_ACTION_LIMIT := 8

const EXPECTED_TOP_ACTIONS := {
	"study": ["problem_set", "office_hour", "library_day"],
	"work": ["part_time_job", "mini_job_extra", "apply_howi", "cv_workshop"],
	"admin": ["write_email_practice", "international_office", "bank_account", "insurance_paperwork"],
	"social": ["language_tandem", "student_club", "date_night", "group_project"],
	"slacker": ["bilibili_rest", "cook_at_home", "go_running"]
}

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var config := _parse_args()
	var report_template := str(config.get("template", DEFAULT_REPORT_TEMPLATE))
	var min_runs := int(config.get("min-runs", 6))
	var errors: Array[String] = []
	var summary: Dictionary = {}
	var top3_by_policy: Dictionary = {}

	for policy in POLICIES:
		var path := _report_path(policy, report_template, config)
		var records := _read_jsonl(path)
		summary[policy] = _summarize(policy, records)
		_validate_policy(policy, records, summary[policy], min_runs, errors)
		top3_by_policy[policy] = _top_action_ids(summary[policy]["top_actions"], 3)

	_validate_cross_policy_top_actions(top3_by_policy, errors)

	var out_path := str(config.get("out", "reports/route_boundary_validation.json"))
	_write_text(_global_path(out_path), JSON.stringify({
		"errors": errors,
		"summary": summary,
		"top3_by_policy": top3_by_policy
	}, "\t"))

	if not errors.is_empty():
		for error in errors:
			printerr(error)
		print("Route boundary validation failed: %d errors -> %s" % [errors.size(), _global_path(out_path)])
		quit(1)
		return

	print("Route boundary validation complete: %d policies -> %s" % [POLICIES.size(), _global_path(out_path)])
	quit(0)

func _report_path(policy: String, template: String, config: Dictionary) -> String:
	var key := "%s-report" % policy
	if config.has(key):
		return str(config[key])
	if policy == "admin" and FileAccess.file_exists("res://%s" % DEFAULT_ADMIN_REPORT):
		return DEFAULT_ADMIN_REPORT
	return template % policy

func _read_jsonl(path: String) -> Array:
	var normalized := path
	if not normalized.begins_with("res://") and not normalized.begins_with("user://") and not normalized.begins_with("/"):
		normalized = "res://%s" % normalized
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

func _summarize(policy: String, records: Array) -> Dictionary:
	var ending_counts: Dictionary = {}
	var action_counts: Dictionary = {}
	var pipeline_stalled := 0
	var exam_passed := 0
	var money_total := 0
	var stress_total := 0
	var hunger_total := 0
	var academic_total := 0
	var social_total := 0
	var career_total := 0
	var work_half_days_total := 0

	for record in records:
		var ending_id := str(record.get("final_ending_id", "unknown"))
		ending_counts[ending_id] = int(ending_counts.get(ending_id, 0)) + 1
		if ending_id == "pipeline_stalled":
			pipeline_stalled += 1
		var final_exam: Dictionary = record.get("final_exam", {}) if record.get("final_exam", {}) is Dictionary else {}
		if bool(final_exam.get("passed", false)):
			exam_passed += 1
		var final_state: Dictionary = record.get("final_state", {}) if record.get("final_state", {}) is Dictionary else {}
		money_total += int(final_state.get("money", 0))
		stress_total += int(final_state.get("stress", 0))
		hunger_total += int(final_state.get("hunger", 0))
		academic_total += int(final_state.get("academic_progress", 0))
		social_total += int(final_state.get("social", 0))
		career_total += int(final_state.get("career_progress", 0))
		work_half_days_total += int(final_state.get("annual_work_half_days", 0))
		for week in record.get("action_sequence", []):
			if not week is Dictionary:
				continue
			for action_id in week.get("actions", []):
				action_counts[str(action_id)] = int(action_counts.get(str(action_id), 0)) + 1

	var run_count := records.size()
	return {
		"policy": policy,
		"runs": run_count,
		"ending_counts": ending_counts,
		"pipeline_stalled": pipeline_stalled,
		"exam_passed": exam_passed,
		"avg_money": _avg_int(money_total, run_count),
		"avg_stress": _avg_int(stress_total, run_count),
		"avg_hunger": _avg_int(hunger_total, run_count),
		"avg_academic": _avg_int(academic_total, run_count),
		"avg_social": _avg_int(social_total, run_count),
		"avg_career": _avg_int(career_total, run_count),
		"avg_work_half_days": _avg_int(work_half_days_total, run_count),
		"top_actions": _top_action_entries(action_counts, TOP_ACTION_LIMIT)
	}

func _validate_policy(policy: String, records: Array, summary: Dictionary, min_runs: int, errors: Array[String]) -> void:
	if records.size() < min_runs:
		errors.append("%s has %d runs, expected at least %d" % [policy, records.size(), min_runs])
	if int(summary.get("pipeline_stalled", 0)) > 0:
		errors.append("%s has pipeline_stalled runs: %d" % [policy, int(summary["pipeline_stalled"])])
	var top_action_ids := _top_action_ids(summary["top_actions"], TOP_ACTION_LIMIT)
	var expected: Array = EXPECTED_TOP_ACTIONS.get(policy, [])
	for action_id in expected:
		if top_action_ids.has(action_id):
			return
	errors.append("%s top %d actions do not include any expected route action %s; got %s" % [policy, TOP_ACTION_LIMIT, ",".join(expected), ",".join(top_action_ids)])

func _validate_cross_policy_top_actions(top3_by_policy: Dictionary, errors: Array[String]) -> void:
	var action_to_policies: Dictionary = {}
	for policy in top3_by_policy.keys():
		for action_id in top3_by_policy[policy]:
			if not action_to_policies.has(action_id):
				action_to_policies[action_id] = []
			action_to_policies[action_id].append(policy)
	for action_id in action_to_policies.keys():
		var policies: Array = action_to_policies[action_id]
		if policies.size() >= POLICIES.size():
			errors.append("action %s appears in every policy top 3" % action_id)

func _top_action_entries(counts: Dictionary, limit: int) -> Array:
	var entries: Array = []
	for action_id in counts.keys():
		entries.append({"action_id": action_id, "count": int(counts[action_id])})
	entries.sort_custom(func(a, b): return int(a["count"]) > int(b["count"]))
	return entries.slice(0, mini(limit, entries.size()))

func _top_action_ids(entries: Array, limit: int) -> Array:
	var ids: Array[String] = []
	for index in range(mini(limit, entries.size())):
		ids.append(str(entries[index].get("action_id", "")))
	return ids

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
