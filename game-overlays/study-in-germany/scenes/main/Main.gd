extends Control

const SimulationEngineScript := preload("res://scripts/simulation/SimulationEngine.gd")
const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")
const ExamResolverScript := preload("res://scripts/simulation/ExamResolver.gd")
const EndingResolverScript := preload("res://scripts/simulation/EndingResolver.gd")
const SaveManagerScript := preload("res://scripts/simulation/SaveManager.gd")
const RiskEvaluatorScript := preload("res://scripts/simulation/RiskEvaluator.gd")
const SemesterReportBuilderScript := preload("res://scripts/simulation/SemesterReportBuilder.gd")

var engine = SimulationEngineScript.new()
var current_event = null
var current_action_filter := "all"
var event_locale := "en"

var root_box: VBoxContainer
var title_label: Label
var subtitle_label: Label
var objective_label: Label
var stats_grid: GridContainer
var risk_label: Label
var action_filter_bar: HBoxContainer
var action_list: VBoxContainer
var plan_list: VBoxContainer
var log_view: RichTextLabel
var week_summary_label: Label
var primary_button: Button
var save_button: Button
var continue_button: Button
var difficulty_option: OptionButton
var event_panel: PanelContainer
var event_title: Label
var event_body: Label
var event_language_button: Button
var event_choices: VBoxContainer
var result_panel: PanelContainer
var result_title: Label
var result_body: RichTextLabel

func _ready() -> void:
	_build_ui()
	_show_title()
	EventBus.state_changed.connect(_refresh)
	EventBus.log_added.connect(func(_message: String) -> void: _refresh_logs())

