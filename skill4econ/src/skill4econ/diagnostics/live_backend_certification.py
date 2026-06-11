from __future__ import annotations

import csv
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

from ..adapters.heavy_backend_contract import (
    canonical_backend_result,
    probe_r_backend,
    validate_spatial_impacts_table,
    write_canonical_backend_result,
)
from ..config import resolve_stata, resolve_stata_batch_args
from ..contracts.stata_safety import validate_stata_spec
from ..core import REPO_ROOT, listify
from ..stata_wrappers import _vendor_adopath_block


def _as_path(value: Any, base: Path) -> Path:
    path = Path(str(value))
    if not path.is_absolute():
        path = base / path
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row}) or ["note"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def _quote(path: Path) -> str:
    return str(path).replace("\\", "/")


def materialize_live_fixture(output_dir: Path, spec: dict[str, Any] | None = None) -> Path:
    """Create a small balanced panel with stable coordinates for live backend certification."""

    spec = spec or {}
    n_units = max(6, int(spec.get("cert_units", 12)))
    n_years = max(3, int(spec.get("cert_years", 4)))
    start_year = int(spec.get("cert_start_year", 2019))
    path = output_dir / "fixtures" / "live_spatial_panel.csv"
    rows: list[dict[str, Any]] = []
    grid_width = max(3, int(math.ceil(math.sqrt(n_units))))
    for unit in range(1, n_units + 1):
        col = (unit - 1) % grid_width
        row = (unit - 1) // grid_width
        lon = float(col + 0.07 * (unit % 3))
        lat = float(row + 0.05 * ((unit + 1) % 4))
        unit_fe = ((unit % 5) - 2) * 0.12
        for offset in range(n_years):
            year = start_year + offset
            trend = float(offset)
            noise = (((unit * 13 + year * 17) % 23) - 11) / 90
            x1 = 0.25 * math.sin(unit / 2) + 0.08 * trend + ((unit * 7 + year) % 11) / 40
            x2 = 0.18 * math.cos(unit / 3) - 0.05 * trend + ((unit * 5 + year * 3) % 13) / 55
            spatial_signal = 0.14 * (1 if unit in {2, 3, 7, 8, 11, 12} else 0)
            y = 1.2 + unit_fe + 0.11 * trend + 0.38 * x1 - 0.18 * x2 + spatial_signal + noise
            count_y = max(0.2, 2.0 + y + 0.04 * unit + (((unit + year) % 5) / 20))
            rows.append(
                {
                    "unit_id": unit,
                    "year": year,
                    "y": round(y, 6),
                    "count_y": round(count_y, 6),
                    "x1": round(x1, 6),
                    "x2": round(x2, 6),
                    "lon": round(lon, 6),
                    "lat": round(lat, 6),
                }
            )
    _write_csv(
        path,
        rows,
        ["unit_id", "year", "y", "count_y", "x1", "x2", "lon", "lat"],
    )
    return path


def _coefficient_export_block(target: Path) -> str:
    return f"""
tempname b V
matrix `b' = e(b)
matrix `V' = e(V)
local names : colnames `b'
local k = colsof(`b')
preserve
clear
set obs `k'
gen str128 term = ""
gen double coef = .
gen double std_error = .
gen double z_stat = .
gen double p_value = .
forvalues i = 1/`k' {{
    local nm : word `i' of `names'
    replace term = "`nm'" in `i'
    replace coef = `b'[1,`i'] in `i'
    replace std_error = sqrt(`V'[`i',`i']) in `i'
    replace z_stat = coef[`i'] / std_error[`i'] in `i'
    replace p_value = 2 * normal(-abs(z_stat[`i'])) in `i'
}}
export delimited using "{_quote(target)}", replace
restore
"""


def _run_stata_do(
    spec: dict[str, Any],
    output_dir: Path,
    *,
    name: str,
    do_text: str,
    timeout: int,
) -> dict[str, Any]:
    executable, source = resolve_stata(spec)
    scripts = output_dir / "scripts"
    logs = output_dir / "logs"
    scripts.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    do_path = scripts / f"{name}.do"
    stdout_path = logs / f"{name}.stdout.log"
    stderr_path = logs / f"{name}.stderr.log"
    do_path.write_text(do_text, encoding="utf-8")
    if executable is None:
        return canonical_backend_result(
            backend="stata",
            adapter=name,
            status="backend_unavailable",
            available=False,
            error_code="BACKEND_UNAVAILABLE",
            message="Stata executable is not available.",
            extra={"stata_source": source, "do_file": str(do_path)},
        )
    cmd = [str(executable), *resolve_stata_batch_args(executable, spec), str(do_path)]
    try:
        with stdout_path.open("w", encoding="utf-8", errors="replace") as out, stderr_path.open(
            "w", encoding="utf-8", errors="replace"
        ) as err:
            proc = subprocess.run(
                cmd,
                cwd=str(output_dir),
                stdout=out,
                stderr=err,
                text=True,
                timeout=timeout,
                check=False,
            )
            rc = int(proc.returncode)
    except subprocess.TimeoutExpired:
        rc = 124
    log_path = output_dir / f"{name}.log"
    if rc == 0 and log_path.exists():
        text = log_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\nr\(\d+\);", text):
            rc = 1
    status = "ok" if rc == 0 else ("backend_timeout" if rc == 124 else "backend_error")
    return canonical_backend_result(
        backend="stata",
        adapter=name,
        status=status,
        available=True,
        error_code=None if rc == 0 else ("BACKEND_TIMEOUT" if rc == 124 else "BACKEND_ERROR"),
        message="Stata batch completed." if rc == 0 else "Stata batch failed; inspect logs.",
        command=cmd,
        returncode=rc,
        extra={
            "do_file": str(do_path),
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
            "stata_log": str(log_path) if log_path.exists() else None,
            "stata_source": source,
            "executable": str(executable),
        },
    )


def _stata_command_available(spec: dict[str, Any], output_dir: Path, command: str) -> dict[str, Any]:
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{command}_which.log", replace text
capture which {command}
local rc = _rc
display "{command}_rc=" `rc'
log close
exit `rc'
"""
    result = _run_stata_do(spec, output_dir, name=f"which_{command}", do_text=do_text, timeout=60)
    if result.get("status") == "backend_error":
        result["status"] = "missing_dependency"
        result["backend_run_status"] = "missing_dependency"
        result["available"] = False
        result["error_code"] = "BACKEND_MISSING_DEPENDENCY"
        result["message"] = f"Stata command {command} is not available."
    result["command_name"] = command
    return result


def parse_estat_impact_log(log_text: str, variables: list[str], *, model: str, w_name: str) -> list[dict[str, Any]]:
    sections = {"direct", "indirect", "total"}
    current: str | None = None
    values: dict[str, dict[str, dict[str, float]]] = {}
    varset = set(variables)
    number_re = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
    for line in log_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        first = stripped.split()[0].lower().rstrip("|") if stripped.split() else ""
        if first in sections:
            current = first
            continue
        if current is None or "|" not in line:
            continue
        lhs, rhs = line.split("|", 1)
        term = lhs.strip()
        if term not in varset:
            continue
        nums = number_re.findall(rhs)
        if len(nums) < 4:
            continue
        values.setdefault(term, {})[current] = {
            "estimate": float(nums[0]),
            "std_error": float(nums[1]),
            "z_stat": float(nums[2]),
            "p_value": float(nums[3]),
        }
    rows: list[dict[str, Any]] = []
    for term, by_section in sorted(values.items()):
        if not {"direct", "indirect", "total"}.issubset(by_section):
            continue
        row: dict[str, Any] = {
            "backend": "stata_spxtregress",
            "model": model,
            "w_name": w_name,
            "effect": term,
            "direct": by_section["direct"]["estimate"],
            "indirect": by_section["indirect"]["estimate"],
            "total": by_section["total"]["estimate"],
            "direct_std_error": by_section["direct"]["std_error"],
            "indirect_std_error": by_section["indirect"]["std_error"],
            "total_std_error": by_section["total"]["std_error"],
            "direct_p_value": by_section["direct"]["p_value"],
            "indirect_p_value": by_section["indirect"]["p_value"],
            "total_p_value": by_section["total"]["p_value"],
        }
        rows.append(row)
    return rows


def _spxtregress_options(model: str, w_name: str, covariates: list[str], spec: dict[str, Any]) -> str:
    xlist = " ".join(covariates)
    panel_effect = str(spec.get("spxtregress_panel_effect") or "fe").strip().lower()
    if panel_effect not in {"fe", "re"}:
        raise ValueError("spxtregress_panel_effect must be either 'fe' or 're'.")
    extras = listify(spec.get("spxtregress_extra_options") or [])
    if "spxtregress_iterate" in spec:
        extras.append(f"iterate({int(spec['spxtregress_iterate'])})")
    suffix = " ".join(str(item).strip() for item in extras if str(item).strip())
    suffix = f" {suffix}" if suffix else ""
    if model == "SAR":
        return f"{panel_effect} dvarlag({w_name}){suffix}"
    if model == "SEM":
        return f"{panel_effect} errorlag({w_name}){suffix}"
    if model == "SDM":
        return f"{panel_effect} dvarlag({w_name}) ivarlag({w_name}: {xlist}){suffix}"
    raise ValueError(f"Unknown spatial model: {model}")


def run_stata_spxtregress_live_matrix(
    spec: dict[str, Any],
    output_dir: Path,
    data_path: Path,
) -> dict[str, Any]:
    tables = output_dir / "tables"
    w_grid = spec.get("w_grid") or [
        {"name": "W_row", "options": "normalize(row)"},
        {"name": "W_minmax", "options": "normalize(minmax)"},
        {"name": "W_trunc_row", "options": "vtruncate(0.25) normalize(row)"},
    ]
    models = [str(item).upper() for item in (spec.get("spatial_models") or ["SAR", "SEM", "SDM"])]
    id_col = str(spec.get("id") or "unit_id")
    time_col = str(spec.get("time") or "year")
    y = str(spec.get("y") or "y")
    covariates = listify(spec.get("x") or ["x1", "x2"])
    lon = str(spec.get("lon") or "lon")
    lat = str(spec.get("lat") or "lat")
    command_status = _stata_command_available(spec, output_dir, "spxtregress")
    matrix_rows: list[dict[str, Any]] = []
    impact_rows: list[dict[str, Any]] = []
    coef_sources: list[str] = []
    if command_status.get("status") != "ok":
        _write_csv(tables / "stata_spxtregress_live_matrix.csv", [])
        return {"status": "missing_dependency", "command_status": command_status, "matrix_rows": [], "impact_rows": []}

    for w_spec in w_grid:
        w_name = str(w_spec.get("name") or "W")
        w_options = str(w_spec.get("options") or "normalize(row)")
        for model in models:
            model_options = _spxtregress_options(model, w_name, covariates, spec)
            safe_name = f"spxtregress_{w_name}_{model}".lower()
            coef_path = tables / f"{safe_name}_coefficients.csv"
            do_text = f"""
version 17
set more off
import delimited using "{_quote(data_path)}", clear varnames(1)
xtset {id_col} {time_col}
spset {id_col}, coord({lon} {lat})
quietly summarize {time_col}, meanonly
local __s4e_first_time = r(min)
spmatrix create idistance {w_name} if {time_col} == `__s4e_first_time', {w_options} replace
spmatrix summarize {w_name}
capture noisily spxtregress {y} {" ".join(covariates)}, {model_options} force
local model_rc = _rc
display "skill4econ_model_rc=" `model_rc'
if `model_rc' == 0 {{
{_coefficient_export_block(coef_path)}
    capture noisily estat impact {" ".join(covariates)}, nolog
    local impact_rc = _rc
    display "skill4econ_impact_rc=" `impact_rc'
}}
exit `model_rc'
"""
            result = _run_stata_do(spec, output_dir, name=safe_name, do_text=do_text, timeout=int(spec.get("spxtregress_timeout", 240)))
            log_path_value = result.get("stata_log")
            log_path = Path(str(log_path_value)) if log_path_value else output_dir / f"{safe_name}.log"
            impacts: list[dict[str, Any]] = []
            if log_path.exists():
                impacts = parse_estat_impact_log(
                    log_path.read_text(encoding="utf-8", errors="replace"),
                    covariates,
                    model=model,
                    w_name=w_name,
                )
            has_coef = coef_path.exists()
            if has_coef:
                coef_sources.append(str(coef_path))
            requires_impact = model in {"SAR", "SDM"}
            status = str(result.get("status"))
            if status == "ok" and requires_impact and not impacts:
                status = "result_missing"
                result["status"] = status
                result["backend_run_status"] = status
                result["error_code"] = "SDM_IMPACTS_MISSING" if model == "SDM" else "BACKEND_RESULT_MISSING"
                result["message"] = "Model ran but estat impact did not yield a complete direct/indirect/total table."
            matrix_rows.append(
                {
                    "backend": "stata_spxtregress",
                    "model": model,
                    "w_name": w_name,
                    "w_options": w_options,
                    "model_options": model_options,
                    "status": status,
                    "returncode": result.get("returncode"),
                    "has_coefficients": has_coef,
                    "has_impact_decomposition": bool(impacts),
                    "coefficient_path": str(coef_path) if has_coef else "",
                    "stata_log": str(log_path) if log_path.exists() else "",
                    "error_code": result.get("error_code"),
                    "message": result.get("message"),
                }
            )
            impact_rows.extend(impacts)
            write_canonical_backend_result(output_dir / "backend_results" / f"{safe_name}.json", result)
    _write_csv(tables / "stata_spxtregress_live_matrix.csv", matrix_rows)
    _write_csv(tables / "stata_spxtregress_live_impacts.csv", impact_rows)
    impact_validation = validate_spatial_impacts_table(impact_rows) if impact_rows else canonical_backend_result(
        backend="stata_spxtregress",
        status="result_missing",
        available=True,
        error_code="BACKEND_RESULT_MISSING",
        message="No complete estat impact rows were parsed from the live spxtregress matrix.",
    )
    return {
        "status": "ok" if any(row["status"] == "ok" for row in matrix_rows) else "failed",
        "command_status": command_status,
        "matrix_rows": matrix_rows,
        "impact_rows": impact_rows,
        "impact_validation": impact_validation,
        "coefficient_sources": coef_sources,
        "artifacts": {
            "matrix": "tables/stata_spxtregress_live_matrix.csv",
            "impacts": "tables/stata_spxtregress_live_impacts.csv",
        },
    }


def run_stata_ppmlhdfe_live_certification(spec: dict[str, Any], output_dir: Path, data_path: Path) -> dict[str, Any]:
    tables = output_dir / "tables"
    id_col = str(spec.get("id") or "unit_id")
    time_col = str(spec.get("time") or "year")
    y = str(spec.get("ppml_y") or "count_y")
    covariates = listify(spec.get("ppml_x") or spec.get("x") or ["x1", "x2"])
    coef_path = tables / "ppmlhdfe_live_coefficients.csv"
    command_status = _stata_command_available(spec, output_dir, "ppmlhdfe")
    if command_status.get("status") != "ok":
        return {"status": "missing_dependency", "command_status": command_status, "rows": []}
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
import delimited using "{_quote(data_path)}", clear varnames(1)
which ppmlhdfe
capture noisily ppmlhdfe {y} {" ".join(covariates)}, absorb({id_col} {time_col}) vce(cluster {id_col})
local model_rc = _rc
display "skill4econ_ppmlhdfe_rc=" `model_rc'
if `model_rc' == 0 {{
{_coefficient_export_block(coef_path)}
}}
exit `model_rc'
"""
    result = _run_stata_do(spec, output_dir, name="ppmlhdfe_live", do_text=do_text, timeout=int(spec.get("ppmlhdfe_timeout", 300)))
    status = str(result.get("status"))
    if status == "ok" and not coef_path.exists():
        status = "result_missing"
        result["status"] = status
        result["backend_run_status"] = status
        result["error_code"] = "BACKEND_RESULT_MISSING"
        result["message"] = "ppmlhdfe ran but coefficient output was not written."
    row = {
        "backend": "stata_ppmlhdfe",
        "model": "PPMLHDFE",
        "status": status,
        "returncode": result.get("returncode"),
        "has_coefficients": coef_path.exists(),
        "coefficient_path": str(coef_path) if coef_path.exists() else "",
        "stata_log": result.get("stata_log") or "",
        "error_code": result.get("error_code"),
        "message": result.get("message"),
        "fallback_used": False,
    }
    _write_csv(tables / "ppmlhdfe_live_certification.csv", [row])
    write_canonical_backend_result(output_dir / "backend_results" / "ppmlhdfe_live.json", result)
    return {
        "status": status,
        "command_status": command_status,
        "rows": [row],
        "artifacts": {"certification": "tables/ppmlhdfe_live_certification.csv"},
    }


def run_r_backend_live_probes(spec: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    packages = {
        "r_spdep": ["spdep"],
        "r_splm": ["splm", "spdep"],
        "r_spatialreg": ["spatialreg", "spdep"],
    }
    rows = []
    results: dict[str, Any] = {}
    for backend, package_list in packages.items():
        result = probe_r_backend(package_list, timeout=float(spec.get("r_probe_timeout", 30)))
        result["backend"] = backend
        results[backend] = result
        rows.append(
            {
                "backend": backend,
                "status": result.get("status"),
                "available": result.get("available"),
                "missing_packages": ",".join(map(str, result.get("missing_packages") or result.get("missing_dependencies") or [])),
                "error_code": result.get("error_code"),
                "message": result.get("message"),
            }
        )
        write_canonical_backend_result(output_dir / "backend_results" / f"{backend}.json", result)
    _write_csv(output_dir / "tables" / "r_live_backend_probes.csv", rows)
    return {"status": "ok" if any(row["status"] == "ok" for row in rows) else "missing_dependency", "rows": rows, "results": results}


def run_live_backend_certification(
    spec: dict[str, Any],
    output_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    validate_stata_spec(spec)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)
    (out / "backend_results").mkdir(exist_ok=True)
    base = Path(repo_root or REPO_ROOT)
    data_value = spec.get("data")
    data_path = _as_path(data_value, base) if data_value else materialize_live_fixture(out, spec)
    if not data_path.exists():
        raise ValueError(f"live_backend_certification data not found: {data_path}")

    r_result = run_r_backend_live_probes(spec, out)
    xsmle_status = _stata_command_available(spec, out, "xsmle")
    spxt_result = run_stata_spxtregress_live_matrix(spec, out, data_path) if spec.get("run_spxtregress", True) else {"status": "skipped", "matrix_rows": [], "impact_rows": []}
    ppml_result = run_stata_ppmlhdfe_live_certification(spec, out, data_path) if spec.get("run_ppmlhdfe", True) else {"status": "skipped", "rows": []}

    summary_rows: list[dict[str, Any]] = []
    for row in r_result.get("rows") or []:
        summary_rows.append({**row, "family": "r_live_probe"})
    summary_rows.append(
        {
            "family": "stata_live_probe",
            "backend": "stata_xsmle",
            "status": xsmle_status.get("status"),
            "available": xsmle_status.get("available"),
            "missing_packages": "xsmle" if xsmle_status.get("status") != "ok" else "",
            "error_code": xsmle_status.get("error_code"),
            "message": xsmle_status.get("message"),
        }
    )
    for row in spxt_result.get("matrix_rows") or []:
        summary_rows.append({**row, "family": "stata_spxtregress_matrix"})
    for row in ppml_result.get("rows") or []:
        summary_rows.append({**row, "family": "stata_ppmlhdfe"})
    _write_csv(out / "tables" / "live_backend_certification_matrix.csv", summary_rows)
    _write_csv(
        out / "model_table.csv",
        [
            {
                "backend": row.get("backend"),
                "model": row.get("model") or row.get("family"),
                "w_name": row.get("w_name", ""),
                "status": row.get("status"),
                "term": "",
                "note": row.get("message", ""),
                "source_path": row.get("coefficient_path") or row.get("stata_log") or "",
            }
            for row in summary_rows
        ],
        ["backend", "model", "w_name", "status", "term", "note", "source_path"],
    )

    warnings: list[dict[str, Any]] = []
    for row in summary_rows:
        status = str(row.get("status"))
        if status in {"ok", "parser_only"}:
            continue
        code = str(row.get("error_code") or ("PPMLHDFE_MISSING" if row.get("backend") == "stata_ppmlhdfe" else "BACKEND_MISSING_DEPENDENCY"))
        if code == "R_BACKEND_UNAVAILABLE":
            code = "BACKEND_UNAVAILABLE"
        warnings.append(
            {
                "severity": "yellow" if status in {"missing_dependency", "backend_unavailable", "skipped"} else "red",
                "code": code,
                "message": f"{row.get('backend')} certification status: {status}. {row.get('message') or ''}".strip(),
                "action": "Install/configure the backend or inspect live certification logs before making live backend claims.",
                "affected_artifacts": ["tables/live_backend_certification_matrix.csv"],
            }
        )
    sdm_ok = any(
        row.get("backend") == "stata_spxtregress"
        and row.get("model") == "SDM"
        and row.get("status") == "ok"
        and row.get("has_impact_decomposition")
        for row in spxt_result.get("matrix_rows") or []
    )
    if not sdm_ok:
        warnings.append(
            {
                "severity": "red",
                "code": "SDM_IMPACTS_MISSING",
                "message": "No live SDM run produced a complete direct/indirect/total impact decomposition.",
                "action": "Do not report SDM indirect effects until the live impact artifact is present.",
                "affected_artifacts": ["tables/stata_spxtregress_live_impacts.csv"],
            }
        )

    status = "ok" if any(str(row.get("status")) == "ok" for row in summary_rows) else "missing_dependency"
    payload = {
        "status": status,
        "data": str(data_path),
        "r_backends": r_result,
        "stata_xsmle": xsmle_status,
        "stata_spxtregress": spxt_result,
        "stata_ppmlhdfe": ppml_result,
        "sdm_live_impact_decomposition_certified": sdm_ok,
        "warnings": warnings,
        "artifacts": {
            "summary": "tables/live_backend_certification_matrix.csv",
            "spxtregress_matrix": "tables/stata_spxtregress_live_matrix.csv",
            "spxtregress_impacts": "tables/stata_spxtregress_live_impacts.csv",
            "ppmlhdfe": "tables/ppmlhdfe_live_certification.csv",
            "r_probe": "tables/r_live_backend_probes.csv",
        },
    }
    _write_json(out / "live_backend_certification.json", payload)
    return payload
