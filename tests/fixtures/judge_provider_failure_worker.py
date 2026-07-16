"""Failure-injection worker emulating a provider loss after startup."""

from __future__ import annotations

import json

print(
    json.dumps(
        {
            "schema_version": "judge-replay-worker-v1",
            "status": "failed",
            "checks": [{"id": "provider", "status": "failed"}],
            "artifacts": [],
            "error_code": "provider_failed_mid_run",
            "error": "injected provider connection loss",
            "remediation": "Retry live mode or use offline Replay evidence.",
        }
    )
)
raise SystemExit(1)
