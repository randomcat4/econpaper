from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _warning(code: str, severity: str, message: str, action: str) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "action": action}


def _quantiles(values: Any) -> dict[str, float]:
    import numpy as np

    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {key: math.nan for key in ["p1", "p5", "p50", "p95", "p99"]}
    qs = np.quantile(arr, [0.01, 0.05, 0.5, 0.95, 0.99])
    return {key: float(value) for key, value in zip(["p1", "p5", "p50", "p95", "p99"], qs)}


def _weighted_mean_var(values: Any, weights: Any) -> tuple[float, float]:
    import numpy as np
    import pandas as pd

    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    mask = v.notna() & w.notna() & (w > 0)
    if not bool(mask.any()):
        return math.nan, math.nan
    vv = v[mask].to_numpy(dtype=float)
    ww = w[mask].to_numpy(dtype=float)
    total = float(ww.sum())
    if total <= 0:
        return math.nan, math.nan
    mean = float(np.sum(ww * vv) / total)
    var = float(np.sum(ww * (vv - mean) ** 2) / total)
    return mean, var


def _pooled_unweighted_sd_by_var(work: Any, treat: str, variables: list[str]) -> dict[str, float]:
    import math
    import numpy as np
    import pandas as pd

    wt = work[treat] == 1
    wc = work[treat] == 0
    result: dict[str, float] = {}
    for var in variables:
        if var not in work.columns:
            continue
        treated = pd.to_numeric(work.loc[wt, var], errors="coerce").dropna()
        control = pd.to_numeric(work.loc[wc, var], errors="coerce").dropna()
        treated_var = float(treated.var(ddof=1)) if len(treated) > 1 else math.nan
        control_var = float(control.var(ddof=1)) if len(control) > 1 else math.nan
        if np.isfinite(treated_var + control_var) and (treated_var + control_var) > 0:
            result[var] = float(math.sqrt((treated_var + control_var) / 2))
        else:
            result[var] = math.nan
    return result


def _effective_sample_size(weights: Any) -> float:
    import numpy as np

    arr = np.asarray(weights, dtype=float)
    arr = arr[np.isfinite(arr) & (arr > 0)]
    denom = float(np.sum(arr**2))
    if denom <= 0:
        return 0.0
    return float(np.sum(arr) ** 2 / denom)


def _top_share(weights: Any, share: float = 0.01) -> float:
    import numpy as np

    arr = np.asarray(weights, dtype=float)
    arr = arr[np.isfinite(arr) & (arr > 0)]
    if arr.size == 0 or float(arr.sum()) <= 0:
        return 0.0
    n_top = max(1, int(math.ceil(arr.size * share)))
    return float(np.sort(arr)[-n_top:].sum() / arr.sum())


