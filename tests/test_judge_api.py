"""Service and HTTP contract tests for bounded human Judge Mode."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from game_analysis_agent.judge_api import (
    CampaignCreateRequest,
    JudgeAPIError,
    JudgeService,
    ProviderTestRequest,
    parse_json_body,
)
from tools.run_judge_api import handler_factory

ROOT = Path(__file__).resolve().parents[1]


class _Responses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        return SimpleNamespace(id="resp_probe", model="gpt-5.6-luna-2026-07-01")


class _Client:
    def __init__(self) -> None:
        self.responses = _Responses()


class _Factory:
    def __init__(self) -> None:
        self.client = _Client()
        self.kwargs: dict[str, object] = {}

    def __call__(self, **kwargs):  # noqa: ANN003
        self.kwargs = kwargs
        return self.client


def _wait(service: JudgeService, campaign_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        result = service.campaigns.get(campaign_id)
        if result["status"] not in {"queued", "running"}:
            return result
        time.sleep(0.01)
    raise AssertionError("campaign did not reach a terminal state")


def test_provider_status_and_test_never_serialize_server_key() -> None:
    factory = _Factory()
    service = JudgeService(
        project_root=ROOT,
        environment={"OPENAI_API_KEY": "sk-server-secret", "OPENAI_PERSONA_MODEL": "gpt-5.6-luna"},
        openai_client_factory=factory,
    )

    status = service.providers.status()
    result = service.providers.test(ProviderTestRequest(provider="openai"))
    serialized = json.dumps({"status": status, "result": result})

    assert status["providers"]["openai"]["api_key_configured"] is True
    assert factory.kwargs["api_key"] == "sk-server-secret"
    assert factory.client.responses.calls[0]["store"] is False
    assert "sk-server-secret" not in serialized
    assert "api_key" not in result


def test_openai_test_without_key_is_typed_unavailable() -> None:
    service = JudgeService(project_root=ROOT, environment={})

    with pytest.raises(JudgeAPIError) as error:
        service.providers.test(ProviderTestRequest(provider="openai"))

    assert error.value.code == "openai_key_missing"
    assert error.value.status_code == 503


def test_request_contract_rejects_key_unknown_persona_and_oversize() -> None:
    with pytest.raises(JudgeAPIError, match="does not match"):
        parse_json_body(b'{"provider":"openai","api_key":"forbidden"}', CampaignCreateRequest)
    with pytest.raises(ValidationError):
        CampaignCreateRequest(provider="replay", personas=("ghost",))
    with pytest.raises(JudgeAPIError) as error:
        parse_json_body(b" " * (33 * 1024), CampaignCreateRequest)
    assert error.value.code == "request_too_large"


def test_replay_campaign_and_public_experiment_are_bounded_and_labeled() -> None:
    service = JudgeService(project_root=ROOT, environment={})
    created = service.campaigns.create(
        CampaignCreateRequest(provider="replay", personas=("newbie",), seeds=(42,), max_weeks=3)
    )
    completed = _wait(service, str(created["campaign_id"]))
    experiment = service.experiment("cashflow-drift-repair-v1")

    assert completed["status"] == "completed"
    assert completed["mode"] == "prerecorded"
    assert completed["result"]["completed_cells"] == 18
    assert experiment["decision"] == "rejected"
    assert experiment["patch"]["canonical_source_path"] == "demo/study-in-germany"
    assert experiment["patch"]["disposition"] == "candidate_not_merged"
    assert "SimulationEngine.gd" in experiment["patch"]["diff"]
    assert experiment["mode"] == "prerecorded"
    assert [item["cohort"] for item in experiment["cohorts"]] == [
        "baseline_fixed",
        "patched_fixed",
        "baseline_holdout",
        "patched_holdout",
    ]
    with pytest.raises(JudgeAPIError, match="Only the committed"):
        service.experiment("../../private")


def test_live_campaign_fails_without_key_instead_of_falling_back() -> None:
    service = JudgeService(project_root=ROOT, environment={})
    created = service.campaigns.create(
        CampaignCreateRequest(provider="openai", personas=("newbie",), seeds=(42,), max_weeks=1)
    )
    failed = _wait(service, str(created["campaign_id"]))

    assert failed["status"] == "failed"
    assert failed["mode"] == "live"
    assert failed["error"]["code"] == "openai_key_missing"


def test_provider_status_requires_explicit_live_runner_opt_in(tmp_path: Path) -> None:
    game = tmp_path / "game"
    game.mkdir()
    (game / "project.godot").write_text("[application]\n", encoding="utf-8")
    environment = {"OPENAI_API_KEY": "server-only", "GAME_PROJECT_PATH": str(game)}

    disabled = JudgeService(project_root=ROOT, environment=environment)
    enabled = JudgeService(
        project_root=ROOT,
        environment=environment,
        live_runner=lambda _job: {"source": "test"},
    )

    disabled_status = disabled.providers.status()["providers"]["openai"]
    enabled_status = enabled.providers.status()["providers"]["openai"]
    assert disabled_status["live_runner_enabled"] is False
    assert disabled_status["live_campaign_ready"] is False
    assert enabled_status["live_runner_enabled"] is True
    assert enabled_status["live_campaign_ready"] is True


def test_campaign_capacity_and_cancellation_are_enforced(tmp_path: Path) -> None:
    game = tmp_path / "game"
    game.mkdir()
    (game / "project.godot").write_text("[application]\n", encoding="utf-8")
    release = threading.Event()

    def live_runner(_job):  # noqa: ANN001, ANN202
        release.wait(timeout=2)
        return {"source": "injected-live-runner"}

    service = JudgeService(
        project_root=ROOT,
        environment={"OPENAI_API_KEY": "server-only", "GAME_PROJECT_PATH": str(game)},
        live_runner=live_runner,
    )
    request = CampaignCreateRequest(provider="openai", max_weeks=1)
    first = service.campaigns.create(request)
    second = service.campaigns.create(request)
    with pytest.raises(JudgeAPIError) as error:
        service.campaigns.create(request)
    cancelled = service.campaigns.cancel(str(first["campaign_id"]))
    release.set()
    first_result = _wait(service, str(first["campaign_id"]))
    second_result = _wait(service, str(second["campaign_id"]))

    assert error.value.code == "campaign_capacity_exceeded"
    assert cancelled["campaign_id"] == first["campaign_id"]
    assert first_result["status"] == "cancelled"
    assert second_result["status"] == "completed"


def test_http_surface_status_replay_events_and_experiment() -> None:
    from http.server import ThreadingHTTPServer

    service = JudgeService(project_root=ROOT, environment={})
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), handler_factory(service, ROOT / "frontend/dist")
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(f"{base}/api/provider-status") as response:
            status = json.load(response)
        request = urllib.request.Request(
            f"{base}/api/campaigns",
            data=json.dumps({"provider": "replay"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            created = json.load(response)
        completed = _wait(service, created["campaign_id"])
        with urllib.request.urlopen(f"{base}/api/campaigns/{created['campaign_id']}/events") as response:
            events = response.read().decode()
        with urllib.request.urlopen(f"{base}/api/experiments/cashflow-drift-repair-v1") as response:
            experiment = json.load(response)
        with urllib.request.urlopen(f"{base}/") as response:
            index = response.read().decode()
        asset_path = re.search(
            r'src="(/(?:game_analysis_agent/)?assets/[^"]+\.js)"', index
        )
        assert asset_path is not None
        with urllib.request.urlopen(f"{base}{asset_path.group(1)}") as response:
            javascript = response.read()
            javascript_type = response.headers.get_content_type()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status["providers"]["replay"]["status"] == "available"
    assert completed["status"] == "completed"
    assert "event: campaign_completed" in events
    assert experiment["decision"] == "rejected"
    assert javascript_type in {"application/javascript", "text/javascript"}
    assert len(javascript) > 1000


def test_http_unknown_route_is_typed_404() -> None:
    from http.server import ThreadingHTTPServer

    service = JudgeService(project_root=ROOT, environment={})
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), handler_factory(service, ROOT / "frontend/dist")
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/unknown")
        payload = json.load(error.value)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert error.value.code == 404
    assert payload["error"]["code"] == "route_not_found"
