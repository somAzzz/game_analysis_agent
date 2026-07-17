---
status: implemented-with-release-data-gate
date: 2026-07-17
branch: OpenAI-build-week-2026
scope: all evaluator-facing frontend routes
visual_source:
  - audit-before/01-judge-mission.png
  - audit-before/02-playthrough-inspector.png
---

# Playtest Forge 产品界面系统 V2

> 2026-07-17 实施状态：视觉系统、共享 shell、辅助页层级、Graph transport、
> empty/error/404 状态和可访问性交互已经落地并通过实现 QA。比赛发布前仍有
> 一个独立数据门禁：Archive/Dossier/Graph 当前读取的 committed
> `frontend/public-demo` 仍是明确标注的 aggregate/sanitized bundle；不能把它
> 改名为 actual Replay。Judge Mission 与 Playthrough Inspector 已使用真实的
> prerecorded Godot Replay 证据。

## 1. 产品目标

Playtest Forge 是为游戏开发者服务的可审计自动化 playtest 与 bounded
repair 工具。比赛界面必须同时证明三件事：

1. agent 确实在真实游戏状态中做出了逐步选择；
2. Codex 能把失败收敛为一个可证伪假设和有边界的修复；
3. 系统会因为 fixed/holdout 证据不足而拒绝自己的 patch。

主体验不是营销站、数据后台或电子杂志，而是 **Playable Evidence
Console**：像游戏引擎调试器一样可操作，像实验记录一样可信，像比赛
叙事一样在 90 秒内有明确高潮。

## 2. 设计基准与不可变原则

唯一视觉基准是已完成的 Judge Mission 与 Playthrough Inspector。辅助页
必须继承它们，不能再建立第三套主题。

### 2.1 设计语言

- **环境**：深色游戏测试工作台，不使用旧版米白纸张背景。
- **显示字体**：Fraunces，用于结论、页面主问题和关键事件。
- **叙事字体**：Newsreader，用于解释、假设和长文本。
- **证据字体**：IBM Plex Mono，用于事件、seed、hash、状态与操作。
- **形状**：直角、细规则线、无通用 SaaS 圆角；层级来自边界与密度。
- **图像**：只使用现有 Persona、地图与真实项目资产；不新增 emoji、
  CSS 绘图、手工 SVG 或无证据装饰。
- **动效**：只解释状态变化、路径播放、选择和打开/关闭；支持
  `prefers-reduced-motion`。

### 2.2 语义色

| Token | 建议值 | 含义 |
| --- | --- | --- |
| `--forge-bg` | `#071318` | 全局工作台背景 |
| `--forge-surface` | `#0c1e24` | 面板、卡片、工具区 |
| `--forge-surface-raised` | `#10262c` | hover、选择、展开层 |
| `--forge-ink` | `#eff4ec` | 主内容 |
| `--forge-muted` | `#91a6a3` | 次要说明 |
| `--forge-rule` | `#294249` | 分隔与结构 |
| `--forge-evidence` | `#77ddd4` | 已执行路径、选中证据、当前状态 |
| `--forge-legal` | `#f2c66d` | 合法但未执行、待检查、warning |
| `--forge-risk` | `#ff665f` | failed、rejected、attractor、terminal risk |
| `--forge-pass` | `#75c99a` | verified pass；不能单独依赖颜色 |

旧 `--paper/--ink/--accent` 只作为迁移期兼容映射，不能继续定义页面
设计。

## 3. 统一信息架构

```text
Judge Mission /
  └─ Playthrough Inspector /playthrough-inspector?persona=<slug>
       └─ Decision Graph Lab /decision-graph/:issue/:run
            └─ Evidence Dossier /issue/:kind/:id
                 └─ Mission Archive /reports
```

这不是强制逐页点击的漏斗，而是一组深度逐渐增加的问题：

