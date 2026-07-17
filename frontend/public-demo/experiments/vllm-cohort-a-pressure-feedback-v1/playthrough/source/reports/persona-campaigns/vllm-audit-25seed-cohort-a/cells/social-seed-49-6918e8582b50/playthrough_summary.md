# Interactive Player Summary

## Overview

- run id: **social-seed-49-6918e8582b50**
- weeks played: **19**
- final ending: **cashflow_collapse**
- truncated at max_weeks: **False**

## Final State

```json
{
  "academic_progress": 0,
  "annual_work_half_days": 0,
  "aps_knowledge": 32,
  "aps_score": 0,
  "arrears_amount": 1234,
  "background": "ordinary",
  "blocked_account_balance": 6944,
  "career_progress": 10,
  "cash_shortfall_count": 8,
  "city": "Berlin",
  "completed_events": [
    "arrival",
    "semester_ticket",
    "missing_school_registration",
    "wg_interview",
    "legal_work_limit_notice",
    "anmeldung_deadline",
    "academic_gap",
    "testdaf_blocks_enrollment",
    "exam_registration",
    "midterm_pressure",
    "prof_email",
    "group_invite",
    "exercise_sheet_warning",
    "visa_status_hidden_check",
    "office_hour_full",
    "klausur_countdown",
    "project_presentation",
    "exam_week",
    "after_exam_void"
  ],
  "content_version": "dev-hardcoded-0.1.0",
  "current_week_work_hours": 0,
  "difficulty": "normal",
  "energy": 65,
  "exam_readiness": 20,
  "failed_courses": 1,
  "flags": {
    "anna_group": true,
    "arrears": true,
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
  "gpa_score": 63,
  "hunger": 100,
  "language": 100,
  "last_ending_id": "cashflow_collapse",
  "last_exam_result": {
    "academic_progress": 0,
    "energy": 65,
    "exam_readiness": 30,
    "failed_courses": 1,
    "grade": 5.0,
    "passed": false,
    "score": 14,
    "stress": 90,
    "summary": "Nicht bestanden"
  },
  "loneliness": 5,
  "money": 0,
  "no_social_streak": 0,
  "parent_pressure": 64,
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
  "rng_state": -3588809084663003793,
  "rules_version": "sim-0.2.0",
  "run_id": 1,
  "seed": 49,
  "semester": 1,
  "social": 96,
  "stress": 100,
  "testdaf_listening": 2,
  "testdaf_reading": 2,
  "testdaf_speaking": 2,
  "testdaf_writing": 2,
  "university_tier": "未定位",
  "unpaid_social_streak": 8,
  "visa_progress": 75,
  "week": 20,
  "weekly_free_social_actions": 0,
  "weekly_paid_social_actions": 0,
  "weekly_snapshots": []
}
```

## Weekly Decisions

| week | actions | goal | event | valid | anomalies |
| --- | --- | --- | --- | --- | --- |
| 1 | bank_account, insurance_paperwork, language_tandem, cook_at_home | Prioritize essential admin tasks for registration and visa progress while using  | arrival | True | 0 |
| 2 | language_tandem, student_club, cook_at_home, go_running | Gain social connections and language practice while maintaining low stress and h | semester_ticket | True | 0 |
| 3 | language_tandem, cook_at_home, budget_call | Prioritize critical TestDaF exam to unlock registration, while using social/lang | missing_school_registration | True | 0 |
| 4 | anmeldung, language_tandem, cook_at_home, go_running | Prioritize time-sensitive admin task (Anmeldung) to unlock visa progress, while  | wg_interview | True | 0 |
| 5 | language_tandem, cook_at_home, go_running, sell_unused_stuff | Prioritize immediate cash injection and social/mental stability to avoid burnout | legal_work_limit_notice | True | 0 |
| 6 | language_tandem, cook_at_home, student_club, write_email_practice | 优先通过社交和语言活动维持人设并缓解孤独，同时做饭控制饥饿和成本；暂不投入高精力备考以保留能量应对突发行政需求 | anmeldung_deadline | True | 0 |
| 7 | language_tandem, cook_at_home, go_running, write_email_practice | Prioritize social connection and language practice to align with persona, while  | academic_gap | True | 0 |
| 8 | language_tandem, go_running, write_email_practice | Maintain social/language persona and mental health while deferring high-stress a | testdaf_blocks_enrollment | True | 0 |
| 9 | rent_talk_extension, budget_call, language_tandem, go_running | Prioritize immediate cash flow stabilization via rent negotiation and family sup | exam_registration | True | 2 |
| 10 | wg_dinner, language_tandem, cook_at_home, sleep_recover | Prioritize stress reduction and social connection over academic progress and imm | midterm_pressure | True | 2 |
| 11 | take_a_real_break, go_running, cook_at_home, language_tandem | Prioritize immediate stress reduction and basic survival (hunger) to prevent bur | prof_email | True | 2 |
| 12 | take_a_real_break, language_tandem, budget_call, go_running | Prioritize immediate stress reduction and cash injection to prevent burnout and  | group_invite | True | 3 |
| 13 | go_running, language_tandem, student_club | Prioritize immediate survival (hunger/stress) and social persona maintenance; de | exercise_sheet_warning | True | 3 |
| 14 | cook_at_home, take_a_real_break, language_tandem, budget_call | Sacrifice academic progress and exam readiness to stabilize critical survival me | visa_status_hidden_check | True | 3 |
| 15 | take_a_real_break, cook_at_home, rent_talk_extension, go_running | Prioritize immediate survival and stress reduction to prevent game over; accept  | office_hour_full | True | 3 |
| 16 | take_a_real_break, language_tandem, office_hour | Stabilize survival (hunger/stress) and maintain social/language persona while ma | klausur_countdown | True | 3 |
| 17 | take_a_real_break, language_tandem, office_hour | Prioritize immediate survival (hunger/stress) to prevent game over, while mainta | project_presentation | True | 4 |
| 18 | take_a_real_break, cook_at_home, language_tandem, go_running | Prioritize immediate survival and stress reduction to prevent game over; accept  | exam_week | True | 4 |
| 19 | take_a_real_break, language_tandem, office_hour | Stabilize survival metrics (stress/hunger) to prevent game over; minimal academi | after_exam_void | True | 4 |

## Anomalies Triggered

| week | kind | severity | message |
| --- | --- | --- | --- |
| 9 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 9 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 10 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 10 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 11 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 11 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 12 | `single_week_spike` | warning | `hunger` jumped from 64.0 to 98 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 13 | `single_week_spike` | warning | `hunger` jumped from 64.0 to 98 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 14 | `single_week_spike` | warning | `hunger` jumped from 64.0 to 98 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 15 | `single_week_spike` | warning | `hunger` jumped from 64.0 to 98 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 16 | `single_week_spike` | warning | `hunger` jumped from 64.0 to 98 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 17 | `single_week_spike` | warning | `hunger` jumped from 64.0 to 98 in a single week (Δ=+34.0). |
| 17 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 6 consecutive weeks (week=17). |
| 18 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 36.0 to 70 in a single week (Δ=+34.0). |
| 18 | `single_week_spike` | warning | `hunger` jumped from 64.0 to 98 in a single week (Δ=+34.0). |
| 18 | `hunger_ignored_too_long` | warning | Hunger ≥ 85 for 7 consecutive weeks (week=18). |
| 19 | `single_week_spike` | warning | `stress` jumped from 61.0 to 91 in a single week (Δ=+30.0). |

