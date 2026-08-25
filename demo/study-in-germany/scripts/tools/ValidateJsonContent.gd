extends SceneTree

const DataLoaderScript := preload("res://scripts/data/DataLoader.gd")

const EVENT_JSON_PATHS := [
	"res://data/events/application_events.json",
	"res://data/events/admin_events.json",
	"res://data/events/academic_events.json",
	"res://data/events/life_events.json",
	"res://data/events/work_events.json",
	"res://data/events/relationship_events.json",
	"res://data/events/random_events.json"
]

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

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var actions := DataLoaderScript.load_actions("res://data/actions/generated_actions.json")
	var events := DataLoaderScript.load_events_from_paths(EVENT_JSON_PATHS)
	var endings := DataLoaderScript.load_endings("res://data/endings/generated_endings.json")
	var characters := DataLoaderScript.load_characters("res://data/characters/npcs.json")
	var errors: Array[String] = []
	_validate_ids(actions, "action", errors)
	var event_ids := _validate_ids(events, "event", errors)
	_validate_mainline_ids_exist(event_ids, errors)
	_validate_ids(endings, "ending", errors)
	_validate_ids(characters, "character", errors)
	for event in events:
		if event.choices.size() < 1:
			errors.append("event %s has no choices" % event.id)
		if MAINLINE_EVENT_IDS.has(event.id) and event.choices.size() < 4:
			errors.append("mainline event %s should have 4 choices, got %d" % [event.id, event.choices.size()])
	_validate_event_source_order(events, errors)
	if not errors.is_empty():
		for error in errors:
			printerr(error)
		quit(1)
		return
	print("JSON content validation complete: %d actions, %d events, %d endings, %d characters" % [
		actions.size(),
		events.size(),
		endings.size(),
		characters.size()
	])
	quit(0)

func _validate_ids(items: Array, item_type: String, errors: Array[String]) -> Dictionary:
	var ids: Dictionary = {}
	for item in items:
		if str(item.id) == "":
			errors.append("%s has empty id" % item_type)
			continue
		if ids.has(item.id):
			errors.append("%s duplicate id %s" % [item_type, item.id])
		ids[item.id] = true
	return ids

func _validate_mainline_ids_exist(event_ids: Dictionary, errors: Array[String]) -> void:
	for event_id in MAINLINE_EVENT_IDS.keys():
		if not event_ids.has(event_id):
			errors.append("missing mainline event id: %s" % event_id)

func _validate_event_source_order(events: Array, errors: Array[String]) -> void:
	var seen: Dictionary = {}
	for event in events:
		var source_order := int(event.source_order)
		if source_order < 0 or source_order >= events.size():
			errors.append("event %s has out-of-range source_order %d" % [event.id, source_order])
		if seen.has(source_order):
			errors.append("event source_order duplicate %d for %s and %s" % [source_order, seen[source_order], event.id])
		seen[source_order] = event.id
	for index in range(events.size()):
		if not seen.has(index):
			errors.append("event source_order missing %d" % index)
