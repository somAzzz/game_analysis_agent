---
status: active
date: 2026-08-21
audience: [maintainers, product, frontend, game, content]
scope: >-
  现有游戏与前端能力盘点、可配置参数字典、缺口分析、前端方案原始材料。
  本文是 discovery / source material，不是声称已实现的计划，也不做玩法平衡判断。
  所有事实以 2026-08-21 仓库快照为证据；跨仓库数字未来可能变化。
---

# 游戏参数与卡牌作者工作台 Discovery（2026-08-21 快照）

> 本文是 **discovery / source material**，供后续 PRD / API contract / ADR / build checklist 使用。
> 文中每条事实均标注证据路径；跨仓库数字（79 卡 / 138 事件 / 4 flow / 8 段 / 22 结局 / 5 NPC）为
> **2026-08-21 快照**，未来可能变化。本文**不做玩法平衡判断**。

## 0. 结论摘要

- **优先扩展 `study-in-germany/workbench` 为统一 Content Workbench**（事件 + 卡牌 + 参数 + 图片），
  而不是把游戏内容 CRUD 塞进 `game_analysis_agent/frontend` 的 React 看板。
- **理由**：workbench 已具备 Node API（`workbench/server.mjs`）、事件发布链（**event-only**：
  validate → compile → publish → Godot event-only safe reload）、Godot live bridge
  （WebSocket `set_state` / `trigger_event` / `reload_content`，reload 仅事件）、原子写与 revision 乐观并发；
  卡牌 canonical source 与编译产物都在同一 sibling 仓库，扩展现有 API 成本最低。
- **两个产品保持边界**：`game_analysis_agent` 继续负责分析 / 评审 / 矩阵 / persona / 证据；
  通过后续“分析触发 / 深链”协作（例如从分析看板深链到 workbench 的某张卡 / 某个事件），不合并内容编辑。
- **卡牌图片（`presentation.icon` / `accent`）当前在 schema 与 pack manifest 中预留，但编译 / Godot
  渲染链路未贯通**；“上传图片并显示”需要 §3 的端到端 8 段链路。
- **关键现状缺口（source）**：workbench 发布链当前是 **event-only** —— 当前 `/api/validate` 只运行事件
  authoring/graph/schedule validator；当前 `/api/compile` 与 `/api/publish` 只调用 `CompileEventContent.gd`，
  它读取现有 `action_content_manifest.json` 并把其 hash/card_count 写进 combined `content_manifest.json`，
  但不会运行 `tools/cards validate/compile/check`，因此卡牌源修改可能仍对应旧 action runtime/manifest；
  当前 `WorkbenchBridge._reload_content()` 只调用 `DataRegistry.reload_event_source(true)`（DataRegistry 没有公开
  action reload 方法），因此即使未来编译了新 `actions.runtime.json`，正在运行的 Godot 会话也不会通过现有 bridge
  热重载行动卡。§2.3 / §7 / §9 中统一的 card+event 发布链是 **proposal**，不是现状。

## 1. 两套前端边界

| 维度 | `game_analysis_agent/frontend`（React/Vite） | `study-in-germany/workbench`（原生 JS/Node） |
|---|---|---|
| 技术栈 | React 18 + Vite + TypeScript（`react-router-dom`） | 原生 JS ESM（`server.mjs` + 静态 `public/`） |
| 定位 | 分析 / 评审看板（Judge Mission、playthrough inspector、reports/issues、decision graph） | 事件作者工作台（事件 / 时间轴 / 剧情图 / 现场） |
| 路由 | 见 `frontend/src/App.tsx`：`/`（JudgePage）、`/playthrough-inspector`、`/reports`、`/issue/:kind/:id`、`/decision-graph/:runId` | 单页 4 个 view：editor / timeline / graph / live（见 `public/index.html`） |
| 数据读取 | 静态 manifests（`manifest.json`、`browse/.../manifest.json`、decision graph manifest、`experiment-index.json`、`experiments/.../judge-experiment.json`、`judge-demo.json`）+ Judge API（`provider-status` / `provider-test` / `campaigns` / `experiments` / `human-review`） | REST `/api/events`、`/api/flows`、`/api/validate`、`/api/compile`、`/api/publish`、`/api/runtime/*` + WebSocket `/api/runtime/live` |
| 游戏内容 CRUD | **无**（无卡牌编辑、无图片上传、无 pack/registries 路由） | 事件 CRUD（list/detail/create/save/clone/archive）+ flow 保存；**无 cards/pack/registries/assets 路由** |
| 发布 | 分析证据 / 报告（静态 JSON） | 事件 validate/compile/publish + event-only safe reload；combined manifest 只引用已有 action manifest |
| 结论 | 分析参数与游戏内容参数分层 | 内容编辑应落在 workbench |