func _build_ui() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)

	root_box = VBoxContainer.new()
	root_box.set_anchors_preset(Control.PRESET_FULL_RECT)
	root_box.add_theme_constant_override("separation", 12)
	root_box.offset_left = 18
	root_box.offset_top = 14
	root_box.offset_right = -18
	root_box.offset_bottom = -14
	add_child(root_box)

	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 16)
	root_box.add_child(header)

	var title_box := VBoxContainer.new()
	title_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(title_box)

	title_label = Label.new()
	title_label.text = "留德模拟器"
	title_label.add_theme_font_size_override("font_size", 30)
	title_box.add_child(title_label)

	subtitle_label = Label.new()
	subtitle_label.text = "从录取到第一学期结算：每周选 4 个行动，平衡学业、钱、签证和心态。"
	subtitle_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title_box.add_child(subtitle_label)

	var top_bar := HBoxContainer.new()
	top_bar.add_theme_constant_override("separation", 8)
	header.add_child(top_bar)

	var new_button := Button.new()
	new_button.text = "新游戏"
	new_button.pressed.connect(_start_new_game)
	top_bar.add_child(new_button)

	continue_button = Button.new()
	continue_button.text = "继续游戏"
	continue_button.pressed.connect(_continue_game)
	top_bar.add_child(continue_button)

	var difficulty_label := Label.new()
	difficulty_label.text = "难度"
	top_bar.add_child(difficulty_label)

	difficulty_option = OptionButton.new()
	difficulty_option.custom_minimum_size = Vector2(92, 0)
	_add_difficulty_item("easy", "轻松")
	_add_difficulty_item("normal", "标准")
	_add_difficulty_item("hard", "困难")
	_add_difficulty_item("realistic", "现实")
	difficulty_option.selected = 1
	difficulty_option.tooltip_text = "难度会影响每周生活压力、事件触发权重和事件选项成功率。"
	top_bar.add_child(difficulty_option)

	save_button = Button.new()
	save_button.text = "保存"
	save_button.pressed.connect(_save_game)
	top_bar.add_child(save_button)

	primary_button = Button.new()
	primary_button.text = "开始本周"
	primary_button.pressed.connect(_resolve_week)
	top_bar.add_child(primary_button)

	var main_row := HBoxContainer.new()
	main_row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	main_row.add_theme_constant_override("separation", 12)
	root_box.add_child(main_row)

	var left_panel := PanelContainer.new()
	left_panel.custom_minimum_size = Vector2(300, 0)
	main_row.add_child(left_panel)

	var left_box := VBoxContainer.new()
	left_box.add_theme_constant_override("separation", 8)
	left_panel.add_child(left_box)

	objective_label = Label.new()
	objective_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	objective_label.add_theme_font_size_override("font_size", 15)
	left_box.add_child(objective_label)

	var stats_title := Label.new()
	stats_title.text = "状态"
	stats_title.add_theme_font_size_override("font_size", 20)
	left_box.add_child(stats_title)

	stats_grid = GridContainer.new()
	stats_grid.columns = 2
	left_box.add_child(stats_grid)

	risk_label = Label.new()
	risk_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	risk_label.add_theme_font_size_override("font_size", 14)
	left_box.add_child(risk_label)

	var center_panel := PanelContainer.new()
	center_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	main_row.add_child(center_panel)

	var center_box := VBoxContainer.new()
	center_box.add_theme_constant_override("separation", 8)
	center_panel.add_child(center_box)

	var actions_title := Label.new()
	actions_title.text = "行动卡"
	actions_title.add_theme_font_size_override("font_size", 20)
	center_box.add_child(actions_title)

	action_filter_bar = HBoxContainer.new()
	action_filter_bar.add_theme_constant_override("separation", 6)
	center_box.add_child(action_filter_bar)
	_build_action_filters()

	var action_scroll := ScrollContainer.new()
	action_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	center_box.add_child(action_scroll)

	action_list = VBoxContainer.new()
	action_list.add_theme_constant_override("separation", 6)
	action_scroll.add_child(action_list)

	var right_panel := PanelContainer.new()
	right_panel.custom_minimum_size = Vector2(420, 0)
	main_row.add_child(right_panel)

	var right_box := VBoxContainer.new()
	right_box.add_theme_constant_override("separation", 8)
	right_panel.add_child(right_box)

	var plan_title := Label.new()
	plan_title.text = "本周计划"
	plan_title.add_theme_font_size_override("font_size", 20)
	right_box.add_child(plan_title)

	week_summary_label = Label.new()
	week_summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right_box.add_child(week_summary_label)

	plan_list = VBoxContainer.new()
	right_box.add_child(plan_list)

	var log_title := Label.new()
	log_title.text = "日志"
	log_title.add_theme_font_size_override("font_size", 20)
	right_box.add_child(log_title)

	var log_scroll := ScrollContainer.new()
	log_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_box.add_child(log_scroll)

	log_view = RichTextLabel.new()
	log_view.bbcode_enabled = true
	log_view.fit_content = true
	log_view.scroll_active = false
	log_view.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	log_view.custom_minimum_size = Vector2(380, 0)
	log_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	log_scroll.add_child(log_view)

	event_panel = PanelContainer.new()
	event_panel.visible = false
	event_panel.set_anchors_preset(Control.PRESET_CENTER)
	event_panel.custom_minimum_size = Vector2(760, 420)
	add_child(event_panel)

	var event_box := VBoxContainer.new()
	event_box.add_theme_constant_override("separation", 10)
	event_panel.add_child(event_box)

	event_title = Label.new()
	event_title.add_theme_font_size_override("font_size", 24)
	event_box.add_child(event_title)

	event_language_button = Button.new()
	event_language_button.text = "中文"
	event_language_button.tooltip_text = "Switch event language / 切换事件语言"
	event_language_button.pressed.connect(_toggle_event_locale)
	event_box.add_child(event_language_button)

	event_body = Label.new()
	event_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	event_box.add_child(event_body)

	event_choices = VBoxContainer.new()
	event_choices.add_theme_constant_override("separation", 6)
	event_box.add_child(event_choices)

	result_panel = PanelContainer.new()
	result_panel.visible = false
	result_panel.set_anchors_preset(Control.PRESET_CENTER)
	result_panel.custom_minimum_size = Vector2(760, 460)
	add_child(result_panel)

	var result_box := VBoxContainer.new()
	result_box.add_theme_constant_override("separation", 10)
	result_panel.add_child(result_box)

	result_title = Label.new()
	result_title.add_theme_font_size_override("font_size", 24)
	result_box.add_child(result_title)

	result_body = RichTextLabel.new()
	result_body.bbcode_enabled = true
	result_body.fit_content = false
	result_body.scroll_active = true
	result_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	result_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	result_body.custom_minimum_size = Vector2(680, 320)
	result_box.add_child(result_body)

	var close_result := Button.new()
	close_result.text = "回到标题"
	close_result.pressed.connect(_show_title)
	result_box.add_child(close_result)

func _add_difficulty_item(id: String, label: String) -> void:
	difficulty_option.add_item(label)
	difficulty_option.set_item_metadata(difficulty_option.item_count - 1, id)

