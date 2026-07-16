class_name SemesterReportBuilder
extends RefCounted

static func build_report(state: Node, actions: Array) -> String:
	var lines: Array[String] = []
	lines.append("[b]第一学期报告[/b]")
	lines.append("路线画像：%s" % _route_profile(state))
	lines.append("最常用行动：%s" % _most_used_action_text(state, actions))
	lines.append("最难的一周：%s" % _worst_week_text(state))
	lines.append("文件夹痕迹：%s" % _paperwork_text(state))
	lines.append("关系与家庭：%s" % _relationship_text(state))
	lines.append("打工与风险：%s" % _work_text(state))
	lines.append("一句话总结：%s" % _one_line_summary(state))
	return "\n".join(lines)

static func _route_profile(state: Node) -> String:
	var counts := _tag_counts(state)
	var route_scores := {
		"学业线": int(counts.get("study", 0)) + int(counts.get("language", 0)),
		"行政线": int(counts.get("admin", 0)) + int(counts.get("application", 0)),
		"打工线": int(counts.get("money", 0)) + int(counts.get("career", 0)),
		"社交线": int(counts.get("social", 0)) + int(counts.get("life", 0)),
		"恢复线": int(counts.get("mental", 0)) + int(counts.get("recovery", 0))
	}
	var ordered := route_scores.keys()
	ordered.sort_custom(func(a, b) -> bool: return int(route_scores[a]) > int(route_scores[b]))
	var primary := str(ordered[0]) if not ordered.is_empty() else "混合线"
	var secondary := str(ordered[1]) if ordered.size() > 1 else "无明显副线"
	return "%s为主，%s为辅。" % [primary, secondary]

static func _most_used_action_text(state: Node, actions: Array) -> String:
	if state.action_history.is_empty():
		return "还没有足够行动记录。"
	var counts: Dictionary = {}
	for item in state.action_history:
		var action_id := str(item.get("action_id", ""))
		if action_id == "":
			continue
		counts[action_id] = int(counts.get(action_id, 0)) + 1
	if counts.is_empty():
		return "还没有足够行动记录。"
	var best_id := ""
	var best_count := 0
	for action_id in counts.keys():
		var count := int(counts[action_id])
		if count > best_count:
			best_id = str(action_id)
			best_count = count
	var action_name := _action_name(best_id, actions)
	return "%s x%d" % [action_name, best_count]

static func _worst_week_text(state: Node) -> String:
	if state.weekly_snapshots.is_empty():
		return "没有记录到明显低谷。"
	var worst: Dictionary = {}
	var worst_score := -INF
	for snapshot in state.weekly_snapshots:
		if int(snapshot.get("week", 0)) < 1:
			continue
		var score := float(snapshot.get("pressure_score", 0))
		if score > worst_score:
			worst_score = score
			worst = snapshot
	if worst.is_empty():
		for snapshot in state.weekly_snapshots:
			var score := float(snapshot.get("pressure_score", 0))
			if score > worst_score:
				worst_score = score
				worst = snapshot
	if worst.is_empty():
		return "没有记录到明显低谷。"
	return "第 %d 周，压力 %d、饥饿 %d、现金 %d EUR。" % [
		int(worst.get("week", 0)),
		int(worst.get("stress", 0)),
		int(worst.get("hunger", 0)),
		int(worst.get("money", 0))
	]

static func _paperwork_text(state: Node) -> String:
	var fragments: Array[String] = []
	fragments.append("APS %s" % ("已过" if state.flags.has("aps_passed") else "未过"))
	fragments.append("TestDaF %s" % state.testdaf_label())
	fragments.append("注册%s" % ("完成" if state.flags.has("school_registered") else "未完成"))
	fragments.append("居留%s" % ("确认" if state.flags.has("visa_valid") else "未确认"))
	var email_count := _action_count(state, "write_email_practice") + _completed_count(state, ["prof_email", "prof_reply", "termin_missing", "visa_status_hidden_check"])
	if email_count > 0:
		fragments.append("关键邮件/沟通 %d 次" % email_count)
	return "，".join(fragments)

static func _relationship_text(state: Node) -> String:
	var parent_count := _action_count(state, "budget_call") + _completed_count(state, ["parents_future", "parents_money_hint", "parents_package", "family_compare"])
	var fragments: Array[String] = []
	if state.flags.has("relationship_stable") or state.flags.has("partner_cook"):
		fragments.append("稳定关系提供了生活支持")
	elif state.flags.has("romance_bankrupt") or state.flags.has("romance_scammed"):
		fragments.append("感情线带来了明显损耗")
	elif state.flags.has("romance_slow"):
		fragments.append("感情线保持谨慎观察")
	else:
		fragments.append("感情线不是本局主轴")
	if parent_count > 0:
		fragments.append("家庭/父母沟通 %d 次" % parent_count)
	if state.loneliness >= 70:
		fragments.append("孤独感仍然偏高")
	elif state.loneliness <= 30:
		fragments.append("孤独感控制得不错")
	return "，".join(fragments)

static func _work_text(state: Node) -> String:
	var legal_hours := 0
	var illegal_hours := 0
	for item in state.action_history:
		var action_id := str(item.get("action_id", ""))
		if action_id == "part_time_job":
			legal_hours += 10
		elif action_id == "mini_job_extra":
			legal_hours += 18
		elif action_id == "illegal_cash_work":
			illegal_hours += 8
	var temptations := _completed_count(state, ["desperate_illegal_work_offer", "illegal_cash_job_offer", "illegal_work_followup"])
	var fragments: Array[String] = []
	fragments.append("合法打工约 %d 小时" % legal_hours)
	if illegal_hours > 0:
		fragments.append("黑工约 %d 小时" % illegal_hours)
	elif temptations > 0:
		fragments.append("遭遇黑工诱惑 %d 次但没有形成主轴" % temptations)
	if state.flags.has("work_law_violation"):
		fragments.append("合规风险已升级")
	elif state.flags.has("work_limit_exceeded"):
		fragments.append("曾经越过每周 20 小时红线")
	return "，".join(fragments)

static func _one_line_summary(state: Node) -> String:
	if state.flags.has("deportation_order"):
		return "这一局真正的 boss 是居留身份。"
	if state.failed_courses > 0:
		return "你撑到了期末，但学习系统需要重建。"
	if state.arrears_amount > 0 and state.hunger >= 70:
		return "你不是没努力，是生活成本一直在追着你跑。"
	if state.social >= 75:
		return "你在德国建立了一点关系网，它开始反过来托住你。"
	if state.academic_progress >= 75 and state.exam_readiness >= 65:
		return "这是一条很硬的学业路线，代价是持续高压。"
	return "你把第一学期变成了一个还算可控的开局。"

static func _tag_counts(state: Node) -> Dictionary:
	var counts: Dictionary = {}
	for item in state.action_history:
		var action_type := str(item.get("type", ""))
		if action_type == "":
			continue
		counts[action_type] = int(counts.get(action_type, 0)) + 1
	return counts

static func _action_count(state: Node, action_id: String) -> int:
	var count := 0
	for item in state.action_history:
		if str(item.get("action_id", "")) == action_id:
			count += 1
	return count

static func _completed_count(state: Node, event_ids: Array[String]) -> int:
	var count := 0
	for event_id in event_ids:
		if state.completed_events.has(event_id):
			count += 1
	return count

static func _action_name(action_id: String, actions: Array) -> String:
	for action in actions:
		if action.id == action_id:
			return action.name
	return action_id
