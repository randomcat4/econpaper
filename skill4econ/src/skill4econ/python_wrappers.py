from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

from .config import dea_discovery_chain, resolve_dea_backend
from .core import (
    ROOT,
    REPO_ROOT,
    RunContext,
    Skill4EconError,
    copy_if_needed,
    data_path_from_spec,
    dependency_report,
    file_sha256,
    listify,
    missing_dependency,
    read_table,
    require_columns,
    run_subprocess,
    write_audit,
    write_json,
    write_manifest,
    write_model_table,
)


def _plan_or_dry(ctx: RunContext, requirements: list[str]) -> dict[str, Any] | None:
    if ctx.state in {"plan", "dry-run", "audit"}:
        messages = [
            f"{ctx.method} state={ctx.state}; estimation was not executed.",
            *requirements,
        ]
        write_audit(ctx, "planned" if ctx.state == "plan" else "validated", messages)
        return write_manifest(ctx, "planned" if ctx.state == "plan" else "validated")
    return None


def _positive_finite_df(df: Any) -> float | None:
    try:
        value = float(df)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def _df_payload(df: Any) -> int | float:
    value = _positive_finite_df(df)
    if value is None:
        return math.nan
    return int(value) if value.is_integer() else value


def _t_pvalue(t_stat: float, df: Any) -> float:
    try:
        stat = float(t_stat)
    except (TypeError, ValueError):
        return math.nan
    df_value = _positive_finite_df(df)
    if df_value is None or not math.isfinite(stat):
        return math.nan
    from scipy.stats import t

    return float(t.sf(abs(stat), df_value) * 2.0)


def _t_critical(df: Any, confidence: float = 0.95) -> float:
    df_value = _positive_finite_df(df)
    if df_value is None:
        return math.nan
    from scipy.stats import t

    alpha = 1.0 - confidence
    return float(t.ppf(1.0 - alpha / 2.0, df_value))


