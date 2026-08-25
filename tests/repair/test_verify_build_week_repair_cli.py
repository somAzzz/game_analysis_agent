from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from game_analysis_agent.report_archive import (
    ReportArchiveError,
    archive_path_for,
    verify_archive,
)
from tools.repair.verify_build_week_repair import (
    _finalize_report_storage,
    build_parser,
)


def _required_args(tmp_path: Path) -> list[str]:
    return [
        "--plan",
        str(tmp_path / "plan.json"),
        "--patch-evidence",
        str(tmp_path / "patch.json"),
        "--baseline-game",
        str(tmp_path / "baseline"),
        "--patched-game",
        str(tmp_path / "patched"),
        "--output-dir",
        str(tmp_path / "output"),
        "--task-reference",
        "task",
        "--feedback-session-id",
        "session",
        "--model",
        "model",
    ]


def _write_jsonl(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps({"row": index, "payload": "repeated" * 50}) + "\n" for index in range(count)
        ),
        encoding="utf-8",
    )


def test_terminal_archiving_is_the_parser_default(tmp_path: Path) -> None:
    parsed = build_parser().parse_args(_required_args(tmp_path))

    assert parsed.keep_jsonl is False
    assert parsed.archive_level == 3
    assert parsed.zstd_bin == "zstd"


def test_keep_jsonl_is_an_explicit_override(tmp_path: Path) -> None:
    parsed = build_parser().parse_args([*_required_args(tmp_path), "--keep-jsonl"])
    source = tmp_path / "output" / "private" / "playthrough.jsonl"
    _write_jsonl(source, 2)

    storage = _finalize_report_storage(tmp_path / "output", keep_jsonl=True)

    assert parsed.keep_jsonl is True
    assert storage["status"] == "kept_jsonl"
    assert storage["files"] == 1
    assert source.is_file()
    assert not archive_path_for(source).exists()


def test_archive_failure_keeps_current_jsonl(tmp_path: Path) -> None:
    output = tmp_path / "output"
    source = output / "private" / "playthrough.jsonl"
    _write_jsonl(source, 2)

    with pytest.raises(ReportArchiveError, match="zstd executable is unavailable"):
        _finalize_report_storage(
            output,
            keep_jsonl=False,
            zstd_bin="definitely-missing-zstd-for-test",
        )

    assert source.is_file()
    assert not archive_path_for(source).exists()


@pytest.mark.skipif(shutil.which("zstd") is None, reason="zstd is unavailable")
def test_terminal_storage_replaces_jsonl_only_after_verified_archives(tmp_path: Path) -> None:
    output = tmp_path / "output"
    sources = [
        output / "baseline-fixed" / "private" / "a" / "playthrough.jsonl",
        output / "patched-holdout" / "private" / "b" / "playthrough.jsonl",
    ]
    _write_jsonl(sources[0], 2)
    _write_jsonl(sources[1], 3)

    storage = _finalize_report_storage(output, keep_jsonl=False)

    assert storage["status"] == "archived"
    assert storage["files"] == 2
    assert storage["records"] == 5
    assert storage["compressed_bytes"] < storage["uncompressed_bytes"]
    for source in sources:
        assert not source.exists()
        verify_archive(archive_path_for(source))
