class_name EconomyRules
extends RefCounted

const LEGAL_WEEKLY_WORK_HOURS := 20
const LEGAL_ANNUAL_HALF_DAYS := 280
const LEGAL_WORK_HOURLY_WAGE_2026 := 13.90
const ILLEGAL_CASH_WORK_WAGE_RATIO := 0.80
const GERMANY_MINIMUM_WAGE_2026 := LEGAL_WORK_HOURLY_WAGE_2026
const ILLEGAL_CASH_WORK_WAGE := LEGAL_WORK_HOURLY_WAGE_2026 * ILLEGAL_CASH_WORK_WAGE_RATIO

static func legal_work_income_for_hours(hours: int) -> int:
	return roundi(float(maxi(hours, 0)) * LEGAL_WORK_HOURLY_WAGE_2026)

static func illegal_work_income_for_hours(hours: int) -> int:
	return roundi(float(maxi(hours, 0)) * ILLEGAL_CASH_WORK_WAGE)
