# game_analysis_agent

面向 Godot 数值模拟游戏的开发侧 AI Agent 流水线。本项目把"试玩 / 边界 / Bug / 数值"分析自动化：
让 LLM 在压缩报告、异常检测和工具调用之上产生诊断，而不是把 LLM 塞进游戏运行时当 NPC。

```text
Godot headless simulation
  ├─ RunSimulation.gd           (Monte Carlo via study-in-germany)
  ├─ RunBoundaryProbe.gd        (extreme-scenario probing)
  ├─ ExportEventGraph.gd        (event / action / ending catalog)
  └─ RunInteractiveProbe.gd     (driven by the interactive player)
        │
        ▼
Python analysis layer
  ├─ analytics.py               (ending / weekly / pick / event / choice stats)
  ├─ anomaly_detector.py        (invariant + repeat + dead-state + spike detection)
  ├─ value_analyzer.py          (dominant / dead actions, choice bias, ending lock-in)
  └─ bug_summarizer.py          (anomaly → markdown)
        │
        ▼
LLM agent layer (provider: vllm | sglang | deepseek)
  ├─ balance                    (existing) — diagnose ending distribution + tuning
  ├─ content_qa                 (existing) — review event text + choices
  ├─ event_graph                (existing) — audit trigger graph
  ├─ bug_hunter                 (new) — review anomalies + raw runs → bug_diagnosis.md
  ├─ boundary_prober            (new) — review extreme runs → boundary_report.md
  ├─ value_reviewer             (new) — review value_report.json → value_review.md
  └─ interactive_player         (new) — drive the simulator with tool calls
```

默认 LLM 通过 vLLM OpenAI-compatible server 接入，模型目标为 Qwen3.6 NVFP4。实际仓库名
或本地路径通过环境变量配置，方便替换为你机器上已经下载好的 checkpoint。

## 快速开始

### 方式 A：Docker（推荐，vLLM + Godot sidecar）

```bash
cp .env.example .env
# 编辑 .env 填 HF_TOKEN / GAME_PROJECT_PATH 等
docker compose pull vllm
docker compose up -d vllm godot
docker compose logs -f vllm           # 等待 "Application startup complete"
docker compose ps                      # 确认 vllm / godot 都是 healthy

# 真实玩法命令从宿主机运行，wrapper 会进入 Godot sidecar
uv run python tools/run_gameplay_agent.py play \
  --report-dir reports/play/local-smoke \
  --persona newbie --weeks 5 --seed 42
```

详见 [docs/DOCKER.md](docs/DOCKER.md)。该方式会在本地启动一个
vLLM v0.25.0 容器（默认服务 NVIDIA 官方 Qwen3.6 27B NVFP4 + MTP
投机解码）以及一个常驻 Godot 工具容器。可选的 `agent` 容器只用于已有
报告的纯 Python 分析/QA，不负责进入 Godot sidecar 执行游戏进程。

### 方式 B：本地 Python + 已有 vLLM endpoint

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 安装依赖（推荐使用 `uv` / `pip` + virtualenv）：

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 不需要 Godot 或 LLM 的确定性检查
uv run pytest -q -ra
uv run ruff check .
```

3. 启动本地 vLLM 服务（如果你用的是 `deepseek` 则可跳过）：

```bash
MODEL_ID=/path/to/qwen3.6-nvfp4 ./tools/run_vllm_qwen.sh
```

4. 一键跑通整个流水线（模拟/分析 → 导出 → 全验证 → LLM QA → 质量门禁）：

```bash
python3 tools/run_gameplay_agent.py all --runs 20 --policy balanced
```

   这条命令会输出到：

   ```text
   reports/balance/<run_id>/raw_runs.jsonl
   reports/balance/<run_id>/summary.json
   reports/balance/<run_id>/ending_distribution.csv
   reports/balance/<run_id>/weekly_stats.csv
   reports/balance/<run_id>/action_pick_rates.csv
   reports/balance/<run_id>/event_trigger_rates.csv
   reports/balance/<run_id>/choice_pick_rates.csv
   reports/balance/<run_id>/anomalies.jsonl
   reports/balance/<run_id>/bugs.jsonl
   reports/balance/<run_id>/bugs_summary.md
   reports/balance/<run_id>/value_report.json
   reports/balance/<run_id>/route_report.json
   reports/balance/<run_id>/coverage_report.json
   reports/balance/<run_id>/validation_summary.json
   reports/balance/<run_id>/gate_report.json
   reports/balance/<run_id>/agent_diagnosis.md
   reports/balance/<run_id>/tuning_proposal.md
   reports/balance/<run_id>/content_issues.md
   reports/balance/<run_id>/event_graph_report.md
   reports/balance/<run_id>/bug_diagnosis.md
   reports/balance/<run_id>/value_review.md
   reports/balance/<run_id>/report_manifest.json
   ```

5. 单独运行其它子命令：

```bash
# 仅模拟 + 分析（不调 LLM）
python3 tools/run_gameplay_agent.py sim --runs 100 --policy random
python3 tools/run_gameplay_agent.py analyze --report-dir reports/balance/baseline

