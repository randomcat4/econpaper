from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ..adapters.heavy_backend_contract import probe_r_backend
from ..core import REPO_ROOT, read_spec
from ..validation import write_validation_report


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


def _as_repo_path(value: str | Path) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else REPO_ROOT / path


def _extract_last_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    for line in reversed(stripped.splitlines()):
        try:
            parsed = json.loads(line)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _default_cases() -> list[dict[str, Any]]:
    return [
        {
            "workflow": "did_paper_run",
            "case": "simple_2x2",
            "spec": "skill4econ/examples/mini_panel/did_paper_run_spec.yml",
            "expected_statuses": ["success"],
        },
        {
            "workflow": "did_paper_run",
            "case": "staggered_stata_first",
            "spec": "skill4econ/examples/mini_panel/did_paper_staggered_spec.yml",
            "expected_statuses": ["success", "partial_success", "success_with_warnings", "degraded"],
        },
        {
            "workflow": "did_paper_run",
            "case": "twfe_modern_flip_fixture",
            "inline_spec": {
                "data": "skill4econ/tests/fixtures/did/twfe_modern_did_flip.csv",
                "design_type": "staggered_adoption_did",
                "id": "unit",
                "time": "year",
                "y": "y",
                "treat": "treat",
                "gvar": "gvar",
                "x": ["x1"],
                "cluster": "unit",
                "engine_policy": "stata_first",
                "event_window": [-2, 2],
                "base_period": -1,
            },
            "expected_statuses": ["success", "partial_success", "success_with_warnings"],
        },
        {
            "workflow": "psm_did_policy_run",
            "case": "policy_good",
            "spec": "skill4econ/examples/mini_panel/psm_did_policy_run_spec.yml",
            "expected_statuses": ["success", "partial_success", "success_with_warnings"],
        },
        {
            "workflow": "psm_did_policy_run",
            "case": "missing_treatment_column",
            "spec": "skill4econ/examples/mini_panel/bad_psm_did_missing_treat.yml",
            "expected_statuses": ["failed"],
        },
        {
            "workflow": "psm_did_policy_run",
            "case": "no_drdid_sample_support",
            "spec": "skill4econ/examples/mini_panel/psm_did_policy_run_spec.yml",
            "overrides": {"drdid_sample_if": "year == 1900"},
            "expected_statuses": ["success", "partial_success", "success_with_warnings", "degraded", "failed"],
        },
        {
            "workflow": "spatial_spillover_run",
            "case": "spatial_good",
            "spec": "skill4econ/examples/mini_panel/spatial_spillover_run_spec.yml",
            "expected_statuses": ["success", "partial_success", "success_with_warnings"],
        },
        {
            "workflow": "spatial_spillover_run",
            "case": "missing_weights",
            "spec": "skill4econ/examples/mini_panel/bad_spatial_missing_weights.yml",
            "expected_statuses": ["failed"],
        },
        {
            "workflow": "spatial_spillover_run",
            "case": "alternate_w",
            "spec": "skill4econ/examples/mini_panel/spatial_spillover_run_spec.yml",
            "overrides": {"weights": "skill4econ/examples/mini_panel/spatial_weights_alt.csv"},
            "expected_statuses": ["success", "partial_success", "success_with_warnings", "not_paper_ready"],
        },
    ]