def _inference_row(
    term: str,
    coef: float,
    std_error: float,
    df_inference: Any,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    coef_value = float(coef)
    se_value = float(std_error)
    t_stat = float(coef_value / se_value) if math.isfinite(se_value) and se_value > 0 else math.nan
    critical = _t_critical(df_inference)
    ci_low = coef_value - critical * se_value if math.isfinite(critical) and math.isfinite(se_value) else math.nan
    ci_high = coef_value + critical * se_value if math.isfinite(critical) and math.isfinite(se_value) else math.nan
    row = {
        "term": term,
        "coef": coef_value,
        "std_error": se_value,
        "p_value": _t_pvalue(t_stat, df_inference),
        "t_stat": t_stat,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "df_inference": _df_payload(df_inference),
    }
    if extra:
        row.update(extra)
    return row


def _few_cluster_inference_risk(cluster: str, n_clusters: int) -> dict[str, Any]:
    degradation = "supplementary_only" if n_clusters < 15 else "none"
    return {
        "severity": "yellow",
        "code": "FEW_CLUSTERS_INFERENCE_FRAGILE",
        "message": (
            f"Cluster-robust inference used only G={n_clusters} clusters for "
            f"cluster variable '{cluster}'. Few clusters can make t-based clustered "
            "standard errors anti-conservative; use wild cluster bootstrap before "
            "treating significance as publication-ready."
        ),
        "action": "Run seeded wild cluster bootstrap inference and report the cluster count.",
        "claim_degradation": degradation,
        "affected_artifacts": ["model_table.csv"],
    }


def _synthetic_placebo_too_few_donors_risk(n_donors: int) -> dict[str, Any]:
    return {
        "severity": "yellow",
        "code": "SC_PLACEBO_TOO_FEW_DONORS",
        "message": (
            f"Synthetic-control placebo inference was skipped because only {n_donors} "
            "complete donor units were available. In-space placebo p-values are too "
            "fragile with fewer than 10 donors."
        ),
        "action": "Report the synthetic-control fit as exploratory or add donor support before using placebo inference.",
        "claim_degradation": "supplementary_only",
        "affected_artifacts": ["model_table.csv", "synthetic_fit.csv"],
    }


def _iv_weak_instrument_risk(endog_name: str, f_stat: float) -> dict[str, Any]:
    return {
        "severity": "red",
        "code": "IV_WEAK_INSTRUMENT",
        "message": (
            f"First-stage partial F-statistic for endogenous variable '{endog_name}' "
            f"is {f_stat:.3g}, below the conventional F >= 10 weak-instrument screen."
        ),
        "action": "Do not use this IV estimate for claims until stronger excluded instruments or weak-IV robust inference are supplied.",
        "claim_degradation": "not_for_claim",
        "affected_artifacts": ["model_table.csv", "iv_first_stage.json"],
    }


def _iv_first_stage_missing_risk(error: Exception) -> dict[str, Any]:
    return {
        "severity": "red",
        "code": "IV_FIRST_STAGE_MISSING",
        "message": f"IV2SLS completed, but first-stage diagnostics could not be extracted: {error}",
        "action": "Fix first-stage diagnostic extraction before treating the IV estimate as claimable.",
        "claim_degradation": "not_for_claim",
        "affected_artifacts": ["iv_first_stage.json"],
    }


def _as_finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _series_value(container: Any, key: str) -> Any:
    if container is None:
        return None
    try:
        if hasattr(container, "get"):
            value = container.get(key)
        else:
            value = getattr(container, key, None)
    except Exception:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _series_float(container: Any, key: str) -> float | None:
    return _as_finite_float(_series_value(container, key))


def _finite_min(values: Any) -> float | None:
    try:
        import numpy as np

        array = np.asarray(values, dtype=float).reshape(-1)
        finite = array[np.isfinite(array)]
        if finite.size == 0:
            return None
        return float(np.min(finite))
    except Exception:
        return None


def _rdrobust_result_row(result: Any, *, preferred_label: str = "Robust") -> dict[str, Any]:
    coef_table = getattr(result, "coef")
    se_table = getattr(result, "se")
    pv_table = getattr(result, "pv")
    ci_table = getattr(result, "ci")
    labels = list(getattr(coef_table, "index", []))
    if not labels:
        raise Skill4EconError("rdrobust result has no coefficient row labels.")
    label = preferred_label if preferred_label in labels else labels[-1]

    def scalar(table: Any, position: int = 0) -> float:
        cell = table.loc[label]
        if hasattr(cell, "iloc"):
            return float(cell.iloc[position])
        return float(cell)

    ci_values = ci_table.loc[label]
    return {
        "term": str(label),
        "coef": scalar(coef_table),
        "std_error": scalar(se_table),
        "p_value": scalar(pv_table),
        "ci_low": float(ci_values.iloc[0]) if hasattr(ci_values, "iloc") else float(ci_values),
        "ci_high": float(ci_values.iloc[-1]) if hasattr(ci_values, "iloc") else float(ci_values),
    }


def _rdd_continuity_covariates(spec: dict[str, Any], covars: list[str]) -> list[str]:
    value = (
        spec.get("covariate_continuity")
        if "covariate_continuity" in spec
        else spec.get("covariate_continuity_vars", spec.get("continuity_covariates"))
    )
    if isinstance(value, dict):
        value = value.get("covariates") or value.get("variables") or value.get("vars")
    if value is True:
        raw = covars
    elif value is False or value is None or value == "":
        raw = covars
    else:
        raw = listify(value)
    return [item for item in dict.fromkeys(str(item) for item in raw) if item]


def _write_rdd_density_test(ctx: RunContext, running_values: Any, cutoff: float, *, alpha: float) -> dict[str, Any]:
    try:
        import numpy as np
        import rddensity as rddensity_pkg
    except Exception as exc:
        payload = {
            "status": "missing_dependency",
            "backend": "python_rddensity",
            "error_code": "BACKEND_MISSING_DEPENDENCY",
            "message": f"rddensity import failed: {exc}",
        }
        write_json(ctx.artifact("rdd_density_test.json"), payload)
        return payload

    values = np.asarray(running_values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 20:
        payload = {
            "status": "failed",
            "backend": "python_rddensity",
            "error_code": "RDD_DENSITY_TOO_FEW_OBSERVATIONS",
            "message": "RDD density test requires at least 20 finite running-variable observations.",
            "n_obs": int(values.size),
        }
        write_json(ctx.artifact("rdd_density_test.json"), payload)
        return payload

    try:
        result = rddensity_pkg.rddensity(values, c=cutoff)
        test = getattr(result, "test", None)
        p_value = _series_float(test, "p_jk")
        p_source = "p_jk"
        if p_value is None:
            p_value = _series_float(test, "p_asy")
            p_source = "p_asy"
        if p_value is None:
            raise Skill4EconError("rddensity did not return a finite p-value.")
        t_stat = _series_float(test, "t_jk")
        if t_stat is None:
            t_stat = _series_float(test, "t_asy")
        bino = getattr(result, "bino", None)
        payload = {
            "status": "passed" if p_value >= alpha else "failed",
            "backend": "python_rddensity",
            "method": "rddensity",
            "cutoff": cutoff,
            "alpha": alpha,
            "p_value": p_value,
            "p_value_source": p_source,
            "t_stat": t_stat,
            "n_full": _series_float(getattr(result, "n", None), "full"),
            "n_left": _series_float(getattr(result, "n", None), "left"),
            "n_right": _series_float(getattr(result, "n", None), "right"),
            "effective_n_left": _series_float(getattr(result, "n", None), "eff_left"),
            "effective_n_right": _series_float(getattr(result, "n", None), "eff_right"),
            "bandwidth_left": _series_float(getattr(result, "h", None), "left"),
            "bandwidth_right": _series_float(getattr(result, "h", None), "right"),
            "density_left": _series_float(getattr(result, "hat", None), "left"),
            "density_right": _series_float(getattr(result, "hat", None), "right"),
            "density_difference": _series_float(getattr(result, "hat", None), "diff"),
            "binomial_min_p_value": _finite_min(_series_value(bino, "pval")),
            "artifact": "rdd_density_test.json",
        }
    except Exception as exc:
        payload = {
            "status": "failed",
            "backend": "python_rddensity",
            "error_code": "RDD_DENSITY_BACKEND_ERROR",
            "message": f"rddensity failed: {exc}",
        }
    write_json(ctx.artifact("rdd_density_test.json"), payload)
    return payload


def _write_covariate_continuity(
    ctx: RunContext,
    rdrobust_pkg: Any,
    work: Any,
    *,
    running: str,
    covariates: list[str],
    cutoff: float,
    bandwidth: Any,
    cluster: str | None,
    alpha: float,
) -> dict[str, Any]:
    if not covariates:
        payload = {
            "status": "not_requested",
            "covariates": [],
            "rows": [],
            "artifact": None,
        }
        write_json(ctx.artifact("covariate_continuity.json"), payload)
        return payload

    rows: list[dict[str, Any]] = []
    for covariate in covariates:
        kwargs: dict[str, Any] = {"c": cutoff}
        if bandwidth is not None:
            kwargs["h"] = float(bandwidth)
        if cluster:
            kwargs["cluster"] = work[cluster]
        try:
            result = rdrobust_pkg.rdrobust(work[covariate], work[running], **kwargs)
            row = _rdrobust_result_row(result)
            p_value = _as_finite_float(row.get("p_value"))
            row.update(
                {
                    "covariate": covariate,
                    "n_obs": int(len(work)),
                    "cluster": cluster or "",
                    "n_clusters": int(work[cluster].nunique(dropna=True)) if cluster else math.nan,
                    "alpha": alpha,
                    "backend": "rdrobust",
                    "status": "passed" if p_value is not None and p_value >= alpha else "failed",
                }
            )
        except Exception as exc:
            row = {
                "covariate": covariate,
                "status": "failed",
                "backend": "rdrobust",
                "message": str(exc)[:240],
            }
        rows.append(row)

    import pandas as pd

    pd.DataFrame(rows).to_csv(ctx.artifact("covariate_continuity.csv"), index=False, encoding="utf-8-sig")
    payload = {
        "status": "passed" if rows and all(row.get("status") == "passed" for row in rows) else "failed",
        "covariates": covariates,
        "alpha": alpha,
        "artifact": "covariate_continuity.csv",
        "rows": rows,
    }
    write_json(ctx.artifact("covariate_continuity.json"), payload)
    return payload


def _residualize_matrix(matrix: Any, controls: Any):
    import numpy as np

    values = np.asarray(matrix, dtype=float)
    control_values = np.asarray(controls, dtype=float)
    if control_values.size == 0:
        return values
    return values - control_values @ (np.linalg.pinv(control_values) @ values)


def _partial_rsquared(y_resid: Any, z_resid: Any) -> float:
    import numpy as np

    y_values = np.asarray(y_resid, dtype=float)
    z_values = np.asarray(z_resid, dtype=float)
    fitted = z_values @ (np.linalg.pinv(z_values) @ y_values)
    resid = y_values - fitted
    sst = float(np.sum(y_values**2))
    if sst <= 1e-15:
        return math.nan
    return float(1.0 - float(np.sum(resid**2)) / sst)


def _extract_iv_first_stage(result: Any) -> dict[str, Any]:
    import numpy as np
    from scipy.stats import chi2, f

    first_stage = result.first_stage
    endog_names = list(getattr(first_stage.endog, "cols", []) or [])
    instrument_names = list(getattr(first_stage.instr, "cols", []) or [])
    if not endog_names:
        raise Skill4EconError("linearmodels first_stage reported no endogenous variables.")
    if not instrument_names:
        raise Skill4EconError("linearmodels first_stage reported no excluded instruments.")
    individual = getattr(first_stage, "individual", {}) or {}
    weights = np.sqrt(np.asarray(first_stage.weights.ndarray, dtype=float))
    exog_values = weights * np.asarray(first_stage.exog.ndarray, dtype=float)
    instr_values = weights * np.asarray(first_stage.instr.ndarray, dtype=float)
    instr_resid = _residualize_matrix(instr_values, exog_values)

    diagnostics = []
    for position, endog_name in enumerate(endog_names):
        first_result = individual.get(str(endog_name))
        if first_result is None:
            raise Skill4EconError(f"linearmodels first_stage missing individual result for {endog_name}.")

        params = first_result.params
        cov = first_result.cov
        present_instruments = [name for name in instrument_names if name in params.index]
        if len(present_instruments) == len(instrument_names):
            instrument_params = params.loc[present_instruments].to_numpy(dtype=float)
            instrument_cov = cov.loc[present_instruments, present_instruments].to_numpy(dtype=float)
        else:
            n_instr = len(instrument_names)
            instrument_params = params.iloc[-n_instr:].to_numpy(dtype=float)
            instrument_cov = cov.iloc[-n_instr:, -n_instr:].to_numpy(dtype=float)
            present_instruments = instrument_names

        raw_stat = float(instrument_params.T @ np.linalg.pinv(instrument_cov) @ instrument_params)
        df_num = int(len(instrument_params))
        cov_type = str(getattr(first_result, "cov_type", ""))
        if cov_type in {"homoskedastic", "unadjusted"}:
            f_stat = float(raw_stat / df_num)
            df_denom = float(getattr(first_result, "df_resid", math.nan))
            p_value = float(f.sf(f_stat, df_num, df_denom)) if math.isfinite(df_denom) else math.nan
            distribution = f"F({df_num},{df_denom:g})" if math.isfinite(df_denom) else f"F({df_num},nan)"
        else:
            f_stat = raw_stat
            df_denom = None
            p_value = float(chi2.sf(f_stat, df_num))
            distribution = f"chi2({df_num})"

        endog_values = weights * first_stage.endog.pandas[[endog_name]].to_numpy(dtype=float)
        endog_resid = _residualize_matrix(endog_values, exog_values)
        partial_r2 = _partial_rsquared(endog_resid, instr_resid)
        diagnostics.append(
            {
                "endog": str(endog_name),
                "instruments": list(map(str, present_instruments)),
                "partial_f_stat": f_stat,
                "partial_f_p_value": p_value,
                "partial_f_distribution": distribution,
                "partial_f_df": df_num,
                "partial_f_df_denom": df_denom,
                "partial_r_squared": partial_r2,
                "first_stage_rsquared": float(getattr(first_result, "rsquared", math.nan)),
                "cov_type": cov_type,
                "position": int(position),
            }
        )
    return {"status": "ok", "diagnostics": diagnostics}


def _ols_numpy(
    df,
    y: str,
    terms: list[str],
    *,
    cluster: str | None = None,
    rank_for_correction: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import numpy as np

    columns = [y, *terms]
    if cluster:
        columns.append(cluster)
    work = df[columns].dropna().copy()
    if len(work) <= len(terms):
        raise Skill4EconError("OLS sample too small for the requested design matrix.")
    y_arr = work[y].to_numpy(dtype=float)
    X = work[terms].to_numpy(dtype=float)
    n, k = X.shape
    rank = int(np.linalg.matrix_rank(X))
    if rank < k:
        raise Skill4EconError(
            f"OLS design matrix is rank deficient: rank={rank}, columns={k}. "
            "Fix collinearity or unsupported dummy/event terms before estimating."
        )
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y_arr
    resid = y_arr - X @ beta
    correction_rank = max(int(rank_for_correction or k), k)
    df_resid = max(n - correction_rank, 1)
    n_clusters: int | None = None
    df_inference = df_resid
    if cluster:
        groups = work[cluster].astype(str).to_numpy()
        unique_groups = sorted(set(groups))
        n_clusters = len(unique_groups)
        if len(unique_groups) >= 2:
            meat = np.zeros((k, k))
            for group in unique_groups:
                idx = groups == group
                xg = X[idx, :]
                ug = resid[idx]
                score = xg.T @ ug
                meat += np.outer(score, score)
            scale = (len(unique_groups) / (len(unique_groups) - 1)) * ((n - 1) / df_resid)
            cov = scale * xtx_inv @ meat @ xtx_inv
            cov_type = f"cluster:{cluster}:numpy"
            df_inference = len(unique_groups) - 1
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
        rows.append(_inference_row(term, float(coef), float(se), df_inference))
    meta = {
        "nobs": int(n),
        "df_resid": int(df_resid),
        "df_inference": _df_payload(df_inference),
        "cov_type": cov_type,
        "rank_for_correction": int(correction_rank),
    }
    if n_clusters is not None:
        meta["n_clusters"] = int(n_clusters)
        if cov_type.startswith("cluster:") and n_clusters < 30 and cluster:
            meta["inference_risks"] = [_few_cluster_inference_risk(cluster, n_clusters)]
    return rows, meta


def _with_constant(df, columns: list[str], name: str = "_const"):
    work = df.copy()
    work[name] = 1.0
    return work, [name, *columns]


def _absorbed_fe_rank(df: Any, fe_cols: list[str]) -> int:
    if not fe_cols:
        return 0
    if len(fe_cols) == 1:
        return int(df[fe_cols[0]].astype(str).nunique())
    if len(fe_cols) != 2:
        levels = sum(int(df[col].astype(str).nunique()) for col in fe_cols)
        return max(levels - len(fe_cols) + 1, 0)

    left = [f"0:{value}" for value in df[fe_cols[0]].astype(str)]
    right = [f"1:{value}" for value in df[fe_cols[1]].astype(str)]
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for a, b in zip(left, right):
        union(a, b)
    components = {find(node) for node in parent}
    return max(len(parent) - len(components), 0)


def _within_transform(df: Any, columns: list[str], fe_cols: list[str], *, max_iter: int = 100, tol: float = 1e-10):
    import numpy as np

    transformed = df[columns].astype(float).copy()
    groups = [df[col].astype(str) for col in fe_cols]
    for _ in range(max_iter):
        previous = transformed.to_numpy(dtype=float, copy=True)
        for group in groups:
            transformed = transformed - transformed.groupby(group).transform("mean")
        delta = float(np.nanmax(np.abs(transformed.to_numpy(dtype=float) - previous)))
        if delta <= tol:
            break
    return transformed


def _absorbed_fe_ols_frame(df: Any, y: str, terms: list[str], fe_cols: list[str]):
    transformed = _within_transform(df, [y, *terms], fe_cols)
    rank_for_correction = len(terms) + _absorbed_fe_rank(df, fe_cols)
    meta = {
        "absorbed_fixed_effects": list(fe_cols),
        "absorbed_fe_rank": int(rank_for_correction - len(terms)),
        "fe_transform": "alternating_within_demeaning",
    }
    return transformed, rank_for_correction, meta


def _term_coef(rows: list[dict[str, Any]], term: str) -> float:
    return float(next(row["coef"] for row in rows if row["term"] == term))


def _clustered_mean_se(values: Any, clusters: Any) -> tuple[float, int]:
    import numpy as np

    arr = np.asarray(values, dtype=float)
    group_values = np.asarray(clusters)
    if len(arr) != len(group_values):
        raise Skill4EconError("Clustered score SE received values and clusters with different lengths.")
    unique_groups = np.unique(group_values)
    n_clusters = int(len(unique_groups))
    if n_clusters < 2:
        raise Skill4EconError("Clustered score SE requires at least two clusters.")
    centered = arr - float(np.mean(arr))
    cluster_sums = np.asarray([float(np.sum(centered[group_values == group])) for group in unique_groups], dtype=float)
    variance = (n_clusters / (n_clusters - 1.0)) * float(np.sum(cluster_sums**2)) / (len(arr) ** 2)
    return float(math.sqrt(max(variance, 0.0))), n_clusters


def _bootstrap_mediation_indirect(
    work: Any,
    *,
    y: str,
    treat: str,
    mediator: str,
    x: list[str],
    reps: int,
    seed: int,
) -> dict[str, Any]:
    import numpy as np

    rng = np.random.default_rng(seed)
    draws: list[float] = []
    nobs = int(len(work))
    for _ in range(reps):
        sample = work.iloc[rng.integers(0, nobs, size=nobs)].reset_index(drop=True)
        try:
            m_df, m_terms = _with_constant(sample, [treat, *x])
            m_rows, _ = _ols_numpy(m_df, mediator, m_terms)
            y_direct_df, y_direct_terms = _with_constant(sample, [treat, mediator, *x])
            direct_rows, _ = _ols_numpy(y_direct_df, y, y_direct_terms)
            draw = _term_coef(m_rows, treat) * _term_coef(direct_rows, mediator)
        except Exception:
            continue
        if math.isfinite(draw):
            draws.append(float(draw))
    if len(draws) < 30:
        raise Skill4EconError("Mediation bootstrap produced too few valid resamples.")
    arr = np.asarray(draws, dtype=float)
    return {
        "indirect_effect_draws": [float(value) for value in arr],
        "std_error": float(np.std(arr, ddof=1)),
        "ci_low": float(np.quantile(arr, 0.025)),
        "ci_high": float(np.quantile(arr, 0.975)),
        "successful_reps": int(len(arr)),
        "requested_reps": int(reps),
        "seed": int(seed),
        "se_method": "seeded_nonparametric_bootstrap_percentile",
    }


def _synthetic_control_fit(
    pivot: Any,
    *,
    target_unit: Any,
    donor_units: list[Any],
    pre_mask: Any,
    post_mask: Any,
) -> dict[str, Any]:
    import numpy as np
    from scipy.optimize import minimize

    pre_arr = np.asarray(pre_mask, dtype=bool)
    post_arr = np.asarray(post_mask, dtype=bool)
    complete_donors = [
        donor
        for donor in donor_units
        if donor in pivot.columns and not pivot.loc[:, donor].isna().any()
    ]
    if len(complete_donors) == 0:
        raise Skill4EconError("No complete donor units for synthetic control.")
    if pivot.loc[pre_arr, target_unit].isna().any() or pivot.loc[post_arr, target_unit].isna().any():
        raise Skill4EconError(f"Synthetic control target unit has missing outcomes: {target_unit}")
    X0 = pivot.loc[pre_arr, complete_donors].to_numpy(dtype=float)
    X1 = pivot.loc[pre_arr, target_unit].to_numpy(dtype=float)
    n_donors = X0.shape[1]
    objective = lambda w: float(np.sum((X1 - X0 @ w) ** 2))
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = [(0.0, 1.0)] * n_donors
    result = minimize(objective, np.ones(n_donors) / n_donors, bounds=bounds, constraints=cons)
    if not result.success:
        raise Skill4EconError(f"Synthetic control optimizer failed: {result.message}")
    weights = result.x
    synthetic = pivot.loc[:, complete_donors].to_numpy(dtype=float) @ weights
    treated_path = pivot.loc[:, target_unit].to_numpy(dtype=float)
    gap = treated_path - synthetic
    pre_rmspe = float(np.sqrt(np.mean(gap[pre_arr] ** 2)))
    post_rmspe = float(np.sqrt(np.mean(gap[post_arr] ** 2))) if post_arr.any() else math.nan
    ratio = float(post_rmspe / pre_rmspe) if math.isfinite(pre_rmspe) and pre_rmspe > 1e-12 else math.inf
    post_att = float(np.mean(gap[post_arr])) if post_arr.any() else math.nan
    return {
        "target_unit": target_unit,
        "donors": complete_donors,
        "weights": weights,
        "synthetic": synthetic,
        "treated": treated_path,
        "gap": gap,
        "pre_rmspe": pre_rmspe,
        "post_rmspe": post_rmspe,
        "post_pre_rmspe_ratio": ratio,
        "post_att": post_att,
    }


def _path_from_spec_value(value: Any, role: str) -> Path:
    if not value:
        raise Skill4EconError(f"Spec must provide {role}.")
    path = Path(str(value))
    if not path.is_absolute():
        workspace_path = REPO_ROOT / path
        repo_path = ROOT / path
        path = workspace_path if workspace_path.exists() else repo_path
    if not path.exists():
        raise Skill4EconError(f"{role} not found: {path}")
    return path


def _learner_pair(kind: str, random_seed: int):
    if kind == "gradient_boosting":
        from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

        return GradientBoostingRegressor(random_state=random_seed), GradientBoostingClassifier(random_state=random_seed)
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

    return (
        RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=random_seed),
        RandomForestClassifier(n_estimators=100, min_samples_leaf=2, random_state=random_seed),
    )


def _logit_pscore(values: Any):
    import numpy as np

    pscore = np.clip(np.asarray(values, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(pscore / (1.0 - pscore))


def _nearest_same_group_variance(scores: Any, outcomes: Any):
    import numpy as np

    score_values = np.asarray(scores, dtype=float)
    outcome_values = np.asarray(outcomes, dtype=float)
    n = len(outcome_values)
    if n == 0:
        return np.asarray([], dtype=float)
    fallback = float(np.var(outcome_values, ddof=1)) if n > 1 else 0.0
    if n <= 1:
        return np.asarray([fallback], dtype=float)
    distances = np.abs(score_values[:, None] - score_values[None, :])
    np.fill_diagonal(distances, np.inf)
    nearest = np.argmin(distances, axis=1)
    variances = ((outcome_values - outcome_values[nearest]) ** 2) / 2.0
    variances[~np.isfinite(variances)] = fallback
    return variances


def _matching_att_with_ai_se(work: Any, y: str, treat: str, *, caliper: float | None, with_replacement: bool) -> dict[str, Any]:
    import numpy as np

    treated = work[work[treat] == 1].copy()
    control = work[work[treat] == 0].copy()
    treated_score = _logit_pscore(treated["_pscore"])
    control_score = _logit_pscore(control["_pscore"])
    treated_y = treated[y].to_numpy(dtype=float)
    control_y = control[y].to_numpy(dtype=float)
    distance_matrix = np.abs(treated_score[:, None] - control_score[None, :])
    max_distance = math.inf if caliper is None else float(caliper)

    if with_replacement:
        nearest = np.argmin(distance_matrix, axis=1)
        distances = distance_matrix[np.arange(len(treated)), nearest]
        keep = distances <= max_distance
        treated_pos = np.where(keep)[0]
        control_pos = nearest[keep]
        matched_distances = distances[keep]
    else:
        candidates = [
            (float(distance_matrix[i, j]), int(i), int(j))
            for i in range(distance_matrix.shape[0])
            for j in range(distance_matrix.shape[1])
            if distance_matrix[i, j] <= max_distance
        ]
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        used_treated: set[int] = set()
        used_control: set[int] = set()
        selected: list[tuple[float, int, int]] = []
        for distance, i, j in candidates:
            if i in used_treated or j in used_control:
                continue
            used_treated.add(i)
            used_control.add(j)
            selected.append((distance, i, j))
        treated_pos = np.asarray([item[1] for item in selected], dtype=int)
        control_pos = np.asarray([item[2] for item in selected], dtype=int)
        matched_distances = np.asarray([item[0] for item in selected], dtype=float)

    if len(treated_pos) == 0:
        raise Skill4EconError("PSM caliper removed all nearest-neighbor matches.")

    pair_effects = treated_y[treated_pos] - control_y[control_pos]
    att = float(np.mean(pair_effects))
    treated_variance = _nearest_same_group_variance(treated_score, treated_y)
    control_variance = _nearest_same_group_variance(control_score, control_y)
    control_match_counts = np.bincount(control_pos, minlength=len(control_y)).astype(float)
    n_matched = int(len(treated_pos))
    ai_variance = float(
        (
            np.sum(treated_variance[treated_pos])
            + np.sum((control_match_counts**2) * control_variance)
        )
        / (n_matched**2)
    )
    se = float(math.sqrt(max(ai_variance, 0.0)))
    return {
        "att": att,
        "std_error": se,
        "n_matched": n_matched,
        "treated_n": int(len(treated)),
        "control_n": int(len(control)),
        "mean_match_distance": float(np.mean(matched_distances)),
        "max_match_distance": float(np.max(matched_distances)),
        "dropped_treated": int(len(treated) - n_matched),
        "with_replacement": bool(with_replacement),
        "se_method": "abadie_imbens_2006_nn_att_pscore",
    }


def _ipw_point_estimates(y_values: Any, treat_values: Any, pscore_values: Any) -> tuple[float, float]:
    import numpy as np

    y_arr = np.asarray(y_values, dtype=float)
    treat_arr = np.asarray(treat_values, dtype=float)
    pscore = np.clip(np.asarray(pscore_values, dtype=float), 1e-6, 1 - 1e-6)
    treated_share = float(treat_arr.mean())
    if treated_share <= 0 or treated_share >= 1:
        raise Skill4EconError("IPW requires both treated and control observations.")
    ate = float(np.mean(treat_arr * y_arr / pscore - (1 - treat_arr) * y_arr / (1 - pscore)))
    att = float(
        (np.mean(treat_arr * y_arr) - np.mean((1 - treat_arr) * pscore * y_arr / (1 - pscore)))
        / treated_share
    )
    return ate, att


def _bootstrap_ipw(
    y_values: Any,
    treat_values: Any,
    pscore_values: Any,
    *,
    reps: int,
    seed: int,
) -> dict[str, Any]:
    import numpy as np

    y_arr = np.asarray(y_values, dtype=float)
    treat_arr = np.asarray(treat_values, dtype=float)
    pscore = np.asarray(pscore_values, dtype=float)
    rng = np.random.default_rng(seed)
    ate_draws: list[float] = []
    att_draws: list[float] = []
    n = len(y_arr)
    for _ in range(reps):
        idx = rng.integers(0, n, size=n)
        try:
            ate, att = _ipw_point_estimates(y_arr[idx], treat_arr[idx], pscore[idx])
        except Skill4EconError:
            continue
        ate_draws.append(ate)
        att_draws.append(att)
    if len(ate_draws) < 30:
        raise Skill4EconError("IPW bootstrap produced too few valid resamples with both treatment arms.")

    def _summary(draws: list[float]) -> dict[str, float]:
        arr = np.asarray(draws, dtype=float)
        return {
            "std_error": float(np.std(arr, ddof=1)),
            "ci_low": float(np.quantile(arr, 0.025)),
            "ci_high": float(np.quantile(arr, 0.975)),
        }

    return {
        "ate": _summary(ate_draws),
        "att": _summary(att_draws),
        "successful_reps": int(len(ate_draws)),
        "requested_reps": int(reps),
        "seed": int(seed),
        "se_method": "seeded_nonparametric_bootstrap_fixed_pscore",
    }


def _wild_cluster_bootstrap_ols(
    df: Any,
    *,
    y: str,
    terms: list[str],
    cluster: str,
    reps: int,
    seed: int,
    rank_for_correction: int | None = None,
) -> dict[str, Any]:
    import numpy as np

    work = df[[y, *terms, cluster]].dropna().copy()
    base_rows, _ = _ols_numpy(work, y, terms, cluster=cluster, rank_for_correction=rank_for_correction)
    base = {row["term"]: row for row in base_rows}
    y_arr = work[y].to_numpy(dtype=float)
    X = work[terms].to_numpy(dtype=float)
    beta = np.asarray([base[term]["coef"] for term in terms], dtype=float)
    fitted = X @ beta
    resid = y_arr - fitted
    groups = work[cluster].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    rng = np.random.default_rng(seed)
    exceed = {term: 0 for term in terms}
    successful = 0
    for _ in range(reps):
        multipliers = {group: rng.choice([-1.0, 1.0]) for group in unique_groups}
        y_star = fitted + np.asarray([multipliers[group] for group in groups], dtype=float) * resid
        boot = work.copy()
        boot["__wild_y"] = y_star
        try:
            boot_rows, _ = _ols_numpy(boot, "__wild_y", terms, cluster=cluster, rank_for_correction=rank_for_correction)
        except Skill4EconError:
            continue
        successful += 1
        for row in boot_rows:
            term = row["term"]
            se = float(row.get("std_error", math.nan))
            if not math.isfinite(se) or se <= 0:
                continue
            boot_t = abs((float(row["coef"]) - float(base[term]["coef"])) / se)
            observed_t = abs(float(base[term].get("t_stat", math.nan)))
            if math.isfinite(observed_t) and boot_t >= observed_t:
                exceed[term] += 1
    if successful < 30:
        raise Skill4EconError("Wild cluster bootstrap produced too few valid resamples.")
    rows = [
        {
            "term": term,
            "wild_cluster_p_value": float((1 + exceed[term]) / (1 + successful)),
            "wild_cluster_reps": int(successful),
            "wild_cluster_seed": int(seed),
            "wild_cluster_distribution": "rademacher",
            "n_clusters": int(len(unique_groups)),
        }
        for term in terms
    ]
    return {
        "rows": rows,
        "successful_reps": int(successful),
        "requested_reps": int(reps),
        "seed": int(seed),
        "distribution": "rademacher",
        "n_clusters": int(len(unique_groups)),
    }


def py_preflight(ctx: RunContext) -> dict[str, Any]:
    report = dependency_report()
    write_json(ctx.artifact("dependency_report.json"), report)
    messages = ["Python dependency preflight completed."]
    write_audit(ctx, "ok", messages, dependencies=report)
    return write_manifest(ctx, "ok", dependencies=report)


def data_audit(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires data/input path for run state."])
    if planned:
        return planned
    df, path = read_table(ctx.spec)
    profile = {
        "path": str(path),
        "sha256": file_sha256(path),
        "rows": int(len(df)),
        "columns": list(map(str, df.columns)),
        "missing_by_column": {str(k): int(v) for k, v in df.isna().sum().items()},
        "duplicate_rows": int(df.duplicated().sum()),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
    }
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    if id_col and time_col and id_col in df.columns and time_col in df.columns:
        profile["panel"] = {
            "entities": int(df[id_col].nunique()),
            "periods": int(df[time_col].nunique()),
            "entity_time_duplicates": int(df.duplicated([id_col, time_col]).sum()),
        }
    write_json(ctx.artifact("data_profile.json"), profile)
    write_audit(ctx, "ok", ["Data audit completed."], profile=profile)
    return write_manifest(ctx, "ok", data_profile=profile)


def ols_cluster(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y and x columns. Optional cluster column."])
    if planned:
        return planned

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    if not y or not x:
        raise Skill4EconError("ols_cluster requires y and at least one x/covar.")
    require_columns(df, [y, *x], "OLS")
    cluster = str(ctx.spec.get("cluster")) if ctx.spec.get("cluster") else None
    if cluster:
        require_columns(df, [cluster], "cluster")
    work, terms = _with_constant(df, x)
    rows, meta = _ols_numpy(work, y, terms, cluster=cluster)
    if cluster and int(meta.get("n_clusters") or 999999) < 30 and bool(ctx.spec.get("wild_cluster_bootstrap", True)):
        import pandas as pd

        wild = _wild_cluster_bootstrap_ols(
            work,
            y=y,
            terms=terms,
            cluster=cluster,
            reps=max(39, int(ctx.spec.get("wild_cluster_bootstrap_reps", 99))),
            seed=int(ctx.spec.get("wild_cluster_seed", ctx.spec.get("random_seed", 20260601))),
        )
        wild_by_term = {row["term"]: row for row in wild["rows"]}
        rows = [{**row, **wild_by_term.get(row["term"], {})} for row in rows]
        pd.DataFrame(wild["rows"]).to_csv(ctx.artifact("wild_cluster_bootstrap.csv"), index=False, encoding="utf-8-sig")
        write_json(ctx.artifact("wild_cluster_bootstrap.json"), wild)
        meta["wild_cluster_bootstrap"] = {
            "artifact": "wild_cluster_bootstrap.csv",
            "successful_reps": wild["successful_reps"],
            "distribution": wild["distribution"],
            "seed": wild["seed"],
        }
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["OLS completed."], estimator="numpy OLS", **meta)
    return write_manifest(ctx, "ok", estimator="numpy OLS", **meta)


def panel_fe_re(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, x, id, and time columns."])
    if planned:
        return planned
    try:
        from linearmodels.panel import PanelOLS, RandomEffects
    except Exception as exc:
        raise Skill4EconError("panel_fe_re requires linearmodels; no fallback estimator was run.") from exc

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    require_columns(df, [y, id_col, time_col, *x], "panel")
    if not y or not x or not id_col or not time_col:
        raise Skill4EconError("panel_fe_re requires y, at least one x/covar, id, and time.")
    model = str(ctx.spec.get("model", "fe")).lower()
    if model not in {"fe", "re"}:
        raise Skill4EconError("panel_fe_re model must be 'fe' or 're'.")
    panel = df.set_index([id_col, time_col]).sort_index()
    panel = panel.copy()
    panel["_const"] = 1.0
    X = panel[["_const", *x]]
    effects = set(listify(ctx.spec.get("fe")))
    if not effects:
        effects = {"entity", "time"}
    try:
        if model == "re":
            result = RandomEffects(panel[y], X).fit()
            estimator = "linearmodels.RandomEffects"
        else:
            result = PanelOLS(
                panel[y],
                X,
                entity_effects="entity" in effects or id_col in effects,
                time_effects="time" in effects or time_col in effects,
            ).fit(cov_type="clustered", cluster_entity=True)
            estimator = "linearmodels.PanelOLS"
    except Exception as exc:
        raise Skill4EconError(f"linearmodels panel estimation failed; no fallback was run: {exc}") from exc
    rows = [
        {
            "term": term,
            "coef": float(result.params[term]),
            "std_error": float(result.std_errors[term]),
            "p_value": float(result.pvalues[term]),
            "t_stat": float(result.tstats[term]),
        }
        for term in result.params.index
    ]
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["Panel model completed."], estimator=estimator, panel_model=model)
    return write_manifest(ctx, "ok", estimator=estimator, panel_model=model)


def did_twfe_event(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Requires y, treat, post, id, and time columns for TWFE DID run."],
    )
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    treat = str(ctx.spec.get("treat"))
    post = str(ctx.spec.get("post"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    cluster = str(ctx.spec.get("cluster", id_col))
    require_columns(df, [y, treat, post, id_col, time_col, cluster, *x], "DID")

    columns = [y, treat, post, id_col, time_col, *x]
    if cluster not in columns:
        columns.append(cluster)
    work = df[columns].dropna().copy()
    work["_did_treat_post"] = work[treat].astype(float) * work[post].astype(float)
    keep_terms = ["_did_treat_post", *x]
    design, rank_for_correction, fe_meta = _absorbed_fe_ols_frame(work, y, keep_terms, [id_col, time_col])
    design[cluster] = work[cluster].to_numpy()
    rows, meta = _ols_numpy(design, y, keep_terms, cluster=cluster, rank_for_correction=rank_for_correction)
    meta.update(fe_meta)
    rows = [row for row in rows if row["term"] in {"_did_treat_post", *x}]
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["TWFE DID completed."], estimator="numpy TWFE", **meta)
    return write_manifest(ctx, "ok", estimator="numpy TWFE", **meta)


def iv_2sls(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, x, endog, and instrument columns."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    endog = str(ctx.spec.get("endog"))
    instrument = str(ctx.spec.get("instrument"))
    require_columns(df, [y, endog, instrument, *x], "IV")
    exog = " + ".join(x) if x else "1"
    formula = f"{y} ~ 1"
    if x:
        formula += " + " + exog
    formula += f" + [{endog} ~ {instrument}]"
    try:
        from linearmodels.iv import IV2SLS

        result = IV2SLS.from_formula(formula, df).fit(cov_type="robust")
        rows = [
            {
                "term": term,
                "coef": float(result.params[term]),
                "std_error": float(result.std_errors[term]),
                "p_value": float(result.pvalues[term]),
                "t_stat": float(result.tstats[term]),
            }
            for term in result.params.index
        ]
        estimator = "linearmodels.IV2SLS"
        meta = {"formula": formula}
    except Exception as exc:
        raise Skill4EconError(f"linearmodels IV2SLS failed; no fallback was run: {exc}") from exc
    warnings: list[dict[str, Any]] = []
    try:
        first_stage = _extract_iv_first_stage(result)
    except Exception as exc:
        first_stage = {"status": "failed", "error": str(exc), "error_type": exc.__class__.__name__}
        warnings.append(_iv_first_stage_missing_risk(exc))
    else:
        for diagnostic in first_stage.get("diagnostics") or []:
            f_stat = float(diagnostic.get("partial_f_stat", math.nan))
            endog_name = str(diagnostic.get("endog") or "endog")
            rows.append(
                {
                    "term": f"first_stage_F_{endog_name}",
                    "coef": f_stat,
                    "std_error": math.nan,
                    "p_value": diagnostic.get("partial_f_p_value"),
                    "t_stat": math.nan,
                    "partial_r_squared": diagnostic.get("partial_r_squared"),
                    "f_dist": diagnostic.get("partial_f_distribution"),
                }
            )
            if math.isfinite(f_stat) and f_stat < 10.0:
                warnings.append(_iv_weak_instrument_risk(endog_name, f_stat))
    write_json(ctx.artifact("iv_first_stage.json"), first_stage)
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["IV2SLS completed."], estimator=estimator, warnings=warnings, first_stage=first_stage, **meta)
    return write_manifest(
        ctx,
        "ok",
        estimator=estimator,
        warnings=warnings,
        first_stage_artifact="iv_first_stage.json",
        **meta,
    )


def rdd_local_linear(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, running, cutoff. Optional bandwidth."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    running = str(ctx.spec.get("running"))
    cutoff = float(ctx.spec.get("cutoff", 0))
    bandwidth = ctx.spec.get("bandwidth")
    require_columns(df, [y, running], "RDD")
    work = df.copy()
    work["_running_centered"] = work[running] - cutoff
    if bandwidth is not None:
        bw = float(bandwidth)
        work = work[work["_running_centered"].abs() <= bw].copy()
    work["_treated_right"] = (work["_running_centered"] >= 0).astype(int)
    if len(work) < 8:
        raise Skill4EconError("RDD sample too small after bandwidth filtering.")
    work, terms = _with_constant(work, ["_treated_right", "_running_centered"])
    rows, meta = _ols_numpy(work, y, terms)
    write_model_table(ctx, rows)
    write_audit(
        ctx,
        "ok",
        ["Minimal local-linear RDD completed. Prefer rdrobust for publication runs."],
        estimator="numpy local-linear RDD",
        **meta,
    )
    return write_manifest(ctx, "ok", estimator="numpy local-linear RDD", **meta)


def rdrobust_rdd(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Dependency-gated rdrobust RDD adapter. Requires y and running."])
    if planned:
        return planned
    try:
        import rdrobust as rdrobust_pkg
    except Exception:
        return missing_dependency(ctx, "rdrobust", "Calonico-Cattaneo-Titiunik robust RDD inference")

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    running = str(ctx.spec.get("running"))
    cutoff = float(ctx.spec.get("cutoff", 0))
    covars = listify(ctx.spec.get("covars") or ctx.spec.get("x"))
    continuity_covariates = _rdd_continuity_covariates(ctx.spec, covars)
    cluster = str(ctx.spec.get("cluster")) if ctx.spec.get("cluster") else None
    needed = list(dict.fromkeys([y, running, *covars, *continuity_covariates, *([cluster] if cluster else [])]))
    require_columns(df, needed, "rdrobust RDD")
    work = df[needed].dropna().copy()
    kwargs: dict[str, Any] = {"c": cutoff}
    if ctx.spec.get("bandwidth") is not None:
        kwargs["h"] = float(ctx.spec["bandwidth"])
    if covars:
        kwargs["covs"] = work[covars]
    if cluster:
        kwargs["cluster"] = work[cluster]
    try:
        result = rdrobust_pkg.rdrobust(work[y], work[running], **kwargs)
    except Exception as exc:
        raise Skill4EconError(f"rdrobust failed; no fallback estimator was run: {exc}") from exc

    rows: list[dict[str, Any]] = []
    try:
        coef_table = getattr(result, "coef")
        se_table = getattr(result, "se")
        pv_table = getattr(result, "pv")
        ci_table = getattr(result, "ci")
        for label in list(getattr(coef_table, "index", [])):
            coef = float(coef_table.loc[label].iloc[0] if hasattr(coef_table.loc[label], "iloc") else coef_table.loc[label])
            se = float(se_table.loc[label].iloc[0] if hasattr(se_table.loc[label], "iloc") else se_table.loc[label])
            p_value = float(pv_table.loc[label].iloc[0] if hasattr(pv_table.loc[label], "iloc") else pv_table.loc[label])
            ci_values = ci_table.loc[label]
            ci_low = float(ci_values.iloc[0])
            ci_high = float(ci_values.iloc[-1])
            rows.append(
                {
                    "term": str(label),
                    "coef": coef,
                    "std_error": se,
                    "p_value": p_value,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "n_obs": int(len(work)),
                    "backend": "rdrobust",
                    "cluster": cluster or "",
                    "n_clusters": int(work[cluster].nunique(dropna=True)) if cluster else math.nan,
                }
            )
    except Exception as exc:
        raise Skill4EconError(f"rdrobust result parser failed; no partial rows were written: {exc}") from exc
    if not rows:
        raise Skill4EconError("rdrobust returned no coefficient rows.")
    try:
        bws = getattr(result, "bws")
        bws.reset_index().to_csv(ctx.artifact("rdd_bandwidth.csv"), index=False, encoding="utf-8-sig")
    except Exception:
        bws = None
    variable_units = ctx.spec.get("variable_units") if isinstance(ctx.spec.get("variable_units"), dict) else {}
    outcome_unit = str(
        variable_units.get(y)
        or ctx.spec.get("outcome_unit")
        or ctx.spec.get("y_unit")
        or ""
    )
    running_unit = str(
        variable_units.get(running)
        or ctx.spec.get("running_unit")
        or ""
    )
    summary_rows = []
    for variable in [y, running]:
        series = work[variable]
        unit = outcome_unit if variable == y else running_unit
        summary_rows.append(
            {
                "variable": variable,
                "n": int(series.shape[0]),
                "mean": float(series.mean()),
                "sd": float(series.std(ddof=1)) if series.shape[0] > 1 else 0.0,
                "min": float(series.min()),
                "max": float(series.max()),
                "unit": unit,
            }
        )
    try:
        import pandas as pd

        pd.DataFrame(summary_rows).to_csv(ctx.artifact("summary_stats.csv"), index=False, encoding="utf-8-sig")
        rdplot_bins = []
        bins_per_side = int(ctx.spec.get("rdplot_bins_per_side") or 12)
        centered = work[[y, running]].copy()
        centered["_running_centered"] = centered[running] - cutoff
        for side_name, side_df in (("left", centered[centered["_running_centered"] < 0]), ("right", centered[centered["_running_centered"] >= 0])):
            if side_df.empty:
                continue
            side_df = side_df.copy()
            side_df["_bin"] = pd.cut(side_df["_running_centered"], bins=min(bins_per_side, max(1, len(side_df))), duplicates="drop")
            for interval, group in side_df.groupby("_bin", observed=True):
                if group.empty:
                    continue
                rdplot_bins.append(
                    {
                        "side": side_name,
                        "bin_left": float(interval.left),
                        "bin_right": float(interval.right),
                        "running_centered_mean": float(group["_running_centered"].mean()),
                        "outcome_mean": float(group[y].mean()),
                        "n": int(len(group)),
                    }
                )
        if rdplot_bins:
            figures_dir = ctx.artifact("figures")
            figures_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rdplot_bins).to_csv(figures_dir / "rdplot_bins.csv", index=False, encoding="utf-8-sig")
            write_json(
                figures_dir / "manifest.json",
                {
                    "version": "skill4econ.figure_manifest.v1",
                    "figures": [
                        {
                            "figure_id": "rdplot_style_bins",
                            "kind": "rdplot_style_binned_scatter",
                            "path": "figures/rdplot_bins.csv",
                            "x": running,
                            "y": y,
                            "cutoff": cutoff,
                            "status": "computed",
                        }
                    ],
                },
            )
        placebo_rows = []
        for donut in listify(ctx.spec.get("donut_holes") or [0.05, 0.1, 0.2]):
            try:
                donut_width = float(donut)
            except (TypeError, ValueError):
                continue
            placebo_work = work[(work[running] - cutoff).abs() >= donut_width].copy()
            if placebo_work.empty:
                placebo_rows.append({"family": "donut_placebo", "donut": donut_width, "status": "insufficient_sample"})
                continue
            placebo_kwargs = dict(kwargs)
            if covars:
                placebo_kwargs["covs"] = placebo_work[covars]
            try:
                placebo = rdrobust_pkg.rdrobust(placebo_work[y], placebo_work[running], **placebo_kwargs)
                robust_label = "Robust" if "Robust" in list(getattr(placebo.coef, "index", [])) else list(getattr(placebo.coef, "index", []))[-1]
                coef = float(placebo.coef.loc[robust_label].iloc[0])
                se = float(placebo.se.loc[robust_label].iloc[0])
                p_value = float(placebo.pv.loc[robust_label].iloc[0])
                placebo_rows.append(
                    {
                        "family": "donut_placebo",
                        "donut": donut_width,
                        "term": str(robust_label),
                        "coef": coef,
                        "std_error": se,
                        "p_value": p_value,
                        "n_obs": int(len(placebo_work)),
                        "status": "computed",
                    }
                )
            except Exception as exc:
                placebo_rows.append(
                    {
                        "family": "donut_placebo",
                        "donut": donut_width,
                        "status": "failed",
                        "message": str(exc)[:240],
                    }
                )
        pd.DataFrame(placebo_rows).to_csv(ctx.artifact("placebo_tests.csv"), index=False, encoding="utf-8-sig")
    except Exception:
        pass
    alpha = float(ctx.spec.get("diagnostic_alpha", 0.05))
    density_test = _write_rdd_density_test(ctx, work[running], cutoff, alpha=alpha)
    covariate_continuity = _write_covariate_continuity(
        ctx,
        rdrobust_pkg,
        work,
        running=running,
        covariates=continuity_covariates,
        cutoff=cutoff,
        bandwidth=ctx.spec.get("bandwidth"),
        cluster=cluster,
        alpha=alpha,
    )
    diagnostics = {
        "version": "skill4econ.rdd_diagnostics.v1",
        "estimator": "rdrobust",
        "cutoff": cutoff,
        "nobs": int(len(work)),
        "cluster": cluster,
        "n_clusters": int(work[cluster].nunique(dropna=True)) if cluster else None,
        "bandwidth_path": "rdd_bandwidth.csv" if bws is not None else None,
        "rd_plot": {
            "status": "computed",
            "path": "figures/manifest.json",
        },
        "placebo_tests": {
            "status": "computed",
            "path": "placebo_tests.csv",
        },
        "density_test": density_test,
        "covariate_continuity": covariate_continuity,
    }
    write_json(ctx.artifact("rdd_diagnostics.json"), diagnostics)
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["rdrobust RDD completed."], estimator="rdrobust", cutoff=cutoff)
    return write_manifest(
        ctx,
        "ok",
        estimator="rdrobust",
        cutoff=cutoff,
        nobs=int(len(work)),
        claim_level="main_estimate",
        paper_readiness="paper_ready",
        main_claim_available=True,
        rdd_diagnostics=diagnostics,
    )


def did_event_study(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Requires y, id, time, and either event_time or gvar/adoption_time. Optional window=[min,max]."],
    )
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    cluster = str(ctx.spec.get("cluster", id_col))
    event_time = ctx.spec.get("event_time")
    gvar = ctx.spec.get("gvar") or ctx.spec.get("adoption_time") or ctx.spec.get("treat_time")
    needed = [y, id_col, time_col, *x]
    if cluster not in needed:
        needed.append(cluster)
    if event_time:
        needed.append(str(event_time))
    elif gvar:
        needed.append(str(gvar))
    else:
        raise Skill4EconError("did_event_study requires event_time or gvar/adoption_time.")
    require_columns(df, needed, "event study")
    work = df[needed].dropna(subset=[y, id_col, time_col]).copy()
    if event_time:
        work["_event_time"] = work[str(event_time)]
        treated_mask = work["_event_time"].notna()
    else:
        work["_gvar"] = work[str(gvar)].fillna(0)
        treated_mask = work["_gvar"].astype(float) > 0
        work["_event_time"] = work[time_col].astype(float) - work["_gvar"].astype(float)
    window = ctx.spec.get("window", [-3, 3])
    lo, hi = int(window[0]), int(window[1])
    if lo > hi:
        raise Skill4EconError("did_event_study window lower bound must be <= upper bound.")
    base = int(ctx.spec.get("base_period", -1))
    event_terms: list[str] = []
    for k in range(lo, hi + 1):
        if k == base:
            continue
        name = f"event_{k}".replace("-", "m")
        work[name] = ((work["_event_time"] == k) & treated_mask).astype(float)
        event_terms.append(name)
    keep_terms = [*event_terms, *x]
    design, rank_for_correction, fe_meta = _absorbed_fe_ols_frame(work, y, keep_terms, [id_col, time_col])
    design[cluster] = work[cluster].to_numpy()
    rows, meta = _ols_numpy(design, y, keep_terms, cluster=cluster, rank_for_correction=rank_for_correction)
    meta.update(fe_meta)
    rows = [row for row in rows if row["term"] in set(event_terms + x)]
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["Event-study TWFE completed."], estimator="numpy event-study TWFE", window=[lo, hi], base_period=base, **meta)
    return write_manifest(ctx, "ok", estimator="numpy event-study TWFE", window=[lo, hi], base_period=base, **meta)


def spatial_did_reduced_form(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        [
            "Requires panel data plus edge-list weights with source, target, weight.",
            "Estimates reduced-form y ~ D + W*D + FE, not a SAR/SDM model.",
        ],
    )
    if planned:
        return planned
    import numpy as np
    import pandas as pd

    df, _ = read_table(ctx.spec)
    weights_path = _path_from_spec_value(
        ctx.spec.get("weights") or ctx.spec.get("weight_matrix") or ctx.spec.get("w_path"),
        "weights/weight_matrix/w_path",
    )
    w = pd.read_csv(weights_path)
    source_col = str(ctx.spec.get("weight_source", "source"))
    target_col = str(ctx.spec.get("weight_target", "target"))
    weight_col = str(ctx.spec.get("weight", "weight"))
    require_columns(w, [source_col, target_col, weight_col], "spatial weights")
    y = str(ctx.spec.get("y"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    treat = str(ctx.spec.get("treat"))
    post = str(ctx.spec.get("post"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    require_columns(df, [y, id_col, time_col, treat, post, *x], "spatial DID")
    work = df[[y, id_col, time_col, treat, post, *x]].dropna().copy()
    work["_D"] = work[treat].astype(float) * work[post].astype(float)
    w = w[[source_col, target_col, weight_col]].dropna().copy()
    w[weight_col] = w[weight_col].astype(float)
    if bool(ctx.spec.get("row_standardize", True)):
        row_sums = w.groupby(source_col)[weight_col].transform("sum")
        if (row_sums == 0).any():
            raise Skill4EconError("Spatial weights contain a zero row sum before row standardization.")
        w[weight_col] = w[weight_col] / row_sums
    lag_vars = ["_D"]
    if bool(ctx.spec.get("include_wx", True)):
        lag_vars.extend(x)
    for var in lag_vars:
        lookup = work[[id_col, time_col, var]].rename(
            columns={id_col: source_col, var: f"__focal_{var}"}
        )
        neighbor = work[[id_col, time_col, var]].rename(
            columns={id_col: target_col, var: f"__neighbor_{var}"}
        )
        merged = lookup[[source_col, time_col]].drop_duplicates().merge(w, on=source_col, how="left")
        merged = merged.merge(neighbor, on=[target_col, time_col], how="left")
        merged[f"_W{var.removeprefix('_')}"] = merged[weight_col] * merged[f"__neighbor_{var}"]
        lagged = (
            merged.groupby([source_col, time_col], as_index=False)[f"_W{var.removeprefix('_')}"]
            .sum()
            .rename(columns={source_col: id_col})
        )
        work = work.merge(lagged, on=[id_col, time_col], how="left")
    work["_WD"] = work.pop("_WD")
    w_x = [f"_W{var}" for var in x if f"_W{var}" in work.columns]
    work[["_WD", *w_x]] = work[["_WD", *w_x]].fillna(0.0)

    cluster = str(ctx.spec.get("cluster", id_col))
    keep_terms = ["_D", "_WD", *x, *w_x]
    design, rank_for_correction, fe_meta = _absorbed_fe_ols_frame(work, y, keep_terms, [id_col, time_col])
    design[cluster] = work[cluster].to_numpy()
    rows, meta = _ols_numpy(design, y, keep_terms, cluster=cluster, rank_for_correction=rank_for_correction)
    meta.update(fe_meta)
    rows = [row for row in rows if row["term"] in set(keep_terms)]
    write_model_table(ctx, rows)
    lagged_path = ctx.artifact("spatial_lagged_panel.csv")
    work.to_csv(lagged_path, index=False, encoding="utf-8-sig")
    diagnostics = {
        "weights_path": str(weights_path),
        "weights_edges": int(len(w)),
        "row_standardized": bool(ctx.spec.get("row_standardize", True)),
        "include_wx": bool(ctx.spec.get("include_wx", True)),
        "estimand_warning": "Reduced-form neighbor exposure DID. This is not SAR/SDM MLE/GMM and does not solve spatial endogeneity.",
        "key_terms": ["_D", "_WD"],
    }
    warnings = [
        {
            "severity": "yellow",
            "code": "SPATIAL_SE_NOT_USED",
            "message": "Reduced-form spatial DID is estimated with ordinary clustered/HC covariance, not Conley or spatial HAC standard errors.",
            "action": "Report this limitation and run a spatial-SE adapter before using inference as spatially robust evidence.",
        },
        {
            "severity": "yellow",
            "code": "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION",
            "message": "The W*treatment coefficient is a reduced-form exposure coefficient, not an SDM/SAR indirect effect decomposition.",
            "action": "Do not call _WD a structural indirect effect unless an SDM/SAR adapter reports direct/indirect/total impacts.",
        },
    ]
    write_json(ctx.artifact("spatial_diagnostics.json"), diagnostics)
    write_audit(
        ctx,
        "ok",
        ["Reduced-form spatial spillover DID completed.", diagnostics["estimand_warning"]],
        estimator="numpy TWFE spatial exposure reduced-form",
        warnings=warnings,
        **meta,
        diagnostics=diagnostics,
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="numpy TWFE spatial exposure reduced-form",
        warnings=warnings,
        lagged_panel=str(lagged_path),
        **meta,
    )


def quantile_regression(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y and x. Optional quantile/tau."])
    if planned:
        return planned
    try:
        from statsmodels.regression.quantile_regression import QuantReg
    except Exception:
        return missing_dependency(ctx, "statsmodels", "quantile regression")

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    if not y or not x:
        raise Skill4EconError("quantile_regression requires y and at least one x/covar.")
    require_columns(df, [y, *x], "quantile regression")
    tau = float(ctx.spec.get("quantile", ctx.spec.get("tau", 0.5)))
    work = df[[y, *x]].dropna().copy()
    work["_const"] = 1.0
    terms = ["_const", *x]
    result = QuantReg(work[y], work[terms]).fit(
        q=tau,
        vcov=str(ctx.spec.get("vcov", "robust")),
        kernel=str(ctx.spec.get("kernel", "epa")),
        bandwidth=str(ctx.spec.get("bandwidth", "hsheather")),
        max_iter=int(ctx.spec.get("max_iter", 1000)),
    )
    ci = result.conf_int(alpha=0.05)
    rows = []
    for term in terms:
        rows.append(
            {
                "term": "_intercept" if term == "_const" else term,
                "coef": float(result.params[term]),
                "std_error": float(result.bse[term]),
                "p_value": float(result.pvalues[term]),
                "t_stat": float(result.tvalues[term]),
                "ci_low": float(ci.loc[term, 0]),
                "ci_high": float(ci.loc[term, 1]),
                "df_inference": int(result.df_resid),
            }
        )
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["Quantile regression completed."], estimator="statsmodels.QuantReg", quantile=tau)
    return write_manifest(ctx, "ok", estimator="statsmodels.QuantReg", quantile=tau, nobs=int(len(work)))


def threshold_panel_search(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Requires y, x, threshold, id, time. Searches candidate thresholds and fits two-regime slopes."],
    )
    if planned:
        return planned
    import numpy as np
    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    threshold = str(ctx.spec.get("threshold") or ctx.spec.get("q"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    if not y or not x or not threshold or not id_col or not time_col:
        raise Skill4EconError("threshold_panel requires y, at least one x/covar, threshold, id, and time.")
    require_columns(df, [y, threshold, id_col, time_col, *x], "threshold panel")
    trim = float(ctx.spec.get("trim", 0.15))
    grid_size = int(ctx.spec.get("grid_size", 20))
    work = df[[y, threshold, id_col, time_col, *x]].dropna().copy()
    values = np.sort(work[threshold].to_numpy(dtype=float))
    lo = np.quantile(values, trim)
    hi = np.quantile(values, 1 - trim)
    candidates = np.unique(np.linspace(lo, hi, grid_size))
    scan_rows = []
    best = None
    for cand in candidates:
        low = (work[threshold] <= cand).astype(float)
        high = 1.0 - low
        candidate_terms = []
        for var in x:
            low_name = f"{var}_low"
            high_name = f"{var}_high"
            work[low_name] = work[var].astype(float) * low
            work[high_name] = work[var].astype(float) * high
            candidate_terms.extend([low_name, high_name])
        design, rank_for_correction, _ = _absorbed_fe_ols_frame(work, y, candidate_terms, [id_col, time_col])
        rows, _ = _ols_numpy(design, y, candidate_terms, rank_for_correction=rank_for_correction)
        beta = np.array([row["coef"] for row in rows], dtype=float)
        resid = design[y].to_numpy(dtype=float) - design[candidate_terms].to_numpy(dtype=float) @ beta
        ssr = float(np.sum(resid**2))
        scan_rows.append({"threshold": float(cand), "ssr": ssr})
        if best is None or ssr < best["ssr"]:
            best = {"threshold": float(cand), "ssr": ssr, "rows": rows}
    if best is None:
        raise Skill4EconError("No threshold candidates were generated.")
    write_model_table(ctx, [row for row in best["rows"] if row["term"].endswith("_low") or row["term"].endswith("_high")])
    write_json(ctx.artifact("threshold_scan.json"), {"candidates": scan_rows, "best_threshold": best["threshold"]})
    write_audit(ctx, "ok", ["Threshold panel grid search completed."], estimator="numpy threshold FE grid", best_threshold=best["threshold"])
    return write_manifest(ctx, "ok", estimator="numpy threshold FE grid", best_threshold=best["threshold"], grid_size=int(len(candidates)))


def mediation_baron_kenny(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, treat, mediator, and optional x controls."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    treat = str(ctx.spec.get("treat") or ctx.spec.get("treatment"))
    mediator = str(ctx.spec.get("mediator"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    require_columns(df, [y, treat, mediator, *x], "mediation")
    work = df[[y, treat, mediator, *x]].dropna().copy()
    m_df, m_terms = _with_constant(work, [treat, *x])
    m_rows, _ = _ols_numpy(m_df, mediator, m_terms)
    y_total_df, y_total_terms = _with_constant(work, [treat, *x])
    total_rows, _ = _ols_numpy(y_total_df, y, y_total_terms)
    y_direct_df, y_direct_terms = _with_constant(work, [treat, mediator, *x])
    direct_rows, _ = _ols_numpy(y_direct_df, y, y_direct_terms)
    a = _term_coef(m_rows, treat)
    b = _term_coef(direct_rows, mediator)
    total = _term_coef(total_rows, treat)
    direct = _term_coef(direct_rows, treat)
    bootstrap_reps = int(ctx.spec.get("bootstrap_reps", ctx.spec.get("mediation_bootstrap_reps", 999)))
    bootstrap_seed = int(ctx.spec.get("bootstrap_seed", ctx.spec.get("random_seed", 20260601)))
    bootstrap = _bootstrap_mediation_indirect(
        work,
        y=y,
        treat=treat,
        mediator=mediator,
        x=x,
        reps=bootstrap_reps,
        seed=bootstrap_seed,
    )

    def _renamed_row(source_rows: list[dict[str, Any]], source_term: str, target_term: str, coef_value: float) -> dict[str, Any]:
        source = next(row for row in source_rows if row["term"] == source_term)
        return {**source, "term": target_term, "coef": float(coef_value)}

    rows = [
        _renamed_row(m_rows, treat, "a_treat_to_mediator", a),
        _renamed_row(direct_rows, mediator, "b_mediator_to_y", b),
        _renamed_row(total_rows, treat, "total_effect", total),
        _renamed_row(direct_rows, treat, "direct_effect", direct),
        _inference_row(
            "indirect_effect_ab",
            float(a * b),
            bootstrap["std_error"],
            max(bootstrap["successful_reps"] - 1, 1),
            extra={
                "ci_low": bootstrap["ci_low"],
                "ci_high": bootstrap["ci_high"],
                "se_method": bootstrap["se_method"],
                "bootstrap_reps": bootstrap["successful_reps"],
            },
        ),
    ]
    write_model_table(ctx, rows)
    write_json(ctx.artifact("mediation_bootstrap.json"), bootstrap)
    not_valid_for = ["causal mediation under sequential ignorability"]
    write_audit(
        ctx,
        "ok",
        [
            "Baron-Kenny, not causal mediation (Imai et al.); indirect-effect inference uses a seeded percentile bootstrap.",
        ],
        estimator="numpy OLS mediation",
        bootstrap_reps=bootstrap["successful_reps"],
        not_valid_for=not_valid_for,
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="numpy OLS mediation",
        nobs=int(len(work)),
        not_valid_for=not_valid_for,
        bootstrap_reps=bootstrap["successful_reps"],
    )


def synthetic_control_basic(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Requires y, id, time, treated_unit, treatment_time. Uses pre-treatment outcome path as predictors."],
    )
    if planned:
        return planned
    import pandas as pd

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    treated_unit = ctx.spec.get("treated_unit")
    treatment_time = ctx.spec.get("treatment_time")
    if treated_unit is None or treatment_time is None:
        raise Skill4EconError("synthetic_control_basic requires treated_unit and treatment_time.")
    require_columns(df, [y, id_col, time_col], "synthetic control")
    work = df[[y, id_col, time_col]].dropna().copy()
    pivot = work.pivot_table(index=time_col, columns=id_col, values=y, aggfunc="mean").sort_index()
    if treated_unit not in pivot.columns:
        try:
            treated_unit = type(pivot.columns[0])(treated_unit)
        except Exception:
            pass
    if treated_unit not in pivot.columns:
        raise Skill4EconError(f"treated_unit not found in id column: {treated_unit}")
    pre = pivot.index < treatment_time
    post = pivot.index >= treatment_time
    if int(pre.sum()) < 2:
        raise Skill4EconError("Synthetic control requires at least two pre-treatment periods.")
    if int(post.sum()) < 1:
        raise Skill4EconError("Synthetic control requires at least one post-treatment period.")
    donors = [col for col in pivot.columns if col != treated_unit]
    fit_result = _synthetic_control_fit(
        pivot,
        target_unit=treated_unit,
        donor_units=donors,
        pre_mask=pre,
        post_mask=post,
    )
    donors = list(fit_result["donors"])
    weights = fit_result["weights"]
    fit = pd.DataFrame({"time": list(pivot.index), "treated": fit_result["treated"], "synthetic": fit_result["synthetic"]})
    fit["gap"] = fit["treated"] - fit["synthetic"]
    fit.to_csv(ctx.artifact("synthetic_fit.csv"), index=False, encoding="utf-8-sig")
    weight_rows = [
        {
            "term": str(donor),
            "coef": float(weight),
            "std_error": math.nan,
            "p_value": math.nan,
            "ci_low": math.nan,
            "ci_high": math.nan,
            "df_inference": math.nan,
        }
        for donor, weight in zip(donors, weights)
    ]
    warnings: list[dict[str, Any]] = []
    placebo_p = math.nan
    if len(donors) < 10:
        warnings.append(_synthetic_placebo_too_few_donors_risk(len(donors)))
    else:
        placebo_rows = [
            {
                "unit": str(treated_unit),
                "is_treated_unit": True,
                "pre_rmspe": fit_result["pre_rmspe"],
                "post_rmspe": fit_result["post_rmspe"],
                "post_pre_rmspe_ratio": fit_result["post_pre_rmspe_ratio"],
                "post_att": fit_result["post_att"],
            }
        ]
        for placebo_unit in donors:
            placebo_donors = [donor for donor in donors if donor != placebo_unit]
            try:
                placebo_fit = _synthetic_control_fit(
                    pivot,
                    target_unit=placebo_unit,
                    donor_units=placebo_donors,
                    pre_mask=pre,
                    post_mask=post,
                )
            except Skill4EconError:
                continue
            placebo_rows.append(
                {
                    "unit": str(placebo_unit),
                    "is_treated_unit": False,
                    "pre_rmspe": placebo_fit["pre_rmspe"],
                    "post_rmspe": placebo_fit["post_rmspe"],
                    "post_pre_rmspe_ratio": placebo_fit["post_pre_rmspe_ratio"],
                    "post_att": placebo_fit["post_att"],
                }
            )
        placebo_count = len(placebo_rows) - 1
        if placebo_count < 10:
            warnings.append(_synthetic_placebo_too_few_donors_risk(placebo_count))
        else:
            treated_ratio = float(fit_result["post_pre_rmspe_ratio"])
            placebo_ratios = [float(row["post_pre_rmspe_ratio"]) for row in placebo_rows[1:]]
            placebo_p = float((1 + sum(ratio >= treated_ratio for ratio in placebo_ratios)) / (1 + len(placebo_ratios)))
        pd.DataFrame(placebo_rows).to_csv(ctx.artifact("synthetic_placebo.csv"), index=False, encoding="utf-8-sig")
    model_rows = list(weight_rows)
    if math.isfinite(placebo_p):
        model_rows.append(
            {
                "term": "placebo_permutation_p",
                "coef": placebo_p,
                "std_error": math.nan,
                "p_value": placebo_p,
                "ci_low": math.nan,
                "ci_high": math.nan,
                "df_inference": math.nan,
                "se_method": "in_space_placebo_post_pre_rmspe_ratio",
            }
        )
    write_model_table(ctx, model_rows)
    pre_rmse = float(fit_result["pre_rmspe"])
    post_att = float(fit_result["post_att"])
    write_audit(
        ctx,
        "ok",
        ["Basic synthetic control completed with in-space placebo inference."],
        estimator="scipy constrained least squares",
        pre_rmse=pre_rmse,
        post_att=post_att,
        placebo_permutation_p=placebo_p,
        warnings=warnings,
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="scipy constrained least squares",
        pre_rmse=pre_rmse,
        post_att=post_att,
        placebo_permutation_p=placebo_p,
        donors=len(donors),
        warnings=warnings,
    )


def dml_plr_crossfit(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, treatment, and x/features. sklearn cross-fitting fallback."])
    if planned:
        return planned
    import numpy as np
    from sklearn.base import clone
    from sklearn.metrics import mean_squared_error
    from sklearn.model_selection import KFold

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    treatment = str(ctx.spec.get("treatment") or ctx.spec.get("d") or ctx.spec.get("treat"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("features") or ctx.spec.get("covars"))
    cluster = str(ctx.spec.get("cluster")) if ctx.spec.get("cluster") else None
    if not y or not treatment or not x:
        raise Skill4EconError("dml_plr_crossfit requires y, treatment/d/treat, and at least one x/feature.")
    needed = [y, treatment, *x]
    if cluster and cluster not in needed:
        needed.append(cluster)
    require_columns(df, needed, "DML PLR")
    work = df[needed].dropna().copy()
    folds = int(ctx.spec.get("folds", 3))
    seed = int(ctx.spec.get("random_seed", 20260601))
    learner_kind = str(ctx.spec.get("learner", "random_forest"))
    reg_learner, _ = _learner_pair(learner_kind, seed)
    y_arr = work[y].to_numpy(dtype=float)
    d_arr = work[treatment].to_numpy(dtype=float)
    X = work[x].to_numpy(dtype=float)
    y_hat = np.zeros(len(work))
    d_hat = np.zeros(len(work))
    fold_sizes = []
    for train_idx, test_idx in KFold(n_splits=folds, shuffle=True, random_state=seed).split(X):
        fold_sizes.append(int(len(test_idx)))
        ml_y = clone(reg_learner)
        ml_d = clone(reg_learner)
        ml_y.fit(X[train_idx], y_arr[train_idx])
        ml_d.fit(X[train_idx], d_arr[train_idx])
        y_hat[test_idx] = ml_y.predict(X[test_idx])
        d_hat[test_idx] = ml_d.predict(X[test_idx])
    y_res = y_arr - y_hat
    d_res = d_arr - d_hat
    denom = float(np.mean(d_res**2))
    if denom <= 1e-12:
        raise Skill4EconError("DML PLR residualized treatment has near-zero variance.")
    theta = float(np.mean(d_res * y_res) / denom)
    score = d_res * (y_res - theta * d_res)
    inference_risks: list[dict[str, Any]] = []
    if cluster:
        cluster_values = work[cluster].astype(str).to_numpy()
        se, n_clusters = _clustered_mean_se(score / denom, cluster_values)
        df_inference = max(n_clusters - 1, 1)
        cluster_se: str | dict[str, Any] = {
            "mode": "cluster_summed_orthogonal_score",
            "cluster": cluster,
            "n_clusters": n_clusters,
            "formula": "sqrt(G/(G-1) * sum_g(sum_i psi_i)^2 / n^2)",
        }
        if n_clusters < 30:
            inference_risks.append(_few_cluster_inference_risk(cluster, n_clusters))
    else:
        se = float(np.sqrt(np.mean(score**2) / (denom**2 * len(work))))
        df_inference = len(work) - 1
        cluster_se = "iid_orthogonal_score"
    rows = [
        _inference_row(
            "theta_plr",
            theta,
            se,
            df_inference,
            extra={
                "nobs": int(len(work)),
                "se_method": cluster_se["mode"] if isinstance(cluster_se, dict) else cluster_se,
                "cluster": cluster or "",
                "n_clusters": n_clusters if cluster else math.nan,
            },
        )
    ]
    write_model_table(ctx, rows)
    diagnostics = {
        "estimator": "sklearn cross-fitting PLR fallback, not DoubleML package",
        "folds": folds,
        "fold_sizes": fold_sizes,
        "random_seed": seed,
        "learner": learner_kind,
        "treatment": treatment,
        "nuisance_rmse_y": float(np.sqrt(mean_squared_error(y_arr, y_hat))),
        "nuisance_rmse_d": float(np.sqrt(mean_squared_error(d_arr, d_hat))),
        "cluster_se": cluster_se,
        "identification": ["partial linear model", "orthogonality", "unconfoundedness conditional on X"],
    }
    write_json(ctx.artifact("dml_diagnostics.json"), diagnostics)
    write_audit(ctx, "ok", ["DML PLR sklearn cross-fitting fallback completed.", diagnostics["estimator"]], **diagnostics)
    return write_manifest(
        ctx,
        "ok",
        estimator=diagnostics["estimator"],
        nobs=int(len(work)),
        folds=folds,
        inference_risks=inference_risks,
    )


def dml_irm_crossfit(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, binary treatment, and x/features. sklearn AIPW/IRM fallback."])
    if planned:
        return planned
    import numpy as np
    from sklearn.base import clone
    from sklearn.metrics import log_loss, mean_squared_error, roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    treatment = str(ctx.spec.get("treatment") or ctx.spec.get("d") or ctx.spec.get("treat"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("features") or ctx.spec.get("covars"))
    cluster = str(ctx.spec.get("cluster")) if ctx.spec.get("cluster") else None
    if not y or not treatment or not x:
        raise Skill4EconError("dml_irm_crossfit requires y, binary treatment/d/treat, and at least one x/feature.")
    needed = [y, treatment, *x]
    if cluster and cluster not in needed:
        needed.append(cluster)
    require_columns(df, needed, "DML IRM")
    work = df[needed].dropna().copy()
    y_arr = work[y].to_numpy(dtype=float)
    d_arr = work[treatment].to_numpy(dtype=int)
    if set(np.unique(d_arr)) - {0, 1}:
        raise Skill4EconError("DML IRM requires a binary treatment coded 0/1.")
    folds = int(ctx.spec.get("folds", 3))
    seed = int(ctx.spec.get("random_seed", 20260601))
    trim = float(ctx.spec.get("trim", 0.01))
    learner_kind = str(ctx.spec.get("learner", "random_forest"))
    reg_learner, clf_learner = _learner_pair(learner_kind, seed)
    X = work[x].to_numpy(dtype=float)
    mu0 = np.zeros(len(work))
    mu1 = np.zeros(len(work))
    p_hat = np.zeros(len(work))
    fold_sizes = []
    for train_idx, test_idx in StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed).split(X, d_arr):
        fold_sizes.append(int(len(test_idx)))
        ml_m0 = clone(reg_learner)
        ml_m1 = clone(reg_learner)
        ml_g = clone(clf_learner)
        train0 = train_idx[d_arr[train_idx] == 0]
        train1 = train_idx[d_arr[train_idx] == 1]
        if len(train0) == 0 or len(train1) == 0:
            raise Skill4EconError("Each DML IRM fold needs treated and control observations in training.")
        ml_m0.fit(X[train0], y_arr[train0])
        ml_m1.fit(X[train1], y_arr[train1])
        ml_g.fit(X[train_idx], d_arr[train_idx])
        mu0[test_idx] = ml_m0.predict(X[test_idx])
        mu1[test_idx] = ml_m1.predict(X[test_idx])
        p_hat[test_idx] = ml_g.predict_proba(X[test_idx])[:, 1]
    p_raw = p_hat.copy()
    keep = (p_raw >= trim) & (p_raw <= 1 - trim)
    trimmed = int((~keep).sum())
    if keep.sum() < max(8, folds * 2):
        raise Skill4EconError("DML IRM overlap trimming removed too many observations.")
    p = np.clip(p_raw[keep], trim, 1 - trim)
    yk = y_arr[keep]
    dk = d_arr[keep]
    mu0k = mu0[keep]
    mu1k = mu1[keep]
    psi1 = mu1k + dk * (yk - mu1k) / p
    psi0 = mu0k + (1 - dk) * (yk - mu0k) / (1 - p)
    score_ate = psi1 - psi0
    ate = float(np.mean(score_ate))
    treated_share = float(dk.mean())
    att_score = (dk * (yk - mu0k) - (1 - dk) * p / (1 - p) * (yk - mu0k)) / treated_share
    att = float(np.mean(att_score))
    inference_risks: list[dict[str, Any]] = []
    if cluster:
        cluster_values = work[cluster].astype(str).to_numpy()[keep]
        se_ate, n_clusters = _clustered_mean_se(score_ate, cluster_values)
        se_att, _ = _clustered_mean_se(att_score, cluster_values)
        df_inference = max(n_clusters - 1, 1)
        cluster_se: str | dict[str, Any] = {
            "mode": "cluster_summed_aipw_score",
            "cluster": cluster,
            "n_clusters": n_clusters,
            "formula": "sqrt(G/(G-1) * sum_g(sum_i centered_score_i)^2 / n^2)",
        }
        if n_clusters < 30:
            inference_risks.append(_few_cluster_inference_risk(cluster, n_clusters))
    else:
        se_ate = float(np.std(score_ate, ddof=1) / np.sqrt(len(score_ate)))
        se_att = float(np.std(att_score, ddof=1) / np.sqrt(len(att_score)))
        df_inference = int(keep.sum()) - 1
        cluster_se = "iid_aipw_score"
    rows = [
        _inference_row(
            "ATE_aipw",
            ate,
            se_ate,
            df_inference,
            extra={
                "nobs": int(keep.sum()),
                "se_method": cluster_se["mode"] if isinstance(cluster_se, dict) else cluster_se,
                "cluster": cluster or "",
                "n_clusters": n_clusters if cluster else math.nan,
            },
        ),
        _inference_row(
            "ATT_aipw",
            att,
            se_att,
            df_inference,
            extra={
                "nobs": int(keep.sum()),
                "se_method": cluster_se["mode"] if isinstance(cluster_se, dict) else cluster_se,
                "cluster": cluster or "",
                "n_clusters": n_clusters if cluster else math.nan,
            },
        ),
    ]
    write_model_table(ctx, rows)
    try:
        auc = float(roc_auc_score(d_arr, p_raw))
    except Exception:
        auc = math.nan
    diagnostics = {
        "estimator": "sklearn cross-fitting IRM/AIPW fallback, not DoubleML/EconML package",
        "folds": folds,
        "fold_sizes": fold_sizes,
        "random_seed": seed,
        "learner": learner_kind,
        "treatment": treatment,
        "trim": trim,
        "trimmed_observations": trimmed,
        "propensity_min": float(np.min(p_raw)),
        "propensity_max": float(np.max(p_raw)),
        "propensity_quantiles": [float(v) for v in np.quantile(p_raw, [0.01, 0.05, 0.5, 0.95, 0.99])],
        "propensity_auc": auc,
        "propensity_log_loss": float(log_loss(d_arr, np.clip(p_raw, 1e-6, 1 - 1e-6))),
        "outcome_rmse_mu0_controls": float(np.sqrt(mean_squared_error(y_arr[d_arr == 0], mu0[d_arr == 0]))),
        "outcome_rmse_mu1_treated": float(np.sqrt(mean_squared_error(y_arr[d_arr == 1], mu1[d_arr == 1]))),
        "cluster_se": cluster_se,
        "identification": ["unconfoundedness conditional on X", "overlap", "orthogonal AIPW score"],
    }
    write_json(ctx.artifact("dml_diagnostics.json"), diagnostics)
    write_audit(ctx, "ok", ["DML IRM sklearn cross-fitting fallback completed.", diagnostics["estimator"]], **diagnostics)
    return write_manifest(
        ctx,
        "ok",
        estimator=diagnostics["estimator"],
        nobs=int(keep.sum()),
        folds=folds,
        inference_risks=inference_risks,
    )


def doubleml_adapter(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Dependency-gated adapter. Use dml_plr_crossfit when DoubleML is unavailable."])
    if planned:
        return planned
    try:
        import doubleml  # noqa: F401
    except Exception:
        return missing_dependency(ctx, "doubleml", "real DoubleML adapter")
    write_audit(ctx, "interface_only", ["DoubleML is importable, but real package adapter is not wired yet. Use dml_plr_crossfit/dml_irm_crossfit tonight."])
    return write_manifest(ctx, "interface_only", package="doubleml")


def cs_did_attgt_py(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Dependency-gated Python Callaway-Sant'Anna ATT(g,t) adapter."])
    if planned:
        return planned
    from .adapters.python.cs_did import run_cs_did_attgt

    return run_cs_did_attgt(ctx)


def econml_adapter(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Dependency-gated adapter. Use dml_irm_crossfit/PLR fallback when EconML is unavailable."])
    if planned:
        return planned
    try:
        import econml  # noqa: F401
    except Exception:
        return missing_dependency(ctx, "econml", "real EconML adapter")
    write_audit(ctx, "interface_only", ["EconML is importable, but real package adapter is not wired yet. Do not claim CausalForestDML tonight."])
    return write_manifest(ctx, "interface_only", package="econml")


def psm_overlap_balance(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, treat, and x columns."])
    if planned:
        return planned

    df, _ = read_table(ctx.spec)
    from .diagnostics.overlap_balance import run_overlap_balance_diagnostics

    diag = run_overlap_balance_diagnostics(df, ctx.spec, ctx.run_dir)
    diagnostics = diag["diagnostics"]
    write_audit(
        ctx,
        "ok",
        ["PSM/IPW overlap, balance, and weight diagnostics completed."],
        warnings=diag["warnings"],
        diagnostics=diagnostics,
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="sklearn/logit propensity diagnostics",
        warnings=diag["warnings"],
        nobs=diagnostics.get("n_obs"),
    )


def psm_ipw_match(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires y, treat, and x columns."])
    if planned:
        return planned
    import numpy as np

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    treat = str(ctx.spec.get("treat") or ctx.spec.get("treatment"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars") or ctx.spec.get("controls"))
    if not y or not treat or not x:
        raise Skill4EconError("psm_ipw_match requires y, treat, and at least one x/covar.")
    require_columns(df, [y, treat, *x], "PSM")
    from .diagnostics.overlap_balance import run_overlap_balance_diagnostics

    diag = run_overlap_balance_diagnostics(df, ctx.spec, ctx.run_dir)
    work = diag["analysis_frame"].dropna(subset=[y]).copy()
    treated = work[work[treat] == 1]
    control = work[work[treat] == 0]
    if treated.empty or control.empty:
        raise Skill4EconError("PSM requires both treated and control observations.")
    pscore = np.clip(work["_pscore"].to_numpy(dtype=float), 1e-6, 1 - 1e-6)
    treat_arr = work[treat].to_numpy(dtype=float)
    y_arr = work[y].to_numpy(dtype=float)

    logit_pscore = _logit_pscore(pscore)
    default_caliper = float(0.2 * np.std(logit_pscore, ddof=1)) if len(logit_pscore) > 1 else math.nan
    caliper = ctx.spec.get("caliper")
    caliper_value = float(caliper) if caliper is not None else default_caliper
    with_replacement = bool(ctx.spec.get("with_replacement", ctx.spec.get("replacement", True)))
    match_caliper: float | None = caliper_value
    match_warnings: list[dict[str, Any]] = []
    try:
        match = _matching_att_with_ai_se(
            work,
            y,
            treat,
            caliper=match_caliper,
            with_replacement=with_replacement,
        )
        caliper_relaxed = False
    except Skill4EconError:
        if caliper is not None:
            raise
        match_caliper = None
        caliper_relaxed = True
        match = _matching_att_with_ai_se(
            work,
            y,
            treat,
            caliper=match_caliper,
            with_replacement=with_replacement,
        )
        match_warnings.append(
            {
                "severity": "red",
                "code": "PSM_OVERLAP_WEAK",
                "message": (
                    "The default Austin caliper produced no nearest-neighbor matches; "
                    "a no-caliper nearest-neighbor result was reported only as a diagnostic."
                ),
                "action": "Do not use this matching estimate for claims; redesign support or provide a justified caliper.",
                "claim_degradation": "not_for_claim",
                "affected_artifacts": ["model_table.csv", "psm_diagnostics.json"],
            }
        )
    ate_ipw, att_ipw = _ipw_point_estimates(y_arr, treat_arr, pscore)
    bootstrap_reps = max(99, int(ctx.spec.get("bootstrap_reps", ctx.spec.get("ipw_bootstrap_reps", 199))))
    bootstrap_seed = int(ctx.spec.get("bootstrap_seed", ctx.spec.get("random_seed", 20260601)))
    ipw_bootstrap = _bootstrap_ipw(
        y_arr,
        treat_arr,
        pscore,
        reps=bootstrap_reps,
        seed=bootstrap_seed,
    )
    rows = [
        _inference_row(
            "ATT_nearest_neighbor",
            match["att"],
            match["std_error"],
            max(match["n_matched"] - 1, 1),
            extra={
                "nobs": match["n_matched"],
                "se_method": match["se_method"],
                "caliper": match_caliper,
                "with_replacement": with_replacement,
            },
        ),
        _inference_row(
            "ATE_ipw",
            ate_ipw,
            ipw_bootstrap["ate"]["std_error"],
            max(ipw_bootstrap["successful_reps"] - 1, 1),
            extra={
                "nobs": int(len(work)),
                "se_method": ipw_bootstrap["se_method"],
                "bootstrap_reps": ipw_bootstrap["successful_reps"],
                "ci_low": ipw_bootstrap["ate"]["ci_low"],
                "ci_high": ipw_bootstrap["ate"]["ci_high"],
            },
        ),
        _inference_row(
            "ATT_ipw",
            att_ipw,
            ipw_bootstrap["att"]["std_error"],
            max(ipw_bootstrap["successful_reps"] - 1, 1),
            extra={
                "nobs": int(len(work)),
                "se_method": ipw_bootstrap["se_method"],
                "bootstrap_reps": ipw_bootstrap["successful_reps"],
                "ci_low": ipw_bootstrap["att"]["ci_low"],
                "ci_high": ipw_bootstrap["att"]["ci_high"],
            },
        ),
    ]
    write_model_table(ctx, rows)
    warnings = [
        warning
        for warning in (diag["warnings"] or [])
        if warning.get("code") != "PSM_NAIVE_SE_NOT_ABADIE_IMBENS"
    ]
    warnings.extend(match_warnings)
    write_json(
        ctx.artifact("psm_diagnostics.json"),
        {
            "treated_n": int(len(treated)),
            "control_n": int(len(control)),
            "matched_treated_n": match["n_matched"],
            "dropped_treated": match["dropped_treated"],
            "mean_match_distance": match["mean_match_distance"],
            "max_match_distance": match["max_match_distance"],
            "match_distance_scale": "logit_pscore",
            "caliper": match_caliper,
            "requested_caliper": caliper_value,
            "caliper_relaxed_due_to_no_matches": caliper_relaxed,
            "caliper_default_rule": "0.2 * sd(logit propensity score)" if caliper is None else "user_supplied",
            "with_replacement": with_replacement,
            "matching_se_method": match["se_method"],
            "ipw_bootstrap": ipw_bootstrap,
            "pscore_min": float(pscore.min()),
            "pscore_max": float(pscore.max()),
            "overlap_balance": diag["diagnostics"],
        },
    )
    write_audit(
        ctx,
        "ok",
        ["PSM nearest-neighbor, IPW, and diagnostics completed with real inference."],
        estimator="sklearn",
        warnings=warnings,
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="sklearn PSM + numpy IPW",
        warnings=warnings,
        nobs=int(len(work)),
    )


def spatial_weights_factory(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires unit id plus lon/lat columns for distance-based W, or an edge list path."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    from .adapters.python.spatial_weights import build_spatial_weights

    result = build_spatial_weights(df, ctx.spec, ctx.run_dir)
    write_json(ctx.artifact("spatial_weights_factory.json"), result)
    write_audit(
        ctx,
        "ok",
        ["Spatial weights factory completed."],
        warnings=result["warnings"],
        metadata=result["metadata_payload"],
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="python spatial weights factory",
        warnings=result["warnings"],
        matrix_metadata=result["metadata_payload"],
    )


def spatial_w_audit(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires panel/unit data plus weights edge list path(s)."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    weights = ctx.spec.get("weights") or ctx.spec.get("weight_matrix") or ctx.spec.get("w_path")
    weight_paths = listify(ctx.spec.get("weight_paths"))
    if weights:
        weight_paths.insert(0, str(weights))
    if not weight_paths:
        raise Skill4EconError("spatial_w_audit requires weights/weight_matrix/w_path or weight_paths.")
    from .diagnostics.spatial_preflight import audit_spatial_weights, write_spatial_w_comparison

    results = []
    warnings: list[dict[str, Any]] = []
    if len(weight_paths) == 1:
        result = audit_spatial_weights(weight_paths[0], df, ctx.spec, ctx.run_dir)
        results.append(result)
        warnings.extend(result["warnings"])
    else:
        for idx, path in enumerate(weight_paths, 1):
            subdir = ctx.run_dir / f"w_{idx:02d}"
            result = audit_spatial_weights(path, df, ctx.spec, subdir)
            results.append(result)
            warnings.extend(result["warnings"])
        write_spatial_w_comparison(results, ctx.run_dir)
    write_json(ctx.artifact("spatial_w_audit_summary.json"), {"weights": results, "warnings": warnings})
    write_audit(ctx, "ok", ["Spatial W audit completed."], warnings=warnings)
    return write_manifest(ctx, "ok", estimator="python spatial W audit", warnings=warnings, n_weights=len(results))


def spatial_moran_preflight(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Requires panel data plus a spatial weights edge list."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    weights = ctx.spec.get("weights") or ctx.spec.get("weight_matrix") or ctx.spec.get("w_path")
    if not weights:
        raise Skill4EconError("spatial_moran_preflight requires weights/weight_matrix/w_path.")
    from .diagnostics.spatial_moran import run_moran_preflight

    result = run_moran_preflight(df, weights, ctx.spec, ctx.run_dir)
    write_json(ctx.artifact("spatial_moran_preflight.json"), result)
    write_audit(ctx, "ok", ["Spatial Moran preflight completed."], warnings=result["warnings"])
    return write_manifest(ctx, "ok", estimator="python Moran I + basic local Moran", warnings=result["warnings"])


def spatial_spdep_lisa(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Dependency-gated R spdep local Moran/LISA adapter."])
    if planned:
        return planned
    data_path = data_path_from_spec(ctx.spec)
    if data_path is None:
        raise Skill4EconError("spatial_spdep_lisa requires data/input/input_path.")
    weights = ctx.spec.get("weights") or ctx.spec.get("weight_matrix") or ctx.spec.get("w_path")
    if not weights:
        raise Skill4EconError("spatial_spdep_lisa requires weights/weight_matrix/w_path.")
    weights_path = _path_from_spec_value(weights, "weights/weight_matrix/w_path")
    from .diagnostics.spatial_moran import run_spdep_lisa_adapter

    result = run_spdep_lisa_adapter(data_path, weights_path, ctx.spec, ctx.run_dir)
    write_json(ctx.artifact("spatial_spdep_lisa.json"), result)
    if result.get("status") == "ok":
        write_audit(ctx, "ok", ["R spdep local Moran/LISA completed."], warnings=result.get("warnings") or [])
        return write_manifest(ctx, "ok", estimator="R spdep localmoran", warnings=result.get("warnings") or [])
    status = "missing_dependency" if result.get("status") == "skipped_backend_unavailable" else "failed"
    write_audit(ctx, status, ["R spdep local Moran/LISA was not run."], warnings=result.get("warnings") or [])
    return write_manifest(
        ctx,
        status,
        package="R spdep",
        purpose="R local Moran/LISA adapter",
        warnings=result.get("warnings") or [],
    )


def spatial_exposure_did(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        [
            "Requires panel data plus edge-list weights with source, target, weight, and optional distance_km.",
            "Constructs W*treatment exposure, near/far controls, buffer deletion, and reduced-form TWFE exposure DID.",
        ],
    )
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    weights = ctx.spec.get("weights") or ctx.spec.get("weight_matrix") or ctx.spec.get("w_path")
    if not weights:
        raise Skill4EconError("spatial_exposure_did requires weights/weight_matrix/w_path.")
    weights_path = _path_from_spec_value(weights, "weights/weight_matrix/w_path")
    from .diagnostics.spatial_exposure import run_spatial_exposure_did

    result = run_spatial_exposure_did(df, weights_path, ctx.spec, ctx.run_dir)
    warnings = list(result.get("warnings") or [])
    warnings.extend(
        [
            {
                "severity": "yellow",
                "code": "SPATIAL_SE_NOT_USED",
                "message": "Spatial exposure DID uses ordinary clustered/HC covariance; Conley or spatial HAC standard errors are not implemented in this adapter.",
                "action": "Run a spatial-SE comparison before presenting spatial inference as robust.",
            },
            {
                "severity": "yellow",
                "code": "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION",
                "message": "The W*treatment exposure coefficient is reduced-form and has no direct/indirect/total impact decomposition.",
                "action": "Use a SAR/SDM adapter with impact decomposition before claiming structural spillover effects.",
            },
        ]
    )
    write_json(ctx.artifact("spatial_exposure_did_summary.json"), result)
    write_model_table(ctx, result.get("rows") or [])
    write_audit(
        ctx,
        "ok",
        [
            "Spatial exposure DID completed.",
            "Estimator is reduced-form TWFE with local treatment and W*treatment exposure; it is not SAR/SDM impact decomposition.",
        ],
        warnings=warnings,
        safe_claims=result.get("safe_claims") or [],
        unsafe_claims=result.get("unsafe_claims") or [],
        artifacts=result.get("artifacts") or {},
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="numpy TWFE spatial exposure DID",
        claim_level="sensitivity_only",
        paper_readiness="supplementary_only",
        main_claim_available=False,
        estimand_scope="reduced_form_spatial_exposure",
        not_valid_for=[
            "structural indirect effect",
            "SAR/SEM/SDM impact decomposition",
            "policy spillover mechanism proven",
        ],
        warnings=warnings,
        safe_claims=result.get("safe_claims") or [],
        method_card={"claim_limits": result.get("unsafe_claims") or []},
        artifacts_detail=result.get("artifacts") or {},
        contaminated_control_share=result.get("contaminated_control_share"),
        event_study_status=result.get("event_study_status"),
    )


def spatial_panel_model_adapter(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Dependency-gated SAR/SEM/SDM adapter. Provide impact_decomposition to parse backend direct/indirect/total effects."],
    )
    if planned:
        return planned
    from .diagnostics.spatial_models import run_spatial_model_adapter

    result = run_spatial_model_adapter(ctx.spec, ctx.run_dir, repo_root=ctx.repo_root)
    write_json(ctx.artifact("spatial_panel_model_adapter_summary.json"), result)
    if result.get("rows"):
        write_model_table(
            ctx,
            [
                {
                    "term": f"{row.get('effect')}_{part}",
                    "coef": row.get(part),
                    "std_error": row.get("std_error"),
                    "p_value": row.get("p_value"),
                }
                for row in result.get("rows") or []
                for part in ["direct_effect", "indirect_effect", "total_effect"]
            ],
        )
    status = "ok" if result.get("status") == "ok" else "missing_dependency"
    write_audit(ctx, status, ["Spatial panel model adapter completed dependency gate."], warnings=result.get("warnings") or [])
    return write_manifest(
        ctx,
        status,
        estimator="spatial panel SAR/SEM/SDM adapter",
        claim_level="adapter_only",
        paper_readiness="not_available" if status != "ok" else "supplementary_only",
        main_claim_available=False,
        estimand_scope="spatial_structural_adapter_contract",
        not_valid_for=["paper-ready SAR/SEM/SDM claims without a real backend execution audit"],
        warnings=result.get("warnings") or [],
        backend_status=result.get("backend_status"),
    )


def spatial_se_comparison(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Compares clustered/HC SE with distance-cutoff spatial HAC SE when lon/lat exist."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    weights = ctx.spec.get("weights") or ctx.spec.get("weight_matrix") or ctx.spec.get("w_path")
    if not weights:
        raise Skill4EconError("spatial_se_comparison requires weights/weight_matrix/w_path.")
    weights_path = _path_from_spec_value(weights, "weights/weight_matrix/w_path")
    from .diagnostics.spatial_se import run_spatial_se_comparison

    result = run_spatial_se_comparison(df, weights_path, ctx.spec, ctx.run_dir)
    write_json(ctx.artifact("spatial_se_comparison_summary.json"), result)
    write_audit(ctx, "ok", ["Spatial SE comparison completed."], warnings=result.get("warnings") or [])
    return write_manifest(
        ctx,
        "ok",
        estimator="python distance-cutoff spatial HAC SE comparison",
        claim_level="sensitivity_only",
        paper_readiness="supplementary_only",
        main_claim_available=False,
        estimand_scope="spatial_se_sensitivity_only",
        not_valid_for=["full Conley inference", "full spatial panel inference"],
        warnings=result.get("warnings") or [],
        cutoffs_km=result.get("cutoffs_km"),
        se_status=result.get("status"),
    )


def spatial_w_sensitivity(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Runs the same spatial exposure DID across multiple W matrices and records sign/significance instability."])
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    from .diagnostics.w_sensitivity import run_w_sensitivity

    result = run_w_sensitivity(df, ctx.spec, ctx.run_dir)
    write_json(ctx.artifact("spatial_w_sensitivity_summary.json"), result)
    write_model_table(ctx, result.get("rows") or [])
    write_audit(ctx, "ok", ["Spatial W sensitivity completed."], warnings=result.get("warnings") or [])
    return write_manifest(
        ctx,
        "ok",
        estimator="python spatial exposure DID W sensitivity",
        claim_level="sensitivity_only",
        paper_readiness="supplementary_only",
        main_claim_available=False,
        estimand_scope="w_sensitivity_for_reduced_form_spatial_exposure",
        warnings=result.get("warnings") or [],
        n_weights=result.get("n_weights"),
    )


def live_backend_certification(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        [
            "Runs dependency-gated live certification for Stata/R spatial backends and ppmlhdfe.",
            "This is a slow diagnostic; it must not be treated as a paper estimate by itself.",
        ],
    )
    if planned:
        return planned
    from .diagnostics.live_backend_certification import run_live_backend_certification

    result = run_live_backend_certification(ctx.spec, ctx.run_dir, repo_root=ctx.repo_root)
    write_json(ctx.artifact("live_backend_certification_summary.json"), result)
    status = "ok" if result.get("status") == "ok" else "missing_dependency"
    write_audit(
        ctx,
        status,
        ["Live backend certification completed with dependency-gated external calls."],
        warnings=result.get("warnings") or [],
        certification_artifacts=result.get("artifacts") or {},
    )
    return write_manifest(
        ctx,
        status,
        estimator="live backend certification harness",
        claim_level="diagnostic",
        paper_readiness="supplementary_only" if status == "ok" else "not_available",
        main_claim_available=False,
        estimand_scope="backend_live_certification_not_paper_estimate",
        not_valid_for=["paper-ready causal claims", "structural spatial claims without inspecting live impact artifacts"],
        warnings=result.get("warnings") or [],
        certification=result,
    )


def flagship_slow_matrix(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        [
            "Runs an opt-in slow matrix across flagship workflow cases and Stata/R backend profiles.",
            "This is a certification/audit harness; individual child run_dirs must be inspected before paper claims.",
        ],
    )
    if planned:
        return planned
    from .diagnostics.flagship_slow_matrix import run_flagship_slow_matrix

    result = run_flagship_slow_matrix(ctx.spec, ctx.run_dir, repo_root=ctx.repo_root)
    write_json(ctx.artifact("flagship_slow_matrix_summary.json"), result)
    status = "ok" if result.get("status") == "ok" else "partial_success"
    write_audit(
        ctx,
        status,
        ["Flagship slow matrix completed with child run directories and backend-profile rows."],
        warnings=result.get("warnings") or [],
        matrix_artifacts=result.get("artifacts") or {},
    )
    return write_manifest(
        ctx,
        status,
        estimator="flagship workflow slow matrix",
        claim_level="diagnostic",
        paper_readiness="supplementary_only",
        main_claim_available=False,
        estimand_scope="workflow_backend_certification_matrix",
        not_valid_for=["paper-ready claims without inspecting each child run_dir", "R backend claims when R rows are backend_unavailable"],
        warnings=result.get("warnings") or [],
        matrix=result,
    )


def ml_prediction_audit(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Checks chronological split and feature/label timing. Optional run fits simple baselines."],
    )
    if planned:
        return planned
    df, _ = read_table(ctx.spec)
    time_col = str(ctx.spec.get("time"))
    y = str(ctx.spec.get("y") or ctx.spec.get("label"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("features"))
    require_columns(df, [time_col, y, *x], "ML prediction")
    split = ctx.spec.get("split", {})
    messages = []
    status = "ok"
    if split.get("type") != "chronological":
        status = "fatal"
        messages.append("Finance ML split must be chronological.")
    else:
        messages.append("Chronological split declared.")
    if ctx.spec.get("uses_random_split"):
        status = "fatal"
        messages.append("Random split is prohibited for default finance time-series tasks.")
    train_end = split.get("train_end")
    test_start = split.get("test_start")
    if train_end is not None and test_start is not None and train_end >= test_start:
        status = "fatal"
        messages.append("train_end must be earlier than test_start.")
    write_audit(ctx, status, messages, split=split)
    return write_manifest(ctx, status, split=split)


def plot_diagnostics(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(ctx, ["Creates simple diagnostic plots from a CSV/XLSX input."])
    if planned:
        return planned
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return missing_dependency(ctx, "matplotlib", "diagnostic plotting")
    df, _ = read_table(ctx.spec)
    y = ctx.spec.get("y")
    if not y:
        raise Skill4EconError("plot_diagnostics requires y.")
    require_columns(df, [str(y)], "plot")
    fig_dir = ctx.run_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    ax = df[str(y)].hist()
    ax.set_title(str(y))
    fig = ax.get_figure()
    path = fig_dir / f"{y}_hist.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    write_audit(ctx, "ok", ["Diagnostic plot written."], figure=str(path))
    return write_manifest(ctx, "ok", figures=[str(path)])


def dea_sbm_malmquist_adapter(ctx: RunContext) -> dict[str, Any]:
    requirements = [
        "Vendored backend: skill4econ.backends.dea (self-contained, in-process).",
        "Spec requires data XLSX plus dea: {dmus, periods, nx, ny, nb, undesirable, sup}.",
        "Optional override via spec.dea.backend_path or SKILL4ECON_DEA_BACKEND.",
    ]
    planned = _plan_or_dry(ctx, requirements)
    if planned:
        return planned
    params = ctx.spec.get("dea") or {}
    if ctx.spec.get("second_stage") or params.get("second_stage"):
        warning = {
            "severity": "red",
            "code": "DEA_SECOND_STAGE_NAIVE_TOBIT",
            "message": "DEA second-stage/determinants analysis was requested, but this adapter only certifies SBM and Malmquist index construction.",
            "action": "Run an explicitly specified second-stage design with bootstrap or defensible limited-dependent-variable assumptions; do not treat naive Tobit as automatic publication evidence.",
        }
        write_audit(
            ctx,
            "failed",
            ["DEA second-stage requests are intentionally blocked in dea_sbm_malmquist_adapter."],
            warnings=[warning],
            second_stage_available=False,
        )
        return write_manifest(
            ctx,
            "failed",
            warnings=[warning],
            second_stage_available=False,
            environmental_determinants_claim=False,
        )
    required = ["dmus", "periods", "nx", "ny", "nb", "undesirable", "sup"]
    missing = [key for key in required if key not in params]
    if missing:
        raise Skill4EconError(f"DEA adapter missing dea params: {missing}")
    source_data = data_path_from_spec(ctx.spec)
    if source_data is None or source_data.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise Skill4EconError("DEA adapter requires an XLSX input file.")

    override_path, source = resolve_dea_backend(ctx.spec)
    if override_path is not None:
        return _run_external_dea_backend(ctx, override_path, source_data, params, source)
    return _run_vendored_dea_backend(ctx, source_data, params)


def _run_vendored_dea_backend(
    ctx: RunContext,
    source_data: Path,
    params: dict[str, Any],
) -> dict[str, Any]:
    try:
        import pandas as pd
    except Exception:
        return missing_dependency(ctx, "pandas", "DEA adapter requires pandas")
    try:
        from .backends.dea import compute_indices, write_excel
    except Exception as exc:
        write_audit(ctx, "failed", [f"Vendored DEA backend import failed: {exc}"])
        return write_manifest(ctx, "failed", error=str(exc))

    df = pd.read_excel(source_data, index_col=0)
    copy_if_needed(source_data, ctx.artifact("input.xlsx"))
    try:
        result = compute_indices(
            df,
            dmus=int(params["dmus"]),
            periods=int(params["periods"]),
            nx=int(params["nx"]),
            ny=int(params["ny"]),
            nb=int(params["nb"]),
            undesirable=int(params["undesirable"]),
            sup=int(params["sup"]),
            progress=bool(ctx.spec.get("progress", False)),
        )
    except Exception as exc:
        write_audit(ctx, "failed", [f"DEA computation failed: {exc}"], error_type=exc.__class__.__name__)
        return write_manifest(ctx, "failed", error=str(exc), error_type=exc.__class__.__name__)
    output = ctx.artifact("allindex.xlsx")
    write_excel(result, output)
    write_audit(
        ctx,
        "ok",
        ["DEA adapter ran the vendored skill4econ.backends.dea module in-process."],
        backend="vendored",
        backend_module="skill4econ.backends.dea",
        source_snapshot="skill4econ.backends.dea.original.dea_calculator.py",
        second_stage_available=False,
        environmental_determinants_claim=False,
        sheets=list(result.as_sheet_dict().keys()),
        params=result.meta,
    )
    return write_manifest(
        ctx,
        "ok",
        backend="vendored",
        backend_module="skill4econ.backends.dea",
        source_snapshot="skill4econ.backends.dea.original.dea_calculator.py",
        second_stage_available=False,
        environmental_determinants_claim=False,
        output=str(output),
        sheets=list(result.as_sheet_dict().keys()),
        params=result.meta,
    )


def _run_external_dea_backend(
    ctx: RunContext,
    backend_root: Path,
    source_data: Path,
    params: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    calc_src = backend_root / "dea_calculator.py"
    if not calc_src.exists():
        write_audit(
            ctx,
            "missing_dependency",
            [
                f"External DEA backend path {backend_root} does not contain dea_calculator.py.",
                *[f"  - {step}" for step in dea_discovery_chain()],
            ],
        )
        return write_manifest(
            ctx,
            "missing_dependency",
            backend="external",
            backend_root=str(backend_root),
            discovery_source=source,
        )
    work = ctx.run_dir / "dea_work"
    work.mkdir(exist_ok=True)
    copy_if_needed(source_data, work / "t1.xlsx")
    calc_tmp = work / "dea_calculator_skill4econ.py"
    code = calc_src.read_text(encoding="utf-8", errors="replace")
    import re

    for key, value in params.items():
        code = re.sub(rf"^{key}\s*=\s*\d+", f"{key} = {int(value)}", code, flags=re.MULTILINE)
    calc_tmp.write_text(code, encoding="utf-8")
    rc = run_subprocess(
        [sys.executable, str(calc_tmp)],
        cwd=work,
        timeout=int(ctx.spec.get("timeout", 600)),
        stdout_path=ctx.artifact("stdout.log"),
        stderr_path=ctx.artifact("stderr.log"),
    )
    output = work / "allindex.xlsx"
    if output.exists():
        copy_if_needed(output, ctx.artifact("allindex.xlsx"))
    status = "ok" if rc == 0 and output.exists() else "failed"
    write_audit(
        ctx,
        status,
        ["DEA adapter invoked external override backend."],
        backend="external_override",
        backend_root=str(backend_root),
        discovery_source=source,
        returncode=rc,
        output_exists=output.exists(),
    )
    return write_manifest(
        ctx,
        status,
        backend="external_override",
        backend_root=str(backend_root),
        discovery_source=source,
        returncode=rc,
        output=str(ctx.artifact("allindex.xlsx")) if output.exists() else None,
    )


PYTHON_METHODS = {
    "py_preflight": py_preflight,
    "data_audit": data_audit,
    "ols_cluster": ols_cluster,
    "panel_fe_re": panel_fe_re,
    "did_twfe_event": did_twfe_event,
    "iv_2sls": iv_2sls,
    "rdd_local_linear": rdd_local_linear,
    "rdrobust_rdd": rdrobust_rdd,
    "did_event_study": did_event_study,
    "spatial_did_reduced_form": spatial_did_reduced_form,
    "spatial_did": spatial_did_reduced_form,
    "quantile_regression": quantile_regression,
    "threshold_panel_search": threshold_panel_search,
    "threshold_panel": threshold_panel_search,
    "mediation_baron_kenny": mediation_baron_kenny,
    "mediation_moderation": mediation_baron_kenny,
    "synthetic_control_basic": synthetic_control_basic,
    "synthetic_control": synthetic_control_basic,
    "dml_plr_crossfit": dml_plr_crossfit,
    "dml_irm_crossfit": dml_irm_crossfit,
    "cs_did_attgt_py": cs_did_attgt_py,
    "doubleml_adapter": doubleml_adapter,
    "econml_adapter": econml_adapter,
    "psm_overlap_balance": psm_overlap_balance,
    "psm_ipw_match": psm_ipw_match,
    "spatial_weights_factory": spatial_weights_factory,
    "spatial_w_audit": spatial_w_audit,
    "spatial_moran_preflight": spatial_moran_preflight,
    "spatial_spdep_lisa": spatial_spdep_lisa,
    "spatial_exposure_did": spatial_exposure_did,
    "spatial_panel_model_adapter": spatial_panel_model_adapter,
    "spatial_se_comparison": spatial_se_comparison,
    "spatial_w_sensitivity": spatial_w_sensitivity,
    "live_backend_certification": live_backend_certification,
    "flagship_slow_matrix": flagship_slow_matrix,
    "ml_prediction_audit": ml_prediction_audit,
    "plot_diagnostics": plot_diagnostics,
    "dea_sbm_malmquist_adapter": dea_sbm_malmquist_adapter,
}
