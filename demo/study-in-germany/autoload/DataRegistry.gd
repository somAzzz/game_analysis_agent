extends Node

const ActionDefScript := preload("res://scripts/data/ActionDef.gd")
const EventChoiceDefScript := preload("res://scripts/data/EventChoiceDef.gd")
const EventDefScript := preload("res://scripts/data/EventDef.gd")
const CharacterDefScript := preload("res://scripts/data/CharacterDef.gd")
const EndingDefScript := preload("res://scripts/data/EndingDef.gd")
const DataLoaderScript := preload("res://scripts/data/DataLoader.gd")

const ACTION_JSON_PATH := "res://data/actions/generated_actions.json"
const EVENT_JSON_PATH := "res://data/events/generated_events.json"
const EVENT_JSON_PATHS := [
	"res://data/events/application_events.json",
	"res://data/events/admin_events.json",
	"res://data/events/academic_events.json",
	"res://data/events/life_events.json",
	"res://data/events/work_events.json",
	"res://data/events/relationship_events.json",
	"res://data/events/random_events.json"
]
const CHARACTER_JSON_PATH := "res://data/characters/npcs.json"
const ENDING_JSON_PATH := "res://data/endings/generated_endings.json"

var actions: Array = []
var events: Array = []
var characters: Array = []
var endings: Array = []
var action_source: String = "hardcoded"
var event_source: String = "hardcoded"
var character_source: String = "hardcoded"
var ending_source: String = "hardcoded"

func _ready() -> void:
	randomize()
	if not _load_characters_from_json():
		_build_characters()
	if not _load_actions_from_json():
		_build_actions()
	if not _load_events_from_json():
		_build_events()
	if not _load_endings_from_json():
		_build_endings()

func get_action_by_id(action_id: String):
	for action in actions:
		if action.id == action_id:
			return action
	return null

func get_ending_by_id(ending_id: String):
	for ending in endings:
		if ending.id == ending_id:
			return ending
	return null

func _action(id: String, name: String, description: String, energy: int, money: int, effects: Dictionary, tags: Array, requirements: Dictionary = {}, risks: Array = [], set_flag: String = ""):
	var action = ActionDefScript.new()
	action.id = id
	action.name = name
	action.description = description
	action.cost_energy = energy
	action.cost_money = money
	action.cost_slots = 1
	action.effects = effects
	action.tags = tags
	action.requirements = requirements
	action.risk_tags = risks
	action.set_flag = set_flag
	return action

func _choice(text: String, success_effects: Dictionary, failure_effects: Dictionary = {}, success_rate: float = 1.0, requirements: Dictionary = {}, set_flag: String = "", success_modifiers: Dictionary = {}):
	var choice = EventChoiceDefScript.new()
	choice.text = text
	choice.success_effects = success_effects
	choice.failure_effects = failure_effects if not failure_effects.is_empty() else _default_failure_effects(success_effects)
	choice.success_rate = success_rate
	choice.requirements = requirements
	choice.set_flag = set_flag
	choice.success_modifiers = success_modifiers if not success_modifiers.is_empty() else _infer_success_modifiers(success_effects, choice.failure_effects)
	return choice

func _default_failure_effects(success_effects: Dictionary) -> Dictionary:
	var failure := {"stress": 2}
	for key in success_effects.keys():
		var value := int(success_effects[key])
		match str(key):
			"academic_progress", "language", "social", "visa_progress", "career_progress", "gpa_score", "aps_knowledge", "aps_score":
				if value > 0:
					failure[str(key)] = -1
			"money":
				if value >= 0:
					failure["money"] = -35
				else:
					failure["money"] = value
			"energy":
				if value >= 0:
					failure["energy"] = -4
				else:
					failure["energy"] = value
			"stress":
				if value < 0:
					failure["stress"] = 4
			"loneliness":
				if value < 0:
					failure["loneliness"] = 2
			"hunger":
				if value < 0:
					failure["hunger"] = 6
	return failure

func _event(id: String, title: String, body: String, event_type: String, trigger: Dictionary, choices: Array, weight: float = 1.0, repeatable: bool = false):
	var event = EventDefScript.new()
	event.id = id
	event.title = title
	event.body = body
	event.event_type = event_type
	event.trigger = trigger
	event.choices = _complete_event_choices(id, title, trigger, choices)
	event.weight = weight
	event.repeatable = repeatable
	return event

func _infer_success_modifiers(success_effects: Dictionary, failure_effects: Dictionary) -> Dictionary:
	var modifiers := {"energy": 0.001, "stress": -0.002}
	if success_effects.has("academic_progress"):
		modifiers["academic_progress"] = 0.003
	if success_effects.has("language") or success_effects.has("visa_progress"):
		modifiers["language"] = 0.003
	if success_effects.has("social") or success_effects.has("loneliness"):
		modifiers["social"] = 0.003
	if success_effects.has("hunger"):
		modifiers["energy"] = 0.002
		modifiers["money"] = 0.001
	if success_effects.has("career_progress"):
		modifiers["career_progress"] = 0.003
	if success_effects.has("aps_knowledge") or success_effects.has("aps_score"):
		modifiers["aps_knowledge"] = 0.003
		modifiers["language"] = float(modifiers.get("language", 0.0)) + 0.001
	if success_effects.has("money"):
		modifiers["money"] = 0.001
	if failure_effects.has("stress"):
		modifiers["stress"] = -0.003
	return modifiers

func _complete_event_choices(event_id: String, title: String, trigger: Dictionary, choices: Array) -> Array:
	var completed := choices.duplicate()
	var focus := _event_focus(event_id, title, trigger, choices)
	var templates := [
		_build_balanced_choice("稳妥处理", focus),
		_build_balanced_choice("寻求帮助", focus),
		_build_balanced_choice("冒险推进", focus),
		_build_balanced_choice("暂时回避", focus)
	]
	var template_index := 0
	while completed.size() < 4 and template_index < templates.size():
		completed.append(templates[template_index])
		template_index += 1
	if completed.size() > 4:
		completed = completed.slice(0, 4)
	return completed

func _event_focus(event_id: String, title: String, trigger: Dictionary, choices: Array) -> String:
	var text := "%s %s" % [event_id, title]
	if text.contains("aps") or text.contains("APS") or text.contains("TestAS") or text.contains("审核") or text.contains("申请季"):
		return "aps_knowledge"
	if text.contains("exam") or text.contains("lecture") or text.contains("moodle") or text.contains("presentation") or text.contains("academic") or text.contains("Klausur") or text.contains("课程") or text.contains("考试") or text.contains("课堂") or text.contains("论文") or text.contains("图书馆") or text.contains("实验"):
		return "academic_progress"
	if text.contains("visa") or text.contains("termin") or text.contains("registration") or text.contains("anmeldung") or text.contains("insurance") or text.contains("bank") or text.contains("市政厅") or text.contains("行政") or text.contains("签证") or text.contains("保险") or text.contains("银行") or text.contains("注册"):
		return "visa_progress"
	if text.contains("job") or text.contains("career") or text.contains("hiwi") or text.contains("linkedin") or text.contains("cv") or text.contains("Hackathon") or text.contains("职业") or text.contains("简历") or text.contains("招聘") or text.contains("打工"):
		return "career_progress"
	if text.contains("money") or text.contains("rent") or text.contains("fee") or text.contains("refund") or text.contains("blocked") or text.contains("房租") or text.contains("费用") or text.contains("退款") or text.contains("账户") or text.contains("工资") or text.contains("金钱"):
		return "money"
	if text.contains("language") or text.contains("deutsch") or text.contains("accent") or text.contains("DeepL") or text.contains("德语") or text.contains("口音") or text.contains("邮件"):
		return "language"
	if text.contains("wg") or text.contains("roommate") or text.contains("anna") or text.contains("li_") or text.contains("social") or text.contains("potluck") or text.contains("室友") or text.contains("同学") or text.contains("聚餐") or text.contains("邻居") or text.contains("社团"):
		return "social"
	if text.contains("date") or text.contains("romance") or text.contains("partner") or text.contains("恋爱") or text.contains("感情") or text.contains("约会") or text.contains("对象"):
		return "social"
	if text.contains("hunger") or text.contains("mensa") or text.contains("dinner") or text.contains("food") or text.contains("饥饿") or text.contains("吃饭") or text.contains("喝酒") or text.contains("食堂") or text.contains("做饭"):
		return "hunger"
	if text.contains("mental") or text.contains("lonely") or text.contains("burnout") or text.contains("sick") or text.contains("心理") or text.contains("孤独") or text.contains("感冒") or text.contains("失眠"):
		return "stress"
	for choice in choices:
		for key in choice.success_effects.keys():
			if ["academic_progress", "visa_progress", "career_progress", "money", "language", "social", "stress", "hunger", "aps_knowledge", "aps_score", "gpa_score"].has(str(key)):
				return str(key)
	return "academic_progress"

func _build_balanced_choice(archetype: String, focus: String):
	match archetype:
		"稳妥处理":
			return _choice("稳妥处理", _focus_effect(focus, 3, {"stress": 1}), _focus_effect(focus, 1, {"stress": 4}), 0.58, {}, "", _focus_modifiers(focus, {"energy": 0.001, "stress": -0.002}))
		"寻求帮助":
			return _choice("寻求帮助", _focus_effect(focus, 2, {"social": 2, "stress": -2}), {"stress": 3, "social": -1}, 0.5, {}, "", _focus_modifiers(focus, {"social": 0.002, "language": 0.001, "loneliness": -0.001}))
		"冒险推进":
			return _choice("冒险推进", _focus_effect(focus, 5, {"energy": -7, "stress": 4}), {"energy": -9, "stress": 7}, 0.38, {}, "", _focus_modifiers(focus, {"energy": 0.002, "stress": -0.003}))
	return _choice("暂时回避", _avoid_effect(focus), _focus_effect(focus, -3, {"stress": 3}), 0.72, {}, "", {"stress": -0.002, "energy": 0.002, "loneliness": -0.001})

func _focus_modifiers(focus: String, extra: Dictionary) -> Dictionary:
	var modifiers := extra.duplicate()
	match focus:
		"academic_progress":
			modifiers["academic_progress"] = 0.002
		"visa_progress":
			modifiers["visa_progress"] = 0.002
			modifiers["language"] = 0.0015
		"career_progress":
			modifiers["career_progress"] = 0.002
			modifiers["language"] = 0.001
		"aps_knowledge":
			modifiers["aps_knowledge"] = 0.0025
			modifiers["language"] = 0.0015
		"money":
			modifiers["money"] = 0.001
			modifiers["energy"] = float(modifiers.get("energy", 0.0)) + 0.001
		"language":
			modifiers["language"] = 0.0025
		"social":
			modifiers["social"] = 0.0025
			modifiers["language"] = 0.001
		"hunger":
			modifiers["energy"] = 0.002
			modifiers["money"] = 0.001
		"stress":
			modifiers["resilience"] = 0.0
			modifiers["stress"] = float(modifiers.get("stress", 0.0)) - 0.002
	return modifiers

func _focus_effect(focus: String, amount: int, extra: Dictionary = {}) -> Dictionary:
	var effects := extra.duplicate()
	match focus:
		"money":
			effects["money"] = int(effects.get("money", 0)) + amount * 35
		"aps_knowledge":
			effects["aps_knowledge"] = int(effects.get("aps_knowledge", 0)) + amount
			effects["stress"] = int(effects.get("stress", 0)) + max(0, amount / 2)
		"stress":
			effects["stress"] = int(effects.get("stress", 0)) - amount
			effects["energy"] = int(effects.get("energy", 0)) + max(0, amount / 2)
		"hunger":
			effects["hunger"] = int(effects.get("hunger", 0)) - amount * 4
			effects["energy"] = int(effects.get("energy", 0)) + max(0, amount)
		_:
			effects[focus] = int(effects.get(focus, 0)) + amount
	return effects

func _avoid_effect(focus: String) -> Dictionary:
	var effects := {"stress": -4, "energy": 5}
	match focus:
		"academic_progress":
			effects["academic_progress"] = -3
		"visa_progress":
			effects["visa_progress"] = -2
		"career_progress":
			effects["career_progress"] = -2
		"money":
			effects["money"] = -70
		"aps_knowledge":
			effects["aps_knowledge"] = -2
		"language":
			effects["language"] = -1
		"social":
			effects["loneliness"] = 3
		"stress":
			effects["loneliness"] = -2
		"hunger":
			effects["hunger"] = 8
			effects["money"] = 20
	return effects

func _character(id: String, name: String, role: String, description: String, relationship: Dictionary):
	var character = CharacterDefScript.new()
	character.id = id
	character.name = name
	character.role = role
	character.description = description
	character.starting_relationship = relationship
	return character