func _build_action_filters() -> void:
	var filters := [
		["all", "全部"],
		["application", "申请季"],
		["study", "学业"],
		["language", "德语"],
		["admin", "行政"],
		["money", "金钱"],
		["social", "社交"],
		["life", "生活"],
		["mental", "心理"],
		["career", "职业"]
	]
	for item in filters:
		var tag := str(item[0])
		var button := Button.new()
		button.text = str(item[1])
		button.toggle_mode = true
		button.button_pressed = tag == current_action_filter
		button.pressed.connect(func() -> void:
			current_action_filter = tag
			_refresh_action_filters()
			_refresh_actions()
		)
		action_filter_bar.add_child(button)

func _refresh_action_filters() -> void:
	for child in action_filter_bar.get_children():
		if child is Button:
			child.button_pressed = child.text == _filter_label(current_action_filter)

func _filter_label(tag: String) -> String:
	var labels := {
		"all": "全部",
		"application": "申请季",
		"study": "学业",
		"language": "德语",
		"admin": "行政",
		"money": "金钱",
		"social": "社交",
		"life": "生活",
		"mental": "心理",
		"career": "职业"
	}
	return labels.get(tag, tag)

func _show_title() -> void:
	title_label.text = "留德模拟器"
	event_panel.visible = false
	result_panel.visible = false
	primary_button.disabled = true
	save_button.disabled = true
	continue_button.disabled = not SaveManagerScript.has_save()
	difficulty_option.disabled = false
	_select_difficulty_option(GameState.difficulty)
	_clear_container(action_list)
	_clear_container(plan_list)
	_clear_container(stats_grid)
	log_view.clear()
	objective_label.text = "目标：在 20 周内完成第一学期，避免行政崩盘、压力爆表和资金断裂。"
	risk_label.text = ""
	week_summary_label.text = "先点击“新游戏”，再从行动卡中选择本周 4 个行动。"
	_set_log_text(["选择新游戏开始 20 周留德 Demo，或继续上次存档。"])

func _start_new_game() -> void:
	GameState.reset()
	GameState.configure_run({"difficulty": _selected_difficulty()})
	engine.clear_plan()
	GameState.add_log("申请季开始。先通过 APS，再申请大学并进入德国第一学期。难度：%s。" % _difficulty_label(GameState.difficulty))
	_enter_game()

func _continue_game() -> void:
	if SaveManagerScript.load_game(GameState):
		engine.clear_plan()
		_select_difficulty_option(GameState.difficulty)
		GameState.add_log("读取存档。")
		_enter_game()

func _enter_game() -> void:
	result_panel.visible = false
	event_panel.visible = false
	save_button.disabled = false
	difficulty_option.disabled = true
	continue_button.disabled = true
	_refresh()
	if GameState.last_ending_id != "":
		_show_saved_ending()

func _refresh() -> void:
	title_label.text = "%s / 第 %d 学期 / %s / %s" % [_time_label(), GameState.semester, GameState.city, _difficulty_label(GameState.difficulty)]
	subtitle_label.text = _phase_text()
	_refresh_stats()
	_refresh_actions()
	_refresh_plan()
	_refresh_logs()
	primary_button.disabled = engine.used_slots() < SimulationEngineScript.MAX_ACTION_SLOTS or event_panel.visible or result_panel.visible

func _selected_difficulty() -> String:
	if difficulty_option == null or difficulty_option.selected < 0:
		return "normal"
	return str(difficulty_option.get_item_metadata(difficulty_option.selected))

func _select_difficulty_option(difficulty: String) -> void:
	if difficulty_option == null:
		return
	for index in range(difficulty_option.item_count):
		if str(difficulty_option.get_item_metadata(index)) == difficulty:
			difficulty_option.selected = index
			return
	difficulty_option.selected = 1

func _difficulty_label(difficulty: String) -> String:
	match difficulty:
		"easy":
			return "轻松"
		"hard":
			return "困难"
		"realistic":
			return "现实"
	return "标准"

