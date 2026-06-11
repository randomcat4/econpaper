from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _fmt_boundary(value: float | str) -> str:
    if value == "inf":
        return "inf"
    numeric = float(value)
    text = f"{numeric:g}".replace("-", "neg_").replace(".", "p")
    return text


def _normal_pvalue(t_stat: float) -> float:
    if not math.isfinite(t_stat):
        return math.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _ols_numpy(df: Any, y_col: str, terms: list[str], cluster_col: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import numpy as np

    columns = [y_col, *terms]
    if cluster_col:
        columns.append(cluster_col)
    work = df[columns].dropna().copy()
    if len(work) <= len(terms):
        raise ValueError("TWFE sample is too small for the requested spatial exposure design.")
    y_arr = work[y_col].to_numpy(dtype=float)
    X = work[terms].to_numpy(dtype=float)
    n, k = X.shape
    rank = int(np.linalg.matrix_rank(X))
    if rank < k:
        raise ValueError(f"TWFE design matrix is rank deficient: rank={rank}, columns={k}.")
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y_arr
    resid = y_arr - X @ beta
    df_resid = max(n - k, 1)
    if cluster_col:
        groups = work[cluster_col].astype(str).to_numpy()
        unique_groups = sorted(set(groups))
        if len(unique_groups) >= 2:
            meat = np.zeros((k, k))
            for group in unique_groups:
                idx = groups == group
                score = X[idx, :].T @ resid[idx]
                meat += np.outer(score, score)
            scale = (len(unique_groups) / (len(unique_groups) - 1)) * ((n - 1) / df_resid)
            cov = scale * xtx_inv @ meat @ xtx_inv
            cov_type = f"cluster:{cluster_col}:numpy"
        else:
            cov = xtx_inv @ ((X * resid[:, None]).T @ (X * resid[:, None])) @ xtx_inv
            cov *= n / df_resid
            cov_type = "HC1:numpy"
    else:
        cov = xtx_inv @ ((X * resid[:, None]).T @ (X * resid[:, None])) @ xtx_inv
        cov *= n / df_resid
        cov_type = "HC1:numpy"
    stderr = np.sqrt(np.maximum(np.diag(cov), 0.0))
    rows = []
    for term, coef, se in zip(terms, beta, stderr):
        t_stat = float(coef / se) if se > 0 else math.nan
        rows.append(
            {
                "term": term,
                "coef": float(coef),
                "std_error": float(se),
                "t_stat": t_stat,
                "p_value": _normal_pvalue(t_stat),
            }
        )
    return rows, {"nobs": int(n), "df_resid": int(df_resid), "cov_type": cov_type}


def _read_edges(edge_list: str | Path, spec: dict[str, Any]) -> Any:
    import pandas as pd

    source_col = str(spec.get("weight_source") or spec.get("source") or "source")
    target_col = str(spec.get("weight_target") or spec.get("target") or "target")
    weight_col = str(spec.get("weight") or spec.get("weight_col") or "weight")
    distance_col = str(spec.get("distance_col") or "distance_km")
    edges = pd.read_csv(edge_list)
    missing = [col for col in [source_col, target_col] if col not in edges.columns]
    if missing:
        raise ValueError(f"Spatial exposure weights are missing columns: {missing}")
    if weight_col not in edges.columns:
        edges[weight_col] = 1.0
    keep = [source_col, target_col, weight_col]
    if distance_col in edges.columns:
        keep.append(distance_col)
    edges = edges[keep].dropna(subset=[source_col, target_col, weight_col]).copy()
    edges = edges[edges[source_col] != edges[target_col]].copy()
    edges[weight_col] = edges[weight_col].astype(float)
    if bool(spec.get("row_standardize", True)):
        row_sums = edges.groupby(source_col)[weight_col].transform("sum")
        if (row_sums <= 0).any():
            raise ValueError("Spatial weights contain nonpositive row sums before row standardization.")
        edges[weight_col] = edges[weight_col] / row_sums
    return edges, {
        "source_col": source_col,
        "target_col": target_col,
        "weight_col": weight_col,
        "distance_col": distance_col if distance_col in edges.columns else None,
        "row_standardized": bool(spec.get("row_standardize", True)),
    }


def _make_local_treatment(df: Any, spec: dict[str, Any], treat_col: str, post_col: str | None) -> tuple[Any, str]:
    work = df.copy()
    explicit = str(spec.get("local_effect_col") or "")
    if explicit:
        if explicit not in work.columns:
            raise ValueError(f"local_effect_col `{explicit}` is not in the panel data.")
        work["_local_treatment"] = work[explicit].astype(float)
        return work, explicit
    if post_col and post_col in work.columns and not bool(spec.get("exposure_uses_raw_treat", False)):
        work["_local_treatment"] = work[treat_col].astype(float) * work[post_col].astype(float)
        return work, f"{treat_col}*{post_col}"
    work["_local_treatment"] = work[treat_col].astype(float)
    return work, treat_col


def _build_exposure(panel: Any, edges: Any, meta: dict[str, Any], spec: dict[str, Any]) -> tuple[Any, list[str]]:
    import pandas as pd

    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    source_col = meta["source_col"]
    target_col = meta["target_col"]
    weight_col = meta["weight_col"]
    distance_col = meta.get("distance_col")
    lookup = panel[[id_col, time_col]].drop_duplicates().rename(columns={id_col: source_col})
    neighbor = panel[[id_col, time_col, "_local_treatment"]].rename(
        columns={id_col: target_col, "_local_treatment": "__neighbor_treat"}
    )
    merged = lookup.merge(edges, on=source_col, how="left")
    merged = merged.merge(neighbor, on=[target_col, time_col], how="left")
    merged["__neighbor_treat"] = merged["__neighbor_treat"].fillna(0.0)
    merged["_spatial_exposure"] = merged[weight_col].fillna(0.0) * merged["__neighbor_treat"]
    exposure = (
        merged.groupby([source_col, time_col], as_index=False)["_spatial_exposure"]
        .sum()
        .rename(columns={source_col: id_col})
    )
    ring_cols: list[str] = []
    rings = spec.get("distance_rings_km") or spec.get("distance_rings") or []
    if rings and distance_col:
        boundaries = sorted(float(item) for item in rings)
        if not boundaries or boundaries[0] > 0:
            boundaries.insert(0, 0.0)
        intervals: list[tuple[float, float | str]] = []
        for lo, hi in zip(boundaries[:-1], boundaries[1:]):
            intervals.append((lo, hi))
        if bool(spec.get("include_open_ended_ring", True)):
            intervals.append((boundaries[-1], "inf"))
        for lo, hi in intervals:
            col = f"exposure_ring_{_fmt_boundary(lo)}_{_fmt_boundary(hi)}"
            ring_cols.append(col)
            hi_mask = True if hi == "inf" else merged[distance_col].astype(float) < float(hi)
            mask = (merged[distance_col].astype(float) >= float(lo)) & hi_mask
            ring = (
                merged.loc[mask]
                .assign(**{col: lambda x: x[weight_col].fillna(0.0) * x["__neighbor_treat"]})
                .groupby([source_col, time_col], as_index=False)[col]
                .sum()
                .rename(columns={source_col: id_col})
            )
            exposure = exposure.merge(ring, on=[id_col, time_col], how="left")
    exposure = exposure.fillna(0.0)
    out = panel.merge(exposure, on=[id_col, time_col], how="left")
    out[["_spatial_exposure", *ring_cols]] = out[["_spatial_exposure", *ring_cols]].fillna(0.0)
    out = out.sort_values([id_col, time_col]).copy()
    lag = int(spec.get("exposure_lag", 1))
    out["_spatial_exposure_lag"] = out.groupby(id_col)["_spatial_exposure"].shift(lag)
    out["_spatial_exposure_cumulative"] = out.groupby(id_col)["_spatial_exposure"].cumsum()
    return out, ring_cols


def _write_distribution(values: Any, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    clean = values.dropna()
    if len(clean):
        plt.hist(clean, bins=min(30, max(5, int(math.sqrt(len(clean))))), color="#357C78", edgecolor="white")
        plt.xlabel("Spatial exposure")
        plt.ylabel("Observations")
    else:
        plt.text(0.5, 0.5, "No exposure values", ha="center", va="center")
        plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _summary_tables(panel: Any, spec: dict[str, Any], output_dir: Path) -> dict[str, str]:
    import pandas as pd

    tables = output_dir / "tables"
    figures = output_dir / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    threshold = float(spec.get("near_exposure_threshold", spec.get("buffer_threshold", 0.0)))
    work = panel.copy()
    work["_is_control"] = work["_local_treatment"].astype(float) <= 0
    work["_near_control"] = ((work["_is_control"]) & (work["_spatial_exposure"] > threshold)).astype(int)
    work["_far_control"] = ((work["_is_control"]) & (work["_spatial_exposure"] <= threshold)).astype(int)
    work["_buffer_drop"] = work["_near_control"].astype(int)
    work["_buffer_keep"] = 1 - work["_buffer_drop"]
    summary_rows = []
    for year, group in work.groupby(time_col):
        controls = group[group["_is_control"]]
        summary_rows.append(
            {
                "year": year,
                "n_obs": int(len(group)),
                "n_units": int(group[id_col].nunique()),
                "treated_share": float((group["_local_treatment"] > 0).mean()),
                "mean_exposure": float(group["_spatial_exposure"].mean()),
                "p50_exposure": float(group["_spatial_exposure"].quantile(0.50)),
                "p90_exposure": float(group["_spatial_exposure"].quantile(0.90)),
                "max_exposure": float(group["_spatial_exposure"].max()),
                "contaminated_controls": int(controls["_near_control"].sum()) if len(controls) else 0,
                "contaminated_control_share": float(controls["_near_control"].mean()) if len(controls) else math.nan,
                "far_controls": int(controls["_far_control"].sum()) if len(controls) else 0,
            }
        )
    contaminated = work.loc[
        work["_near_control"] == 1,
        [id_col, time_col, "_spatial_exposure", "_spatial_exposure_lag", "_spatial_exposure_cumulative"],
    ].copy()
    summary_path = tables / "spatial_exposure_summary.csv"
    contaminated_path = tables / "contaminated_controls.csv"
    panel_path = output_dir / "spatial_exposure_panel.csv"
    buffered_path = output_dir / "spatial_exposure_panel_buffered.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
    contaminated.to_csv(contaminated_path, index=False, encoding="utf-8-sig")
    work.to_csv(panel_path, index=False, encoding="utf-8-sig")
    work.loc[work["_buffer_keep"] == 1].to_csv(buffered_path, index=False, encoding="utf-8-sig")
    _write_distribution(work["_spatial_exposure"], figures / "spatial_exposure_distribution.png")
    return {
        "summary": "tables/spatial_exposure_summary.csv",
        "contaminated_controls": "tables/contaminated_controls.csv",
        "distribution": "figures/spatial_exposure_distribution.png",
        "panel": "spatial_exposure_panel.csv",
        "buffered_panel": "spatial_exposure_panel_buffered.csv",
    }


def _twfe_design(panel: Any, spec: dict[str, Any], keep_terms: list[str]) -> tuple[Any, list[str], str]:
    import pandas as pd

    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    y_col = str(spec.get("y") or spec.get("outcome") or "y")
    covars = [str(item) for item in (spec.get("x") or spec.get("covars") or [])]
    cluster_col = str(spec.get("cluster") or id_col)
    needed = list(dict.fromkeys([y_col, id_col, time_col, cluster_col, *keep_terms, *covars]))
    missing = [col for col in needed if col not in panel.columns]
    if missing:
        raise ValueError(f"Spatial exposure TWFE missing columns: {missing}")
    design = panel[needed].dropna(subset=[y_col, *keep_terms, *covars]).copy()
    design = design.join(pd.get_dummies(design[id_col].astype(str), prefix=f"fe_{id_col}", drop_first=True))
    design = design.join(pd.get_dummies(design[time_col].astype(str), prefix=f"fe_{time_col}", drop_first=True))
    design["_const"] = 1.0
    base_terms = ["_const", *keep_terms, *covars]
    fe_terms = [col for col in design.columns if col.startswith(f"fe_{id_col}_") or col.startswith(f"fe_{time_col}_")]
    return design, [*base_terms, *fe_terms], cluster_col


def _estimate_main_model(panel: Any, spec: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    import pandas as pd

    tables = output_dir / "tables"
    y_col = str(spec.get("y") or spec.get("outcome") or "y")
    keep_terms = ["_local_treatment", "_spatial_exposure"]
    design, terms, cluster_col = _twfe_design(panel, spec, keep_terms)
    rows, meta = _ols_numpy(design, y_col, terms, cluster_col)
    main_rows = [row for row in rows if row["term"] in set(keep_terms)]
    for row in main_rows:
        row["estimand"] = "local_effect" if row["term"] == "_local_treatment" else "spillover_effect"
        row["estimator"] = "numpy TWFE spatial exposure DID"
    pd.DataFrame(main_rows).to_csv(tables / "spatial_exposure_twfe.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([row for row in main_rows if row["term"] == "_local_treatment"]).to_csv(
        tables / "local_effect.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame([row for row in main_rows if row["term"] == "_spatial_exposure"]).to_csv(
        tables / "spillover_effect.csv", index=False, encoding="utf-8-sig"
    )
    return {
        "rows": main_rows,
        "meta": meta,
        "artifacts": {
            "twfe": "tables/spatial_exposure_twfe.csv",
            "local_effect": "tables/local_effect.csv",
            "spillover_effect": "tables/spillover_effect.csv",
        },
    }


def _local_did_common_output(panel: Any, spec: dict[str, Any], main: dict[str, Any], event: dict[str, Any], output_dir: Path) -> str | None:
    local_rows = [row for row in main.get("rows") or [] if row.get("term") == "_local_treatment"]
    if not local_rows:
        return None
    row = local_rows[0]
    estimate = row.get("coef")
    std_error = row.get("std_error")
    try:
        ci_low = float(estimate) - 1.96 * float(std_error)
        ci_high = float(estimate) + 1.96 * float(std_error)
    except (TypeError, ValueError):
        ci_low = None
        ci_high = None
    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    dynamic_path = "tables/spatial_exposure_event_study.csv" if event.get("status") == "ok" else None
    payload = {
        "estimator": "spatial_exposure_local_twfe",
        "estimand": "local_ATT_reduced_form",
        "estimand_scope": "reduced_form_spatial_exposure",
        "design_type": "spatial_exposure_did",
        "n_obs": (main.get("meta") or {}).get("nobs"),
        "n_units": int(panel[id_col].nunique(dropna=True)) if id_col in panel.columns else None,
        "n_periods": int(panel[time_col].nunique(dropna=True)) if time_col in panel.columns else None,
        "control_group": spec.get("control_group") or "untreated observations; exposed controls diagnosed separately",
        "claim_level": "sensitivity_only",
        "paper_readiness": "supplementary_only",
        "main_claim_available": False,
        "is_structural_spillover_model": False,
        "has_impact_decomposition": False,
        "main_effect": {
            "estimate": estimate,
            "std_error": std_error,
            "p_value": row.get("p_value"),
            "ci_low": ci_low,
            "ci_high": ci_high,
            "term": "_local_treatment",
            "source_path": "tables/local_effect.csv",
        },
        "dynamic_effects_path": dynamic_path,
        "group_time_effects_path": None,
        "raw_output_path": None,
        "backend": "numpy_twfe_spatial_exposure",
        "engine": "python",
        "role": "benchmark_not_main",
        "twfe_role": "comparison_only",
        "status": "success",
        "note": "DID common schema bridge for the local treatment coefficient only. The W*treatment exposure coefficient remains reduced-form and is not a structural indirect effect.",
    }
    path = output_dir / "did_common_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return "did_common_output.json"


def _event_relative_time(panel: Any, spec: dict[str, Any], exposure_threshold: float) -> Any:
    import pandas as pd

    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    work = panel.copy()
    if spec.get("gvar") and str(spec.get("gvar")) in work.columns:
        g_col = str(spec.get("gvar"))
        work["_first_treat_time"] = pd.to_numeric(work[g_col], errors="coerce")
    else:
        treated_times = (
            work.loc[work["_local_treatment"] > 0, [id_col, time_col]]
            .assign(__time=lambda x: pd.to_numeric(x[time_col], errors="coerce"))
            .groupby(id_col)["__time"]
            .min()
        )
        work["_first_treat_time"] = work[id_col].map(treated_times)
    exposure_times = (
        work.loc[work["_spatial_exposure"] > exposure_threshold, [id_col, time_col]]
        .assign(__time=lambda x: pd.to_numeric(x[time_col], errors="coerce"))
        .groupby(id_col)["__time"]
        .min()
    )
    numeric_time = pd.to_numeric(work[time_col], errors="coerce")
    work["_event_time_local"] = numeric_time - work["_first_treat_time"]
    work["_first_exposure_time"] = work[id_col].map(exposure_times)
    work["_event_time_exposure"] = numeric_time - work["_first_exposure_time"]
    return work


def _estimate_event_models(panel: Any, spec: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    import pandas as pd

    tables = output_dir / "tables"
    y_col = str(spec.get("y") or spec.get("outcome") or "y")
    threshold = float(spec.get("near_exposure_threshold", spec.get("buffer_threshold", 0.0)))
    window = spec.get("event_window") or [-3, 3]
    lo, hi = int(window[0]), int(window[1])
    base = int(spec.get("base_period", -1))
    work = _event_relative_time(panel, spec, threshold)
    event_terms: list[str] = []
    event_summary = []
    for k in range(lo, hi + 1):
        if k == base:
            continue
        local_col = f"_event_local_{'m' + str(abs(k)) if k < 0 else 'p' + str(k)}"
        exposure_col = f"_event_exposure_{'m' + str(abs(k)) if k < 0 else 'p' + str(k)}"
        work[local_col] = ((work["_event_time_local"] == k) & work["_first_treat_time"].notna()).astype(float)
        work[exposure_col] = ((work["_event_time_exposure"] == k) & work["_first_exposure_time"].notna()).astype(float) * work[
            "_spatial_exposure"
        ].astype(float)
        for col, kind in [(local_col, "local_treatment"), (exposure_col, "spatial_exposure")]:
            support = int((work[col] != 0).sum())
            event_summary.append({"term": col, "relative_time": k, "kind": kind, "support": support})
            if support > 0 and work[col].nunique(dropna=True) > 1:
                event_terms.append(col)
    pd.DataFrame(event_summary).to_csv(tables / "spatial_exposure_event_support.csv", index=False, encoding="utf-8-sig")
    if not event_terms:
        return {
            "status": "skipped",
            "warnings": [
                {
                    "severity": "yellow",
                    "code": "EXPOSURE_CONTROL_DEFINITION_WEAK",
                    "message": "Event-study exposure terms have no support in the requested window.",
                    "action": "Check treatment timing, exposure threshold, and event_window before claiming dynamic effects.",
                    "affected_artifacts": ["tables/spatial_exposure_event_support.csv"],
                }
            ],
            "artifacts": {"support": "tables/spatial_exposure_event_support.csv"},
        }
    design, terms, cluster_col = _twfe_design(work, spec, event_terms)
    try:
        rows, meta = _ols_numpy(design, y_col, terms, cluster_col)
        rows = [row for row in rows if row["term"] in set(event_terms)]
        for row in rows:
            row["estimand"] = "event_study_local" if row["term"].startswith("_event_local_") else "event_study_exposure"
            row["estimator"] = "numpy event-study TWFE spatial exposure DID"
        pd.DataFrame(rows).to_csv(tables / "spatial_exposure_event_study.csv", index=False, encoding="utf-8-sig")
        return {
            "status": "ok",
            "rows": rows,
            "meta": meta,
            "warnings": [],
            "artifacts": {
                "event_study": "tables/spatial_exposure_event_study.csv",
                "support": "tables/spatial_exposure_event_support.csv",
            },
        }
    except ValueError as exc:
        return {
            "status": "skipped",
            "warnings": [
                {
                    "severity": "yellow",
                    "code": "EXPOSURE_CONTROL_DEFINITION_WEAK",
                    "message": f"Event-study spatial exposure design was not estimable: {exc}",
                    "action": "Use a larger panel, wider support, or a simpler event window before claiming dynamic effects.",
                    "affected_artifacts": ["tables/spatial_exposure_event_support.csv"],
                }
            ],
            "artifacts": {"support": "tables/spatial_exposure_event_support.csv"},
        }


def run_spatial_exposure_did(df: Any, edge_list: str | Path, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    y_col = str(spec.get("y") or spec.get("outcome") or "y")
    treat_col = str(spec.get("treat") or spec.get("treatment") or "treat")
    post_col = str(spec.get("post") or "") or None
    required = [id_col, time_col, y_col, treat_col]
    if post_col:
        required.append(post_col)
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Spatial exposure DID missing panel columns: {missing}")
    work, local_source = _make_local_treatment(df, spec, treat_col, post_col)
    edges, edge_meta = _read_edges(edge_list, spec)
    panel, ring_cols = _build_exposure(work, edges, edge_meta, spec)
    artifacts = _summary_tables(panel, spec, out)
    main = _estimate_main_model(panel, spec, out)
    event = _estimate_event_models(panel, spec, out) if bool(spec.get("run_event_study", True)) else {"status": "skipped", "warnings": [], "artifacts": {}}
    common_output = _local_did_common_output(panel, spec, main, event, out)
    warnings: list[dict[str, Any]] = []
    threshold = float(spec.get("near_exposure_threshold", spec.get("buffer_threshold", 0.0)))
    controls = panel.loc[panel["_local_treatment"] <= 0].copy()
    contaminated_share = float((controls["_spatial_exposure"] > threshold).mean()) if len(controls) else math.nan
    trigger_share = float(spec.get("contaminated_control_share_threshold", 0.05))
    if math.isfinite(contaminated_share) and contaminated_share > trigger_share:
        warnings.append(
            {
                "severity": "yellow",
                "code": "CONTROL_GROUP_CONTAMINATED",
                "message": f"{contaminated_share:.1%} of control observations have spatial exposure above {threshold:g}.",
                "action": "Report near-control/far-control definitions, consider buffer-zone deletion, and avoid interpreting exposed controls as clean controls.",
                "affected_artifacts": ["tables/contaminated_controls.csv", "spatial_exposure_panel_buffered.csv"],
            }
        )
    if not any(key in spec for key in ["near_exposure_threshold", "buffer_threshold", "distance_rings_km", "distance_rings"]):
        warnings.append(
            {
                "severity": "yellow",
                "code": "EXPOSURE_CONTROL_DEFINITION_WEAK",
                "message": "No explicit exposure threshold, buffer threshold, or distance-ring definition was supplied.",
                "action": "Define near/far controls and buffer rules in the spec before making spatial spillover claims.",
            }
        )
    if (spec.get("distance_rings_km") or spec.get("distance_rings")) and not edge_meta.get("distance_col"):
        warnings.append(
            {
                "severity": "yellow",
                "code": "EXPOSURE_CONTROL_DEFINITION_WEAK",
                "message": "Distance-ring exposure was requested but the edge list has no distance column.",
                "action": "Build W with distance_km or pass distance_col before using ring exposure.",
            }
        )
    warnings.extend(event.get("warnings") or [])
    rows = [*main["rows"], *(event.get("rows") or [])]
    payload = {
        "edge_list": str(edge_list),
        "id": id_col,
        "time": time_col,
        "outcome": y_col,
        "treatment": treat_col,
        "local_treatment_source": local_source,
        "edge_metadata": edge_meta,
        "ring_exposure_columns": ring_cols,
        "threshold": threshold,
        "contaminated_control_share": contaminated_share,
        "main_model": main["meta"],
        "event_study_status": event["status"],
        "event_model": event.get("meta") or {},
        "claim_level": "sensitivity_only",
        "paper_readiness": "supplementary_only",
        "main_claim_available": False,
        "estimand_scope": "reduced_form_spatial_exposure",
        "is_structural_spillover_model": False,
        "has_impact_decomposition": False,
        "allowed_claim": "association between spatial exposure and outcome under specified W and controls",
        "forbidden_claims": [
            "structural indirect effect",
            "SAR/SEM/SDM impact decomposition",
            "policy spillover mechanism proven",
        ],
        "warnings": warnings,
        "rows": rows,
        "artifacts": {
            **artifacts,
            **main["artifacts"],
            **(event.get("artifacts") or {}),
            **({"did_common_output": common_output} if common_output else {}),
        },
        "safe_claims": [
            "The output separates local treatment and W*treatment spillover coefficients.",
            "Spatial exposure is a reduced-form exposure DID diagnostic, not SAR/SDM impact decomposition.",
        ],
        "unsafe_claims": [
            "Do not call the W*treatment coefficient a structural indirect effect without a spatial model and impact decomposition.",
            "Do not treat exposed controls as clean controls when CONTROL_GROUP_CONTAMINATED is raised.",
        ],
    }
    (out / "spatial_exposure_did.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
