from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable, Sequence


BACKEND_CONTRACT_VERSION = "heavy-backend-contract-v0.1"

BACKEND_RUN_STATUS_VALUES = {
    "ok",
    "known_gap",
    "missing_dependency",
    "backend_unavailable",
    "backend_error",
    "backend_timeout",
    "result_missing",
    "parser_only",
    "parser_error",
    "invalid_result",
    "invalid_spec",
    "unsupported",
}

BACKEND_CAPABILITY_REGISTRY: dict[str, dict[str, Any]] = {
    "r_spatialreg": {
        "language": "r",
        "packages": ["spatialreg", "spdep"],
        "methods": ["SAR", "SEM", "SDM"],
        "required_outputs": ["direct", "indirect", "total"],
        "claim_level_when_live": "supplementary_only_until_certified",
    },
    "r_splm": {
        "language": "r",
        "packages": ["splm", "spdep"],
        "methods": ["spatial_panel"],
        "required_outputs": ["direct", "indirect", "total"],
        "claim_level_when_live": "supplementary_only_until_certified",
    },
    "r_spdep": {
        "language": "r",
        "packages": ["spdep"],
        "methods": ["moran", "local_moran"],
        "required_outputs": ["global_moran", "local_moran"],
        "claim_level_when_live": "diagnostic",
    },
    "stata_xsmle": {
        "language": "stata",
        "packages": ["xsmle"],
        "methods": ["SAR", "SEM", "SDM", "spatial_panel"],
        "required_outputs": ["direct", "indirect", "total"],
        "claim_level_when_live": "supplementary_only_until_certified",
    },
    "stata_spxtregress": {
        "language": "stata",
        "packages": ["spxtregress"],
        "methods": ["SAR", "SEM", "SDM", "spatial_panel"],
        "required_outputs": ["direct", "indirect", "total"],
        "claim_level_when_live": "supplementary_only_until_certified",
    },
    "stata_ppmlhdfe": {
        "language": "stata",
        "packages": ["ppmlhdfe", "reghdfe", "ftools"],
        "methods": ["ppml_high_dimensional_fe"],
        "required_outputs": ["coef_table", "convergence", "se"],
        "claim_level_when_live": "supplementary_only_until_certified",
    },
}


def _tail(value: str | None, limit: int = 4000) -> str:
    return (value or "")[-limit:]


