from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ..config import resolve_stata, resolve_stata_batch_args


def check_python_package(package: str, import_name: str | None = None) -> dict[str, Any]:
    target = import_name or package
    try:
        module = importlib.import_module(target)
        return {
            "backend": "python",
            "package": package,
            "import": target,
            "available": True,
            "version": getattr(module, "__version__", "unknown"),
        }
    except Exception as exc:
        return {
            "backend": "python",
            "package": package,
            "import": target,
            "available": False,
            "error": exc.__class__.__name__,
            "message": str(exc),
        }


def check_rscript() -> dict[str, Any]:
    exe = shutil.which("Rscript")
    if not exe:
        return {"backend": "r", "available": False, "executable": None, "message": "Rscript not found on PATH."}
    proc = subprocess.run(
        [exe, "--version"],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    version = (proc.stderr or proc.stdout).strip().splitlines()
    return {
        "backend": "r",
        "available": proc.returncode == 0,
        "executable": exe,
        "version": version[0] if version else "unknown",
    }


def check_r_package(package: str) -> dict[str, Any]:
    r = check_rscript()
    if not r.get("available"):
        return {**r, "package": package}
    exe = str(r["executable"])
    expr = f"if (!requireNamespace('{package}', quietly=TRUE)) quit(status=42); cat(as.character(packageVersion('{package}')))"
    proc = subprocess.run(
        [exe, "-e", expr],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    return {
        "backend": "r",
        "package": package,
        "available": proc.returncode == 0,
        "version": proc.stdout.strip() if proc.returncode == 0 else None,
        "message": proc.stderr.strip() if proc.returncode else "",
    }


def check_stata(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    executable, source = resolve_stata(spec)
    return {
        "backend": "stata",
        "available": executable is not None,
        "executable": str(executable) if executable else None,
        "source": source,
    }


def check_stata_package(command: str, spec: dict[str, Any] | None = None) -> dict[str, Any]:
    stata = check_stata(spec)
    if not stata.get("available"):
        return {**stata, "package": command, "message": "Stata executable unavailable."}
    exe = Path(str(stata["executable"]))
    with tempfile.TemporaryDirectory(prefix="skill4econ_stata_check_") as tmp:
        tmp_path = Path(tmp)
        do_file = tmp_path / "check.do"
        log_file = tmp_path / "check.log"
        do_file.write_text(
            "\n".join(
                [
                    "version 17",
                    "set more off",
                    f'log using "{log_file.as_posix()}", replace text',
                    f"capture which {command}",
                    "local rc = _rc",
                    "log close",
                    "exit `rc'",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        cmd = [str(exe), *resolve_stata_batch_args(exe, spec), str(do_file)]
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=60)
        return {
            "backend": "stata",
            "package": command,
            "available": proc.returncode == 0,
            "executable": str(exe),
            "returncode": proc.returncode,
            "log": log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else "",
        }


def check_backends(
    *,
    spec: dict[str, Any] | None = None,
    python_packages: dict[str, str] | None = None,
    stata_packages: list[str] | None = None,
    r_packages: list[str] | None = None,
    run_external_package_checks: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "stata": check_stata(spec),
        "r": check_rscript(),
        "python": {"available": True, "packages": {}},
    }
    for package, import_name in (python_packages or {}).items():
        report["python"]["packages"][package] = check_python_package(package, import_name)
    report["stata"]["packages"] = {}
    if run_external_package_checks:
        for package in stata_packages or []:
            report["stata"]["packages"][package] = check_stata_package(package, spec)
    else:
        for package in stata_packages or []:
            report["stata"]["packages"][package] = "not_checked"
    report["r"]["packages"] = {}
    if run_external_package_checks:
        for package in r_packages or []:
            report["r"]["packages"][package] = check_r_package(package)
    else:
        for package in r_packages or []:
            report["r"]["packages"][package] = "not_checked"
    return report


def write_backend_status(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