func _refresh_stats() -> void:
	_clear_container(stats_grid)
	objective_label.text = _objective_text()
	var rows: Array = [
		["金钱", "%d EUR" % GameState.money, clampi(GameState.money / 30, 0, 100)],
		["冻结余额", "%d EUR" % GameState.blocked_account_balance, clampi(GameState.blocked_account_balance / 119, 0, 100)],
		["精力", "%d" % GameState.energy, GameState.energy],
		["压力", "%d" % GameState.stress, GameState.stress],
		["孤独", "%d" % GameState.loneliness, GameState.loneliness],
		["饥饿", "%d" % GameState.hunger, GameState.hunger],
		["学业", "%d" % GameState.academic_progress, GameState.academic_progress],
		["备考", "%d" % GameState.exam_readiness, GameState.exam_readiness],
		["德语", "%d" % GameState.language, GameState.language],
		["社交", "%d" % GameState.social, GameState.social],
		["职业", "%d" % GameState.career_progress, GameState.career_progress],
		["大学成绩", "%d" % GameState.gpa_score, GameState.gpa_score],
		["专业复习", "%d" % GameState.aps_knowledge, GameState.aps_knowledge],
		["APS", "%d" % GameState.aps_score, GameState.aps_score],
		["TestDaF", GameState.testdaf_label(), 100 if GameState.has_testdaf_4x4() else 45],
		["本周工时", "%d / 20h" % GameState.current_week_work_hours, clampi(GameState.current_week_work_hours * 5, 0, 100)],
		["年度半天", "%d / 280" % GameState.annual_work_half_days, clampi(GameState.annual_work_half_days * 100 / 280, 0, 100)],
		["挂科", "%d" % GameState.failed_courses, clampi(GameState.failed_courses * 50, 0, 100)]
	]
	for row in rows:
		var key := Label.new()
		key.text = "%s\n%s" % [row[0], row[1]]
		stats_grid.add_child(key)
		var bar := ProgressBar.new()
		bar.custom_minimum_size = Vector2(150, 18)
		bar.min_value = 0
		bar.max_value = 100
		bar.value = int(row[2])
		bar.show_percentage = false
		stats_grid.add_child(bar)
	risk_label.text = _risk_text()
	var top_risks := _top_risk_text()
	if top_risks != "":
		risk_label.text += "\n\n%s" % top_risks
	if GameState.week <= 0:
		risk_label.text += "\n大学档位：%s" % GameState.university_tier

func _refresh_actions() -> void:
	_clear_container(action_list)
	for action in DataRegistry.actions:
		if not action.can_use(GameState) and action.disabled_reason(GameState) == "当前阶段已错过":
			continue
		if current_action_filter != "all" and not action.tags.has(current_action_filter):
			continue
		var action_ref = action
		var card := PanelContainer.new()
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		action_list.add_child(card)

		var row := VBoxContainer.new()
		row.add_theme_constant_override("separation", 4)
		card.add_child(row)

		var button := Button.new()
		button.custom_minimum_size = Vector2(0, 36)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.text = action_ref.name
		button.tooltip_text = action_ref.description
		button.disabled = not engine.can_add_action(action_ref)
		if not action_ref.can_use(GameState):
			button.text += "（%s）" % action_ref.disabled_reason(GameState)
		button.pressed.connect(func() -> void:
			if engine.add_action(action_ref):
				_refresh()
		)
		row.add_child(button)

		var detail := Label.new()
		detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		detail.text = "%s\n%s" % [action_ref.description, _action_detail(action_ref)]
		row.add_child(detail)

func _action_detail(action) -> String:
	var parts: Array[String] = []
	if action.cost_energy > 0:
		parts.append("精力 -%d" % action.cost_energy)
	if action.cost_money > 0:
		parts.append("金钱 -%d" % action.cost_money)
	for key in action.effects.keys():
		parts.append(_effect_part(str(key), int(action.effects[key])))
	return "；".join(parts)

func _refresh_plan() -> void:
	_clear_container(plan_list)
	var used := engine.used_slots()
	var header := Label.new()
	header.text = "行动槽：%d / %d" % [used, SimulationEngineScript.MAX_ACTION_SLOTS]
	plan_list.add_child(header)
	week_summary_label.text = _plan_summary()
	for index in range(engine.planned_actions.size()):
		var action = engine.planned_actions[index]
		var action_index := index
		var row := HBoxContainer.new()
		plan_list.add_child(row)
		var label := Label.new()
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.text = "%d. %s" % [index + 1, action.name]
		row.add_child(label)
		var remove := Button.new()
		remove.text = "移除"
		remove.pressed.connect(func() -> void:
			engine.remove_action(action_index)
			_refresh()
		)
		row.add_child(remove)
	for empty in range(SimulationEngineScript.MAX_ACTION_SLOTS - used):
		var label := Label.new()
		label.text = "- 空行动槽"
		plan_list.add_child(label)