证据：`frontend/src/App.tsx`、`frontend/src/lib/api.ts`（本仓库）；
`workbench/README.md`、`workbench/server.mjs`、`workbench/public/index.html`、`workbench/public/app.js`（sibling）。

## 2. 卡牌现状（canonical source → runtime）

- **canonical source**：`content/card_packs/core/pack.json` + `content/card_packs/core/cards/*.json`，共 **79** 张；
  pack manifest `cards` 数组也是 79 条。
- **编译产物**：`content/generated/actions.runtime.json` 的 `items` 共 **79**；
  `content/generated/action_content_manifest.json` 的 `card_count=79`、`compiler_version=1.1.0`、`source_files=80`（pack.json + 79 cards）。
- **运行时**：`autoload/DataRegistry.gd` 从 `res://content/generated/actions.runtime.json` 加载；
  `project.godot` `[action_authoring] legacy_action_fallback_enabled=false`（**legacy fallback 关闭**）。
- **工具**：`tools/cards.py` 命令 `validate` / `compile` / `check` / `new-card`；
  具备路径安全（`_safe_relative`）、注册表 / 语义校验、确定性排序（core 按 `source_order`，additive 按 `card_id`）、
  原子输出（`_atomic_write`）与 freshness check（`check` → `fresh:true`）。
- **缺失**：无 HTTP CRUD、无 revision 字段、无单卡 archive/delete、无图片上传；
  workbench 无卡牌 validate/compile/publish/热重载入口（卡牌链路仅手动 CLI，见 §2.3）。
- **schema**：`content/schemas/action-card-v1.schema.json` / `action-card-v2.schema.json`（v1/v2）。

### 2.1 顶层字段（v2）

`schema_version, card_id, source_order, name_key, description_key, fallback_name,
fallback_description, legacy_ids, costs, effects, requirements, tags, risk_tags,
keywords, execution, resolution(v2 optional), supply, upgrade_paths, presentation`

### 2.2 关键子结构

- **costs**：`slots` 0..4、`energy` 0..1000、`money` 0..1,000,000。
- **effects registry（16 项，`content/registries/effects_v1.json`）**：
  `academic_progress, admin_readiness, aps_knowledge, arrears_amount, career_progress, energy,
  exam_readiness, hunger, language, loneliness, money, parent_pressure, reciprocity_debt,
  social, stress, work_hours`。
- **conditions registry（15 项，`content/registries/conditions_v1.json`）**：
  `flag, learned_action, max_energy, max_parent_pressure, max_reciprocity_debt, max_week,
  min_aps_knowledge, min_hunger, min_language, min_money, min_semester, min_social,
  min_stress, min_week, missing_flag`。
  > 注意：`requirements` 与 `supply.*_when` 使用**同一** registry；当前实际出现的条件集合是
  > registry 允许集合的**子集**（需按卡逐一核对，本文不做玩法判断）。
  > 实际出现（2026-08-21 快照，79 张卡）：`requirements` 实际出现 **13** 项：
  > `flag, max_energy, max_parent_pressure, max_reciprocity_debt, max_week, min_aps_knowledge,
  > min_hunger, min_language, min_money, min_social, min_stress, min_week, missing_flag`。
  > `supply.unlock_when/visible_when/offer_when/retire_when/expire_when` 实际出现 **6** 项：
  > `flag, learned_action, max_week, min_semester, min_week, missing_flag`。
- **scope**：`segment_ids, segment_kinds, phases, semester_min, semester_max`。
- **execution**：`set_flag, cooldown_group, max_per_week(0..4), diminishing_window(0..52),
  diminishing_factor(0..1)`。
- **supply**：`schema_version`；`type` base/opportunity/critical/burden；`lane`
  personal/opportunity/system；`deck_policy` starter/learnable/external_only/never；`retain_policy`
  one_week/none；`draw_category` growth/life/wildcard；`base_weight, priority, first_grant,
  unlock_when, visible_when, offer_when, retire_when, expire_when, deadline, auto_offer,
  offer_groups, plan_groups, crisis_for`；可选 `term_learning, base_role, delay_policy`。
  > 部分组合有语义约束（`tools/cards.py` 的 `SUPPLY_POLICY_TRIPLES` / `SUPPLY_TYPE_POLICY_RULES`），
  > **不能当自由枚举随便搭配**。
- **upgrade_paths**：path label + `levels`/`effects`（现有运行时最多两级逻辑；5 张卡带 upgrade_paths）。
- **resolution v2**：`d12_check`，含 `authored_dc` 4..12、`primary`（stat+curve）、最多 2 个
  `supports`、`flat_modifiers`（-1/0/1）、`advantage/disadvantage`（各最多 1）、`difficulty_scaling`、
  `on_success`/`on_failure` 的 effects+set_flags、可选 burden `persistence`
  （`instance_kind=burden, clear_on=success, retain_on=failure, retry_dc_reduction_per_failure/cap 0..4`）。