func _ending(id: String, title: String, description: String, priority: int, conditions: Dictionary):
	var ending = EndingDefScript.new()
	ending.id = id
	ending.title = title
	ending.description = description
	ending.priority = priority
	ending.conditions = conditions
	return ending

func _load_endings_from_json() -> bool:
	if not FileAccess.file_exists(ENDING_JSON_PATH):
		return false
	var loaded := DataLoaderScript.load_endings(ENDING_JSON_PATH)
	if loaded.is_empty():
		return false
	endings = loaded
	ending_source = ENDING_JSON_PATH
	return true

func _build_characters() -> void:
	character_source = "hardcoded"
	characters = [
		_character("li", "李同学", "中国同学", "消息灵通，也会把群里的焦虑一并转发给你。", {"favorability": 25, "trust": 20, "conflict": 0, "story_stage": 0}),
		_character("anna", "Anna", "德国同学", "小组课上认识的德国同学，直接但靠谱。", {"favorability": 15, "trust": 10, "conflict": 0, "story_stage": 0}),
		_character("cem", "Cem", "WG 室友", "会提醒你垃圾分类，也会邀请你周末做饭。", {"favorability": 20, "trust": 15, "conflict": 0, "story_stage": 0}),
		_character("mueller", "Müller 教授", "教授", "回邮件不快，但很看重准备充分的学生。", {"favorability": 10, "trust": 5, "conflict": 0, "story_stage": 0}),
		_character("parents", "父母", "家庭", "跨国视频电话里永远绕不开钱、成绩和未来。", {"favorability": 40, "trust": 35, "conflict": 10, "story_stage": 0})
	]

func _load_characters_from_json() -> bool:
	if not FileAccess.file_exists(CHARACTER_JSON_PATH):
		return false
	var loaded := DataLoaderScript.load_characters(CHARACTER_JSON_PATH)
	if loaded.is_empty():
		return false
	characters = loaded
	character_source = CHARACTER_JSON_PATH
	return true

func _load_actions_from_json() -> bool:
	if not FileAccess.file_exists(ACTION_JSON_PATH):
		return false
	var loaded := DataLoaderScript.load_actions(ACTION_JSON_PATH)
	if loaded.is_empty():
		return false
	actions = loaded
	action_source = ACTION_JSON_PATH
	return true

func _load_events_from_json() -> bool:
	var all_group_files_exist := true
	for path in EVENT_JSON_PATHS:
		if not FileAccess.file_exists(str(path)):
			all_group_files_exist = false
			break
	if all_group_files_exist:
		var grouped := DataLoaderScript.load_events_from_paths(EVENT_JSON_PATHS)
		if not grouped.is_empty():
			events = grouped
			event_source = ",".join(EVENT_JSON_PATHS)
			return true
	if not FileAccess.file_exists(EVENT_JSON_PATH):
		return false
	var loaded := DataLoaderScript.load_events(EVENT_JSON_PATH)
	if loaded.is_empty():
		return false
	events = loaded
	event_source = EVENT_JSON_PATH
	return true

func _build_actions() -> void:
	action_source = "hardcoded"
	actions = [
		_action("aps_language_course", "APS 语言课", "准备 APS 面谈可用的德语/英语表达，把课程内容讲清楚比背模板更重要。", 14, 60, {"language": 7, "aps_knowledge": 2, "stress": 2}, ["application", "language"], {"max_week": 0, "missing_flag": "aps_passed"}),
		_action("testdaf_prep_china", "国内 TestDaF 备考", "针对阅读、听力、写作和口语刷题。目标不是总分好看，而是四项都至少 TDN 4。", 18, 120, {"language": 10, "stress": 4}, ["application", "language"], {"max_week": 0, "missing_flag": "testdaf_passed"}),
		_action("testdaf_exam_china", "参加 TestDaF", "在出国前参加 TestDaF。四项都达到 TDN 4 才满足多数德语授课项目入学语言要求。", 24, 215, {"stress": 8}, ["application", "language"], {"max_week": 0, "min_money": 215, "min_language": 55, "missing_flag": "testdaf_passed"}, ["language_risk"]),
		_action("aps_part_time_job", "申请季打工攒钱", "补 APS 费用、公证翻译和申请费，但会挤压复习时间。收益按工时结算，采用当前德国最低工资口径。", 26, 0, {"work_hours": 23, "aps_knowledge": -2, "stress": 6}, ["application", "money"], {"max_week": 0, "missing_flag": "aps_passed"}, ["study_risk"]),
		_action("review_university_courses", "复习大学专业课", "重新翻成绩单和专业课笔记，准备解释自己真的学过什么。", 22, 0, {"aps_knowledge": 12, "academic_progress": 3, "stress": 6}, ["application", "study"], {"max_week": 0, "missing_flag": "aps_passed"}),
		_action("organize_aps_documents", "整理 APS 材料", "成绩单、在读/毕业证明、公证翻译和申请系统，一个错漏就会拖慢全线。", 14, 30, {"visa_progress": 5, "aps_knowledge": 4, "stress": 4}, ["application", "admin"], {"max_week": 0, "missing_flag": "aps_documents_ready"}, [], "aps_documents_ready"),
		_action("aps_interview", "参加 APS 审核", "提交材料并参加 APS 面谈/TestAS。结果会决定你能申请的德国大学档位。", 28, 250, {"stress": 10}, ["application", "admin"], {"max_week": 0, "min_money": 250, "min_language": 30, "min_aps_knowledge": 45, "flag": "aps_documents_ready", "missing_flag": "aps_passed"}, ["application_risk"]),
		_action("attend_lecture", "认真上课", "跟住本周课程，代价是精力和一点压力。未完成学校注册时无法正常上课。", 16, 0, {"academic_progress": 8, "stress": 3}, ["study"], {"flag": "school_registered"}),
		_action("problem_set", "刷题备考", "把 Übung 做到手酸，考试掌握度明显上涨。", 24, 0, {"academic_progress": 12, "stress": 8}, ["study", "exam"], {}, ["burnout"]),
		_action("group_project", "推进小组项目", "给小组发消息、整理文档、争取不在 presentation 前爆炸。", 18, 0, {"academic_progress": 7, "social": 4, "stress": 5}, ["study", "social"], {"min_week": 7, "flag": "school_registered"}),
		_action("library_day", "图书馆自习", "安静地补进度，顺便意识到大家都很能学。", 20, 0, {"academic_progress": 10, "loneliness": 2}, ["study"]),
		_action("office_hour", "教授答疑", "准备问题去 office hour，德语越好越不慌。", 14, 0, {"academic_progress": 6, "career_progress": 3, "stress": -2}, ["study", "career"], {"min_week": 6, "flag": "school_registered"}),
		_action("write_hausarbeit", "写 Hausarbeit", "提前写论文草稿，后期少一点绝望。", 22, 0, {"academic_progress": 11, "language": 2, "stress": 6}, ["study", "exam"], {"min_week": 12, "flag": "school_registered"}),
		_action("german_course", "上德语课", "短期不救命，长期处处救命。", 15, 20, {"language": 9, "social": 1}, ["language"], {"flag": "testdaf_passed"}),
		_action("language_school_germany", "德国语言班", "没在出国前拿到 TestDaF 4x4，就只能在德国继续读语言。课更密，费用也高很多。", 22, 420, {"language": 13, "stress": 5, "academic_progress": -2}, ["language", "admin"], {"min_week": 1, "missing_flag": "testdaf_passed"}, ["money_risk"]),
		_action("testdaf_exam_germany", "德国重考 TestDaF", "在德国重考 TestDaF。考试和生活成本叠加，拖得越久，注册和学业越危险。", 26, 360, {"stress": 10}, ["language", "admin"], {"min_week": 1, "min_money": 360, "min_language": 58, "missing_flag": "testdaf_passed"}, ["money_risk", "study_risk"]),
		_action("language_tandem", "语言交换", "半小时德语，半小时中文，互相礼貌卡壳。", 12, 0, {"language": 6, "social": 5, "loneliness": -3}, ["language", "social"]),
		_action("write_email_practice", "练习德语邮件", "学习如何在 Sehr geehrte 和 Hallo 之间做人。", 8, 0, {"language": 4, "visa_progress": 2, "stress": -1}, ["language", "admin"]),
		_action("watch_german_news", "看德语新闻", "听懂了天气，没听懂政治，但已经是进步。", 8, 0, {"language": 3, "loneliness": 1}, ["language"]),
		_action("insurance_paperwork", "处理保险", "确认学生公保/私保状态，拿到学校注册需要的电子保险通知。2026 年学生公保常见约 141-146 EUR/月。", 18, 0, {"visa_progress": 10, "stress": 6}, ["admin"], {"max_week": 8}),
		_action("bank_account", "激活冻结账户", "激活 Sperrkonto 并绑定 Girokonto。2026 年学生签证通常需 11,904 EUR，每月最多释放 992 EUR。", 18, 0, {"visa_progress": 8, "stress": 5}, ["admin"], {"min_week": 1, "max_week": 9}),
		_action("school_registration", "完成学校注册", "提交保险电子通知、TestDaF 4x4、缴纳学期费并完成 Einschreibung。注册窗口很短，错过后只能等下学期，时间、房租和精神状态都会被拖住。", 20, 320, {"visa_progress": 6, "stress": 6, "academic_progress": 2}, ["admin", "study"], {"min_week": 1, "max_week": 6, "flag": "testdaf_passed", "missing_flag": "school_registered"}, [], "school_registered"),
		_action("next_semester_registration", "下学期注册", "错过 Einschreibung 窗口后，等下一学期补注册。身份能续上，但本学期的房租、保险和学习时间已经付出代价。", 24, 540, {"visa_progress": 5, "stress": 12, "academic_progress": -10}, ["admin", "study"], {"min_week": 12, "flag": "testdaf_passed", "missing_flag": "school_registered"}, ["money_risk", "study_risk"], "school_registered"),
		_action("anmeldung", "办理 Anmeldung", "住址登记是无数后续手续的钥匙。", 22, 0, {"visa_progress": 13, "stress": 8}, ["admin"], {"min_week": 4, "max_week": 10}),
		_action("visa_appointment", "办理居留许可", "刷 Termin、补材料、拿 Fiktionsbescheinigung 或电子居留卡。没办好不会显示成普通数值，但会触发严重风险。", 16, 0, {"visa_progress": 9, "stress": 7}, ["admin"], {"min_week": 8, "missing_flag": "visa_valid"}, ["admin_risk"], "visa_valid"),
		_action("international_office", "找 International Office", "学校老师可能不能解决一切，但至少知道下一封邮件发给谁。", 14, 0, {"visa_progress": 7, "stress": -3}, ["admin", "support"], {"min_week": 5}),
		_action("part_time_job", "打工", "合法学生工时内补生活费。按 2026 年德国最低工资 13.90 EUR/小时结算，同时要守住学期内每周 20 小时、全年 140 个全天/280 个半天的边界。", 28, 0, {"academic_progress": -4, "stress": 4, "work_hours": 10}, ["money", "career"], {"min_week": 6}, ["study_risk"]),
		_action("mini_job_extra", "多打一班工", "多接 18 小时合法班，按最低工资结算。如果本周已经打工，这一班可能把你推过每周 20 小时红线。", 36, 0, {"academic_progress": -8, "stress": 12, "loneliness": 3, "work_hours": 18}, ["money"], {"min_week": 10}, ["burnout", "study_risk", "legal_risk"]),
		_action("scholarship", "申请奖学金", "写动机信，整理材料，赌一个回音。", 18, 0, {"career_progress": 6, "stress": 3}, ["money", "career"], {"min_week": 5}),
		_action("budget_call", "和父母谈预算", "开口很难，但月底更难。", 10, 0, {"money": 180, "stress": 5, "loneliness": -2}, ["money", "family"]),
		_action("cook_at_home", "自己做饭", "省钱，稳定，偶尔治愈。", 8, 16, {"energy": 8, "stress": -2, "hunger": -30}, ["life"]),
		_action("wg_dinner", "参加 WG 晚餐", "聊垃圾分类、房租和哪里买酱油。", 12, 10, {"social": 7, "language": 3, "loneliness": -7, "hunger": -24}, ["social", "language", "life"]),
		_action("student_club", "参加学生社团", "认识新朋友，也认识新的 Doodle 投票。", 16, 5, {"social": 9, "language": 2, "career_progress": 2, "loneliness": -5}, ["social"]),
		_action("classmate_meal", "同学聚餐", "交换课程情报和焦虑。", 12, 18, {"social": 6, "academic_progress": 2, "stress": -2, "hunger": -18}, ["social", "study", "life"]),
		_action("date_night", "尝试约会", "可能很尴尬，也可能让这座城市亮一点。", 16, 15, {"social": 6, "loneliness": -8, "stress": -2}, ["social"], {"min_week": 8}),
		_action("partner_cook_together", "和对象一起做饭", "稳定的关系会把晚饭变成恢复点：有人分担，也有人提醒你别只吃面包。", 10, 8, {"loneliness": -12, "hunger": -32, "stress": -5, "money": 18}, ["social", "life"], {"min_week": 10, "flag": "partner_cook"}),
		_action("luxury_date", "高消费约会", "餐厅、展览、短途旅行都很浪漫，账单也很现实。", 18, 95, {"social": 9, "loneliness": -12, "stress": -4, "career_progress": -1}, ["social"], {"min_week": 10, "flag": "partner_spender"}, ["money_risk"]),
		_action("sleep_recover", "好好睡觉", "没有成长感，但人类需要睡觉。", 0, 0, {"energy": 28, "stress": -8}, ["mental"]),
		_action("go_running", "去跑步", "用腿把焦虑暂时甩开。", 8, 0, {"energy": 12, "stress": -10, "loneliness": -2}, ["mental"]),
		_action("therapy", "心理咨询", "预约很难，但说出来会轻一点。", 10, 25, {"stress": -18, "loneliness": -10}, ["mental"], {"min_week": 6}),
		_action("bilibili_rest", "躺平刷视频", "立刻回血，明天再说。", 0, 0, {"energy": 18, "stress": -12, "academic_progress": -5}, ["mental"], {}, ["study_risk"]),
		_action("cv_workshop", "简历工作坊", "学习如何把普通经历写得像项目管理。", 14, 0, {"career_progress": 10, "language": 2}, ["career"], {"min_week": 9}),
		_action("apply_howi", "投 HiWi", "给教授和研究所发申请，开始职业线。", 18, 0, {"career_progress": 12, "stress": 4}, ["career"], {"min_week": 12, "min_language": 30})
	]
	_apply_action_balance_controls()

