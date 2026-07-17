# Interactive Player Summary

## Overview

- run id: **slacker-seed-45-96d9256d2493**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 0,
  "aps_knowledge": 35,
  "aps_score": 0,
  "arrears_amount": 2968,
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
    "family_compare",
    "exam_registration",
    "midterm_pressure",
    "doctor_appointment",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "deposit_worry",
    "klausur_countdown",
    "office_hour_full",
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
  "gpa_score": 79,
  "hunger": 100,
  "language": 84,
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
  "no_social_streak": 4,
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
  "rng_state": 942656899613653825,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 45,
  "semester": 1,
  "social": 40,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 0,
  "visa_progress": 4,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bilibili_rest, go_running, cook_at_home, language_tandem | max stress reduction and comfort at cost of academic progress | arrival | True | 0 |
| 2 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize stress reduction and comfort; accept significant academic and visa prog | rent_pressure | True | 0 |
| 3 | bilibili_rest, go_running, cook_at_home, language_tandem | Maximize immediate comfort and stress relief; accept severe long-term penalties  | missing_school_registration | True | 0 |
| 4 | bilibili_rest, go_running, cook_at_home, language_tandem | maximize immediate stress relief and comfort at the cost of visa progress and ac | wg_interview | True | 0 |
| 5 | bilibili_rest, go_running, cook_at_home, language_tandem | Max stress relief and comfort; accept severe academic/visa lag and financial ris | legal_work_limit_notice | True | 0 |
| 6 | bilibili_rest, go_running, cook_at_home, language_tandem | maximize immediate stress relief and comfort at the cost of visa and academic pr | anmeldung_deadline | True | 0 |
| 7 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | Prioritize stress relief and immediate cash inflow; accept further academic and  | registration_window_missed | True | 2 |
| 8 | bilibili_rest, go_running, language_tandem, sell_unused_stuff | Maximize immediate stress relief and comfort; accept severe long-term penalties  | family_compare | True | 3 |
| 9 | bilibili_rest, go_running, language_tandem | Maximize stress relief and energy recovery; accept critical financial and academ | exam_registration | True | 3 |
| 10 | cook_at_home, go_running, bilibili_rest, language_tandem | Prioritize immediate survival (hunger/stress) and comfort; accept severe academi | midterm_pressure | True | 3 |
| 11 | bilibili_rest, go_running, language_tandem | Prioritize immediate survival (hunger) and mental health (stress/energy) via low | doctor_appointment | True | 3 |
| 12 | bilibili_rest, go_running, language_tandem | Immediate stress relief and hunger mitigation at the cost of further academic an | group_invite | True | 3 |
| 13 | take_a_real_break, go_running, language_tandem | Survive hunger and stress spike; accept academic failure and financial crisis. | exercise_sheet_warning | True | 3 |
| 14 | cook_at_home, take_a_real_break, go_running, bilibili_rest | Prioritize immediate survival of hunger and stress via low-effort actions; accep | visa_status_hidden_check | True | 4 |
| 15 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress reduction and energy recovery; accept severe academic  | deposit_worry | True | 4 |
| 16 | take_a_real_break, go_running, bilibili_rest, language_tandem | Maximize stress reduction and energy recovery at the cost of academic progress a | klausur_countdown | True | 4 |
| 17 | take_a_real_break, go_running, bilibili_rest, language_tandem | Maximize stress relief and energy recovery; accept critical academic and financi | office_hour_full | True | 4 |
| 18 | take_a_real_break, go_running, bilibili_rest, cook_at_home | Maximize immediate stress relief and energy recovery; accept severe academic reg | exam_week | True | 4 |
| 19 | take_a_real_break, go_running, bilibili_rest | Maximize immediate stress relief and survival; accept total academic and financi | after_exam_void | True | 4 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 7 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 7 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 8 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 8 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 14 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=14). |
| 15 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=15). |
| 16 | `single_week_spike` | warning | `stress` jumped from 0.0 to 31 in a single week (Δ=+31.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |

