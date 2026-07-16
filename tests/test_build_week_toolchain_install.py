"""Tests for the checksum-verified local Build Week tool installer."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from game_analysis_agent.build_week_toolchain_install import (
    ToolchainInstallError,
    install_toolchain,
)


def _tar_node() -> bytes:
    output = io.BytesIO()
    script = b"#!/bin/sh\necho v20.20.2\n"
    npm = b"#!/bin/sh\necho 10.8.2\n"
    with tarfile.open(fileobj=output, mode="w:gz") as bundle:
        for name, content in (
            ("node-v20.20.2/bin/node", script),
            ("node-v20.20.2/bin/npm", npm),
        ):
            info = tarfile.TarInfo(name)
            info.mode = 0o755
            info.size = len(content)
            bundle.addfile(info, io.BytesIO(content))
    return output.getvalue()


def _zip_godot(*, unsafe: bool = False) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        info = zipfile.ZipInfo(
            "../escape" if unsafe else "Godot.app/Contents/MacOS/Godot"
        )
        info.external_attr = (0o100755 & 0xFFFF) << 16
        bundle.writestr(info, b"#!/bin/sh\necho 4.4.stable.official\n")
    return output.getvalue()


def _manifest(node: bytes, godot: bytes) -> dict:
    return {
        "node": {
            "version": "20.20.2",
            "assets": {
                "darwin-arm64": {
                    "archive": "node.tar.gz",
                    "url": "https://example.test/node.tar.gz",
                    "sha256": hashlib.sha256(node).hexdigest(),
                    "strip_components": 1,
                }
            },
        },
        "godot": {
            "version": "4.4.stable",
            "assets": {
                "darwin-arm64": {
                    "archive": "godot.zip",
                    "url": "https://example.test/godot.zip",
                    "sha512": hashlib.sha512(godot).hexdigest(),
                    "strip_components": 0,
                    "executable": "Godot.app/Contents/MacOS/Godot",
                }
            },
        },
    }


def _downloader(assets: dict[str, bytes]):
    def download(url: str, destination: Path) -> None:
        destination.write_bytes(assets[Path(url).name])

    return download


def test_installs_pinned_tools_and_writes_environment(tmp_path: Path) -> None:
    node = _tar_node()
    godot = _zip_godot()
    root = tmp_path / "tools"

    result = install_toolchain(
        _manifest(node, godot),
        install_root=root,
        cache_root=tmp_path / "cache",
        system="Darwin",
        machine="arm64",
        downloader=_downloader({"node.tar.gz": node, "godot.zip": godot}),
    )

    assert result["status"] == "ready"
    assert result["tools"]["node"]["observed_version"] == "v20.20.2"
    assert result["tools"]["godot"]["observed_version"] == "4.4.stable.official"
    assert (root / "node/bin/node").is_file()
    assert (root / "godot/Godot.app/Contents/MacOS/Godot").is_file()
    environment = (root / "env.sh").read_text(encoding="utf-8")
    assert "BUILD_WEEK_NODE_BIN" in environment
    assert "GODOT_BIN" in environment
    assert str(tmp_path) not in json.dumps(result)


def test_matching_managed_install_is_reused(tmp_path: Path) -> None:
    node = _tar_node()
    godot = _zip_godot()
    manifest = _manifest(node, godot)
    kwargs = {
        "manifest": manifest,
        "install_root": tmp_path / "tools",
        "cache_root": tmp_path / "cache",
        "system": "Darwin",
        "machine": "arm64",
        "downloader": _downloader({"node.tar.gz": node, "godot.zip": godot}),
    }
    install_toolchain(**kwargs)

    second = install_toolchain(**kwargs)

    assert second["tools"]["node"]["status"] == "existing"
    assert second["tools"]["godot"]["status"] == "existing"


def test_checksum_mismatch_leaves_no_install(tmp_path: Path) -> None:
    node = _tar_node()
    godot = _zip_godot()
    manifest = _manifest(node, godot)
    manifest["node"]["assets"]["darwin-arm64"]["sha256"] = "0" * 64

    with pytest.raises(ToolchainInstallError, match="checksum mismatch"):
        install_toolchain(
            manifest,
            install_root=tmp_path / "tools",
            cache_root=tmp_path / "cache",
            system="Darwin",
            machine="arm64",
            tools=["node"],
            downloader=_downloader({"node.tar.gz": node}),
        )

    assert not (tmp_path / "tools/node").exists()


def test_unsafe_archive_path_is_rejected(tmp_path: Path) -> None:
    node = _tar_node()
    godot = _zip_godot(unsafe=True)

    with pytest.raises(ToolchainInstallError, match="unsafe"):
        install_toolchain(
            _manifest(node, godot),
            install_root=tmp_path / "tools",
            cache_root=tmp_path / "cache",
            system="Darwin",
            machine="arm64",
            tools=["godot"],
            downloader=_downloader({"godot.zip": godot}),
        )

    assert not (tmp_path / "escape").exists()


def test_linux_arm64_reports_godot_unsupported(tmp_path: Path) -> None:
    node = _tar_node()
    manifest = _manifest(node, _zip_godot())
    manifest["node"]["assets"]["linux-arm64"] = manifest["node"]["assets"].pop(
        "darwin-arm64"
    )

    result = install_toolchain(
        manifest,
        install_root=tmp_path / "tools",
        cache_root=tmp_path / "cache",
        system="Linux",
        machine="aarch64",
        tools=["godot"],
        downloader=_downloader({}),
    )

    assert result["status"] == "ready"
    assert result["tools"]["godot"]["status"] == "unsupported"


def test_executable_cannot_escape_install_root(tmp_path: Path) -> None:
    node = _tar_node()
    godot = _zip_godot()
    manifest = _manifest(node, godot)
    manifest["node"]["assets"]["darwin-arm64"]["executable"] = "../node"

    with pytest.raises(ToolchainInstallError, match="unsafe node executable"):
        install_toolchain(
            manifest,
            install_root=tmp_path / "tools",
            cache_root=tmp_path / "cache",
            system="Darwin",
            machine="arm64",
            tools=["node"],
            downloader=_downloader({"node.tar.gz": node}),
        )
