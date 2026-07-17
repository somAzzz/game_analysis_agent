# Interactive Player Summary

## Overview

- run id: **social-seed-54-016c51939d4e**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 2,
  "annual_work_half_days": 0,
  "aps_knowledge": 38,
  "aps_score": 0,
  "arrears_amount": 1221,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 14,
  "cash_shortfall_count": 11,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "semester_ticket",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "academic_gap",
    "prof_email",
    "exam_registration",
    "midterm_pressure",
    "missed_exam_registration",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "office_hour_full",
    "klausur_countdown",
    "parents_money_hint",
    "exam_week",
    "after_exam_void"
  ],
  "content_version": "dev-hardcoded-0.1.0",
  "current_week_work_hours": 0,
  "difficulty": "normal",
  "energy": 16,
  "exam_readiness": 34,
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
    "visa_valid": true,
    "wg_cooking": true,
    "work_law_briefed": true
  },
  "gpa_score": 62,
  "hunger": 100,
  "language": 100,
  "last_ending_id": "cashflow_collapse",
  "last_exam_result": {
    "academic_progress": 2,
    "energy": 16,
    "exam_readiness": 44,
    "failed_courses": 1,
    "grade": 5.0,
    "passed": false,
    "score": 8,
    "stress": 98,
    "summary": "Nicht bestanden"
  },
  "loneliness": 17,
  "money": 0,
  "no_social_streak": 0,
  "parent_pressure": 16,
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
  "rng_state": -984951780194305456,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 54,
  "semester": 1,
  "social": 98,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 3,
  "testdaf_speaking": 3,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 30,
  "visa_progress": 68,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | language_tandem, student_club, cook_at_home, write_email_practice | 优先通过低成本社交和语言活动缓解孤独感并提升德语水平，同时通过做饭维持基本生存需求，暂不投入高成本语言班或高强度刷题，以符合社交路线策略并保留资金应对注册危机。 | arrival | True | 0 |
| 2 | insurance_paperwork, language_tandem, cook_at_home, go_running | Prioritize critical admin task (insurance) to unlock registration, while maintai | semester_ticket | True | 0 |
| 3 | bank_account, language_tandem, cook_at_home, go_running | Prioritize unlocking financial resources and registration prerequisites (bank_ac | missing_school_registration | True | 0 |
| 4 | language_tandem, student_club, cook_at_home, go_running | Gain social and language progress while managing stress and hunger with low cost | wg_interview | True | 0 |
| 5 | language_tandem, sell_unused_stuff, international_office | Prioritize immediate cash injection via selling items to mitigate arrears risk,  | legal_work_limit_notice | True | 0 |
| 6 | language_tandem, cook_at_home, rent_talk_extension, go_running | Resolve immediate arrears and hunger while maintaining social/language progress  | anmeldung_deadline | True | 0 |
| 7 | language_tandem, group_project, write_email_practice, go_running | Prioritize social/language growth and low-stress admin progress while deferring  | academic_gap | True | 1 |
| 8 | language_tandem, budget_call, go_running | Gain 260 EUR to clear arrears and reduce stress/hunger, while maintaining social | prof_email | True | 2 |
| 9 | language_tandem, go_running, write_email_practice | Prioritize immediate survival (hunger) and mental health (stress/loneliness) ove | exam_registration | True | 2 |
| 10 | cook_at_home, go_running, language_tandem, rent_talk_extension | Prioritize immediate survival by reducing hunger and stress via low-cost actions | midterm_pressure | True | 2 |
| 11 | take_a_real_break, language_tandem, go_running | Prioritize immediate survival (hunger/stress) and energy recovery over academic  | missed_exam_registration | True | 2 |
| 12 | take_a_real_break, go_running, language_tandem | Prioritize immediate survival by reducing hunger and stress to prevent game-over | group_invite | True | 2 |
| 13 | take_a_real_break, language_tandem, rent_talk_extension | Prioritize immediate survival by reducing hunger and stress to prevent game-over | exercise_sheet_warning | True | 3 |
| 14 | cook_at_home, take_a_real_break, language_tandem, rent_talk_extension | Sacrificing academic progress and exam readiness to stabilize critical survival  | visa_status_hidden_check | True | 3 |
| 15 | take_a_real_break, language_tandem, rent_talk_extension | Prioritize immediate survival by reducing critical stress and hunger, while addr | office_hour_full | True | 3 |
| 16 | take_a_real_break, language_tandem, office_hour | Prioritize immediate survival (stress/hunger reduction) and minimal social/langu | klausur_countdown | True | 3 |
| 17 | take_a_real_break, language_tandem, office_hour | Sacrifice academic progress and exam readiness this week to stabilize stress and | parents_money_hint | True | 3 |
| 18 | cook_at_home, take_a_real_break, language_tandem, office_hour | Prioritize survival (hunger/stress) and social/language maintenance over academi | exam_week | True | 3 |
| 19 | take_a_real_break, language_tandem, office_hour | Sacrifice academic progress and exam readiness this week to stabilize critical s | after_exam_void | True | 3 |

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
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 10 consecutive weeks (week=17). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 62.0 to 96 in a single week (Δ=+34.0). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 11 consecutive weeks (week=18). |
| 19 | `single_week_spike` | warning | `hunger` jumped from 28.0 to 62 in a single week (Δ=+34.0). |