# 边界探测（需要 Godot + GAME_PROJECT_PATH 指向 study-in-germany）
python3 tools/run_gameplay_agent.py probe --extreme "zero_money,deep_debt,flag_chaos"

# 默认运行 content / json-content / economy / risk / route / demo 六个验证器。
# route/demo 的前置输入默认重新生成；仅在明确需要时传 --reuse-inputs。
python3 tools/run_gameplay_agent.py validate \
  --report-dir reports/validation/<run_id>

# 执行确定性质量门禁
python3 tools/run_gameplay_agent.py gates \
  --report-dir reports/balance/<run_id>

# 让 LLM 当玩家试玩
python3 tools/run_gameplay_agent.py play --report-dir reports/play/test --weeks 20

# 离线评估已经记录的试玩，不调用 Godot 或 LLM
python3 tools/run_gameplay_agent.py eval --report-dir reports/play/test

# 不调用 LLM，直接捕获游戏原生 RiskEvaluator 风险建议；缺失时失败
python3 tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/test

# 先严格校验并枚举全部 140 个单元
python3 tools/run_gameplay_agent.py matrix --dry-run --jobs 4

# before/after 各自拥有隔离的 cell 报告目录，不会互相覆盖
python3 tools/run_gameplay_agent.py matrix \
  --out reports/matrix/before --jobs 4
# 应用待验证的代码改动，但保持 config/matrix.yaml 不变
python3 tools/run_gameplay_agent.py matrix \
  --out reports/matrix/after --jobs 4
# 中断后在同一个 --out 上续跑
python3 tools/run_gameplay_agent.py matrix \
  --out reports/matrix/after --jobs 4 --resume
python3 tools/run_gameplay_agent.py compare-matrix \
  --before reports/matrix/before --after reports/matrix/after \
  --out reports/compare/matrix

# 仅跑某个 agent（如果只想看一份诊断）
python3 tools/run_agent.py balance reports/balance/baseline

# Build an editorial-style HTML dashboard over all reports/
python3 tools/build_dashboard.py all
# → reports/index.html + reports/browse/<kind>/<id>/index.html
# → reports/browse/decision_graph/<run>/<id>/index.html  (full decision graph
#   with every game event plotted across three lanes; agent's path glowing)
# → reports/manifest.json + reports/browse/<kind>/<id>/manifest.json
#   (data feed for the React frontend below)

# Render the decision graph for one specific run on demand:
python3 tools/build_dashboard.py decision-graph \
  --report-dir reports/balance/<run>/ --run-id 0

# React + React Flow frontend (alternative to the static HTML):
cd frontend && npm ci
npm test
npm run test:coverage
npm run dev          # http://localhost:5173
npm run build        # → frontend/dist/   (static SPA, ready to serve)
# Mirror the manifest into the Vite project for development:
python3 tools/build_dashboard.py emit-frontend-manifest \
  --reports reports --frontend-public frontend/public
