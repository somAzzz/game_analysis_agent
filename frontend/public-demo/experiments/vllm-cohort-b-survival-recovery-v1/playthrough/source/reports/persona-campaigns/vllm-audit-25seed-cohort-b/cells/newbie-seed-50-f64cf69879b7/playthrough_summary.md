# Interactive Player Summary

## Overview

- run id: **newbie-seed-50-f64cf69879b7**
- weeks played: **19**
- final ending: **burnout_pause**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 3,
  "aps_knowledge": 41,
  "aps_score": 0,
  "arrears_amount": 677,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 12,
  "cash_shortfall_count": 7,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "semester_ticket",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "testdaf_blocks_enrollment",
    "student_job_offer",
    "exam_registration",
    "midterm_pressure",
    "burnout_warning",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "moodle_quiz",
    "klausur_countdown",
    "language_wall",
    "exam_week",
    "after_exam_void"
  ],
  "content_version": "dev-hardcoded-0.1.0",
  "current_week_work_hours": 0,
  "difficulty": "normal",
  "energy": 83,
  "exam_readiness": 30,
  "failed_courses": 1,
  "flags": {
    "anna_group": true,
    "arrears": true,
    "arrived": true,
    "cash_shortfall": true,
    "cashflow_crisis": true,
    "cashflow_warning": true,
    "exam_registered": true,
    "housing_contract_active": true,
    "needs_retake": true,
    "school_registered": true,
    "shallow_friendships": true,
    "wg_cooking": true,
    "work_law_briefed": true
  },
  "gpa_score": 60,
  "hunger": 100,
  "language": 55,
  "last_ending_id": "burnout_pause",
  "last_exam_result": {
    "academic_progress": 0,
    "energy": 83,
    "exam_readiness": 40,
    "failed_courses": 1,
    "grade": 5.0,
    "passed": false,
    "score": 9,
    "stress": 90,
    "summary": "Nicht bestanden"
  },
  "loneliness": 74,
  "money": 0,
  "no_social_streak": 18,
  "parent_pressure": 80,
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
  "rng_state": 8000008820456466844,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 50,
  "semester": 1,
  "social": 11,
  "stress": 100,
  "testdaf_listening": 3,
  "testdaf_reading": 3,
  "testdaf_speaking": 3,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 0,
  "visa_progress": 97,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bank_account, insurance_paperwork, budget_call, cook_at_home | Prioritizing administrative setup and immediate financial stability over languag | arrival | True | 0 |
| 2 | insurance_paperwork, library_day, cook_at_home | Prioritizing the critical path to university registration (TestDaF + Insurance)  | semester_ticket | True | 0 |
| 3 | insurance_paperwork, library_day, cook_at_home | Prioritize critical registration prerequisites (insurance, TestDaF) while mainta | missing_school_registration | True | 0 |
| 4 | anmeldung, language_tandem, cook_at_home, go_running | Prioritize critical visa step (Anmeldung) and stress reduction while maintaining | wg_interview | True | 0 |
| 5 | cook_at_home, language_tandem, go_running, international_office | Prioritize survival and stress relief while advancing visa and language goals; m | legal_work_limit_notice | True | 0 |
| 6 | part_time_job, cook_at_home, go_running | Prioritize language school to fix the high-severity TestDaF risk, use part-time  | anmeldung_deadline | True | 0 |
| 7 | budget_call, go_running, cook_at_home | Prioritize visa-critical language school and cash injection; accept stress from  | testdaf_blocks_enrollment | True | 0 |
| 8 | bank_account, rent_talk_extension, take_a_real_break, go_running | Unlock blocked funds to solve cash crisis, reduce immediate stress to prevent bu | student_job_offer | True | 0 |
| 9 | budget_call, sell_unused_stuff, language_tandem, go_running | Gain ~400 EUR cash to clear arrears and stabilize hunger/rent, while maintaining | exam_registration | True | 1 |
| 10 | take_a_real_break, cook_at_home, language_tandem, write_email_practice | Sacrifice academic progress and exam readiness this week to drastically lower st | midterm_pressure | True | 1 |
| 11 | take_a_real_break, cook_at_home, go_running, budget_call | Prioritize immediate survival by reducing critical stress and securing funds; ac | burnout_warning | True | 2 |
| 12 | take_a_real_break, cook_at_home, problem_set, go_running | Prioritize stress reduction and hunger to prevent burnout/game over, then invest | group_invite | True | 2 |
| 13 | take_a_real_break, budget_call, rent_talk_extension | Prioritize survival by drastically reducing stress and hunger, and securing cash | exercise_sheet_warning | True | 2 |
| 14 | cook_at_home, take_a_real_break, rent_talk_extension, go_running | Prioritize survival (hunger/stress) and financial stability over academic progre | visa_status_hidden_check | True | 2 |
| 15 | take_a_real_break, cook_at_home, go_running, sell_unused_stuff | Reduce critical stress and hunger to prevent game over; sell items for immediate | moodle_quiz | True | 2 |
| 16 | take_a_real_break, go_running, office_hour | Prioritize immediate survival by reducing critical stress and hunger. Use remain | klausur_countdown | True | 2 |
| 17 | take_a_real_break, go_running, office_hour | Prioritize survival by eating and resting to lower stress/hunger, then use remai | language_wall | True | 3 |
| 18 | cook_at_home, take_a_real_break, go_running, office_hour | Prioritize immediate survival by reducing hunger and stress to safe levels, then | exam_week | True | 3 |
| 19 | take_a_real_break, go_running, office_hour | Prioritize survival by reducing hunger and stress to prevent game over, then use | after_exam_void | True | 3 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 9 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=17). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=18). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 24.0 to 58 in a single week (Δ=+34.0). |
| 19 | `single_week_spike` | warning | `energy` jumped from 67.0 to 97 in a single week (Δ=+30.0). |
| 19 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=19). |