- **presentation**：schema 允许 `icon` 与 `accent`。
- **其他 registry**：tags（25）、risk tags（9）、keywords（13）、phases（3：application /
  first_semester / later_semester）、public flags（9）、supply groups（15）、pack permissions
  （core vs additive 的能力 / 供应类型 / flag 写权限）。

### 2.3 数据流：现状（source）与 proposal 统一链路

现状 —— 两条独立链路：

- 卡牌源（`content/card_packs/**`）→ `tools/cards`（手动 CLI：`validate` / `compile` / `check`）→
  `content/generated/actions.runtime.json` + `action_content_manifest.json`
- 事件源（`content/events/**`）→ workbench `/api/validate`（事件 authoring/graph/schedule validator）+
  `/api/compile`（`CompileEventContent.gd`）→ `content/generated/events.runtime.json` + combined
  `content_manifest.json`（仅引用已有 action manifest 的 hash/card_count）→
  `WorkbenchBridge._reload_content()` → `DataRegistry.reload_event_source(true)`（**event-only** 热重载）

现状缺口：workbench 链路完全不触碰卡牌源 —— 卡牌源修改需手动运行 `tools/cards`，
且运行中的 Godot 会话没有行动卡热重载路径（DataRegistry 无公开 action reload 方法）。

Proposal 统一链路（**proposal**，非现状）：

- 卡牌源 + 事件源 → workbench 统一 validate（cards：`tools/cards validate`；events：现有事件 validator）→
  确定性 compile（cards：`tools/cards compile`；events：`CompileEventContent.gd`）→ combined manifest hash 链
  （actions.runtime / action manifest / content manifest 互相可校验）→ publish transaction
  （失败不替换现有 runtime/manifests）→ 新增 `reload_action_source` 或 `reload_all_content`，在安全点同时替换
  event/action registries → ACK 返回实际 action/event hash/version。

## 3. 图片链路断点（端到端）

Schema 与旧设计文档预留 `presentation.icon`，pack manifest 有 `assets` 数组；但**当前 core pack
`assets=[]`，79 张卡没有 `icon`，只有 `accent`**（accent 取值：admin/application/career/growth/
language/life/mental/money/social/study/wildcard）。

“上传图片并显示”需要以下 **8 段链路**，当前**全部或部分断点**：

| # | 链路段 | 当前状态 | 证据 |
|---|---|---|---|
| 1 | Source / Schema validation | **预留但未贯通**：v2 schema 允许 `presentation.icon`/`accent`，pack manifest 有 `assets`；但 `tools/cards.py _validate_card` 未校验 presentation，pack `assets` 未校验/投影 | `content/schemas/action-card-v2.schema.json`、`content/card_packs/core/pack.json`、`tools/cards.py` |
| 2 | Safe upload / storage | **断点**：workbench server 无 multipart/binary upload、无 card asset endpoint、无 asset MIME/static serving、无删除引用检查 | `workbench/server.mjs` |
| 3 | Manifest / hash | **断点**：`action_content_manifest` 只 hash `pack.json` + cards，未含 pack assets/locales/tests 的完整源文件投影 | `tools/cards.py`（`build_outputs`） |
| 4 | Compiler runtime projection | **断点**：`_runtime_record` 丢弃 `presentation`（runtime item 无 icon/accent/presentation 键） | `tools/cards.py`（`_runtime_record`）、`content/generated/actions.runtime.json` |
| 5 | DataLoader / ActionDef | **断点**：`DataLoader.action_from_dict` 不加载 presentation；`ActionDef.gd` 无 icon/accent 字段 | `scripts/data/DataLoader.gd`、`scripts/data/ActionDef.gd` |
| 6 | Godot rendering | **断点**：`Main.gd` 用 PanelContainer + Button + Label 文本渲染行动卡，不加载 Texture2D、不显示卡图；`ActionCard.tscn` 仅是静态 Button 场景，非动态列表实现 | `scenes/main/Main.gd`、`scenes/ui/ActionCard.tscn` |
| 7 | 运行时热重载 | **断点**：现有 `WorkbenchBridge._reload_content()` 为 event-only（仅调用 `DataRegistry.reload_event_source`），卡牌不会刷新；DataRegistry 无公开 action reload 方法。Proposal：新增 `reload_action_source` / `reload_all_content`，在安全点同时替换 event/action registries，ACK 返回实际 action/event hash/version | `autoload/WorkbenchBridge.gd`、`autoload/DataRegistry.gd` |
| 8 | Fallback | **建议新增**：缺图时无 fallback 策略 | — |

**建议的安全约束（明确标为建议，非现状）**：

