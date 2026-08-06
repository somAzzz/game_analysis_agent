"""Scheduling, isolation, resume, partial, and cancellation tests."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from game_analysis_agent.campaign_contract import (
    CampaignCellState,
    CampaignRequest,
    CampaignSourceIdentity,
)
from game_analysis_agent.campaign_runner import (
    CampaignRunner,
    CellExecutionOutcome,
    ChildProcessRegistry,
)


def _request(**overrides) -> CampaignRequest:  # noqa: ANN003
    payload = {
        "campaign_id": "runner-test-v1",
        "personas": ["newbie", "study"],
        "seeds": [42, 43],
        "max_weeks": 2,
        "provider": "replay",
        "concurrency": 2,
        "report_root": "reports/campaigns",
    }
    payload.update(overrides)
    return CampaignRequest.model_validate(payload)


def _source(**overrides) -> CampaignSourceIdentity:  # noqa: ANN003
    payload = {
        "agent_commit": "a" * 40,
        "agent_tree": "b" * 40,
        "game_commit": "c" * 40,
        "game_tree": "d" * 40,
        "game_archive_sha256": "e" * 64,
        "campaign_config_sha256": "f" * 64,
        "provider": "replay",
        "provider_mode": "replay",
        "provider_revision": "fixture:test",
    }
    payload.update(overrides)
    return CampaignSourceIdentity.model_validate(payload)


class _Executor:
    def __init__(self, *, delay_s: float = 0) -> None:
        self.calls = []
        self.delay_s = delay_s
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def __call__(self, request, output_dir, context):  # noqa: ANN001
        with self.lock:
            self.calls.append(request.cell_id)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            rows = []
            for week in range(1, request.max_weeks + 1):
                assert not context.cancelled
                rows.append(
                    json.dumps(
                        {
                            "campaign_id": request.campaign_id,
                            "cell_id": request.cell_id,
                            "persona": request.persona.value,
                            "seed": request.seed,
                            "week": week,
                        },
                        sort_keys=True,
                    )
                )
                if self.delay_s:
                    time.sleep(self.delay_s)
            (output_dir / "playthrough.jsonl").write_text(
                "\n".join(rows) + "\n", encoding="utf-8"
            )
            return CellExecutionOutcome(
                state=CampaignCellState.COMPLETED,
                stop_reason="week_limit",
                completed_weeks=request.max_weeks,
            )
        finally:
            with self.lock:
                self.active -= 1


def test_runner_isolates_cells_caps_concurrency_and_writes_citations(tmp_path: Path) -> None:
    executor = _Executor(delay_s=0.02)
    runner = CampaignRunner(
        project_root=tmp_path,
        request=_request(),
        source=_source(),
        executor=executor,
    )

    summary = runner.run()

    assert summary.submittable is True
    assert summary.status_counts["completed"] == 4
    assert executor.max_active == 2
    assert len({result.request.output_dir for result in summary.results}) == 4
    assert all(len(result.citations) == 2 for result in summary.results)
    assert all(result.artifacts[0].record_count == 2 for result in summary.results)
    assert not list(tmp_path.rglob("*.tmp"))


def test_resume_skips_only_exact_completed_source_and_input(tmp_path: Path) -> None:
    executor = _Executor()
    request = _request()
    first = CampaignRunner(
        project_root=tmp_path, request=request, source=_source(), executor=executor
    ).run()
    assert len(executor.calls) == 4

    never = _Executor()
    resumed = CampaignRunner(
        project_root=tmp_path, request=request, source=_source(), executor=never
    ).run(resume=True)
    assert never.calls == []
    assert len(resumed.resumed_cell_ids) == 4

    changed = _Executor()
    rerun = CampaignRunner(
        project_root=tmp_path,
        request=request,
        source=_source(provider_revision="fixture:changed"),
        executor=changed,
    ).run(resume=True)
    assert len(changed.calls) == 4
    assert rerun.resumed_cell_ids == ()
    assert first.results[0].source != rerun.results[0].source


def test_exception_after_a_written_week_is_partial_and_not_submittable(tmp_path: Path) -> None:
    def partial(request, output_dir, context):  # noqa: ANN001
        del context
        (output_dir / "playthrough.jsonl").write_text(
            json.dumps({"week": 1, "cell_id": request.cell_id}) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError("probe sk-test stopped")

    summary = CampaignRunner(
        project_root=tmp_path,
        request=_request(personas=["newbie"], seeds=[42]),
        source=_source(),
        executor=partial,
    ).run()

    result = summary.results[0]
    assert result.state == CampaignCellState.PARTIAL
    assert result.completed_weeks == 1
    assert "sk-test" not in result.error
    assert summary.submittable is False


class _Child:
    def __init__(self, *, exits_on_terminate: bool) -> None:
        self.exits_on_terminate = exits_on_terminate
        self.running = True
        self.terminated = 0
        self.killed = 0

    def poll(self):  # noqa: ANN201
        return None if self.running else 0

    def terminate(self) -> None:
        self.terminated += 1
        if self.exits_on_terminate:
            self.running = False

    def wait(self, timeout=None):  # noqa: ANN001, ANN201
        if self.running:
            raise TimeoutError(timeout)
        return 0

    def kill(self) -> None:
        self.killed += 1
        self.running = False


def test_child_registry_terminates_then_kills_stubborn_processes() -> None:
    graceful = _Child(exits_on_terminate=True)
    stubborn = _Child(exits_on_terminate=False)
    registry = ChildProcessRegistry()
    registry.register(graceful)
    registry.register(stubborn)

    assert registry.terminate_all(grace_s=0) == 2
    assert graceful.terminated == 1 and graceful.killed == 0
    assert stubborn.terminated == 1 and stubborn.killed == 1


def test_runner_cancellation_propagates_to_active_cell(tmp_path: Path) -> None:
    entered = threading.Event()

    def blocking(request, output_dir, context):  # noqa: ANN001
        del request, output_dir
        entered.set()
        while not context.cancelled:
            time.sleep(0.005)
        return CellExecutionOutcome(
            state=CampaignCellState.CANCELLED,
            stop_reason="cancelled",
            completed_weeks=0,
            error="campaign cancelled",
            artifact_names=(),
        )

    runner = CampaignRunner(
        project_root=tmp_path,
        request=_request(personas=["newbie"], seeds=[42], concurrency=1),
        source=_source(),
        executor=blocking,
    )
    holder = []
    thread = threading.Thread(target=lambda: holder.append(runner.run()))
    thread.start()
    assert entered.wait(timeout=1)
    runner.cancel()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert holder[0].results[0].state == CampaignCellState.CANCELLED
    assert holder[0].submittable is False