def _estimate_propensity(work: Any, treat: str, covariates: list[str], spec: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    import numpy as np
    import pandas as pd

    supplied = spec.get("propensity_score") or spec.get("pscore") or spec.get("pscore_col")
    if supplied:
        col = str(supplied)
        if col not in work.columns:
            raise ValueError(f"user-supplied propensity score column not found: {col}")
        pscore = pd.to_numeric(work[col], errors="coerce")
        if pscore.isna().any():
            raise ValueError(f"user-supplied propensity score column has missing/non-numeric values: {col}")
        return np.clip(pscore.to_numpy(dtype=float), 1e-6, 1 - 1e-6), {
            "ps_model": "user_supplied",
            "pscore_col": col,
            "covariates": covariates,
        }

    model_type = str(spec.get("ps_model") or spec.get("propensity_model") or "logit").lower()
    if not covariates:
        raise ValueError("propensity score estimation requires x/covars unless pscore_col is supplied.")
    if model_type == "probit":
        import statsmodels.api as sm

        y = pd.to_numeric(work[treat], errors="coerce").to_numpy(dtype=float)
        X = sm.add_constant(work[covariates].astype(float), has_constant="add")
        model = sm.Probit(y, X).fit(disp=0)
        pscore = model.predict(X)
        return np.clip(pscore, 1e-6, 1 - 1e-6), {
            "ps_model": "probit",
            "covariates": covariates,
            "converged": bool(getattr(model, "mle_retvals", {}).get("converged", True)),
        }

    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(max_iter=int(spec.get("ps_max_iter", 1000)))
    model.fit(work[covariates], work[treat])
    pscore = model.predict_proba(work[covariates])[:, 1]
    return np.clip(pscore, 1e-6, 1 - 1e-6), {
        "ps_model": "logit",
        "covariates": covariates,
        "intercept": float(model.intercept_[0]),
        "coef": {name: float(value) for name, value in zip(covariates, model.coef_[0])},
    }


def _summary_rows(work: Any, treat: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, frame in [
        ("all", work),
        ("treated", work[work[treat] == 1]),
        ("control", work[work[treat] == 0]),
    ]:
        values = frame["_pscore"].astype(float)
        q = _quantiles(values)
        rows.append(
            {
                "group": label,
                "n": int(len(values)),
                "min": float(values.min()) if len(values) else math.nan,
                "max": float(values.max()) if len(values) else math.nan,
                "mean": float(values.mean()) if len(values) else math.nan,
                "sd": float(values.std(ddof=1)) if len(values) > 1 else math.nan,
                **q,
            }
        )
    return rows


def _off_support_table(work: Any, treat: str, lower: float, upper: float, has_common: bool) -> Any:
    import numpy as np

    result = work.copy()
    if has_common:
        result["_off_support"] = (result["_pscore"] < lower) | (result["_pscore"] > upper)
        result["_off_support_reason"] = np.where(
            result["_pscore"] < lower,
            "below_common_support",
            np.where(result["_pscore"] > upper, "above_common_support", ""),
        )
    else:
        result["_off_support"] = True
        result["_off_support_reason"] = "no_common_support_interval"
    keep_cols = [col for col in ["_row_id", treat, "_pscore", "_off_support_reason"] if col in result.columns]
    return result.loc[result["_off_support"], keep_cols].copy()


def _balance_rows(
    work: Any,
    treat: str,
    variables: list[str],
    weights: Any,
    label: str,
    standardizer: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    import numpy as np

    rows: list[dict[str, Any]] = []
    wt = work[treat] == 1
    wc = work[treat] == 0
    for var in variables:
        if var not in work.columns:
            continue
        treated_mean, treated_var = _weighted_mean_var(work.loc[wt, var], weights.loc[wt])
        control_mean, control_var = _weighted_mean_var(work.loc[wc, var], weights.loc[wc])
        supplied_denom = (standardizer or {}).get(var)
        if supplied_denom and np.isfinite(supplied_denom) and supplied_denom > 0:
            denom = float(supplied_denom)
            denominator_source = "unweighted_pooled_pre_adjustment_sd"
        else:
            denom = math.sqrt((treated_var + control_var) / 2) if np.isfinite(treated_var + control_var) and (treated_var + control_var) > 0 else math.nan
            denominator_source = "weighted_stage_pooled_sd"
        smd = (treated_mean - control_mean) / denom if denom and np.isfinite(denom) else (0.0 if treated_mean == control_mean else math.nan)
        variance_ratio = treated_var / control_var if control_var and np.isfinite(control_var) else math.nan
        abs_smd = abs(float(smd)) if np.isfinite(smd) else math.nan
        smd_flag = "red" if np.isfinite(abs_smd) and abs_smd > 0.25 else ("yellow" if np.isfinite(abs_smd) and abs_smd > 0.10 else "ok")
        rows.append(
            {
                "stage": label,
                "variable": var,
                "treated_mean": treated_mean,
                "control_mean": control_mean,
                "weighted_treated_mean": treated_mean,
                "weighted_control_mean": control_mean,
                "smd_denominator": denom,
                "smd_denominator_source": denominator_source,
                "smd": float(smd) if np.isfinite(smd) else math.nan,
                "abs_smd": abs_smd,
                "smd_flag": smd_flag,
                "variance_ratio": float(variance_ratio) if np.isfinite(variance_ratio) else math.nan,
                "treated_missing_rate": float(work.loc[wt, var].isna().mean()) if int(wt.sum()) else math.nan,
                "control_missing_rate": float(work.loc[wc, var].isna().mean()) if int(wc.sum()) else math.nan,
            }
        )
    return rows


def _ipw_weights(work: Any, treat: str, *, stabilized: bool = False, trim: float | None = None) -> Any:
    import numpy as np
    import pandas as pd

    d = work[treat].astype(float).to_numpy()
    p = work["_pscore"].astype(float).to_numpy()
    if trim is not None:
        p = np.clip(p, trim, 1 - trim)
    treated_share = float(d.mean())
    weights = d / p + (1 - d) / (1 - p)
    if stabilized:
        weights = d * treated_share / p + (1 - d) * (1 - treated_share) / (1 - p)
    return pd.Series(weights, index=work.index, name="_weight")


def _matching_weights(work: Any, treat: str, spec: dict[str, Any]) -> Any:
    import pandas as pd
    from sklearn.neighbors import NearestNeighbors

    treated = work[work[treat] == 1]
    control = work[work[treat] == 0]
    if treated.empty or control.empty:
        raise ValueError("PSM diagnostics require both treated and control observations.")
    nn = NearestNeighbors(n_neighbors=1).fit(control[["_pscore"]])
    distances, indices = nn.kneighbors(treated[["_pscore"]])
    caliper = spec.get("matching_caliper") or spec.get("caliper")
    caliper_value = float(caliper) if caliper is not None else None
    weights = pd.Series(0.0, index=work.index, name="_match_weight")
    control_indices = control.index.to_list()
    for treated_idx, distance, matched_pos in zip(treated.index.to_list(), distances.flatten(), indices.flatten()):
        if caliper_value is not None and float(distance) > caliper_value:
            continue
        weights.loc[treated_idx] += 1.0
        weights.loc[control_indices[int(matched_pos)]] += 1.0
    return weights


def _weight_summary_row(name: str, weights: Any) -> dict[str, Any]:
    import numpy as np

    arr = np.asarray(weights, dtype=float)
    positive = arr[np.isfinite(arr) & (arr > 0)]
    if positive.size == 0:
        return {"weight_type": name, "n": 0}
    return {
        "weight_type": name,
        "n": int(positive.size),
        "mean": float(np.mean(positive)),
        "max": float(np.max(positive)),
        "p95": float(np.quantile(positive, 0.95)),
        "p99": float(np.quantile(positive, 0.99)),
        "effective_sample_size": _effective_sample_size(positive),
        "effective_sample_size_share": float(_effective_sample_size(positive) / positive.size),
        "top_1pct_weight_share": _top_share(positive, 0.01),
    }


def _plot_propensity(work: Any, treat: str, density_path: Path, hist_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    density_path.parent.mkdir(parents=True, exist_ok=True)
    treated = work.loc[work[treat] == 1, "_pscore"].astype(float)
    control = work.loc[work[treat] == 0, "_pscore"].astype(float)
    bins = 24

    plt.figure(figsize=(7, 4))
    plt.hist(control, bins=bins, density=True, histtype="step", linewidth=2, label="control")
    plt.hist(treated, bins=bins, density=True, histtype="step", linewidth=2, label="treated")
    plt.xlabel("Propensity score")
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()
    plt.savefig(density_path, dpi=160)
    plt.close()

    plt.figure(figsize=(7, 4))
    plt.hist(control, bins=bins, alpha=0.55, label="control")
    plt.hist(treated, bins=bins, alpha=0.55, label="treated")
    plt.xlabel("Propensity score")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(hist_path, dpi=160)
    plt.close()


def _plot_love(before: list[dict[str, Any]], after_ipw: list[dict[str, Any]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    variables = [row["variable"] for row in before]
    before_map = {row["variable"]: row.get("abs_smd") for row in before}
    after_map = {row["variable"]: row.get("abs_smd") for row in after_ipw}
    y = list(range(len(variables)))
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, max(3, 0.35 * len(variables) + 1.5)))
    plt.axvline(0.1, color="#999999", linestyle="--", linewidth=1)
    plt.scatter([before_map.get(var, math.nan) for var in variables], y, label="before", color="#444444")
    plt.scatter([after_map.get(var, math.nan) for var in variables], y, label="after_ipw", color="#1f77b4")
    plt.yticks(y, variables)
    plt.xlabel("Absolute standardized mean difference")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_weights(weights: Any, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    plt.hist(weights, bins=30, color="#4c78a8", alpha=0.85)
    plt.xlabel("IPW weight")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _normal_pvalue(t_stat: float) -> float:
    if not math.isfinite(t_stat):
        return math.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2)))


def _grid_values(value: Any, default: list[Any], cast: Any) -> list[Any]:
    values = _listify(value) if value is not None else default
    result: list[Any] = []
    for item in values:
        if isinstance(item, str) and item.lower() in {"true", "false"}:
            result.append(item.lower() == "true")
        else:
            result.append(cast(item))
    return result


def _psm_grid_match(
    work: Any,
    *,
    y: str,
    treat: str,
    balance_vars: list[str],
    standardizer: dict[str, float],
    n_neighbors: int,
    caliper: float,
    replacement: bool,
) -> dict[str, Any]:
    import numpy as np
    import pandas as pd

    treated = work[work[treat] == 1].copy()
    control = work[work[treat] == 0].copy()
    control_indices = control.index.to_list()
    available = set(control_indices)
    effects: list[float] = []
    matched_treated: list[Any] = []
    matched_controls: list[list[Any]] = []
    weights = pd.Series(0.0, index=work.index, name="_grid_match_weight")

    for treated_idx, treated_row in treated.sort_values("_pscore").iterrows():
        candidates = control_indices if replacement else [idx for idx in control_indices if idx in available]
        scored = []
        for control_idx in candidates:
            distance = abs(float(treated_row["_pscore"]) - float(work.loc[control_idx, "_pscore"]))
            if distance <= caliper:
                scored.append((distance, control_idx))
        scored.sort(key=lambda item: item[0])
        chosen = [idx for _, idx in scored[:n_neighbors]]
        if not chosen:
            continue
        matched_treated.append(treated_idx)
        matched_controls.append(chosen)
        weights.loc[treated_idx] += 1.0
        for control_idx in chosen:
            weights.loc[control_idx] += 1.0 / len(chosen)
            if not replacement and control_idx in available:
                available.remove(control_idx)
        treated_y = float(treated_row[y])
        control_y = float(work.loc[chosen, y].astype(float).mean())
        effects.append(treated_y - control_y)

    matched_n = len(effects)
    treated_n = int(len(treated))
    sample_loss = float(1 - matched_n / treated_n) if treated_n else math.nan
    if matched_n:
        arr = np.asarray(effects, dtype=float)
        att = float(np.mean(arr))
        se = float(np.std(arr, ddof=1) / math.sqrt(matched_n)) if matched_n > 1 else math.nan
        t_stat = float(att / se) if se and math.isfinite(se) and se > 0 else math.nan
        p_value = _normal_pvalue(t_stat)
        ci_low = float(att - 1.96 * se) if se and math.isfinite(se) else math.nan
        ci_high = float(att + 1.96 * se) if se and math.isfinite(se) else math.nan
        max_smd = max(
            (
                row.get("abs_smd") or 0.0
                for row in _balance_rows(work, treat, balance_vars, weights, "psm_grid", standardizer)
            ),
            default=math.nan,
        )
    else:
        att = se = t_stat = p_value = ci_low = ci_high = max_smd = math.nan

    return {
        "n_neighbors": int(n_neighbors),
        "caliper": float(caliper),
        "replacement": bool(replacement),
        "matched_treated_n": int(matched_n),
        "treated_n": treated_n,
        "matched_control_unique_n": int(len({idx for group in matched_controls for idx in group})),
        "sample_loss": sample_loss,
        "max_smd_after_matching": float(max_smd) if math.isfinite(max_smd) else math.nan,
        "att": att,
        "std_error": se,
        "std_error_method": "naive_matched_pair_sd_not_abadie_imbens" if math.isfinite(se) else "not_available",
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_value": p_value,
        "significant_5pct": bool(p_value < 0.05) if math.isfinite(p_value) else None,
    }


def _plot_psm_grid(rows: list[dict[str, Any]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plottable = [row for row in rows if math.isfinite(float(row.get("att", math.nan)))]
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, max(3, 0.32 * max(len(plottable), 1) + 1.5)))
    if not plottable:
        plt.text(0.5, 0.5, "No matched PSM grid specifications", ha="center", va="center")
        plt.axis("off")
    else:
        labels = [
            f"k={row['n_neighbors']}, c={row['caliper']:.2f}, {'rep' if row['replacement'] else 'norep'}"
            for row in plottable
        ]
        y_pos = list(range(len(plottable)))
        estimates = [float(row["att"]) for row in plottable]
        errors = [
            max(0.0, float(row["att"]) - float(row["ci_low"])) if math.isfinite(float(row.get("ci_low", math.nan))) else 0.0
            for row in plottable
        ]
        plt.axvline(0, color="#777777", linewidth=1)
        plt.errorbar(estimates, y_pos, xerr=errors, fmt="o", capsize=2, color="#1f77b4")
        plt.yticks(y_pos, labels, fontsize=8)
        plt.xlabel("PSM ATT with approximate 95% CI")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _psm_sensitivity_grid(
    work: Any,
    spec: dict[str, Any],
    y: str,
    treat: str,
    balance_vars: list[str],
    standardizer: dict[str, float],
    tables: Path,
    figures: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    neighbors = _grid_values(spec.get("psm_grid_neighbors"), [1, 2, 3, 5], int)
    calipers = _grid_values(spec.get("psm_grid_calipers"), [0.01, 0.03, 0.05], float)
    replacements = _grid_values(spec.get("psm_grid_replacement"), [True, False], bool)
    rows: list[dict[str, Any]] = []
    for n_neighbors in neighbors:
        for caliper in calipers:
            for replacement in replacements:
                rows.append(
                    _psm_grid_match(
                        work,
                        y=y,
                        treat=treat,
                        balance_vars=balance_vars,
                        standardizer=standardizer,
                        n_neighbors=int(n_neighbors),
                        caliper=float(caliper),
                        replacement=bool(replacement),
                    )
                )
    import pandas as pd

    pd.DataFrame(rows).to_csv(tables / "psm_grid_results.csv", index=False, encoding="utf-8-sig")
    _plot_psm_grid(rows, figures / "psm_grid_forest.png")

    warnings: list[dict[str, Any]] = []
    matched_rows = [row for row in rows if int(row.get("matched_treated_n") or 0) > 0]
    if any(str(row.get("std_error_method")) == "naive_matched_pair_sd_not_abadie_imbens" for row in matched_rows):
        warnings.append(
            _warning(
                "PSM_NAIVE_SE_NOT_ABADIE_IMBENS",
                "yellow",
                "PSM grid confidence intervals use a naive matched-pair standard error, not Abadie-Imbens matching inference.",
                "Use the grid for diagnostic sensitivity only; do not report these p-values as publication-grade matching inference.",
            )
        )
    sample_loss_threshold = float(spec.get("psm_sample_loss_threshold", 0.30))
    if (not matched_rows and rows) or (matched_rows and min(float(row.get("sample_loss") or 0.0) for row in matched_rows) > sample_loss_threshold):
        warnings.append(
            _warning(
                "PSM_SAMPLE_LOSS_HIGH",
                "red",
                "Every PSM grid specification loses more than 30% of treated observations.",
                "Do not treat matched-sample DID as representative without revising support/calipers.",
            )
        )
    estimates = [float(row.get("att")) for row in matched_rows if math.isfinite(float(row.get("att", math.nan)))]
    has_sign_flip = bool(estimates and min(estimates) < 0 < max(estimates))
    sig_values = {row.get("significant_5pct") for row in matched_rows if row.get("significant_5pct") is not None}
    if has_sign_flip or len(sig_values) > 1:
        warnings.append(
            _warning(
                "TRIM_SENSITIVITY_UNSTABLE",
                "yellow",
                "PSM grid estimates change sign or 5% significance status across plausible matching specifications.",
                "Report the grid as sensitivity evidence and avoid presenting one caliper/neighbor choice as decisive.",
            )
        )
    return rows, warnings


def run_overlap_balance_diagnostics(df: Any, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import roc_auc_score

    out = Path(output_dir)
    tables = out / "tables"
    figures = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    y = str(spec.get("y") or spec.get("outcome") or "")
    treat = str(spec.get("treat") or spec.get("treatment") or "")
    covariates = _listify(spec.get("x") or spec.get("covars") or spec.get("controls"))
    balance_vars = _unique(_listify(spec.get("balance_vars")) or covariates)
    id_cols = _listify(spec.get("id") or spec.get("unit_id")) + _listify(spec.get("time") or spec.get("time_id"))
    supplied_pscore = spec.get("propensity_score") or spec.get("pscore") or spec.get("pscore_col")
    required = _unique([y, treat, *covariates, *balance_vars, *id_cols, str(supplied_pscore or "")])
    missing = [col for col in required if col and col not in df.columns]
    if missing:
        raise ValueError(f"PSM/IPW diagnostics missing required columns: {missing}")
    if not treat:
        raise ValueError("PSM/IPW diagnostics require treat/treatment.")
    model_required = [treat, *(covariates if not supplied_pscore else [str(supplied_pscore)])]
    work = df[required].copy()
    work["_row_id"] = work.index
    work = work.dropna(subset=model_required).copy()
    work[treat] = pd.to_numeric(work[treat], errors="coerce")
    if set(work[treat].dropna().astype(float).unique().tolist()) - {0.0, 1.0}:
        raise ValueError("PSM/IPW diagnostics require a binary 0/1 treatment column.")
    work[treat] = work[treat].astype(int)
    if int((work[treat] == 1).sum()) == 0 or int((work[treat] == 0).sum()) == 0:
        raise ValueError("PSM/IPW diagnostics require both treated and control observations.")

    pscore, model_info = _estimate_propensity(work, treat, covariates, spec)
    work["_pscore"] = pscore

    treated_ps = work.loc[work[treat] == 1, "_pscore"].astype(float)
    control_ps = work.loc[work[treat] == 0, "_pscore"].astype(float)
    common_lower = float(max(treated_ps.min(), control_ps.min()))
    common_upper = float(min(treated_ps.max(), control_ps.max()))
    has_common = bool(common_lower <= common_upper)
    common_width = float(max(0.0, common_upper - common_lower))
    off_support = _off_support_table(work, treat, common_lower, common_upper, has_common)
    off_support_share = float(len(off_support) / len(work)) if len(work) else math.nan

    summary_rows = _summary_rows(work, treat)
    pd.DataFrame(summary_rows).to_csv(tables / "propensity_summary.csv", index=False, encoding="utf-8-sig")
    off_support.to_csv(tables / "off_support_units.csv", index=False, encoding="utf-8-sig")
    _plot_propensity(work, treat, figures / "propensity_overlap_density.png", figures / "propensity_overlap_hist.png")

    weights_ipw = _ipw_weights(work, treat)
    weights_stabilized = _ipw_weights(work, treat, stabilized=True)
    trim = float(spec.get("ipw_trim") or spec.get("trim") or 0.05)
    weights_trimmed = _ipw_weights(work, treat, trim=trim)
    weights_matching = _matching_weights(work, treat, spec)
    smd_standardizer = _pooled_unweighted_sd_by_var(work, treat, balance_vars)

    before_weights = pd.Series(1.0, index=work.index, name="_unweighted")
    before_rows = _balance_rows(work, treat, balance_vars, before_weights, "before", smd_standardizer)
    before_rows = sorted(before_rows, key=lambda row: (row.get("abs_smd") if row.get("abs_smd") == row.get("abs_smd") else -1), reverse=True)
    order = [row["variable"] for row in before_rows]
    rank = {var: idx for idx, var in enumerate(order)}
    matching_rows = sorted(_balance_rows(work, treat, balance_vars, weights_matching, "after_matching", smd_standardizer), key=lambda row: rank.get(row["variable"], 999))
    ipw_rows = sorted(_balance_rows(work, treat, balance_vars, weights_ipw, "after_ipw", smd_standardizer), key=lambda row: rank.get(row["variable"], 999))
    trimmed_ipw_rows = sorted(_balance_rows(work, treat, balance_vars, weights_trimmed, "after_trimmed_ipw", smd_standardizer), key=lambda row: rank.get(row["variable"], 999))
    pd.DataFrame(before_rows).to_csv(tables / "balance_table_before.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(matching_rows).to_csv(tables / "balance_table_after_matching.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ipw_rows).to_csv(tables / "balance_table_after_ipw.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(trimmed_ipw_rows).to_csv(tables / "balance_table_after_trimmed_ipw.csv", index=False, encoding="utf-8-sig")
    _plot_love(before_rows, ipw_rows, figures / "love_plot.png")

    weight_rows = [
        _weight_summary_row("ipw", weights_ipw),
        _weight_summary_row("stabilized_ipw", weights_stabilized),
        _weight_summary_row("trimmed_ipw", weights_trimmed),
    ]
    pd.DataFrame(weight_rows).to_csv(tables / "weight_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(weight_rows).to_csv(tables / "ipw_weight_diagnostics.csv", index=False, encoding="utf-8-sig")
    work_with_weights = work.copy()
    work_with_weights["_ipw_weight"] = weights_ipw
    extreme_cutoff = max(float(spec.get("extreme_weight_threshold", 10.0)), float(np.quantile(weights_ipw, 0.99)))
    extreme_cols = [col for col in ["_row_id", treat, "_pscore", "_ipw_weight", *id_cols] if col in work_with_weights.columns]
    work_with_weights.loc[work_with_weights["_ipw_weight"] >= extreme_cutoff, extreme_cols].to_csv(
        tables / "extreme_weight_units.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _plot_weights(weights_ipw, figures / "weight_histogram.png")
    psm_grid_rows, psm_grid_warnings = (
        _psm_sensitivity_grid(work.dropna(subset=[y]).copy(), spec, y, treat, balance_vars, smd_standardizer, tables, figures)
        if y and y in work.columns
        else ([], [])
    )
    trimming_rows = [
        {
            "trim_rule": "none",
            "max_weight": weight_rows[0].get("max"),
            "p95_weight": weight_rows[0].get("p95"),
            "p99_weight": weight_rows[0].get("p99"),
            "effective_sample_size": weight_rows[0].get("effective_sample_size"),
            "effective_sample_size_share": weight_rows[0].get("effective_sample_size_share"),
        },
        {
            "trim_rule": f"clip_pscore_{trim:g}",
            "max_weight": weight_rows[2].get("max"),
            "p95_weight": weight_rows[2].get("p95"),
            "p99_weight": weight_rows[2].get("p99"),
            "effective_sample_size": weight_rows[2].get("effective_sample_size"),
            "effective_sample_size_share": weight_rows[2].get("effective_sample_size_share"),
        },
    ]
    pd.DataFrame(trimming_rows).to_csv(tables / "ipw_trimming_sensitivity.csv", index=False, encoding="utf-8-sig")

    try:
        auc = float(roc_auc_score(work[treat], work["_pscore"]))
    except Exception:
        auc = math.nan
    max_after_matching = max((row.get("abs_smd") or 0.0 for row in matching_rows), default=0.0)
    max_after_ipw = max((row.get("abs_smd") or 0.0 for row in ipw_rows), default=0.0)
    max_after_trimmed_ipw = max((row.get("abs_smd") or 0.0 for row in trimmed_ipw_rows), default=0.0)
    ipw_summary = weight_rows[0]
    trimmed_summary = weight_rows[2]
    warnings: list[dict[str, Any]] = []
    off_support_threshold = float(spec.get("off_support_threshold", 0.10))
    if off_support_share > off_support_threshold:
        warnings.append(
            _warning(
                "OFF_SUPPORT_HIGH_SHARE",
                "red" if off_support_share > 0.25 else "yellow",
                f"{off_support_share:.1%} of observations are outside common support.",
                "Trim or redesign the comparison set before relying on PSM/IPW estimates.",
            )
        )
    mean_gap = abs(float(treated_ps.mean()) - float(control_ps.mean()))
    poor_overlap = (
        (not has_common)
        or (np.isfinite(auc) and auc > float(spec.get("poor_overlap_auc", 0.95)))
        or mean_gap > float(spec.get("poor_overlap_mean_gap", 0.50))
    )
    if poor_overlap:
        warnings.append(
            _warning(
                "POOR_OVERLAP",
                "red" if (not has_common or off_support_share > 0.25) else "yellow",
                f"Common support width={common_width:.3f}, PS AUC={auc:.3f}, treated-control mean PS gap={mean_gap:.3f}.",
                "Report overlap diagnostics; avoid causal claims where treated/control covariate support barely overlaps.",
            )
        )
    balance_yellow = float(spec.get("balance_smd_yellow", 0.10))
    balance_red = float(spec.get("balance_smd_red", 0.25))
    best_after = min(max_after_matching, max_after_ipw, max_after_trimmed_ipw)
    if best_after > balance_yellow:
        warnings.append(
            _warning(
                "BALANCE_STILL_POOR",
                "red" if best_after > balance_red else "yellow",
                f"Best post-adjustment maximum absolute SMD is {best_after:.3f}.",
                "Do not present PSM/IPW as balanced; revise covariates, trim/caliper, or weaken claims.",
            )
        )
    extreme_threshold = float(spec.get("extreme_weight_threshold", 10.0))
    top_share_threshold = float(spec.get("top_weight_share_threshold", 0.20))
    raw_extreme = bool((ipw_summary.get("max") or 0.0) > extreme_threshold or (ipw_summary.get("top_1pct_weight_share") or 0.0) > top_share_threshold)
    trimmed_extreme = bool((trimmed_summary.get("max") or 0.0) > extreme_threshold or (trimmed_summary.get("top_1pct_weight_share") or 0.0) > top_share_threshold)
    if raw_extreme:
        warnings.append(
            _warning(
                "EXTREME_IPW_WEIGHTS",
                "red" if (ipw_summary.get("max") or 0.0) > extreme_threshold * 2 else "yellow",
                f"Max IPW weight is {ipw_summary.get('max'):.3f}; top 1% hold {(ipw_summary.get('top_1pct_weight_share') or 0.0):.1%} of total weight.",
                "Inspect extreme units and report trimmed/stabilized IPW sensitivity.",
            )
        )
    ess_share = float(ipw_summary.get("effective_sample_size_share") or 0.0)
    if ess_share < float(spec.get("min_effective_sample_size_share", 0.50)):
        warnings.append(
            _warning(
                "LOW_EFFECTIVE_SAMPLE_SIZE",
                "red" if ess_share < 0.25 else "yellow",
                f"IPW effective sample size share is {ess_share:.1%}.",
                "Do not lean on unstable IPW; trim/re-specify the propensity model and report ESS.",
            )
        )
    if raw_extreme and not trimmed_extreme:
        warnings.append(
            _warning(
                "trim_weights_reduced_risk",
                "green",
                "Trimmed IPW reduced the extreme-weight diagnostic below the configured threshold.",
                "Record both raw and trimmed IPW results in robustness tables.",
            )
        )
    warnings.extend(psm_grid_warnings)

    diagnostics = {
        "model_info": model_info,
        "n_obs": int(len(work)),
        "treated_n": int((work[treat] == 1).sum()),
        "control_n": int((work[treat] == 0).sum()),
        "common_support": {
            "lower": common_lower,
            "upper": common_upper,
            "width": common_width,
            "has_common_support": has_common,
            "off_support_n": int(len(off_support)),
            "off_support_share": off_support_share,
            "auc": auc,
        },
        "overlap_status": "fail" if poor_overlap else ("weak" if off_support_share > 0 else "pass"),
        "balance_status": "fail" if best_after > balance_red else ("weak" if best_after > balance_yellow else "pass"),
        "max_standardized_mean_difference_before": max((row.get("abs_smd") or 0.0 for row in before_rows), default=0.0),
        "max_standardized_mean_difference_after": best_after,
        "smd_denominator_source": "unweighted_pooled_pre_adjustment_sd",
        "smd_standardizer": smd_standardizer,
        "effective_sample_size_treated": _effective_sample_size(weights_ipw.loc[work[treat] == 1]),
        "effective_sample_size_control": _effective_sample_size(weights_ipw.loc[work[treat] == 0]),
        "max_weight": ipw_summary.get("max"),
        "p95_weight": ipw_summary.get("p95"),
        "p99_weight": ipw_summary.get("p99"),
        "trim_rules_evaluated": [row["trim_rule"] for row in trimming_rows],
        "retained_share_treated": max(
            (1.0 - float(row.get("sample_loss") or 0.0) for row in psm_grid_rows if row.get("matched_treated_n")),
            default=1.0,
        ),
        "retained_share_control": float((weights_matching.loc[work[treat] == 0] > 0).mean()) if int((work[treat] == 0).sum()) else math.nan,
        "max_abs_smd_after_matching": max_after_matching,
        "max_abs_smd_after_ipw": max_after_ipw,
        "max_abs_smd_after_trimmed_ipw": max_after_trimmed_ipw,
        "psm_grid_specs": len(psm_grid_rows),
        "warnings": warnings,
        "artifacts": {
            "propensity_summary": "tables/propensity_summary.csv",
            "off_support_units": "tables/off_support_units.csv",
            "balance_before": "tables/balance_table_before.csv",
            "balance_after_matching": "tables/balance_table_after_matching.csv",
            "balance_after_ipw": "tables/balance_table_after_ipw.csv",
            "balance_after_trimmed_ipw": "tables/balance_table_after_trimmed_ipw.csv",
            "weight_summary": "tables/weight_summary.csv",
            "ipw_weight_diagnostics": "tables/ipw_weight_diagnostics.csv",
            "ipw_trimming_sensitivity": "tables/ipw_trimming_sensitivity.csv",
            "extreme_weight_units": "tables/extreme_weight_units.csv",
            "psm_grid_results": "tables/psm_grid_results.csv",
            "propensity_density": "figures/propensity_overlap_density.png",
            "propensity_hist": "figures/propensity_overlap_hist.png",
            "love_plot": "figures/love_plot.png",
            "weight_histogram": "figures/weight_histogram.png",
            "psm_grid_forest": "figures/psm_grid_forest.png",
        },
    }
    (out / "overlap_balance_diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "analysis_frame": work,
        "propensity_col": "_pscore",
        "ipw_weights": weights_ipw,
        "matching_weights": weights_matching,
        "diagnostics": diagnostics,
        "warnings": warnings,
    }