```

默认的 `config/matrix.yaml` 会展开为 140 个稳定单元：126 个模拟单元
（难度 × 策略 × 场景 × seed）、8 个边界单元和 6 个 persona 试玩单元。
矩阵 YAML 使用严格 schema，未知或非法字段会在执行前失败；状态会原子写入
`matrix_manifest.json`、`matrix_summary.json` 和每个单元的
`cell_manifest.json`。矩阵和单元都记录精确的运行源码 SHA-256；源码变化后
`--resume` 会重新执行旧成功单元。`compare-matrix` 仅接受完整、非 dry-run
且 config hash、cell 集合、参数、命令、seed 和 cell manifest 相匹配的两次
执行，并独立重验 CSV schema、coverage/catalog 一致性、模拟/边界契约、报告源码
指纹及重新计算的 persona 评估。产物内容允许变化，变化会写入
`matrix_compare_summary.json` 和逐模拟单元的结构化 diff。
每次矩阵的实际 report 目录都隔离在对应 `--out` 下，因此不需要复制旧报告或
使用不同 worktree。

## 可追溯报告

每个报告目录都会写 `trace-manifest-v2` 格式的
`report_manifest.json`。除报告级 `run_id`、命令参数、源文件/生成文件、
SHA-256、修改时间和 JSONL 行号索引外，`provenance` 还记录：

- Agent 与游戏仓库的 Git commit 和 dirty 状态；
- Python、平台、Godot 版本或可用性；
- `config/` 与 `prompts/` 的内容哈希。
- 可区分不同 dirty worktree 的运行源码 SHA-256。

前端列表读取 `reports/report_index.json`，再打开每份报告的 manifest
下钻。交互试玩还会写 `playthrough_agent_report.json`（完整 LLM 调用审计）
和 `agent_eval.json`；后者统计首轮/最终合法率、回退与修复率、非法动作、
事件选择、异常、风险确认、persona 对齐以及 LLM 错误/延迟。

## 测试系统

宿主机没有 `godot4` 时，优先使用仓库内的 Docker wrapper。它会保持宿主机与
容器中的绝对路径一致，并使用当前 UID/GID，避免生成 root 所有的报告：

```bash
export GAME_PROJECT_PATH=/home/bo/projects/python/study-in-germany
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"
docker compose up -d godot vllm
"$GODOT_BIN" --version

uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/docker-smoke
```

wrapper 会优先复用 compose 中常驻的 `godot` 服务；服务未启动时退回一次性
容器。默认镜像是本机已缓存的 `barichello/godot-ci:4.4`；可通过
`GODOT_DOCKER_IMAGE` 覆盖。挂载约定和 CI 完整性要求见 [AGENTS.md](AGENTS.md)。

### 使用本地 LLM Agent 做真实测试

最直接的端到端测试是让本地 LLM 选择行动，同时由真实 Godot 项目推进游戏。
先做不调用 LLM 的游戏契约预检，便于区分 Godot 和模型问题：

```bash
docker compose up -d vllm godot
docker compose ps

uv run python tools/run_gameplay_agent.py interactive-probe \
  --report-dir reports/interactive/local-smoke
```

然后运行 5 周 smoke test，并独立重验录制证据：

```bash
uv run python tools/run_gameplay_agent.py play \
  --report-dir reports/play/local-newbie-smoke \
  --persona newbie \
  --difficulty normal \
  --scenario default_first_semester \
  --seed 42 \
  --weeks 5

uv run python tools/run_gameplay_agent.py eval \
  --report-dir reports/play/local-newbie-smoke

uv run python -m json.tool \
  reports/play/local-newbie-smoke/agent_eval.json
```

正式测试把 `--weeks` 改成 `20`。可用 persona 为 `newbie`、`study`、
`money`、`social`、`visa` 和 `slacker`。合格结果至少应满足：

- `valid: true` 且 `errors` 为空；
- `final_valid_rate >= 0.95`；
- `fallback_rate <= 0.05`；
- `illegal_action_rate == 0`；
- `llm_error_rate <= 0.05`；
- `anomaly_rate_per_5_weeks <= 1`。

`persona_alignment_rate` 和 `risk_acknowledgement_rate` 分别反映角色策略
一致性以及模型是否理解游戏原生风险提示，也应人工对比不同 persona。

若要让六个 LLM 审查 Agent 分析新生成的真实游戏数据，可把所有证据写入同一个
报告目录：

```bash
REPORT=reports/balance/local-real-42

