---
status: implemented-design-qa-passed
date: 2026-07-17
branch: OpenAI-build-week-2026
scope: actual playthrough evidence, persona presentation, route generation
selected_visual_direction: Tactical Forge Mission Map (option 1)
---

# Playthrough 实际证据与前端准入计划

## 0. 产品决定

- Judge Mission 与 Playthrough Inspector 延续 **Tactical Forge Mission Map** 方向。
- 移除 Q 版 Codex/机器人角色。路径上的 runner 始终是当前选中的 Q 版 Persona。
- 六个 Q 版小人分别代表 `newbie`、`study`、`money`、`social`、`visa`、`slacker` 六种策略，不是装饰角色。
- Hover 显示策略摘要；Click 打开策略详情、三个 seed 的测试表现与真实路径入口。
- Playthrough 的节点、边、状态变化、事件、行动和选项必须来自实际测试结果；不得用 `_mock_decision_graph()` 或设计师手绘路径进入正式前端。
- `PF-00`–`PF-05` 的数据证据门槛已经通过；Option 1 已于 2026-07-17 经 Review Lab 确认，并完成正式前端实现与设计 QA。

## 1. 当前是否已经有实际测试结果

结论：**现在已有 fresh real-Godot 4.4 + hash-pinned Replay 的完整 18-cell 实际测试结果，原始逐步 engine trace、派生路径 view 和防篡改 manifest 均已保留。**

本轮在 detached clean worktree `c96f2ed3595162a174e680b563337f6215f6eace` 中执行，使用仓库校验安装器下载并 SHA-512 验证的官方 Godot `4.4.stable.official.4c311cbee`。新 campaign 为 `playthrough-evidence-full-v1`，未覆盖既有 `campaign-v1` 或 repair evidence。

### 1.1 已存在且通过验证的证据

| 证据 | 当前事实 | 能支持的 UI |
| --- | --- | --- |
| `./judge --mode inspect --offline` | 123 个 artifact hash/schema 和 6 条公开 claim 通过 | Judge Mission 的 verified truth 与 provenance |
| `./judge --mode replay --offline` | 684 条 Replay entry；6 Persona；3 seeds；18 target members | `prerecorded` Persona 行为路径与选择序列 |
| `persona_runs.jsonl` | 342 条周级记录；每 cell 19 周；含 money、stress、ending、row hash | 周节点、money/stress 趋势、attractor entry |
| full Replay fixture | 342 decision + 342 event-choice entry；含 action IDs、event ID、choice ID、entry fingerprint | 实际采取的行动和事件选项 |
| `campaign_summary.json` / `failure_clusters.json` | 18/18 进入 cashflow/stress attractor；含首次进入周、cell、line 和 record hash | Persona 收敛图与 failure-zone 标记 |
| `config/player_personas.yaml` | Persona 描述、优先级、风险容忍、探索度、failure intent | Persona hover/click 的静态策略契约 |
| `demo/study-in-germany/data/` | 实际事件、行动、选项和 ending 文案/参数 | ID 到真实游戏内容的显示关联 |
| fresh `playthrough-evidence-full-v1` | 18/18 complete；342 raw weeks；0 partial；0 fallback；0 provider error | 完整 actual path、状态前后、delta、合法行动/选项、结局 |
| `examples/build_week_2026/playthrough-v1/manifest.json` | 18 cells；342 nodes；324 actual edges；1,336 legal event choices；全部 hash/check 通过 | Playthrough Inspector 的唯一数据入口 |

这批证据来自实际 real-Godot campaign 的公开投影和 hash-pinned Replay，而不是 fresh live OpenAI run。UI truth label 必须持续显示 `PRERECORDED REPLAY`。

### 1.2 已证实的 representative path 片段

`money · seed 42` 可以作为首个 Inspector 用例：

| Week | 实际 actions | 实际 event / choice | money | stress |
| ---: | --- | --- | ---: | ---: |
| 1 | `problem_set`, `library_day`, `language_school_germany`, `language_tandem` | `arrival` / `立刻去超市和 dm 补生活用品` | 142 | 32 |
| 2 | `problem_set`, `library_day`, `language_tandem`, `write_email_practice` | `germany_language_track_start` / `找便宜语言学校` | 0 | 49 |
| 3 | `problem_set`, `library_day`, `language_tandem`, `write_email_practice` | `missing_school_registration` / `先找 International Office` | 0 | 82 |
| 4 | `problem_set`, `library_day`, `language_tandem`, `write_email_practice` | `wg_interview` / `表现得非常德式` | 0 | 100 |

