extends Node

var rng := RandomNumberGenerator.new()
var current_seed: int = 0

func _ready() -> void:
	randomize_seed()

func randomize_seed() -> void:
	rng.randomize()
	current_seed = int(rng.randi() & 0x7fffffff)
	rng.seed = current_seed

func set_seed(seed_value: int) -> void:
	current_seed = seed_value
	rng.seed = seed_value

func get_rng_state() -> int:
	return rng.state

func set_rng_state(state_value: int) -> void:
	rng.state = state_value

func rand_float() -> float:
	return rng.randf()

func rand_float_range(min_value: float, max_value: float) -> float:
	return rng.randf_range(min_value, max_value)

func rand_int(min_value: int, max_value: int) -> int:
	return rng.randi_range(min_value, max_value)

func pick_weighted(items: Array, weight_func: Callable):
	if items.is_empty():
		return null
	var total := 0.0
	for item in items:
		total += maxf(0.0, float(weight_func.call(item)))
	if total <= 0.0:
		return items.front()
	var roll := rand_float() * total
	var current := 0.0
	for item in items:
		current += maxf(0.0, float(weight_func.call(item)))
		if roll <= current:
			return item
	return items.back()