uv run python tools/run_gameplay_agent.py sim \
  --report-dir "$REPORT" --runs 200 --weeks 20 \
  --policy balanced --difficulty normal --seed 42
uv run python tools/run_gameplay_agent.py export --report-dir "$REPORT"
uv run python tools/run_gameplay_agent.py probe \
  --report-dir "$REPORT" --runs 30 --weeks 20 \
  --policy balanced --seed 42 \
  --extreme "zero_money,deep_debt,no_energy,flag_chaos"
uv run python tools/run_gameplay_agent.py qa --report-dir "$REPORT"
uv run python tools/run_gameplay_agent.py gates --report-dir "$REPORT"
```

`play` 会生成 `playthrough.jsonl`、`playthrough_summary.md`、
`playthrough_agent_report.json`、`agent_eval.json` 和
`report_manifest.json`。虽然 `play` 已自动生成评估，仍建议再运行一次
`eval`：录制证据无效时，独立命令会返回非零退出码。当前游戏 demo 有 3 个
已知平衡失败，所以一体化 `all` 可能在 validator 阶段正确停止、尚未进入
LLM QA；上面的分步流程可以分别检查每个阶段。

本地确定性检查：

```bash
uv sync --extra dev --locked
uv run pytest -q -ra
uv run ruff check .

cd frontend
npm ci
npm test
npm run test:coverage
npm run build
```

Pull Request 和 `main` 分支 push 会执行完整 Python 测试、全仓 Ruff、
140 单元矩阵 dry-run、带覆盖率门槛的前端 Vitest 和公开站点生产构建。
定时或手动的 real-Godot job 会：

1. 使用 secret 检出固定 commit 的私有 `study-in-germany`；
2. 下载官方 Godot 包并验证 SHA-512；
3. 生成并分析新鲜 trace，导出 catalog，运行全部六个 validator；
4. 执行确定性 smoke gates；
5. 捕获游戏原生交互风险建议，验证六类跨仓库数据契约并上传 Agent/游戏证据。

详见 [游戏产物契约测试](docs/GAME_CONTRACT_TESTING.md)。

## 目录结构

```text
config/
  agent_profiles.yaml           — agent 配置（system_prompt / user_prompt / output_files / temperature）
  gates.yaml                    — 可执行、失败关闭的质量门禁
  matrix.yaml                   — 可执行、严格、可恢复的测试矩阵
  player_personas.yaml          — 交互试玩 persona

docs/
  ARCHITECTURE.md
  DATA_CONTRACTS.md
  GAMEPLAY_AGENT.md             — 新 agent 类型说明
  GODOT_INTEGRATION.md
  INTEGRATION_WITH_STUDY_IN_GERMANY.md
  PROJECT_PLAN.md
  VLLM_QWEN_LOCAL_AGENT.md

prompts/
  balance_agent_{system,user}.md
  bug_hunter_{system,user}.md
  boundary_prober_{system,user}.md
  content_qa_agent_{system,user}.md
  event_graph_agent_{system,user}.md
  player_{system,user}.md
  value_reviewer_{system,user}.md

scripts/tools/
  RunBalanceSim.gd              — deprecated stub; 真实跑局见 study-in-germany/RunSimulation.gd
  AnomalyCollector.gd           — 镜像 Python 不变量检测，给 boundary_runs 附带轻量标记

src/game_analysis_agent/
  __init__.py
  agent_eval.py                 — 录制试玩的确定性质量评估
  env.py                        — .env loader
  settings.py                   — Settings dataclass + get_settings()
  schemas.py                    — Pydantic LLMCall / Anomaly / Finding
  contracts.py                  — 跨仓库产物契约
  llm_client.py                 — OpenAI-compatible client with provider switching + audit
  tool_loop.py                  — OpenAI-compatible tool-calling loop
  analytics.py                  — 纯统计函数
  coverage.py                   — 状态/事件/动作/转移覆盖率
  anomaly_detector.py           — 不变量 / 重复 / 死局 / 突变检测
  value_analyzer.py             — 必选 / 死选 / 偏向 / 终局单一化检测
  bug_summarizer.py             — anomalies → Markdown
  game_tools.py                 — OpenAI tools + Godot subprocess wrappers
  quality_gates.py              — 严格、失败关闭的门禁执行器
  test_matrix.py                — 140 单元矩阵计划、并发与恢复
  agents/
    base.py                     — Agent 抽象基类
    balance.py
    content_qa.py
    event_graph.py
    bug_hunter.py
    boundary_prober.py
    value_reviewer.py
    interactive_player.py

