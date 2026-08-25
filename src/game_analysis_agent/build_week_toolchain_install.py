"""No-root, checksum-verified installer for pinned Build Week tools."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .build_week_toolchain import platform_identifier

MARKER_FILE = ".playtest-forge-tool.json"
MARKER_SCHEMA = "build-week-installed-tool-v1"
INSTALL_SCHEMA = "build-week-toolchain-install-v1"


class ToolchainInstallError(RuntimeError):
    """Raised when a pinned tool cannot be installed safely and exactly."""


Downloader = Callable[[str, Path], None]


def install_toolchain(
    manifest: Mapping[str, Any],
    *,
    install_root: str | Path,
    cache_root: str | Path,
    system: str,
    machine: str,
    tools: Sequence[str] = ("node", "godot"),
    replace: bool = False,
    downloader: Downloader | None = None,
) -> dict[str, Any]:
    """Install selected pinned tools and write a sourceable environment file."""

    platform_id = platform_identifier(system, machine)
    root = Path(install_root).expanduser().resolve()
    cache = Path(cache_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    selected = list(dict.fromkeys(tools))
    unsupported = sorted(set(selected) - {"node", "godot"})
    if unsupported:
        raise ToolchainInstallError(f"unsupported tools requested: {', '.join(unsupported)}")

    results: dict[str, dict[str, Any]] = {}
    for tool in selected:
        tool_config = _mapping(manifest, tool)
        assets = _mapping(tool_config, "assets")
        asset = assets.get(platform_id)
        if asset is None:
            results[tool] = {
                "status": "unsupported",
                "version": tool_config.get("version", "unknown"),
                "platform": platform_id,
            }
            continue
        if not isinstance(asset, Mapping):
            raise ToolchainInstallError(f"invalid {tool} asset for {platform_id}")
        results[tool] = install_asset(
            tool,
            version=str(tool_config["version"]),
            platform_id=platform_id,
            asset=asset,
            install_dir=root / tool,
            cache_dir=cache,
            replace=replace,
            downloader=downloader,
        )

    environment = _write_environment(root, results)
    failed = [result for result in results.values() if result["status"] == "failed"]
    return {
        "schema_version": INSTALL_SCHEMA,
        "status": "ready" if not failed else "failed",
        "platform": platform_id,
        "install_root": f"<tools>/{root.name}",
        "environment_file": environment.name,
        "tools": results,
    }


def install_asset(
    tool: str,
    *,
    version: str,
    platform_id: str,
    asset: Mapping[str, Any],
    install_dir: Path,
    cache_dir: Path,
    replace: bool,
    downloader: Downloader | None,
) -> dict[str, Any]:
    """Download, verify, safely extract, and atomically install one tool."""

    archive_name = _required_string(asset, "archive", tool)
    if Path(archive_name).name != archive_name:
        raise ToolchainInstallError(f"invalid archive name for {tool}")
    url = _required_string(asset, "url", tool)
    digest_name = "sha512" if "sha512" in asset else "sha256"
    expected_digest = _required_string(asset, digest_name, tool)
    strip_components = asset.get("strip_components", 0)
    if not isinstance(strip_components, int) or strip_components < 0:
        raise ToolchainInstallError(f"invalid strip_components for {tool}")
    executable = asset.get("executable")
    if executable is not None and not isinstance(executable, str):
        raise ToolchainInstallError(f"invalid executable for {tool}")

    existing = _existing_install(install_dir, tool, version, platform_id, expected_digest)
    if existing and not replace:
        return {**existing, "status": "existing"}
    if install_dir.exists() and not existing:
        raise ToolchainInstallError(
            f"refusing to replace unmanaged or mismatched {tool} installation"
        )

    archive = cache_dir / archive_name
    _ensure_archive(
        url,
        archive,
        algorithm=digest_name,
        expected=expected_digest,
        downloader=downloader or _download,
    )
    temporary = Path(tempfile.mkdtemp(prefix=f".{tool}.", dir=install_dir.parent))
    backup: Path | None = None
    try:
        _extract_archive(archive, temporary, strip_components=strip_components)
        executable_path = _resolve_executable(tool, temporary, executable)
        observed_version = _tool_version(executable_path)
        expected_numeric = version.split(".stable", 1)[0]
        if not _version_matches(tool, observed_version, expected_numeric):
            raise ToolchainInstallError(
                f"installed {tool} version mismatch: expected {version}, got {observed_version}"
            )
        marker = {
            "schema_version": MARKER_SCHEMA,
            "tool": tool,
            "version": version,
            "platform": platform_id,
            "archive": archive_name,
            "digest_algorithm": digest_name,
            "digest": expected_digest,
            "executable": executable_path.relative_to(temporary).as_posix(),
        }
        (temporary / MARKER_FILE).write_text(
            json.dumps(marker, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if install_dir.exists():
            backup = install_dir.with_name(f".{install_dir.name}.previous")
            if backup.exists():
                raise ToolchainInstallError(f"{tool} backup path already exists")
            os.replace(install_dir, backup)
        os.replace(temporary, install_dir)
        if backup is not None:
            shutil.rmtree(backup)
        return {
            "status": "installed",
            "version": version,
            "observed_version": observed_version,
            "platform": platform_id,
            "executable": marker["executable"],
            "digest": expected_digest,
        }
    except Exception:
        if backup is not None and backup.exists() and not install_dir.exists():
            os.replace(backup, install_dir)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _ensure_archive(
    url: str,
    archive: Path,
    *,
    algorithm: str,
    expected: str,
    downloader: Downloader,
) -> None:
    if archive.is_file() and _file_digest(archive, algorithm) == expected:
        return
    archive.unlink(missing_ok=True)
    temporary = archive.with_name(f".{archive.name}.download")
    temporary.unlink(missing_ok=True)
    try:
        downloader(url, temporary)
        actual = _file_digest(temporary, algorithm)
        if actual != expected:
            raise ToolchainInstallError(
                f"download checksum mismatch for {archive.name}: expected {expected}, got {actual}"
            )
        os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)


def _download(url: str, destination: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as out:
            shutil.copyfileobj(response, out)
    except (OSError, TimeoutError) as exc:
        raise ToolchainInstallError(
            f"unable to download {Path(url).name}: {exc.__class__.__name__}"
        ) from exc


def _extract_archive(archive: Path, destination: Path, *, strip_components: int) -> None:
    if archive.name.endswith((".tar.gz", ".tar.xz", ".tar")):
        _extract_tar(archive, destination, strip_components=strip_components)
    elif archive.name.endswith(".zip"):
        _extract_zip(archive, destination, strip_components=strip_components)
    else:
        raise ToolchainInstallError(f"unsupported tool archive: {archive.name}")


def _extract_tar(archive: Path, destination: Path, *, strip_components: int) -> None:
    try:
        with tarfile.open(archive, mode="r:*") as bundle:
            for member in bundle.getmembers():
                relative = _stripped_safe_path(member.name, strip_components)
                if relative is None:
                    continue
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = bundle.extractfile(member)
                    if source is None:
                        raise ToolchainInstallError(f"unable to read {member.name}")
                    with source, target.open("wb") as handle:
                        shutil.copyfileobj(source, handle)
                    target.chmod(member.mode & 0o777)
                elif member.issym():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    _write_safe_symlink(target, member.linkname, destination)
                else:
                    raise ToolchainInstallError(f"unsupported tar member: {member.name}")
    except (tarfile.TarError, OSError) as exc:
        raise ToolchainInstallError(f"unable to extract {archive.name}") from exc


def _extract_zip(archive: Path, destination: Path, *, strip_components: int) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                relative = _stripped_safe_path(member.filename, strip_components)
                if relative is None:
                    continue
                target = destination.joinpath(*relative.parts)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                mode = (member.external_attr >> 16) & 0o777
                file_type = (member.external_attr >> 16) & 0o170000
                if file_type == stat.S_IFLNK:
                    linkname = bundle.read(member).decode("utf-8")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    _write_safe_symlink(target, linkname, destination)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
                if mode:
                    target.chmod(mode)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ToolchainInstallError(f"unable to extract {archive.name}") from exc


def _stripped_safe_path(value: str, strip_components: int) -> PurePosixPath | None:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ToolchainInstallError(f"unsafe tool archive path: {value}")
    parts = path.parts[strip_components:]
    if not parts:
        return None
    return PurePosixPath(*parts)


def _write_safe_symlink(target: Path, linkname: str, root: Path) -> None:
    if not linkname or Path(linkname).is_absolute():
        raise ToolchainInstallError(f"unsafe tool archive symlink: {linkname}")
    resolved = (target.parent / linkname).resolve(strict=False)
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ToolchainInstallError(f"tool archive symlink escapes root: {linkname}") from exc
    target.symlink_to(linkname)


def _resolve_executable(tool: str, root: Path, configured: Any) -> Path:
    relative = str(configured) if configured else ("bin/node" if tool == "node" else "godot")
    path = root / _safe_relative_path(relative, label=f"{tool} executable")
    if not path.is_file():
        raise ToolchainInstallError(f"installed {tool} executable not found: {relative}")
    if not os.access(path, os.X_OK):
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _tool_version(executable: Path) -> str:
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolchainInstallError(
            f"unable to execute installed tool: {exc.__class__.__name__}"
        ) from exc
    output = (completed.stdout or completed.stderr).strip().splitlines()
    if completed.returncode != 0 or not output:
        raise ToolchainInstallError("installed tool version check failed")
    return output[0].strip()


def _version_matches(tool: str, observed: str, expected: str) -> bool:
    normalized = observed.lstrip("v")
    if tool == "godot":
        return ".".join(normalized.split(".")[:2]) == ".".join(expected.split(".")[:2])
    return normalized == expected


def _existing_install(
    path: Path, tool: str, version: str, platform_id: str, digest: str
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    marker = path / MARKER_FILE
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        payload.get("schema_version") != MARKER_SCHEMA
        or payload.get("tool") != tool
        or payload.get("version") != version
        or payload.get("platform") != platform_id
        or payload.get("digest") != digest
    ):
        return None
    try:
        executable_relative = _safe_relative_path(
            str(payload.get("executable", "")), label=f"{tool} marker executable"
        )
    except ToolchainInstallError:
        return None
    executable = path / executable_relative
    if not executable.is_file() or not os.access(executable, os.X_OK):
        return None
    return {
        "version": version,
        "observed_version": _tool_version(executable),
        "platform": platform_id,
        "executable": executable_relative.as_posix(),
        "digest": digest,
    }


def _write_environment(root: Path, results: Mapping[str, Mapping[str, Any]]) -> Path:
    lines = ["# Generated by Playtest Forge Build Week toolchain installer."]
    node = results.get("node")
    if node and node.get("status") in {"installed", "existing"}:
        executable = root / "node" / str(node["executable"])
        npm = executable.parent / "npm"
        lines.extend(
            [
                f'export BUILD_WEEK_NODE_BIN="{executable}"',
                f'export BUILD_WEEK_NPM_BIN="{npm}"',
                f'export PATH="{executable.parent}:$PATH"',
            ]
        )
    godot = results.get("godot")
    if godot and godot.get("status") in {"installed", "existing"}:
        executable = root / "godot" / str(godot["executable"])
        lines.append(f'export GODOT_BIN="{executable}"')
    environment = root / "env.sh"
    environment.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return environment


def _file_digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_string(payload: Mapping[str, Any], key: str, tool: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ToolchainInstallError(f"missing {tool} asset {key}")
    return value


def _safe_relative_path(value: str, *, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ToolchainInstallError(f"unsafe {label}: {value}")
    return path


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ToolchainInstallError(f"toolchain {key} must be an object")
    return value
