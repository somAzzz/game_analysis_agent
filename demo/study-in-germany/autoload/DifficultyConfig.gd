extends Node

const DEFAULT_DIFFICULTY := "normal"

var modes := {
	"easy": {
		"name": "轻松",
		"description": "给第一次体验的玩家更多容错，生活压力和坏事件权重更低。",
		"success_rate_bonus": 0.08,
		"success_rate_min": 0.1,
		"success_rate_max": 0.95,
		"weekly_drift": {"energy": 38, "stress": 0, "loneliness": 0, "hunger": 8, "money": -220},
		"initial_profile": {"money": [5000, 9000], "gpa_score": [70, 88], "language": [35, 55], "aps_knowledge": [35, 55], "stress": [12, 26], "loneliness": [16, 30], "hunger": [10, 25], "social": [14, 28]},
		"negative_money_stress": 5,
		"high_stress_academic_penalty": -1,
		"high_loneliness_energy": 24,
		"event_type_weights": {"fixed": 1.0, "conditional": 0.75, "random": 1.0},
		"event_focus_weights": {"stress": 0.7, "admin": 0.8, "money": 0.8, "academic": 0.9, "positive": 1.25}
	},
	"normal": {
		"name": "标准",
		"description": "默认体验，维持当前第一学期 Demo 的压力节奏。",
		"success_rate_bonus": 0.0,
		"success_rate_min": 0.05,
		"success_rate_max": 0.9,
		"weekly_drift": {"energy": 32, "stress": 2, "loneliness": 1, "hunger": 12, "money": -255},
		"initial_profile": {"money": [2500, 7500], "gpa_score": [58, 82], "language": [20, 45], "aps_knowledge": [25, 45], "stress": [18, 35], "loneliness": [20, 38], "hunger": [15, 35], "social": [10, 25]},
		"negative_money_stress": 8,
		"high_stress_academic_penalty": -2,
		"high_loneliness_energy": 20,
		"event_type_weights": {"fixed": 1.0, "conditional": 1.0, "random": 1.0},
		"event_focus_weights": {"stress": 1.0, "admin": 1.0, "money": 1.0, "academic": 1.0, "positive": 1.0}
	},
	"hard": {
		"name": "困难",
		"description": "行政、金钱和压力事件更容易出现，事件选择成功率更低。",
		"success_rate_bonus": -0.06,
		"success_rate_min": 0.04,
		"success_rate_max": 0.85,
		"weekly_drift": {"energy": 26, "stress": 4, "loneliness": 2, "hunger": 15, "money": -285},
		"initial_profile": {"money": [1000, 5500], "gpa_score": [48, 75], "language": [10, 35], "aps_knowledge": [15, 35], "stress": [25, 48], "loneliness": [25, 45], "hunger": [20, 42], "social": [8, 22]},
		"negative_money_stress": 11,
		"high_stress_academic_penalty": -3,
		"high_loneliness_energy": 16,
		"event_type_weights": {"fixed": 1.0, "conditional": 1.35, "random": 1.0},
		"event_focus_weights": {"stress": 1.35, "admin": 1.25, "money": 1.25, "academic": 1.15, "positive": 0.85}
	},
	"realistic": {
		"name": "现实",
		"description": "更接近高压留学开局：生活成本更高，恢复更慢，风险事件更频繁。",
		"success_rate_bonus": -0.1,
		"success_rate_min": 0.03,
		"success_rate_max": 0.8,
		"weekly_drift": {"energy": 22, "stress": 5, "loneliness": 2, "hunger": 18, "money": -320},
		"initial_profile": {"money": [500, 4500], "gpa_score": [42, 72], "language": [5, 30], "aps_knowledge": [10, 30], "stress": [30, 55], "loneliness": [28, 50], "hunger": [25, 48], "social": [6, 18]},
		"negative_money_stress": 14,
		"high_stress_academic_penalty": -4,
		"high_loneliness_energy": 12,
		"event_type_weights": {"fixed": 1.0, "conditional": 1.6, "random": 0.95},
		"event_focus_weights": {"stress": 1.55, "admin": 1.45, "money": 1.4, "academic": 1.25, "positive": 0.75}
	}
}

func normalize(difficulty: String) -> String:
	if modes.has(difficulty):
		return difficulty
	return DEFAULT_DIFFICULTY

func get_mode(difficulty: String) -> Dictionary:
	return modes[normalize(difficulty)]

func get_success_rate_bonus(difficulty: String) -> float:
	return float(get_mode(difficulty).get("success_rate_bonus", 0.0))

func get_success_rate_min(difficulty: String) -> float:
	return float(get_mode(difficulty).get("success_rate_min", 0.05))

func get_success_rate_max(difficulty: String) -> float:
	return float(get_mode(difficulty).get("success_rate_max", 0.9))

func get_weekly_drift(difficulty: String) -> Dictionary:
	return get_mode(difficulty).get("weekly_drift", {}).duplicate(true)

func get_initial_profile(difficulty: String) -> Dictionary:
	return get_mode(difficulty).get("initial_profile", {}).duplicate(true)

func get_negative_money_stress(difficulty: String) -> int:
	return int(get_mode(difficulty).get("negative_money_stress", 8))

func get_high_stress_academic_penalty(difficulty: String) -> int:
	return int(get_mode(difficulty).get("high_stress_academic_penalty", -2))

func get_high_loneliness_energy(difficulty: String) -> int:
	return int(get_mode(difficulty).get("high_loneliness_energy", 20))

func get_event_type_weight(difficulty: String, event_type: String) -> float:
	var weights: Dictionary = get_mode(difficulty).get("event_type_weights", {})
	return float(weights.get(event_type, 1.0))

func get_event_focus_weight(difficulty: String, focus: String) -> float:
	var weights: Dictionary = get_mode(difficulty).get("event_focus_weights", {})
	return float(weights.get(focus, 1.0))

func list_modes() -> Array:
	return modes.keys()
