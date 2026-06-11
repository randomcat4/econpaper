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


def _normal_pvalue(t_stat: float) -> float:
    if math.isnan(t_stat):
        return math.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _ols_numpy(
    df,
    y: str,
    terms: list[str],
    *,
    cluster: str | None = None,
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
    df_resid = max(n - k, 1)
    if cluster:
        groups = work[cluster].astype(str).to_numpy()
        unique_groups = sorted(set(groups))
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
                "p_value": _normal_pvalue(t_stat),
                "t_stat": t_stat,
            }
        )
    meta = {"nobs": int(n), "df_resid": int(df_resid), "cov_type": cov_type}
    return rows, meta


def _with_constant(df, columns: list[str], name: str = "_const"):
    work = df.copy()
    work[name] = 1.0
    return work, [name, *columns]


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
    import pandas as pd

    columns = [y, treat, post, id_col, time_col, *x]
    if cluster not in columns:
        columns.append(cluster)
    work = df[columns].dropna().copy()
    work["_did_treat_post"] = work[treat].astype(float) * work[post].astype(float)
    design = work[["_did_treat_post", *x]].copy()
    design = design.join(pd.get_dummies(work[id_col].astype(str), prefix=f"fe_{id_col}", drop_first=True))
    design = design.join(
        pd.get_dummies(work[time_col].astype(str), prefix=f"fe_{time_col}", drop_first=True)
    )
    design["_const"] = 1.0
    design[y] = work[y].to_numpy()
    design[cluster] = work[cluster].to_numpy()
    terms = ["_const", "_did_treat_post", *[c for c in design.columns if c not in {y, cluster, "_const", "_did_treat_post"}]]
    rows, meta = _ols_numpy(design, y, terms, cluster=cluster)
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
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["IV2SLS completed."], estimator=estimator, **meta)
    return write_manifest(ctx, "ok", estimator=estimator, **meta)


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


def did_event_study(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Requires y, id, time, and either event_time or gvar/adoption_time. Optional window=[min,max]."],
    )
    if planned:
        return planned
    import pandas as pd

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
    design = work[event_terms + x].copy()
    design = design.join(pd.get_dummies(work[id_col].astype(str), prefix=f"fe_{id_col}", drop_first=True))
    design = design.join(pd.get_dummies(work[time_col].astype(str), prefix=f"fe_{time_col}", drop_first=True))
    design["_const"] = 1.0
    design[y] = work[y].to_numpy()
    design[cluster] = work[cluster].to_numpy()
    terms = ["_const", *event_terms, *x, *[c for c in design.columns if c not in {y, cluster, "_const", *event_terms, *x}]]
    rows, meta = _ols_numpy(design, y, terms, cluster=cluster)
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
    import pandas as pd

    design = work[["_D", "_WD", *x, *w_x]].copy()
    design = design.join(pd.get_dummies(work[id_col].astype(str), prefix=f"fe_{id_col}", drop_first=True))
    design = design.join(pd.get_dummies(work[time_col].astype(str), prefix=f"fe_{time_col}", drop_first=True))
    design["_const"] = 1.0
    design[y] = work[y].to_numpy()
    cluster = str(ctx.spec.get("cluster", id_col))
    design[cluster] = work[cluster].to_numpy()
    keep_terms = ["_D", "_WD", *x, *w_x]
    terms = ["_const", *keep_terms, *[c for c in design.columns if c not in {y, cluster, "_const", *keep_terms}]]
    rows, meta = _ols_numpy(design, y, terms, cluster=cluster)
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
        from sklearn.linear_model import QuantileRegressor
    except Exception:
        return missing_dependency(ctx, "sklearn", "quantile regression")

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    x = listify(ctx.spec.get("x") or ctx.spec.get("covars"))
    if not y or not x:
        raise Skill4EconError("quantile_regression requires y and at least one x/covar.")
    require_columns(df, [y, *x], "quantile regression")
    tau = float(ctx.spec.get("quantile", ctx.spec.get("tau", 0.5)))
    alpha = float(ctx.spec.get("alpha", 0.0))
    work = df[[y, *x]].dropna().copy()
    model = QuantileRegressor(quantile=tau, alpha=alpha, solver="highs")
    model.fit(work[x], work[y])
    rows = [{"term": "_intercept", "coef": float(model.intercept_), "std_error": math.nan, "p_value": math.nan}]
    rows.extend(
        {"term": term, "coef": float(coef), "std_error": math.nan, "p_value": math.nan}
        for term, coef in zip(x, model.coef_)
    )
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["Quantile regression completed."], estimator="sklearn.QuantileRegressor", quantile=tau)
    return write_manifest(ctx, "ok", estimator="sklearn.QuantileRegressor", quantile=tau, nobs=int(len(work)))


