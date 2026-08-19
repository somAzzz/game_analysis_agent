from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from game_analysis_agent.report_archive import (
    ReportArchiveError,
    archive_jsonl,
    archive_jsonl_tree,
    archive_path_for,
    discover_jsonl,
    iter_jsonl_rows,
    jsonl_artifact_exists,
    jsonl_identity,
    manifest_path_for,
    restore_archive,
    verify_archive,
)

pytestmark = pytest.mark.skipif(shutil.which("zstd") is None, reason="zstd is unavailable")


def _write_rows(path: Path, count: int = 20) -> bytes:
    content = "".join(
        json.dumps(
            {
                "run_id": index,
                "weekly_log": [
                    {"week": week, "state": "repeated-value" * 20} for week in range(20)
                ],
            },
            separators=(",", ":"),
        )
        + "\n"
        for index in range(count)
    ).encode()
    path.write_bytes(content)
    return content


def test_archive_round_trip_and_replace(tmp_path: Path) -> None:
    source = tmp_path / "runs.jsonl"
    original = _write_rows(source)

    manifest = archive_jsonl(source, replace=True)
    archive = archive_path_for(source)

    assert not source.exists()
    assert archive.is_file()
    assert manifest_path_for(archive).is_file()
    assert manifest.records == 20
    assert manifest.uncompressed_bytes == len(original)
    assert manifest.compressed_bytes < manifest.uncompressed_bytes
    assert verify_archive(archive) == manifest

    restored = restore_archive(archive)
    assert restored == source
    assert restored.read_bytes() == original


def test_archive_keeps_source_by_default_and_rejects_corruption(tmp_path: Path) -> None:
    source = tmp_path / "runs.jsonl"
    _write_rows(source, count=2)
    archive_jsonl(source)
    archive = archive_path_for(source)

    assert source.is_file()
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with pytest.raises(ReportArchiveError, match="compressed archive"):
        verify_archive(archive)
    with pytest.raises(ReportArchiveError, match="compressed archive"):
        list(iter_jsonl_rows(archive))


def test_discover_jsonl_is_recursive_stable_and_ignores_archives(tmp_path: Path) -> None:
    first = tmp_path / "b" / "two.jsonl"
    second = tmp_path / "a" / "one.jsonl"
    first.parent.mkdir()
    second.parent.mkdir()
    _write_rows(first, count=1)
    _write_rows(second, count=1)
    (tmp_path / "a" / "old.jsonl.zst").write_bytes(b"archive")

    assert discover_jsonl([tmp_path, first]) == sorted([first.resolve(), second.resolve()])


def test_invalid_jsonl_never_creates_an_archive(tmp_path: Path) -> None:
    source = tmp_path / "bad.jsonl"
    source.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ReportArchiveError, match="invalid JSONL"):
        archive_jsonl(source, replace=True)

    assert source.is_file()
    assert not archive_path_for(source).exists()


def test_archived_jsonl_is_streamed_through_its_logical_path(tmp_path: Path) -> None:
    source = tmp_path / "runs.jsonl"
    original = _write_rows(source, count=3)

    archive_jsonl(source, replace=True)

    assert jsonl_artifact_exists(source)
    assert [row["run_id"] for _, row in iter_jsonl_rows(source)] == [0, 1, 2]
    identity = jsonl_identity(source)
    assert identity.records == 3
    assert identity.bytes == len(original)


def test_archive_tree_accepts_empty_derived_jsonl(tmp_path: Path) -> None:
    empty = tmp_path / "anomalies.jsonl"
    empty.write_bytes(b"")
    _write_rows(tmp_path / "raw_runs.jsonl", count=1)

    storage = archive_jsonl_tree(tmp_path)

    assert storage["files"] == 2
    assert storage["records"] == 1
    assert list(iter_jsonl_rows(empty)) == []
