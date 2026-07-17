# Interactive Player Summary

## Overview

- run id: **money-seed-43-19fc7eb327d9**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 96,
  "annual_work_half_days": 0,
  "aps_knowledge": 30,
  "aps_score": 0,
  "arrears_amount": 2824,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 11,
  "cash_shortfall_count": 15,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "rent_pressure",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "health_insurance_letter",
    "desperate_illegal_work_offer",
    "exam_registration",
    "midterm_pressure",
    "classmate_home_dinner",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "hiwi_hint",
    "klausur_countdown",
    "termin_missing",
    "exam_week",
    "after_exam_void"
  ],
  "content_version": "dev-hardcoded-0.1.0",
  "current_week_work_hours": 0,
  "difficulty": "normal",
  "energy": 12,
  "exam_readiness": 100,
  "failed_courses": 0,
  "flags": {
    "anna_group": true,
    "arrears": true,
    "cash_shortfall": true,
    "cashflow_crisis": true,
    "cashflow_warning": true,
    "deportation_warning": true,
    "exam_registered": true,
    "housing_contract_active": true,
    "no_close_friends": true,
    "rent_arrears": true,
    "school_registered": true,
    "shallow_friendships": true,
    "work_law_briefed": true
  },
  "gpa_score": 65,
  "hunger": 100,
  "language": 71,
  "last_ending_id": "cashflow_collapse",
  "last_exam_result": {
    "academic_progress": 96,
    "energy": 12,
    "exam_readiness": 100,
    "failed_courses": 0,
    "grade": 3.0,
    "passed": true,
    "score": 57,
    "stress": 100,
    "stress_after": 96,
    "summary": "Befriedigend"
  },
  "loneliness": 100,
  "money": 0,
  "no_social_streak": 0,
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
  "rng_state": 665259779458378849,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 43,
  "semester": 1,
  "social": 34,
  "stress": 96,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 26,
  "visa_progress": 21,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | problem_set, library_day, language_school_germany, language_tandem | exercise money priorities | arrival | True | 0 |
| 2 | problem_set, library_day, language_tandem, write_email_practice | exercise money priorities | rent_pressure | True | 0 |
| 3 | problem_set, library_day, language_tandem, write_email_practice | exercise money priorities | missing_school_registration | True | 0 |
| 4 | attend_lecture, problem_set, library_day, language_tandem | exercise money priorities | wg_interview | True | 0 |
| 5 | attend_lecture, problem_set, library_day, language_tandem | exercise money priorities | legal_work_limit_notice | True | 0 |
| 6 | attend_lecture, problem_set, library_day, office_hour | exercise money priorities | anmeldung_deadline | True | 0 |
| 7 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | health_insurance_letter | True | 0 |
| 8 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | desperate_illegal_work_offer | True | 0 |
| 9 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | exam_registration | True | 0 |
| 10 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | midterm_pressure | True | 0 |
| 11 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | classmate_home_dinner | True | 0 |
| 12 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | group_invite | True | 0 |
| 13 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | exercise_sheet_warning | True | 0 |
| 14 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | visa_status_hidden_check | True | 1 |
| 15 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | hiwi_hint | True | 1 |
| 16 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | klausur_countdown | True | 1 |
| 17 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | termin_missing | True | 1 |
| 18 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | exam_week | True | 1 |
| 19 | attend_lecture, problem_set, group_project, library_day | exercise money priorities | after_exam_void | True | 1 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 14 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=14). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=15). |
| 16 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=16). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 9 consecutive weeks (week=17). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 10 consecutive weeks (week=18). |
| 19 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 11 consecutive weeks (week=19). |

