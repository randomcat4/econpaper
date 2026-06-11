from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _panel_contract(contract: dict[str, Any] | None) -> dict[str, Any]:
    panel = (contract or {}).get("panel")
    return panel if isinstance(panel, dict) else {}


def _policy_contract(contract: dict[str, Any] | None) -> dict[str, Any]:
    policy = (contract or {}).get("policy")
    return policy if isinstance(policy, dict) else {}


def _col(spec: dict[str, Any], contract: dict[str, Any] | None, *names: str) -> str:
    panel = _panel_contract(contract)
    aliases = {
        "id": panel.get("unit_id"),
        "time": panel.get("time_id"),
        "y": panel.get("outcome"),
        "treat": panel.get("treatment"),
        "treatment": panel.get("treatment"),
        "gvar": panel.get("first_treat_year"),
        "adoption_time": panel.get("first_treat_year"),
    }
    for name in names:
        value = spec.get(name)
        if value:
            return str(value)
        value = aliases.get(name)
        if value:
            return str(value)
    return ""


def _warn(code: str, severity: str, message: str, action: str = "") -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "action": action,
    }


def _numeric(series: Any):
    import pandas as pd

    return pd.to_numeric(series, errors="coerce")


def _binary_like(values: Any) -> bool:
    observed = {float(v) for v in values.dropna().unique().tolist()}
    return observed.issubset({0.0, 1.0})


def _continuous_treatment(values: Any) -> bool:
    observed = values.dropna().unique()
    if len(observed) <= 2:
        return False
    try:
        return not _binary_like(values)
    except Exception:
        return True


def _treatment_reversal(df: Any, id_col: str, time_col: str, treat_col: str) -> int:
    if not all([id_col, time_col, treat_col]) or any(col not in df.columns for col in [id_col, time_col, treat_col]):
        return 0
    work = df[[id_col, time_col, treat_col]].dropna().copy()
    if work.empty:
        return 0
    work["_time"] = _numeric(work[time_col])
    work["_treat"] = _numeric(work[treat_col])
    reversals = 0
    for _, group in work.sort_values("_time").groupby(id_col):
        ever_seen = False
        for value in group["_treat"].tolist():
            if value == 1:
                ever_seen = True
            elif ever_seen and value == 0:
                reversals += 1
                break
    return int(reversals)


def _cohort_period_support(df: Any, id_col: str, time_col: str, gvar_col: str) -> tuple[dict[str, int], dict[str, int]]:
    if any(col not in df.columns for col in [id_col, time_col, gvar_col]):
        return {}, {}
    import pandas as pd

    work = df[[id_col, time_col, gvar_col]].dropna(subset=[id_col, time_col]).copy()
    work["_time"] = _numeric(work[time_col])
    work["_gvar"] = _numeric(work[gvar_col]).fillna(0)
    treated = work[work["_gvar"] > 0].copy()
    if treated.empty:
        return {}, {}
    per_unit = (
        treated.groupby(id_col, dropna=False)
        .agg(gvar=("_gvar", "min"), min_time=("_time", "min"), max_time=("_time", "max"))
        .reset_index()
    )
    per_unit["pre_periods"] = (per_unit["gvar"] - per_unit["min_time"]).clip(lower=0)
    per_unit["post_periods"] = (per_unit["max_time"] - per_unit["gvar"] + 1).clip(lower=0)
    pre = per_unit.groupby("gvar")["pre_periods"].min().astype(int).to_dict()
    post = per_unit.groupby("gvar")["post_periods"].min().astype(int).to_dict()
    return {str(int(k)): int(v) for k, v in pre.items()}, {str(int(k)): int(v) for k, v in post.items()}


def _default_recommendations(design_type: str, has_never: bool) -> tuple[list[str], list[str]]:
    if design_type == "two_by_two":
        return ["drdid", "twfe"], []
    if design_type == "single_timing":
        return ["drdid", "did_imputation", "event_study_twfe", "twfe"], []
    if design_type == "staggered_adoption":
        preferred = ["cs_did_attgt", "did_imputation", "event_study_twfe", "twfe"]
        if not has_never:
            preferred.insert(1, "cs_did_attgt_not_yet")
        return preferred, ["twfe"]
    if design_type == "continuous_treatment":
        return [], ["twfe", "drdid", "cs_did_attgt"]
    return ["twfe"], []