1. Mission：系统发现了什么，为什么拒绝 patch？
2. Inspector：某个策略每一周实际发生了什么？
3. Graph Lab：有哪些分支，哪条路径被执行？
4. Dossier：哪些聚合、Gate、异常与 agent 分析支持结论？
5. Archive：还可以检查哪些测试任务？

## 4. 全局应用壳

所有路由共享 `ForgeWorkspace`：

- 左：`PLAYTEST / FORGE`，始终返回 Judge Mission；
- 中：Judge Mission、Playthrough Inspector、Mission Archive；
- 右：当前 truth label 或页面证据类型；
- 当前路由使用 evidence 色背景和 `aria-current="page"`；
- 子页面在正文内使用单一 breadcrumb，不重复第二套导航；
- footer 与 header 使用相同深色 token，不因页面切换改变主题。

全局状态使用统一 `ForgeStatePanel`：loading、empty、not found、API error、
graph unavailable。每个状态必须说明发生了什么和下一步可执行动作。

## 5. 页面功能与交互规范

### 5.1 Judge Mission `/`

**页面任务**：90 秒内建立主张、展示不同 Persona 的异常收敛，并证明
rejected decision 由证据而不是文案决定。

**保留**：当前 Hero、6 Persona squad、真实 campaign 数字、Repair、Proof、
rejected verdict、signed replay CTA。

**交互**：Persona hover/focus 摘要；click 打开 detail；CTA 进入对应 seed 42
Inspector；drawer 有 focus trap、Escape、focus restoration。

**审核重点**：仍然是全产品视觉基准，不因共享壳抽取发生视觉回归。

### 5.2 Playthrough Inspector `/playthrough-inspector`

**页面任务**：逐周检查某个 Persona 的实际路径、当前状态、选择、delta 和
证据 hash。

**保留**：六策略切换、实际 19-node 路径、人物 runner、Previous/Play/Next、
W1/W3/W19 跳转、键盘、状态 HUD、week record、evidence console。

**交互约束**：

- Persona 切换必须同步 runner、节点、选择、状态、console 和 URL；
- runner hover/focus 只显示当前 `state_after`，delta 留在详细卡；
- 未执行选择始终标为 legal here / not executed；
- truth label 在播放、暂停和切 Persona 时保持可见。

### 5.3 Decision Graph Lab `/decision-graph/:runId/:runIndex?`

**页面任务**：查看事件图的实际/示例路径、合法分支、当前 week、选择和
effects；它是 Inspector 的结构性深挖工具，而不是另一篇报告。

**首屏结构**：

```text
ForgeWorkspace
Compact evidence header: issue / run / seed / policy / ending / truth
Legend + graph canvas
Previous | Play/Pause | Next | week slider | current week
Current event detail | Selected choice / branch effects
```

**设计变化**：

- 删除旧版超大 cream cover 和访问时间；首屏直接进入图；
- executed/current path 使用 evidence cyan；legal branches 使用 amber；
  terminal/risk 使用 coral；
- selected node、current week 和详情面板使用同一 selection 状态；
- React Flow canvas 使用深色网格与深色 minimap；
- timeline cell 必须是 button，支持 Tab/Enter/Space；
- Reset、Play/Pause、Previous、Next 使用 Phosphor icon 加可见文本，不使用
  Unicode 符号；slider 有 label 和当前值；
- standalone 页面提供返回 Evidence Dossier；embedded 模式不重复 header。

**证据边界**：当前 `public-demo` graph 仍必须标为 illustrative。不得因为
视觉迁移把示例图称为实际 replay；接入真实 graph builder 后再升级 truth
label。

### 5.4 Evidence Dossier `/issue/:kind/:id`

**页面任务**：把一个失败或异常的 Gate、聚合证据、Graph、趋势、异常和
agent 分析组织成可审计调查记录。

**首屏结构**：

```text
ForgeWorkspace
Back to Mission Archive
Issue name + kind/scenario/policy/difficulty
Gate disposition
Runs | anomalies | findings | agent outputs | truth
Sticky section navigation
Traceability + primary findings
```

**交互**：