tests/                          — 单元测试 + fixture
tools/
  analyze_balance.py            — CLI 入口，拆出业务逻辑到 analytics.py
  compare_matrix.py             — 固定 seed 的严格矩阵 before/after 对比
  generate_agent_prompt.py
  run_agent.py                  — 单个 agent CLI
  run_balance_sim.sh            — 包装 study-in-germany 的 RunSimulation.gd
  run_gameplay_agent.py         — 一站式 orchestration CLI
  run_vllm_qwen.sh
```

## 项目文档

- [完整项目规划](docs/PROJECT_PLAN.md)
- [系统架构](docs/ARCHITECTURE.md)
- [新 agent 类型说明](docs/GAMEPLAY_AGENT.md)
- [与 study-in-germany 的集成约定](docs/INTEGRATION_WITH_STUDY_IN_GERMANY.md)
- [Docker 部署](docs/DOCKER.md)
- [Godot 接入规范](docs/GODOT_INTEGRATION.md)
- [本地 vLLM + Qwen 接入](docs/VLLM_QWEN_LOCAL_AGENT.md)
- [数据与报告规范](docs/DATA_CONTRACTS.md)
- [本地 LLM 游戏系统真实测试报告（2026-07-13）](docs/LOCAL_LLM_GAME_SYSTEM_AUDIT_20260713.md)
- [Service-first MCP 迁移计划](docs/MCP_MIGRATION_PLAN.md)

## 当前状态

- ✅ Settings + 三 provider 切换（vllm / sglang / deepseek）
- ✅ Pydantic 审计 + 不变量 / 重复 / 死局 / 突变检测
- ✅ 7 个 agent（balance, content_qa, event_graph, bug_hunter, boundary_prober,
  value_reviewer, interactive_player）
- ✅ Tool-calling loop（OpenAI 兼容 + JSON fallback helper）
- ✅ 3 个新 Godot 工具（RunBoundaryProbe / ExportEventGraph / RunInteractiveProbe）
- ✅ `all` 串联 export、六个 validator、可选 LLM QA 和质量门禁
- ✅ 严格、可并发、可恢复的 140 单元测试矩阵
- ✅ 隔离 report 目录、严格配对的固定 seed `compare-matrix`
- ✅ Godot `RiskEvaluator` 原生 top-risks 契约、严格校验和可审计 fallback
- ✅ `agent_eval.json`、coverage v2、统计置信区间和 provenance manifest
- ✅ pytest + Ruff + Vitest + 前端生产构建的 CI
- ✅ 六类跨仓库产物契约及 real-Godot 定时/手动 smoke job

在另一台环境复现完整流水线，需要：

1. 一台能跑 Godot 4 的机器（`godot4 --headless`）。
2. 一份 `study-in-germany` checkout（GAME_PROJECT_PATH）。
3. 若要运行 fresh persona 单元，还需 vLLM / SGLang / DeepSeek 任意一个 endpoint。

缺任何一个，Python 侧仍然能跑：analytics / anomaly_detector / value_analyzer / tests
全部基于本地 fixture 自测，前端也可以基于公开样例运行测试和构建。

## 当前环境限制

本机已用 SHA-512 校验的官方 Godot 4.7-dev5 完成真实模拟、边界、catalog、
五个干净 validator、交互 RiskEvaluator 契约及 Agent 关键门禁验证。游戏自身的
`demo` validator 仍如实报告 3 个平衡失败（动作集中度 2 项、结局多样性 1 项），
因此完整 `all` 正确返回非零；这不是测试系统跳过或伪造通过。当前没有真实 LLM
endpoint，所以 fresh persona 矩阵仍需外部服务。私有仓库 CI 还必须配置具有只读
权限的 `STUDY_IN_GERMANY_TOKEN`。
