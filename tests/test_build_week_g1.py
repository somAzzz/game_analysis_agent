"""Unit tests for the fail-closed G1 provider/security reviewer."""

from __future__ import annotations

from game_analysis_agent.build_week_g1 import scan_secret_text


def test_secret_scanner_rejects_high_entropy_key_without_copying_value() -> None:
    secret = "sk-proj-" + "abcdefghijklmnopqrstuvwxyz123456"

    findings = scan_secret_text(f"OPENAI_API_KEY={secret}", location="test")

    assert findings
    assert secret not in str(findings)
    assert findings[0]["location"] == "test"


def test_secret_scanner_allows_named_variables_and_obvious_test_placeholders() -> None:
    text = (
        "OPENAI_API_KEY=\napi_key=sk-test\nredact sk-private-test\n"
        ".mask-image-with-a-very-long-css-class-name"
    )

    assert scan_secret_text(text, location="test") == []