def canonical_backend_result(
    *,
    backend: str,
    status: str,
    adapter: str | None = None,
    available: bool | None = None,
    message: str | None = None,
    error_code: str | None = None,
    returncode: int | None = None,
    command: Sequence[str] | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    expected_outputs: Sequence[str | Path] | None = None,
    missing_outputs: Sequence[str | Path] | None = None,
    elapsed_seconds: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in BACKEND_RUN_STATUS_VALUES:
        status = "invalid_result"
        error_code = error_code or "BACKEND_INVALID_RESULT"
    payload: dict[str, Any] = {
        "contract_version": BACKEND_CONTRACT_VERSION,
        "backend": backend,
        "adapter": adapter or backend,
        "status": status,
        "backend_run_status": status,
        "available": bool(available) if available is not None else status == "ok",
        "error_code": error_code,
        "message": message or "",
        "fallback_used": False,
    }
    if returncode is not None:
        payload["returncode"] = returncode
    if command is not None:
        payload["command"] = [str(item) for item in command]
    if stdout is not None:
        payload["stdout_tail"] = _tail(stdout)
    if stderr is not None:
        payload["stderr_tail"] = _tail(stderr)
    if expected_outputs is not None:
        payload["expected_outputs"] = [str(item) for item in expected_outputs]
    if missing_outputs is not None:
        payload["missing_outputs"] = [str(item) for item in missing_outputs]
    if elapsed_seconds is not None:
        payload["elapsed_seconds"] = round(float(elapsed_seconds), 3)
    if extra:
        payload.update(extra)
    return payload


def write_canonical_backend_result(path: str | Path, result: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def probe_r_backend(
    packages: Iterable[str],
    *,
    executable: str | Path | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    package_list = [str(item) for item in packages if str(item)]
    rscript = str(executable or os.environ.get("SKILL4ECON_RSCRIPT") or shutil.which("Rscript") or "")
    if not rscript:
        return canonical_backend_result(
            backend="r",
            status="backend_unavailable",
            available=False,
            error_code="R_BACKEND_UNAVAILABLE",
            message="Rscript not found on PATH. No R spatial backend was run.",
            extra={"missing_dependencies": ["Rscript"], "missing_packages": package_list},
        )
    if not package_list:
        return canonical_backend_result(
            backend="r",
            status="ok",
            available=True,
            message="Rscript executable found; no package probe requested.",
            extra={"executable": rscript, "packages": []},
        )
    quoted = ", ".join(json.dumps(item) for item in package_list)
    expr = (
        f"packages <- c({quoted}); "
        "missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly=TRUE)]; "
        "if (length(missing)) { cat(paste(missing, collapse=',')); quit(status=42) }; "
        "cat('ok')"
    )
    command = [rscript, "-e", expr]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return canonical_backend_result(
            backend="r",
            status="backend_timeout",
            available=True,
            error_code="BACKEND_TIMEOUT",
            message=f"R package probe exceeded {timeout} seconds.",
            command=command,
            stdout=exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout,
            stderr=exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr,
            elapsed_seconds=time.perf_counter() - start,
            extra={"executable": rscript, "packages": package_list},
        )
    elapsed = time.perf_counter() - start
    if proc.returncode == 0:
        return canonical_backend_result(
            backend="r",
            status="ok",
            available=True,
            message="R packages are importable.",
            command=command,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            elapsed_seconds=elapsed,
            extra={"executable": rscript, "packages": package_list},
        )
    missing_text = (proc.stdout or "").strip()
    missing_packages = [item.strip() for item in missing_text.split(",") if item.strip()] or package_list
    return canonical_backend_result(
        backend="r",
        status="missing_dependency",
        available=False,
        error_code="BACKEND_MISSING_DEPENDENCY",
        message="One or more required R packages are not importable.",
        command=command,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        elapsed_seconds=elapsed,
        extra={"executable": rscript, "packages": package_list, "missing_packages": missing_packages},
    )


def run_backend_command(
    command: Sequence[str | Path],
    *,
    expected_outputs: Sequence[str | Path] | None = None,
    cwd: str | Path | None = None,
    timeout: float = 60,
    backend: str = "external_backend",
    adapter: str | None = None,
) -> dict[str, Any]:
    cmd = [str(item) for item in command]
    base = Path(cwd).resolve() if cwd else None
    expected = [Path(item) for item in (expected_outputs or [])]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(base) if base else None,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return canonical_backend_result(
            backend=backend,
            adapter=adapter,
            status="backend_timeout",
            available=True,
            error_code="BACKEND_TIMEOUT",
            message=f"Backend command exceeded {timeout} seconds.",
            command=cmd,
            stdout=exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout,
            stderr=exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr,
            expected_outputs=expected,
            elapsed_seconds=time.perf_counter() - start,
        )
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        return canonical_backend_result(
            backend=backend,
            adapter=adapter,
            status="backend_error",
            available=True,
            error_code="BACKEND_ERROR",
            message="Backend command returned a non-zero exit code.",
            command=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            expected_outputs=expected,
            elapsed_seconds=elapsed,
        )
    missing = []
    for path in expected:
        resolved = path if path.is_absolute() else (base / path if base else Path.cwd() / path)
        if not resolved.exists():
            missing.append(path)
    if missing:
        return canonical_backend_result(
            backend=backend,
            adapter=adapter,
            status="result_missing",
            available=True,
            error_code="BACKEND_RESULT_MISSING",
            message="Backend exited successfully but did not write required output files.",
            command=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            expected_outputs=expected,
            missing_outputs=missing,
            elapsed_seconds=elapsed,
        )
    return canonical_backend_result(
        backend=backend,
        adapter=adapter,
        status="ok",
        available=True,
        message="Backend command completed and required outputs exist.",
        command=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        expected_outputs=expected,
        elapsed_seconds=elapsed,
    )


def _rows_from_csv(path: str | Path) -> tuple[list[dict[str, Any]], list[str]]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def validate_spatial_impacts_table(rows_or_path: Sequence[dict[str, Any]] | str | Path) -> dict[str, Any]:
    if isinstance(rows_or_path, (str, Path)):
        rows, columns = _rows_from_csv(rows_or_path)
    else:
        rows = [dict(item) for item in rows_or_path]
        columns = sorted({str(key) for row in rows for key in row})
    lower = {str(col).lower(): str(col) for col in columns}
    if not rows:
        return canonical_backend_result(
            backend="impact_parser",
            status="invalid_result",
            available=False,
            error_code="BACKEND_PARSE_FAILED",
            message="Impact decomposition table is empty.",
        )
    wide_components = {
        "direct": lower.get("direct") or lower.get("direct_effect"),
        "indirect": lower.get("indirect") or lower.get("indirect_effect"),
        "total": lower.get("total") or lower.get("total_effect"),
    }
    missing_wide = [name for name, col in wide_components.items() if col is None]
    if not missing_wide:
        return canonical_backend_result(
            backend="impact_parser",
            status="ok",
            available=True,
            message="Impact decomposition includes direct, indirect, and total effects.",
            extra={"impact_components": ["direct", "indirect", "total"], "row_count": len(rows)},
        )
    type_col = lower.get("impact_type") or lower.get("effect_type") or lower.get("component")
    if type_col:
        observed = {str(row.get(type_col, "")).strip().lower() for row in rows}
        missing_long = sorted({"direct", "indirect", "total"} - observed)
        if not missing_long:
            return canonical_backend_result(
                backend="impact_parser",
                status="ok",
                available=True,
                message="Long-form impact decomposition includes direct, indirect, and total effects.",
                extra={"impact_components": ["direct", "indirect", "total"], "row_count": len(rows)},
            )
    return canonical_backend_result(
        backend="impact_parser",
        status="invalid_result",
        available=False,
        error_code="SDM_IMPACTS_MISSING",
        message="Spatial model output lacks a complete direct/indirect/total impact decomposition.",
        extra={"missing_components": missing_wide, "columns": columns, "row_count": len(rows)},
    )