- 仅 PNG / WebP（是否接受 JPEG 列为**开放决策**）。
- 魔数 + MIME 双验。
- 尺寸 / 像素 / 字节上限（例如 ≤ 512×512、≤ 200KB，数值待 ADR 定）。
- 随机临时文件 + 原子 rename。
- 规范化 pack-relative path；**禁止 SVG / 绝对路径 / URL / 路径穿越**。
- 覆盖与删除要做引用检查。
- 产物 hash（纳入 manifest）。
- 缺图 fallback。
- **不要建议 base64 写进 JSON**。

## 4. 可配置参数字典（矩阵）

| 参数域 | 当前 source of truth | 规模 / 例子 | 当前是否可由 UI 修改 | 验证 / 发布方式 | 建议暴露级别 |
|---|---|---|---|---|---|
| cards（79） | `content/card_packs/core/pack.json` + `cards/*.json` | 79 张 | **否**（workbench 无 card API） | `tools/cards.py` validate/compile/check | **MVP**（卡牌库/编辑器） |
| events（138） | `content/events/**/*.json` | 138 个 | **是**（workbench 事件 CRUD） | `/api/validate` + `ValidateEventGraph.gd` + `/api/compile` | MVP（已有） |
| flows（4） | `content/flows/*.json` | 4 个 | **是**（workbench flow 保存） | `/api/flows` PUT + `ValidateEventGraph` | MVP（已有） |
| pack metadata | `content/card_packs/core/pack.json` | 1 pack | **否** | `tools/cards.py` validate | 高级 |
| registries | `content/registries/*_v1.json` | effects16 / conditions15 / tags25 / risks9 / keywords13 / phases3 / flags9 / supply_groups15 | **否** | `tools/cards.py` + Godot validator | 高级（只读下拉） |
| campaign（1）+ segments（8） | `content/campaigns/germany_student_campaign.json` + `content/segments/*.json` | 1 campaign、8 segments | **否** | 无专用工具 | 暂不开放 |
| initial scenarios（3 + 1 fixture） | `data/scenarios/{default_first_semester,high_stress_start,low_money_start}.json` + `p6a_testdaf_fixtures.json` | 3 实际开局 + 1 TestDaF fixture | **否**（仅 `RunSimulation` 读取） | `RunSimulation.gd` `apply_scenario` | 高级（现场调试） |
| difficulty（4 modes） | `autoload/DifficultyConfig.gd` | easy/normal/hard/realistic；name/description/language_gate_waived/success_rate_min/max/bonus/weekly_drift/initial_profile/negative_money_stress/high_stress_academic_penalty/high_loneliness_energy/event_type/focus weights | **否**（GDScript const） | 代码 + 测试 | 高级 / 暂不开放 |
| NPC（5） | `data/characters/npcs.json`（fallback `DataRegistry._build_characters`） | 5 个 | **否** | `DataLoader.load_characters` | 高级 |
| endings（22） | `data/endings/generated_endings.json`（fallback `DataRegistry._build_endings`） | 22 个 | **否** | `DataLoader.load_endings` | 高级 |
| project authoring toggles | `project.godot` `[action_authoring]` / `[event_authoring]` | `legacy_action_fallback_enabled=false`、`event_scheduler_v2_enabled=true`、`legacy_event_fallback_enabled=false`、`workbench_bridge_enabled=false`、`workbench_url` | **否**（ProjectSettings） | Godot 启动读取 | 暂不开放 |
| game state / start-state fields | `autoload/GameState.gd` + `data/scenarios/*.json` | money, energy, stress, loneliness, hunger, academic, exam, language, social, admin, flags, city/background 等 | **部分**（workbench 现场 `set_state` 可改 week/seed/flags；完整 start-state 否） | `WorkbenchBridge` `set_state` | 高级（现场调试，**非静态设计参数**） |
| 硬编码规则参数 | 多个 `.gd` const | 见下 | **否**（需 GDScript/code/test） | 代码 + 测试 | **暂不开放**（首期不让前端任意改） |

> **说明**：game state / start-state fields 可作为“场景编辑 / 现场调试”，但**不要把运行历史 /
> 存档内部状态都当静态设计参数**。

### 4.1 硬编码规则参数域（当前改动需 GDScript / code / test）

- **MAX_STAT / 4 action slots**：`GameState.MAX_STAT=100`；`ActionSupplyService.MAX_ACTION_SLOTS=4`、
  `OFFER_CAPACITY=6`、`BASE_TARGET=2`、`CATEGORIES=[growth,life,wildcard]`。
