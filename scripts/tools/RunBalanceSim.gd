extends SceneTree

const RUNS_DEFAULT := 1000
const MAX_WEEKS := 20

var runs := RUNS_DEFAULT
var policy_name := "balanced"
var seed_base := 42
var out_path := "user://balance_runs.jsonl"


func _init() -> void:
	_parse_args()

	var file := FileAccess.open(out_path, FileAccess.WRITE)
	if file == null:
		push_error("Cannot open output file: %s" % out_path)
		quit(1)
		return

	for i in range(runs):
		var result := _run_single_game(i)
		file.store_line(JSON.stringify(result))

	file.close()
	print("Balance simulation finished: %s runs -> %s" % [runs, out_path])
	quit(0)


func _parse_args() -> void:
	for arg in OS.get_cmdline_args():
		if arg.begins_with("--runs="):
			runs = int(arg.get_slice("=", 1))
		elif arg.begins_with("--policy="):
			policy_name = arg.get_slice("=", 1)
		elif arg.begins_with("--seed="):
			seed_base = int(arg.get_slice("=", 1))
		elif arg.begins_with("--out="):
			out_path = arg.get_slice("=", 1)


func _run_single_game(run_index: int) -> Dictionary:
	seed(seed_base + run_index)

	# Replace these preload paths with the real game project paths.
	# var state = preload("res://autoload/GameState.gd").new()
	# var registry = preload("res://autoload/DataRegistry.gd").new()
	# var engine = preload("res://scripts/simulation/SimulationEngine.gd").new()
	# engine.start_new_run(seed_base + run_index)

	var weekly_log := []

	# Integration placeholder. Once SimulationEngine exposes a pure simulation API,
	# loop until engine.is_finished(), select actions, and append snapshots.
	for week in range(1, MAX_WEEKS + 1):
		weekly_log.append({
			"week": week,
			"actions": [],
			"event_id": "",
			"choice_id": "",
			"state": _empty_state(week)
		})

	return {
		"run_id": run_index,
		"policy": policy_name,
		"seed": seed_base + run_index,
		"ending_id": "placeholder",
		"final_state": _empty_state(MAX_WEEKS),
		"weekly_log": weekly_log
	}


func _select_actions(policy: String, actions: Array, state) -> Array:
	match policy:
		"random":
			return _random_actions(actions, 4)
		"study":
			return _weighted_actions(actions, state, {"study": 5.0, "german": 1.5, "rest": 1.0})
		"money":
			return _weighted_actions(actions, state, {"work": 5.0, "study": 1.0, "rest": 1.0})
		"balanced":
			return _balanced_actions(actions, state)
		_:
			return _random_actions(actions, 4)


func _random_actions(actions: Array, count: int) -> Array:
	var selected := actions.duplicate()
	selected.shuffle()
	return selected.slice(0, min(count, selected.size()))


func _weighted_actions(actions: Array, _state, _weights: Dictionary) -> Array:
	# Replace with scoring against your ActionDef tags/effects.
	return _random_actions(actions, 4)


func _balanced_actions(actions: Array, state) -> Array:
	# Replace with a scoring function that responds to low money, low admin,
	# high stress, low academic, and low energy.
	return _weighted_actions(actions, state, {})


func _empty_state(week: int) -> Dictionary:
	return {
		"week": week,
		"money": 0,
		"energy": 0,
		"stress": 0,
		"loneliness": 0,
		"academic": 0,
		"german": 0,
		"social": 0,
		"admin": 0,
		"career": 0
	}