def threshold_panel_search(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Requires y, x, threshold, id, time. Searches candidate thresholds and fits two-regime slopes."],
    )
    if planned:
        return planned
    import numpy as np
    import pandas as pd

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
        design = pd.DataFrame(index=work.index)
        low = (work[threshold] <= cand).astype(float)
        high = 1.0 - low
        for var in x:
            design[f"{var}_low"] = work[var].astype(float) * low
            design[f"{var}_high"] = work[var].astype(float) * high
        design = design.join(pd.get_dummies(work[id_col].astype(str), prefix=f"fe_{id_col}", drop_first=True))
        design = design.join(pd.get_dummies(work[time_col].astype(str), prefix=f"fe_{time_col}", drop_first=True))
        design["_const"] = 1.0
        design[y] = work[y].to_numpy()
        terms = ["_const", *[c for c in design.columns if c not in {y, "_const"}]]
        rows, _ = _ols_numpy(design, y, terms)
        beta = np.array([row["coef"] for row in rows], dtype=float)
        resid = design[y].to_numpy(dtype=float) - design[terms].to_numpy(dtype=float) @ beta
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
    a = next(row["coef"] for row in m_rows if row["term"] == treat)
    b = next(row["coef"] for row in direct_rows if row["term"] == mediator)
    total = next(row["coef"] for row in total_rows if row["term"] == treat)
    direct = next(row["coef"] for row in direct_rows if row["term"] == treat)
    rows = [
        {"term": "a_treat_to_mediator", "coef": a, "std_error": next(row["std_error"] for row in m_rows if row["term"] == treat), "p_value": next(row["p_value"] for row in m_rows if row["term"] == treat)},
        {"term": "b_mediator_to_y", "coef": b, "std_error": next(row["std_error"] for row in direct_rows if row["term"] == mediator), "p_value": next(row["p_value"] for row in direct_rows if row["term"] == mediator)},
        {"term": "total_effect", "coef": total, "std_error": next(row["std_error"] for row in total_rows if row["term"] == treat), "p_value": next(row["p_value"] for row in total_rows if row["term"] == treat)},
        {"term": "direct_effect", "coef": direct, "std_error": next(row["std_error"] for row in direct_rows if row["term"] == treat), "p_value": next(row["p_value"] for row in direct_rows if row["term"] == treat)},
        {"term": "indirect_effect_ab", "coef": float(a * b), "std_error": math.nan, "p_value": math.nan},
    ]
    write_model_table(ctx, rows)
    write_audit(ctx, "ok", ["Baron-Kenny style mediation completed; bootstrap inference not included."], estimator="numpy OLS mediation")
    return write_manifest(ctx, "ok", estimator="numpy OLS mediation", nobs=int(len(work)))


