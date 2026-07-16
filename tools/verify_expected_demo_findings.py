#!/usr/bin/env python3
"""Fail closed unless real-Godot validation matches the declared demo defect."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class ExpectedFindingError(RuntimeError):
    """Raised when the declared expected-failure contract does not match."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExpectedFindingError(f"invalid or missing JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ExpectedFindingError(f"JSON root must be an object: {path}")
    return value


def verify_expected_findings(
    *, report_dir: Path, validate_exit_code: int, project_root: Path = ROOT
) -> dict[str, Any]:
    contract = _read(project_root / "config/build_week_2026_expected_demo_findings.json")
    pin = _read(project_root / "config/build_week_2026_game_pin.json")
    if contract.get("schema_version") != "build-week-expected-demo-findings-v1":
        raise ExpectedFindingError("expected-finding schema is unsupported")
    if contract.get("game_commit") != (pin.get("pin") or {}).get("commit"):
        raise ExpectedFindingError("expected findings are not bound to the current game pin")
    if validate_exit_code != contract.get("expected_validate_exit_code"):
        raise ExpectedFindingError("validate exit code differs from declared expected failure")

    summary = _read(report_dir / "validation_summary.json")
    checks = {item.get("check"): item for item in summary.get("checks", [])}
    required = set(contract.get("required_passing_validators") or [])
    failed_required = sorted(
        name for name in required if (checks.get(name) or {}).get("returncode") != 0
    )
    if failed_required:
        raise ExpectedFindingError(f"required validators failed: {failed_required}")
    demo = checks.get("demo") or {}
    if demo.get("returncode") != 1:
        raise ExpectedFindingError("demo validator did not return the declared failure")
    unexpected_checks = sorted(
        name for name, item in checks.items() if name != "demo" and item.get("returncode") != 0
    )
    if unexpected_checks:
        raise ExpectedFindingError(f"unexpected validator failures: {unexpected_checks}")

    report = _read(report_dir / "demo_gate_validation.json")
    actual_errors = report.get("errors")
    expected_errors = contract.get("expected_errors")
    if actual_errors != expected_errors:
        raise ExpectedFindingError(
            "demo findings changed; review the game evidence and update the contract deliberately"
        )
    return {
        "schema_version": "build-week-expected-demo-findings-result-v1",
        "status": "passed",
        "game_commit": contract["game_commit"],
        "expected_failure_count": len(expected_errors),
        "passing_validators": sorted(required),
        "demo_validator_status": "expected_failure",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--validate-exit-code", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify_expected_findings(
            report_dir=args.report_dir.resolve(),
            validate_exit_code=args.validate_exit_code,
        )
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
    except ExpectedFindingError as exc:
        print(f"expected demo finding error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
