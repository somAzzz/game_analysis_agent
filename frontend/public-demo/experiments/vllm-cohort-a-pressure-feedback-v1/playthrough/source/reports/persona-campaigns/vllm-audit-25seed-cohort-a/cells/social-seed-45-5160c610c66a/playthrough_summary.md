# Interactive Player Summary

## Overview

- run id: **social-seed-45-5160c610c66a**
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
  "arrears_amount": 2270,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 3,
  "cash_shortfall_count": 10,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "rent_pressure",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "registration_window_missed",
    "parents_money_hint",
    "exam_registration",
    "midterm_pressure",
    "doctor_appointment",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "family_compare",
    "klausur_countdown",
    "office_hour_full",
    "exam_week",
    "after_exam_void"
  ],
  "content_version": "dev-hardcoded-0.1.0",
  "current_week_work_hours": 0,
  "difficulty": "normal",
  "energy": 80,
  "exam_readiness": 0,
  "failed_courses": 1,
  "flags": {
    "anna_group": true,
    "arrears": true,
    "arrived": true,
    "cash_shortfall": true,
    "cashflow_crisis": true,
    "cashflow_warning": true,
    "housing_contract_active": true,
    "needs_retake": true,
    "no_close_friends": true,
    "registration_delayed": true,
    "shallow_friendships": true,
    "visa_valid": true,
    "wg_cooking": true,
    "work_law_briefed": true
  },
  "gpa_score": 79,
  "hunger": 100,
  "language": 100,
  "last_ending_id": "cashflow_collapse",
  "last_exam_result": {
    "academic_progress": 0,
    "energy": 80,
    "exam_readiness": 7,
    "failed_courses": 1,
    "grade": 5.0,
    "passed": false,
    "score": 3,
    "stress": 90,
    "summary": "Nicht bestanden"
  },
  "loneliness": 1,
  "money": 0,
  "no_social_streak": 0,
  "parent_pressure": 32,
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
  "social": 100,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 2,
  "visa_progress": 100,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bank_account, language_tandem, student_club, cook_at_home | Prioritize unlocking financial stability via bank account activation while simul | arrival | True | 0 |
| 2 | insurance_paperwork, language_tandem, student_club, cook_at_home | Prioritize critical admin task for registration while maintaining social/languag | rent_pressure | True | 0 |
| 3 | insurance_paperwork, language_tandem, student_club, cook_at_home | Prioritize critical admin for registration while maintaining social/language pro | missing_school_registration | True | 0 |
| 4 | anmeldung, language_tandem, cook_at_home, go_running | Prioritize critical admin task (Anmeldung) to unlock registration, while maintai | wg_interview | True | 0 |
| 5 | insurance_paperwork, language_tandem, cook_at_home, go_running | Prioritize critical registration prerequisite (insurance) and social/language ma | legal_work_limit_notice | True | 0 |
| 6 | insurance_paperwork, language_tandem, cook_at_home, go_running | Prioritize critical admin for registration while maintaining social/language pro | anmeldung_deadline | True | 0 |
| 7 | bank_account, language_tandem, go_running | Unlock blocked funds to resolve cash crisis and enable registration; maintain so | registration_window_missed | True | 0 |
| 8 | bank_account, language_tandem, go_running, budget_call | Unlocking funds resolves the critical cash shortage, allowing for future registr | parents_money_hint | True | 1 |
| 9 | take_a_real_break, budget_call, cook_at_home, language_tandem | Prioritize mental health recovery and financial stability over academic progress | exam_registration | True | 1 |
| 10 | cook_at_home, language_tandem, go_running, take_a_real_break | Prioritizing mental health and basic survival (stress/hunger) over academic prog | midterm_pressure | True | 2 |
| 11 | cook_at_home, go_running, language_tandem, rent_talk_extension | Stabilize hunger and stress to prevent burnout; address cashflow root cause via  | doctor_appointment | True | 2 |
| 12 | take_a_real_break, language_tandem, go_running | Prioritize immediate survival (hunger) and mental health (stress) to prevent gam | group_invite | True | 2 |
| 13 | take_a_real_break, language_tandem, sell_unused_stuff | Prioritize survival (hunger/stress) and immediate cash injection to avoid game o | exercise_sheet_warning | True | 2 |
| 14 | cook_at_home, take_a_real_break, language_tandem, go_running | Prioritize immediate survival by reducing stress and hunger to prevent game over | visa_status_hidden_check | True | 2 |
| 15 | take_a_real_break, language_tandem, go_running | Survival first: reduce stress/hunger to prevent game over; sacrifice academic pr | family_compare | True | 3 |
| 16 | language_tandem, go_running, take_a_real_break | Survival priority: resolve hunger and stress to prevent game over, accepting aca | klausur_countdown | True | 3 |
| 17 | take_a_real_break, language_tandem, go_running | Prioritize mental health and basic needs over study to prevent collapse; accept  | office_hour_full | True | 3 |
| 18 | take_a_real_break, wg_dinner, language_tandem, go_running | Sacrifice academic progress and exam readiness to stabilize stress and hunger, e | exam_week | True | 3 |
| 19 | take_a_real_break, go_running, language_tandem | Stabilize stress and hunger to prevent game over; accept significant academic an | after_exam_void | True | 3 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 8 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=15). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 16 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=16). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=17). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 9 consecutive weeks (week=18). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 19 | `single_week_spike` | warning | `energy` jumped from 42.0 to 73 in a single week (Δ=+31.0). |
| 19 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 10 consecutive weeks (week=19). |

