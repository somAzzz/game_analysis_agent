#!/usr/bin/env python3
"""Create, verify, or restore lossless Zstandard JSONL report archives."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.report_archive import (  # noqa: E402
    ReportArchiveError,
    archive_jsonl,
    archive_path_for,
    discover_jsonl,
    restore_archive,
    verify_archive,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zstd-bin", default="zstd")
    subparsers = parser.add_subparsers(dest="command", required=True)

    archive = subparsers.add_parser("archive", help="Archive JSONL files or directory trees.")
    archive.add_argument("paths", nargs="+", type=Path)
    archive.add_argument("--level", type=int, default=3)
    archive.add_argument(
        "--apply",
        action="store_true",
        help="Create archives; the default is a read-only dry run.",
    )
    archive.add_argument(
        "--replace",
        action="store_true",
        help="Delete each source only after its archive and manifest verify.",
    )
    archive.add_argument("--json", action="store_true")

    verify = subparsers.add_parser("verify", help="Verify one or more .jsonl.zst archives.")
    verify.add_argument("archives", nargs="+", type=Path)
    verify.add_argument("--json", action="store_true")

    restore = subparsers.add_parser("restore", help="Restore archives to their JSONL names.")
    restore.add_argument("archives", nargs="+", type=Path)
    restore.add_argument(
        "--apply",
        action="store_true",
        help="Restore files; the default is a read-only dry run.",
    )
    restore.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "archive":
            if args.replace and not args.apply:
                raise ReportArchiveError("--replace requires --apply")
            sources = discover_jsonl(args.paths)
            if not sources:
                raise ReportArchiveError("no JSONL files found")
            for source in sources:
                archive = archive_path_for(source)
                if not args.apply:
                    _emit(
                        {
                            "status": "would_archive",
                            "source": str(source),
                            "archive": str(archive),
                            "replace": args.replace,
                        },
                        json_output=args.json,
                    )
                    continue
                manifest = archive_jsonl(
                    source,
                    level=args.level,
                    replace=args.replace,
                    zstd_bin=args.zstd_bin,
                )
                _emit(
                    {"status": "archived", **asdict(manifest), "source_removed": args.replace},
                    json_output=args.json,
                )
            return 0

        if args.command == "verify":
            for archive in args.archives:
                manifest = verify_archive(archive, zstd_bin=args.zstd_bin)
                _emit(
                    {"status": "verified", **asdict(manifest)},
                    json_output=args.json,
                )
            return 0

        for archive in args.archives:
            if not args.apply:
                _emit(
                    {"status": "would_restore", "archive": str(archive)},
                    json_output=args.json,
                )
                continue
            target = restore_archive(archive, zstd_bin=args.zstd_bin)
            _emit(
                {"status": "restored", "archive": str(archive), "target": str(target)},
                json_output=args.json,
            )
        return 0
    except (OSError, ReportArchiveError) as exc:
        print(f"report archive error: {exc}", file=sys.stderr)
        return 1


def _emit(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    status = payload["status"]
    name = payload.get("source_name") or payload.get("source") or payload.get("archive")
    if status in {"archived", "verified"}:
        print(
            f"{status}: {name} "
            f"({payload['uncompressed_bytes']} -> {payload['compressed_bytes']} bytes, "
            f"{payload['records']} records)"
        )
    else:
        print(f"{status}: {name}")


if __name__ == "__main__":
    raise SystemExit(main())
