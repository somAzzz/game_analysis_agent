from __future__ import annotations

import hashlib
import json

from game_analysis_agent.inference_ab_trace import JsonlPersonaTraceSink


def test_jsonl_trace_sink_hashes_canonical_request(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "trace.jsonl"
    sink = JsonlPersonaTraceSink(path)
    record = {
        "schema_version": "persona-chat-trace-v1",
        "request_id": "newbie-42-w1",
        "request_fingerprint": "a" * 64,
        "persona": "newbie",
        "seed": 42,
        "week": 1,
        "phase": "decision",
        "attempt": 1,
        "step_name": "week-1",
        "model": "local-test",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.3,
        "max_tokens": 32,
        "enable_thinking": True,
    }

    sink(record)
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        payload["request"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )

    assert payload["request_sha256"] == hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    assert payload["request"]["messages"] == record["messages"]
    assert payload["request"]["extra_body"]["chat_template_kwargs"] == {
        "enable_thinking": True
    }
