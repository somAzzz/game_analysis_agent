class_name EndingResolver
extends RefCounted

static func resolve_ending(endings: Array, state: Node):
	var matches: Array = []
	for ending in endings:
		if ending.matches(state):
			matches.append(ending)
	matches.sort_custom(func(a, b) -> bool: return a.priority > b.priority)
	if matches.is_empty():
		return null
	state.last_ending_id = matches.front().id
	return matches.front()
