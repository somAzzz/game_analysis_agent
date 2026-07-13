# Service-first MCP 迁移计划

> 状态：规划文档，尚未开始 MCP 实现。
> 核心顺序：**先抽 Service Layer，再写 MCP Adapter。禁止先包装 CLI。**

本文汇总当前项目 MCP 化的目标架构、工具边界、文件改造、测试门禁和执行顺序，
用于后续开发时直接照单实施。当前 CLI、Godot runner、Docker sidecar、报告契约
和质量门禁都继续保留；MCP 是新增入口，不是对现有系统的推倒重写。

## 1. 已确定的架构决策

1. 不把 `tools/run_gameplay_agent.py` 的 `cmd_*` 直接注册为 MCP Tool。
2. 不允许 MCP Adapter 构造 `argparse.Namespace` 调用 CLI。
3. 先把业务逻辑抽成与传输协议无关的 Service：

   ```python
   simulation_service.run(...)
   report_service.read(...)
   gameplay_service.step(...)
   ```

4. CLI 和 MCP 最终都只能依赖同一套 Service：

   ```text
   argparse CLI ──┐
                  ├── Service Layer ── Godot / analytics / gates / reports
   MCP Adapter ───┘
   ```

5. Service 不打印、不退出进程、不依赖 MCP、不返回 CLI exit code。
6. Service 使用类型化 Request/Result 和类型化异常；CLI 再把结果映射为文本和
   exit code，MCP 再把结果映射为 structured content/tool error。
7. 第一版 MCP 使用 STDIO；Streamable HTTP 和远程认证后置。
8. vLLM 仍是推理服务，不是 MCP Host。由 Codex、Claude、VS Code 或自定义
   MCP Host 负责让模型发现并调用 MCP Tool。

## 2. 当前能力基线

项目目前没有 MCP Server，因此当前 MCP Tool 数量是 0。

[game_tools.py](../src/game_analysis_agent/game_tools.py) 中已有 6 个可直接迁移的
LLM function tools：

1. `get_state`
2. `list_available_actions`
3. `inspect_event`
4. `inspect_action`
5. `step`
6. `finish`

`InteractiveProbe.preview_step()` 已实现，但尚未注册成现有 LLM Tool。

[run_gameplay_agent.py](../tools/run_gameplay_agent.py) 还有 14 个 CLI 子命令：
`sim`、`analyze`、`probe`、`interactive-probe`、`export`、
`validate`、`matrix`、`compare-matrix`、`index`、`gates`、
`eval`、`qa`、`play`、`all`。这些命令不能机械地一一映射成 MCP Tool。

可以继续原样复用的核心模块：

- Godot GDScript runner 和 Docker wrapper；
- analytics、coverage、anomaly、value 分析；
- 六类跨仓库数据契约；
- report manifest 和源码指纹；
- strict quality gates；
- test matrix 和 fixed-seed compare；
- 前端和公开报告。

## 3. 目标架构

```text
MCP Host + LLM
      │
      ▼
MCP Client
      │
      ▼
game-analysis MCP Adapter
  ├─ Tools
  ├─ Resources
  └─ Prompts
      │
      ▼
Service Layer
  ├─ SimulationService
  ├─ ReportService
  ├─ GameplayService
  ├─ ValidationService
  ├─ AgentReviewService (兼容模式，可选)
  └─ MatrixService (后置)
      │
      ├─ Godot runner / Docker sidecar
      ├─ analytics / contracts / gates
      └─ reports/
```

## 4. 第一阶段：抽取 Service Layer

### 4.1 建议目录

```text
src/game_analysis_agent/
  services/
    __init__.py
    errors.py
    models.py
    simulation.py
    reports.py
    gameplay.py
    validation.py
    agent_review.py
    matrix.py
```

MCP 目录在这个阶段**不要创建**，MCP SDK 依赖也先不要加入。

### 4.2 通用 Service 规则

