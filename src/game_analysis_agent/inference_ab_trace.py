"""Private, exact-request trace support for local inference A/B benchmarks."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any


class JsonlPersonaTraceSink:
    """Append canonical request payloads to a thread-safe, private JSONL trace."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def __call__(self, record: dict[str, Any]) -> None:
        request = {
            "model": record["model"],
            "messages": record["messages"],
            "temperature": record["temperature"],
            "max_tokens": record["max_tokens"],
            "extra_body": {
                "chat_template_kwargs": {
                    "enable_thinking": bool(record["enable_thinking"]),
                }
            },
        }
        canonical = json.dumps(
            request, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        payload = {
            **record,
            "request": request,
            "request_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
