from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core import ROOT

REPO_ROOT = ROOT
REPORT_PATH = REPO_ROOT / "artifacts" / "smoke" / "latest_smoke_report.json"


@dataclass
class SmokeCheck:
    name: str
    args: list[str]


def _extract_last_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    for line in reversed(stripped.splitlines()):
        try:
            parsed = json.loads(line)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    start = stripped.rfind("{")
    if start >= 0:
        try:
            parsed = json.loads(stripped[start:])
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _suite_checks(suite: str, strict: bool) -> list[SmokeCheck]:
    pytest_base = [sys.executable, "-m", "pytest"]
    checks: dict[str, list[SmokeCheck]] = {
        "contracts": [
            SmokeCheck("contracts_pytest", [*pytest_base, "tests/contracts", "tests/validation", "-q"]),
        ],
        "backend-contract": [
            SmokeCheck("backend_contract_pytest", [*pytest_base, "tests/backends", "tests/adapters", "-q"]),
        ],
        "live-backend": [
            SmokeCheck(
                "live_backend_certification_cli",
                [
                    sys.executable,
                    "-m",
                    "skill4econ.cli",
                    "run",
                    "--engine",
                    "python",
                    "--method",
                    "live_backend_certification",
                    "--spec",
                    "examples/mini_panel/live_backend_certification_spec.yml",
                    "--run",
                ],
            ),
        ],
        "flagship-slow": [
            SmokeCheck(
                "flagship_slow_matrix_cli",
                [
                    sys.executable,
                    "-m",
                    "skill4econ.cli",
                    "run",
                    "--engine",
                    "python",
                    "--method",
                    "flagship_slow_matrix",
                    "--spec",
                    "examples/mini_panel/flagship_slow_matrix_spec.yml",
                    "--run",
                ],
            ),
        ],
        "did": [
            SmokeCheck("did_pytest", [*pytest_base, "tests/smoke/test_did_adapters.py", "tests/smoke/test_did_paper_run.py", "-q"]),
        ],
        "psm": [
            SmokeCheck("psm_pytest", [*pytest_base, "tests/smoke/test_psm_overlap_balance.py", "-q"]),
        ],
        "spatial": [
            SmokeCheck("spatial_pytest", [*pytest_base, "tests/smoke/test_spatial_weights.py", "tests/smoke/test_spatial_advanced.py", "-q"]),
        ],
        "all": [
            SmokeCheck("backend_contract_pytest", [*pytest_base, "tests/backends", "tests/adapters", "-q"]),
            SmokeCheck("full_cli_smoke", [sys.executable, "tests/smoke/run_smoke.py"]),
        ],
    }
    selected = checks.get(suite)
    if selected is None:
        raise ValueError(f"Unknown smoke suite: {suite}")
    if strict and suite != "contracts":
        selected = [*checks["contracts"], *selected]
    return selected


def run_smoke_suite(suite: str, *, strict: bool = False, timeout: int | None = None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for check in _suite_checks(suite, strict):
        proc = subprocess.run(
            check.args,
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        inner_checks = 1
        inner_status = None
        parsed = _extract_last_json_object(proc.stdout)
        if parsed:
            inner_checks = int(parsed.get("checks") or inner_checks)
            inner_status = parsed.get("status")
        results.append(
            {
                "name": check.name,
                "command": check.args,
                "status": "ok" if proc.returncode == 0 else "failed",
                "inner_status": inner_status,
                "inner_checks": inner_checks,
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-4000:],
                "stderr_tail": proc.stderr[-4000:],
            }
        )
    failed = [item for item in results if item["status"] != "ok"]
    report = {
        "status": "ok" if not failed else "failed",
        "suite": suite,
        "strict": strict,
        "checks": sum(int(item.get("inner_checks") or 1) for item in results),
        "outer_checks": len(results),
        "failed": len(failed),
        "skipped": 0,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
