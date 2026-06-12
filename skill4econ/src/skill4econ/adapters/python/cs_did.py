from __future__ import annotations

"""Dependency-gated Python Callaway-Sant'Anna DID adapter.

Backend decision, 2026-06-12: the Python path uses the maintained
`differences.ATTgt` API when available. The API documents cohort-time ATT,
simple aggregation, event aggregation, never-treated and not-yet-treated
controls, clustering, and bootstrap options. `pyfixest` is still recorded in
dependency discovery for future adoption if its DID module exposes the same
ATT(g,t) and event aggregation surface on Windows, but this module does not
fabricate a NumPy CS-DID implementation.
"""

import json
import math
import re
from typing import Any

import pandas as pd

from ...core import RunContext, Skill4EconError, missing_dependency, read_table, require_columns, write_audit, write_json, write_manifest, write_model_table


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    flat = df.copy()
    flat.columns = [
        "_".join(str(part) for part in col if str(part)) if isinstance(col, tuple) else str(col)
        for col in flat.columns
    ]
    return flat


def _first_value(row: pd.Series, candidates: list[str]) -> Any:
    lowered = {str(key).lower(): key for key in row.index}
    normalized = {_normalize_key(str(key)): key for key in row.index}
    for name in candidates:
        key = lowered.get(name.lower())
        if key is not None:
            return row.get(key)
        key = normalized.get(_normalize_key(name))
        if key is not None:
            return row.get(key)
    for name in candidates:
        target = _normalize_key(name)
        for key in row.index:
            key_norm = _normalize_key(str(key))
            if key_norm.endswith(target):
                return row.get(key)
    return None


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _as_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def _model_rows_from_frame(df: pd.DataFrame, *, term_prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if df.empty:
        return rows
    flat = _flatten_columns(df.reset_index())
    for pos, row in flat.iterrows():
        coef = _as_float(_first_value(row, ["ATT", "att", "estimate", "coef", "coefficient"]))
        if not math.isfinite(coef):
            continue
        se = _as_float(_first_value(row, ["std_error", "std.err", "stderr", "std_err", "se"]))
        p_value = _as_float(_first_value(row, ["p_value", "pvalue", "p.val", "p"]))
        ci_low = _as_float(_first_value(row, ["ci_low", "lower", "lower_ci", "conf_low", "2.5%"]))
        ci_high = _as_float(_first_value(row, ["ci_high", "upper", "upper_ci", "conf_high", "97.5%"]))
        t_stat = coef / se if math.isfinite(se) and se > 0 else math.nan
        if not math.isfinite(p_value) and math.isfinite(t_stat):
            p_value = math.erfc(abs(t_stat) / math.sqrt(2))
        cohort = _first_value(row, ["cohort", "group", "g"])
        base_period = _first_value(row, ["base_period", "base"])
        time = _first_value(row, ["time", "t"])
        event = _first_value(row, ["event", "relative_period", "relative_time"])
        if event is not None:
            term = f"event_{event}" if term_prefix == "event" else f"{term_prefix}_event_{event}"
        elif cohort is not None and time is not None:
            if base_period is not None:
                term = f"{term_prefix}_g{cohort}_b{base_period}_t{time}"
            else:
                term = f"{term_prefix}_g{cohort}_t{time}"
        else:
            term = f"{term_prefix}_{pos}"
        rows.append(
            {
                "term": str(term),
                "coef": coef,
                "std_error": se,
                "t_stat": t_stat,
                "p_value": p_value,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "backend": "differences.ATTgt",
            }
        )
    return rows


def _write_frame(path, df: pd.DataFrame) -> None:
    _flatten_columns(df.reset_index()).to_csv(path, index=False, encoding="utf-8-sig")


def _differences_base_period(value: Any) -> str:
    text = str(value or "varying").strip().lower()
    if text in {"varying", "universal"}:
        return text
    return "varying"


def run_cs_did_attgt(ctx: RunContext) -> dict[str, Any]:
    try:
        import differences
    except Exception:
        return missing_dependency(ctx, "differences", "Python Callaway-Sant'Anna ATT(g,t) adapter")

    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    gvar = str(ctx.spec.get("gvar") or ctx.spec.get("adoption_time") or ctx.spec.get("cohort"))
    covars = [str(item) for item in (ctx.spec.get("covariates") or ctx.spec.get("x") or [])]
    cluster = str(ctx.spec.get("cluster")) if ctx.spec.get("cluster") else None
    if not y or not id_col or not time_col or not gvar:
        raise Skill4EconError("cs_did_attgt_py requires y, id, time, and gvar/adoption_time.")
    needed = [y, id_col, time_col, gvar, *covars]
    if cluster and cluster not in needed:
        needed.append(cluster)
    require_columns(df, needed, "Python CS-DID")
    non_gvar_required = [col for col in needed if col != gvar]
    work = df[needed].dropna(subset=non_gvar_required).copy()
    work[gvar] = pd.to_numeric(work[gvar], errors="coerce")
    work.loc[work[gvar] <= 0, gvar] = pd.NA
    if work[gvar].notna().sum() == 0:
        raise Skill4EconError("cs_did_attgt_py requires at least one treated cohort in gvar.")
    formula = y if not covars else f"{y} ~ {' + '.join(covars)}"
    control_group = str(ctx.spec.get("control_group", "never_treated"))
    if control_group not in {"never_treated", "not_yet_treated"}:
        raise Skill4EconError("cs_did_attgt_py control_group must be never_treated or not_yet_treated.")
    base_period = _differences_base_period(
        ctx.spec.get("differences_base_period")
        or ctx.spec.get("attgt_base_period")
        or ctx.spec.get("csdid_base_period")
        or "varying"
    )

    panel = work.set_index([id_col, time_col]).sort_index()
    estimator = differences.ATTgt(
        data=panel,
        cohort_column=gvar,
        base_period=base_period,
        anticipation=int(ctx.spec.get("anticipation", 0)),
    )
    cluster_arg = None if cluster is None or cluster == id_col else cluster
    fit_kwargs = {
        "formula": formula,
        "control_group": control_group,
        "est_method": str(ctx.spec.get("est_method", ctx.spec.get("method", "reg"))),
        "boot_iterations": int(ctx.spec.get("boot_iterations", 0)),
        "random_state": int(ctx.spec.get("random_seed", 20260601)),
        "n_jobs": int(ctx.spec.get("n_jobs", 1)),
        "progress_bar": False,
    }
    if cluster_arg is not None:
        fit_kwargs["cluster_var"] = cluster_arg
    fit = estimator.fit(**fit_kwargs)
    aggregate_kwargs = {
        "boot_iterations": int(ctx.spec.get("boot_iterations", 0)),
        "random_state": int(ctx.spec.get("random_seed", 20260601)),
        "n_jobs": int(ctx.spec.get("n_jobs", 1)),
    }
    if cluster_arg is not None:
        aggregate_kwargs["cluster_var"] = cluster_arg
    simple = estimator.aggregate(
        type_of_aggregation="simple",
        overall=True,
        **aggregate_kwargs,
    )
    event = estimator.aggregate(
        type_of_aggregation="event",
        overall=False,
        **aggregate_kwargs,
    )
    att_gt = fit.to_pandas() if hasattr(fit, "to_pandas") else pd.DataFrame(fit)

    _write_frame(ctx.artifact("att_gt.csv"), pd.DataFrame(att_gt))
    _write_frame(ctx.artifact("simple_att.csv"), pd.DataFrame(simple))
    _write_frame(ctx.artifact("event_study.csv"), pd.DataFrame(event))
    rows = _model_rows_from_frame(pd.DataFrame(simple), term_prefix="ATT")
    rows.extend(_model_rows_from_frame(pd.DataFrame(event), term_prefix="event"))
    rows.extend(_model_rows_from_frame(pd.DataFrame(att_gt), term_prefix="att_gt"))
    write_model_table(ctx, rows)
    pretest_error = None
    try:
        pretest = getattr(estimator, "wald_pre_test", None)
    except Exception as exc:
        pretest = None
        pretest_error = f"{exc.__class__.__name__}: {exc}"
    write_json(
        ctx.artifact("pretrend_test.json"),
        {
            "wald_pre_test": json.loads(json.dumps(pretest, default=str)),
            "role": "diagnostic_only",
            "error": pretest_error,
        },
    )
    messages = ["Python Callaway-Sant'Anna ATT(g,t) adapter completed through differences.ATTgt."]
    if pretest_error:
        messages.append(f"Pretrend diagnostic unavailable from differences.ATTgt: {pretest_error}")
    write_audit(
        ctx,
        "ok",
        messages,
        estimator="differences.ATTgt",
        nobs=int(len(work)),
        n_units=int(work[id_col].nunique()),
        n_periods=int(work[time_col].nunique()),
        control_group=control_group,
        differences_base_period=base_period,
        cluster=cluster,
        cluster_arg=cluster_arg,
    )
    return write_manifest(
        ctx,
        "ok",
        estimator="differences.ATTgt",
        nobs=int(len(work)),
        n_units=int(work[id_col].nunique()),
        n_periods=int(work[time_col].nunique()),
        backend="differences",
        aggregation_method="cohort_time",
        main_estimand="ATT(g,t)",
        control_group=control_group,
        differences_base_period=base_period,
        cluster=cluster,
        cluster_arg=cluster_arg,
    )
