# Interactive Player Summary

## Overview

- run id: **slacker-seed-42-e2cfa2477f47**
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
  "arrears_amount": 2765,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 0,
  "cash_shortfall_count": 13,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "germany_language_track_start",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "registration_window_missed",
    "parents_money_hint",
    "exam_registration",
    "midterm_pressure",
    "family_compare",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "desperate_illegal_work_offer",
    "klausur_countdown",
    "room_contract_clause",
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
  "gpa_score": 61,
  "hunger": 100,
  "language": 75,
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
  "no_social_streak": 12,
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
  "rng_state": 6857406829159869010,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 42,
  "semester": 1,
  "social": 26,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 0,
  "visa_progress": 13,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bilibili_rest, go_running, cook_at_home, language_tandem | High stress reduction and energy gain at the cost of academic progress and visa  | arrival | True | 0 |
| 2 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize stress reduction and energy recovery while ignoring urgent registration | germany_language_track_start | True | 0 |
| 3 | bilibili_rest, go_running, cook_at_home, language_tandem | maximize immediate stress relief and energy recovery at the cost of academic and | missing_school_registration | True | 0 |
| 4 | bilibili_rest, go_running, cook_at_home, language_tandem | maximize immediate stress relief and energy recovery at the cost of academic and | wg_interview | True | 0 |
| 5 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | Prioritize immediate stress relief and minimal energy expenditure; sell items to | legal_work_limit_notice | True | 0 |
| 6 | bilibili_rest, go_running, cook_at_home, language_tandem | max stress relief and energy recovery at cost of visa progress and academic stan | anmeldung_deadline | True | 0 |
| 7 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | Max stress relief and minimal energy cost; sell items for cash while ignoring vi | registration_window_missed | True | 1 |
| 8 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | Maximize stress reduction and energy recovery; sell items for immediate cash to  | parents_money_hint | True | 2 |
| 9 | cook_at_home, bilibili_rest, go_running, language_tandem | Prioritize immediate survival and mental comfort; hunger reduced, stress lowered | exam_registration | True | 2 |
| 10 | cook_at_home, bilibili_rest, go_running, language_tandem | Immediate stress and hunger relief via low-effort actions; ignores critical visa | midterm_pressure | True | 2 |
| 11 | bilibili_rest, go_running, language_tandem | Prioritize immediate survival (hunger/stress) and comfort; accept academic/visa  | family_compare | True | 2 |
| 12 | take_a_real_break, go_running, language_tandem | Prioritize immediate survival (hunger/stress) via low-effort actions; accept aca | group_invite | True | 2 |
| 13 | bilibili_rest, go_running, language_tandem | Immediate hunger and stress relief via low-effort actions; accepts severe academ | exercise_sheet_warning | True | 3 |
| 14 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Prioritize immediate survival (hunger/stress) via low-effort actions; accept sev | visa_status_hidden_check | True | 3 |
| 15 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress/hunger relief and energy recovery; accept severe acade | desperate_illegal_work_offer | True | 4 |
| 16 | take_a_real_break, go_running, bilibili_rest, cook_at_home | Maximize immediate stress relief and energy recovery at the cost of critical aca | klausur_countdown | True | 4 |
| 17 | take_a_real_break, go_running, bilibili_rest, rent_talk_extension | Max stress relief and energy recovery; accepts critical academic/visa regression | room_contract_clause | True | 4 |
| 18 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Immediate survival and stress relief at the cost of total academic and visa fail | exam_week | True | 4 |
| 19 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept total academic and  | after_exam_void | True | 4 |

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
| 15 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 0 consecutive weeks (week=14). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 16 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 0 consecutive weeks (week=14). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 1 consecutive weeks (week=14). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |

