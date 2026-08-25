"""Lossless, auditable Zstandard archives for large JSONL report artifacts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO

SCHEMA_VERSION = "jsonl-zstd-archive-v1"
ARCHIVE_SUFFIX = ".jsonl.zst"
MANIFEST_SUFFIX = ".manifest.json"


class ReportArchiveError(RuntimeError):
    """Raised when an archive cannot be created or verified safely."""


@dataclass(frozen=True)
class JsonlArchiveManifest:
    """Identity and round-trip proof for one compressed JSONL artifact."""

    schema_version: str
    source_name: str
    archive_name: str
    codec: str
    compression_level: int
    records: int
    uncompressed_bytes: int
    uncompressed_sha256: str
    compressed_bytes: int
    compressed_sha256: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class JsonlScan:
    records: int
    bytes: int
    sha256: str


def archive_path_for(source: str | Path) -> Path:
    path = Path(source)
    if not path.name.endswith(".jsonl"):
        raise ReportArchiveError(f"source must end with .jsonl: {path}")
    return path.with_name(f"{path.name}.zst")


def manifest_path_for(archive: str | Path) -> Path:
    path = Path(archive)
    if not path.name.endswith(ARCHIVE_SUFFIX):
        raise ReportArchiveError(f"archive must end with {ARCHIVE_SUFFIX}: {path}")
    return path.with_name(f"{path.name}{MANIFEST_SUFFIX}")


def archive_jsonl(
    source: str | Path,
    *,
    level: int = 3,
    replace: bool = False,
    zstd_bin: str = "zstd",
) -> JsonlArchiveManifest:
    """Compress one JSONL file atomically and prove exact decompression.

    ``replace`` removes the source only after the archive, manifest, compressed
    hash, decompressed hash, byte count, record count, and JSON rows all verify.
    """

    if not 1 <= level <= 19:
        raise ReportArchiveError("compression level must be between 1 and 19")
    executable = _resolve_zstd(zstd_bin)
    source_path = _regular_file(source, label="source")
    archive = archive_path_for(source_path)
    manifest_path = manifest_path_for(archive)
    if archive.exists() or manifest_path.exists():
        raise ReportArchiveError(f"archive destination already exists: {archive}")

    before = _identity(source_path)
    source_scan = _scan_file(source_path)
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(archive)
    published = False
    try:
        with temporary.open("wb") as output:
            completed = subprocess.run(
                [executable, "-q", f"-{level}", "-c", str(source_path)],
                check=False,
                stdout=output,
                stderr=subprocess.PIPE,
            )
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", errors="replace")[-500:]
            raise ReportArchiveError(f"zstd compression failed: {message}")
        if _identity(source_path) != before:
            raise ReportArchiveError("source changed while it was being archived")

        compressed_scan = _scan_bytes(temporary)
        round_trip = _scan_zstd(temporary, executable)
        if round_trip != source_scan:
            raise ReportArchiveError("archive does not round-trip to the exact source bytes")

        payload = JsonlArchiveManifest(
            schema_version=SCHEMA_VERSION,
            source_name=source_path.name,
            archive_name=archive.name,
            codec="zstd",
            compression_level=level,
            records=source_scan.records,
            uncompressed_bytes=source_scan.bytes,
            uncompressed_sha256=source_scan.sha256,
            compressed_bytes=compressed_scan.bytes,
            compressed_sha256=compressed_scan.sha256,
        )
        temporary.replace(archive)
        published = True
        _atomic_write_text(manifest_path, payload.to_json())
        verify_archive(archive, zstd_bin=executable)
        if replace:
            source_path.unlink()
        return payload
    except Exception:
        temporary.unlink(missing_ok=True)
        if published:
            archive.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)
        raise


def archive_jsonl_tree(
    root: str | Path,
    *,
    keep_jsonl: bool = False,
    level: int = 3,
    zstd_bin: str = "zstd",
) -> dict[str, int | str]:
    """Seal every current JSONL below a completed report tree.

    Callers own lifecycle safety: the tree must no longer be running or
    finalizing. Each source is removed only after its individual round-trip
    proof succeeds.
    """

    sources = discover_jsonl([root])
    raw_bytes = sum(source.stat().st_size for source in sources)
    if keep_jsonl:
        return {
            "status": "kept_jsonl",
            "files": len(sources),
            "uncompressed_bytes": raw_bytes,
        }

    compressed_bytes = 0
    records = 0
    for source in sources:
        manifest = archive_jsonl(
            source,
            level=level,
            replace=True,
            zstd_bin=zstd_bin,
        )
        compressed_bytes += manifest.compressed_bytes
        records += manifest.records
    return {
        "status": "archived" if sources else "no_jsonl",
        "files": len(sources),
        "records": records,
        "uncompressed_bytes": raw_bytes,
        "compressed_bytes": compressed_bytes,
    }


def verify_archive(
    archive: str | Path,
    *,
    zstd_bin: str = "zstd",
) -> JsonlArchiveManifest:
    """Verify the archive bytes, manifest, JSONL rows, and exact raw identity."""

    executable = _resolve_zstd(zstd_bin)
    archive_path = _regular_file(archive, label="archive")
    manifest = _load_manifest(manifest_path_for(archive_path))
    if manifest.archive_name != archive_path.name:
        raise ReportArchiveError("manifest archive_name does not match the archive")
    compressed = _scan_bytes(archive_path)
    if (
        compressed.bytes != manifest.compressed_bytes
        or compressed.sha256 != manifest.compressed_sha256
    ):
        raise ReportArchiveError("compressed archive bytes or hash differ from the manifest")
    raw = _scan_zstd(archive_path, executable)
    if (
        raw.records != manifest.records
        or raw.bytes != manifest.uncompressed_bytes
        or raw.sha256 != manifest.uncompressed_sha256
    ):
        raise ReportArchiveError("decompressed JSONL identity differs from the manifest")
    return manifest


def restore_archive(
    archive: str | Path,
    *,
    destination: str | Path | None = None,
    zstd_bin: str = "zstd",
) -> Path:
    """Restore an archive atomically after verifying its manifest."""

    executable = _resolve_zstd(zstd_bin)
    archive_path = _regular_file(archive, label="archive")
    manifest = verify_archive(archive_path, zstd_bin=executable)
    target = (
        Path(destination)
        if destination is not None
        else archive_path.with_name(manifest.source_name)
    )
    target = target.resolve()
    if target.exists():
        raise ReportArchiveError(f"restore destination already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(target)
    try:
        with temporary.open("wb") as output:
            completed = subprocess.run(
                [executable, "-q", "-d", "-c", str(archive_path)],
                check=False,
                stdout=output,
                stderr=subprocess.PIPE,
            )
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", errors="replace")[-500:]
            raise ReportArchiveError(f"zstd decompression failed: {message}")
        restored = _scan_file(temporary)
        expected = JsonlScan(
            records=manifest.records,
            bytes=manifest.uncompressed_bytes,
            sha256=manifest.uncompressed_sha256,
        )
        if restored != expected:
            raise ReportArchiveError("restored JSONL differs from the manifest")
        temporary.replace(target)
        return target
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def resolve_jsonl_artifact(path: str | Path) -> Path:
    """Resolve a logical ``.jsonl`` path to hot JSONL or its cold archive."""

    requested = Path(path)
    if requested.name.endswith(ARCHIVE_SUFFIX):
        return _regular_file(requested, label="JSONL archive")
    if not requested.name.endswith(".jsonl"):
        raise ReportArchiveError(
            f"JSONL path must end with .jsonl or {ARCHIVE_SUFFIX}: {requested}"
        )
    if requested.is_file() and not requested.is_symlink():
        return requested.resolve()
    archive = archive_path_for(requested)
    if archive.is_file() and not archive.is_symlink():
        manifest = _load_manifest(manifest_path_for(archive))
        if manifest.source_name != requested.name:
            raise ReportArchiveError("manifest source_name does not match the logical JSONL path")
        return archive.resolve()
    raise ReportArchiveError(f"JSONL artifact is unavailable: {requested}")


def jsonl_artifact_exists(path: str | Path) -> bool:
    """Return whether hot JSONL or its adjacent verified-manifest archive exists."""

    try:
        resolve_jsonl_artifact(path)
    except ReportArchiveError:
        return False
    return True


def iter_jsonl_rows(
    path: str | Path,
    *,
    zstd_bin: str = "zstd",
) -> Iterator[tuple[int, dict[str, Any]]]:
    """Stream object rows from hot JSONL or verified cold JSONL.

    Cold reads verify the decompressed byte count, SHA-256, and record count
    against the adjacent manifest during the same pass used by the reader.
    """

    artifact = resolve_jsonl_artifact(path)
    if artifact.name.endswith(ARCHIVE_SUFFIX):
        yield from _iter_zstd_jsonl(artifact, zstd_bin=zstd_bin)
        return
    with artifact.open("rb") as handle:
        yield from _iter_object_rows(handle, label=str(artifact))


def jsonl_identity(path: str | Path, *, zstd_bin: str = "zstd") -> JsonlScan:
    """Return the logical uncompressed JSONL identity for hot or cold evidence."""

    artifact = resolve_jsonl_artifact(path)
    if artifact.name.endswith(ARCHIVE_SUFFIX):
        manifest = verify_archive(artifact, zstd_bin=zstd_bin)
        return JsonlScan(
            records=manifest.records,
            bytes=manifest.uncompressed_bytes,
            sha256=manifest.uncompressed_sha256,
        )
    return _scan_file(artifact)


def discover_jsonl(paths: list[str | Path]) -> list[Path]:
    """Return stable, de-duplicated JSONL files from files or directories."""

    found: dict[Path, None] = {}
    for raw in paths:
        path = Path(raw).resolve()
        if path.is_dir():
            candidates = path.rglob("*.jsonl")
        else:
            candidates = (path,)
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.name.endswith(".jsonl") and resolved.is_file():
                found[resolved] = None
    return sorted(found)


def _load_manifest(path: Path) -> JsonlArchiveManifest:
    regular = _regular_file(path, label="manifest")
    try:
        payload = json.loads(regular.read_text(encoding="utf-8"))
        manifest = JsonlArchiveManifest(**payload)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ReportArchiveError(f"invalid archive manifest: {path}: {exc}") from exc
    if manifest.schema_version != SCHEMA_VERSION or manifest.codec != "zstd":
        raise ReportArchiveError("unsupported archive manifest schema or codec")
    return manifest


def _scan_file(path: Path) -> JsonlScan:
    with path.open("rb") as handle:
        return _scan_jsonl(handle, label=str(path))


def _scan_bytes(path: Path) -> JsonlScan:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return JsonlScan(records=0, bytes=size, sha256=digest.hexdigest())


def _scan_zstd(path: Path, executable: str) -> JsonlScan:
    process = subprocess.Popen(
        [executable, "-q", "-d", "-c", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    try:
        scan = _scan_jsonl(process.stdout, label=str(path))
    except Exception:
        process.stdout.close()
        process.kill()
        process.wait()
        raise
    process.stdout.close()
    stderr = process.stderr.read() if process.stderr is not None else b""
    returncode = process.wait()
    if returncode != 0:
        message = stderr.decode("utf-8", errors="replace")[-500:]
        raise ReportArchiveError(f"zstd verification failed: {message}")
    return scan


def _scan_jsonl(handle: BinaryIO, *, label: str) -> JsonlScan:
    digest = hashlib.sha256()
    size = 0
    records = 0
    for line_number, line in enumerate(handle, start=1):
        digest.update(line)
        size += len(line)
        if not line.strip():
            continue
        try:
            json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReportArchiveError(f"invalid JSONL at {label}:{line_number}: {exc}") from exc
        records += 1
    return JsonlScan(records=records, bytes=size, sha256=digest.hexdigest())


def _iter_object_rows(handle: BinaryIO, *, label: str) -> Iterator[tuple[int, dict[str, Any]]]:
    for line_number, line in enumerate(handle, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReportArchiveError(f"invalid JSONL at {label}:{line_number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ReportArchiveError(f"JSONL row is not an object at {label}:{line_number}")
        yield line_number, payload


def _iter_zstd_jsonl(path: Path, *, zstd_bin: str) -> Iterator[tuple[int, dict[str, Any]]]:
    executable = _resolve_zstd(zstd_bin)
    manifest = _load_manifest(manifest_path_for(path))
    if manifest.archive_name != path.name:
        raise ReportArchiveError("manifest archive_name does not match the archive")
    compressed = _scan_bytes(path)
    if (
        compressed.bytes != manifest.compressed_bytes
        or compressed.sha256 != manifest.compressed_sha256
    ):
        raise ReportArchiveError("compressed archive bytes or hash differ from the manifest")
    process = subprocess.Popen(
        [executable, "-q", "-d", "-c", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    digest = hashlib.sha256()
    size = 0
    records = 0

    class _HashingReader(io.RawIOBase):
        def readable(self) -> bool:
            return True

        def readinto(self, buffer: bytearray) -> int:
            nonlocal size
            chunk = process.stdout.read(len(buffer))
            if not chunk:
                return 0
            buffer[: len(chunk)] = chunk
            digest.update(chunk)
            size += len(chunk)
            return len(chunk)

    buffered = io.BufferedReader(_HashingReader())
    try:
        for line_number, payload in _iter_object_rows(buffered, label=str(path)):
            records += 1
            yield line_number, payload
        buffered.close()
        stderr = process.stderr.read() if process.stderr is not None else b""
        returncode = process.wait()
        if returncode != 0:
            message = stderr.decode("utf-8", errors="replace")[-500:]
            raise ReportArchiveError(f"zstd read failed: {message}")
        if (
            records != manifest.records
            or size != manifest.uncompressed_bytes
            or digest.hexdigest() != manifest.uncompressed_sha256
        ):
            raise ReportArchiveError("decompressed JSONL identity differs from the manifest")
    except BaseException:
        buffered.close()
        if process.poll() is None:
            process.kill()
        process.wait()
        raise


def _regular_file(path: str | Path, *, label: str) -> Path:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise ReportArchiveError(f"{label} is not a regular file: {candidate}")
    return candidate.resolve()


def _resolve_zstd(value: str) -> str:
    executable = shutil.which(value)
    if executable is None:
        raise ReportArchiveError(
            f"zstd executable is unavailable: {value}; install zstd or pass --zstd-bin"
        )
    return executable


def _identity(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return stat.st_ino, stat.st_size, stat.st_mtime_ns


def _temporary_path(destination: Path) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    return Path(name)


def _atomic_write_text(path: Path, text: str) -> None:
    temporary = _temporary_path(path)
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