- 输入必须是 Pydantic model 或 dataclass，不能是 `argparse.Namespace`。
- 输出必须是结构化 Result，不能只是整数退出码。
- 失败使用类型化异常，例如：

  ```python
  class ServiceError(RuntimeError): ...
  class InvalidRequestError(ServiceError): ...
  class GodotExecutionError(ServiceError): ...
  class ContractFailure(ServiceError): ...
  class ReportNotFoundError(ServiceError): ...
  class UnsafePathError(ServiceError): ...
  ```

- Service 内禁止 `print()`、`sys.exit()` 和解析命令行。
- 日志使用标准 logging 或注入的事件/进度回调。
- 所有文件访问必须经过 `ReportService` 的安全路径解析。
- 所有 Godot 调用必须经过可注入的 runner，方便单元测试替换。
- 写报告时继续生成 manifest、哈希和 provenance。
- Request 必须限制 runs、weeks、jobs、persona、policy、difficulty 和 scenario。

### 4.3 SimulationService

目标接口：

```python
result = simulation_service.run(
    SimulationRequest(
        run_id="local-real-42",
        runs=200,
        weeks=20,
        policy="balanced",
        difficulty="normal",
        scenario="default_first_semester",
        seed=42,
    )
)
```

建议 Result：

```python
class SimulationResult(BaseModel):
    run_id: str
    report_dir: Path
    raw_trace: Path
    total_runs: int
    status: Literal["completed"]
    manifest: Path
```

从当前 `cmd_sim()` 和 `cmd_analyze()` 中抽出：

- 参数默认值和 canonical policy；
- report 目录初始化；
- Godot `RunSimulation.gd` 调用；
- stale artifact 防护；
- trace contract 校验；
- catalog consistency 校验；
- analytics/anomaly/value 分析；
- manifest 写入。

CLI Adapter 只负责：

```python
try:
    result = simulation_service.run(request)
except ServiceError as exc:
    print(str(exc), file=sys.stderr)
    return map_service_error_to_exit_code(exc)
print(f"Analysis written to {result.report_dir}")
return 0
```

### 4.4 ReportService

目标接口：

```python
manifest = report_service.read_manifest(run_id)
summary = report_service.read(run_id, "summary.json")
reports = report_service.list_reports(kind="balance")
trace = report_service.read_jsonl_slice(run_id, "raw_runs.jsonl", start=0, limit=20)
```

职责：

- 统一 `REPORT_ROOT`；
- 只接受 `run_id + artifact name`，不把任意绝对路径暴露给 MCP；
- 拒绝 `..`、符号链接逃逸和 allowlist 外文件；
- 读取并验证 JSON/JSONL/CSV/Markdown；
- 限制单次读取大小；
- 提供 report index、manifest、summary、gate、agent eval、anomaly 切片；
- 写入仍由业务 Service 完成，ReportService 负责原子写和安全解析。

### 4.5 GameplayService

目标接口：

```python
session = gameplay_service.start(
    StartPlaythroughRequest(
        persona="newbie",
        difficulty="normal",
        scenario="default_first_semester",
        seed=42,
    )
)

state = gameplay_service.get_state(session.playthrough_id)
result = gameplay_service.step(
    StepRequest(
        playthrough_id=session.playthrough_id,
        actions=["library_day"],
        event_choice_id="",
    )
)
final = gameplay_service.finish(session.playthrough_id)
evaluation = gameplay_service.evaluate(session.playthrough_id)
```

从 `InteractiveProbe` 抽出：

- start/get-state/list-actions/inspect/preview/step/finish；
- plan 累积和 Godot replay；
- risk guidance 契约；
- anomaly detection；
- agent eval 和 manifest。

Service 阶段就要解决会话问题，而不是留给 MCP Wrapper：

- 每局显式 `playthrough_id`；
- 每个 session 独立锁；
- session TTL；
- finished 状态；
- session plan 原子持久化；
- 服务重启恢复；
- 相同 session 的并发 step 拒绝或串行；
- 不同 session 互不污染。

建议存储：

```text
reports/mcp/sessions/<playthrough_id>/session.json
```

目录名可以暂时保留为 `mcp/sessions`，但存储实现属于 GameplayService，
不依赖 MCP SDK。

### 4.6 ValidationService

目标接口：

```python
validation_service.export_catalog(...)
validation_service.run_boundary_probe(...)
validation_service.validate(...)
validation_service.evaluate_gates(...)
```