- **economy legal work / wage / living costs**：`EconomyRules.gd`
  `LEGAL_WEEKLY_WORK_HOURS=20`、`LEGAL_ANNUAL_HALF_DAYS=280`、`LEGAL_WORK_HOURLY_WAGE_2026=13.90`、
  `ILLEGAL_CASH_WORK_WAGE_RATIO=0.80`、`GERMANY_MINIMUM_WAGE_2026=13.90`、
  `ILLEGAL_CASH_WORK_WAGE=11.12`；`GameState` `BLOCKED_ACCOUNT_REQUIRED_2026=11904`、
  `MONTHLY_RENT_ESTIMATE_2026=500`、`HEALTH_INSURANCE_MONTHLY_ESTIMATE_2026=145`。
- **action supply capacity / base target / category**：`ActionSupplyService`
  `OFFER_CAPACITY=6`、`BASE_TARGET=2`、`CATEGORIES`。
- **language thresholds / caps / ratios**：`ActionModifierService`
  `BEGINNER_LANGUAGE_THRESHOLD=38`、`BEGINNER_WEEKLY_CAP=1`、`FOUNDATION_WEEKLY_CAP=3`、
  `ADVANCED_LANGUAGE_THRESHOLD=60`、`LANGUAGE_MASTERY_CAP=89`、
  `LANGUAGE_MASTERY_WEEKS_REQUIRED=90` 及 ratio 常量。
- **burden thresholds / locks / stress / DC**：`BurdenService`
  `MAX_SEVERITY=3`、`MAX_ACTIVE_BURDENS=2`、`PARENTS_FOLLOW_UP_PRESSURE_THRESHOLD=48`、
  `UNREAD_EMAIL_IGNORED_STRESS=5`、`PARENTS_FOLLOW_UP_IGNORED_STRESS=3`、
  `ABHA_EMAIL_LOCK_TURNS=2`、`ABHA_TERMIN_LOCK_TURNS=4`、`ABHA_STRESS_PER_TURN=2`、`ABHA_D12_DC=8`。
- **residence DC / state machine**：`ResidenceService`
  `FIRST_APPLICATION_DC=7`、`RENEWAL_DC=8`、`REMEDY_DC=10`、`ENFORCEMENT_DC=9` 及 document/application 状态常量。
- **exam formula / grade thresholds**：`ExamResolver` `KLAUSUR_CHECK_SPEC`（`authored_dc=6`）、
  `raw_score = academic_progress*0.35 + exam_readiness*0.40 + language*0.10 + (energy-50)*0.08 - max(0, stress-55)*0.35 + clamp(check margin,-8,8)`，
  再 clamp 到 0..100；grade<5.0 passed。
- **route scoring / thresholds**：`RouteResolver` `WORK_ROUTE_MIN_ACTIONS=5`、
  `CLEAR_ROUTE_MARGIN=2`、`FOCUS_ROUTE_POINTS=6`、`FOCUS_ROUTES`/`ROUTES`。
- **recovery diagnostic thresholds**：`RecoveryDiagnosticService`
  `CASH_RESERVE_THRESHOLD=100`、`HUNGER_THRESHOLD=70`、`STRESS_THRESHOLD=70`、
  `ENERGY_THRESHOLD=25`、`NEED_ORDER`。
- **growth / focus / combo registries**：`scripts/data/GrowthRegistry.gd`、
  `FocusRegistry.gd`、`KeywordRegistry.gd`、`KeywordComboRegistry.gd`。

> **分层**：`game_analysis_agent` 的 matrix / persona / gate / provider config 属于“**分析参数**”，
> 与“**游戏内容参数**”分层；未来可以是单独高级页，**不要与卡牌作者 MVP 混在一起**。
> 证据：`config/matrix*.yaml`、`config/gates.yaml`、`config/player_personas.yaml`、
> `tools/gameplay/run_gameplay_agent.py`、`tools/persona/run_persona_campaign.py`（本仓库）。

## 5. 缺口矩阵（P0 / P1 / P2）

