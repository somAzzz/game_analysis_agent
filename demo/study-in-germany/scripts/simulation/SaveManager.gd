class_name SaveManager
extends RefCounted

const SAVE_PATH := "user://savegame.json"

static func save_game(state: Node) -> bool:
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		return false
	file.store_string(JSON.stringify(state.to_save_data(), "\t"))
	return true

static func load_game(state: Node) -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		return false
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		return false
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return false
	state.from_save_data(parsed)
	return true

static func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)