func _apply_action_balance_controls() -> void:
	for action in actions:
		match action.id:
			"sleep_recover":
				action.cooldown_group = "rest"
				action.max_per_week = 1
				action.diminishing_window = 3
				action.diminishing_factor = 0.55
				action.effects = {"energy": 30, "stress": -8, "academic_progress": -4, "exam_readiness": -2, "career_progress": -2}
				action.requirements["max_energy"] = 75
			"bilibili_rest":
				action.cooldown_group = "avoidance"
				action.max_per_week = 1
				action.diminishing_window = 3
				action.diminishing_factor = 0.5
				action.effects = {"energy": 8, "stress": -14, "academic_progress": -6, "exam_readiness": -5, "language": -2, "loneliness": 3}
			"attend_lecture":
				action.effects = {"academic_progress": 7, "exam_readiness": 3, "stress": 3}
			"problem_set":
				action.effects = {"academic_progress": 6, "exam_readiness": 12, "stress": 8}
				action.cooldown_group = "deep_study"
				action.max_per_week = 2
			"group_project":
				action.effects = {"academic_progress": 7, "exam_readiness": 4, "social": 4, "stress": 5}
			"library_day":
				action.effects = {"academic_progress": 8, "exam_readiness": 5, "loneliness": 2}
			"office_hour":
				action.effects = {"academic_progress": 5, "exam_readiness": 5, "career_progress": 3, "stress": -2}
			"write_hausarbeit":
				action.effects = {"academic_progress": 8, "exam_readiness": 6, "language": 2, "stress": 6}
			"part_time_job":
				action.effects = {"academic_progress": -4, "exam_readiness": -3, "stress": 4, "work_hours": 10}
			"mini_job_extra":
				action.effects = {"academic_progress": -8, "exam_readiness": -7, "stress": 12, "loneliness": 3, "work_hours": 18}
			"therapy":
				action.cooldown_group = "therapy"
				action.max_per_week = 1
				action.diminishing_window = 4
				action.diminishing_factor = 0.45
				action.cost_money = 120
				action.effects = {"stress": -28, "loneliness": -6}
				action.requirements["min_stress"] = 55
			"cook_at_home":
				action.cooldown_group = "meal"
				action.max_per_week = 2
				action.diminishing_window = 1
				action.diminishing_factor = 0.7
				action.cost_money = 15
				action.cost_energy = 5
				action.effects = {"stress": -2, "hunger": -30}
			"classmate_meal":
				action.cooldown_group = "social_meal"
				action.max_per_week = 1
				action.diminishing_window = 3
				action.diminishing_factor = 0.65
				action.cost_money = 18
				action.effects = {"social": 6, "academic_progress": 2, "stress": -2, "hunger": -28, "loneliness": -3}
				action.requirements["min_hunger"] = 35
			"wg_dinner":
				action.cooldown_group = "social_meal"
				action.max_per_week = 1
				action.diminishing_window = 2
				action.diminishing_factor = 0.65
				action.cost_money = 10
				action.effects = {"social": 7, "language": 3, "loneliness": -7, "hunger": -30}
				action.requirements["min_hunger"] = 35
			"partner_cook_together":
				action.cooldown_group = "social_meal"
				action.max_per_week = 1
				action.diminishing_window = 2
				action.diminishing_factor = 0.65
				action.requirements["min_hunger"] = 35
			"go_running":
				action.cooldown_group = "exercise"
				action.max_per_week = 1
				action.diminishing_window = 2
				action.diminishing_factor = 0.65
				action.effects = {"energy": 8, "stress": -8, "loneliness": -1}
			"student_club":
				action.cooldown_group = "social_activity"
				action.max_per_week = 1
				action.diminishing_window = 2
				action.diminishing_factor = 0.7
				action.effects = {"social": 7, "language": 2, "career_progress": 1, "loneliness": -4, "stress": 2}