| 优先级 | 缺口 | 现状 | 目标 |
|---|---|---|---|
| P0 | card API | workbench 无 `/api/cards` 路由（list/detail/POST/PUT/clone/archive/remove） | 新增卡牌 CRUD |
| P0 | revision / concurrency | card 无 revision 字段（事件有 revision 乐观并发） | sidecar / revision manifest 或 schema 演进 |
| P0 | card save rollback validation | 保存需 validate + 全 pack 校验 + 原子写 + 失败回滚（事件已有类似模式） | 复用事件保存模式 |
| P0 | pack manifest 同步 | 新增/删除卡需同步 `pack.json` `cards` 数组（sorted/unique） | 自动同步 |
| P0 | 图片端到端 | §3 八段断点 | 打通 8 段链路 |
| P0 | combined card+event compile/publish transaction | 当前 `/api/compile` / `/api/publish` 只调用 `CompileEventContent.gd`（只引用已有 `action_content_manifest.json` 的 hash/card_count，不运行 `tools/cards validate/compile/check`）；卡牌源修改可能仍对应旧 action runtime/manifest | card validate + 确定性 compile 进入 publish transaction；失败不替换现有 runtime/manifests（**proposal**） |
| P0 | action 热重载 | 当前 `WorkbenchBridge._reload_content()` 只调用 `DataRegistry.reload_event_source(true)`；DataRegistry 无公开 action reload 方法，运行中的 Godot 会话不热重载行动卡 | 新增 `reload_action_source` 或 `reload_all_content`，在安全点同时替换 event/action registries，ACK 返回实际 action/event hash/version（**proposal**） |
| P0 | dirty / change set | 前端需 dirty 跟踪 + 变更集（事件已有 dirty，卡无） | 卡牌 dirty 跟踪 + 变更集 |
| P1 | registry dropdown / reference validation | 编辑器用 registry 下拉（effects/conditions/tags/risks/keywords/phases/flags/supply groups） | 只读 registry 下拉 |
| P1 | bulk edit / clone / create / archive | 批量操作 | 批量改卡 |
| P1 | diff / review / undo | 变更 diff、审阅、撤销 | 变更审阅 |
| P1 | preview parity | 编辑预览与 Godot 渲染一致 | 预览对齐 |
| P1 | tests | card / workbench / Godot 全套 | 全套测试 |
| P1 | access / security | 本地-only 边界、auth、路径安全、MIME/魔数 | 安全约束落地 |
| P2 | other parameter domains | difficulty / rules / scenarios / NPC / endings 的编辑 | 暂不开放或高级 |

## 6. 推荐 IA / 页面

总览、卡牌库、卡牌编辑器、事件 / 时间轴 / 剧情图（复用）、参数中心、发布中心、现场、分析入口。

```
[总览] [卡牌库] [卡牌编辑器] [事件] [时间轴] [剧情图] [参数中心] [发布中心] [现场] [分析入口]
卡牌库:     搜索/筛选(79) | 列表(id/name/tags/supply.type/revision) | 新建/克隆/归档
卡牌编辑器: 左=分区表单(基本/费用效果/条件范围/牌库供给/执行判定/升级/展示图片/JSON advanced) 右=预览+校验
参数中心:   只读 registry 下拉源 + 高级(难度/规则/场景) 折叠
发布中心:   validate→compile→publish 状态 + manifest hash + Godot reload ACK
现场:       Godot live telemetry + set_state/trigger_event/reload_content
分析入口:   深链到 game_analysis_agent (reports/issues/decision-graph)
```

### 卡牌编辑器分区与字段控件映射（具体）

- **基本**：`card_id`(disabled)、`name_key`、`description_key`、`fallback_name`、
  `fallback_description`、`legacy_ids`、`source_order`。
- **费用效果**：`costs.slots` / `energy` / `money`；`effects`（registry 下拉 + 数值）。
- **条件范围**：`requirements`（registry 下拉 + 值）；`scope.segment_ids` / `segment_kinds` /
  `phases` / `semester_min` / `semester_max`。
- **牌库供给**：`supply.*`（`type` / `lane` / `deck_policy` / `retain_policy` / `draw_category` /
  `base_weight` / `priority` / `first_grant` / `unlock_when` / `visible_when` / `offer_when` /
  `retire_when` / `expire_when` / `deadline` / `auto_offer` / `offer_groups` / `plan_groups` /
  `crisis_for` / `term_learning` / `base_role` / `delay_policy`）。
- **执行 / 判定**：`execution.*`；`resolution`（`d12_check`：`authored_dc` / `primary` /
  `supports` / `flat_modifiers` / `advantage` / `disadvantage` / `difficulty_scaling` /
  `on_success` / `on_failure` / `persistence`）。
- **升级**：`upgrade_paths`。
- **展示 / 图片**：`presentation.accent`、`presentation.icon`（upload / replace / delete）。
- **JSON advanced**：完整 JSON 编辑 + 校验（可回退）。

## 7. 核心工作流

- **改单卡**：打开卡 → 编辑分区 → 本地校验 → `PUT /api/cards/:id`（`expected_revision`）→
  服务端 validate + 全 pack 校验 + 原子写 + `revision+1` → 返回新 revision；冲突 409。
- **批量改卡**：选择多卡 → 批量字段（如 tags / costs）→ 一次提交变更集 → 服务端逐卡校验 +
  原子写 + 回滚。
- **上传 / 替换图片**：选择 PNG/WebP → `POST /api/assets/upload`（multipart）→ 魔数 + MIME +
  尺寸 / 字节校验 → 随机临时 + 原子 rename → 返回 pack-relative path + hash → 卡
  `presentation.icon` 引用 → 删除做引用检查。
