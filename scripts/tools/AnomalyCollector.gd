class_name AnomalyCollector

# Minimal invariant checks mirrored from the Python anomaly detector.
# The Python side is the source of truth; this helper just emits a few
# machine-readable flags inside each boundary run so the prober agent can
# consume one JSONL without extra round trips.

const UPPER_BOUNDED := ["energy", "stress", "loneliness", "hunger", "academic_progress", "exam_readiness", "language", "social", "visa_progress", "career_progress", "gpa_score", "aps_knowledge", "aps_score"]
const NON_NEGATIVE := ["money", "blocked_account_balance", "current_week_work_hours", "annual_work_half_days"]

static func collect(weekly_log: Array, final_state: Dictionary) -> Array:
	var anomalies: Array = []
	var prev: Dictionary = {}
	for week_record in weekly_log:
		var week_no: int = int(week_record.get("week", 0))
		var state: Dictionary = week_record.get("after_state", {})
		for metric in UPPER_BOUNDED:
			var value = state.get(metric)
			if typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT:
				continue
			var fv: float = float(value)
			if fv < 0.0:
				anomalies.append({"kind": "stat_underflow", "metric": metric, "value": fv, "week": week_no})
			elif fv > 100.0:
				anomalies.append({"kind": "stat_overflow", "metric": metric, "value": fv, "week": week_no})
		for metric in NON_NEGATIVE:
			var value = state.get(metric)
			if typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT:
				continue
			var fv: float = float(value)
			if fv < 0.0:
				anomalies.append({
					"kind": "negative_money" if metric in ["money", "blocked_account_balance"] else "stat_underflow",
					"metric": metric,
					"value": fv,
					"week": week_no,
				})
		if prev.has("state"):
			for metric in UPPER_BOUNDED:
				var cur = state.get(metric)
				var prv = prev["state"].get(metric)
				if (typeof(cur) == TYPE_INT or typeof(cur) == TYPE_FLOAT) and (typeof(prv) == TYPE_INT or typeof(prv) == TYPE_FLOAT):
					var delta: float = float(cur) - float(prv)
					if absf(delta) >= 30.0:
						anomalies.append({
							"kind": "single_week_spike",
							"metric": metric,
							"from": float(prv),
							"to": float(cur),
							"week": week_no,
						})
		prev = {"state": state.duplicate(true), "week": week_no}

	if final_state.get("flags", {}).has("pipeline_stalled"):
		anomalies.append({"kind": "pipeline_stalled", "week": -1})
	return anomalies