func _build_events() -> void:
	event_source = "hardcoded"
	events = [
		_event("aps_start", "申请季开始：APS", "你还没有真正出发。APS 会核查学历材料真实性和入学资格，并通过面谈或 TestAS 检查你是否真的学过成绩单上的课程。", "fixed", {"week": -8}, [
			_choice("先看清 APS 要求", {"aps_knowledge": 5, "stress": 2}),
			_choice("列材料清单", {"visa_progress": 4, "stress": 3}, {}, 1.0, {}, "aps_checklist"),
			_choice("估算申请预算", {"money": 80, "stress": 2}),
			_choice("先背面谈模板", {"language": 2, "aps_knowledge": 1}, {"stress": 5}, 0.45)
		]),
		_event("testdaf_requirement_notice", "TestDaF 4x4 要求", "德语授课项目通常要看 TestDaF 四项小分。你的目标不是平均分，而是阅读、听力、写作、口语都达到 TDN 4。", "fixed", {"week": -7, "missing_flag": "testdaf_passed"}, [
			_choice("制定四项备考计划", {"language": 6, "stress": 3}),
			_choice("重点补口语和写作", {"language": 5, "aps_knowledge": 1, "stress": 4}),
			_choice("先报名考试占考位", {"money": -215, "stress": 2}, {"money": -215, "stress": 6}, 0.7),
			_choice("觉得可以到德国再考", {"stress": -2, "money": 40}, {"stress": 5}, 0.62, {}, "language_track_risk")
		]),
		_event("aps_not_ready", "APS 还没达标", "距离申请季结束越来越近。要参加 APS，至少需要材料齐、钱够、语言能说明课程、专业课复习到位。", "conditional", {"week": 0, "missing_flag": "aps_passed"}, [
			_choice("继续复习专业课", {"aps_knowledge": 10, "stress": 6, "energy": -8}),
			_choice("补语言表达", {"language": 7, "stress": 4, "money": -40}),
			_choice("临时打工补费用", {"work_hours": 19, "energy": -20, "stress": 7}),
			_choice("重新整理材料", {"visa_progress": 5, "aps_knowledge": 3, "stress": 4}, {}, 1.0, {}, "aps_documents_ready")
		], 1.0, true),
		_event("aps_elite_university_options", "APS 高分定位", "你的 APS 结果和成绩背景足以冲刺更强的研究型大学或 TU9 项目，但申请材料也要更精细。", "fixed", {"week": 0, "min_aps_score": 84, "flag": "aps_passed"}, [
			_choice("冲刺 TU9/精英项目", {"career_progress": 8, "stress": 8, "money": -120}, {"stress": 12, "money": -160}, 0.62, {}, "applied_elite"),
			_choice("研究型大学为主", {"career_progress": 6, "stress": 4, "money": -80}, {}, 0.78, {}, "applied_research"),
			_choice("保留应用科学大学兜底", {"stress": -2, "money": -60}, {}, 1.0, {}, "applied_balanced"),
			_choice("先等更完美材料", {"stress": 5, "career_progress": -2})
		]),
		_event("aps_mid_university_options", "APS 稳妥定位", "你的 APS 分数可以申请不少综合大学和应用科学大学。选校策略比盲目冲名校更重要。", "fixed", {"week": 0, "min_aps_score": 60, "max_aps_score": 83, "flag": "aps_passed"}, [
			_choice("综合大学 + 应用科学混申", {"career_progress": 5, "stress": 3, "money": -90}, {}, 0.8, {}, "applied_balanced"),
			_choice("优先看课程匹配", {"academic_progress": 3, "career_progress": 4, "stress": 2}, {}, 0.82, {}, "applied_matched"),
			_choice("只冲排名", {"stress": 8, "money": -120}, {"stress": 14, "career_progress": -3}, 0.42, {}, "applied_risky"),
			_choice("先补语言再申请", {"language": 5, "stress": 3, "money": -50})
		]),
		_event("aps_low_university_options", "APS 低空通过", "APS 通过了，但分数和背景比较紧。你仍能申请，但需要更多保底、预科或受限专业策略。", "fixed", {"week": 0, "min_aps_score": 50, "max_aps_score": 59, "flag": "aps_passed"}, [
			_choice("主打保底项目", {"stress": -2, "money": -70}, {}, 1.0, {}, "applied_safe"),
			_choice("考虑预科或桥梁课程", {"academic_progress": 4, "language": 3, "money": -100}, {}, 0.78, {}, "applied_foundation"),
			_choice("继续补背景再申请", {"aps_knowledge": 5, "language": 3, "stress": 4}),
			_choice("硬冲高排名", {"stress": 10, "money": -130}, {"stress": 16, "money": -180}, 0.28, {}, "applied_risky")
		]),
		_event("arrival", "抵达德国", "你拖着两个箱子出站。APS、录取、签证、保险证明和冻结账户证明都已经在出发前完成，现在要把德国本地手续接上。", "fixed", {"week": 1}, [
			_choice("先去宿舍放行李", {"energy": 10, "stress": -4}, {}, 1.0, {}, "arrived"),
			_choice("立刻去超市和 dm 补生活用品", {"money": -55, "energy": -6, "stress": -3, "hunger": -10}, {}, 1.0, {}, "arrived_supplied"),
			_choice("先激活 SIM 卡和银行 App", {"visa_progress": 4, "language": 1, "stress": 4}, {"stress": 8, "visa_progress": -2}, 0.68, {"language": 0.003}, "arrived"),
			_choice("坐在车站缓一缓", {"stress": -8, "loneliness": 4, "visa_progress": -2, "money": -25}, {}, 1.0, {}, "arrived")
		]),
		_event("germany_language_track_start", "德国继续读语言", "你已经到德国，但 TestDaF 还没 4x4。语言班、住宿和生活费同时烧钱，正式注册和上课都会被推迟。", "conditional", {"min_week": 1, "max_week": 3, "missing_flag": "testdaf_passed"}, [
			_choice("报名密集语言班", {"language": 10, "money": -420, "stress": 6, "academic_progress": -3}),
			_choice("先自学一周省钱", {"language": 4, "money": 40, "stress": 5, "academic_progress": -4}),
			_choice("问学校能否条件注册", {"visa_progress": 3, "stress": 4}, {"stress": 8}, 0.45),
			_choice("找便宜语言学校", {"language": 6, "money": -260, "stress": 8}, {"language": 2, "money": -220, "stress": 12}, 0.55)
		]),
		_event("testdaf_blocks_enrollment", "TestDaF 卡住注册", "学校提醒：没有合格语言证明，德语授课项目不能正式注册。每拖一周，都在花生活费和错过课程。", "conditional", {"min_week": 3, "max_week": 8, "missing_flag": "testdaf_passed"}, [
			_choice("集中冲刺重考", {"language": 9, "money": -360, "stress": 10, "academic_progress": -4}),
			_choice("申请语言班延期", {"visa_progress": 3, "stress": 6, "money": -120}, {"stress": 12}, 0.55),
			_choice("转英语授课/其他项目", {"career_progress": 2, "stress": 9, "money": -100}, {"stress": 14, "career_progress": -2}, 0.42, {}, "program_switch_considered"),
			_choice("继续拖延", {"stress": 10, "academic_progress": -8, "money": -180})
		], 1.4),
		_event("first_lecture", "第一次上课", "教授讲得很快，PPT 看起来很熟悉但又陌生。", "fixed", {"week": 3, "flag": "school_registered"}, [
			_choice("硬着头皮记笔记", {"academic_progress": 5, "exam_readiness": 2, "stress": 3}),
			_choice("课后问同学资料", {"social": 4, "academic_progress": 3, "loneliness": -2}, {"stress": 4}, 0.75, {"social": 0.003, "language": 0.002}),
			_choice("当晚重看 Moodle 资料", {"academic_progress": 4, "exam_readiness": 5, "energy": -8, "stress": 2}),
			_choice("假装都听懂了", {"stress": -3, "academic_progress": -4, "exam_readiness": -4})
		]),
		_event("missing_school_registration", "注册没完成，上不了课", "你到了教室门口才发现账号、选课和课程材料都卡在注册状态。学期费花了时间和精力，学业却开始空转。", "fixed", {"week": 3, "missing_flag": "school_registered"}, [
			_choice("当天补注册", {"money": -320, "stress": 8, "academic_progress": -4, "visa_progress": 4}, {"stress": 12, "academic_progress": -8}, 0.82, {"flag": "testdaf_passed"}, "school_registered"),
			_choice("先找 International Office", {"stress": 4, "academic_progress": -3, "visa_progress": 3}, {"stress": 8, "academic_progress": -7}, 0.72, {}, "school_registered"),
			_choice("只靠自学顶一周", {"academic_progress": -6, "stress": 3, "hunger": 5}),
			_choice("继续拖延", {"academic_progress": -10, "stress": 8, "money": -80})
		]),
		_event("registration_window_missed", "错过学校注册窗口", "Einschreibung 截止日过去了。就算之后 TestDaF 过了，也不能立刻进入本学期正常学习，只能处理延期、语言班或例外申请。生活费还在烧，精神压力开始变成主线。", "fixed", {"week": 7, "missing_flag": "school_registered"}, [
			_choice("接受下学期再注册", {"money": -650, "stress": 14, "academic_progress": -12, "visa_progress": 2}, {}, 1.0, {}, "registration_delayed"),
			_choice("带 TestDaF 和材料求例外", {"money": -360, "stress": 12, "visa_progress": 5, "academic_progress": -5}, {"money": -420, "stress": 18, "academic_progress": -10}, 0.46, {"flag": "testdaf_passed"}, "school_registered", {"language": 0.003, "visa_progress": 0.003}),
			_choice("转入语言班等待下学期", {"language": 8, "money": -900, "stress": 10, "academic_progress": -9}, {}, 1.0, {}, "registration_delayed"),
			_choice("逃避邮件和截止日", {"stress": 22, "academic_progress": -16, "money": -420, "hunger": 8}, {}, 1.0, {}, "registration_delayed")
		]),
		_event("wg_interview", "WG 面试", "室友问你平时会不会很吵，以及是不是愿意一起打扫厨房。", "fixed", {"week": 4}, [
			_choice("表现得非常德式", {"visa_progress": 6, "social": 3}, {"stress": 5}, 0.7, {}, "housing_stable"),
			_choice("说自己会做中餐", {"social": 7, "loneliness": -4, "hunger": -6}, {"stress": 3}, 0.8, {}, "wg_cooking"),
			_choice("坦白预算很紧", {"money": 120, "stress": 5}, {"stress": 8, "social": -3}, 0.55, {"social": 0.003}, "cheap_room_hint"),
			_choice("过度迎合每条规则", {"stress": 8, "social": 2, "energy": -6}, {"stress": 12}, 0.62, {"language": 0.002}, "housing_stable")
		]),
		_event("legal_work_limit_notice", "学生打工时长说明", "学校提醒非欧盟学生：打工通常不能超过每年 140 个全天或 280 个半天，学期内每周超过 20 小时会让居留和学业状态变得危险。", "fixed", {"week": 5}, [
			_choice("把工时记进日历", {"stress": 2, "visa_progress": 3}, {}, 1.0, {}, "work_law_briefed"),
			_choice("只接合同清楚的班", {"career_progress": 3, "visa_progress": 2, "money": -40}, {}, 1.0, {}, "work_law_briefed"),
			_choice("问 AStA/International Office", {"language": 2, "visa_progress": 4, "stress": -1}, {}, 1.0, {}, "work_law_briefed"),
			_choice("觉得自己不会超", {"stress": -2}, {"visa_progress": -2, "stress": 4}, 0.6, {}, "work_law_briefed")
		]),
		_event("anmeldung_deadline", "Anmeldung 提醒", "没有住址登记，后面的银行、保险、延签都会变得微妙。", "fixed", {"week": 6}, [
			_choice("立刻补材料", {"visa_progress": 7, "stress": 4, "energy": -4}),
			_choice("先问 International Office", {"visa_progress": 5, "stress": -2, "language": 1}),
			_choice("请室友确认 Wohnungsgeberbestätigung", {"visa_progress": 6, "social": 3, "stress": 1}, {"stress": 6, "visa_progress": -2}, 0.76, {"social": 0.003, "language": 0.002}),
			_choice("把信封塞进抽屉", {"stress": -5, "visa_progress": -8, "money": -30}, {}, 1.0, {}, "admin_avoidance")
		]),
		_event("midterm_pressure", "期中压力", "作业、阅读和生活琐事开始一起上门。", "fixed", {"week": 10}, [
			_choice("整理学习计划", {"academic_progress": 5, "exam_readiness": 4, "stress": -2}),
			_choice("先睡一觉", {"energy": 16, "stress": -6, "academic_progress": -2, "exam_readiness": -2}),
			_choice("砍掉一班打工补作业", {"academic_progress": 7, "exam_readiness": 5, "money": -139, "stress": 3}),
			_choice("靠咖啡硬顶", {"academic_progress": 4, "exam_readiness": 2, "stress": 10, "energy": -12})
		]),
		_event("group_invite", "德国同学邀你组队", "Anna 问你要不要一起做 presentation。", "fixed", {"week": 12}, [
			_choice("答应并主动分工", {"academic_progress": 6, "exam_readiness": 4, "social": 8, "language": 3}, {"stress": 5}, 0.85, {"social": 0.003, "language": 0.002}, "anna_group"),
			_choice("只接资料整理的部分", {"academic_progress": 4, "exam_readiness": 2, "social": 3, "stress": 2}, {}, 1.0, {}, "anna_group"),
			_choice("请她先解释评分标准", {"exam_readiness": 6, "language": 3, "social": 5}, {"stress": 6}, 0.72, {"language": 0.003, "social": 0.002}, "anna_group"),
			_choice("委婉拒绝", {"stress": -3, "social": -4, "academic_progress": -3})
		]),
		_event("exam_week", "第一次 Klausur", "题目每个词都认识，连起来突然不认识。", "fixed", {"week": 18}, [
			_choice("先做会的题", {"exam_readiness": 5, "stress": 4}, {"stress": 8, "exam_readiness": -3}, 0.72, {"exam_readiness": 0.004, "stress": -0.002}),
			_choice("硬翻译题目", {"language": 3, "exam_readiness": 2, "stress": 7}, {"stress": 12, "exam_readiness": -4}, 0.58, {"language": 0.004, "stress": -0.002}),
			_choice("先扫整张卷子分配时间", {"exam_readiness": 7, "stress": 2}, {"stress": 7}, 0.68, {"exam_readiness": 0.005}),
			_choice("盯着第一题死磕", {"exam_readiness": -5, "stress": 10}, {"stress": 14, "exam_readiness": -8}, 0.38, {"stress": -0.002})
		]),
		_event("semester_wrap", "学期快结束了", "你开始理解德国大学的节奏，也理解了为什么大家都说第一学期是适应期。", "fixed", {"week": 20}, [
			_choice("复盘这一学期", {"stress": -5, "career_progress": 2, "exam_readiness": 2}),
			_choice("给下学期列行政清单", {"visa_progress": 4, "stress": -2}),
			_choice("约朋友吃饭庆祝", {"social": 5, "loneliness": -6, "money": -28, "hunger": -18}),
			_choice("直接躺平刷手机", {"energy": 8, "stress": -4, "career_progress": -2, "academic_progress": -2})
		]),
		_event("termin_missing", "Ausländerbehörde 没有 Termin", "未来三个月都没有可预约时间。", "conditional", {"min_week": 8, "max_visa": 45}, [
			_choice("每天早上刷新", {"visa_progress": 8, "stress": 8}),
			_choice("写邮件解释情况", {"visa_progress": 7, "language": 2}, {"stress": 6}, 0.7),
			_choice("找学校帮忙", {"visa_progress": 10, "stress": -2}, {}, 0.85),
			_choice("只等系统放号", {"stress": -3, "visa_progress": -8}, {"stress": 8, "visa_progress": -10}, 0.45, {}, "deportation_warning")
		]),
		_event("visa_status_hidden_check", "居留期限临近", "日历提醒你签证或居留许可快到期。系统里没有绿色进度条，只有 Termin、材料和一封封邮件。", "fixed", {"week": 14, "missing_flag": "visa_valid"}, [
			_choice("立刻联系外管局和学校", {"visa_progress": 9, "language": 2, "stress": 9}, {"stress": 14, "visa_progress": -3}, 0.74, {}, "visa_valid"),
			_choice("补材料并申请 Fiktionsbescheinigung", {"visa_progress": 7, "stress": 7}, {"stress": 12}, 0.66, {}, "visa_valid"),
			_choice("只在网页上继续刷 Termin", {"visa_progress": 3, "stress": 10}, {"stress": 16, "visa_progress": -4}, 0.42, {}, "deportation_warning"),
			_choice("相信不会查到自己", {"stress": -2, "visa_progress": -8}, {"stress": 8, "visa_progress": -12}, 0.35, {}, "deportation_warning")
		], 1.6),
		_event("deportation_risk_notice", "居留风险升级", "外管局来信要求你尽快说明身份状态。之前的拖延或不合规打工已经让风险从背景音变成了倒计时。", "conditional", {"min_week": 15, "flag": "deportation_warning"}, [
			_choice("带齐材料当面补救", {"visa_progress": 8, "stress": 14, "money": -60}, {"stress": 18, "money": -120}, 0.58, {}, "visa_valid"),
			_choice("请学校 International Office 介入", {"visa_progress": 7, "language": 2, "stress": 10}, {"stress": 16}, 0.64, {}, "visa_valid"),
			_choice("找律师咨询", {"visa_progress": 6, "stress": 8, "money": -280}, {"stress": 12, "money": -360}, 0.72, {}, "visa_valid"),
			_choice("继续硬扛", {"stress": 18, "academic_progress": -8, "visa_progress": -15}, {"stress": 24, "academic_progress": -12}, 0.45, {}, "deportation_order")
		], 2.0),
		_event("rent_pressure", "房租压力", "房租和押金让账户余额看起来很不友好。", "conditional", {"max_money": 700}, [
			_choice("接更多班", {"energy": -18, "academic_progress": -4, "exam_readiness": -3, "stress": 6, "work_hours": 8}),
			_choice("和父母解释", {"money": 300, "stress": 8, "loneliness": -2}, {"stress": 12}, 0.8),
			_choice("找短期 Nachhilfe/家教", {"money": 180, "career_progress": 3, "stress": 5, "energy": -10}, {"stress": 9, "money": 40}, 0.62, {"language": 0.002, "social": 0.002}),
			_choice("先欠着房租赌下月释放", {"money": 220, "stress": 14, "visa_progress": -4}, {"stress": 20, "visa_progress": -8}, 0.42, {}, "rent_arrears")
		]),
		_event("burnout_warning", "身体发出警告", "你不是很困，但也完全不想动。", "conditional", {"min_stress": 78}, [
			_choice("强制休息", {"stress": -15, "energy": 18, "academic_progress": -3}),
			_choice("继续硬撑", {"academic_progress": 4, "stress": 10, "energy": -12})
		]),
		_event("lonely_christmas", "一个人的节日", "街上很安静，宿舍厨房也很安静。", "conditional", {"min_week": 14, "min_loneliness": 65}, [
			_choice("给家里打视频", {"loneliness": -10, "stress": 4, "energy": 3}),
			_choice("约同学吃饭", {"loneliness": -14, "social": 5, "money": -25, "hunger": -18}, {"stress": 6, "money": -15}, 0.75, {"social": 0.003}),
			_choice("去教堂/学生会活动", {"loneliness": -12, "language": 2, "social": 3, "stress": 2}, {"stress": 8}, 0.66, {"language": 0.002, "social": 0.002}),
			_choice("自己扛过去", {"stress": 8, "energy": -6, "loneliness": 6, "academic_progress": -2})
		]),
		_event("academic_gap", "课程听不懂", "你发现真正的难点不是知识点，而是老师默认你早就知道。", "conditional", {"min_week": 5, "max_academic": 35}, [
			_choice("补基础", {"academic_progress": 8, "stress": 4}),
			_choice("问李同学资料", {"academic_progress": 5, "social": 2}, {"stress": 3}, 0.8)
		]),
		_event("language_wall", "德语墙", "你在柜台前听到了一个长句，灵魂短暂离线。", "conditional", {"min_week": 4, "min_visa": 20, "min_stress": 35}, [
			_choice("请对方说慢一点", {"language": 4, "stress": -2}, {"stress": 5}, 0.7),
			_choice("改用英语", {"visa_progress": 2}, {"stress": 4}, 0.65)
		]),
		_event("job_study_conflict", "打工和学习撞车", "老板问你周末能不能多来一班，作业也在问同一个问题。", "conditional", {"min_week": 10, "max_money": 1200, "max_academic": 55}, [
			_choice("选择上班", {"academic_progress": -6, "exam_readiness": -5, "stress": 6, "work_hours": 10}),
			_choice("选择写作业", {"academic_progress": 8, "exam_readiness": 6, "money": -80, "stress": 2}),
			_choice("和老板换短班", {"work_hours": 5, "academic_progress": 4, "exam_readiness": 3, "stress": 5}, {"stress": 10, "money": -60}, 0.64, {"social": 0.002, "language": 0.002}),
			_choice("两边都答应", {"work_hours": 8, "academic_progress": 2, "exam_readiness": 1, "stress": 14, "energy": -18}, {"stress": 20, "academic_progress": -6, "exam_readiness": -6}, 0.42, {}, "overcommitted")
		]),
		_event("work_limit_exceeded_warning", "打工时长越线", "这一周的合法工作时长已经超过 20 小时。钱确实进账了，但如果继续这样安排，雇主记录、工资单和居留身份都会变成风险点。", "conditional", {"min_week": 7, "flag": "work_limit_exceeded"}, [
			_choice("马上减少排班", {"stress": 8, "money": -160, "visa_progress": 4}, {"stress": 12, "money": -220}, 0.78, {}, "work_hours_corrected"),
			_choice("向外管局/学校咨询许可", {"visa_progress": 6, "language": 2, "stress": 7, "money": -40}, {"stress": 13, "visa_progress": -2}, 0.62, {}, "work_hours_corrected"),
			_choice("换成校内 HiWi 路线", {"career_progress": 8, "money": -90, "stress": 4, "academic_progress": 2}, {"stress": 9, "career_progress": 2}, 0.64, {}, "work_hours_corrected"),
			_choice("继续超时先赚钱", {"energy": -24, "stress": 18, "academic_progress": -8, "work_hours": 12}, {"work_hours": 6, "stress": 24, "visa_progress": -12}, 0.48, {}, "work_law_violation")
		], 1.8),
		_event("desperate_illegal_work_offer", "没钱后的黑工诱惑", "账户已经见底，饥饿和压力一起上升。有人说有现金工，当天结账、不问身份、不签合同。它能救这个月，也可能把你推向居留风险。", "conditional", {"min_week": 5, "max_money": 0, "min_hunger": 55}, [
			_choice("找学生会紧急援助", {"money": 120, "stress": 6, "hunger": -18, "social": 2}, {"stress": 12, "hunger": -8}, 0.62),
			_choice("向同学或父母借钱", {"money": 260, "loneliness": -3, "stress": 9, "hunger": -12}, {"stress": 16, "loneliness": 5}, 0.72),
			_choice("接下现金黑工", {"illegal_work_hours": 36, "hunger": -18, "energy": -34, "stress": 20, "academic_progress": -9}, {"illegal_work_hours": 14, "energy": -25, "stress": 24, "visa_progress": -8}, 0.58, {}, "illegal_work_taken"),
			_choice("去食物救助/低价食堂", {"hunger": -34, "stress": 8, "money": 20, "social": -1}, {"hunger": -18, "stress": 12}, 0.78)
		], 2.0),
		_event("annual_work_limit_warning", "年度打工额度用尽", "你已经接近或超过全年半天额度。短期现金流很好看，但长期合规性和续签解释都会变得沉重。", "conditional", {"min_week": 12, "flag": "annual_work_limit_exceeded"}, [
			_choice("停止接班并整理记录", {"stress": 10, "money": -260, "visa_progress": 5}, {"stress": 16, "money": -340}, 0.7, {}, "work_hours_corrected"),
			_choice("咨询专业法律帮助", {"visa_progress": 7, "stress": 8, "money": -320}, {"stress": 14, "money": -420}, 0.72, {}, "work_hours_corrected"),
			_choice("赌不会被发现", {"work_hours": 17, "stress": 18, "visa_progress": -10}, {"stress": 26, "visa_progress": -18}, 0.42, {}, "work_law_violation"),
			_choice("转向奖学金和校内岗位", {"career_progress": 8, "money": -90, "stress": 6}, {"stress": 10}, 0.6)
		], 1.6),
		_event("illegal_cash_job_offer", "现金黑工邀请", "有人介绍一份现金结算的活，不签合同、不报工时。钱来得快，但可能违反签证/居留和工作时长规则。", "conditional", {"min_week": 9, "max_money": 900}, [
			_choice("拒绝并找合法 Minijob", {"career_progress": 4, "stress": 3, "visa_progress": 2}),
			_choice("接下黑工补现金流", {"illegal_work_hours": 30, "energy": -30, "stress": 14, "academic_progress": -6, "hunger": -8}, {"illegal_work_hours": 10, "energy": -24, "stress": 18, "visa_progress": -6}, 0.62, {}, "illegal_work_taken"),
			_choice("先问学校法律建议", {"career_progress": 3, "language": 2, "stress": -1}, {"stress": 5}, 0.78),
			_choice("向父母借过这个月", {"money": 240, "stress": 7, "loneliness": -2})
		], 1.4),
		_event("illegal_work_followup", "黑工后续风险", "现金工没有工资单，也没有清晰工时。你开始担心这件事会不会影响居留和学业。", "conditional", {"min_week": 12, "flag": "illegal_work_taken"}, [
			_choice("立刻停止并保留记录", {"stress": 9, "money": -120, "visa_progress": 3}, {"stress": 14, "money": -180}, 0.7),
			_choice("找 ASTA 或法律咨询", {"visa_progress": 5, "language": 2, "stress": 5}, {"stress": 10}, 0.72, {}, "visa_valid"),
			_choice("继续做，先把钱赚到", {"illegal_work_hours": 24, "energy": -22, "stress": 16, "academic_progress": -7}, {"illegal_work_hours": 12, "stress": 22, "visa_progress": -10}, 0.5, {}, "deportation_warning"),
			_choice("假装无事发生", {"stress": 6, "visa_progress": -5}, {"stress": 14, "visa_progress": -10}, 0.42, {}, "deportation_warning")
		], 1.6),
		_event("parents_future", "父母问未来", "视频电话里，父母问你毕业以后留德国还是回国。", "conditional", {"min_week": 13, "min_stress": 45}, [
			_choice("说还没想好", {"stress": 3, "loneliness": -3}),
			_choice("说想留德国", {"career_progress": 4, "stress": 5}),
			_choice("说回国也不错", {"stress": -2, "career_progress": 2})
		]),
		_event("prof_email", "第一次给教授写邮件", "你花了 40 分钟纠结称呼和语气。", "conditional", {"min_week": 6, "min_language": 24}, [
			_choice("用 DeepL 润色", {"language": 3, "academic_progress": 3}, {}, 0.9, {}, "prof_email_ok"),
			_choice("直接发", {"academic_progress": 4}, {"stress": 5}, 0.65),
			_choice("问中国同学", {"social": 3, "stress": -2})
		]),
		_event("health_insurance_letter", "保险来信", "信里每个词都重要，但你只确定 Beitragsnummer 很重要。", "conditional", {"min_week": 5, "max_visa": 55}, [
			_choice("认真翻译", {"visa_progress": 6, "language": 2, "stress": 2}),
			_choice("拍给群友", {"visa_progress": 4, "social": 2})
		]),
		_event("project_presentation", "Presentation 临近", "小组文档终于打开了，但大家的理解不完全一样。", "conditional", {"min_week": 13, "max_academic": 70}, [
			_choice("主动整合 slides", {"academic_progress": 8, "social": 3, "stress": 6}),
			_choice("只负责自己的部分", {"academic_progress": 4, "stress": -2})
		]),
		_event("cheap_ticket", "廉价火车票", "一张去邻城的票很便宜，便宜到像是在诱惑你逃离作业。", "random", {"min_week": 6, "max_week": 15}, [
			_choice("周末短途旅行", {"stress": -12, "loneliness": -7, "money": -55, "academic_progress": -2}),
			_choice("忍住不去", {"academic_progress": 2, "stress": 2})
		], 1.2),
		_event("flat_kitchen", "WG 厨房会议", "厨房台面上出现了没人承认的锅。", "random", {"min_week": 5}, [
			_choice("主动打扫", {"social": 4, "stress": 2}),
			_choice("在群里礼貌提醒", {"language": 2, "social": 2}, {"social": -2, "stress": 4}, 0.7)
		], 1.0),
		_event("student_discount", "学生优惠", "你发现一个 App 能省下一些交通或超市钱。", "random", {"min_week": 3}, [
			_choice("立刻研究", {"money": 90, "stress": -1}),
			_choice("收藏但不看", {"stress": -2})
		], 1.0),
		_event("classmate_home_dinner", "去同学家吃饭", "李同学说今晚多做了菜，问你要不要过去。你很饿，也有点不好意思。", "conditional", {"min_week": 6, "min_hunger": 45}, [
			_choice("带点水果过去", {"hunger": -38, "social": 7, "loneliness": -6, "money": -12}, {"hunger": -18, "stress": 4}, 0.85),
			_choice("空手去但主动洗碗", {"hunger": -32, "social": 5, "stress": -2}, {"hunger": -15, "social": -1, "stress": 3}, 0.78),
			_choice("拒绝，回宿舍泡面", {"hunger": -16, "money": 8, "loneliness": 3}),
			_choice("顺便打包明天午饭", {"hunger": -42, "money": 20, "social": -1}, {"social": -4, "stress": 5, "hunger": -20}, 0.52)
		], 1.3),
		_event("drinks_with_classmates", "同学约你喝酒", "小组同学说今晚去酒吧。去不去都不是纯社交选择：钱、第二天精力和关系都会变。", "random", {"min_week": 8}, [
			_choice("去小酌一杯", {"social": 8, "loneliness": -6, "money": -25, "energy": -8, "stress": -5, "hunger": 4}, {"money": -30, "energy": -12, "stress": 4}, 0.78),
			_choice("喝无酒精饮料", {"social": 5, "loneliness": -3, "money": -12, "stress": -2}, {"social": 1, "money": -10}, 0.86),
			_choice("拒绝去学习", {"academic_progress": 4, "social": -2, "stress": 2}),
			_choice("喝过头", {"social": 10, "stress": -6, "money": -45, "energy": -18, "academic_progress": -3, "hunger": 8}, {"money": -55, "energy": -25, "stress": 10, "academic_progress": -6}, 0.43)
		], 0.9),
		_event("romance_crossroads", "感情支线开端", "你在活动和约会 App 之间认识了几个人。留学生活已经很难，亲密关系可能是支撑，也可能是新的风险。", "conditional", {"min_week": 9, "min_social": 35, "missing_flags": ["partner_cook", "partner_spender", "partner_unstable", "romance_slow"]}, [
			_choice("选择会一起做饭的对象", {"social": 5, "loneliness": -10, "stress": -3, "hunger": -10}, {"stress": 5, "loneliness": 4}, 0.74, {}, "partner_cook"),
			_choice("选择很会玩但花钱多的对象", {"social": 9, "loneliness": -12, "money": -90, "stress": -4}, {"money": -130, "stress": 6}, 0.68, {}, "partner_spender"),
			_choice("被热烈追求打动", {"social": 7, "loneliness": -14, "stress": -5}, {"stress": 8, "loneliness": 6}, 0.55, {}, "partner_unstable"),
			_choice("慢慢观察，不急着确定", {"social": 3, "stress": -2, "loneliness": -2}, {}, 1.0, {}, "romance_slow")
		], 1.2),
		_event("stable_partner_cooking", "稳定关系的一顿饭", "对方带了食材来宿舍一起做饭。你们聊课程、房租和未来，晚饭没有很贵，但很踏实。", "conditional", {"min_week": 11, "flag": "partner_cook"}, [
			_choice("一起备菜聊天", {"loneliness": -14, "hunger": -34, "stress": -6, "money": 12, "social": 4}),
			_choice("顺便做明天便当", {"loneliness": -10, "hunger": -42, "money": 28, "energy": -4}, {"stress": 3, "hunger": -18}, 0.76),
			_choice("聊清楚彼此边界", {"stress": -8, "social": 3, "loneliness": -6}, {"stress": 5}, 0.72, {}, "relationship_stable"),
			_choice("只享受今晚，不谈以后", {"loneliness": -8, "hunger": -24, "stress": -2})
		], 1.1),
		_event("expensive_partner_weekend", "高消费对象的周末计划", "对方发来餐厅、演出和邻城旅行链接，每一项都很心动，每一项都在烧钱。", "conditional", {"min_week": 11, "flag": "partner_spender"}, [
			_choice("AA 但设预算上限", {"social": 5, "loneliness": -7, "money": -55, "stress": 2}, {"money": -90, "stress": 7}, 0.72),
			_choice("硬着头皮全跟", {"social": 9, "loneliness": -12, "money": -220, "stress": 8, "academic_progress": -3}, {"money": -300, "stress": 14}, 0.48, {}, "romance_financial_pressure"),
			_choice("坦白说自己预算有限", {"stress": 4, "social": 2, "money": 20}, {"social": -4, "loneliness": 6, "stress": 8}, 0.68, {}, "relationship_boundaries"),
			_choice("拒绝这个周末", {"money": 40, "loneliness": 5, "academic_progress": 3})
		], 1.2),
		_event("romance_scam_risk", "被欺骗感情的风险", "对方开始频繁借钱、临时消失，又在你想退出时突然变得温柔。你意识到这可能不是普通矛盾。", "conditional", {"min_week": 12, "flag": "partner_unstable"}, [
			_choice("立刻停止转账并拉开距离", {"stress": 12, "loneliness": 10, "money": -40}, {"stress": 18, "loneliness": 15, "money": -90}, 0.72, {}, "heartbreak_recovered"),
			_choice("找朋友复盘聊天记录", {"social": 4, "stress": 6, "loneliness": 4}, {"stress": 12, "loneliness": 8}, 0.76, {}, "heartbreak_recovered"),
			_choice("继续相信对方", {"loneliness": -8, "money": -260, "stress": 10, "academic_progress": -5}, {"money": -420, "stress": 22, "loneliness": 18, "academic_progress": -8}, 0.38, {}, "romance_scammed"),
			_choice("当面摊牌", {"stress": 10, "social": 2, "loneliness": 8}, {"stress": 18, "money": -160, "loneliness": 12}, 0.58, {}, "heartbreak_recovered")
		], 1.5),
		_event("romance_bankruptcy_warning", "感情开销失控", "你翻开账单，发现这段关系已经不只是浪漫问题，而是现金流问题。下个月房租和保险都在等你。", "conditional", {"min_week": 13, "flag": "romance_financial_pressure", "max_money": 250}, [
			_choice("停止高消费约会", {"money": 80, "stress": 10, "loneliness": 8}, {"stress": 16, "money": -40}, 0.7, {}, "relationship_boundaries"),
			_choice("和对方谈清预算", {"social": 3, "stress": 8, "money": 30}, {"social": -6, "stress": 14}, 0.62, {}, "relationship_boundaries"),
			_choice("接更多班补窟窿", {"work_hours": 22, "energy": -28, "academic_progress": -7, "stress": 12}),
			_choice("继续刷卡维持体面", {"money": -380, "stress": 18, "academic_progress": -8}, {"money": -520, "stress": 24, "loneliness": 8}, 0.34, {}, "romance_bankrupt")
		], 1.4),
		_event("relationship_support_exam", "稳定关系的考前支持", "考试前一晚，对方没有拉你出去玩，而是给你留了安静时间和一盒饭。", "conditional", {"min_week": 16, "flag": "relationship_stable"}, [
			_choice("接受支持后继续复习", {"academic_progress": 6, "loneliness": -10, "hunger": -24, "stress": -8}),
			_choice("一起散步十分钟", {"stress": -10, "energy": 6, "loneliness": -8}),
			_choice("认真表达感谢", {"social": 4, "loneliness": -12, "stress": -4}),
			_choice("焦虑中有点冷淡", {"academic_progress": 3, "social": -2, "stress": 2})
		], 1.1),
		_event("library_friend", "图书馆熟脸", "你又在图书馆看到同一个同学，互相点了点头。", "random", {"min_week": 7}, [
			_choice("主动聊天", {"social": 5, "language": 2, "loneliness": -4}, {"stress": 3}, 0.75),
			_choice("继续学习", {"academic_progress": 4})
		], 1.1),
		_event("mailbox_shock", "信箱惊吓", "信箱里躺着一封看起来很正式的信。", "random", {"min_week": 4}, [
			_choice("马上拆开", {"visa_progress": 3, "stress": 2}),
			_choice("晚上再说", {"stress": 5})
		], 1.1),
		_event("spati_talk", "深夜便利店闲聊", "店员问你从哪里来，你突然多说了几句。", "random", {"min_week": 8}, [
			_choice("继续聊", {"language": 3, "loneliness": -3}),
			_choice("买完就走", {"energy": 2})
		], 0.8),
		_event("rainy_week", "连续阴雨", "天黑得很早，心情也跟着早退。", "random", {"min_week": 6}, [
			_choice("出门运动", {"stress": -7, "energy": 5}, {"energy": -4}, 0.75),
			_choice("宅在宿舍", {"energy": 8, "loneliness": 4})
		], 1.0),
		_event("course_forum", "课程论坛救命帖", "有人在 Moodle 里问了你也想问的问题。", "random", {"min_week": 5}, [
			_choice("认真看讨论", {"academic_progress": 5, "stress": -2}),
			_choice("顺手回复", {"academic_progress": 4, "social": 3}, {"stress": 2}, 0.8)
		], 1.2),
		_event("grocery_inflation", "超市价格刺眼", "你发现奶酪、鸡蛋和水果一起涨价了。", "random", {"min_week": 3}, [
			_choice("改做预算", {"money": 75, "stress": 2, "hunger": 4}),
			_choice("假装没看见", {"money": -60, "stress": -1, "hunger": -10})
		], 1.0),
		_event("bike_offer", "二手自行车", "有人低价出一辆自行车，刹车声很有存在感。", "random", {"min_week": 5, "min_money": 500}, [
			_choice("买下", {"money": -120, "energy": 8, "stress": -4}),
			_choice("算了", {"money": 20})
		], 0.9),
		_event("club_poster", "社团海报", "公告栏上有一个看起来不太尴尬的活动。", "random", {"min_week": 4}, [
			_choice("报名参加", {"social": 5, "language": 2, "loneliness": -4}, {"stress": 3}, 0.8),
			_choice("路过", {"energy": 2})
		], 1.0),
		_event("coding_hackathon", "Hackathon 邀请", "周末有场 Hackathon，披萨免费，睡眠自费。", "random", {"min_week": 11}, [
			_choice("参加", {"career_progress": 8, "social": 4, "energy": -15, "stress": 5}),
			_choice("备考优先", {"academic_progress": 5})
		], 0.8),
		_event("prof_reply", "教授回信", "教授竟然回复了，而且不是自动回复。", "random", {"min_week": 8, "flag": "prof_email_ok"}, [
			_choice("认真跟进", {"academic_progress": 5, "career_progress": 4, "stress": -2}),
			_choice("先收藏", {"stress": 2})
		], 1.3),
		_event("anna_coffee", "Anna 约咖啡", "Anna 说 presentation 可以顺便聊一下。", "random", {"min_week": 13, "flag": "anna_group"}, [
			_choice("去", {"social": 7, "language": 4, "loneliness": -5, "money": -12}),
			_choice("说太忙了", {"academic_progress": 2, "social": -2})
		], 1.2),
		_event("li_anxiety", "李同学转发群消息", "群里有人说这门课去年挂了一半。", "random", {"min_week": 9}, [
			_choice("核实信息", {"academic_progress": 3, "stress": 2}),
			_choice("停止看群", {"stress": -5, "loneliness": 1})
		], 1.0),
		_event("parents_package", "家里寄来的包裹", "里面有调料、药和一张写满叮嘱的纸。", "random", {"min_week": 7}, [
			_choice("好好视频感谢", {"loneliness": -8, "stress": -2}),
			_choice("收到就行", {"energy": 4})
		], 0.8),
		_event("tax_id_letter", "税号到了", "一封少见的好消息：Steuer-ID 到了。", "random", {"min_week": 6}, [
			_choice("归档收好", {"visa_progress": 3, "stress": -2}),
			_choice("随手一放", {"stress": 2})
		], 0.8),
		_event("laundry_fail", "洗衣事故", "你发现烘干机和你的衣服并没有达成共识。", "random", {"min_week": 3}, [
			_choice("冷静处理", {"stress": 3, "money": -20}),
			_choice("发给朋友吐槽", {"social": 2, "stress": -2})
		], 0.7),
		_event("mensa_surprise", "食堂惊喜", "今天 Mensa 居然挺好吃。", "random", {"min_week": 2}, [
			_choice("认真享受", {"energy": 7, "stress": -4, "money": -6, "hunger": -18}),
			_choice("拍照发群", {"social": 2, "stress": -2, "hunger": -10})
		], 1.2),
		_event("wrong_platform", "坐错站台", "你站在了正确车站的错误站台。", "random", {"min_week": 2}, [
			_choice("当作城市探索", {"language": 1, "stress": 3}),
			_choice("打车补救", {"money": -35, "stress": -2})
		], 0.7),
		_event("neighbor_noise", "邻居派对", "楼上低音持续到凌晨。", "random", {"min_week": 6}, [
			_choice("上楼沟通", {"language": 2, "stress": -2}, {"stress": 5}, 0.7),
			_choice("戴耳塞", {"energy": -4, "stress": 2})
		], 0.8),
		_event("bank_card_delay", "银行卡还没到", "冻结账户已激活，但 Girocard/借记卡还在路上；每个付款场景都像考试。", "random", {"min_week": 4, "max_visa": 60}, [
			_choice("联系银行", {"visa_progress": 4, "stress": 3}),
			_choice("先借朋友现金", {"social": 2, "stress": -2})
		], 0.9),
		_event("career_fair", "校园招聘会", "你拿到一堆传单，也拿到一点现实感。", "random", {"min_week": 12}, [
			_choice("认真投递", {"career_progress": 9, "language": 2, "stress": 4}),
			_choice("只逛一圈", {"career_progress": 3, "stress": -1})
		], 0.9),
		_event("exam_old_paper", "找到往年题", "网盘里出现了传说中的 Altklausur。", "random", {"min_week": 14}, [
			_choice("立刻刷", {"academic_progress": 8, "stress": 2}),
			_choice("分享给小组", {"academic_progress": 5, "social": 4})
		], 1.3),
		_event("sick_day", "感冒", "身体提醒你德国冬天不是背景贴图。", "random", {"min_week": 8}, [
			_choice("休息", {"energy": 10, "stress": -4, "academic_progress": -3}),
			_choice("硬去上课", {"academic_progress": 4, "energy": -12, "stress": 4})
		], 0.8),
		_event("roommate_help", "室友帮忙", "Cem 提醒你一个手续可以线上办。", "random", {"min_week": 7, "flag": "housing_stable"}, [
			_choice("请他一起看", {"visa_progress": 6, "social": 4, "loneliness": -3}),
			_choice("自己研究", {"visa_progress": 3, "language": 2})
		], 1.0),
		_event("moodle_down", "Moodle 崩了", "截止前一天，系统开始装死。", "random", {"min_week": 9}, [
			_choice("截图发邮件", {"academic_progress": 3, "language": 2, "stress": 2}),
			_choice("等它恢复", {"stress": 6})
		], 0.8),
		_event("refund", "意外退款", "之前多扣的一笔费用退回来了。", "random", {"min_week": 8}, [
			_choice("存起来", {"money": 120, "stress": -2}),
			_choice("改善伙食", {"money": 60, "energy": 8, "stress": -4, "hunger": -18})
		], 0.7),
		_event("winter_dark", "天黑太早", "下午四点像晚上八点。", "random", {"min_week": 11}, [
			_choice("买盏台灯", {"money": -25, "stress": -5, "energy": 4}),
			_choice("适应一下", {"loneliness": 3})
		], 0.9),
		_event("deadline_extension", "延期机会", "老师说可以申请一次延期，但需要合理理由。", "random", {"min_week": 15, "min_stress": 55}, [
			_choice("认真申请", {"academic_progress": 4, "stress": -7}, {"stress": 4}, 0.75),
			_choice("不申请", {"academic_progress": 2, "stress": 3})
		], 0.9),
		_event("quiet_success", "一个小小的顺利", "今天公交准点、邮件有人回、作业也写完了一页。", "random", {"min_week": 2}, [
			_choice("记住这种感觉", {"stress": -5, "energy": 5, "loneliness": -2})
		], 1.0),
		_event("registration_queue", "注册办公室排队", "队伍移动得很慢，但每个人手里都拿着一叠命运。", "random", {"min_week": 2, "max_week": 8}, [
			_choice("耐心排完", {"visa_progress": 5, "stress": 3}),
			_choice("先回去补材料", {"visa_progress": 2, "stress": -2})
		], 1.0),
		_event("sim_card_confusion", "电话卡套餐", "你发现同样叫 unlimited 的套餐也有很多限制。", "random", {"min_week": 1, "max_week": 6}, [
			_choice("认真比价", {"money": 45, "stress": 2}),
			_choice("随便买一个", {"money": -35, "energy": 4})
		], 0.9),
		_event("cash_only_place", "只收现金", "你以为可以刷卡，店员指了指门口的 ATM。", "random", {"min_week": 2}, [
			_choice("去取现金", {"stress": 2, "money": -5}),
			_choice("换一家店", {"energy": -3, "money": 10})
		], 0.8),
		_event("pfand_machine", "押金瓶机器", "机器吐回了两个瓶子，你开始怀疑瓶子也需要签证。", "random", {"min_week": 3}, [
			_choice("研究规则", {"money": 25, "language": 1}),
			_choice("下次再说", {"stress": -1})
		], 0.8),
		_event("sunday_closed", "周日超市关门", "你站在超市门口，和玻璃里的自己对视。", "random", {"min_week": 2}, [
			_choice("翻冰箱做饭", {"money": 25, "energy": -2, "hunger": -12}),
			_choice("点外卖", {"money": -28, "stress": -3, "hunger": -24})
		], 1.0),
		_event("semester_ticket", "学期票激活", "学期票不是自动出现在手机里的，你又学到一件事。", "conditional", {"min_week": 2, "max_visa": 50}, [
			_choice("立刻激活", {"visa_progress": 4, "money": 30}),
			_choice("先截图问同学", {"social": 2, "stress": -1})
		], 1.0),
		_event("lost_in_campus", "校园迷路", "楼号、入口和楼层像是三套不同系统。", "random", {"min_week": 2, "max_week": 7}, [
			_choice("问路", {"language": 2, "social": 2}, {"stress": 3}, 0.8),
			_choice("自己找", {"energy": -5, "stress": 2})
		], 0.9),
		_event("moodle_quiz", "Moodle 小测", "一个不起眼的小测突然算进平时分。", "conditional", {"min_week": 5, "max_academic": 60}, [
			_choice("立刻补做", {"academic_progress": 5, "stress": 3}),
			_choice("接受损失", {"stress": -2, "academic_progress": -3})
		], 1.0),
		_event("lab_partner_absent", "实验搭档失联", "小组实验快开始了，搭档头像安静得像默认设置。", "random", {"min_week": 7}, [
			_choice("自己先推进", {"academic_progress": 5, "stress": 5}),
			_choice("联系助教", {"academic_progress": 3, "language": 2}, {"stress": 4}, 0.75)
		], 0.9),
		_event("office_hour_full", "答疑预约满了", "教授的 office hour 比热门餐厅还难约。", "conditional", {"min_week": 8, "max_academic": 65}, [
			_choice("写清楚问题发邮件", {"academic_progress": 4, "language": 2}, {"stress": 3}, 0.75),
			_choice("找同学讨论", {"academic_progress": 3, "social": 3})
		], 1.0),
		_event("tutorium_help", "Tutorium 救场", "助教把一个你卡了三天的问题讲成了三分钟。", "random", {"min_week": 5}, [
			_choice("认真整理笔记", {"academic_progress": 6, "stress": -2}),
			_choice("课后提问", {"academic_progress": 5, "social": 2}, {"stress": 2}, 0.8)
		], 1.1),
		_event("exam_registration", "考试报名", "考试不是上课就自动报名，系统静静等你犯错。", "fixed", {"week": 9}, [
			_choice("马上报名", {"academic_progress": 2, "exam_readiness": 4, "visa_progress": 2, "stress": -3}, {}, 1.0, {}, "exam_registered"),
			_choice("报名后顺手查考纲", {"exam_readiness": 7, "academic_progress": 1, "stress": 1}, {}, 1.0, {}, "exam_registered"),
			_choice("先问同学报名流程", {"social": 3, "exam_readiness": 3, "stress": 1}, {"stress": 5}, 0.82, {"social": 0.003}, "exam_registered"),
			_choice("晚点再说", {"stress": 5, "exam_readiness": -4})
		]),
		_event("missed_exam_registration", "差点错过考试报名", "你突然想起考试报名截止就在今天。", "conditional", {"min_week": 10, "max_academic": 55}, [
			_choice("立刻补救", {"academic_progress": 3, "exam_readiness": 2, "stress": 7}, {}, 0.85, {"visa_progress": 0.002}, "exam_registered"),
			_choice("写邮件求助", {"language": 2, "exam_readiness": 1, "stress": 8}, {"academic_progress": -4, "exam_readiness": -6}, 0.6, {"language": 0.004}),
			_choice("请同学现场带路", {"social": 4, "exam_readiness": 2, "stress": 5}, {"stress": 10, "exam_readiness": -4}, 0.72, {"social": 0.004}, "exam_registered"),
			_choice("认了，下学期再说", {"stress": -4, "academic_progress": -10, "exam_readiness": -14}, {}, 1.0, {}, "needs_retake")
		], 1.0),
		_event("exercise_sheet_warning", "Übung 分数预警", "Moodle 上的练习分数提醒你：听懂课不等于会做题。", "fixed", {"week": 13}, [
			_choice("补三套练习题", {"exam_readiness": 10, "academic_progress": 3, "stress": 6}, {"stress": 10, "exam_readiness": 2}, 0.78, {"academic_progress": 0.003}),
			_choice("去 Tutorium 问清楚", {"exam_readiness": 7, "language": 2, "stress": 3}, {"stress": 7}, 0.74, {"language": 0.003}),
			_choice("和同学对答案", {"exam_readiness": 6, "social": 4, "stress": 2}, {"stress": 6, "exam_readiness": -2}, 0.68, {"social": 0.003}),
			_choice("先忙别的", {"stress": -2, "exam_readiness": -8, "academic_progress": -3})
		]),
		_event("klausur_countdown", "Klausur 倒计时两周", "日历上的考试日期突然变得很近，所有未完成的题都开始发光。", "fixed", {"week": 16}, [
			_choice("整理错题清单", {"exam_readiness": 12, "stress": 5}, {"stress": 9, "exam_readiness": 2}, 0.75, {"exam_readiness": 0.004}),
			_choice("约教授/助教答疑", {"exam_readiness": 8, "academic_progress": 3, "stress": 3}, {"stress": 9}, 0.66, {"language": 0.003, "academic_progress": 0.003}),
			_choice("和小组模拟考试", {"exam_readiness": 9, "social": 4, "stress": 4}, {"stress": 8, "exam_readiness": 1}, 0.7, {"social": 0.003}),
			_choice("继续拖延", {"energy": 5, "stress": -4, "exam_readiness": -12})
		]),
		_event("deutsch_phrase_win", "一句德语说顺了", "你在柜台前完整说完一句话，对方也完整听懂了。", "random", {"min_week": 5, "min_language": 30}, [
			_choice("乘胜追击多说两句", {"language": 4, "stress": -3}),
			_choice("见好就收", {"stress": -2})
		], 1.0),
		_event("accent_misunderstood", "口音误会", "你说了三遍，对方还是听成了另一个词。", "random", {"min_week": 4, "max_stress": 80}, [
			_choice("换个说法", {"language": 3, "stress": 2}, {"stress": 5}, 0.75),
			_choice("拿手机打字", {"visa_progress": 1, "stress": -1})
		], 0.9),
		_event("deep_l_trap", "翻译器陷阱", "翻译结果看起来很正式，正式到不像人话。", "random", {"min_week": 6}, [
			_choice("自己改一遍", {"language": 3, "academic_progress": 2}),
			_choice("直接发送", {"stress": -2}, {"stress": 5}, 0.65)
		], 0.9),
		_event("room_contract_clause", "租房合同条款", "合同里有一段 Nebenkosten，你读完更不确定了。", "conditional", {"min_week": 4, "max_visa": 55}, [
			_choice("请室友解释", {"visa_progress": 4, "social": 3}),
			_choice("自己查", {"language": 3, "stress": 3})
		], 1.0),
		_event("heating_argument", "暖气温度争论", "室友觉得 19 度很合理，你觉得南方人需要尊严。", "random", {"min_week": 10}, [
			_choice("开会协商", {"social": 3, "language": 2}, {"stress": 4}, 0.75),
			_choice("多穿一件", {"money": 10, "stress": 2})
		], 0.8),
		_event("trash_sorting_test", "垃圾分类考试", "你拿着包装盒，面对四个垃圾桶。", "random", {"min_week": 3}, [
			_choice("查清楚再扔", {"language": 1, "social": 2}),
			_choice("凭直觉", {"stress": -1}, {"social": -2, "stress": 3}, 0.6)
		], 0.8),
		_event("deposit_worry", "押金焦虑", "你开始担心退房时押金会不会完整回来。", "conditional", {"min_week": 9, "max_money": 1000}, [
			_choice("拍照留档", {"money": 60, "stress": -2}),
			_choice("先不想", {"stress": -3})
		], 0.8),
		_event("family_compare", "亲戚比较", "家里人转来一个同龄人已经工作的消息。", "conditional", {"min_week": 8, "min_stress": 45}, [
			_choice("少看消息", {"stress": -6, "loneliness": 2}),
			_choice("认真解释自己的节奏", {"stress": 4, "career_progress": 2})
		], 1.0),
		_event("parents_money_hint", "父母暗示开销", "父母说最近汇率又变了，你听懂了没说出口的压力。", "conditional", {"min_week": 7, "max_money": 1300}, [
			_choice("做预算表给他们看", {"money": 120, "stress": 3}),
			_choice("先安慰他们", {"loneliness": -3, "stress": 2})
		], 1.0),
		_event("homesick_food", "想家的一顿饭", "你突然很想吃家里的味道。", "random", {"min_week": 6, "min_loneliness": 40}, [
			_choice("自己复刻", {"loneliness": -7, "energy": 5, "money": -18, "hunger": -26}),
			_choice("去中餐馆", {"loneliness": -10, "money": -38, "stress": -3, "hunger": -32})
		], 1.0),
		_event("wechat_silence", "朋友圈沉默", "你发现自己越来越少发动态，因为不知道该怎么概括这一周。", "conditional", {"min_week": 10, "min_loneliness": 55}, [
			_choice("写一段真实记录", {"loneliness": -5, "stress": -2}),
			_choice("继续潜水", {"loneliness": 3, "energy": 2})
		], 0.9),
		_event("friend_back_home", "国内朋友升职", "朋友说升职了，你真心祝贺，也有一点恍惚。", "random", {"min_week": 12}, [
			_choice("祝贺并聊聊近况", {"loneliness": -4, "stress": 2}),
			_choice("关掉聊天", {"stress": -2, "loneliness": 3})
		], 0.8),
		_event("student_job_offer", "临时工机会", "一个同学说店里缺人，今晚就能试工。", "conditional", {"min_week": 8, "max_money": 1500}, [
			_choice("去试工", {"work_hours": 8, "energy": -20, "stress": 4}),
			_choice("婉拒", {"academic_progress": 3, "stress": -2})
		], 1.0),
		_event("boss_extra_shift", "老板加班请求", "老板说这周人手不够，希望你多来一次。", "random", {"min_week": 12}, [
			_choice("答应", {"work_hours": 8, "energy": -18, "academic_progress": -4}),
			_choice("拒绝", {"academic_progress": 4, "stress": 2})
		], 0.9),
		_event("payslip_question", "工资单疑惑", "工资单上每个扣款项目都像陌生词汇测试。", "random", {"min_week": 10}, [
			_choice("研究税和保险", {"career_progress": 3, "language": 2}),
			_choice("问同事", {"social": 3, "stress": -2})
		], 0.8),
		_event("hiwi_hint", "HiWi 暗示", "助教说下学期研究所有学生助理位置。", "conditional", {"min_week": 13, "min_academic": 55}, [
			_choice("主动询问", {"career_progress": 8, "academic_progress": 2}, {"stress": 3}, 0.75),
			_choice("先准备简历", {"career_progress": 5, "stress": 1})
		], 1.0),
		_event("linkedin_message", "LinkedIn 私信", "有人看了你的主页，但你还没写完项目经历。", "random", {"min_week": 12}, [
			_choice("完善主页", {"career_progress": 6, "stress": 2}),
			_choice("暂时忽略", {"energy": 3})
		], 0.8),
		_event("cv_language_choice", "简历语言选择", "你不知道该投英文简历还是德文简历。", "conditional", {"min_week": 14, "min_language": 35}, [
			_choice("做双语版本", {"career_progress": 7, "language": 2, "stress": 3}),
			_choice("先用英文", {"career_progress": 4})
		], 0.9),
		_event("career_doubt", "职业方向怀疑", "你突然不确定自己到底想留德、回国、读博还是转行。", "conditional", {"min_week": 15, "min_stress": 50}, [
			_choice("列路线利弊", {"career_progress": 5, "stress": -4}),
			_choice("先不想未来", {"stress": -5, "career_progress": -2})
		], 1.0),
		_event("presentation_applause", "Presentation 掌声", "讲完后有人点头，还有人真的鼓掌了两下。", "random", {"min_week": 14, "min_academic": 55}, [
			_choice("接受这个小胜利", {"academic_progress": 5, "social": 4, "stress": -5}),
			_choice("复盘不足", {"academic_progress": 4, "stress": 2})
		], 0.9),
		_event("presentation_freeze", "Presentation 卡壳", "你讲到一半忘了下一个词。", "random", {"min_week": 14, "max_stress": 85}, [
			_choice("看提示继续", {"language": 2, "stress": 4}, {"stress": 8}, 0.75),
			_choice("让队友接一下", {"social": -1, "stress": 3})
		], 0.8),
		_event("plagiarism_warning", "引用格式警告", "老师提醒引用格式不规范也可能出大问题。", "conditional", {"min_week": 11, "max_academic": 65}, [
			_choice("重整参考文献", {"academic_progress": 5, "stress": 3}),
			_choice("问图书馆课程", {"academic_progress": 4, "language": 2})
		], 0.9),
		_event("library_workshop", "图书馆文献课", "你学会了几个数据库，也学会了什么叫检索焦虑。", "random", {"min_week": 9}, [
			_choice("参加", {"academic_progress": 5, "career_progress": 2, "stress": -1}),
			_choice("跳过", {"energy": 4})
		], 0.8),
		_event("blocked_account_notice", "冻结账户提醒", "2026 年学生签证常见资金证明是 11,904 EUR/年。钱不是一次性可用，激活后通常每月最多释放 992 EUR。", "conditional", {"min_week": 6, "max_money": 900}, [
			_choice("按 992 EUR/月重做预算", {"stress": -4, "career_progress": 2}),
			_choice("误以为能一次取出", {"stress": 8, "money": -120}, {"stress": 10, "money": -180}, 0.35),
			_choice("问银行客服确认释放日", {"visa_progress": 3, "language": 2, "stress": 2}, {"stress": 5}, 0.7),
			_choice("先打工补现金流", {"work_hours": 8, "energy": -16, "stress": 4})
		], 1.0),
		_event("insurance_payment", "保险扣费", "学生公保和护理保险按月扣费。2026 年 TK 等公保学生费率常见约 141-146 EUR/月。", "random", {"min_week": 5}, [
			_choice("记入月度预算", {"money": -145, "stress": -1}),
			_choice("假装没看见", {"money": -145, "stress": 5}),
			_choice("核对年龄和护理保险费率", {"language": 2, "stress": 2}, {"stress": 5}, 0.72),
			_choice("联系保险公司改扣款账户", {"visa_progress": 2, "stress": 3}, {"stress": 6}, 0.68)
		], 0.8),
		_event("semester_fee_due", "学期费提醒", "学校发来 Semesterbeitrag 邮件。德国多数公立大学不是传统高学费，但学期费、学生会费和交通票仍要按时缴。", "fixed", {"week": 16}, [
			_choice("按时缴费", {"money": -320, "visa_progress": 5, "stress": -2}),
			_choice("先确认截止日期", {"stress": 3, "language": 1})
		]),
		_event("refund_from_landlord", "房东退小额费用", "房东说上月杂费多收了一点，给你退回来了。", "random", {"min_week": 11, "flag": "housing_stable"}, [
			_choice("存起来", {"money": 80, "stress": -2}),
			_choice("买点好吃的", {"money": 35, "energy": 5, "stress": -3, "hunger": -16})
		], 0.7),
		_event("city_registration_letter", "市政厅来信", "信不长，但你读了三遍才确定它不是坏消息。", "random", {"min_week": 7}, [
			_choice("归档", {"visa_progress": 3, "stress": -2}),
			_choice("问室友确认", {"visa_progress": 2, "social": 2})
		], 0.8),
		_event("train_strike", "火车罢工", "你计划好的路线突然变成谜题。", "random", {"min_week": 8}, [
			_choice("提前改路线", {"energy": -5, "stress": 3, "language": 1}),
			_choice("改线上学习", {"academic_progress": 3, "stress": -2})
		], 0.8),
		_event("bike_flat_tire", "自行车爆胎", "你终于拥有了德国生活的一项经典支线。", "random", {"min_week": 7}, [
			_choice("自己修", {"money": -15, "language": 2, "energy": -4}),
			_choice("去车店", {"money": -45, "stress": -2})
		], 0.7),
		_event("doctor_appointment", "预约医生", "你开始理解为什么大家说先打电话。", "conditional", {"min_week": 9, "min_stress": 55}, [
			_choice("打电话预约", {"language": 4, "stress": 3}, {"stress": 6}, 0.7),
			_choice("找线上预约", {"stress": -2, "visa_progress": 1})
		], 0.9),
		_event("pharmacy_advice", "药房建议", "药剂师说得很慢，你第一次觉得慢是一种善意。", "random", {"min_week": 8}, [
			_choice("认真听", {"language": 2, "energy": 5, "stress": -2}),
			_choice("照着买", {"money": -18, "energy": 4})
		], 0.7),
		_event("mental_health_webinar", "心理健康讲座", "学校发来讲座链接，主题像是专门写给你的。", "conditional", {"min_week": 10, "min_stress": 60}, [
			_choice("参加", {"stress": -10, "loneliness": -4}),
			_choice("收藏不看", {"stress": -1})
		], 1.0),
		_event("snow_day", "第一场雪", "雪把城市变得安静，也把路变得很滑。", "random", {"min_week": 12}, [
			_choice("出去走走", {"loneliness": -5, "stress": -4, "energy": -3}),
			_choice("在宿舍看雪", {"energy": 4, "loneliness": -2})
		], 0.8),
		_event("neighbor_greeting", "邻居打招呼", "你在楼梯间和邻居进行了一场 12 秒的德语对话。", "random", {"min_week": 5}, [
			_choice("多聊一句", {"language": 2, "social": 2}, {"stress": 2}, 0.8),
			_choice("礼貌结束", {"stress": -1})
		], 0.9),
		_event("international_potluck", "国际学生聚餐", "每个人都带了一道菜，也带来一点各自的故事。", "random", {"min_week": 9}, [
			_choice("带一道家乡菜", {"social": 7, "loneliness": -8, "money": -25, "hunger": -24}),
			_choice("只去聊天", {"social": 4, "loneliness": -4, "hunger": -12})
		], 1.0),
		_event("after_exam_void", "考后空虚", "考试结束了，但你没有想象中那么轻松。", "fixed", {"week": 19}, [
			_choice("休息半天", {"stress": -10, "energy": 12}),
			_choice("立刻复盘", {"academic_progress": 3, "stress": 3})
		])
	]