- **发布到 Godot（proposal，非现状）**：`POST /api/publish`（combined card+event transaction）→
  validate（cards：`tools/cards validate`；events：现有事件 validator）→ 确定性 compile
  （cards：`tools/cards compile`；events：`CompileEventContent.gd`）→ manifest hash 链
  （actions.runtime / action manifest / content manifest）→ 失败不替换现有 runtime/manifests →
  broadcast `content_published` → Godot safe reload（新增 `reload_action_source` / `reload_all_content`，
  在安全点同时替换 event/action registries）→ ACK 返回实际 action/event hash/version。
- **回滚 / 冲突处理**：409 `revision_conflict` → 重新载入；保存失败 → 原子回滚（不覆写）；
  publish 失败 → 保留上一 manifest。

## 8. API 草案（**proposal**）

> 以下为**建议**，非现状。推荐 **JSON metadata + 独立 binary upload**，**不用 base64**。

- `GET /api/cards` → list（id, name, tags, supply.type, revision, source_order）
- `GET /api/cards/:id` → detail（full card + revision）
- `POST /api/cards` → create（validate + pack manifest 同步 + `revision=1`；revision 记录于
  sidecar/HTTP metadata，除非 Phase 0 决定 schema 演进，否则不写进稳定 card JSON）
- `PUT /api/cards/:id` → update（`expected_revision` 或 ETag；409 on conflict；validate + 原子写 + 回滚）
- `POST /api/cards/:id/clone` → clone（new id，`revision=1` 记录于 sidecar/HTTP metadata；
  当前 card schema 无 `status`/`draft` 字段，克隆产物即普通卡）
- `POST /api/cards/:id/archive` → archive（语义由 Phase 0 决定：sidecar `disabled`/`archive` 标记、
  移出 `pack.json` manifest、或不做；当前 card schema 无 `status` 字段；任何一种语义都做引用检查）
- `DELETE /api/cards/:id` → remove（引用检查 + pack manifest 同步）
- `GET /api/registries` → 各 registry（effects/conditions/tags/risks/keywords/phases/flags/supply groups/pack permissions）
- `GET /api/schema` → action-card v1/v2 schema
- `POST /api/assets/upload` → multipart binary（PNG/WebP）→ 返回 `{path, hash, mime, size}`
- `DELETE /api/assets/:path` → 删除（引用检查）
- `GET /api/assets/:path` → static serving（pack-relative, 路径安全）
- `POST /api/validate` → cards+events validate
- `POST /api/compile` → cards+events compile（deterministic, byte-identical）
- `POST /api/publish` → validate+compile+manifest+Godot reload
- `GET /api/changes` → dirty / change set
- `GET /api/diff/:id` → card diff

> **revision 说明**：现有 source **没有 revision**，需 **sidecar / revision manifest**（例如
> `content/card_packs/core/.revisions.json` 或每卡 sidecar）**或 schema 演进**（在 card 加
> `revision` 字段，但避免随便污染稳定卡牌 schema）。建议 **sidecar**。

## 9. 分阶段计划

- **Phase 0 — contract decisions**
  - 决定 revision 存放（sidecar vs schema）；决定图片格式（PNG/WebP，JPEG 开放）；
    决定 combined publish 粒度（card+event 原子 vs 分别）；决定 pack manifest 同步策略；
    决定 card archive 语义（sidecar `disabled`/`archive` 标记 vs 移出 manifest vs 不做）。
  - **验收门**：契约文档 + 安全约束 ADR。
- **Phase 1 — card CRUD without images**
  - `/api/cards` list/detail/POST/PUT/clone/archive/remove；revision 乐观并发 + 409；
    validate + 原子写 + 回滚；pack manifest 同步。
  - **验收门**：79 卡可列出 / 搜索 / 编辑 / 创建 / 克隆 / 归档；冲突 409 不覆写；无效不落盘；
    pack manifest 一致；compile twice byte-identical；卡牌门至少包括 `./tools/cards validate`、
    `./tools/cards check`、cards 单测（`tools/test_cards*.py`）与 workbench 测试
    （`workbench/test/server.test.mjs`）全部通过。
- **Phase 2 — image end-to-end + Godot render**
  - upload/delete/static + 安全约束；manifest hash 覆盖 assets；compiler 投影 presentation；
    DataLoader/ActionDef 加载 icon/accent；Godot 渲染 + fallback。
  - **验收门**：上传 / 替换 / 删除引用安全；缺图 fallback；Godot 显示卡图；旧 save/ID 不破坏；
    combined publish 验收（proposal 目标，非现状）：验证 actions.runtime / action manifest /
    content manifest 的 hash 链与 event/action reload ACK。
- **Phase 3 — parameter center**
  - 只读 registry 下拉；高级：难度 / 规则 / 场景（只读或受限编辑）。
  - **验收门**：参数中心展示；不破坏游戏。
- **Phase 4 — analysis integration**
  - 分析入口深链；分析参数独立高级页。
  - **验收门**：深链可用；边界清晰。

