from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "skill4econ/tests/smoke/test_psm_overlap_balance.py",
    ]
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
