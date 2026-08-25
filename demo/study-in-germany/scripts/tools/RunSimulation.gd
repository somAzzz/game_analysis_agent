extends SceneTree

const SimulationEngineScript := preload("res://scripts/simulation/SimulationEngine.gd")
const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")
const ExamResolverScript := preload("res://scripts/simulation/ExamResolver.gd")
const EndingResolverScript := preload("res://scripts/simulation/EndingResolver.gd")
const PlayerPolicyScript := preload("res://scripts/policies/PlayerPolicy.gd")
const RandomPolicyScript := preload("res://scripts/policies/RandomPolicy.gd")
const BalancedPolicyScript := preload("res://scripts/policies/BalancedPolicy.gd")
const StudyPolicyScript := preload("res://scripts/policies/StudyPolicy.gd")
const WorkPolicyScript := preload("res://scripts/policies/WorkPolicy.gd")
const AdminPolicyScript := preload("res://scripts/policies/AdminPolicy.gd")
const SocialPolicyScript := preload("res://scripts/policies/SocialPolicy.gd")
const SlackerPolicyScript := preload("res://scripts/policies/SlackerPolicy.gd")
const SemesterReportBuilderScript := preload("res://scripts/simulation/SemesterReportBuilder.gd")

var run_records: Array = []
var weekly_state_rows: Array = []
var action_available_counts: Dictionary = {}
var action_pick_counts: Dictionary = {}
var event_trigger_counts: Dictionary = {}
var event_week_totals: Dictionary = {}
var ending_counts: Dictionary = {}
var game_state: Node
var data_registry: Node

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	game_state = root.get_node("/root/GameState")
	data_registry = root.get_node("/root/DataRegistry")
	var config: Dictionary = _parse_args()
	var runs: int = int(config.get("runs", 1))
	var base_seed: int = int(config.get("seed", 42))
	var policy_name: String = str(config.get("policy", "balanced"))
	var difficulty: String = str(config.get("difficulty", "normal"))
	var max_weeks: int = int(config.get("weeks", 20))
	var out_path: String = str(config.get("out", "reports/raw_runs.jsonl"))
	var out_file = _open_write(out_path)
	if out_file == null:
		printerr("Failed to open output: %s" % out_path)
		quit(1)
		return

	for run_index in range(runs):
		var run_id: int = run_index + 1
		var run_seed: int = base_seed + run_index
		var record: Dictionary = _simulate_run(run_id, run_seed, policy_name, difficulty, max_weeks, config)
		run_records.append(record)
		out_file.store_line(JSON.stringify(record))
	out_file.close()

	_write_metric_reports(out_path, policy_name, difficulty, runs)
	print("Simulation complete: %d runs -> %s" % [runs, _global_path(out_path)])
	quit(0)