该 cell 在 week 3 首次进入 `cashflow-stress-attractor`，其公开 row hash 为 `c9570ea6b2fe09cb438a15769d060e07d68395a60b842493af84d3e46d8d5884`。

## 2. 已解决缺口与仍需保持的边界

上一轮审计发现原始 `reports/.../playthrough.jsonl` 未保留。本轮已经用 fresh real-Godot campaign 重新生成并放入 [`examples/build_week_2026/playthrough-v1/`](../../../../examples/build_week_2026/playthrough-v1/README.md)，因此现在可以真实显示：

- 19 个顺序 week 节点；
- 每周 selected actions；
- 每周 event 与 selected choice；
- 每周完整 `state_before` / `state_after`、UI delta 和 full numeric delta；
- 当周全部 `available_action_ids` 与合法 event choices；
- triggered content、risk guidance、anomaly 和 attractor entry；
- 实际 final ending；18/18 均为 `cashflow_collapse`；
- Persona/seed、Replay provenance、raw artifact、row/entry/content hash。

仍然不能把下列内容伪装成测试事实：

- 未实际执行的行动组合对应的未来状态；
- 未选择 event choice 的完整后续多周路线；
- 一张声称覆盖所有 counterfactual future states 的完整分支图。

因此正式 UI 使用 **actual sequential replay path + legal option stubs**：实线代表实际执行路径；虚线 stub 只代表当周真实合法但未执行的选项，并明确标注没有实测未来状态。

## 3. Persona 信息设计

### 3.1 Hover card

Hover 只展示可以直接引用的事实：

- Persona 名称和策略一句话；
- priorities；
- risk tolerance；
- exploration；
- failure intent；
- 三个 seeds 的 completed/valid 状态；
- persona alignment rate；
- 首次进入 target attractor 的 week 范围。

不要把 priority 直接写成“学习能力 90”或“社交能力 80”。当前配置描述的是策略偏好，不是角色能力值。

若希望使用雷达图，轴必须改为可计算的实际行为占比：

- Study actions %；
- Work actions %；
- Social actions %；
- Admin actions %；
- Recovery/Escape actions %。

这些实际 action-tag rate 已由 `personas.json` 从 342 周 trace 与 hash-pinned action catalog 联合生成。它们代表观察到的选择分布，不代表人的能力值，且多标签比例不要求相加为 100%。

### 3.2 Click detail

详情 Drawer/Panel 包含：

1. 策略契约：description、priorities、acceptable costs、hard avoids。
2. 三个 seed 对比：weeks、valid、alignment、first-attractor week、max stress、final money。
3. 实际选择分布：action group、event choice、risk awareness。
4. 路径入口：`Inspect seed 42/43/44`。
5. Truth：Replay/live、fixture fingerprint、game/source revision。

### 3.3 Runner

- Playthrough graph 上只显示当前 Persona 的 Q 版小人。
- Step 改变时，小人移动到对应实际节点。
- Reduced motion 下直接切换节点，不播放行走动画。
- 不再出现 Codex、机器人或额外旁白角色。

## 4. 前端前置实际测试门槛

### `PF-00` — 冻结 trace contract（passed）

Owner：DE + QA + PD

必须字段：

- campaign/cell/persona/seed/week；
- `state_before`, `state_after`, `delta`；
- available and selected action IDs；
- triggered event ID、available choices、selected choice ID；
- action/event result；
- anomaly/invariant results；
- ending 或明确的 `week_limit` stop reason；
- provider/mode/revision、row hash、Replay entry fingerprints；
- game/agent/config fingerprints。

结果：342/342 行均包含所需字段；final ending 从每个 cell 的 `playthrough_summary.md` 读取并纳入 view。

### `PF-01` — 在隔离 clean worktree 准备实际 runtime（passed）

Owner：RE + DE

```bash
uv run python tools/prepare_embedded_demo.py \
  --output reports/local-game-runtime --replace --json
export GAME_PROJECT_PATH="$PWD/reports/local-game-runtime"
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"
"$GODOT_BIN" --version
```

不要在当前包含设计文档改动的 dirty worktree 中运行 canonical campaign；runner 会 fail closed。使用独立的 clean worktree，并确认 `.playtest-forge-source.json` 与 embedded pin 匹配。

结果：使用独立 detached worktree；embedded runtime pin 通过；Docker 不可用后改用仓库 checksum installer 安装的官方 Godot 4.4，未使用本机 4.7。

### `PF-02` — 先跑 representative cell（passed）

Owner：DE

目标：`money · seed 42 · normal · default_first_semester · 20 weeks · replay`。

产物写入新目录，不覆盖既有比赛 bundle：

