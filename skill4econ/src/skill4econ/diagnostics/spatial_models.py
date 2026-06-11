from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..adapters.heavy_backend_contract import (
    BACKEND_CONTRACT_VERSION,
    BACKEND_CAPABILITY_REGISTRY,
    canonical_backend_result,
    probe_r_backend,
    validate_spatial_impacts_table,
    write_canonical_backend_result,
)


def _as_path(value: Any, base: Path) -> Path:
    path = Path(str(value))
    if not path.is_absolute():
        path = base / path
    return path


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _probe_r_package(package: str) -> dict[str, Any]:
    return probe_r_backend([package])


def _r_status_row(backend: str, package: str, probe: dict[str, Any]) -> dict[str, Any]:
    status = str(probe.get("status"))
    return {
        "backend": backend,
        "available": status == "ok",
        "status": status,
        "backend_run_status": status,
        "error_code": probe.get("error_code"),
        "missing_dependencies": ",".join(map(str, probe.get("missing_packages") or probe.get("missing_dependencies") or [])),
        "note": probe.get("message") or f"R package {package} probe returned {status}.",
    }


def backend_status() -> list[dict[str, Any]]:
    splm_probe = _probe_r_package("splm")
    spdep_probe = _probe_r_package("spdep")
    stata_available = shutil.which("stata") is not None or shutil.which("StataMP-64") is not None
    return [
        {
            "backend": "stata_spxtregress",
            "available": stata_available,
            "status": "known_gap" if stata_available else "backend_unavailable",
            "backend_run_status": "known_gap" if stata_available else "backend_unavailable",
            "error_code": None if stata_available else "BACKEND_UNAVAILABLE",
            "missing_dependencies": "" if stata_available else "stata",
            "note": "preflight only; full spxtregress adapter is not wired",
        },
        {
            "backend": "stata_xsmle",
            "available": False,
            "status": "known_gap",
            "backend_run_status": "known_gap",
            "error_code": None,
            "missing_dependencies": "xsmle_live_probe_not_run",
            "note": "xsmle command availability is checked by Stata spatial_panel_preflight",
        },
        _r_status_row("r_splm", "splm", splm_probe),
        _r_status_row("r_spdep", "spdep", spdep_probe),
    ]


