"""Safety checks for the legacy balance simulation adapter."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_balance_wrapper_uses_writable_runtime_and_rejects_canonical_demo() -> None:
    script = (ROOT / "tools/run_balance_sim.sh").read_text(encoding="utf-8")

    assert "reports/runtime/balance-sim-game" in script
    assert "tools/prepare_embedded_demo.py" in script
    assert "Refusing to run Godot inside the canonical embedded demo" in script
    assert 'GAME_PROJECT_PATH="${GAME_PROJECT_PATH:-$ROOT/demo/study-in-germany}"' not in script