func _simulate_run(run_id: int, run_seed: int, policy_name: String, difficulty: String, max_weeks: int, config: Dictionary) -> Dictionary:
	game_state.reset()
	game_state.configure_run({
		"run_id": run_id,
		"seed": run_seed,
		"policy": policy_name,
		"difficulty": difficulty,
		"content_version": str(config.get("content-version", game_state.CONTENT_VERSION)),
		"rules_version": str(config.get("rules-version", game_state.RULES_VERSION))
	})
	var scenario_id: String = str(config.get("scenario", ""))
	var scenario: Dictionary = _load_scenario(scenario_id)
	if not scenario.is_empty():
		game_state.apply_scenario(scenario)

	var policy = _make_policy(policy_name)
	var engine = SimulationEngineScript.new()
	var weekly_log: Array = []
	var action_sequence: Array = []
	var exam: Dictionary = {}
	var ending = null
	var guard_iterations: int = 0
	var guard_limit: int = maxi(60, max_weeks + 30)

	while game_state.week <= max_weeks and game_state.last_ending_id == "":
		guard_iterations += 1
		if guard_iterations > guard_limit:
			game_state.set_flag("pipeline_stalled")
			game_state.last_ending_id = "pipeline_stalled"
			game_state.add_log("模拟器保护：申请/注册管线长期没有推进，提前结束本次自动测试。")
			break
		var week: int = game_state.week
		var before_state: Dictionary = game_state.export_public_stats()
		var available_actions: Array = engine.get_available_actions(game_state)
		var available_action_ids: Array = _action_ids(available_actions)
		_count_available_actions(available_action_ids)

		var selected_action_ids: Array = policy.choose_actions(before_state, available_actions, SimulationEngineScript.MAX_ACTION_SLOTS)
		selected_action_ids = _fill_action_plan(selected_action_ids, available_actions, SimulationEngineScript.MAX_ACTION_SLOTS)
		selected_action_ids = engine.set_plan_from_action_ids(selected_action_ids)
		_count_picked_actions(selected_action_ids)

		var action_effects: Array = _describe_action_effects(selected_action_ids)
		var event = engine.resolve_week()
		var after_actions_and_drift: Dictionary = game_state.export_public_stats()
		var event_choice_id: String = ""
		var event_detail: Dictionary = {}

		if event != null:
			var available_choices: Array = _available_choices(event)
			var chosen_choice_index: int = policy.choose_event_option(after_actions_and_drift, event, available_choices)
			if chosen_choice_index >= 0 and chosen_choice_index < available_choices.size():
				var choice = available_choices[chosen_choice_index]
				var original_choice_index: int = _choice_index(event, choice)
				event_choice_id = _choice_id(event, choice, original_choice_index)
				event_detail = EventResolverScript.resolve_choice_detailed(event, choice, game_state)
				_count_event(event.id, week)

		var after_state: Dictionary = game_state.export_public_stats()
		game_state.record_week_snapshot("simulation_week_end")
		var week_record: Dictionary = {
			"week": week,
			"available_action_ids": available_action_ids,
			"selected_action_ids": selected_action_ids,
			"before_state": before_state,
			"action_effects": action_effects,
			"life_drift_effects": engine.last_life_drift_effects,
			"event_pool": engine.last_event_pool,
			"triggered_event_id": event.id if event != null else "",
			"event_choice_id": event_choice_id,
			"event_effects": event_detail.get("effects", {}),
			"event_success": event_detail.get("success", null),
			"after_actions_and_drift_state": after_actions_and_drift,
			"after_state": after_state
		}
		weekly_log.append(week_record)
		weekly_state_rows.append({
			"policy": policy_name,
			"difficulty": game_state.difficulty,
			"run_id": run_id,
			"seed": run_seed,
			"week": week,
			"state": after_state
		})
		action_sequence.append({
			"week": week,
			"actions": selected_action_ids,
			"event_choice": event_choice_id
		})

		if game_state.week >= max_weeks:
			exam = ExamResolverScript.resolve_exam(game_state)
			ending = EndingResolverScript.resolve_ending(data_registry.endings, game_state)
			if ending == null:
				ending = data_registry.get_ending_by_id("stable_start")
			game_state.last_ending_id = ending.id
			break
		engine.finish_week()

	var final_ending_id: String = game_state.last_ending_id
	if final_ending_id == "" and ending != null:
		final_ending_id = ending.id
	if final_ending_id == "":
		final_ending_id = "unknown"
	ending_counts[final_ending_id] = int(ending_counts.get(final_ending_id, 0)) + 1

	return {
		"run_id": run_id,
		"seed": run_seed,
		"policy": policy_name,
		"difficulty": game_state.difficulty,
		"scenario": scenario_id,
		"content_version": game_state.content_version,
		"rules_version": game_state.rules_version,
		"max_weeks": max_weeks,
		"final_ending_id": final_ending_id,
		"final_exam": exam,
		"final_report": SemesterReportBuilderScript.build_report(game_state, data_registry.actions),
		"final_state": game_state.export_state_snapshot(),
		"weekly_log": weekly_log,
		"action_sequence": action_sequence
	}