- anchor rail 保持 Findings / Graph / Pulse / Value / Anomalies / Agent / Trace；
- 当前 section 可通过 URL hash 访问；
- Graph 作为独立 investigation module，提供打开 Graph Lab 的明确 CTA；
- 表格保持真实排序与数据，不用装饰性图表替换；
- Gate pass/fail 同时使用图标、文本和颜色；
- 错误状态返回 Archive，不返回 Judge 首页。

### 5.5 Mission Archive `/reports`

**页面任务**：让开发者在首屏筛选并打开一个需要调查的测试任务。

**首屏结构**：

```text
ForgeWorkspace
Mission Archive + compact evidence summary
Runs | anomaly observations | critical cards | graphs
Search + kind + severity + sort
Visible result count
Campaign/report cards
```

**设计变化**：

- 删除旧版 “The Analysis Console” cream editorial cover；
- cards 首屏可见；featured graph card 使用 cyan，不使用 ribbon 装饰；
- critical 使用 risk coral；warning 使用 legal amber；
- filters 保持真实、即时、键盘可操作；
- zero results 使用统一 empty state，并提供 Clear filters；
- `public_demo` 或 sanitized 内容继续显示真实 truth label，不做模糊营销。

### 5.6 Not Found 与系统状态

**页面任务**：清楚说明目标不可用，并把用户带回最近的有效工作流。

- 404：`Route not found`，操作为 Judge Mission 与 Mission Archive；
- Archive load error：显示 manifest URL/简化原因与 Retry；
- Dossier/Graph not found：返回 Archive/Dossier；
- Loading：使用文字状态和 `aria-live`，不只依赖 skeleton；
- Empty：说明过滤器没有匹配并提供 Clear filters。

## 6. 交互与可访问性基线

- 所有可点击对象必须是 `button`、`a`、表单元素或有等价键盘语义；
- focus-visible 使用 3px amber outline，深色背景下保持可辨；
- icon 必须来自现有 Phosphor library，并有文本或 accessible name；
- 触控目标至少 40×40；密集 timeline 允许内部水平滚动；
- 页面切换滚动到顶部，anchor 跳转保留目标 heading；
- 动画不影响读取，reduced motion 下直接切状态；
- 颜色不是唯一状态编码；
- Desktop 1280/1536、tablet 1024、mobile 390 均不得产生 root overflow；
- graph canvas 和宽表格可使用明确的内部滚动。

## 7. 内容与证据规则

- event ID、choice ID、seed、hash、provider、source line 不翻译、不改写；
- 真实数据、Replay、illustrative sample、live provider 必须分别标记；
- 页面迁移不能改变 manifest、decision graph 计算、playthrough cell 或 Gate；
- 当前轮次不实施事件中英翻译；
- 不删除现有功能来换取视觉整洁；信息应重排、折叠或建立层级。

## 8. 实施顺序

1. 新建 `ForgeWorkspace`、`ForgeTopNav`、`ForgeStatePanel` 与 token 映射；
2. 迁移 Decision Graph Lab，并修正 timeline/transport 语义；
3. 迁移 Evidence Dossier，接入 shared shell 和 Graph Lab；
4. 迁移 Mission Archive，保留并强化筛选；
5. 迁移 not-found/loading/error/empty/footer；
6. 回归 Judge Mission 与 Playthrough Inspector；
7. browser QA、mobile QA、console、tests、production build。

## 9. Definition of Done

- 六个路由在第一屏看起来属于同一产品；
- Judge/Inspector 与现有截图无 P1/P2 视觉回归；
- Archive 首屏可见筛选器与至少一个 card；
- Dossier 首屏可见 Gate、关键 metric 与 section rail；
- Graph 首屏可见 canvas、legend、当前状态和 transport；
- 所有原有核心交互继续工作；
- loading/error/empty/404 使用共享状态组件；
- browser console 无 error/warning；
- frontend tests、production build、`git diff --check` 通过；
- `frontend/design-qa.md` 最终结果为 `passed`。
