extends SceneTree

# Deprecated shim — kept so callers that still reference
# `res://scripts/tools/RunBalanceSim.gd` get a clear error.
#
# The real runner is `study-in-germany/scripts/tools/RunSimulation.gd`.
# The Python CLI in this repo (`tools/run_balance_sim.sh`,
# `tools/run_gameplay_agent.py`) shells out to it directly via
# `godot4 --path ${GAME_PROJECT_PATH} -s res://scripts/tools/RunSimulation.gd`.

func _init() -> void:
	printerr(
		"RunBalanceSim.gd is deprecated. Use:\n"
		+ "  godot4 --headless --path <game_project> -s res://scripts/tools/RunSimulation.gd\n"
		+ "Set GAME_PROJECT_PATH to your study-in-germany checkout."
	)
	quit(1)