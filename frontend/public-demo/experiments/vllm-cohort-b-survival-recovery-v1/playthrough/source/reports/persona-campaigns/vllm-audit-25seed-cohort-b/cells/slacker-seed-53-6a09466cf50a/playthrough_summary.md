# Interactive Player Summary

## Overview

- run id: **slacker-seed-53-6a09466cf50a**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 0,
  "aps_knowledge": 37,
  "aps_score": 0,
  "arrears_amount": 2851,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 2,
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
    "moodle_quiz",
    "exam_registration",
    "midterm_pressure",
    "illegal_cash_job_offer",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "career_doubt",
    "klausur_countdown",
    "student_job_offer",
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
  "language": 54,
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
  "rng_state": 3616734494533298281,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 53,
  "semester": 1,
  "social": 25,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 0,
  "visa_progress": 1,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize immediate stress relief and energy recovery at the cost of academic pro | arrival | True | 0 |
| 2 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize stress reduction and energy recovery; ignore high-severity registration | germany_language_track_start | True | 0 |
| 3 | bilibili_rest, cook_at_home, go_running, language_tandem | Max stress relief and energy recovery; ignore critical registration and financia | missing_school_registration | True | 0 |
| 4 | bilibili_rest, cook_at_home, go_running, language_tandem | maximize stress relief and energy recovery at the cost of academic progress and  | wg_interview | True | 0 |
| 5 | bilibili_rest, go_running, language_tandem | Maximize stress relief and energy; ignore critical registration and financial ri | legal_work_limit_notice | True | 0 |
| 6 | bilibili_rest, go_running, language_tandem, cook_at_home | max stress relief and energy recovery at cost of academic and visa progress | anmeldung_deadline | True | 0 |
| 7 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | maximize short-term comfort and energy recovery while accepting severe financial | registration_window_missed | True | 2 |
| 8 | bilibili_rest, go_running, language_tandem | Short-term comfort and stress reduction at the cost of worsening financial and a | moodle_quiz | True | 3 |
| 9 | bilibili_rest, go_running, language_tandem | Prioritize immediate survival and stress relief; accept worsening academic and f | exam_registration | True | 3 |
| 10 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Prioritize immediate survival (hunger/stress) via low-effort actions; accept sev | midterm_pressure | True | 3 |
| 11 | bilibili_rest, go_running, language_tandem | Prioritize immediate survival (hunger/stress) via low-effort actions; accept sev | illegal_cash_job_offer | True | 3 |
| 12 | bilibili_rest, go_running, language_tandem | Immediate stress relief and hunger management via low-effort actions; accept wor | group_invite | True | 3 |
| 13 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept severe academic and | exercise_sheet_warning | True | 4 |
| 14 | take_a_real_break, go_running, cook_at_home, bilibili_rest | Maximize immediate stress relief and hunger reduction; accept severe academic an | visa_status_hidden_check | True | 4 |
| 15 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress/hunger relief and energy recovery at the cost of furth | career_doubt | True | 4 |
| 16 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery via rest and low-effort act | klausur_countdown | True | 4 |
| 17 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept severe academic and | student_job_offer | True | 4 |
| 18 | take_a_real_break, go_running, bilibili_rest, cook_at_home | Maximize immediate stress relief and hunger reduction; accept total academic and | exam_week | True | 4 |
| 19 | take_a_real_break, go_running, bilibili_rest | Maximize stress reduction and energy recovery; accept total academic and financi | after_exam_void | True | 4 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 7 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 7 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 8 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 9 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 10 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 11 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 12 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 13 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 13 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=13). |
| 14 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 14 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=14). |
| 15 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 70 in a single week (Δ=+42.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=15). |
| 16 | `single_week_spike` | warning | `stress` jumped from 8.0 to 46 in a single week (Δ=+38.0). |