## 10. MVP 详细验收标准

- 能列出并搜索全部 **79** 张卡。
- 编辑 / 创建 / 克隆卡。
- 所有字段用 registry / schema 控件；Advanced JSON 可回退。
- 冲突返回 **409** 且不覆写。
- 无效内容**不落盘**或**完整回滚**。
- pack manifest 一致（`cards` 数组 sorted/unique，与文件一一对应）。
- **compile twice byte-identical**（`actions.runtime.json` + manifest）。
- publish 后 **Godot safe reload ACK**（现状仅事件；proposal 目标：ACK 返回实际 action/event
  hash/version）。
- 图片上传 / 替换 / 删除**引用安全**、**fallback**。
- 旧 save / ID **不破坏**（`legacy_ids` 保留，runtime id 稳定）。
- 卡牌门：`./tools/cards validate`、`./tools/cards check`（fresh）、cards 单测
  （`tools/test_cards*.py`）、workbench 测试（`workbench/test/server.test.mjs`）全部通过；
  事件侧 Godot `ValidateEventGraph`。
- combined publish 验收（**proposal 目标，非现状**）：验证 actions.runtime / action manifest /
  content manifest 的 hash 链与 event/action reload ACK。
- **不直接编辑 generated**（`actions.runtime.json` / manifest 只读产物）。

## 11. 风险与开放决策

- 图片规格 / 裁切 / 许可元数据。
- revision 存放（sidecar vs schema 演进）。
- card archive 语义（sidecar `disabled`/`archive` 标记 vs 移出 manifest vs 不做；当前 schema 无 `status`）。
- 是否允许 core id / `source_order` 改动（建议**锁定**）。
- atomic publish granularity（card+event 原子 vs 分别）。
- difficulty / rules externalization schema。
- auth / local-only boundary。
- React vs vanilla 是否重构（**建议 MVP 继续现有原生栈，避免前置重写**）。

## 12. Evidence map

> 标注：跨仓库数字（79 / 138 / 4 / 8 / 22 / 5 等）为 **2026-08-21 snapshot**，未来可能变化。

**本仓库（`game_analysis_agent`）**

- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`
- `tools/gameplay/run_gameplay_agent.py`
- `tools/persona/run_persona_campaign.py`
- `config/matrix*.yaml`、`config/gates.yaml`、`config/player_personas.yaml`

**sibling 仓库（`study-in-germany`）— 跨仓库 snapshot**

- `workbench/README.md`、`workbench/server.mjs`、`workbench/public/index.html`、`workbench/public/app.js`
- `content/card_packs/core/pack.json`、`content/card_packs/core/cards/*.json`（79）
- `content/schemas/action-card-v1.schema.json`、`content/schemas/action-card-v2.schema.json`
- `content/registries/{effects,conditions,tags,risks,keywords,phases,public_flags,supply,card_pack_permissions}_v1.json`
- `content/generated/actions.runtime.json`、`content/generated/action_content_manifest.json`
- `tools/cards.py`
- `autoload/DataRegistry.gd`、`autoload/WorkbenchBridge.gd`、`scripts/data/DataLoader.gd`、`scripts/data/ActionDef.gd`
- `scripts/tools/{ValidateEventGraph,ValidateEventAuthoringV2,ValidateEventScheduleAudit,CompileEventContent}.gd`
- `scenes/main/Main.gd`、`scenes/ui/ActionCard.tscn`
- `autoload/DifficultyConfig.gd`、`autoload/GameState.gd`
- `content/campaigns/germany_student_campaign.json`、`content/segments/*.json`
- `data/scenarios/{default_first_semester,high_stress_start,low_money_start,p6a_testdaf_fixtures}.json`
- `data/characters/npcs.json`、`data/endings/generated_endings.json`
- `scripts/simulation/{EconomyRules,ActionSupplyService,ActionModifierService,BurdenService,ResidenceService,ExamResolver,RouteResolver,RecoveryDiagnosticService}.gd`
- `scripts/data/{GrowthRegistry,FocusRegistry,KeywordRegistry,KeywordComboRegistry}.gd`
- `project.godot`

## 13. 可直接进入下一步设计的原始素材

- **核心用户 / 任务**：内容作者 / 游戏设计者 / 前端维护者；任务 = 编辑卡牌 / 事件 / 参数、
  上传图片、发布到 Godot、与分析联动。
- **产品原则**：内容编辑与分析分层；确定性编译；原子写 + 回滚；registry 约束；本地-only 安全；
  不破坏旧 save / ID。
- **术语表**：pack、card、event、flow、registry、manifest、runtime、revision、sidecar、
  safe reload、fallback。
- **待确认问题**：见 §11 开放决策。
- **推荐下一份产物**：PRD、API contract、image asset ADR、build checklist。