func _refresh_logs() -> void:
	var start_index := maxi(0, GameState.event_log.size() - 12)
	var lines: Array[String] = []
	for index in range(start_index, GameState.event_log.size()):
		lines.append(GameState.event_log[index])
	_set_log_text(lines)

func _set_log_text(lines: Array[String]) -> void:
	if log_view == null:
		return
	log_view.clear()
	for line in lines:
		log_view.append_text("• %s\n\n" % line)

func _resolve_week() -> void:
	if engine.used_slots() < SimulationEngineScript.MAX_ACTION_SLOTS:
		return
	current_event = engine.resolve_week()
	if current_event != null:
		_show_event(current_event)
	else:
		_after_event_or_week()
	_refresh()

func _toggle_event_locale() -> void:
	event_locale = "zh" if event_locale == "en" else "en"
	event_language_button.text = "English" if event_locale == "zh" else "中文"
	if current_event != null:
		_show_event(current_event)

func _show_event(event) -> void:
	event_panel.visible = true
	event_title.text = event.localized_title(event_locale)
	event_body.text = "%s\n\n%s" % [
		event.localized_body(event_locale),
		"Your current state changes each option's success chance. Higher is safer, but every choice has a tradeoff." if event_locale == "en" else "当前状态会影响选项成功率。成功率越高越稳，但每个选项的收益和代价不同。"
	]
	_clear_container(event_choices)
	for choice in event.choices:
		if not choice.is_available(GameState):
			continue
		var choice_ref = choice
		var button := Button.new()
		var chance := roundi(EventResolverScript.get_success_rate(choice_ref, GameState) * 100.0)
		button.text = (
			"%s (Success chance %d%%)\nSuccess: %s\nFailure: %s"
			if event_locale == "en"
			else "%s（成功率 %d%%）\n成功：%s\n失败：%s"
		) % [
			choice_ref.localized_text(event_locale),
			chance,
			_event_effect_detail(choice_ref.success_effects),
			_event_effect_detail(choice_ref.failure_effects)
		]
		button.tooltip_text = "Chance after current-state modifiers." if event_locale == "en" else EventResolverScript.describe_success_rate(choice_ref, GameState)
		button.pressed.connect(func() -> void:
			EventResolverScript.resolve_choice(event, choice_ref, GameState)
			event_panel.visible = false
			_after_event_or_week()
			_refresh()
		)
		event_choices.add_child(button)
	if event_choices.get_child_count() == 0:
		var close := Button.new()
		close.text = "Continue" if event_locale == "en" else "继续"
		close.pressed.connect(func() -> void:
			GameState.mark_event_completed(event.id)
			event_panel.visible = false
			_after_event_or_week()
			_refresh()
		)
		event_choices.add_child(close)

func _after_event_or_week() -> void:
	GameState.record_week_snapshot("week_end")
	if GameState.week >= 20:
		_show_exam_and_ending()
	else:
		engine.finish_week()

func _show_exam_and_ending() -> void:
	var exam := ExamResolverScript.resolve_exam(GameState)
	var ending = EndingResolverScript.resolve_ending(DataRegistry.endings, GameState)
	if ending == null:
		ending = DataRegistry.get_ending_by_id("stable_start")
	GameState.last_ending_id = ending.id
	SaveManagerScript.save_game(GameState)
	result_panel.visible = true
	result_title.text = ending.title
	var registration_text := "已注册" if GameState.flags.has("school_registered") else "未注册"
	var visa_text := "居留已确认" if GameState.flags.has("visa_valid") else "居留未确认"
	result_body.text = "[b]考试结果[/b]\n分数：%s\n德国成绩：%s（%s）\n平时学业：%d / 备考掌握：%d / 挂科：%d\n\n[b]结局[/b]\n%s\n\n%s\n\n[b]期末状态[/b]\n学业 %d / 备考 %d / 德语 %d / 社交 %d / 金钱 %d / 压力 %d / 孤独 %d / 饥饿 %d / 工时 %dh / 年度半天 %d / %s / %s" % [
		exam["score"],
		exam["grade"],
		exam["summary"],
		exam.get("academic_progress", GameState.academic_progress),
		exam.get("exam_readiness", GameState.exam_readiness),
		GameState.failed_courses,
		ending.description,
		SemesterReportBuilderScript.build_report(GameState, DataRegistry.actions),
		GameState.academic_progress,
		GameState.exam_readiness,
		GameState.language,
		GameState.social,
		GameState.money,
		GameState.stress,
		GameState.loneliness,
		GameState.hunger,
		GameState.current_week_work_hours,
		GameState.annual_work_half_days,
		registration_text,
		visa_text
	]
	primary_button.disabled = true
	save_button.disabled = false

