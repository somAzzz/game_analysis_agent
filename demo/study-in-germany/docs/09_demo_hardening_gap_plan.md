# Demo Hardening Gap Plan

## Objective

下一阶段目标不是继续扩内容，而是把现有 Demo 从“能跑的内容模拟器”打磨成“有路线、有压力、有辨识度的可试玩 Demo”。

当前项目已经超过 MVP 内容量：43 张行动卡、128 个事件、17 个结局、headless 校验和模拟工具都已可用。主要 gap 不在内容数量，而在数值约束、路线边界、选择代价、UI 引导和关键事件辨识度。

## Current Evidence

- `ValidateContent.gd` 当前通过：0 errors / 0 warnings。
- 内容规模：43 actions / 128 events / 17 endings。
- 模拟暴露的问题：
  - 恢复行动和生活行动过于稳定，`sleep_recover`、`bilibili_rest`、`therapy`、`cook_at_home`、饭局行动容易成为避难所。
  - 高压力、高饥饿、严重负债时仍可能进入普通成功类结局。
  - 玩家能看到风险文本，但缺少结构化 top risks 和建议行动。
  - 事件数量足够，但关键事件的选项辨识度仍需集中打磨。

## Phase 0: Checkpoint And Baseline

Tasks:

- Commit current playable dashboard state.
- Tag `demo-dashboard-v0.1`.
- Create branch `demo-hardening-v0.2`.
- Export baseline simulation reports for normal / realistic / low_money scenarios.

Acceptance:

- Worktree has a named checkpoint.
- Baseline reports are stored under `reports/`.
- Future balance changes can be compared against baseline.

## Phase 1: Data Maintainability

Tasks:

- Split hardcoded content out of `DataRegistry.gd`.
- Target structure:
  - `data/actions/*.json`
  - `data/events/*.json`
  - `data/endings/*.json`
  - `data/characters/*.json`
- Add `DataLoader.gd`.
- Keep `DataRegistry.gd` as query facade only.
- Extend validator to validate JSON content before runtime.

Acceptance:

- Existing content loads without behavior loss.
- Content validation remains 0 errors.
- Adding one action/event no longer requires editing the giant registry file.

Note: this is a large migration and should be done after a checkpoint. It is not mixed with urgent balance fixes.

Implementation status:

- Added `scripts/data/DataLoader.gd` with JSON to Resource loaders for actions, events, choices, endings and characters, plus Resource to Dictionary exporters.
- Added `scripts/tools/ExportContentJson.gd` to export the current hardcoded registry into:
  - `data/actions/generated_actions.json`
  - `data/events/generated_events.json`
  - `data/endings/generated_endings.json`
  - `data/characters/npcs.json`
- Added `scripts/tools/SplitEventsJsonByGroup.gd` to split the generated event snapshot into:
  - `data/events/application_events.json`
  - `data/events/admin_events.json`
  - `data/events/academic_events.json`
  - `data/events/life_events.json`
  - `data/events/work_events.json`
  - `data/events/relationship_events.json`
  - `data/events/random_events.json`
- Added `scripts/tools/ValidateJsonContent.gd` to load generated JSON back into Resource objects.
- Current JSON smoke result: 43 actions / 128 events / 17 endings / 5 characters load successfully.
- Runtime now loads actions from `data/actions/generated_actions.json`, events from the 7 grouped `data/events/*_events.json` files, characters from `data/characters/npcs.json`, and endings from `data/endings/generated_endings.json`, with hardcoded fallback if JSON is missing or invalid.
- `scripts/tools/PrintDataSources.gd` verifies active sources; current output includes `actions=res://data/actions/generated_actions.json`, grouped event source paths, `characters=res://data/characters/npcs.json` and `endings=res://data/endings/generated_endings.json`.
- Event records now include `source_order`; grouped event files are sorted back to original order at load time so fixed-event priority remains stable.
- JSON action/event/endings smoke result: balanced normal 6 runs produced stable/social endings with 0 bad-success cases; low_money_start 6 runs produced 6 cashflow crisis endings with 0 bad-success cases.