func _make_policy(policy_name: String):
	match policy_name:
		"random":
			return RandomPolicyScript.new()
		"study":
			return StudyPolicyScript.new()
		"work":
			return WorkPolicyScript.new()
		"admin":
			return AdminPolicyScript.new()
		"social":
			return SocialPolicyScript.new()
		"slacker":
			return SlackerPolicyScript.new()
		"balanced":
			return BalancedPolicyScript.new()
	return PlayerPolicyScript.new()

func _fill_action_plan(action_ids: Array, available_actions: Array, slots: int) -> Array:
	var selected: Array = action_ids.duplicate()
	var used_slots: int = 0
	for action_id in selected:
		var action = data_registry.get_action_by_id(str(action_id))
		if action != null:
			used_slots += action.cost_slots
	for action in available_actions:
		if used_slots >= slots:
			break
		if selected.has(action.id):
			continue
		if used_slots + action.cost_slots <= slots:
			selected.append(action.id)
			used_slots += action.cost_slots
	return selected

func _available_choices(event) -> Array:
	var choices: Array = []
	for choice in event.choices:
		if choice.is_available(game_state):
			choices.append(choice)
	return choices

func _action_ids(actions: Array) -> Array:
	var ids: Array = []
	for action in actions:
		ids.append(action.id)
	return ids

func _describe_action_effects(action_ids: Array) -> Array:
	var records: Array = []
	for action_id in action_ids:
		var action = data_registry.get_action_by_id(str(action_id))
		if action == null:
			continue
		var effects: Dictionary = action.effects.duplicate(true)
		effects["energy"] = int(effects.get("energy", 0)) - action.cost_energy
		effects["money"] = int(effects.get("money", 0)) - action.cost_money
		records.append({
			"action_id": action.id,
			"effects": effects
		})
	return records

func _choice_index(event, choice) -> int:
	for index in range(event.choices.size()):
		if event.choices[index] == choice:
			return index
	return -1

func _choice_id(event, choice, index: int) -> String:
	var safe_text: String = str(choice.text).to_lower().replace(" ", "_")
	return "%s.choice_%02d_%s" % [event.id, index + 1, safe_text]

func _count_available_actions(action_ids: Array) -> void:
	for action_id in action_ids:
		action_available_counts[action_id] = int(action_available_counts.get(action_id, 0)) + 1

func _count_picked_actions(action_ids: Array) -> void:
	for action_id in action_ids:
		action_pick_counts[action_id] = int(action_pick_counts.get(action_id, 0)) + 1

func _count_event(event_id: String, week: int) -> void:
	event_trigger_counts[event_id] = int(event_trigger_counts.get(event_id, 0)) + 1
	event_week_totals[event_id] = int(event_week_totals.get(event_id, 0)) + week

func _write_metric_reports(raw_out_path: String, policy_name: String, difficulty: String, runs: int) -> void:
	var base_dir: String = _global_path(raw_out_path).get_base_dir()
	_write_text(base_dir.path_join("ending_distribution.csv"), _ending_distribution_csv(policy_name, difficulty, runs))
	_write_text(base_dir.path_join("weekly_states.csv"), _weekly_states_csv())
	_write_text(base_dir.path_join("action_pick_rates.csv"), _action_pick_rates_csv(policy_name, difficulty))
	_write_text(base_dir.path_join("event_trigger_rates.csv"), _event_trigger_rates_csv(policy_name, difficulty, runs))
	_write_text(base_dir.path_join("summary.json"), JSON.stringify({
		"runs": runs,
		"policy": policy_name,
		"difficulty": difficulty,
		"raw_runs": _global_path(raw_out_path),
		"content_version": game_state.CONTENT_VERSION,
		"rules_version": game_state.RULES_VERSION
	}, "\t"))