func _show_saved_ending() -> void:
	var ending = DataRegistry.get_ending_by_id(GameState.last_ending_id)
	if ending == null:
		return
	var exam := GameState.last_exam_result
	result_panel.visible = true
	result_title.text = ending.title
	result_body.text = "[b]已读取结局[/b]\n分数：%s\n德国成绩：%s（%s）\n\n[b]结局[/b]\n%s\n\n%s" % [
		exam.get("score", "-"),
		exam.get("grade", "-"),
		exam.get("summary", "-"),
		ending.description,
		SemesterReportBuilderScript.build_report(GameState, DataRegistry.actions)
	]
	primary_button.disabled = true

func _save_game() -> void:
	if SaveManagerScript.save_game(GameState):
		GameState.add_log("已保存。")
	else:
		GameState.add_log("保存失败。")
	_refresh()

func _clear_container(container: Node) -> void:
	for child in container.get_children():
		container.remove_child(child)
		child.free()

func _phase_text() -> String:
	if GameState.week <= 0:
		return "阶段：APS 与申请季。补齐材料、语言、专业复习和资金，通过 APS 后才能进入德国第一学期。"
	if GameState.week <= 4:
		return "阶段：抵达与安顿。优先把住宿、保险、银行、学校注册和基础适应稳住。"
	if GameState.week <= 9:
		return "阶段：注册与课程启动。行政不要拖，学业也要跟上。"
	if GameState.week <= 14:
		return "阶段：路线分化。你可以偏向学业、社交、职业或打工，但代价会开始显现。"
	if GameState.week <= 18:
		return "阶段：考试压力。控制压力，补足学业，别让行政和钱爆雷。"
	return "阶段：学期结算。最后几周会决定你的第一学期结局。"

func _objective_text() -> String:
	if GameState.week <= 0:
		return "本周目标：让 APS 条件达标。参加 APS 审核需要钱够、材料齐、语言和专业复习达标；APS 分数决定可申请大学档位。"
	return "本周目标：选满 4 个行动后开始本周。第 20 周会根据学业、居留/注册状态、压力、金钱、社交和职业给出结局。"

func _risk_text() -> String:
	var risks: Array[String] = []
	if GameState.money < 0:
		risks.append("资金为负")
	elif GameState.money < 500:
		risks.append("资金紧张")
	if GameState.stress >= 80:
		risks.append("压力危险")
	elif GameState.stress >= 60:
		risks.append("压力偏高")
	if GameState.week <= 0:
		if not GameState.flags.has("aps_documents_ready"):
			risks.append("APS 材料未齐")
		if not GameState.flags.has("testdaf_passed"):
			risks.append("TestDaF 未达 4x4")
		if GameState.aps_knowledge < 45:
			risks.append("专业复习不足")
		if GameState.money < 250:
			risks.append("APS 费用不足")
		if GameState.flags.has("aps_passed"):
			risks.append("APS 已通过")
		if risks.is_empty():
			return "风险：APS 条件接近可提交。"
		return "风险：" + " / ".join(risks)
	if not GameState.flags.has("school_registered") and GameState.week >= 2:
		risks.append("未完成学校注册")
	if GameState.flags.has("registration_delayed"):
		risks.append("注册已延期")
	if not GameState.flags.has("testdaf_passed") and GameState.week >= 1:
		risks.append("TestDaF 未达 4x4")
	if not GameState.flags.has("visa_valid") and GameState.week >= 12:
		risks.append("居留状态未确认")
	if GameState.current_week_work_hours > GameState.LEGAL_WEEKLY_WORK_HOURS:
		risks.append("本周工时超 20 小时")
	if GameState.flags.has("work_law_violation"):
		risks.append("打工合规风险")
	elif GameState.flags.has("work_limit_exceeded"):
		risks.append("工时曾经越线")
	if GameState.academic_progress < 40 and GameState.week >= 10:
		risks.append("学业落后")
	if GameState.exam_readiness < 40 and GameState.week >= 12:
		risks.append("备考不足")
	if GameState.failed_courses > 0:
		risks.append("需要补考/重修")
	if GameState.loneliness >= 70:
		risks.append("孤独偏高")
	if GameState.hunger >= 75:
		risks.append("饥饿影响学习")
	if GameState.flags.has("romance_financial_pressure"):
		risks.append("感情开销失控")
	if GameState.flags.has("romance_scammed"):
		risks.append("感情欺骗创伤")
	if risks.is_empty():
		return "风险：当前没有明显红灯。"
	return "风险：" + " / ".join(risks)