从当前 `cmd_export()`、`cmd_probe()`、`cmd_validate()` 和 `cmd_gates()`
中抽出实际业务逻辑。Result 必须包含：

- 状态；
- 生成文件；
- contract validation 结果；
- gate failure/warning；
- manifest 路径；
- Godot stdout/stderr 摘要（不能直接打印）。

### 4.7 AgentReviewService

现有 `LocalLLMClient` 和六个 QA Agent 可以先保留为兼容 Service：

```python
agent_review_service.run(
    ReviewRequest(run_id="local-real-42", agents=["balance", "bug_hunter"])
)
```

MCP 正式模式更推荐由外部 MCP Host 的 LLM 读取 Resources、调用 Prompts 完成
分析，避免 MCP Server 内部再次调用另一层 LLM。这个 Service 只用于兼容当前
`qa` CLI 和批量回归。

### 4.8 MatrixService

`matrix`、`compare-matrix` 成本高，最后抽取。第一版只抽：

```python
matrix_service.plan(...)
matrix_service.compare(...)
```

真正执行 140 单元矩阵的接口后置，并要求显式资源上限和用户确认。

## 5. Service Layer 完成门禁

以下条件全部满足前，不进入 MCP 实现：

- [ ] `src/game_analysis_agent/services/` 不导入 `argparse`。
- [ ] Service 不调用 `print` 或 `sys.exit`。
- [ ] CLI 只负责参数解析、展示和 exit-code 映射。
- [ ] CLI 现有命令及输出产物保持兼容。
- [ ] Service Request/Result 有严格 schema 和边界校验。
- [ ] Service error 有稳定类型，测试不依赖错误文本匹配。
- [ ] ReportService 阻止路径穿越和符号链接逃逸。
- [ ] Gameplay session 支持隔离、持久化、锁和恢复。
- [ ] simulation/report/gameplay/validation 均有独立单元测试。
- [ ] 现有 pytest、Ruff、前端测试和 matrix dry-run 全部通过。
- [ ] Docker Godot 真实 smoke 通过。
- [ ] CLI 与 Service 生成的 manifest/contract 结果一致。

可自动检查的最低要求：

```bash
rg "argparse|sys\.exit|print\(" src/game_analysis_agent/services
uv run pytest -q -ra
uv run ruff check .
uv run python tools/run_gameplay_agent.py matrix --dry-run --jobs 4
```

第一条 `rg` 预期无输出。

## 6. 第二阶段：增加 MCP Adapter

Service 门禁通过后再增加：

```text
src/game_analysis_agent/mcp/
  __init__.py
  server.py
  models.py
  tools/
    gameplay.py
    pipeline.py
    reports.py
  resources.py
  prompts.py
```

`pyproject.toml` 再加入 MCP 依赖和入口。以 2026-07-13 为基准，官方 Python
SDK v1.x 是生产稳定线，v2 仍是预发布；实施时必须重新核对版本。当前建议：

```toml
[project.optional-dependencies]
mcp = [
    "mcp[cli]==1.28.1",
]

[project.scripts]
game-analysis-mcp = "game_analysis_agent.mcp.server:main"
```

MCP Tool 函数只做三件事：

1. 接收 MCP 参数并构造 Service Request；
2. 调用 Service；
3. 把 Service Result 转成 MCP structured output/resource link。

禁止 MCP Adapter：

- 直接运行 subprocess；
- 直接读写报告文件；
- 直接调用 `cmd_*`；
- 自己实现 contract/gate 逻辑；
- 持有另一套 session 状态；
- 捕获所有异常后返回模糊字符串。

## 7. MCP Tool 数量和分阶段范围

### 7.1 试玩 MVP：9 个

1. `start_playthrough`
2. `get_game_state`
3. `list_available_actions`
4. `inspect_action`
5. `inspect_event`
6. `preview_step`
7. `step_playthrough`
8. `finish_playthrough`
9. `evaluate_playthrough`

### 7.2 完整稳定版：16 个

在上面 9 个基础上增加：

