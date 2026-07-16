extends Node

signal state_changed
signal week_started(week: int)
signal week_resolved(summary: Array)
signal event_ready(event_def)
signal event_resolved(summary: String)
signal exam_resolved(result: Dictionary)
signal ending_resolved(ending_def)
signal log_added(message: String)

func add_log(message: String) -> void:
	log_added.emit(message)