## Phase 2: P0 Gameplay Fixes

### 2.1 Crisis-First Endings

Tasks:

- Add hard crisis endings:
  - `cashflow_collapse`: `money < -1000`, `hunger > 80`, `stress > 80`.
  - `living_imbalance`: `hunger >= 95`, `money < 0`, low energy or severe stress.
  - `burnout_pause`: very high stress combined with low academic/loneliness pressure.
- Add hard survival gates to success endings:
  - `social_connector`: require strong social, school registration, acceptable money, hunger, stress and academic baseline.
  - `stable_start`: require money/stress/hunger survival floor.
  - `career_launch` and `high_pressure_top_student`: cannot trigger during basic survival collapse.

Acceptance:

- `money < -1000 && hunger > 80 && stress > 80` never resolves to `social_connector`, `stable_start`, `career_launch`, or other success endings.
- Low money scenario produces crisis/survival endings instead of misleading success.

### 2.2 Recovery Action Controls

Tasks:

- Add action control fields:
  - `cooldown_group`
  - `max_per_week`
  - `diminishing_window`
  - `diminishing_factor`
- Track weekly action/group counts in `GameState`.
- Apply diminishing returns to restorative effects in `ActionResolver`.
- Tune key recovery/life actions:
  - `sleep_recover`: once per week, rest group, academic/career cost.
  - `bilibili_rest`: short-term pressure relief, stronger academic/loneliness cost.
  - `therapy`: rescue action, high cost, stress requirement, cooldown group.
  - `cook_at_home`: practical hunger tool, limited per week.
  - `classmate_meal` / `wg_dinner`: social food help, limited by group cooldown.

Acceptance:

- Balanced bot no longer solves most runs by repeatedly selecting the same recovery cluster.
- Stress does not trivially stay at 0 across realistic runs.
- Hunger/social recovery is useful but not infinite.

### 2.3 RiskEvaluator UI

Tasks:

- Add `scripts/simulation/RiskEvaluator.gd`.
- Return top 3 risks with score, title, body and suggested actions.
- Show top risks in main UI objective/risk area.
- Validate that suggested actions exist and at least one suggestion is currently actionable in representative risk states.

Acceptance:

- Every week the player can see the three most dangerous issues.
- Risk text includes actionable next steps, not just red flags.

Implementation status:

- `RiskEvaluator.gd` now covers application-season APS and TestDaF risks, registration, cashflow, academics, stress, hunger, visa and work compliance.
- Main UI renders top risks under the status panel and maps suggested action ids to player-facing action names.
- Added `scripts/tools/ValidateRiskGuidance.gd`, which checks 9 representative states: APS blocked, application TestDaF pending, registration window, cashflow crisis, academic warning, stress warning, hunger warning, visa warning and work-limit warning.
- Current validation: `ValidateRiskGuidance.gd` passes and is now included in `ValidateDemoGates.gd`.

### 2.4 Work Income Rules

Tasks:

- Keep legal student work income derived from hours, not hardcoded money rewards.
- Use the current 2026 Germany minimum wage as the legal hourly wage.
- Keep illegal cash work below minimum wage and separate from legal weekly-hour accounting.
- Validate that work-flavored content does not bypass hourly wage calculation by directly adding positive `money`.

Acceptance:

- Legal work effects use `work_hours`; income is calculated as `hours * 13.90 EUR`.
- Illegal cash work effects use `illegal_work_hours`; income is calculated at `80%` of the legal wage.
- Work options cannot mix direct positive `money` with work-hour effects.
- Options that look like job/shift/work income warn or fail validation if they use direct positive `money` instead of hours.

Implementation status:

