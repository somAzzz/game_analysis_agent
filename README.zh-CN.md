# Playtest Forge

Playtest Forge 是一个由 Codex 驱动的游戏质量分析系统。它把确定性模拟、
玩家人格试玩、证据诊断和有边界的修复实验组合起来；只有固定种子与未见
holdout 证据都支持时，候选修改才会被接受。

[开发指南](docs/DEVELOPER_GUIDE.md) ·
[架构](docs/architecture/ARCHITECTURE.md) ·
[Docker 指南](docs/operations/DOCKER.md) ·
[English](README.md)

参考集成使用仓库内置的 Godot 游戏 **Study in Germany**，但核心实现采用可复用的
typed service、provider contract 和 evidence contract。

## 主要能力

- 运行 Godot 确定性模拟、边界探测、验证器和难度矩阵。
- 通过录制 Replay、本地 SGLang/vLLM 或 OpenAI-compatible provider 运行人格试玩。
- 保存 provider 身份、源码指纹、每周决策、游戏状态和失败聚类。
- 使用固定与未见 holdout 对有边界的候选修改做因果比较。
- 当修改破坏 invariant、设计失败、人格一致性或证据完整性时拒绝修改。
- 在 React dashboard 中浏览 campaign、decision、report 和 human review。

## 快速开始

```bash
uv sync --extra dev --locked
npm --prefix frontend ci

uv run pytest -q
uv run ruff check .
npm --prefix frontend run test:coverage
npm --prefix frontend run build:public
```

启动只读 dashboard：

```bash
npm --prefix frontend run prepare:public
npm --prefix frontend run dev -- --host 127.0.0.1
```

打开 `http://127.0.0.1:5173/`。如需本地 API 与可持久化的人工审阅记录：

```bash
npm --prefix frontend run build:public
uv run python tools/judge/run_judge_api.py \
  --host 127.0.0.1 --port 8080 --frontend frontend/dist
```

Provider 凭据只存在于服务端环境变量中，不会传给浏览器。

## Godot 运行时

仓库在 `demo/study-in-germany` 内置了参考游戏。主机没有 Godot 时可使用 Docker：

```bash
uv run python tools/build_week/prepare_embedded_demo.py \
  --output reports/local-game-runtime --replace --json
export GAME_PROJECT_PATH="$PWD/reports/local-game-runtime"
export GODOT_BIN="$PWD/scripts/godot-docker-wrapper"
export GODOT_DOCKER_MOUNT_ROOT="$(cd .. && pwd)"
docker compose --profile game-tools up -d godot
"$GODOT_BIN" --version
```

确定性 smoke：

```bash
uv run python tools/gameplay/run_gameplay_agent.py sim \
  --run-id smoke --runs 12 --policy balanced \
  --difficulty normal --seed 4242 \
  --scenario default_first_semester --weeks 20
```

## 本地 SGLang

默认本地 profile 使用 Qwen3.8-27B NVFP4 + DFlash2；DSpark 和 target-only 是显式回滚：

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.sglang-dflash2.yml build sglang
docker compose --env-file .env --env-file config/sglang/dflash2.env \
  --profile local-sglang up -d sglang
```

详见 [SGLANG_QWEN_LOCAL_AGENT.md](docs/operations/SGLANG_QWEN_LOCAL_AGENT.md)。

## Codex 引导的试玩

仓库内置 `playtest-forge` Skill。开始时先做只读 preflight，并列出运行选择：

```bash
.agents/skills/playtest-forge/scripts/preflight
.agents/skills/playtest-forge/scripts/session-options --choices-only --json
```

流程会在执行前冻结 Godot runtime、provider、难度、persona、seed、时长、保护指标和
证据合同。启动 provider、消耗 API 额度或修改游戏仍需要相应授权。

难度矩阵必须通过受控 matrix 命令执行：

```bash
uv run python tools/gameplay/run_gameplay_agent.py matrix \
  --config config/matrix.normal.yaml --dry-run --jobs 4 \
  --out reports/matrix-normal
```

## 报告存储

运行报告位于 `reports/`，默认不进入 Git。受控矩阵会自动封存完成的 JSONL；其他终态
报告可以使用无损归档服务：

```bash
uv run python tools/reports/archive_jsonl.py archive \
  <terminal-report-dir> --apply --replace
```

只有在 Zstandard 解压、重新解析、记录数、字节数和 SHA-256 全部一致后才删除源文件。

## 目录

```text
.agents/skills/playtest-forge/    Codex 工作流与证据协议
config/                           profile、target、gate 和 contract
demo/study-in-germany/            内置 Godot 参考游戏
examples/                         脱敏的 campaign 与 repair fixture
frontend/                         dashboard、inspector、report、human review
src/game_analysis_agent/          typed service、provider 和分析逻辑
tools/ 与 scripts/                CLI adapter 与运行时辅助工具
docs/                             架构、运维、计划和通用评审文档
```

## 当前限制

- 真实游戏运行需要 Godot 4.4 或 Docker wrapper。
- 实时人格 campaign 需要兼容的模型端点。
- Dashboard API 面向可信本地环境，不是带多租户认证、quota、TTL 和计费治理的托管服务。
- 内置游戏是参考 fixture，不是完整商业游戏。
- Human review 不会自动合并候选修改。

项目使用 MIT License；第三方与生成资产来源见 [ATTRIBUTION.md](ATTRIBUTION.md)。
