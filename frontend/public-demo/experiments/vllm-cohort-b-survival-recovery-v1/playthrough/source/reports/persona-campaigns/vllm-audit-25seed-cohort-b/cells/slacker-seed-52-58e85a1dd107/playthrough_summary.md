# Interactive Player Summary

## Overview

- run id: **slacker-seed-52-58e85a1dd107**
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
  "arrears_amount": 3240,
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
    "prof_email",
    "exam_registration",
    "midterm_pressure",
    "desperate_illegal_work_offer",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "student_job_offer",
    "klausur_countdown",
    "project_presentation",
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
    "housing_contract_active": true,
    "needs_retake": true,
    "no_close_friends": true,
    "registration_delayed": true,
    "shallow_friendships": true,
    "wg_cooking": true,
    "work_law_briefed": true
  },
  "gpa_score": 59,
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
  "rng_state": 5588317804382036676,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 52,
  "semester": 1,
  "social": 28,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 3,
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
| 1 | bilibili_rest, cook_at_home, go_running, language_tandem | Significant reduction in stress and hunger at the cost of academic progress and  | arrival | True | 0 |
| 2 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize stress reduction and energy recovery while ignoring high-severity regis | rent_pressure | True | 0 |
| 3 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize stress reduction and energy recovery at the cost of academic progress a | missing_school_registration | True | 0 |
| 4 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize stress reduction and energy recovery while deliberately ignoring critic | wg_interview | True | 0 |
| 5 | bilibili_rest, cook_at_home, go_running, language_tandem | Max stress relief and energy recovery; ignore critical registration deadline and | legal_work_limit_notice | True | 0 |
| 6 | bilibili_rest, cook_at_home, go_running, language_tandem | Maximize immediate stress relief and energy recovery; accept severe academic and | anmeldung_deadline | True | 0 |
| 7 | bilibili_rest, language_tandem, go_running | Maximize immediate stress relief and energy recovery; accept severe academic and | registration_window_missed | True | 1 |
| 8 | bilibili_rest, go_running, language_tandem | Max stress relief and energy recovery; accept severe academic and visa progress  | prof_email | True | 2 |
| 9 | bilibili_rest, go_running, language_tandem | Max stress reduction and energy recovery; ignore critical financial and academic | exam_registration | True | 2 |
| 10 | cook_at_home, bilibili_rest, go_running, language_tandem | Immediate stress relief and hunger mitigation at the cost of academic progress a | midterm_pressure | True | 2 |
| 11 | bilibili_rest, go_running, language_tandem | Mitigate immediate hunger and stress via cheap food and rest; accept severe acad | desperate_illegal_work_offer | True | 3 |
| 12 | take_a_real_break, cook_at_home, go_running, bilibili_rest | Maximize immediate stress relief and energy recovery; accept severe academic and | group_invite | True | 3 |
| 13 | take_a_real_break, go_running, bilibili_rest, language_tandem | Maximize stress relief and energy recovery; accept severe academic and visa prog | exercise_sheet_warning | True | 3 |
| 14 | cook_at_home, go_running, bilibili_rest, take_a_real_break | Max stress/energy recovery and hunger mitigation; accept academic decay and fina | visa_status_hidden_check | True | 3 |
| 15 | take_a_real_break, bilibili_rest, go_running | Maximize immediate stress relief and energy recovery; accept severe academic dec | student_job_offer | True | 3 |
| 16 | take_a_real_break, go_running, bilibili_rest | Maximize stress reduction and energy recovery via rest and food; accept total ac | klausur_countdown | True | 3 |
| 17 | take_a_real_break, bilibili_rest, go_running | Maximize immediate stress relief and hunger mitigation; accept total academic fa | project_presentation | True | 3 |
| 18 | take_a_real_break, bilibili_rest, go_running, cook_at_home | Prioritize immediate stress relief and hunger mitigation; accept total academic  | exam_week | True | 4 |
| 19 | take_a_real_break, bilibili_rest, go_running | Max stress/energy recovery and hunger mitigation; accept academic decay and fina | after_exam_void | True | 4 |

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
| 11 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 100.0 to 66 in a single week (Δ=-34.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 12.0 to 46 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 46.0 to 80 in a single week (Δ=+34.0). |