func _top_risk_text() -> String:
	var top_risks: Array = RiskEvaluatorScript.get_top_risks(GameState, 3)
	if top_risks.is_empty():
		return ""
	var lines: Array[String] = ["当前最危险："]
	for risk in top_risks:
		var actions: Array = risk.get("suggested_actions", [])
		var action_text := "；建议：" + "、".join(_action_names(actions)) if not actions.is_empty() else ""
		lines.append("- %s %d/100：%s%s" % [
			str(risk.get("title", "")),
			int(risk.get("score", 0)),
			str(risk.get("body", "")),
			action_text
		])
	return "\n".join(lines)

func _action_names(action_ids: Array) -> Array[String]:
	var names: Array[String] = []
	for action_id in action_ids:
		var action = DataRegistry.get_action_by_id(str(action_id))
		names.append(action.name if action != null else str(action_id))
	return names

func _time_label() -> String:
	if GameState.week <= 0:
		return "申请季第 %d 周" % (GameState.week + 9)
	return "第 %d 周" % GameState.week

func _plan_summary() -> String:
	if engine.planned_actions.is_empty():
		return "本周还没有计划。点击中间行动卡加入计划。"
	var effects: Dictionary = {}
	var energy_cost := 0
	var money_cost := 0
	for action in engine.planned_actions:
		energy_cost += action.cost_energy
		money_cost += action.cost_money
		for key in action.effects.keys():
			effects[key] = int(effects.get(key, 0)) + int(action.effects[key])
	if energy_cost > 0:
		effects["energy"] = int(effects.get("energy", 0)) - energy_cost
	if money_cost > 0:
		effects["money"] = int(effects.get("money", 0)) - money_cost
	return "本周预估：" + _effect_detail(effects)

func _event_effect_detail(effects: Dictionary) -> String:
	if event_locale == "zh":
		return _effect_detail(effects)
	if effects.is_empty():
		return "No change"
	var parts: Array[String] = []
	for key in effects.keys():
		var amount := int(effects[key])
		if amount != 0:
			parts.append("%s %+d" % [_event_stat_label(str(key)), amount])
	return "No change" if parts.is_empty() else ", ".join(parts)

func _event_stat_label(key: String) -> String:
	var labels := {
		"money": "Money", "energy": "Energy", "stress": "Stress",
		"hunger": "Hunger", "loneliness": "Loneliness",
		"academic_progress": "Academic progress", "exam_readiness": "Exam readiness",
		"language": "Language", "social": "Social", "visa_progress": "Visa progress",
		"career_progress": "Career progress", "work_hours": "Work hours",
		"illegal_work_hours": "Illegal work hours", "aps_knowledge": "APS knowledge"
	}
	return str(labels.get(key, key.replace("_", " ").capitalize()))

func _effect_detail(effects: Dictionary) -> String:
	if effects.is_empty():
		return "无变化"
	var parts: Array[String] = []
	for key in effects.keys():
		var amount := int(effects[key])
		if amount == 0:
			continue
		parts.append(_effect_part(str(key), amount))
	if parts.is_empty():
		return "无变化"
	return "，".join(parts)

func _effect_part(key: String, amount: int) -> String:
	if key == "work_hours":
		var income: int = GameState.legal_work_income_for_hours(amount)
		return "%s %+d（合法工资 %+d）" % [GameState.stat_label(key), amount, income]
	if key == "illegal_work_hours":
		var income: int = GameState.illegal_work_income_for_hours(amount)
		return "%s %+d（现金 %+d）" % [GameState.stat_label(key), amount, income]
	return "%s %+d" % [GameState.stat_label(key), amount]