def _materialize_case_spec(case: dict[str, Any], output_dir: Path) -> Path:
    generated = output_dir / "generated_specs"
    generated.mkdir(parents=True, exist_ok=True)
    workflow = str(case.get("workflow"))
    name = str(case.get("case"))
    if case.get("inline_spec"):
        spec = dict(case["inline_spec"])
    else:
        spec_path = _as_repo_path(str(case["spec"]))
        spec = read_spec(spec_path)
    spec.update(case.get("overrides") or {})
    spec["output_dir"] = str(output_dir / "child_runs" / workflow / name)
    path = generated / f"{workflow}_{name}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _risk_codes(run_dir: Path) -> list[str]:
    risk_path = run_dir / "reviewer_risk.json"
    if not risk_path.exists():
        return []
    try:
        payload = json.loads(risk_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [str(item.get("code")) for item in payload.get("risks") or [] if item.get("code")]


def _run_stata_profile(
    case: dict[str, Any],
    output_dir: Path,
    *,
    timeout: int,
    strict_validation: bool,
) -> dict[str, Any]:
    spec_path = _materialize_case_spec(case, output_dir)
    workflow = str(case["workflow"])
    case_name = str(case["case"])
    child_output = output_dir / "child_runs" / workflow / case_name
    command = [
        sys.executable,
        "-m",
        "skill4econ.cli",
        "workflow",
        "--name",
        workflow,
        "--spec",
        str(spec_path),
        "--output",
        str(child_output),
        "--run",
    ]
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        elapsed = time.perf_counter() - started
        parsed = _extract_last_json_object(proc.stdout)
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        return {
            "workflow": workflow,
            "case": case_name,
            "backend_profile": "stata",
            "status": "backend_timeout",
            "manifest_status": "",
            "expected_statuses": ",".join(case.get("expected_statuses") or []),
            "expectation_met": False,
            "returncode": 124,
            "elapsed_seconds": round(elapsed, 3),
            "run_dir": "",
            "validation_status": "",
            "risk_codes": "",
            "command": " ".join(command),
            "message": f"Workflow cell timed out after {timeout}s.",
            "stdout_tail": (exc.stdout or "")[-1200:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-1200:] if isinstance(exc.stderr, str) else "",
        }
    manifest = (parsed or {}).get("manifest") or {}
    run_dir = Path(str((parsed or {}).get("run_dir") or manifest.get("run_dir") or ""))
    manifest_status = str(manifest.get("status") or "")
    expected = [str(item) for item in case.get("expected_statuses") or []]
    validation_status = ""
    if run_dir.exists():
        try:
            validation_status = write_validation_report(run_dir, strict=strict_validation).status
        except Exception as exc:
            validation_status = f"validation_error:{exc.__class__.__name__}"
    return {
        "workflow": workflow,
        "case": case_name,
        "backend_profile": "stata",
        "status": "ok" if proc.returncode == 0 else "backend_error",
        "manifest_status": manifest_status,
        "expected_statuses": ",".join(expected),
        "expectation_met": (not expected) or (manifest_status in expected),
        "returncode": proc.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "run_dir": str(run_dir) if run_dir.exists() else "",
        "validation_status": validation_status,
        "risk_codes": ",".join(_risk_codes(run_dir)) if run_dir.exists() else "",
        "command": " ".join(command),
        "message": "Workflow subprocess completed." if proc.returncode == 0 else "Workflow subprocess returned non-zero.",
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
    }


def _run_r_profile(case: dict[str, Any], output_dir: Path, *, timeout: float) -> dict[str, Any]:
    workflow = str(case["workflow"])
    case_name = str(case["case"])
    packages = ["spdep", "splm", "spatialreg"]
    result = probe_r_backend(packages, timeout=timeout)
    status = str(result.get("status"))
    return {
        "workflow": workflow,
        "case": case_name,
        "backend_profile": "r",
        "status": status,
        "manifest_status": "",
        "expected_statuses": "r_backend_available",
        "expectation_met": status == "ok",
        "returncode": "",
        "elapsed_seconds": "",
        "run_dir": "",
        "validation_status": "",
        "risk_codes": "",
        "command": "Rscript requireNamespace probes for spdep/splm/spatialreg",
        "message": str(result.get("message") or ""),
        "stdout_tail": "",
        "stderr_tail": "",
        "missing_dependencies": ",".join(map(str, result.get("missing_dependencies") or [])),
        "missing_packages": ",".join(map(str, result.get("missing_packages") or [])),
        "error_code": str(result.get("error_code") or ""),
    }


def run_flagship_slow_matrix(
    spec: dict[str, Any],
    output_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    _ = repo_root
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    tables = out / "tables"
    cases = list(spec.get("cases") or _default_cases())
    profiles = [str(item).lower() for item in spec.get("backend_profiles") or ["stata", "r"]]
    timeout = int(spec.get("timeout_seconds", 420))
    strict_validation = bool(spec.get("strict_validation", False))
    max_cells = int(spec.get("max_cells", 0) or 0)

    rows: list[dict[str, Any]] = []
    for case in cases:
        for profile in profiles:
            if max_cells and len(rows) >= max_cells:
                break
            if profile == "stata":
                rows.append(_run_stata_profile(case, out, timeout=timeout, strict_validation=strict_validation))
            elif profile == "r":
                rows.append(_run_r_profile(case, out, timeout=float(spec.get("r_probe_timeout", 30))))
            else:
                rows.append(
                    {
                        "workflow": str(case.get("workflow")),
                        "case": str(case.get("case")),
                        "backend_profile": profile,
                        "status": "unsupported",
                        "manifest_status": "",
                        "expected_statuses": "",
                        "expectation_met": False,
                        "message": f"Unsupported backend profile: {profile}",
                    }
                )
        if max_cells and len(rows) >= max_cells:
            break

    fieldnames = [
        "workflow",
        "case",
        "backend_profile",
        "status",
        "manifest_status",
        "expected_statuses",
        "expectation_met",
        "returncode",
        "elapsed_seconds",
        "run_dir",
        "validation_status",
        "risk_codes",
        "missing_dependencies",
        "missing_packages",
        "error_code",
        "command",
        "message",
        "stdout_tail",
        "stderr_tail",
    ]
    _write_csv(tables / "flagship_slow_matrix.csv", rows, fieldnames)
    model_rows = [
        {
            "workflow": row.get("workflow"),
            "model": row.get("backend_profile"),
            "case": row.get("case"),
            "status": row.get("manifest_status") or row.get("status"),
            "term": "",
            "note": row.get("message") or "",
            "source_path": row.get("run_dir") or "",
        }
        for row in rows
    ]
    _write_csv(out / "model_table.csv", model_rows, ["workflow", "model", "case", "status", "term", "note", "source_path"])

    warnings: list[dict[str, Any]] = []
    for row in rows:
        if row.get("expectation_met") is False:
            code = row.get("error_code") or ("BACKEND_UNAVAILABLE" if row.get("backend_profile") == "r" else "SLOW_MATRIX_EXPECTATION_MISMATCH")
            if code == "R_BACKEND_UNAVAILABLE":
                code = "BACKEND_UNAVAILABLE"
            warnings.append(
                {
                    "severity": "yellow" if row.get("backend_profile") == "r" else "red",
                    "code": code,
                    "message": f"{row.get('workflow')}::{row.get('case')}::{row.get('backend_profile')} status={row.get('status')} manifest={row.get('manifest_status')}",
                    "action": "Inspect the cell run_dir/logs before claiming backend workflow coverage.",
                    "affected_artifacts": ["tables/flagship_slow_matrix.csv"],
                }
            )
    status = "ok" if rows and all(row.get("expectation_met") is not False for row in rows) else "partial_success"
    payload = {
        "status": status,
        "rows": rows,
        "n_cells": len(rows),
        "n_stata_cells": sum(1 for row in rows if row.get("backend_profile") == "stata"),
        "n_r_cells": sum(1 for row in rows if row.get("backend_profile") == "r"),
        "warnings": warnings,
        "artifacts": {
            "matrix": "tables/flagship_slow_matrix.csv",
            "model_table": "model_table.csv",
        },
    }
    _write_json(out / "flagship_slow_matrix.json", payload)
    return payload