func _build_endings() -> void:
	ending_source = "hardcoded"
	endings = [
		_ending("forced_departure", "被迫离境", "居留风险没有及时补救，第一学期被行政程序直接打断。钱、成绩和社交都来不及结算，下一步只能先处理身份后果。", 120, {"flag": "deportation_order"}),
		_ending("cashflow_collapse", "现金流断裂", "账户不是紧张，而是已经断裂。饥饿、欠款和压力一起把学习计划挤到桌角，你这学期最重要的任务变成了先活下来。", 118, {"flag": "cashflow_crisis", "min_arrears": 1000, "min_hunger": 65, "min_stress": 65}),
		_ending("living_imbalance", "生活失衡", "你不是没有努力，只是基本生活已经失衡：吃饭、睡眠、现金流和课程全都互相拖拽。下学期要先重建生活秩序。", 116, {"min_cash_shortfall_count": 1, "min_hunger": 95, "max_energy": 35}),
		_ending("burnout_pause", "高压休整", "你把很多事扛到了最后，但压力已经超过学习能承受的范围。你决定暂停冲刺，先把人从系统里救出来。", 114, {"min_stress": 95, "max_academic": 60}),
		_ending("registration_failure", "注册失败", "学校注册没有及时完成，课程、考试报名和学生身份都被卡住。你花了生活费，却没真正进入学习循环。", 110, {"missing_flag": "school_registered"}),
		_ending("academic_failure", "考试失利", "你撑到了考试周，但平时进度、备考掌握度和状态没有形成闭环。第一学期最重要的反馈不是你不适合读书，而是学习系统需要重建。", 109, {"min_failed_courses": 1}),
		_ending("work_law_trouble", "打工违规风险", "为了现金流，你多次把打工时长或现金工风险推过合规边界。第一学期没有败给考试，而是败给了工时记录、居留解释和持续的法律焦虑。", 108, {"flag": "work_law_violation"}),
		_ending("romance_bankrupt", "感情破产", "你不是没有获得陪伴，而是为了维持一段失衡关系把现金流、学业节奏和自尊都透支了。下一步要先止损，再重建边界。", 105, {"flag": "romance_bankrupt"}),
		_ending("admin_collapse", "行政崩盘", "手续拖延滚成雪球，你的第一学期主线变成了和各个办公室通信。下学期还能救，但必须先把注册、保险、住址和居留链补上。", 100, {"max_visa": 45}),
		_ending("mental_crash", "心态爆炸", "你撑过了很多事，但压力和孤独已经压过了成长感。你决定先调整节奏，而不是继续硬扛。", 95, {"min_stress": 85, "min_loneliness": 70}),
		_ending("work_warrior", "打工战神", "账户余额稳住了，但课程进度开始危险。你很会生存，可下学期需要重新夺回学习时间。", 115, {"min_money": 1200, "min_career": 70, "min_annual_work_half_days": 20, "max_academic": 65, "max_arrears": 200, "max_hunger": 90, "max_failed_courses": 0, "flag": "school_registered"}),
		_ending("career_launch", "职业起步", "你没有只盯着考试，也没有只顾眼前生存。简历、邮件、项目和人脉开始连成一条职业路线。", 78, {"min_career": 80, "min_visa": 55, "max_stress": 80, "max_hunger": 70, "max_arrears": 300, "min_money": -500, "max_failed_courses": 0, "flag": "school_registered"}),
		_ending("delayed_enrollment", "延迟入学", "你最终把注册链路接上了，但错过窗口让本学期变成昂贵的缓冲期。下学期可以重新开始，只是钱包、心态和学业节奏都已经被拉长。", 74, {"flag": "registration_delayed"}),
		_ending("high_pressure_top_student", "学霸高压", "成绩很好，笔记很厚，黑眼圈也很德国。你证明了自己能学，但也该学会恢复。", 70, {"min_academic": 78, "min_exam_readiness": 65, "min_stress": 65, "max_stress": 89, "max_hunger": 75, "max_arrears": 300, "min_money": -500, "max_failed_courses": 0, "flag": "school_registered"}),
		_ending("social_connector", "社牛开局", "你不只活下来了，还在这座城市里建立了一点关系网。语言、朋友和机会开始互相推动。", 60, {"min_social": 90, "min_language": 45, "min_academic": 35, "min_exam_readiness": 40, "max_arrears": 300, "min_money": -500, "max_hunger": 70, "max_stress": 80, "max_failed_courses": 0, "flag": "school_registered"}),
		_ending("stable_start", "稳定开局", "你没有把每件事都做到完美，但学业、签证、金钱和心态都还在可控范围里。这是一个扎实的留德开局。", 10, {"min_academic": 45, "min_exam_readiness": 42, "min_visa": 50, "max_stress": 84, "max_hunger": 75, "max_arrears": 300, "min_money": -500, "max_failed_courses": 0, "flag": "school_registered"}),
		_ending("survival_struggle", "勉强撑住", "你撑到了学期末，但代价很清楚：课程、现金流或心态至少有一条线已经被拉到极限。下学期不是简单继续，而是先止血。", 1, {})
	]
