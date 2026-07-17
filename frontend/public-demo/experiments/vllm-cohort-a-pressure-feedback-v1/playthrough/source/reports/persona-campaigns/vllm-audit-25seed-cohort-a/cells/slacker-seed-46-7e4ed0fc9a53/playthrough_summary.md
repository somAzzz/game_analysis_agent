# Interactive Player Summary

## Overview

- run id: **slacker-seed-46-7e4ed0fc9a53**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 0,
  "aps_knowledge": 25,
  "aps_score": 0,
  "arrears_amount": 3323,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 0,
  "cash_shortfall_count": 14,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "germany_language_track_start",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "registration_window_missed",
    "blocked_account_notice",
    "exam_registration",
    "midterm_pressure",
    "wechat_silence",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "project_presentation",
    "klausur_countdown",
    "classmate_home_dinner",
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
    "exam_registered": true,
    "housing_contract_active": true,
    "needs_retake": true,
    "no_close_friends": true,
    "registration_delayed": true,
    "shallow_friendships": true,
    "wg_cooking": true,
    "work_law_briefed": true
  },
  "gpa_score": 72,
  "hunger": 100,
  "language": 66,
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
  "no_social_streak": 18,
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
  "rng_state": -1028926410235084570,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 46,
  "semester": 1,
  "social": 16,
  "stress": 100,
  "testdaf_listening": 3,
  "testdaf_reading": 3,
  "testdaf_speaking": 3,
  "testdaf_writing": 3,
  "university_tier": "未定位",
  "unpaid_social_streak": 0,
  "visa_progress": 12,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bilibili_rest, go_running, cook_at_home, write_email_practice | max stress reduction and energy recovery at cost of academic progress and regist | arrival | True | 0 |
| 2 | bilibili_rest, go_running, cook_at_home, language_tandem | maximize stress reduction and comfort while neglecting academic and administrati | germany_language_track_start | True | 0 |
| 3 | bilibili_rest, go_running, cook_at_home, language_tandem | max stress reduction and comfort at cost of academic progress and registration r | missing_school_registration | True | 0 |
| 4 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize short-term comfort and mental health at the expense of academic progres | wg_interview | True | 0 |
| 5 | bilibili_rest, go_running, language_tandem, write_email_practice | Maximize stress reduction and energy recovery; accept academic delay and registr | legal_work_limit_notice | True | 0 |
| 6 | bilibili_rest, go_running, cook_at_home, sell_unused_stuff | Prioritize immediate stress relief and cash injection via selling items; accept  | anmeldung_deadline | True | 0 |
| 7 | bilibili_rest, go_running, language_tandem, write_email_practice | Maximize stress reduction and energy recovery; accept academic and visa delays t | registration_window_missed | True | 1 |
| 8 | bilibili_rest, go_running, language_tandem, write_email_practice | Max stress reduction and energy recovery; accept critical financial and academic | blocked_account_notice | True | 2 |
| 9 | bilibili_rest, go_running, language_tandem | Maximize immediate stress relief and energy recovery; accept severe academic and | exam_registration | True | 2 |
| 10 | cook_at_home, bilibili_rest, go_running, language_tandem | Prioritize immediate survival (hunger) and stress relief (rest) over academic pr | midterm_pressure | True | 2 |
| 11 | bilibili_rest, go_running, write_email_practice | Satisfy hunger and reduce stress via low-effort actions; accept academic and vis | wechat_silence | True | 2 |
| 12 | take_a_real_break, go_running, bilibili_rest | Survive hunger and reduce stress significantly at the cost of academic progress  | group_invite | True | 2 |
| 13 | take_a_real_break, go_running, bilibili_rest | Prioritize immediate survival (hunger) and stress relief via low-effort actions; | exercise_sheet_warning | True | 3 |
| 14 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Prioritize immediate survival and stress relief; accept severe academic and fina | visa_status_hidden_check | True | 3 |
| 15 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress and hunger relief via rest and food; accept severe aca | project_presentation | True | 3 |
| 16 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress/hunger relief and energy recovery; accept critical fai | klausur_countdown | True | 3 |
| 17 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept critical academic a | classmate_home_dinner | True | 3 |
| 18 | take_a_real_break, go_running, bilibili_rest, cook_at_home | Maximize immediate stress relief and energy recovery; accept critical academic a | exam_week | True | 3 |
| 19 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept critical academic a | after_exam_void | True | 3 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 7 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 13 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=13). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 14 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=14). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=15). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 16 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 9 consecutive weeks (week=16). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 0 consecutive weeks (week=16). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 1 consecutive weeks (week=16). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |

