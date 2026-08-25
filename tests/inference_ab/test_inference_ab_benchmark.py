from __future__ import annotations

import hashlib
import json

import pytest

from game_analysis_agent import inference_ab_benchmark as benchmark


def _trace_row(*, persona: str, week: int, phase: str, attempt: int) -> dict:
    request = {
        "model": "local-test",
        "messages": [{"role": "user", "content": f"{persona}-{week}-{phase}-{attempt}"}],
        "temperature": 0.3,
        "max_tokens": 32,
    }
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": "persona-chat-trace-v1",
        "request_id": f"{persona}-42-w{week}-{phase}",
        "persona": persona,
        "seed": 42,
        "week": week,
        "phase": phase,
        "attempt": attempt,
        "request": request,
        "request_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def test_read_trace_verifies_hash_and_filters_without_reordering(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "trace.jsonl"
    rows = [
        _trace_row(persona="social", week=1, phase="decision", attempt=1),
        _trace_row(persona="newbie", week=1, phase="event_choice", attempt=1),
        _trace_row(persona="social", week=1, phase="decision", attempt=2),
        _trace_row(persona="newbie", week=2, phase="decision", attempt=1),
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    selected = benchmark.read_trace(path, phase="decision", attempt=1)

    assert [(row["persona"], row["week"]) for row in selected] == [
        ("social", 1),
        ("newbie", 2),
    ]


def test_read_trace_rejects_modified_request(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "trace.jsonl"
    row = _trace_row(persona="newbie", week=1, phase="decision", attempt=1)
    row["request"]["max_tokens"] = 64
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="trace hash mismatch"):
        benchmark.read_trace(path)


def test_vllm_request_migrates_legacy_trace_without_mutating_it() -> None:
    legacy = {
        "model": "local-test",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 32,
    }

    migrated = benchmark._vllm_request(legacy)

    assert migrated["max_completion_tokens"] == 32
    assert "max_tokens" not in migrated
    assert legacy["max_tokens"] == 32


def test_calibrated_messages_hits_exact_chat_token_target(monkeypatch) -> None:  # noqa: ANN001
    endpoint = benchmark.Endpoint("http://local/v1", "token", "model")

    def fake_tokenize(_endpoint, messages):  # noqa: ANN001
        return len(messages[0]["content"].split()) + 10

    monkeypatch.setattr(benchmark, "_tokenize", fake_tokenize)

    messages = benchmark.calibrated_messages(endpoint, 512)

    assert fake_tokenize(endpoint, messages) == 512


def test_endpoint_requires_all_local_vllm_environment(monkeypatch) -> None:  # noqa: ANN001
    for name in ("VLLM_BASE_URL", "VLLM_API_KEY", "LLM_SERVED_MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError, match="missing endpoint environment"):
        benchmark.Endpoint.from_env()
