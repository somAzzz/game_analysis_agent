"""Expected real-Godot demo-failure gate tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools.verify_expected_demo_findings import ExpectedFindingError, verify_expected_findings

ROOT = Path(__file__).resolve().parents[1]


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    (project / "config").mkdir(parents=True)
    for name in (
        "build_week_2026_expected_demo_findings.json",
        "build_week_2026_game_pin.json",
    ):
        shutil.copy2(ROOT / "config" / name, project / "config" / name)
    report = tmp_path / "report"
    report.mkdir()
    contract = json.loads(
        (project / "config/build_week_2026_expected_demo_findings.json").read_text(
            encoding="utf-8"
        )
    )
    (report / "validation_summary.json").write_text(
        json.dumps({
            "checks": [
                {"check": name, "returncode": 0}
                for name in contract["required_passing_validators"]
            ] + [{"check": "demo", "returncode": 1}],
        }),
        encoding="utf-8",
    )
    (report / "demo_gate_validation.json").write_text(
        json.dumps({"errors": contract["expected_errors"]}), encoding="utf-8"
    )
    return project, report


def test_accepts_only_declared_demo_failure(tmp_path: Path) -> None:
    project, report = _fixture(tmp_path)

    result = verify_expected_findings(
        report_dir=report, validate_exit_code=1, project_root=project
    )

    assert result["status"] == "passed"
    assert result["expected_failure_count"] == 3


def test_rejects_changed_demo_findings(tmp_path: Path) -> None:
    project, report = _fixture(tmp_path)
    (report / "demo_gate_validation.json").write_text(
        json.dumps({"errors": ["different failure"]}), encoding="utf-8"
    )

    with pytest.raises(ExpectedFindingError, match="findings changed"):
        verify_expected_findings(
            report_dir=report, validate_exit_code=1, project_root=project
        )