10. `run_simulation`
11. `run_boundary_probe`
12. `export_game_catalog`
13. `validate_game`
14. `analyze_report`
15. `evaluate_quality_gates`
16. `compare_matrix_runs`

### 7.3 可选工具：最多 18 个

17. `run_qa`：兼容内部 LLM Agent，不作为 MCP 核心路径。
18. `run_matrix`：高成本工具，默认禁用，必须有限额和确认。

`get_trace_slice`、`get_anomalies` 可以作为只读查询 Tool，也可以由
Report Resource Template 实现；最终选择取决于目标 MCP Host 对分页 Resource
的支持，不应重复提供两套语义。

## 8. MCP Resources

建议 URI：

```text
game-analysis://reports/{run_id}/manifest
game-analysis://reports/{run_id}/summary
game-analysis://reports/{run_id}/gates
game-analysis://reports/{run_id}/agent-eval
game-analysis://reports/{run_id}/anomalies
game-analysis://catalog/actions
game-analysis://catalog/events
game-analysis://config/personas
```

规则：

- Resource handler 只能调用 ReportService；
- 不一次性返回完整 `raw_runs.jsonl`；
- 大文件必须分页、切片或返回 resource link；
- 读取时重新验证 manifest/hash，避免提供 stale evidence；
- 默认只读，不允许通过 URI 写文件。

## 9. MCP Prompts

现有 `prompts/` 映射为：

```text
review_balance(run_id)
review_content(run_id)
hunt_game_bugs(run_id)
review_boundary_results(run_id)
review_game_value(run_id)
play_as_persona(persona, difficulty, scenario)
```

Prompt 只描述工作流和引用哪些 Resource/Tool，不直接调用本地 vLLM，也不写报告。
需要持久化模型审查结果时，单独设计有 schema 的 `submit_review` Tool，且限制
输出文件名和 run_id。

## 10. Transport 和部署

### 10.1 第一版：STDIO

推荐 MCP Host 在宿主机启动：

```text
uv run game-analysis-mcp
```

优点：

- 能直接使用当前 Godot Docker wrapper；
- 能访问相同绝对路径和 reports；
- 不需要暴露 Docker socket；
- 本地 STDIO 不需要 HTTP OAuth；
- MCP Host 负责生命周期。

STDIO 模式下 stdout 只能写 MCP 协议消息，所有日志必须走 stderr 或 MCP logging。

### 10.2 第二版：Streamable HTTP

仅在多客户端或远程接入确有需求后实现：

```text
http://127.0.0.1:8010/mcp
```

本地必须绑定 `127.0.0.1`、验证 Origin。远程部署需要 TLS、OAuth/resource
server、scope 和审计。

### 10.3 Compose

Service Layer 和 STDIO MCP 第一版不需要修改现有 Compose：

```bash
docker compose up -d vllm godot
```

MCP Server 在宿主机运行，通过 wrapper 复用 Godot sidecar。

如果以后把 MCP Server 也放入 Compose，不推荐挂载
`/var/run/docker.sock`。应构建同时包含 Python 和 Godot 的专用 MCP 镜像，
或把 Godot runner 改成受限 RPC 服务。

## 11. 安全和资源限制

- MCP 输入只接受 `run_id`，不接受任意 report 绝对路径。
- report/game project 路径都必须位于配置 allowlist root。
- 限制 runs、weeks、jobs、并发 session、单次返回大小和超时。
- `run_matrix`、覆盖已有报告、删除 session 等操作需要明确确认。
- Tool 返回结构化错误，不泄漏 API key、环境变量或完整 subprocess 命令。
- STDIO 日志不得写 stdout。
- HTTP 模式必须验证 Origin 并加入认证。
- 对每个 MCP 调用记录 request id、tool、参数摘要、耗时、产物和错误。
- 继续复用现有 source fingerprint 和 report manifest。

## 12. 长任务处理

`sim`、`probe`、`validate`、`matrix` 可能运行数分钟：

1. Service 接收 progress callback 和 cancellation token。
2. 第一版 MCP 通过 Context 上报 progress。
3. 超过普通 Tool 超时的任务改成：

   ```text
   start_simulation -> job_id
   get_job_status(job_id)
   cancel_job(job_id)
   ```