- `EconomyRules.gd` centralizes `LEGAL_WORK_HOURLY_WAGE_2026 = 13.90` and `ILLEGAL_CASH_WORK_WAGE_RATIO = 0.80`.
- `GameState.apply_effects` routes `work_hours` through `apply_work_hours` and `illegal_work_hours` through `apply_illegal_work_hours`.
- Converted `aps_part_time_job`, `临时打工补费用`, `赌不会被发现` and `接更多班补窟窿` from direct positive `money` rewards to hour-based work effects.
- `ValidateEconomyRules.gd` now checks wage constants, runtime income application, no mixed positive money/hour effects, and work-flavored direct-money leaks.
- Current validation: legal 10h -> 139 EUR; illegal 10h -> 111 EUR.

## Phase 3: Route Boundaries

Define five main routes:

- Study route: academic/exam success, stress risk.
- Work route: cash survival and work experience, legal/study risk.
- Social route: information and help, but cannot replace money/register/exams.
- Admin route: fewer explosions, slower growth.
- Slacker route: short-term comfort, long-term deadline and academic collapse.

Acceptance:

- Study, work, admin, social and slacker bots produce visibly different action picks and ending distributions.
- No single action appears in top 3 for every bot and every scenario.

Implementation status:

- Added route policies: `WorkPolicy.gd`, `AdminPolicy.gd`, `SocialPolicy.gd`, and `SlackerPolicy.gd`; `StudyPolicy.gd` already existed.
- `RunSimulation.gd` now accepts `--policy study|work|admin|social|slacker|balanced|random`.
- Added route audit notes in `docs/10_route_boundary_audit.md`.
- Added `scripts/tools/ValidateRouteBoundaries.gd` to automatically validate route reports for minimum run count, no pipeline stalls, route-signature top actions, and no universal top-3 action collapse.
- Added `scripts/tools/ValidateDemoGates.gd` to validate v0.2 demo gates from generated simulation reports: report size, bad-success cases, top action share, normal ending variety, low-money crisis rate, route-boundary report status and risk-guidance report status.
- Current route audit confirms distinct top-action clusters:
  - study: `problem_set`, `office_hour`, `library_day`.
  - work: `part_time_job`, `office_hour`, `cv_workshop`, `apply_howi`.
  - admin: `write_email_practice`, `international_office`, `bank_account`, `insurance_paperwork`.
  - social: `language_tandem`, `student_club`, `date_night`, `group_project`.
  - slacker: `go_running`, `cook_at_home`, `bilibili_rest`.
- Remaining watch: work route now resolves cleanly to `work_warrior`; admin route is stable administratively but academically weak.

## Phase 4: Exam And Failure Feedback

Tasks:

- Add `exam_readiness`.
- Add failed-course consequence flags such as `needs_retake`.
- Add mid-semester academic warning events around weeks 8, 12, 16 and 18.
- Make final exam failure affect ending selection.

Acceptance:

- Sacrificing study triggers midgame feedback before week 20.
- Exam failure creates follow-up pressure, not just a final number.

Implementation status:

- `exam_readiness` and `failed_courses` are implemented in `GameState`, save data, UI stats and simulation exports.
- `ExamResolver` now weights academic progress, exam readiness, language, energy, stress and randomness; failure sets `needs_retake`.
- Added week 13 and week 16 exam warning events, expanded week 18 Klausur choices, and added `academic_failure`.
- Current validation: `ValidateContent.gd` reports 0 errors / 0 warnings after this phase.

## Phase 5: Key Event Rewrite

Tasks:

- Identify 20 high-frequency or mainline events.
- Rewrite each with four sharp options:
  - safe but costly
  - risky high reward
  - social/language/admin gated option
  - avoidant short-term relief with long-term cost
- Add validator warnings for weak options:
  - no negative cost
  - nearly identical effects
  - generic option text
  - no effect/flag/requirement

Acceptance:

- Mainline events have memorable trade-offs.
- Auto-completed options are no longer carrying important events.

Implementation status:

