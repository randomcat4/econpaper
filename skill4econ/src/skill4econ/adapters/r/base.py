from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from pathlib import Path

from ...core import RunContext, run_subprocess, write_json
from ..did_common import skipped_backend_unavailable


def _rscript_path() -> str | None:
    return os.environ.get("SKILL4ECON_RSCRIPT") or shutil.which("Rscript")


def _r_package_available(rscript: str, package: str | None) -> tuple[bool, str]:
    if not package:
        return True, "no package probe requested"
    probe = subprocess.run(
        [
            rscript,
            "--vanilla",
            "-e",
            f"ok <- requireNamespace('{package}', quietly=TRUE); cat(if (ok) 'TRUE' else 'FALSE'); quit(status=if (ok) 0 else 11)",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if probe.returncode == 0 and "TRUE" in probe.stdout:
        return True, f"R package available: {package}"
    return False, (probe.stderr.strip() or probe.stdout.strip() or f"R package unavailable: {package}")


def render_r_plan(*, adapter: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    rscript = _rscript_path()
    status = "interface_only_until_r_smoke"
    message = "Rscript not found on PATH."
    if rscript:
        package_ok, message = _r_package_available(rscript, adapter.get("r_package"))
        status = "ready_for_rscript" if package_ok else "interface_only_until_r_smoke"
    return {
        "adapter": adapter["name"],
        "backend": adapter["backend"],
        "engine": "r",
        "r_package": adapter.get("r_package"),
        "rscript": rscript,
        "status": status,
        "message": message,
        "spec": spec,
        "no_fallback_substitution": True,
    }


def skipped(adapter: dict[str, Any], *, design_type: str, message: str) -> dict[str, Any]:
    return skipped_backend_unavailable(
        estimator=adapter["name"],
        design_type=design_type,
        backend=adapter["backend"],
        message=message,
    )


def parse_r_json_result(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "failed",
            "risk_code": "BACKEND_RESULT_MISSING",
            "error": f"R backend did not write expected JSON result: {path}",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "failed",
            "risk_code": "BACKEND_PARSE_FAILED",
            "error": str(exc),
            "error_type": exc.__class__.__name__,
        }
    if not isinstance(payload, dict):
        return {
            "status": "failed",
            "risk_code": "BACKEND_INVALID_RESULT",
            "error": "R backend JSON result must be an object.",
        }
    return payload


def run_r_json(
    *,
    ctx: RunContext,
    adapter: dict[str, Any],
    script_body: str,
    timeout: int = 300,
) -> dict[str, Any]:
    rscript = _rscript_path()
    backend_status = {
        "backend": adapter["backend"],
        "adapter": adapter["name"],
        "r_package": adapter.get("r_package"),
        "available": False,
        "status": "backend_unavailable",
    }
    if not rscript:
        backend_status["message"] = "Rscript not found on PATH."
        write_json(ctx.artifact("r_backend_status.json"), backend_status)
        return {"status": "interface_only_until_r_smoke", "reason": backend_status["message"], "backend_status": backend_status}
    package_ok, package_message = _r_package_available(rscript, adapter.get("r_package"))
    if not package_ok:
        backend_status["executable"] = rscript
        backend_status["message"] = package_message
        write_json(ctx.artifact("r_backend_status.json"), backend_status)
        return {"status": "interface_only_until_r_smoke", "reason": package_message, "backend_status": backend_status}

    backend_status.update({"available": True, "status": "ready", "executable": rscript, "message": package_message})
    write_json(ctx.artifact("r_backend_status.json"), backend_status)
    spec_path = ctx.artifact("r_spec.json")
    result_path = ctx.artifact("r_result.json")
    script_path = ctx.artifact("r_script.R")
    write_json(spec_path, ctx.spec)
    script = f"""
options(warn=1)
args <- commandArgs(trailingOnly=TRUE)
spec_path <- args[[1]]
result_path <- args[[2]]
if (!requireNamespace("jsonlite", quietly=TRUE)) {{
  stop("R package jsonlite is required for skill4econ R adapters")
}}
spec <- jsonlite::fromJSON(spec_path, simplifyVector=FALSE)
{script_body}
"""
    script_path.write_text(script, encoding="utf-8")
    rc = run_subprocess(
        [rscript, "--vanilla", str(script_path), str(spec_path), str(result_path)],
        cwd=ctx.run_dir,
        timeout=timeout,
        stdout_path=ctx.artifact("r_stdout.log"),
        stderr_path=ctx.artifact("r_stderr.log"),
    )
    payload = parse_r_json_result(result_path)
    payload.setdefault("returncode", rc)
    if rc != 0 and payload.get("status") != "ok":
        payload.setdefault("status", "failed")
        payload.setdefault("risk_code", "BACKEND_ERROR")
        payload.setdefault("error", f"Rscript exited with code {rc}")
    return payload