def synthetic_control_basic(ctx: RunContext) -> dict[str, Any]:
    planned = _plan_or_dry(
        ctx,
        ["Requires y, id, time, treated_unit, treatment_time. Uses pre-treatment outcome path as predictors."],
    )
    if planned:
        return planned
    import numpy as np
    import pandas as pd
    from scipy.optimize import minimize

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
    if int(pre.sum()) < 2:
        raise Skill4EconError("Synthetic control requires at least two pre-treatment periods.")
    donors = [col for col in pivot.columns if col != treated_unit]
    X0 = pivot.loc[pre, donors].to_numpy(dtype=float)
    X1 = pivot.loc[pre, treated_unit].to_numpy(dtype=float)
    keep = ~np.isnan(X0).any(axis=0)
    donors = [donor for donor, ok in zip(donors, keep) if ok]
    X0 = X0[:, keep]
    if X0.shape[1] == 0:
        raise Skill4EconError("No complete donor units for synthetic control.")
    n_donors = X0.shape[1]
    objective = lambda w: float(np.sum((X1 - X0 @ w) ** 2))
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = [(0.0, 1.0)] * n_donors
    result = minimize(objective, np.ones(n_donors) / n_donors, bounds=bounds, constraints=cons)
    if not result.success:
        raise Skill4EconError(f"Synthetic control optimizer failed: {result.message}")
    weights = result.x
    synth = pivot[donors].to_numpy(dtype=float) @ weights
    fit = pd.DataFrame({"time": list(pivot.index), "treated": pivot[treated_unit].to_numpy(dtype=float), "synthetic": synth})
    fit["gap"] = fit["treated"] - fit["synthetic"]
    fit.to_csv(ctx.artifact("synthetic_fit.csv"), index=False, encoding="utf-8-sig")
    weight_rows = [{"term": str(donor), "coef": float(weight), "std_error": math.nan, "p_value": math.nan} for donor, weight in zip(donors, weights)]
    write_model_table(ctx, weight_rows)
    pre_rmse = float(np.sqrt(np.mean(fit.loc[pivot.index < treatment_time, "gap"].to_numpy(dtype=float) ** 2)))
    post_att = float(fit.loc[pivot.index >= treatment_time, "gap"].mean())
    write_audit(ctx, "ok", ["Basic synthetic control completed."], estimator="scipy constrained least squares", pre_rmse=pre_rmse, post_att=post_att)
    return write_manifest(ctx, "ok", estimator="scipy constrained least squares", pre_rmse=pre_rmse, post_att=post_att, donors=len(donors))


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
    if not y or not treatment or not x:
        raise Skill4EconError("dml_plr_crossfit requires y, treatment/d/treat, and at least one x/feature.")
    require_columns(df, [y, treatment, *x], "DML PLR")
    work = df[[y, treatment, *x]].dropna().copy()
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
    se = float(np.sqrt(np.mean(score**2) / (denom**2 * len(work))))
    t_stat = float(theta / se) if se > 0 else math.nan
    rows = [{"term": "theta_plr", "coef": theta, "std_error": se, "t_stat": t_stat, "p_value": _normal_pvalue(t_stat), "nobs": int(len(work))}]
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
        "cluster_se": "not implemented",
        "identification": ["partial linear model", "orthogonality", "unconfoundedness conditional on X"],
    }
    write_json(ctx.artifact("dml_diagnostics.json"), diagnostics)
    write_audit(ctx, "ok", ["DML PLR sklearn cross-fitting fallback completed.", diagnostics["estimator"]], **diagnostics)
    return write_manifest(ctx, "ok", estimator=diagnostics["estimator"], nobs=int(len(work)), folds=folds)


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
    if not y or not treatment or not x:
        raise Skill4EconError("dml_irm_crossfit requires y, binary treatment/d/treat, and at least one x/feature.")
    require_columns(df, [y, treatment, *x], "DML IRM")
    work = df[[y, treatment, *x]].dropna().copy()
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
    se_ate = float(np.std(score_ate, ddof=1) / np.sqrt(len(score_ate)))
    t_ate = float(ate / se_ate) if se_ate > 0 else math.nan
    treated_share = float(dk.mean())
    att_score = (dk * (yk - mu0k) - (1 - dk) * p / (1 - p) * (yk - mu0k)) / treated_share
    att = float(np.mean(att_score))
    se_att = float(np.std(att_score, ddof=1) / np.sqrt(len(att_score)))
    t_att = float(att / se_att) if se_att > 0 else math.nan
    rows = [
        {"term": "ATE_aipw", "coef": ate, "std_error": se_ate, "t_stat": t_ate, "p_value": _normal_pvalue(t_ate), "nobs": int(keep.sum())},
        {"term": "ATT_aipw", "coef": att, "std_error": se_att, "t_stat": t_att, "p_value": _normal_pvalue(t_att), "nobs": int(keep.sum())},
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
        "cluster_se": "not implemented",
        "identification": ["unconfoundedness conditional on X", "overlap", "orthogonal AIPW score"],
    }
    write_json(ctx.artifact("dml_diagnostics.json"), diagnostics)
    write_audit(ctx, "ok", ["DML IRM sklearn cross-fitting fallback completed.", diagnostics["estimator"]], **diagnostics)
    return write_manifest(ctx, "ok", estimator=diagnostics["estimator"], nobs=int(keep.sum()), folds=folds)


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
    from sklearn.neighbors import NearestNeighbors

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
    nn = NearestNeighbors(n_neighbors=1).fit(control[["_pscore"]])
    distances, indices = nn.kneighbors(treated[["_pscore"]])
    matched_control = control.iloc[indices.flatten()].reset_index(drop=True)
    treated = treated.reset_index(drop=True)
    att = float((treated[y] - matched_control[y]).mean())
    pscore = np.clip(work["_pscore"].to_numpy(dtype=float), 1e-6, 1 - 1e-6)
    treat_arr = work[treat].to_numpy(dtype=float)
    y_arr = work[y].to_numpy(dtype=float)
    treated_share = float(treat_arr.mean())
    if treated_share <= 0 or treated_share >= 1:
        raise Skill4EconError("IPW requires both treated and control observations.")
    ate_ipw = float(np.mean(treat_arr * y_arr / pscore - (1 - treat_arr) * y_arr / (1 - pscore)))
    att_ipw = float(
        (np.mean(treat_arr * y_arr) - np.mean((1 - treat_arr) * pscore * y_arr / (1 - pscore)))
        / treated_share
    )
    rows = [
        {"term": "ATT_nearest_neighbor", "coef": att, "std_error": math.nan, "p_value": math.nan},
        {"term": "ATE_ipw", "coef": ate_ipw, "std_error": math.nan, "p_value": math.nan},
        {"term": "ATT_ipw", "coef": att_ipw, "std_error": math.nan, "p_value": math.nan},
    ]
    write_model_table(ctx, rows)
    write_json(
        ctx.artifact("psm_diagnostics.json"),
        {
            "treated_n": int(len(treated)),
            "control_n": int(len(control)),
            "mean_match_distance": float(np.mean(distances)),
            "pscore_min": float(pscore.min()),
            "pscore_max": float(pscore.max()),
            "overlap_balance": diag["diagnostics"],
        },
    )
    write_audit(
        ctx,
        "ok",
        ["PSM nearest-neighbor, simple IPW, and diagnostics completed."],
        estimator="sklearn",
        warnings=diag["warnings"],
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="sklearn PSM + numpy IPW",
        warnings=diag["warnings"],
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
