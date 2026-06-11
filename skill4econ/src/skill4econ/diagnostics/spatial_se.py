from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .spatial_exposure import _build_exposure, _make_local_treatment, _ols_numpy, _read_edges, _twfe_design


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return float(2 * radius * math.asin(min(1.0, math.sqrt(a))))


def _normal_pvalue(t_stat: float) -> float:
    if not math.isfinite(t_stat):
        return math.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _spatial_hac_rows(design: Any, y_col: str, terms: list[str], keep_terms: list[str], id_col: str, lon_col: str, lat_col: str, cutoffs: list[float]) -> list[dict[str, Any]]:
    import numpy as np

    work = design[[y_col, id_col, lon_col, lat_col, *terms]].dropna().copy()
    y = work[y_col].to_numpy(dtype=float)
    X = work[terms].to_numpy(dtype=float)
    n, k = X.shape
    if n <= k or np.linalg.matrix_rank(X) < k:
        raise ValueError("Spatial SE design is rank deficient or too small.")
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    coords = work[[id_col, lon_col, lat_col]].drop_duplicates(subset=[id_col]).set_index(id_col)
    ids = work[id_col].tolist()
    rows: list[dict[str, Any]] = []
    for cutoff in cutoffs:
        meat = np.zeros((k, k))
        for i in range(n):
            xi = X[i, :]
            ui = resid[i]
            ci = coords.loc[ids[i]]
            for j in range(n):
                cj = coords.loc[ids[j]]
                dist = _haversine_km(float(ci[lat_col]), float(ci[lon_col]), float(cj[lat_col]), float(cj[lon_col]))
                if dist <= cutoff:
                    meat += np.outer(xi * ui, X[j, :] * resid[j])
        cov = xtx_inv @ meat @ xtx_inv
        stderr = np.sqrt(np.maximum(np.diag(cov), 0.0))
        for term, coef, se in zip(terms, beta, stderr):
            if term not in keep_terms:
                continue
            t_stat = float(coef / se) if se > 0 else math.nan
            rows.append(
                {
                    "term": term,
                    "coef": float(coef),
                    "std_error": float(se),
                    "p_value": _normal_pvalue(t_stat),
                    "t_stat": t_stat,
                    "se_type": "spatial_hac_uniform_cutoff",
                    "kernel": "uniform",
                    "is_full_conley": False,
                    "cutoff_km": float(cutoff),
                }
            )
    return rows


def _plot_cutoffs(rows: list[dict[str, Any]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    plottable = [row for row in rows if row.get("se_type") == "spatial_hac_uniform_cutoff"]
    if not plottable:
        plt.text(0.5, 0.5, "No spatial SE estimates", ha="center", va="center")
        plt.axis("off")
    else:
        for term in sorted({row["term"] for row in plottable}):
            subset = [row for row in plottable if row["term"] == term]
            subset.sort(key=lambda row: float(row["cutoff_km"]))
            plt.plot([row["cutoff_km"] for row in subset], [row["std_error"] for row in subset], marker="o", label=term)
        plt.xlabel("Distance cutoff (km)")
        plt.ylabel("Spatial HAC standard error")
        plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def run_spatial_se_comparison(df: Any, edge_list: str | Path, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    import pandas as pd

    out = Path(output_dir)
    tables = out / "tables"
    figures = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    y_col = str(spec.get("y") or spec.get("outcome") or "y")
    treat_col = str(spec.get("treat") or spec.get("treatment") or "treat")
    post_col = str(spec.get("post") or "") or None
    lon_col = str(spec.get("lon") or spec.get("longitude") or "lon")
    lat_col = str(spec.get("lat") or spec.get("latitude") or "lat")
    cutoffs = [float(item) for item in (spec.get("spatial_se_cutoffs_km") or spec.get("cutoffs_km") or [50, 100, 200])]

    warnings: list[dict[str, Any]] = []
    work, _ = _make_local_treatment(df, spec, treat_col, post_col)
    edges, meta = _read_edges(edge_list, spec)
    panel, _ = _build_exposure(work, edges, meta, spec)
    keep_terms = ["_local_treatment", "_spatial_exposure"]
    design, terms, cluster_col = _twfe_design(panel, spec, keep_terms)
    base_rows, base_meta = _ols_numpy(design, y_col, terms, cluster_col)
    rows = []
    for row in base_rows:
        if row["term"] in keep_terms:
            rows.append({**row, "se_type": base_meta.get("cov_type"), "cutoff_km": None})

    if lon_col not in panel.columns or lat_col not in panel.columns:
        warnings.append(
            {
                "severity": "yellow",
                "code": "SPATIAL_SE_NOT_USED",
                "message": f"Coordinate columns `{lon_col}`/`{lat_col}` are unavailable; spatial HAC/Conley comparison was skipped.",
                "action": "Add lon/lat coordinates or use a backend spatial-SE adapter before claiming spatially robust inference.",
            }
        )
    else:
        design_with_coords = design.join(panel.loc[design.index, [lon_col, lat_col]])
        rows.extend(_spatial_hac_rows(design_with_coords, y_col, terms, keep_terms, id_col, lon_col, lat_col, cutoffs))
        warnings.append(
            {
                "severity": "yellow",
                "code": "SPATIAL_HAC_UNIFORM_KERNEL",
                "message": "Spatial SE comparison uses a uniform distance-cutoff HAC sensitivity grid, not a full Conley kernel implementation.",
                "action": "Report it as cutoff sensitivity only; use a certified Conley/spatial-panel backend before claiming publication-grade spatial inference.",
            }
        )

    pd.DataFrame(rows).to_csv(tables / "spatial_se_comparison.csv", index=False, encoding="utf-8-sig")
    _plot_cutoffs(rows, figures / "spatial_se_cutoff_sensitivity.png")
    payload = {
        "status": "ok" if any(row.get("se_type") == "spatial_hac_uniform_cutoff" for row in rows) else "skipped_no_coordinates",
        "claim_level": "sensitivity_only",
        "paper_readiness": "supplementary_only",
        "main_claim_available": False,
        "is_full_conley": False,
        "is_full_spatial_panel_inference": False,
        "cutoffs_km": cutoffs,
        "warnings": warnings,
        "rows": rows,
        "artifacts": {
            "comparison": "tables/spatial_se_comparison.csv",
            "cutoff_sensitivity": "figures/spatial_se_cutoff_sensitivity.png",
        },
    }
    (out / "spatial_se_comparison.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