def parse_impact_decomposition(path: str | Path, output_dir: str | Path, *, repo_root: str | Path | None = None) -> dict[str, Any]:
    import pandas as pd

    base = Path(repo_root or ".")
    source = _as_path(path, base)
    if not source.exists():
        raise ValueError(f"BACKEND_PARSE_FAILED: impact_decomposition file not found: {source}")
    raw = pd.read_csv(source)
    validation = validate_spatial_impacts_table(source)
    if validation.get("status") != "ok":
        code = validation.get("error_code") or "BACKEND_PARSE_FAILED"
        raise ValueError(f"{code}: {validation.get('message')}")
    lower = {str(col).lower(): col for col in raw.columns}
    model_col = lower.get("model") or lower.get("spatial_model")
    effect_col = lower.get("effect") or lower.get("term") or lower.get("estimand")
    direct_col = lower.get("direct") or lower.get("direct_effect")
    indirect_col = lower.get("indirect") or lower.get("indirect_effect")
    total_col = lower.get("total") or lower.get("total_effect")
    se_col = lower.get("std_error") or lower.get("se")
    p_col = lower.get("p_value") or lower.get("p")
    missing = [name for name, col in [("effect", effect_col), ("direct", direct_col), ("indirect", indirect_col), ("total", total_col)] if col is None]
    if missing:
        raise ValueError(f"SDM_IMPACTS_MISSING: impact_decomposition missing columns: {missing}")

    rows = []
    for record in raw.to_dict("records"):
        rows.append(
            {
                "spatial_model": record.get(model_col) if model_col else "SDM",
                "effect": record.get(effect_col),
                "direct_effect": record.get(direct_col),
                "indirect_effect": record.get(indirect_col),
                "total_effect": record.get(total_col),
                "std_error": record.get(se_col) if se_col else None,
                "p_value": record.get(p_col) if p_col else None,
                "source_path": str(source),
                "backend_contract_version": BACKEND_CONTRACT_VERSION,
            }
        )
    out = Path(output_dir)
    _write_csv(out / "tables" / "spatial_impact_decomposition.csv", rows)
    model_rows = []
    for row in rows:
        for part in ["direct_effect", "indirect_effect", "total_effect"]:
            model_rows.append(
                {
                    "term": f"{row['effect']}_{part}",
                    "coef": row.get(part),
                    "std_error": row.get("std_error"),
                    "p_value": row.get("p_value"),
                    "estimator": "spatial impact decomposition parser",
                    "source_path": str(source),
                }
            )
    _write_csv(out / "model_table.csv", model_rows)
    canonical = canonical_backend_result(
        backend="impact_parser",
        adapter="spatial_panel_model_adapter",
        status="parser_only",
        available=True,
        message="Parsed supplied direct/indirect/total impact decomposition. No live SAR/SEM/SDM backend was run.",
        extra={
            "claim_level": "adapter_only",
            "paper_readiness": "supplementary_only",
            "main_claim_available": False,
            "has_impact_decomposition": True,
            "impact_decomposition": "tables/spatial_impact_decomposition.csv",
            "source_path": str(source),
            "validation": validation,
        },
    )
    write_canonical_backend_result(out / "backend_canonical_result.json", canonical)
    payload = {
        "status": "ok",
        "backend": "impact_parser",
        "backend_contract_version": BACKEND_CONTRACT_VERSION,
        "claim_level": "adapter_only",
        "paper_readiness": "supplementary_only",
        "main_claim_available": False,
        "backend_run_status": "parser_only",
        "has_impact_decomposition": True,
        "rows": rows,
        "warnings": [],
        "canonical_backend_result": canonical,
        "artifacts": {
            "impacts": "tables/spatial_impact_decomposition.csv",
            "model_table": "model_table.csv",
            "backend_canonical_result": "backend_canonical_result.json",
        },
    }
    (out / "spatial_model_adapter.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def run_spatial_model_adapter(spec: dict[str, Any], output_dir: str | Path, *, repo_root: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if spec.get("impact_decomposition") or spec.get("impact_decomposition_path"):
        return parse_impact_decomposition(
            spec.get("impact_decomposition") or spec.get("impact_decomposition_path"),
            out,
            repo_root=repo_root,
        )

    statuses = backend_status()
    _write_csv(out / "tables" / "spatial_backend_status.csv", statuses)
    canonical = canonical_backend_result(
        backend="spatial_panel_model_adapter",
        adapter="spatial_panel_model_adapter",
        status="known_gap",
        available=False,
        error_code="BACKEND_UNAVAILABLE",
        message="No live SAR/SEM/SDM backend was invoked. This is an adapter contract, not an estimate.",
        extra={
            "claim_level": "adapter_only",
            "paper_readiness": "not_available",
            "main_claim_available": False,
            "has_impact_decomposition": False,
            "backend_capabilities": {
                key: BACKEND_CAPABILITY_REGISTRY[key]
                for key in ["stata_xsmle", "stata_spxtregress", "r_splm", "r_spatialreg"]
            },
            "backend_status": statuses,
        },
    )
    write_canonical_backend_result(out / "backend_canonical_result.json", canonical)
    warnings = [
        {
            "severity": "yellow",
            "code": "BACKEND_UNAVAILABLE",
            "message": "No runnable SAR/SEM/SDM backend was invoked. Configure Stata xsmle/spxtregress, R splm, or provide impact_decomposition.",
            "action": "Do not report SAR/SDM results from this adapter until a backend produces direct/indirect/total effects.",
        },
        {
            "severity": "yellow",
            "code": "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION",
            "message": "No direct/indirect/total impact decomposition is available.",
            "action": "Provide a backend output table with direct, indirect, and total effects.",
        },
    ]
    payload = {
        "status": "skipped_backend_unavailable",
        "backend_contract_version": BACKEND_CONTRACT_VERSION,
        "claim_level": "adapter_only",
        "paper_readiness": "not_available",
        "main_claim_available": False,
        "backend_run_status": "known_gap",
        "has_impact_decomposition": False,
        "backend_status": statuses,
        "canonical_backend_result": canonical,
        "warnings": warnings,
        "artifacts": {
            "backend_status": "tables/spatial_backend_status.csv",
            "backend_canonical_result": "backend_canonical_result.json",
        },
    }
    (out / "spatial_model_adapter.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