```text
reports/frontend-playthrough-v1/money-seed-42/
  playthrough.jsonl
  playthrough_summary.md
  report_manifest.json
```

通过条件：每周字段完整、selected ID 合法、before/after 连续、row hash 稳定、0 fallback、0 provider error、Godot execution 成功。

结果：`money · seed 42` 完成 19 周并以 `cashflow_collapse` 结束；week 3 首次进入 cashflow/stress attractor。

### `PF-03` — 跑完整 18-cell Replay campaign（passed）

Owner：DE + RE

- 6 Persona × seeds 42/43/44；
- normal / default_first_semester；
- 20-week cap；
- hash-pinned full Replay fixture；
- fresh real-Godot execution；
- 使用新的 `campaign_id`、`report_root`、bundle 和 target 路径，禁止覆盖 `examples/build_week_2026/campaign-v1` 与现有 repair evidence。

通过条件：18/18 terminal complete，342 expected weekly rows 或有解释的真实 terminal week 数，0 partial、0 fallback、0 provider error，critical invariants 为 0。

结果：18/18 completed、342 weeks、684 Replay calls、0 partial、0 fallback、18 target members；public campaign gate passed。

### `PF-04` — 生成 actual path views（passed）

Owner：DE

从 raw `playthrough.jsonl` 确定性生成：

```text
examples/build_week_2026/playthrough-v1/
  manifest.json
  personas.json
  cells/
    money-seed-42.json
    ...
```

每个 cell view 包含：

- sequential actual nodes；
- actual state-transition edges；
- legal but unselected option stubs，不生成虚假的未来状态；
- full before/after/delta；
- actual event/action/choice/result；
- target attractor entry；
- exact source references and hashes。

展示实际游戏数据，不做游戏内容脱敏；仍排除 secret、host path 和 provider 私有 trace。

结果：`tools/build_playthrough_views.py` 生成 18 个 cell view、342 个 actual node、324 条 actual edge、1,336 个 legal event choice 和六 Persona 的实测 action-tag rate。

### `PF-05` — 路径证据 gate（passed）

Owner：QA + Playtest Forge

必须自动验证：

- route node 数与 trace step 数一致；
- actual edge 连续且没有凭空节点；
- selected action/choice 属于当周合法集合；
- delta 等于 after - before；
- target entry 对应 frozen cluster rule；
- source row/entry/content hash 全部可解析；
- Persona 三个 seed 不串线；
- Replay 绝不标为 live。

结果：`uv run python tools/verify_playthrough_views.py` 通过；`tests/test_playthrough_view.py` 覆盖完整 evidence、代表性路径和 raw trace 篡改拒绝。

### `PF-06` — 前端实现准入（data passed，design approval pending）

Owner：PD + QA + RE

`PF-00`–`PF-05` 已全部通过，数据工程不再阻塞实现。Option 1 已通过 Review Lab 确认，`PI-00`、`PI-02`、`PI-03`、`PI-05`–`PI-12` 的比赛核心交互已迁移到正式前端；实现与浏览器回归记录见 `frontend/design-qa.md`。

## 5. Figma 评审边界

评审文件：
[Playtest Forge — Judge Mission + Playthrough Inspector Review v1](https://www.figma.com/design/9Gxo5Rbvo1UHyN7wMAg30d)

仓库内评审源图：

- [`concepts/option-1-actual-replay-review-v2.png`](concepts/option-1-actual-replay-review-v2.png)
- [`concepts/strategy-persona-concept-sheet.png`](concepts/strategy-persona-concept-sheet.png)

本轮 Figma 使用 option 1 作为模板，并包含：

- Judge Mission 默认态；
- Persona hover 态；
- Persona detail 态；
- Playthrough Inspector actual sequential path；
- week 3 attractor-entry selected state；
- Previous / Play / Next / scrubber；
- state/log/evidence 同步标注；
- actual path 与 legal-option stub 的证据语义注释。

Figma 中可以使用已验证的 `money · seed 42` 全 19 周数据、完整 state 和合法 event choices。未执行选项的未来状态仍不能填入虚构数值。

## 6. Definition of Ready

完整前端开工前必须满足：

- 实际 raw playthrough trace 可读且已纳入 hash manifest；
- 至少一个 representative cell 有完整路径 view；
- 六个 Persona 的静态策略契约与实际行为指标分开呈现；
- actual path 与 preview branches 数据来源明确；
- no mock graph；
- no unknown provenance；
- no prerecorded/live 混淆；
- Figma 对路径、Persona hover/detail 和 evidence console 已完成联合评审。

当前前七项均已满足；最后一项等待产品联合评审确认。
