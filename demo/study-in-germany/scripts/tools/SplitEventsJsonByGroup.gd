extends SceneTree

const DataLoaderScript := preload("res://scripts/data/DataLoader.gd")

const SOURCE_PATH := "res://data/events/generated_events.json"
const GROUP_PATHS := {
	"application": "res://data/events/application_events.json",
	"admin": "res://data/events/admin_events.json",
	"academic": "res://data/events/academic_events.json",
	"life": "res://data/events/life_events.json",
	"work": "res://data/events/work_events.json",
	"relationship": "res://data/events/relationship_events.json",
	"random": "res://data/events/random_events.json"
}

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var records := DataLoaderScript.load_json_array(SOURCE_PATH)
	var groups := {}
	for group_name in GROUP_PATHS.keys():
		groups[group_name] = []

	for index in range(records.size()):
		var record = records[index]
		if not record is Dictionary:
			continue
		var cloned: Dictionary = record.duplicate(true)
		cloned["source_order"] = index
		var group_name := _group_for_event(cloned)
		groups[group_name].append(cloned)

	for group_name in GROUP_PATHS.keys():
		_write_json(str(GROUP_PATHS[group_name]), groups[group_name])

	print("Split events by group: application=%d, admin=%d, academic=%d, life=%d, work=%d, relationship=%d, random=%d" % [
		groups["application"].size(),
		groups["admin"].size(),
		groups["academic"].size(),
		groups["life"].size(),
		groups["work"].size(),
		groups["relationship"].size(),
		groups["random"].size()
	])
	quit(0)

func _group_for_event(record: Dictionary) -> String:
	var event_id := str(record.get("id", "")).to_lower()
	var title := str(record.get("title", "")).to_lower()
	var body := str(record.get("body", "")).to_lower()
	var trigger: Dictionary = record.get("trigger", {}) if record.get("trigger", {}) is Dictionary else {}
	var text := "%s %s %s %s" % [event_id, title, body, JSON.stringify(trigger).to_lower()]

	if _has_any(text, ["aps", "testdaf", "testas", "university", "application", "申请", "审核", "语言班", "入学语言"]):
		return "application"
	if _has_any(text, ["visa", "termin", "anmeldung", "registration", "insurance", "bank", "blocked", "tax_id", "city_registration", "mailbox", "letter", "paperwork", "居留", "签证", "注册", "保险", "银行", "冻结账户", "外管局", "市政厅"]):
		return "admin"
	if _has_any(text, ["exam", "klausur", "lecture", "academic", "course", "moodle", "presentation", "tutorium", "library", "prof", "office_hour", "hausarbeit", "plagiarism", "group_invite", "课程", "考试", "课堂", "教授", "论文", "图书馆", "小组"]):
		return "academic"
	if _has_any(text, ["job", "work", "hiwi", "boss", "payslip", "career", "linkedin", "cv", "hackathon", "scholarship", "打工", "工时", "工资", "老板", "职业", "简历", "奖学金", "黑工"]):
		return "work"
	if _has_any(text, ["romance", "date", "partner", "scam", "parents", "family", "anna", "li_", "cem", "relationship", "恋爱", "约会", "对象", "感情", "父母", "家庭"]):
		return "relationship"
	if _has_any(text, ["hunger", "food", "mensa", "dinner", "wg", "roommate", "flat", "rent", "grocery", "sick", "bike", "train", "sunday", "heating", "laundry", "winter", "christmas", "lonely", "mental", "homesick", "drink", "spati", "neighbor", "饥饿", "食堂", "吃饭", "喝酒", "做饭", "房租", "感冒", "孤独", "室友", "邻居"]):
		return "life"
	return "random"

func _has_any(text: String, needles: Array) -> bool:
	for needle in needles:
		if text.contains(str(needle).to_lower()):
			return true
	return false

func _write_json(path: String, records: Array) -> void:
	var global_path := ProjectSettings.globalize_path(path)
	DirAccess.make_dir_recursive_absolute(global_path.get_base_dir())
	var file = FileAccess.open(global_path, FileAccess.WRITE)
	if file == null:
		push_error("Cannot write %s" % path)
		return
	file.store_string(JSON.stringify({"items": records}, "\t"))
	file.store_string("\n")
	file.close()
