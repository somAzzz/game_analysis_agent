extends SceneTree

const EventResolverScript := preload("res://scripts/simulation/EventResolver.gd")

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var data_registry: Node = root.get_node("/root/DataRegistry")
	var game_state: Node = root.get_node("/root/GameState")
	var lines: Array[String] = [
		"# 事件选项数值平衡表",
		"",
		"本文件由 `scripts/tools/ExportEventChoiceBalance.gd` 从 `autoload/DataRegistry.gd` 生成。",
		"",
		"当前事件数：%d；当前选项数：%d。" % [data_registry.events.size(), _choice_count(data_registry.events)],
		"",
		"属性名：金钱、冻结余额、精力、压力、孤独、饥饿、学业、德语、社交、行政熟练度、职业。行政熟练度不作为仪表盘普通进度条展示，主要用于邮件、Termin 和材料处理检定；学校注册和居留状态由隐藏 flag 判断。",
		""
	]
	for index in range(data_registry.events.size()):
		var event = data_registry.events[index]
		lines.append("## %03d. %s `%s`" % [index + 1, event.title, event.id])
		lines.append("")
		lines.append("- 类型：`%s`" % event.event_type)
		lines.append("- 触发：`%s`" % JSON.stringify(event.trigger))
		lines.append("- 文本：%s" % event.body)
		lines.append("")
		lines.append("| 选项 | 基础成功率 | 成功变化 | 失败变化 | 成功率影响 | 设置 flag |")
		lines.append("| --- | ---: | --- | --- | --- | --- |")
		for choice in event.choices:
			lines.append("| %s | %d%% | %s | %s | %s | %s |" % [
				_escape_cell(choice.text),
				roundi(float(choice.success_rate) * 100.0),
				_escape_cell(_effect_detail(choice.success_effects, game_state)),
				_escape_cell(_effect_detail(choice.failure_effects, game_state)),
				_escape_cell(_modifier_detail(choice.success_modifiers, game_state)),
				_escape_cell(choice.set_flag if choice.set_flag != "" else "-")
			])
		lines.append("")
	_write_text(ProjectSettings.globalize_path("res://docs/05_event_choice_balance.md"), "\n".join(lines) + "\n")
	print("Exported event choice balance: %d events, %d choices" % [data_registry.events.size(), _choice_count(data_registry.events)])
	quit(0)

func _choice_count(events: Array) -> int:
	var total := 0
	for event in events:
		total += event.choices.size()
	return total

func _effect_detail(effects: Dictionary, game_state: Node) -> String:
	if effects.is_empty():
		return "-"
	var parts: Array[String] = []
	for key in effects.keys():
		var key_name := str(key)
		var amount := int(effects[key])
		if key_name == "work_hours":
			var income: int = game_state.legal_work_income_for_hours(amount)
			parts.append("%s %+d（合法工资 %+d）" % [game_state.stat_label(key_name), amount, income])
		elif key_name == "illegal_work_hours":
			var income: int = game_state.illegal_work_income_for_hours(amount)
			parts.append("%s %+d（现金 %+d）" % [game_state.stat_label(key_name), amount, income])
		else:
			parts.append("%s %+d" % [game_state.stat_label(key_name), amount])
	return "，".join(parts)

func _modifier_detail(modifiers: Dictionary, game_state: Node) -> String:
	if modifiers.is_empty():
		return "固定检定"
	var parts: Array[String] = []
	for key in modifiers.keys():
		var value := float(modifiers[key])
		var sign := "+" if value >= 0.0 else ""
		parts.append("%s %s%.3f" % [game_state.stat_label(str(key)), sign, value])
	return "；".join(parts)

func _escape_cell(value: String) -> String:
	return value.replace("|", "\\|").replace("\n", " ")

func _write_text(path: String, text: String) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file = FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(text)
		file.close()
