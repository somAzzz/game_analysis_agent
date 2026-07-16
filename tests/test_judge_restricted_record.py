"""Truthfulness checks for the committed restricted-environment record."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs/reviews/openai_build_week_2026/P4-restricted-environment.review.json"


def test_restricted_record_passes_offline_but_does_not_claim_docker() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    scenarios = {item["id"]: item for item in record["scenarios"]}

    assert record["status"] == "passed"
    assert record["observations"]["full_tests"] == "404 passed"
    assert scenarios["no_network_docker_gpu_secret_tty_browser_port"]["status"] == "passed"
    assert scenarios["timeout_cleanup"]["status"] == "passed"
    assert scenarios["signal_cleanup"]["status"] == "passed"
    assert scenarios["linux_amd64_codex_universal_approximation"]["status"] == "not_run"
    assert record["host"]["docker"]["status"] == "unavailable"