- Added mainline event quality checks to `ValidateContent.gd`; the validator now flags priority events with fewer than four choices, empty choices, risky choices without failure effects, risky choices without stat modifiers, and duplicate choice effect signatures.
- Added a mainline generic-option gate to `ValidateContent.gd`; priority events now warn if they use auto-fill texts such as `稳妥处理`, `寻求帮助`, `冒险推进` or `暂时回避`.
- Fixed Phase 5 mainline id coverage in `ValidateContent.gd` and `ValidateJsonContent.gd`: `job_study_conflict` and `lonely_christmas` are now checked by their real event ids, and missing mainline ids are hard validation errors.
- Rewrote the first Phase 5 batch as hand-authored four-option events: `arrival`, `first_lecture`, `wg_interview`, `anmeldung_deadline`, `midterm_pressure`, `group_invite`, `semester_wrap`, `termin_missing`, `rent_pressure`, `lonely_christmas`, and `job_study_conflict`.
- Re-exported `docs/05_event_choice_balance.md`; current content remains 128 events / 512 choices.
- Current validation: `ValidateContent.gd` and `ValidateJsonContent.gd` report 0 errors / 0 warnings after this batch.
- Current simulation sample:
  - balanced normal, 12 runs: 0 bad-success cases; top action share 14.6%.
  - balanced realistic, 12 runs: 4 ending types; 10 passed / 2 failed exams; 0 bad-success cases; top action share 10.1%.

## Phase 6: Playable Packaging

Tasks:

- Add first-semester report page.
- Track run stats such as most-used action, worst week, black-work temptations, emails, parent calls.
- Strengthen visual concept around files, mail, phone chats and deadlines.

Acceptance:

- End screen is shareable and tells a specific story.
- Demo feels like “德国留学生文件夹人生”, not a generic stat dashboard.

Implementation status:

- Added weekly state snapshots to `GameState` and save data, including stress, hunger, money, study, exam readiness, work hours and a pressure score.
- Added `SemesterReportBuilder.gd`, which generates a first-semester report from action history, completed events, flags and weekly snapshots.
- End screen now includes route profile, most-used action, hardest week, paperwork status, relationship/family notes, work/legal risk notes and a one-line summary.
- Simulation output now includes `final_report`, so report quality can be checked without opening the UI.
- Result text area is scrollable to support longer shareable reports.
- Current validation: `ValidateContent.gd` reports 0 errors / 0 warnings after this phase; Godot headless boot passes.
- Current simulation sample:
  - balanced normal, 12 runs: 4 ending types (`career_launch`, `social_connector`, `stable_start`, `work_warrior`); 0 bad-success cases; top action share 9.5%.
  - balanced realistic, 12 runs: 4 ending types (`burnout_pause`, `social_connector`, `stable_start`, `survival_struggle`); 0 bad-success cases.
  - balanced low_money_start, 12 runs: 9 `burnout_pause`, 3 `cashflow_collapse`; 0 bad-success cases.
  - `ValidateDemoGates.gd` passes against the latest normal / realistic / low_money reports plus `ValidateContent.gd`, `ValidateRouteBoundaries.gd` and `ValidateRiskGuidance.gd`.

## v0.2 Gates

Technical:

- `ValidateContent.gd`: 0 errors.
- Warnings below 20.
- Every event has 4 valid options.
- Mainline events do not use generic auto-fill option text.
- Headless simulation runs for normal, realistic and low_money scenarios.

Balance:

- No high hunger/high stress/heavy debt success ending.
- Balanced bot top action share below 15% for any single action.
- Normal scenario has at least 4 ending types over larger runs.
- Low money scenario crisis/survival endings are common.
- Work-focused and study-focused policies produce different endings.
- Risk guidance validation has no missing or unavailable suggested actions.

Automated gate command:

```bash
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/ValidateContent.gd --out reports/content_validation.json
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/ValidateRiskGuidance.gd --out reports/risk_guidance_validation.json
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/ValidateDemoGates.gd --out reports/demo_gate_validation.json
```

Experience:

- Top 3 risks are visible each week.
- Recovery actions are useful but cannot be spammed.
- Main route choices create meaningful sacrifices.
