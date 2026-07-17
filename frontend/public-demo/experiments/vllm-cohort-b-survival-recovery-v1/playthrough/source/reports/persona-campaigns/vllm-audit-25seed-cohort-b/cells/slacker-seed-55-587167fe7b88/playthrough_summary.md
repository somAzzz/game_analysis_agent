# Interactive Player Summary

## Overview

- run id: **slacker-seed-55-587167fe7b88**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 0,
  "aps_knowledge": 31,
  "aps_score": 0,
  "arrears_amount": 3083,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 0,
  "cash_shortfall_count": 13,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "rent_pressure",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "registration_window_missed",
    "termin_missing",
    "exam_registration",
    "midterm_pressure",
    "mental_health_webinar",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "lonely_christmas",
    "klausur_countdown",
    "missed_exam_registration",
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
  "gpa_score": 76,
  "hunger": 100,
  "language": 64,
  "last_ending_id": "cashflow_collapse",
  "last_exam_result": {
    "academic_progress": 0,
    "energy": 100,
    "exam_readiness": 0,
    "failed_courses": 1,
    "grade": 5.0,
    "passed": false,
    "score": 1,
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
  "rng_state": -326432125164178509,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 55,
  "semester": 1,
  "social": 22,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 3,
  "testdaf_speaking": 2,
  "testdaf_writing": 3,
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
| 1 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize immediate stress relief and energy recovery at the cost of academic pro | arrival | True | 0 |
| 2 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize comfort and stress relief; ignore critical registration and exam deadli | rent_pressure | True | 0 |
| 3 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize stress reduction and energy recovery; accept severe academic and visa d | missing_school_registration | True | 0 |
| 4 | bilibili_rest, go_running, cook_at_home, language_tandem | maximize stress relief and energy recovery at the cost of academic progress and  | wg_interview | True | 0 |
| 5 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize stress relief and energy; accept critical delays in registration and ex | legal_work_limit_notice | True | 0 |
| 6 | bilibili_rest, cook_at_home, go_running, language_tandem | max stress relief and energy recovery at cost of visa/academic progress | anmeldung_deadline | True | 0 |
| 7 | bilibili_rest, go_running, language_tandem | Maximize stress reduction and energy recovery; accept severe academic and visa d | registration_window_missed | True | 1 |
| 8 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | Prioritize immediate stress relief and energy recovery via slacker actions; sell | termin_missing | True | 2 |
| 9 | bilibili_rest, go_running, language_tandem | Maximize stress relief and energy recovery; accept critical delays in registrati | exam_registration | True | 2 |
| 10 | cook_at_home, bilibili_rest, go_running, language_tandem | Prioritize immediate survival (hunger) and mental comfort (stress/energy) while  | midterm_pressure | True | 2 |
| 11 | bilibili_rest, go_running, language_tandem | Survive hunger and lower stress via slacker routine; accept academic/visa collap | mental_health_webinar | True | 2 |
| 12 | bilibili_rest, go_running, language_tandem | Survive hunger and lower stress at the cost of further academic and visa delays. | group_invite | True | 2 |
| 13 | take_a_real_break, go_running, bilibili_rest | Immediate survival and stress relief via food and rest; accept severe academic a | exercise_sheet_warning | True | 2 |
| 14 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Resolve critical hunger and stress immediately; accept significant loss in acade | visa_status_hidden_check | True | 3 |
| 15 | take_a_real_break, go_running, bilibili_rest | Immediate survival and stress relief via food and rest; accept significant loss  | lonely_christmas | True | 3 |
| 16 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept total failure in ex | klausur_countdown | True | 3 |
| 17 | take_a_real_break, go_running, bilibili_rest | stress drops significantly while energy recovers, but hunger remains 100 and aca | missed_exam_registration | True | 3 |
| 18 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Relieve hunger and stress to survive; accept total academic collapse and visa ri | exam_week | True | 3 |
| 19 | take_a_real_break, go_running, bilibili_rest | Maximize stress reduction and energy recovery; accept total academic collapse an | after_exam_void | True | 3 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 7 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 14 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=14). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=15). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 16 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=16). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 9 consecutive weeks (week=17). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 10 consecutive weeks (week=18). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |

