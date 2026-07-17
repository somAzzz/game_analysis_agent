# Interactive Player Summary

## Overview

- run id: **social-seed-52-385d4e15861f**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 0,
  "aps_knowledge": 30,
  "aps_score": 0,
  "arrears_amount": 1122,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 13,
  "cash_shortfall_count": 9,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "rent_pressure",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "moodle_quiz",
    "prof_email",
    "exam_registration",
    "midterm_pressure",
    "burnout_warning",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "career_doubt",
    "klausur_countdown",
    "parents_money_hint",
    "exam_week",
    "after_exam_void"
  ],
  "content_version": "dev-hardcoded-0.1.0",
  "current_week_work_hours": 0,
  "difficulty": "normal",
  "energy": 50,
  "exam_readiness": 21,
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
    "no_close_friends": true,
    "school_registered": true,
    "shallow_friendships": true,
    "wg_cooking": true,
    "work_law_briefed": true
  },
  "gpa_score": 59,
  "hunger": 100,
  "language": 100,
  "last_ending_id": "cashflow_collapse",
  "last_exam_result": {
    "academic_progress": 0,
    "energy": 50,
    "exam_readiness": 31,
    "failed_courses": 1,
    "grade": 5.0,
    "passed": false,
    "score": 17,
    "stress": 90,
    "summary": "Nicht bestanden"
  },
  "loneliness": 6,
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
  "rng_state": -5715843516723695114,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 52,
  "semester": 1,
  "social": 96,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 3,
  "university_tier": "未定位",
  "unpaid_social_streak": 16,
  "visa_progress": 70,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | insurance_paperwork, language_tandem, student_club, cook_at_home | Prioritize essential admin (insurance) and social/language goals to align with p | arrival | True | 0 |
| 2 | bank_account, language_tandem, student_club, cook_at_home | Prioritize unlocking financial stability via bank activation while maintaining s | rent_pressure | True | 0 |
| 3 | language_tandem, student_club, cook_at_home, insurance_paperwork | Prioritizing social integration and language practice aligns with persona but de | missing_school_registration | True | 0 |
| 4 | anmeldung, language_tandem, student_club, cook_at_home | Prioritizing the high-impact admin task (Anmeldung) to secure legal status, whil | wg_interview | True | 0 |
| 5 | language_tandem, student_club, cook_at_home, write_email_practice | Prioritize social integration and language skills over intense academic study or | legal_work_limit_notice | True | 0 |
| 6 | language_tandem, student_club, cook_at_home, go_running | Prioritize mental health and social integration to maintain persona alignment an | anmeldung_deadline | True | 0 |
| 7 | language_tandem, write_email_practice, go_running, sell_unused_stuff | Prioritize social/language persona and immediate cash injection to mitigate arre | moodle_quiz | True | 0 |
| 8 | language_tandem, group_project, office_hour, go_running | Balance social persona with critical academic progress and stress reduction; def | prof_email | True | 1 |
| 9 | budget_call, language_tandem, go_running, rent_talk_extension | Inject immediate cash and reduce arrears to stabilize survival, while maintainin | exam_registration | True | 2 |
| 10 | cook_at_home, go_running, language_tandem, take_a_real_break | Prioritize immediate survival (hunger/stress) and persona alignment (social/lang | midterm_pressure | True | 3 |
| 11 | cook_at_home, go_running, language_tandem, student_club | Prioritize immediate survival (hunger) and mental health (stress) to prevent gam | burnout_warning | True | 3 |
| 12 | language_tandem, go_running, sell_unused_stuff | Prioritizes immediate survival (hunger/cash) and mental health (stress) over aca | group_invite | True | 3 |
| 13 | take_a_real_break, language_tandem, budget_call | Prioritizes immediate survival (hunger/stress) and financial stabilization over  | exercise_sheet_warning | True | 3 |
| 14 | cook_at_home, take_a_real_break, language_tandem, go_running | Survival first: reduce hunger/stress to prevent game over; accept academic drop  | visa_status_hidden_check | True | 4 |
| 15 | cook_at_home, take_a_real_break, language_tandem, rent_talk_extension | Prioritizes survival (stress/hunger) and financial stability over academic progr | career_doubt | True | 4 |
| 16 | take_a_real_break, language_tandem, go_running | Survival and mental stability prioritized over academic progress to prevent imme | klausur_countdown | True | 4 |
| 17 | take_a_real_break, language_tandem, go_running | Survival and mental stability prioritized over academic progress to prevent imme | parents_money_hint | True | 4 |
| 18 | cook_at_home, take_a_real_break, language_tandem, office_hour | Prioritize immediate survival (hunger/stress) over academic gains. Hunger will d | exam_week | True | 4 |
| 19 | take_a_real_break, language_tandem, go_running | Prioritize immediate survival (stress/hunger) to prevent game over; accept acade | after_exam_void | True | 4 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 8 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 10 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 11 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 12 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 13 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 14 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |
| 14 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=14). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 15 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |
| 15 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=15). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 16 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |
| 16 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 8 consecutive weeks (week=16). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 70.0 to 100 in a single week (Δ=+30.0). |
| 17 | `single_week_spike` | warning | `energy` jumped from 24.0 to 55 in a single week (Δ=+31.0). |

