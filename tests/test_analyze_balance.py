from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


class AnalyzeBalanceTest(unittest.TestCase):
    def test_analyze_balance_fixture(self) -> None:
        raw = Path("tests/fixtures/raw_runs.sample.jsonl")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report"
            result = subprocess.run(
                ["python3", "tools/analyze_balance.py", str(raw), str(out)],
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("Analysis written", result.stdout)
            self.assertTrue((out / "summary.json").exists())
            self.assertTrue((out / "ending_distribution.csv").exists())
            self.assertTrue((out / "weekly_stats.csv").exists())


if __name__ == "__main__":
    unittest.main()
