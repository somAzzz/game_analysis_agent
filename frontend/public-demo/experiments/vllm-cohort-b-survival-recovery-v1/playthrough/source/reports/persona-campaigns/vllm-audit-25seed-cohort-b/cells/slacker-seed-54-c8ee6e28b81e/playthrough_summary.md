# Interactive Player Summary

## Overview

- run id: **slacker-seed-54-c8ee6e28b81e**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 0,
  "aps_knowledge": 38,
  "aps_score": 0,
  "arrears_amount": 3408,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 0,
  "cash_shortfall_count": 15,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "semester_ticket",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "registration_window_missed",
    "classmate_home_dinner",
    "exam_registration",
    "midterm_pressure",
    "doctor_appointment",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "room_contract_clause",
    "klausur_countdown",
    "deportation_risk_notice",
    "exam_week",
    "after_exam_void"
  ],
  "content_version": "dev-hardcoded-0.1.0",
  "current_week_work_hours": 0,
  "difficulty": "normal",
  "energy": 100,
  "exam_readiness": 0,
  "failed_courses": 1,
  "flags": {
    "admin_avoidance": true,
    "arrears": true,
    "arrived": true,
    "cash_shortfall": true,
    "cashflow_crisis": true,
    "cashflow_warning": true,
    "deportation_warning": true,
    "exam_registered": true,
    "housing_contract_active": true,
    "needs_retake": true,
    "no_close_friends": true,
    "registration_delayed": true,
    "shallow_friendships": true,
    "wg_cooking": true,
    "work_law_briefed": true
  },
  "gpa_score": 62,
  "hunger": 100,
  "language": 62,
  "last_ending_id": "cashflow_collapse",
  "last_exam_result": {
    "academic_progress": 0,
    "energy": 100,
    "exam_readiness": 0,
    "failed_courses": 1,
    "grade": 5.0,
    "passed": false,
    "score": 0,
    "stress": 90,
    "summary": "Nicht bestanden"
  },
  "loneliness": 100,
  "money": 0,
  "no_social_streak": 14,
  "parent_pressure": 0,
  "policy": "interactive_player",
  "reciprocity_debt": 0,
  "relationships": {
    "anna": {
      "conflict": 0.0,
      "favorability": 15.0,
      "story_stage": 0.0,
      "trust": 10.0
    },
    "cem": {
      "conflict": 0.0,
      "favorability": 20.0,
      "story_stage": 0.0,
      "trust": 15.0
    },
    "li": {
      "conflict": 0.0,
      "favorability": 25.0,
      "story_stage": 0.0,
      "trust": 20.0
    },
    "mueller": {
      "conflict": 0.0,
      "favorability": 10.0,
      "story_stage": 0.0,
      "trust": 5.0
    },
    "parents": {
      "conflict": 10.0,
      "favorability": 40.0,
      "story_stage": 0.0,
      "trust": 35.0
    }
  },
  "rng_state": 1645151184684559886,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 54,
  "semester": 1,
  "social": 33,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 3,
  "testdaf_speaking": 3,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 0,
  "visa_progress": 3,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bilibili_rest, cook_at_home, go_running, language_tandem | maximize immediate stress reduction and energy recovery at the cost of academic  | arrival | True | 0 |
| 2 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize immediate comfort and stress relief while ignoring critical registratio | semester_ticket | True | 0 |
| 3 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize immediate comfort and stress reduction at the cost of academic progress | missing_school_registration | True | 0 |
| 4 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize stress relief and energy recovery while ignoring critical registration  | wg_interview | True | 0 |
| 5 | bilibili_rest, go_running, language_tandem | maximize stress relief and comfort while delaying critical admin tasks | legal_work_limit_notice | True | 0 |
| 6 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize immediate stress relief and comfort; accept severe academic and adminis | anmeldung_deadline | True | 0 |
| 7 | bilibili_rest, go_running, language_tandem | Prioritize immediate stress relief and energy recovery; accept worsening financi | registration_window_missed | True | 1 |
| 8 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | Immediate stress relief and cash injection via selling items, ignoring critical  | classmate_home_dinner | True | 1 |
| 9 | bilibili_rest, go_running, language_tandem | Maximize stress relief and energy recovery; accept worsening financial and acade | exam_registration | True | 2 |
| 10 | cook_at_home, bilibili_rest, go_running, language_tandem | Prioritize immediate stress relief and hunger management; accept worsening acade | midterm_pressure | True | 2 |
| 11 | bilibili_rest, go_running, language_tandem | Immediate stress relief and hunger management at the cost of further academic an | doctor_appointment | True | 2 |
| 12 | bilibili_rest, go_running, language_tandem | Prioritize survival (hunger) and mental stability (stress) over academic progres | group_invite | True | 2 |
| 13 | take_a_real_break, go_running, bilibili_rest | Prioritize immediate survival (hunger/stress) via low-effort actions; accept sev | exercise_sheet_warning | True | 2 |
| 14 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and hunger reduction; accept severe academic an | visa_status_hidden_check | True | 3 |
| 15 | take_a_real_break, go_running, bilibili_rest | Maximize immediate survival (food/stress) via zero-cost/low-effort actions; acce | room_contract_clause | True | 3 |
| 16 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept severe academic and | klausur_countdown | True | 3 |
| 17 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept severe academic and | deportation_risk_notice | True | 3 |
| 18 | take_a_real_break, go_running, bilibili_rest, cook_at_home | Maximize immediate stress relief and hunger reduction; accept severe academic an | exam_week | True | 3 |
| 19 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress/energy recovery and hunger relief; accept total academ | after_exam_void | True | 3 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 7 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 14 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=14). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=15). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 16 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=16). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 9 consecutive weeks (week=17). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 10 consecutive weeks (week=18). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 58.0 to 92 in a single week (Δ=+34.0). |
| 19 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 11 consecutive weeks (week=19). |