func _ending_distribution_csv(policy_name: String, difficulty: String, runs: int) -> String:
	var lines: Array = ["policy,difficulty,ending_id,count,rate"]
	for ending_id in ending_counts.keys():
		var count: int = int(ending_counts[ending_id])
		lines.append("%s,%s,%s,%d,%.6f" % [policy_name, difficulty, ending_id, count, float(count) / max(1.0, float(runs))])
	return "\n".join(lines) + "\n"

func _weekly_states_csv() -> String:
	var lines: Array = ["policy,difficulty,run_id,seed,week,money,blocked_account_balance,energy,stress,loneliness,hunger,academic_progress,language,social,visa_progress,career_progress,gpa_score,aps_knowledge,aps_score,testdaf_reading,testdaf_listening,testdaf_writing,testdaf_speaking,current_week_work_hours,annual_work_half_days,university_tier"]
	for row in weekly_state_rows:
		var state: Dictionary = row["state"]
		lines.append("%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s" % [
			row["policy"],
			row["difficulty"],
			row["run_id"],
			row["seed"],
			row["week"],
			state["money"],
			state["blocked_account_balance"],
			state["energy"],
			state["stress"],
			state["loneliness"],
			state["hunger"],
			state["academic_progress"],
			state["language"],
			state["social"],
			state["visa_progress"],
			state["career_progress"],
			state["gpa_score"],
			state["aps_knowledge"],
			state["aps_score"],
			state["testdaf_reading"],
			state["testdaf_listening"],
			state["testdaf_writing"],
			state["testdaf_speaking"],
			state["current_week_work_hours"],
			state["annual_work_half_days"],
			_csv_escape(str(state["university_tier"]))
		])
	return "\n".join(lines) + "\n"

func _csv_escape(value: String) -> String:
	if value.contains(",") or value.contains("\"") or value.contains("\n"):
		return "\"%s\"" % value.replace("\"", "\"\"")
	return value

func _action_pick_rates_csv(policy_name: String, difficulty: String) -> String:
	var lines: Array = ["policy,difficulty,action_id,available_count,pick_count,pick_rate_when_available"]
	for action in data_registry.actions:
		var available_count: int = int(action_available_counts.get(action.id, 0))
		var pick_count: int = int(action_pick_counts.get(action.id, 0))
		var rate: float = float(pick_count) / max(1.0, float(available_count))
		lines.append("%s,%s,%s,%d,%d,%.6f" % [policy_name, difficulty, action.id, available_count, pick_count, rate])
	return "\n".join(lines) + "\n"

func _event_trigger_rates_csv(policy_name: String, difficulty: String, runs: int) -> String:
	var lines: Array = ["policy,difficulty,event_id,count,rate,avg_week"]
	for event in data_registry.events:
		var count: int = int(event_trigger_counts.get(event.id, 0))
		var rate: float = float(count) / max(1.0, float(runs))
		var avg_week: String = ""
		if count > 0:
			avg_week = "%.3f" % (float(event_week_totals.get(event.id, 0)) / float(count))
		lines.append("%s,%s,%s,%d,%.6f,%s" % [policy_name, difficulty, event.id, count, rate, avg_week])
	return "\n".join(lines) + "\n"

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

func _load_scenario(scenario_id: String) -> Dictionary:
	var scenario_path: String = scenario_id
	if not scenario_path.ends_with(".json"):
		scenario_path = "data/scenarios/%s.json" % scenario_id
	if not scenario_path.begins_with("res://") and not scenario_path.begins_with("user://") and not scenario_path.begins_with("/"):
		scenario_path = "res://%s" % scenario_path
	if not FileAccess.file_exists(scenario_path):
		return {}
	var file = FileAccess.open(scenario_path, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed

func _open_write(path: String):
	var global_path: String = _global_path(path)
	DirAccess.make_dir_recursive_absolute(global_path.get_base_dir())
	return FileAccess.open(global_path, FileAccess.WRITE)

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