def _declared_matches_detected(declared: str, detected: str) -> bool:
    declared = declared.strip().lower()
    if not declared:
        return True
    groups = {
        "simple_2x2_did": {"two_by_two", "single_timing"},
        "2x2": {"two_by_two"},
        "two_by_two": {"two_by_two"},
        "staggered_adoption_did": {"staggered_adoption"},
        "staggered_adoption": {"staggered_adoption"},
        "repeated_cross_section": {"repeated_cross_section"},
        "continuous_treatment": {"continuous_treatment"},
    }
    return detected in groups.get(declared, {declared})


def detect_did_design(
    df: Any,
    spec: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import pandas as pd

    id_col = _col(spec, contract, "id")
    time_col = _col(spec, contract, "time")
    y_col = _col(spec, contract, "y")
    treat_col = _col(spec, contract, "treat", "treatment")
    post_col = _col(spec, contract, "post")
    gvar_col = _col(spec, contract, "gvar", "adoption_time", "treat_time")
    declared = str(spec.get("design_type") or "")
    controls = _listify(spec.get("controls") or spec.get("x") or spec.get("covars"))
    policy = _policy_contract(contract)
    anticipation_raw = spec.get("anticipation_periods", policy.get("anticipation_periods", 0))
    try:
        anticipation_periods = int(float(anticipation_raw or 0))
    except (TypeError, ValueError):
        anticipation_periods = 0

    warnings: list[dict[str, Any]] = []
    columns = set(map(str, df.columns))
    missing = [col for col in [time_col, y_col] if col and col not in columns]
    if id_col and id_col not in columns and str(spec.get("data_type", "")).lower() != "repeated_cross_section":
        missing.append(id_col)
    if missing:
        warnings.append(
            _warn(
                "DATA_CONTRACT_FAILED",
                "red",
                f"DID design detector is missing required columns: {sorted(set(missing))}.",
                "Fix the data/spec/contract columns before using DID routing.",
            )
        )

    n_units = int(df[id_col].nunique(dropna=True)) if id_col in columns else None
    n_periods = int(df[time_col].nunique(dropna=True)) if time_col in columns else None
    id_time_duplicates = int(df.duplicated([id_col, time_col]).sum()) if id_col in columns and time_col in columns else 0
    observed_cells = int(df[[id_col, time_col]].drop_duplicates().shape[0]) if id_col in columns and time_col in columns else int(len(df))
    possible_cells = int((n_units or 0) * (n_periods or 0)) if n_units and n_periods else None
    panel_balance_ratio = float(observed_cells / possible_cells) if possible_cells else None

    repeated_cross_section = (
        str(spec.get("data_type", "")).lower() in {"repeated_cross_section", "rc"}
        or not id_col
        or id_col not in columns
    )
    if id_time_duplicates and not repeated_cross_section:
        warnings.append(
            _warn(
                "DATA_CONTRACT_ID_TIME_NOT_UNIQUE",
                "red",
                f"{id_time_duplicates} duplicated id-time cells were found.",
                "Resolve duplicate panel cells or declare repeated_cross_section only when appropriate.",
            )
        )
    if panel_balance_ratio is not None and panel_balance_ratio < float(spec.get("panel_balance_threshold", 0.8)):
        warnings.append(
            _warn(
                "UNBALANCED_PANEL_HIGH_LOSS",
                "yellow",
                f"Only {panel_balance_ratio:.3f} of possible unit-period cells are observed.",
                "Report sample construction and check attrition/missing panel cells.",
            )
        )
    if id_col in columns and time_col in columns:
        entity_periods = df.groupby(id_col, dropna=False)[time_col].nunique()
        if len(entity_periods) and int(entity_periods.max()) > 0:
            min_max_ratio = float(entity_periods.min() / entity_periods.max())
            if min_max_ratio < float(spec.get("entity_period_balance_threshold", 0.8)):
                warnings.append(
                    _warn(
                        "UNBALANCED_PANEL_HIGH_LOSS",
                        "yellow",
                        f"Some units have much shorter time support; min/max periods ratio is {min_max_ratio:.3f}.",
                        "Report sample construction and check unit-level attrition.",
                    )
                )
    if anticipation_periods > 0:
        warnings.append(
            _warn(
                "ANTICIPATION_RISK",
                "yellow",
                f"The spec/contract declares {anticipation_periods} anticipation period(s).",
                "Exclude anticipation windows or report event-study leads before interpreting post-treatment effects.",
            )
        )

    design_type = "unknown"
    first_treat_years: list[int] = []
    n_treated_units = 0
    n_never_treated = 0
    has_not_yet = False
    min_pre_by_cohort: dict[str, int] = {}
    min_post_by_cohort: dict[str, int] = {}

    if repeated_cross_section:
        design_type = "repeated_cross_section"

    if treat_col and treat_col in columns and _continuous_treatment(df[treat_col]):
        design_type = "continuous_treatment"
        warnings.append(
            _warn(
                "CONTINUOUS_TREATMENT_NOT_SUPPORTED",
                "yellow",
                f"`{treat_col}` is not binary; DID PaperRun records this as continuous treatment only.",
                "Use a continuous-treatment DID design or discretize explicitly before using binary DID estimators.",
            )
        )

    if design_type not in {"continuous_treatment", "repeated_cross_section"} and gvar_col and gvar_col in columns:
        gvar = _numeric(df[gvar_col]).fillna(0)
        first_treat_years = sorted(int(v) for v in gvar[gvar > 0].dropna().unique().tolist())
        n_treated_cohorts = len(first_treat_years)
        if id_col in columns:
            unit_g = df[[id_col, gvar_col]].copy()
            unit_g["_gvar"] = _numeric(unit_g[gvar_col]).fillna(0)
            by_unit = unit_g.groupby(id_col)["_gvar"].max()
            n_treated_units = int((by_unit > 0).sum())
            n_never_treated = int((by_unit <= 0).sum())
        else:
            n_treated_units = int((gvar > 0).sum())
            n_never_treated = int((gvar <= 0).sum())
        if n_treated_cohorts > 1:
            design_type = "staggered_adoption"
        elif n_treated_cohorts == 1:
            design_type = "single_timing"
        min_pre_by_cohort, min_post_by_cohort = _cohort_period_support(df, id_col, time_col, gvar_col) if id_col and time_col else ({}, {})
        if time_col in columns:
            times = set(_numeric(df[time_col]).dropna().astype(int).tolist())
            has_not_yet = any(any(period < g for period in times) for g in first_treat_years)
    elif design_type not in {"continuous_treatment", "repeated_cross_section"} and treat_col in columns and post_col in columns:
        treat = _numeric(df[treat_col])
        post = _numeric(df[post_col])
        treated_mask = treat == 1
        if id_col in columns:
            work = df[[id_col, treat_col]].copy()
            work["_treat"] = _numeric(work[treat_col]).fillna(0)
            by_unit = work.groupby(id_col)["_treat"].max()
            n_treated_units = int((by_unit > 0).sum())
            n_never_treated = int((by_unit <= 0).sum())
        else:
            n_treated_units = int(treated_mask.sum())
            n_never_treated = int((treat != 1).sum())
        post_times = _numeric(df.loc[post == 1, time_col]).dropna().unique().tolist() if time_col in columns else []
        if post_times:
            first_treat_years = [int(min(post_times))]
        design_type = "two_by_two" if n_periods == 2 else "single_timing"
        if first_treat_years and time_col in columns:
            pre_periods = int(df.loc[post == 0, time_col].nunique(dropna=True))
            post_periods = int(df.loc[post == 1, time_col].nunique(dropna=True))
            min_pre_by_cohort = {str(first_treat_years[0]): pre_periods}
            min_post_by_cohort = {str(first_treat_years[0]): post_periods}
        else:
            min_pre_by_cohort = {}
            min_post_by_cohort = {}

    if not first_treat_years and design_type == "unknown":
        warnings.append(
            _warn(
                "DATA_CONTRACT_FAILED",
                "red",
                "No DID timing fields were usable for design detection.",
                "Provide treat/post for simple DID or gvar/adoption_time for staggered DID.",
            )
        )

    if declared and not _declared_matches_detected(declared, design_type):
        warnings.append(
            _warn(
                "DID_DESIGN_DECLARATION_MISMATCH",
                "yellow",
                f"Declared design_type `{declared}` differs from detected `{design_type}`.",
                "Confirm the spec before interpreting estimator routing.",
            )
        )

    if n_never_treated == 0 and design_type in {"staggered_adoption", "single_timing"}:
        warnings.append(
            _warn(
                "NO_NEVER_TREATED",
                "yellow",
                "No never-treated units were detected.",
                "Use estimators/control options that support not-yet-treated comparisons and report the control group.",
            )
        )
    n_cohorts = len(first_treat_years)
    if design_type == "staggered_adoption" and n_cohorts < int(spec.get("min_treated_cohorts", 3)):
        warnings.append(
            _warn(
                "FEW_TREATED_COHORTS",
                "yellow",
                f"Only {n_cohorts} treated cohorts were detected.",
                "Avoid overclaiming staggered heterogeneity evidence with very few cohorts.",
            )
        )
    weak_pre = {cohort: periods for cohort, periods in min_pre_by_cohort.items() if periods < int(spec.get("min_pre_periods", 3))}
    if weak_pre:
        warnings.append(
            _warn(
                "WEAK_PRETREND_PERIODS",
                "yellow",
                f"Cohorts with fewer than 3 pre-periods: {weak_pre}.",
                "Use a wider pre-period window or weaken pretrend claims.",
            )
        )
    short_post = {cohort: periods for cohort, periods in min_post_by_cohort.items() if periods < int(spec.get("min_post_periods", 2))}
    if short_post:
        warnings.append(
            _warn(
                "POST_PERIOD_TOO_SHORT",
                "yellow",
                f"Cohorts with short post-period support: {short_post}.",
                "Report limited post-treatment support and avoid long-run claims.",
            )
        )
    reversals = _treatment_reversal(df, id_col, time_col, treat_col)
    if reversals:
        warnings.append(
            _warn(
                "TREATMENT_REVERSAL",
                "yellow",
                f"{reversals} units appear to switch from treated back to untreated.",
                "Use a non-absorbing treatment design or fix treatment coding before staggered DID.",
            )
        )

    has_never = bool(n_never_treated)
    recommended, not_main = _default_recommendations(design_type, has_never)
    return {
        "declared_design_type": declared or None,
        "design_type": design_type,
        "data_type": "repeated_cross_section" if repeated_cross_section else "panel",
        "id": id_col or None,
        "time": time_col or None,
        "outcome": y_col or None,
        "treatment": treat_col or None,
        "post": post_col or None,
        "gvar": gvar_col or None,
        "controls": controls,
        "n_units": n_units,
        "n_periods": n_periods,
        "n_treated_units": n_treated_units,
        "n_never_treated_units": n_never_treated,
        "n_treated_cohorts": len(first_treat_years),
        "first_treat_years": first_treat_years,
        "has_never_treated": has_never,
        "all_treated": bool(n_treated_units and n_never_treated == 0),
        "has_not_yet_treated": bool(has_not_yet),
        "min_pre_periods_by_cohort": min_pre_by_cohort,
        "min_post_periods_by_cohort": min_post_by_cohort,
        "id_time_duplicates": id_time_duplicates,
        "panel_balance_ratio": panel_balance_ratio,
        "treatment_reversal_units": reversals,
        "recommended_estimators": recommended,
        "not_recommended_as_main": not_main,
        "reviewer_warnings": warnings,
    }


def write_did_design(path: Path, design: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(design, ensure_ascii=False, indent=2), encoding="utf-8")
