---
status: implemented-passed-with-release-data-gate
date: 2026-07-17
reviewed_document: PRODUCT_UI_SYSTEM.md
review_perspectives: product, frontend, UI/UX, competition judge
---

# Playtest Forge 产品界面系统 V2 — 设计审核

## 审核结论

设计规范可以进入实现。它解决了当前最明显的产品断层：两个核心页与四类
辅助页不再被当成不同产品；每个路由都有明确任务、证据边界、首屏信息和
交互要求。

审核不批准“只换深色背景”的实现。通过门槛包括共享 shell、首屏重排、
Graph transport 语义修复、统一系统状态和真实浏览器 QA。

## 1. 产品设计师审核

**通过。** 页面链路与游戏开发者任务一致：发现问题、检查 playthrough、
理解 graph、核验证据、浏览其它任务。没有新增无价值营销页，也没有删除
Archive/Dossier 的深度功能。

实施门禁：每个页面必须有一个清楚的主任务；Archive 不能重新变成品牌
首页，Dossier 不能只是长报告换颜色。

## 2. 前端设计师审核

**通过。** 规范给出了共享 token、组件边界、兼容旧变量的迁移策略和可测试
的 Definition of Done。先抽 shell 再迁移页面，可以避免继续叠加
`.judge-*` 特例。

实施门禁：

- 不全局翻转 `:root` 造成 Judge/Inspector 回归；辅助页通过
  `.forge-workspace` 兼容映射逐步迁移；
- 不修改 manifest schema、Gate、graph 计算或 playthrough evidence；
- 不用 inline style 继续扩展新设计；新视觉写入集中 stylesheet；
- timeline 从 `div onClick` 改为 button，transport 使用 Phosphor icon。

## 3. UI/UX 审核

**通过。** 颜色语义与核心页一致，并且所有关键状态都有文字编码。布局将
数据和操作移到首屏，保留宽图和表格的内部滚动，符合 developer tool 的
密度。

实施门禁：

- 390 px 不允许 root 横向滚动；
- focus、hover、selected、disabled、loading、error、empty 必须可见；
- Graph 当前 week、selected node、详情必须同步；
- Archive empty state 必须有 Clear filters，而不只是空白文案。

## 4. 比赛评审核

**通过。** 新链路强化两个比赛记忆点：六种策略实际收敛、系统拒绝自己的
patch。Decision Graph Lab 成为技术深挖，而不是脱离主页面的示例报告。

实施门禁：illustrative graph 必须继续明确标记。视觉迁移不能把 sample
冒充真实 Replay；只有 Inspector 的 committed playthrough 可以使用
`prerecorded-real-godot-replay`。

## 5. 与当前实现的差距

| Finding | Severity | Required fix |
| --- | --- | --- |
| Archive/Dossier/Graph/404 使用 cream editorial theme | P1 | 全部进入 ForgeWorkspace |
| Archive 首屏看不到 card | P1 | 缩短 header，把 filters 与结果带入首屏 |
| Dossier 首屏大面积空白，Gate 层级弱 | P1 | compact header + metric strip + gate disposition |
| Graph 首屏主要是 cover，工具本体在下方 | P1 | canvas 和 transport 上移 |
| Graph timeline 是 clickable div | P1 accessibility | 使用 button 与 aria-current |
| Reset/Play 使用 Unicode 符号 | P2 | 使用 Phosphor icon + text |
| Loading/error/404 是零散 inline styles | P2 | ForgeStatePanel |
| 全局 footer 名称仍是 Analytical Review | P2 | 统一 Mission Archive 与 Forge shell |

## 6. 审核后的修订

审核时对初稿做了四项约束性修订：

1. 明确 `.forge-workspace` 兼容迁移，避免全局 token 翻转伤害核心页；
2. 明确 illustrative graph truth label，防止比赛叙事越界；
3. 把 system states 纳入 P0/P1 交付，而不是赛后 polish；
4. 把 Archive empty-state recovery 与 Graph keyboard semantics 写入 DoD。

## 7. 实施授权

设计文档审核通过，可以实现。若实现中需要改变数据含义、增加新路由、
移除现有功能或新增图像资产，必须停止并重新审核；纯组件拆分、样式迁移、
可访问性修复和现有交互重排在本规范授权范围内。

## 8. 实施后复审

**视觉与交互实现通过。** `Mission Archive`、`Evidence Dossier`、
`Decision Graph`、loading/error/empty/404 已进入统一 `ForgeWorkspace`。
桌面首屏现在能直接看到 Archive 过滤与结果、Dossier Gate 与 trace、Graph
transport 与 canvas；Graph week 使用 button + `aria-current`，并补齐
Previous/Next、Reset、Play/Pause、slider label 与 Phosphor icon。

实现证据位于 `audit-after/`。浏览器复审同时验证了 Archive search → empty →
Clear filters recovery、Graph Next → current week 同步，以及干净标签页 0 error / 0
warning。`npm run build` 与 18 项前端测试通过；offline inspect/replay 与
Build Week preflight 通过。

### 仍开放的比赛发布数据门禁

| Finding | Severity | Decision |
| --- | --- | --- |
| Archive/Dossier/Graph 的 tracked public bundle 仍是 aggregate/sanitized；与“比赛可展示实际数据”的最新决定不一致 | P1 release | 当前实现继续如实显示 public/illustrative 标签，不伪装为 Replay；发布前应把这些路由切到 committed Build Week campaign/playthrough evidence，再重新跑 truth-label QA |

该门禁不否定本次视觉迁移，但在比赛发布检查中必须单独关闭。真正的 Replay
证据仍只在 Judge Mission 与 Playthrough Inspector 使用
`prerecorded-real-godot-replay` 标签。