4. 不依赖实验性 MCP Task 才能完成核心功能；等 SDK 和目标 Host 支持稳定后再接。
5. 当前阻塞式 `subprocess.run` 最终应封装为可取消 runner 或受控 worker。

## 13. 测试计划

### Service Layer

- Request/Result schema；
- CLI 默认参数与 Service request 映射；
- typed error 与 exit code 映射；
- fake Godot runner；
- stale output；
- contract failure；
- path traversal/symlink escape；
- session 隔离、锁、TTL、恢复；
- report 大小和分页；
- CLI 兼容回归；
- Docker Godot real smoke。

### MCP Adapter

- `tools/list` 名称和 schema；
- `resources/list` / resource template；
- `prompts/list`；
- in-memory MCP Client 调用；
- structured output schema；
- Service error 到 MCP error；
- STDIO stdout 纯净性；
- 并发 session；
- progress/cancellation；
- localhost HTTP/Origin/auth（进入 HTTP 阶段后）；
- scheduled real-Godot MCP smoke。

## 14. 分阶段执行清单

### Phase A：Service 基础

- [ ] 建立 service errors/models。
- [ ] 抽 ReportService 安全路径和读取。
- [ ] 抽 SimulationService。
- [ ] CLI `sim/analyze` 改为 adapter。
- [ ] 单元测试和 CLI 回归通过。

### Phase B：Gameplay Service

- [ ] 抽 GameplayService。
- [ ] 增加 playthrough id、锁、持久化、恢复。
- [ ] CLI `interactive-probe/play/eval` 改为 adapter。
- [ ] 真实 Godot 交互契约通过。

### Phase C：Validation/Pipeline Service

- [ ] 抽 export/probe/validate/gates。
- [ ] 保留 manifest 和失败关闭语义。
- [ ] CLI `all` 仅编排 Service，不直接实现业务。
- [ ] 全量测试和矩阵 dry-run 通过。

### Phase D：MCP 试玩 MVP

- [ ] 加入固定版本 MCP SDK。
- [ ] 注册 9 个试玩 Tool。
- [ ] 增加报告/目录 Resources。
- [ ] 增加 persona/review Prompts。
- [ ] STDIO Inspector 和 in-memory tests 通过。

### Phase E：完整 MCP

- [ ] 扩展到 16 个 Tool。
- [ ] progress/cancellation/job 模型。
- [ ] MCP 调用审计。
- [ ] real-Godot MCP CI smoke。
- [ ] MCP Host 配置示例和 README。

### Phase F：可选远程化

- [ ] Streamable HTTP。
- [ ] localhost/Origin 防护。
- [ ] OAuth、scope、TLS。
- [ ] 专用 MCP+Godot 镜像或 Godot RPC。

## 15. 完成定义

MCP 迁移只有同时满足以下条件才算完成：

- CLI 与 MCP 共用 Service，没有重复业务实现；
- MCP Adapter 不调用 `cmd_*`；
- 同一输入通过 CLI 和 MCP 得到等价 contract/manifest；
- 试玩 session 可隔离、恢复并处理并发；
- MCP Resources 不泄漏路径或大文件；
- 9 个 MVP Tool 有真实 Godot smoke；
- 16 个完整 Tool 有 schema、错误、超时和审计测试；
- 原有 244+ Python 测试、Ruff、前端测试/build、matrix dry-run 和
  real-Godot contract 继续通过。

## 16. 参考资料

- MCP 架构：<https://modelcontextprotocol.io/docs/learn/architecture>
- MCP Server 概念：<https://modelcontextprotocol.io/docs/learn/server-concepts>
- MCP Tools：<https://modelcontextprotocol.io/specification/2025-11-25/server/tools>
- MCP Resources：<https://modelcontextprotocol.io/specification/2025-11-25/server/resources>
- MCP Prompts：<https://modelcontextprotocol.io/specification/2025-11-25/server/prompts>
- MCP Transports：<https://modelcontextprotocol.io/specification/2025-11-25/basic/transports>
- Python SDK v1.x：<https://github.com/modelcontextprotocol/python-sdk/tree/v1.x>
