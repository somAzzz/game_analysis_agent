# Route Boundary Audit

## Objective

Phase 3 的目标是让 Study、Work、Admin、Social、Slacker 五条路线在自动模拟中表现出不同的行动偏好、压力来源和结局分布，避免所有策略都收敛到同一套最优行动。

## Current Policies

- `study`：优先学业、备考、office hour，接受高压力和行政风险。
- `work`：优先合法工时、HiWi/职业准备和现金流，承担学业与工时合规风险。
- `admin`：优先邮件、International Office、保险、银行、Anmeldung、居留和注册，成长慢但少爆炸。
- `social`：优先语言交换、社团、约会、WG/同学饭局和小组协作，通过关系降低孤独并获得信息。
- `slacker`：优先短期舒适、恢复和生活行动，学业与注册风险显著上升。

所有路线仍保留最低限度的 APS/TestDaF/注册/居留管线推进权重，防止 policy 因路线偏好卡死在申请季。

## Verification Commands

```bash
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/ValidateContent.gd --out reports/content_validation_route_pipeline_fix.json
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/ValidateJsonContent.gd
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/RunSimulation.gd --runs 6 --policy study --difficulty normal --out reports/route_audit_study.jsonl
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/RunSimulation.gd --runs 6 --policy work --difficulty normal --out reports/route_audit_work.jsonl
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/RunSimulation.gd --runs 6 --policy admin --difficulty normal --out reports/route_audit_admin_after_fix.jsonl
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/RunSimulation.gd --runs 6 --policy social --difficulty normal --out reports/route_audit_social.jsonl
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/RunSimulation.gd --runs 6 --policy slacker --difficulty normal --out reports/route_audit_slacker.jsonl
HOME=/Users/bo/projects/study-in-germany/.tmp-home godot4 --headless --path . --script scripts/tools/ValidateRouteBoundaries.gd --out reports/route_boundary_validation.json
```

`ValidateRouteBoundaries.gd` checks that each route has enough runs, no `pipeline_stalled` outcomes, expected route-signature actions in its top actions, and no single action appears in every policy top 3.

## Results

| Route | Ending distribution | Top actions | Route signal |
| --- | --- | --- | --- |
| study | 3 survival_struggle, 3 admin_collapse | problem_set, office_hour, library_day, classmate_meal | 学业/备考满格，但居留和压力风险明显。 |
| work | 6 work_warrior | part_time_job, office_hour, cv_workshop, apply_howi | 现金和职业高，合法工时显著增加；默认守 20h 周工时红线，学业进度被压低。 |
| admin | 2 academic_failure, 2 stable_start, 2 survival_struggle | write_email_practice, international_office, bank_account, insurance_paperwork | 注册/居留稳定，学业成长慢，结局更分散。 |
| social | 4 survival_struggle, 2 admin_collapse | language_tandem, student_club, date_night, group_project | 社交和语言高，孤独低，但行政/学业仍不能被关系完全替代。 |
| slacker | 4 academic_failure, 2 registration_failure | go_running, cook_at_home, bilibili_rest, date_night | 压力和饥饿低，但学业、备考和注册风险集中爆发。 |

## Acceptance Check

- 五条路线的 top actions 明显不同，没有一个行动同时出现在所有路线 top 3。
- `ValidateRouteBoundaries.gd` passes and writes `reports/route_boundary_validation.json`.
- 学习线不等于稳定成功：会牺牲行政并进入 admin_collapse / survival_struggle。
- 打工线不再被 `budget_call` 冒充；现在会真实选择 `part_time_job` / `mini_job_extra`，并触发工时压力。
- 社交线能托住孤独和语言，但不能替代注册、现金流和考试。
- 躺平线能短期舒服，但会稳定制造 academic_failure / registration_failure。

## Remaining Balance Watch

- Work route 已从 6/6 `burnout_pause` 调整为稳定进入 `work_warrior`；后续可继续增加更细的 legal-trouble / HiWi-success 分叉。
- Admin route 已从现金流崩盘修正为行政稳定路线，但学业结果偏弱；这是符合“慢成长”的方向，后续可以加更明确的行政正反馈事件。
- Study route 高压且行政风险高，符合边界；后续 UI 应更早提示“居留未确认”风险。
