"""Smoke tests for the React + React Flow frontend.

These don't run the actual Vite dev server (CI may not have node) — they
verify the build artefacts and that the Python manifest emitter
produces JSON that the React app can actually consume.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"


def _has_node() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


@pytest.mark.skipif(not _has_node(), reason="node/npm not available")
def test_vite_build_succeeds() -> None:
    """Run ``npm run build`` and verify ``dist/index.html`` exists."""
    # Skip if node_modules is missing — no point running on a fresh checkout.
    if not (FRONTEND / "node_modules").exists():
        pytest.skip("frontend/node_modules not installed; skipping Vite build")
    proc = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, f"npm run build failed:\n{proc.stderr}"
    assert (DIST / "index.html").exists()


@pytest.mark.skipif(not _has_node(), reason="node/npm not available")
def test_dist_contains_manifest() -> None:
    """The Python-emitted manifest should be copied into dist/."""
    if not (DIST / "manifest.json").exists():
        pytest.skip("dist/manifest.json not built yet")
    parsed = json.loads((DIST / "manifest.json").read_text())
    assert "issues" in parsed
    assert "counts" in parsed


def test_python_manifest_is_valid_json(tmp_path) -> None:
    """A freshly-emitted manifest should parse cleanly."""
    sys.path.insert(0, str(ROOT / "tools"))
    from emit_manifest import emit_all

    balance = tmp_path / "reports" / "balance" / "demo"
    balance.mkdir(parents=True)
    (balance / "summary.json").write_text(
        json.dumps({"total_runs": 3}), encoding="utf-8"
    )
    emit_all(tmp_path / "reports")
    parsed = json.loads((tmp_path / "reports" / "manifest.json").read_text())
    assert any(card["id"] == "demo" for card in parsed["issues"])