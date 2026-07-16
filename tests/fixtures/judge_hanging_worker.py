"""Failure-injection worker that leaves a child for process-group cleanup tests."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

child = subprocess.Popen(["sleep", "60"])
Path(os.environ["JUDGE_TEST_PID_FILE"]).write_text(
    f"{os.getpid()}\n{child.pid}\n", encoding="utf-8"
)
time.sleep(60)
