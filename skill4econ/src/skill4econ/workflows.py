from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import shlex
from pathlib import Path
from typing import Any

from .core import (
    RunContext,
    Skill4EconError,
    dependency_report,
    file_sha256,
    listify,
    read_table,
    write_audit,
    write_json,
    write_manifest,
    write_text,
)
from .contracts.data_contract import (
    load_data_contract,
    validate_data_contract,
    write_contract_errors,
    write_validated_contract,
)
from .contracts.estimator_registry import route_did_estimators, write_estimator_routing
from .diagnostics.did_design import detect_did_design, write_did_design
from .adapters.did_common import build_common_output, write_common_output
from .python_wrappers import PYTHON_METHODS, _ols_numpy
from .reporting.did_comparison import build_did_estimator_comparison
from .stata_wrappers import STATA_METHODS


WorkflowResult = dict[str, Any]


def _json_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["note"]
        rows = [{"note": ""}]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _configured_placebo_tests(spec: dict[str, Any]) -> list[dict[str, str]]:
    raw = spec.get("placebo_tests") or spec.get("placebo_checks") or []
    if isinstance(raw, (str, dict)):
        raw = [raw]
    rows: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return rows
    for index, item in enumerate(raw, 1):
        if isinstance(item, str):
            post_col = item.strip()
            name = post_col
            treat_col = "_s4e_treat"
        elif isinstance(item, dict):
            post_col = str(
                item.get("post")
                or item.get("post_column")
                or item.get("placebo_post")
                or item.get("placebo_post_column")
                or ""
            ).strip()
            treat_col = str(item.get("treat") or item.get("treat_column") or "_s4e_treat").strip()
            name = str(item.get("name") or item.get("label") or post_col or f"placebo_{index}").strip()
        else:
            continue
        rows.append(
            {
                "name": name or f"placebo_{index}",
                "post_col": post_col,
                "treat_col": treat_col or "_s4e_treat",
            }
        )
    return rows


def _configured_heterogeneity_dimensions(spec: dict[str, Any]) -> list[str]:
    raw = spec.get("heterogeneity_dimensions") or spec.get("heterogeneity_groups") or []
    if not raw and isinstance(spec.get("heterogeneity"), dict):
        raw = spec["heterogeneity"].get("dimensions") or spec["heterogeneity"].get("groups") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    dimensions: list[str] = []
    for item in raw:
        if isinstance(item, str):
            column = item.strip()
        elif isinstance(item, dict):
            column = str(item.get("dimension") or item.get("column") or item.get("name") or "").strip()
        else:
            column = ""
        if column and column not in dimensions:
            dimensions.append(column)
    return dimensions


def _variable_units(spec: dict[str, Any], y: str) -> dict[str, str]:
    raw = spec.get("variable_units") or spec.get("units") or {}
    units: dict[str, str] = {}
    if isinstance(raw, dict):
        units.update({str(key): str(value) for key, value in raw.items() if value is not None})
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            variable = str(item.get("variable") or item.get("name") or "").strip()
            unit = str(item.get("unit") or item.get("units") or "").strip()
            if variable and unit:
                units[variable] = unit
    outcome_unit = str(spec.get("outcome_unit") or spec.get("y_unit") or "").strip()
    if y and outcome_unit:
        units.setdefault(y, outcome_unit)
    return units


def _warning(severity: str, code: str, message: str, *, action: str = "") -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "action": action,
    }


def _has_red(warnings: list[dict[str, Any]]) -> bool:
    return any(item.get("severity") == "red" for item in warnings)


def _normalize_policy(spec: dict[str, Any]) -> str:
    value = (
        spec.get("engine_policy")
        or spec.get("engine_preference")
        or spec.get("requested_engine")
        or "stata_first"
    )
    policy = str(value).lower()
    if policy not in {"stata_first", "stata", "python"}:
        raise Skill4EconError("engine_policy must be one of: stata_first, stata, python.")
    return policy


def _time_as_numeric(series: Any):
    import pandas as pd

    return pd.to_numeric(series, errors="coerce")


def _safe_ratio(numer: int, denom: int) -> float | None:
    if denom == 0:
        return None
    return float(numer / denom)


def _parse_event_term(term: str) -> int | None:
    token = term.strip()
    for prefix in ("_event_", "event_"):
        if token.startswith(prefix):
            token = token[len(prefix) :]
            break
    else:
        return None
    if token.startswith("m") and token[1:].isdigit():
        return -int(token[1:])
    try:
        return int(token)
    except ValueError:
        return None


def _write_event_plot(ctx: RunContext, event_rows: list[dict[str, Any]]) -> str | None:
    points = []
    for row in event_rows:
        event_time = _parse_event_term(str(row.get("term", "")))
        if event_time is None:
            continue
        try:
            coef = float(row.get("coef", "nan"))
            se = float(row.get("std_error", "nan"))
        except (TypeError, ValueError):
            continue
        if math.isnan(coef):
            continue
        points.append({"event_time": event_time, "coef": coef, "std_error": se})
    if not points:
        return None
    points.sort(key=lambda item: item["event_time"])
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    x = [item["event_time"] for item in points]
    y = [item["coef"] for item in points]
    yerr = [
        1.96 * item["std_error"]
        if not math.isnan(item["std_error"])
        else 0.0
        for item in points
    ]
    path = ctx.artifact("event_study_plot.png")
    plt.figure(figsize=(7, 4.2))
    plt.axhline(0, color="#666666", linewidth=1)
    plt.axvline(-0.5, color="#999999", linewidth=1, linestyle="--")
    plt.errorbar(x, y, yerr=yerr, marker="o", capsize=3, color="#1f77b4")
    plt.xlabel("Event time")
    plt.ylabel("Coefficient")
    plt.title("DID event-study estimates")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return str(path)


def _prepare_did_inputs(ctx: RunContext) -> dict[str, Any]:
    import pandas as pd

    spec = dict(ctx.spec)
    warnings: list[dict[str, Any]] = []
    df, data_path = read_table(spec)
    design_type = str(spec.get("design_type", "")).strip().lower()
    if not design_type:
        warnings.append(
            _warning(
                "red",
                "missing_design_type",
                "DID PaperRun requires design_type: simple_2x2_did or staggered_adoption_did.",
                action="Add design_type to the spec instead of asking the workflow to infer the research design.",
            )
        )
    elif design_type not in {"simple_2x2_did", "staggered_adoption_did"}:
        warnings.append(
            _warning(
                "red",
                "invalid_design_type",
                f"Unsupported design_type: {design_type}.",
                action="Use simple_2x2_did or staggered_adoption_did.",
            )
        )

    id_col = str(spec.get("id") or "")
    time_col = str(spec.get("time") or "")
    y = str(spec.get("y") or "")
    controls = listify(spec.get("controls") or spec.get("x") or spec.get("covars"))
    cluster = str(spec.get("cluster") or id_col or "")
    configured_placebos = _configured_placebo_tests(spec)
    configured_heterogeneity = _configured_heterogeneity_dimensions(spec)
    engine_policy = _normalize_policy(spec)
    window_raw = spec.get("event_window", spec.get("window", [-5, 5]))
    if not isinstance(window_raw, list | tuple) or len(window_raw) != 2:
        raise Skill4EconError("event_window/window must be a two-item list, such as [-5, 5].")
    event_window = [int(window_raw[0]), int(window_raw[1])]
    base_period = int(spec.get("base_period", -1))
    if event_window[0] > event_window[1]:
        raise Skill4EconError("event_window lower bound must be <= upper bound.")

    required_columns = [id_col, time_col, y, *controls]
    if cluster:
        required_columns.append(cluster)
    treat_col = str(spec.get("treat") or "")
    post_col = str(spec.get("post") or "")
    gvar_col = str(spec.get("gvar") or spec.get("adoption_time") or spec.get("treat_time") or "")
    if design_type == "simple_2x2_did":
        required_columns.extend([treat_col, post_col])
        if not treat_col or not post_col:
            warnings.append(
                _warning(
                    "red",
                    "missing_simple_did_fields",
                    "simple_2x2_did requires treat and post columns in v0.1.",
                    action="Provide both treat and post; treat_post alone is not enough for PaperRun diagnostics.",
                )
            )
    elif design_type == "staggered_adoption_did":
        required_columns.append(gvar_col)
        if not gvar_col:
            warnings.append(
                _warning(
                    "red",
                    "missing_gvar",
                    "staggered_adoption_did requires gvar/adoption_time.",
                    action="Provide the first treated period per entity, with 0 or missing for never-treated units.",
                )
            )
    missing_names = [
        name
        for name in {col for col in required_columns if col}
        if name not in df.columns
    ]
    diagnostic_columns: list[str] = []
    for placebo in configured_placebos:
        post_name = placebo.get("post_col", "")
        treat_name = placebo.get("treat_col", "")
        if not post_name:
            warnings.append(
                _warning(
                    "yellow",
                    "placebo_test_missing_post_column",
                    f"Configured placebo test `{placebo.get('name')}` does not declare a placebo post column.",
                    action="Add post/post_column to the placebo_tests entry.",
                )
            )
        else:
            diagnostic_columns.append(post_name)
        if treat_name and not treat_name.startswith("_s4e_"):
            diagnostic_columns.append(treat_name)
    diagnostic_columns.extend(configured_heterogeneity)
    missing_diagnostic_columns = sorted(
        {
            col
            for col in diagnostic_columns
            if col and col not in df.columns
        }
    )
    if missing_diagnostic_columns:
        warnings.append(
            _warning(
                "yellow",
                "configured_diagnostic_columns_missing",
                f"Configured optional DID diagnostic columns are missing: {missing_diagnostic_columns}.",
                action="Fix these columns to generate placebo/heterogeneity artifacts; the main DID run is unchanged.",
            )
        )
    if not id_col or not time_col or not y:
        warnings.append(
            _warning(
                "red",
                "missing_core_fields",
                "Spec must provide id, time, and y.",
                action="Add id/time/y to the workflow spec.",
            )
        )
    if missing_names:
        warnings.append(
            _warning(
                "red",
                "missing_columns",
                f"Input data is missing required columns: {missing_names}.",
                action="Fix the data columns or update the spec.",
            )
        )

    data_summary: dict[str, Any] = {
        "data_path": str(data_path),
        "data_sha256": file_sha256(data_path),
        "rows_raw": int(len(df)),
        "columns": list(map(str, df.columns)),
        "design_type": design_type,
        "engine_policy": engine_policy,
        "configured_placebo_tests": configured_placebos,
        "configured_heterogeneity_dimensions": configured_heterogeneity,
    }
    contract_payload = _load_optional_data_contract_payload(ctx)
    did_design = detect_did_design(df, spec, contract_payload)
    write_did_design(ctx.artifact("did_design.json"), did_design)
    data_summary["detected_did_design"] = did_design.get("design_type")
    for item in did_design.get("reviewer_warnings") or []:
        warnings.append(
            _warning(
                str(item.get("severity") or "yellow"),
                str(item.get("code") or "did_design_warning"),
                str(item.get("message") or "DID design detector emitted a warning."),
                action=str(item.get("action") or "Inspect did_design.json."),
            )
        )
    warnings.extend(_validate_optional_data_contract(ctx, df))
    treatment_rows: list[dict[str, Any]] = []
    event_support_rows: list[dict[str, Any]] = []
    sample_construction: dict[str, Any] = {
        "rows_raw": int(len(df)),
        "data_path": str(data_path),
        "model_samples": {},
    }

    if _has_red(warnings):
        _write_preflight_artifacts(
            ctx,
            data_summary,
            treatment_rows,
            event_support_rows,
            sample_construction,
            warnings,
        )
        return {
            "can_run": False,
            "warnings": warnings,
            "data_summary": data_summary,
            "design_type": design_type,
            "did_design": did_design,
            "engine_policy": engine_policy,
        }

    duplicates = df.duplicated([id_col, time_col], keep=False)
    dup_count = int(duplicates.sum())
    data_summary["id_time_duplicates"] = dup_count
    if dup_count:
        df.loc[duplicates, [id_col, time_col]].head(100).to_csv(
            ctx.artifact("duplicate_id_time_rows.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        warnings.append(
            _warning(
                "red",
                "id_time_not_unique",
                f"{dup_count} rows belong to duplicated id-time cells.",
                action="Resolve duplicate panel cells before estimating DID models.",
            )
        )

    entity_counts = df.groupby(id_col, dropna=False)[time_col].nunique()
    data_summary.update(
        {
            "entities": int(df[id_col].nunique(dropna=True)),
            "periods": int(df[time_col].nunique(dropna=True)),
            "min_periods_per_entity": int(entity_counts.min()) if len(entity_counts) else 0,
            "max_periods_per_entity": int(entity_counts.max()) if len(entity_counts) else 0,
            "balanced_panel": bool(entity_counts.nunique() == 1),
        }
    )
    if entity_counts.nunique() > 1:
        warnings.append(
            _warning(
                "yellow",
                "unbalanced_panel",
                "Panel is not balanced across entities.",
                action="Check whether missing entity-year cells are expected and report the sample rule.",
            )
        )

    analysis = df.copy()
    time_num = _time_as_numeric(analysis[time_col])
    if time_num.isna().all():
        warnings.append(
            _warning(
                "red",
                "non_numeric_time",
                "time could not be converted to numeric values for event-time construction.",
                action="Use a numeric year/period variable or pre-compute event_time.",
            )
        )
    analysis["_s4e_time_numeric"] = time_num

    if design_type == "simple_2x2_did":
        analysis["_s4e_treat"] = pd.to_numeric(analysis[treat_col], errors="coerce")
        analysis["_s4e_post"] = pd.to_numeric(analysis[post_col], errors="coerce")
        treat_values = set(analysis["_s4e_treat"].dropna().unique().tolist())
        post_values = set(analysis["_s4e_post"].dropna().unique().tolist())
        if len(treat_values) < 2:
            warnings.append(
                _warning("red", "treatment_has_no_variation", "treat has no usable treated/control variation.")
            )
        if len(post_values) < 2:
            warnings.append(
                _warning("red", "post_has_no_variation", "post has no usable pre/post variation.")
            )
        if not {0, 1}.issuperset(treat_values):
            warnings.append(
                _warning("yellow", "nonbinary_treat", "treat contains values outside {0, 1}.")
            )
        if not {0, 1}.issuperset(post_values):
            warnings.append(
                _warning("yellow", "nonbinary_post", "post contains values outside {0, 1}.")
            )
        first_post = analysis.loc[analysis["_s4e_post"] == 1, "_s4e_time_numeric"].min()
        if pd.isna(first_post):
            warnings.append(
                _warning("red", "no_post_period", "No post-treatment period exists in the current sample.")
            )
            first_post = math.nan
        analysis["_s4e_event_time"] = pd.NA
        treated_mask = analysis["_s4e_treat"] == 1
        if not pd.isna(first_post):
            analysis.loc[treated_mask, "_s4e_event_time"] = (
                analysis.loc[treated_mask, "_s4e_time_numeric"] - first_post
            )
        analysis["_s4e_gvar"] = 0
        if not pd.isna(first_post):
            analysis.loc[treated_mask, "_s4e_gvar"] = int(first_post)
        treatment_rows.extend(
            [
                {"metric": "treated_entities", "value": int(analysis.loc[treated_mask, id_col].nunique())},
                {"metric": "control_entities", "value": int(analysis.loc[~treated_mask, id_col].nunique())},
                {"metric": "pre_rows", "value": int((analysis["_s4e_post"] == 0).sum())},
                {"metric": "post_rows", "value": int((analysis["_s4e_post"] == 1).sum())},
            ]
        )
    else:
        gvar_num = pd.to_numeric(analysis[gvar_col], errors="coerce").fillna(0)
        analysis["_s4e_gvar"] = gvar_num
        treated_mask = gvar_num > 0
        analysis["_s4e_treat"] = treated_mask.astype(int)
        analysis["_s4e_post"] = ((treated_mask) & (time_num >= gvar_num)).astype(int)
        analysis["_s4e_event_time"] = pd.NA
        analysis.loc[treated_mask, "_s4e_event_time"] = time_num.loc[treated_mask] - gvar_num.loc[treated_mask]
        never_entities = analysis.loc[~treated_mask, id_col].nunique()
        treated_entities = analysis.loc[treated_mask, id_col].nunique()
        cohorts = (
            analysis.loc[treated_mask, [id_col, "_s4e_gvar"]]
            .drop_duplicates()
            .groupby("_s4e_gvar")[id_col]
            .nunique()
            .sort_index()
        )
        pre_treated_rows = int(((treated_mask) & (time_num < gvar_num)).sum())
        already_treated_entities = int(
            analysis.loc[treated_mask]
            .groupby(id_col)
            .apply(lambda frame: bool((frame["_s4e_time_numeric"] >= frame["_s4e_gvar"]).all()))
            .sum()
        )
        if treated_entities == 0:
            warnings.append(_warning("red", "no_treated_entities", "No treated entities were found."))
        if pre_treated_rows == 0:
            warnings.append(
                _warning(
                    "red",
                    "no_pre_period",
                    "No treated observations have a pre-treatment period.",
                    action="Extend the sample window or fix adoption_time/gvar.",
                )
            )
        if never_entities == 0:
            warnings.append(
                _warning(
                    "yellow",
                    "no_never_treated",
                    "No never-treated entities were found; identification may rely on not-yet-treated comparisons.",
                )
            )
        if len(cohorts) < 2:
            warnings.append(
                _warning(
                    "yellow",
                    "few_treated_cohorts",
                    "Fewer than two treated cohorts were found for staggered adoption DID.",
                )
            )
        treatment_rows.extend(
            [
                {"metric": "treated_entities", "value": int(treated_entities)},
                {"metric": "never_treated_entities", "value": int(never_entities)},
                {"metric": "already_treated_entities", "value": already_treated_entities},
                {"metric": "treated_cohort_count", "value": int(len(cohorts))},
                {"metric": "pre_treated_rows", "value": pre_treated_rows},
            ]
        )
        for cohort, count in cohorts.items():
            treatment_rows.append({"metric": "cohort_entities", "cohort": cohort, "value": int(count)})
        warnings.append(
            _warning(
                "yellow",
                "twfe_staggered_heterogeneity",
                "TWFE is being used with staggered adoption and may be sensitive to heterogeneous treatment effects.",
                action="Use csdid/drdid or another staggered DID alternative before treating the run as paper-ready.",
            )
        )

    cluster_count = int(analysis[cluster].nunique(dropna=True)) if cluster else 0
    data_summary["cluster"] = cluster
    data_summary["cluster_count"] = cluster_count
    if cluster_count and cluster_count < int(spec.get("min_clusters", 30)):
        warnings.append(
            _warning(
                "yellow",
                "few_clusters",
                f"Only {cluster_count} clusters were found.",
                action="Cluster-robust standard errors may be optimistic with few clusters.",
            )
        )

    sample_cols = [id_col, time_col, y, "_s4e_treat", "_s4e_post", *controls]
    if cluster:
        sample_cols.append(cluster)
    sample_cols = [col for col in dict.fromkeys(sample_cols) if col in analysis.columns]
    rows_after = int(analysis[sample_cols].dropna().shape[0])
    rows_dropped = int(len(analysis) - rows_after)
    sample_construction.update(
        {
            "rows_after_did_listwise": rows_after,
            "rows_dropped_did_listwise": rows_dropped,
            "drop_ratio_did_listwise": _safe_ratio(rows_dropped, int(len(analysis))),
            "missing_by_required_column": {
                col: int(analysis[col].isna().sum())
                for col in sample_cols
            },
        }
    )
    event_sample_cols = [id_col, time_col, y, *controls]
    if cluster:
        event_sample_cols.append(cluster)
    event_sample_cols = [col for col in dict.fromkeys(event_sample_cols) if col in analysis.columns]
    csdid_sample_cols = [id_col, time_col, y, "_s4e_gvar", *controls]
    if cluster:
        csdid_sample_cols.append(cluster)
    csdid_sample_cols = [col for col in dict.fromkeys(csdid_sample_cols) if col in analysis.columns]
    sample_construction["model_samples"] = {
        "baseline_twfe": {
            "required_columns": sample_cols,
            "rows_after_dropna": rows_after,
        },
        "event_study": {
            "required_columns": event_sample_cols,
            "rows_after_dropna": int(analysis[event_sample_cols].dropna().shape[0]),
            "event_time_missing_rows_kept_as_controls": int(analysis["_s4e_event_time"].isna().sum()),
        },
        "csdid_staggered": {
            "required_columns": csdid_sample_cols,
            "rows_after_dropna": int(analysis[csdid_sample_cols].dropna().shape[0]),
            "applicable": bool(design_type == "staggered_adoption_did"),
        },
    }
    if rows_dropped / max(len(analysis), 1) > float(spec.get("large_drop_ratio", 0.2)):
        warnings.append(
            _warning(
                "yellow",
                "large_listwise_deletion",
                f"{rows_dropped} of {len(analysis)} rows would be dropped by listwise deletion.",
                action="Inspect sample_construction.json before interpreting model differences.",
            )
        )

    rank_terms = ["_s4e_treat", "_s4e_post"]
    if design_type == "simple_2x2_did":
        analysis["_s4e_treat_post"] = analysis["_s4e_treat"] * analysis["_s4e_post"]
        rank_terms.append("_s4e_treat_post")
    rank_terms.extend([str(col) for col in controls if col in analysis.columns])
    rank_frame = analysis[rank_terms].apply(pd.to_numeric, errors="coerce").dropna() if rank_terms else None
    if rank_frame is not None and not rank_frame.empty:
        import numpy as np

        x_matrix = np.column_stack([np.ones(len(rank_frame)), rank_frame.to_numpy(dtype=float)])
        rank = int(np.linalg.matrix_rank(x_matrix))
        columns = int(x_matrix.shape[1])
        data_summary["did_design_matrix_rank"] = rank
        data_summary["did_design_matrix_columns"] = columns
        if rank < columns:
            warnings.append(
                _warning(
                    "red",
                    "rank_deficient_design",
                    f"DID design matrix is rank deficient before estimation: rank={rank}, columns={columns}.",
                    action="Remove collinear controls or unsupported dummy terms before running DID.",
                )
            )

    lo, hi = event_window
    for k in range(lo, hi + 1):
        mask = treated_mask & (analysis["_s4e_event_time"] == k)
        support = analysis.loc[mask]
        event_support_rows.append(
            {
                "event_time": k,
                "is_base_period": bool(k == base_period),
                "treated_observations": int(mask.sum()),
                "treated_entities": int(support[id_col].nunique()) if len(support) else 0,
                "calendar_periods": int(support[time_col].nunique()) if len(support) else 0,
                "present_in_model_table": False,
            }
        )
    lead_count = sum(
        1
        for row in event_support_rows
        if row["event_time"] < 0
        and not row["is_base_period"]
        and row["treated_observations"] > 0
    )
    if lead_count < 2:
        warnings.append(
            _warning(
                "yellow",
                "few_pre_treatment_leads",
                "Fewer than two supported pre-treatment leads are available in the event window.",
            )
        )

    analysis_path = ctx.artifact("analysis_data.csv")
    analysis.to_csv(analysis_path, index=False, encoding="utf-8-sig")
    data_summary["analysis_data"] = str(analysis_path)
    summary_path = _write_summary_stats(
        ctx,
        analysis,
        [y, "_s4e_treat", "_s4e_post", *controls],
        variable_units=_variable_units(spec, y),
    )
    cohort_path = _write_cohort_table(ctx, did_design, analysis, id_col=id_col)
    if summary_path:
        data_summary["summary_stats"] = summary_path
    if cohort_path:
        data_summary["cohort_table"] = cohort_path
    _write_preflight_artifacts(
        ctx,
        data_summary,
        treatment_rows,
        event_support_rows,
        sample_construction,
        warnings,
    )
    return {
        "can_run": not _has_red(warnings),
        "warnings": warnings,
        "data_summary": data_summary,
        "treatment_rows": treatment_rows,
        "event_support_rows": event_support_rows,
        "sample_construction": sample_construction,
        "analysis_data": analysis_path,
        "design_type": design_type,
        "did_design": did_design,
        "engine_policy": engine_policy,
        "id": id_col,
        "time": time_col,
        "y": y,
        "controls": controls,
        "cluster": cluster,
        "event_window": event_window,
        "base_period": base_period,
        "configured_placebo_tests": configured_placebos,
        "configured_heterogeneity_dimensions": configured_heterogeneity,
    }


def _write_preflight_artifacts(
    ctx: RunContext,
    data_summary: dict[str, Any],
    treatment_rows: list[dict[str, Any]],
    event_support_rows: list[dict[str, Any]],
    sample_construction: dict[str, Any],
    warnings: list[dict[str, Any]],
) -> None:
    write_json(ctx.artifact("data_summary.json"), data_summary)
    _write_csv(
        ctx.artifact("data_summary.csv"),
        [{"metric": key, "value": value} for key, value in data_summary.items() if key != "columns"],
    )
    _write_csv(ctx.artifact("treatment_timing_summary.csv"), treatment_rows)
    _write_csv(ctx.artifact("event_study_support.csv"), event_support_rows)
    write_json(ctx.artifact("sample_construction.json"), sample_construction)
    write_json(ctx.artifact("warnings.json"), {"warnings": warnings})
    write_json(ctx.artifact("did_diagnostics.json"), {"warnings": warnings})


def _step_ctx(ctx: RunContext, engine: str, method: str, seq: int, spec: dict[str, Any]) -> RunContext:
    return RunContext(
        method=method,
        engine=engine,
        state="run",
        spec=spec,
        run_dir=ctx.run_dir / "steps" / f"{seq:02d}_{engine}_{method}",
    )


def _run_step(ctx: RunContext, engine: str, method: str, seq: int, spec: dict[str, Any]) -> dict[str, Any]:
    handlers = PYTHON_METHODS if engine == "python" else STATA_METHODS
    handler = handlers.get(method)
    step = _step_ctx(ctx, engine, method, seq, spec)
    step.run_dir.mkdir(parents=True, exist_ok=True)
    if handler is None:
        write_audit(step, "failed", [f"Unknown {engine} method: {method}"])
        manifest = write_manifest(step, "failed", error=f"Unknown {engine} method: {method}")
    else:
        try:
            manifest = handler(step)
        except Exception as exc:
            write_audit(step, "failed", [str(exc)], error_type=exc.__class__.__name__)
            manifest = write_manifest(step, "failed", error=str(exc), error_type=exc.__class__.__name__)
    return {
        "seq": seq,
        "engine": engine,
        "method": method,
        "status": manifest.get("status"),
        "run_dir": str(step.run_dir),
        "manifest": manifest,
    }


def _engines_for_policy(policy: str) -> list[str]:
    if policy == "python":
        return ["python"]
    if policy == "stata":
        return ["stata"]
    return ["stata", "python"]


def _base_model_spec(ctx: RunContext, prepared: dict[str, Any]) -> dict[str, Any]:
    spec = dict(ctx.spec)
    spec.update(
        {
            "data": str(prepared["analysis_data"]),
            "id": prepared["id"],
            "time": prepared["time"],
            "y": prepared["y"],
            "x": prepared["controls"],
            "treat": "_s4e_treat",
            "post": "_s4e_post",
            "cluster": prepared["cluster"],
            "output_dir": str(ctx.run_dir / "steps"),
        }
    )
    return spec


def _event_model_spec(ctx: RunContext, prepared: dict[str, Any]) -> dict[str, Any]:
    spec = dict(ctx.spec)
    spec.update(
        {
            "data": str(prepared["analysis_data"]),
            "id": prepared["id"],
            "time": prepared["time"],
            "y": prepared["y"],
            "x": prepared["controls"],
            "event_time": "_s4e_event_time",
            "cluster": prepared["cluster"],
            "window": prepared["event_window"],
            "base_period": prepared["base_period"],
            "output_dir": str(ctx.run_dir / "steps"),
        }
    )
    return spec


def _csdid_model_spec(ctx: RunContext, prepared: dict[str, Any]) -> dict[str, Any]:
    spec = dict(ctx.spec)
    spec.update(
        {
            "data": str(prepared["analysis_data"]),
            "id": prepared["id"],
            "time": prepared["time"],
            "y": prepared["y"],
            "x": prepared["controls"],
            "gvar": "_s4e_gvar",
            "method": ctx.spec.get("csdid_method", "reg"),
            "cluster": prepared["cluster"],
            "output_dir": str(ctx.run_dir / "steps"),
        }
    )
    return spec


def _drdid_model_spec(ctx: RunContext, prepared: dict[str, Any]) -> dict[str, Any]:
    spec = _base_model_spec(ctx, prepared)
    spec["treatment"] = "_s4e_treat"
    spec.setdefault("method", ctx.spec.get("drdid_method", "drimp"))
    spec.setdefault("data_type", ctx.spec.get("data_type", "panel"))
    sample_if = ctx.spec.get("drdid_sample_if") or ctx.spec.get("two_period_sample_if") or ctx.spec.get("sample_if")
    if sample_if:
        spec["sample_if"] = sample_if
    return spec


def _did_imputation_model_spec(ctx: RunContext, prepared: dict[str, Any]) -> dict[str, Any]:
    spec = _csdid_model_spec(ctx, prepared)
    spec["gvar"] = "_s4e_gvar"
    spec.setdefault("horizons", ctx.spec.get("horizons"))
    return {key: value for key, value in spec.items() if value is not None}


def _routed_did_step_spec(ctx: RunContext, prepared: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    estimator = str(selected.get("estimator"))
    if estimator == "twfe":
        return _base_model_spec(ctx, prepared)
    if estimator == "event_study_twfe":
        return _event_model_spec(ctx, prepared)
    if estimator == "drdid":
        return _drdid_model_spec(ctx, prepared)
    if estimator in {"cs_did_attgt", "csdid"}:
        return _csdid_model_spec(ctx, prepared)
    if estimator == "did_imputation":
        return _did_imputation_model_spec(ctx, prepared)
    return dict(ctx.spec)


def _collect_model_tables(
    ctx: RunContext,
    step_results: list[dict[str, Any]],
    *,
    prepared: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    prepared = prepared or {}
    cluster_count = (prepared.get("data_summary") or {}).get("cluster_count")
    for step in step_results:
        child_run_dir = Path(step["run_dir"])
        child_model_table = child_run_dir / "model_table.csv"
        table = _read_csv(child_model_table)
        manifest = step.get("manifest", {}) if isinstance(step.get("manifest"), dict) else {}
        if not table:
            combined.append(
                {
                    "model": step.get("method"),
                    "engine": step.get("engine"),
                    "status": step.get("status"),
                    "source_run_dir": str(child_run_dir),
                    "source_model_table": str(child_model_table),
                    "term": "",
                    "note": manifest.get("error", ""),
                }
            )
            continue
        for row in table:
            row = dict(row)
            coef = _float_or_none(row.get("coef") or row.get("estimate") or row.get("coefficient"))
            se = _float_or_none(row.get("std_error") or row.get("se") or row.get("standard_error"))
            if coef is not None and se is not None:
                row.setdefault("ci_low", coef - 1.96 * se)
                row.setdefault("ci_high", coef + 1.96 * se)
            if not row.get("n_obs"):
                n_obs = manifest.get("nobs") or manifest.get("n_obs") or manifest.get("n")
                if n_obs is not None:
                    row["n_obs"] = n_obs
            if not row.get("n_clusters") and cluster_count is not None:
                row["n_clusters"] = cluster_count
            row["model"] = step.get("method")
            row["engine"] = step.get("engine")
            row["status"] = step.get("status")
            row["source_run_dir"] = str(child_run_dir)
            row["source_model_table"] = str(child_model_table)
            combined.append(row)
    _write_csv(ctx.artifact("model_table.csv"), combined)
    return combined


def _write_summary_stats(
    ctx: RunContext,
    frame: Any,
    variables: list[str],
    *,
    variable_units: dict[str, str] | None = None,
) -> str | None:
    import pandas as pd

    variable_units = variable_units or {}
    rows: list[dict[str, Any]] = []
    for variable in dict.fromkeys([item for item in variables if item]):
        if variable not in frame.columns:
            continue
        series = pd.to_numeric(frame[variable], errors="coerce").dropna()
        if series.empty:
            continue
        rows.append(
            {
                "variable": variable,
                "n": int(series.shape[0]),
                "mean": float(series.mean()),
                "sd": float(series.std(ddof=1)) if series.shape[0] > 1 else 0.0,
                "min": float(series.min()),
                "max": float(series.max()),
                "unit": variable_units.get(variable, ""),
                "source": "analysis_data.csv",
            }
        )
    if not rows:
        return None
    path = ctx.artifact("summary_stats.csv")
    _write_csv(path, rows)
    return str(path)


def _write_cohort_table(
    ctx: RunContext,
    did_design: dict[str, Any],
    frame: Any | None = None,
    *,
    id_col: str = "",
) -> str | None:
    first_treat_years = did_design.get("first_treat_years") or []
    min_pre = did_design.get("min_pre_periods_by_cohort") or {}
    min_post = did_design.get("min_post_periods_by_cohort") or {}
    n_units_by_cohort: dict[str, int] = {}
    if frame is not None and id_col and id_col in frame.columns and "_s4e_gvar" in frame.columns:
        try:
            import pandas as pd

            cohort_frame = frame[[id_col, "_s4e_gvar"]].dropna().copy()
            cohort_frame["_s4e_gvar"] = pd.to_numeric(cohort_frame["_s4e_gvar"], errors="coerce")
            treated = cohort_frame[cohort_frame["_s4e_gvar"] > 0]
            counts = treated.drop_duplicates([id_col, "_s4e_gvar"]).groupby("_s4e_gvar")[id_col].nunique()
            n_units_by_cohort = {str(int(cohort)): int(count) for cohort, count in counts.items()}
        except Exception:
            n_units_by_cohort = {}
    if not n_units_by_cohort and len(first_treat_years) == 1 and did_design.get("n_treated_units") is not None:
        n_units_by_cohort[str(first_treat_years[0])] = int(did_design.get("n_treated_units") or 0)
    rows: list[dict[str, Any]] = []
    for cohort in first_treat_years if isinstance(first_treat_years, list) else []:
        key = str(cohort)
        rows.append(
            {
                "cohort": key,
                "first_treat_period": cohort,
                "n_units": n_units_by_cohort.get(key),
                "min_pre_periods": min_pre.get(key),
                "min_post_periods": min_post.get(key),
                "source": "did_design.json",
            }
        )
    if not rows:
        return None
    path = ctx.artifact("cohort_table.csv")
    _write_csv(path, rows)
    return str(path)


def _write_event_study_table(ctx: RunContext, event_rows: list[dict[str, Any]]) -> str | None:
    rows: list[dict[str, Any]] = []
    for row in event_rows:
        event_time = _parse_event_term(str(row.get("term", "")))
        if event_time is None:
            continue
        coef = _float_or_none(row.get("coef"))
        se = _float_or_none(row.get("std_error"))
        p_value = _float_or_none(row.get("p_value"))
        ci_low = _float_or_none(row.get("ci_low"))
        ci_high = _float_or_none(row.get("ci_high"))
        if coef is None:
            continue
        if (ci_low is None or ci_high is None) and se is not None:
            ci_low = coef - 1.96 * se
            ci_high = coef + 1.96 * se
        rows.append(
            {
                "event_time": event_time,
                "term": row.get("term"),
                "estimate": coef,
                "std_error": se,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "p_value": p_value,
                "model": row.get("model"),
                "engine": row.get("engine"),
                "status": row.get("status"),
                "source_model_table": row.get("source_model_table"),
            }
        )
    if not rows:
        return None
    rows.sort(key=lambda item: int(item["event_time"]))
    path = ctx.artifact("event_study.csv")
    _write_csv(path, rows)
    return str(path)


def _write_pretrend_test(ctx: RunContext, event_rows: list[dict[str, Any]], base_period: int) -> str | None:
    leads: list[dict[str, Any]] = []
    for row in event_rows:
        event_time = _parse_event_term(str(row.get("term", "")))
        if event_time is None or event_time >= 0 or event_time == base_period:
            continue
        coef = _float_or_none(row.get("coef"))
        se = _float_or_none(row.get("std_error"))
        p_value = _float_or_none(row.get("p_value"))
        if coef is None:
            continue
        leads.append(
            {
                "event_time": event_time,
                "estimate": coef,
                "std_error": se,
                "p_value": p_value,
                "source_model_table": row.get("source_model_table"),
            }
        )
    if not leads:
        return None
    p_values = [item["p_value"] for item in leads if item.get("p_value") is not None]
    lead_estimates = [abs(float(item["estimate"])) for item in leads if item.get("estimate") is not None]
    lead_t_stats = [
        abs(float(item["estimate"]) / float(item["std_error"]))
        for item in leads
        if item.get("estimate") is not None and item.get("std_error") not in {None, 0, 0.0}
    ]
    payload = {
        "version": "skill4econ.pretrend_test.v1",
        "test_type": "event_study_lead_screen",
        "formal_joint_test_available": False,
        "base_period": base_period,
        "lead_count": len(leads),
        "pre_period_count": len(leads),
        "lead_p_values_available": len(p_values),
        "min_p_value": min(p_values) if p_values else None,
        "max_abs_estimate": max(lead_estimates) if lead_estimates else None,
        "max_abs_t": max(lead_t_stats) if lead_t_stats else None,
        "any_lead_p_below_0_05": any(value < 0.05 for value in p_values),
        "status": "computed_from_event_study_leads" if p_values else "lead_coefficients_without_p_values",
        "caveat": "This is a machine pretrend diagnostic from event-study lead coefficients, not a joint Wald test.",
        "leads": sorted(leads, key=lambda item: int(item["event_time"])),
    }
    path = ctx.artifact("pretrend_test.json")
    write_json(path, payload)
    return str(path)


def _did_twfe_diagnostic(
    frame: Any,
    *,
    y: str,
    id_col: str,
    time_col: str,
    controls: list[str],
    cluster: str,
    treat_col: str,
    post_col: str,
) -> dict[str, Any]:
    import pandas as pd

    if not treat_col or not post_col:
        return {"status": "skipped_missing_configuration", "error": "treat_col and post_col are required"}
    required = [y, id_col, time_col, treat_col, post_col, *controls]
    if cluster:
        required.append(cluster)
    missing = [col for col in dict.fromkeys(required) if col and col not in frame.columns]
    if missing:
        return {"status": "skipped_missing_columns", "error": f"missing columns: {missing}"}

    columns = [col for col in dict.fromkeys(required) if col]
    work = frame[columns].copy()
    work["_diag_treat"] = pd.to_numeric(work[treat_col], errors="coerce")
    work["_diag_post"] = pd.to_numeric(work[post_col], errors="coerce")
    control_terms = [col for col in controls if col in work.columns]
    for col in control_terms:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=[y, id_col, time_col, "_diag_treat", "_diag_post", *control_terms])
    if len(work) < 4:
        return {"status": "skipped_too_few_rows", "error": "fewer than four usable rows after dropna"}
    if work["_diag_treat"].nunique(dropna=True) < 2:
        return {"status": "skipped_no_treatment_variation", "error": "treatment column has no usable variation"}
    if work["_diag_post"].nunique(dropna=True) < 2:
        return {"status": "skipped_no_post_variation", "error": "post/placebo column has no usable variation"}

    try:
        work["_did_treat_post"] = work["_diag_treat"].astype(float) * work["_diag_post"].astype(float)
        design = work[["_did_treat_post", *control_terms]].copy()
        design = design.join(pd.get_dummies(work[id_col].astype(str), prefix=f"fe_{id_col}", drop_first=True).astype(float))
        design = design.join(
            pd.get_dummies(work[time_col].astype(str), prefix=f"fe_{time_col}", drop_first=True).astype(float)
        )
        design["_const"] = 1.0
        design[y] = pd.to_numeric(work[y], errors="coerce").to_numpy()
        cluster_arg = cluster if cluster and cluster in work.columns else None
        if cluster_arg:
            design[cluster_arg] = work[cluster_arg].to_numpy()
        terms = [
            "_const",
            "_did_treat_post",
            *[col for col in design.columns if col not in {y, cluster_arg, "_const", "_did_treat_post"}],
        ]
        rows, meta = _ols_numpy(design, y, terms, cluster=cluster_arg)
        effect = next((row for row in rows if row.get("term") == "_did_treat_post"), None)
        if not effect:
            return {"status": "failed_no_effect_row", "error": "DID interaction row was not returned"}
        estimate = _float_or_none(effect.get("coef"))
        se = _float_or_none(effect.get("std_error"))
        payload = {
            "status": "computed",
            "estimate": estimate,
            "std_error": se,
            "p_value": _float_or_none(effect.get("p_value")),
            "t_stat": _float_or_none(effect.get("t_stat")),
            "n_obs": meta.get("nobs"),
            "n_clusters": int(work[cluster_arg].nunique(dropna=True)) if cluster_arg else None,
            "cov_type": meta.get("cov_type"),
        }
        if estimate is not None and se is not None:
            payload["ci_low"] = estimate - 1.96 * se
            payload["ci_high"] = estimate + 1.96 * se
        return payload
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "error_type": exc.__class__.__name__}


def _write_placebo_tests(ctx: RunContext, prepared: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]], bool]:
    configs = prepared.get("configured_placebo_tests") or []
    if not configs:
        return None, [], False
    import pandas as pd

    analysis_path = Path(str(prepared["analysis_data"]))
    frame = pd.read_csv(analysis_path)
    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for config in configs:
        name = str(config.get("name") or config.get("post_col") or "placebo")
        post_col = str(config.get("post_col") or "")
        treat_col = str(config.get("treat_col") or "_s4e_treat")
        diagnostic = _did_twfe_diagnostic(
            frame,
            y=str(prepared.get("y") or ""),
            id_col=str(prepared.get("id") or ""),
            time_col=str(prepared.get("time") or ""),
            controls=list(prepared.get("controls") or []),
            cluster=str(prepared.get("cluster") or ""),
            treat_col=treat_col,
            post_col=post_col,
        )
        row = {
            "placebo": name,
            "post_column": post_col,
            "treat_column": treat_col,
            "source": "analysis_data.csv",
            "diagnostic_role": "author_configured_placebo_timing",
            **diagnostic,
        }
        rows.append(row)
        if diagnostic.get("status") != "computed":
            warnings.append(
                _warning(
                    "yellow",
                    "placebo_test_not_computed",
                    f"Configured placebo test `{name}` did not produce a usable estimate: {diagnostic.get('error') or diagnostic.get('status')}.",
                    action="Fix the configured placebo timing column before using placebo evidence.",
                )
            )
    path = ctx.artifact("placebo_tests.csv")
    _write_csv(path, rows)
    return str(path), warnings, any(row.get("status") == "computed" for row in rows)


def _write_heterogeneity(ctx: RunContext, prepared: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]], bool]:
    dimensions = list(prepared.get("configured_heterogeneity_dimensions") or [])
    if not dimensions:
        return None, [], False
    import pandas as pd

    analysis_path = Path(str(prepared["analysis_data"]))
    frame = pd.read_csv(analysis_path)
    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for dimension in dimensions:
        if dimension not in frame.columns:
            warnings.append(
                _warning(
                    "yellow",
                    "heterogeneity_dimension_missing",
                    f"Configured heterogeneity dimension `{dimension}` is missing from analysis_data.csv.",
                    action="Add the dimension column to the input data or remove it from the spec.",
                )
            )
            rows.append(
                {
                    "dimension": dimension,
                    "group": "",
                    "source": "analysis_data.csv",
                    "diagnostic_role": "author_configured_subgroup_did",
                    "status": "skipped_missing_dimension",
                }
            )
            continue
        for group_value, subset in frame.groupby(dimension, dropna=False):
            diagnostic = _did_twfe_diagnostic(
                subset,
                y=str(prepared.get("y") or ""),
                id_col=str(prepared.get("id") or ""),
                time_col=str(prepared.get("time") or ""),
                controls=list(prepared.get("controls") or []),
                cluster=str(prepared.get("cluster") or ""),
                treat_col="_s4e_treat",
                post_col="_s4e_post",
            )
            rows.append(
                {
                    "dimension": dimension,
                    "group": "" if pd.isna(group_value) else str(group_value),
                    "source": "analysis_data.csv",
                    "diagnostic_role": "author_configured_subgroup_did",
                    **diagnostic,
                }
            )
    computed_dimensions = {
        str(row.get("dimension"))
        for row in rows
        if row.get("status") == "computed"
    }
    missing_dimensions = [dimension for dimension in dimensions if dimension not in computed_dimensions]
    if missing_dimensions:
        warnings.append(
            _warning(
                "yellow",
                "heterogeneity_not_computed",
                f"Configured heterogeneity dimensions without usable subgroup estimates: {missing_dimensions}.",
                action="Check subgroup support and variation before using heterogeneity evidence.",
            )
        )
    path = ctx.artifact("heterogeneity.csv")
    _write_csv(path, rows)
    return str(path), warnings, bool(computed_dimensions)


def _write_robustness_grid(
    ctx: RunContext,
    *,
    step_results: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    prepared: dict[str, Any],
    diagnostic_artifacts: dict[str, str | None] | None = None,
) -> str | None:
    rows: list[dict[str, Any]] = []
    for row in comparison_rows:
        if row.get("status") in {None, "", "skipped"}:
            continue
        rows.append(
            {
                "family": "estimator_comparison",
                "check": row.get("estimator"),
                "status": row.get("status"),
                "estimate": row.get("estimate"),
                "std_error": row.get("std_error"),
                "p_value": row.get("p_value"),
                "source_path": row.get("source_path"),
            }
        )
    data_summary = prepared.get("data_summary") or {}
    sample = prepared.get("sample_construction") or {}
    if sample:
        rows.append(
            {
                "family": "sample_construction",
                "check": "did_listwise_deletion",
                "status": "computed",
                "estimate": sample.get("drop_ratio_did_listwise"),
                "std_error": None,
                "p_value": None,
                "source_path": "sample_construction.json",
            }
        )
    if data_summary:
        rows.append(
            {
                "family": "cluster_diagnostic",
                "check": "cluster_count",
                "status": "computed",
                "estimate": data_summary.get("cluster_count"),
                "std_error": None,
                "p_value": None,
                "source_path": "data_summary.json",
            }
        )
    for family, source_path in (diagnostic_artifacts or {}).items():
        if not source_path:
            continue
        rows.append(
            {
                "family": family,
                "check": "author_configured_diagnostic",
                "status": "computed",
                "estimate": None,
                "std_error": None,
                "p_value": None,
                "source_path": source_path,
            }
        )
    if not rows and step_results:
        rows.extend(
            {
                "family": "estimator_status",
                "check": step.get("label") or step.get("method"),
                "status": step.get("status"),
                "estimate": None,
                "std_error": None,
                "p_value": None,
                "source_path": step.get("run_dir"),
            }
            for step in step_results
        )
    if not rows:
        return None
    path = ctx.artifact("robustness_grid.csv")
    _write_csv(path, rows)
    return str(path)


def _write_figure_manifest(ctx: RunContext, figure_paths: list[str | None]) -> str | None:
    rows = []
    for path_text in figure_paths:
        if not path_text:
            continue
        path = Path(path_text)
        if path.exists():
            try:
                rel = path.resolve().relative_to(ctx.run_dir.resolve()).as_posix()
            except ValueError:
                rel = str(path)
            rows.append({"path": rel, "kind": "figure", "exists": True})
    if not rows:
        return None
    path = ctx.artifact("figures") / "manifest.yaml"
    text = "\n".join(
        [
            "figures:",
            *[f"  - path: {row['path']}\n    kind: {row['kind']}\n    exists: true" for row in rows],
        ]
    )
    write_text(path, text + "\n")
    return str(path)


def _write_robustness_plan(ctx: RunContext, design_type: str) -> None:
    text = f"""# Robustness Plan

Status: not executed in this run.

The DID PaperRun v0.1 does not fabricate a robustness summary. A
`robustness_summary.csv` should only be generated after real robustness
models have run.

Recommended next checks for `{design_type}`:

- Baseline with controls versus without controls.
- Alternative event windows when the data support enough leads/lags.
- Alternative clustering or inference strategy when cluster count is low.
- For staggered adoption DID, compare TWFE with csdid/drdid or another
  staggered estimator before treating the package as paper-ready.
"""
    write_text(ctx.artifact("robustness_plan.md"), text)


def _render_report(
    ctx: RunContext,
    prepared: dict[str, Any],
    status: str,
    step_results: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    data = prepared.get("data_summary", {})
    red = [item for item in warnings if item.get("severity") == "red"]
    yellow = [item for item in warnings if item.get("severity") == "yellow"]
    green = [item for item in warnings if item.get("severity") == "green"]
    lines = [
        "# DID PaperRun v0.1 Report",
        "",
        f"Workflow status: `{status}`",
        f"Design type: `{prepared.get('design_type', '')}`",
        f"Engine policy: `{prepared.get('engine_policy', '')}`",
        "",
        "## Data And Sample",
        "",
        f"- Raw rows: {data.get('rows_raw', '')}",
        f"- Entities: {data.get('entities', '')}",
        f"- Periods: {data.get('periods', '')}",
        f"- Balanced panel: {data.get('balanced_panel', '')}",
        f"- Cluster: {data.get('cluster', '')}; cluster count: {data.get('cluster_count', '')}",
        f"- id-time duplicate rows: {data.get('id_time_duplicates', 0)}",
        f"- Event window: {prepared.get('event_window', '')}; omitted/base period: {prepared.get('base_period', '')}",
        "",
        "## Model Steps",
        "",
    ]
    for step in step_results:
        lines.append(
            f"- `{step['engine']}.{step['method']}`: `{step['status']}` ({step['run_dir']})"
        )
    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    if not warnings:
        lines.append("- No warnings were generated.")
    for item in [*red, *yellow, *green]:
        action = f" Action: {item.get('action')}" if item.get("action") else ""
        lines.append(
            f"- `{item.get('severity')}` `{item.get('code')}`: {item.get('message')}{action}"
        )
    lines.extend(
        [
            "",
            "## What Can And Cannot Be Claimed",
            "",
            "- The workflow reports estimates and diagnostics for the current spec.",
            "- It does not prove that the DID identification assumptions hold.",
            "- Do not write that parallel trends are proven or that the policy effect is proven causal solely from this run.",
            "- For supported pre-treatment leads, use wording such as: no obvious pre-trend evidence was detected in the current specification.",
            "- For staggered adoption designs, TWFE-only output is not a complete paper-ready DID package.",
            "",
            "## Generated Files",
            "",
            "- `manifest.json`",
            "- `audit.json`",
            "- `dependency_report.json`",
            "- `data_summary.json` / `data_summary.csv`",
            "- `sample_construction.json`",
            "- `treatment_timing_summary.csv`",
            "- `event_study_support.csv`",
            "- `warnings.json` / `did_diagnostics.json`",
            "- `model_table.csv`",
            "- `event_study_plot.png` when event-study coefficients are available",
            "- `robustness_plan.md`",
            "- `rerun.bat` / `rerun.sh`",
        ]
    )
    write_text(ctx.artifact("research_report.md"), "\n".join(lines) + "\n")


def _write_workflow_rerun_scripts(ctx: RunContext, workflow_name: str) -> None:
    spec_path = ctx.spec.get("_spec_path") or "SPEC"
    output_arg = shlex.quote(str(ctx.run_dir.parent))
    cmd = (
        f"conda run -n base python -m skill4econ.cli workflow "
        f"--name {workflow_name} --spec {shlex.quote(str(spec_path))} --output {output_arg} --run"
    )
    write_text(ctx.artifact("rerun.sh"), "#!/usr/bin/env bash\nset -euo pipefail\n" + cmd + "\n")
    write_text(
        ctx.artifact("rerun.bat"),
        "@echo off\r\n"
        "set PYTHONUTF8=1\r\n"
        "set PYTHONIOENCODING=utf-8\r\n"
        + cmd.replace("'", '"')
        + "\r\n",
    )


def _write_rerun_scripts(ctx: RunContext) -> None:
    _write_workflow_rerun_scripts(ctx, "did_paper_run")


def _resolve_repo_path(ctx: RunContext, value: Any) -> Path:
    path = Path(str(value))
    if not path.is_absolute():
        path = ctx.repo_root / path
    return path


def _load_optional_data_contract_payload(ctx: RunContext) -> dict[str, Any] | None:
    value = ctx.spec.get("data_contract") or ctx.spec.get("contract")
    if not value:
        return None
    path = _resolve_repo_path(ctx, value)
    if not path.exists():
        return None
    try:
        return load_data_contract(path)
    except Exception:
        return None


def _validate_optional_data_contract(ctx: RunContext, df: Any) -> list[dict[str, Any]]:
    value = ctx.spec.get("data_contract") or ctx.spec.get("contract")
    if not value:
        return []
    path = _resolve_repo_path(ctx, value)
    if not path.exists():
        return [
            _warning(
                "red",
                "data_contract_failed",
                f"data_contract was declared but not found: {path}",
                action="Fix the data_contract path or remove it from the spec.",
            )
        ]
    try:
        contract = load_data_contract(path)
        validation = validate_data_contract(contract, df, base_dir=path.parent)
    except Exception as exc:
        return [
            _warning(
                "red",
                "data_contract_failed",
                f"data_contract validation failed: {exc}",
                action="Fix data_contract.yaml before running paper workflows.",
            )
        ]
    write_validated_contract(ctx.artifact("data_contract_validated.yaml"), contract, validation)
    write_contract_errors(ctx.artifact("data_contract_errors.json"), validation)
    warnings: list[dict[str, Any]] = []
    if validation.get("errors"):
        warnings.append(
            _warning(
                "red",
                "data_contract_failed",
                f"data_contract has {len(validation.get('errors') or [])} blocking errors.",
                action="Inspect data_contract_errors.json and fix the input data or contract.",
            )
        )
    for item in validation.get("warnings") or []:
        warnings.append(
            _warning(
                "yellow",
                str(item.get("code") or "data_contract_warning"),
                str(item.get("message") or "data_contract emitted a warning."),
                action="Inspect data_contract_errors.json before making paper claims.",
            )
        )
    return warnings


def _step_status_ok(step: dict[str, Any]) -> bool:
    return step.get("status") == "ok"


def _step_manifest_warnings(step: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = step.get("manifest") if isinstance(step.get("manifest"), dict) else {}
    label = str(step.get("label") or step.get("method") or "step")
    results: list[dict[str, Any]] = []
    for item in manifest.get("warnings") or []:
        if not isinstance(item, dict) or item.get("severity") == "green":
            continue
        code = str(item.get("code") or "step_warning")
        message = str(item.get("message") or "")
        results.append(
            _warning(
                str(item.get("severity") or "yellow"),
                code,
                f"{label}: {message}" if message else f"{label} emitted warning `{code}`.",
                action=str(item.get("action") or "Inspect the step artifacts before using this workflow output."),
            )
        )
    return results


def _effect_from_table(path: Path, preferred_terms: list[str]) -> dict[str, Any] | None:
    rows = _read_csv(path)
    if not rows:
        return None
    for term in preferred_terms:
        for row in rows:
            if str(row.get("term", "")).lower() == term.lower() and _float_or_none(row.get("coef")) is not None:
                return row
    for row in rows:
        if _float_or_none(row.get("coef")) is not None:
            return row
    return None


def _comparison_row(
    *,
    estimator: str,
    role: str,
    step: dict[str, Any] | None,
    effect: dict[str, Any] | None,
    source_path: Path | None,
    note: str = "",
) -> dict[str, Any]:
    estimate = _float_or_none((effect or {}).get("coef"))
    se = _float_or_none((effect or {}).get("std_error"))
    ci_low = estimate - 1.96 * se if estimate is not None and se is not None else None
    ci_high = estimate + 1.96 * se if estimate is not None and se is not None else None
    return {
        "estimator": estimator,
        "role": role,
        "estimate": estimate,
        "std_error": se,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_value": (effect or {}).get("p_value"),
        "status": (step or {}).get("status") or "missing",
        "source_path": str(source_path) if source_path else "",
        "note": note,
    }


def _psm_did_postprocess(ctx: RunContext, step_results: list[dict[str, Any]], warnings: list[dict[str, Any]], data_summary: dict[str, Any]) -> list[dict[str, Any]]:
    del warnings, data_summary
    by_label = {str(step.get("label")): step for step in step_results}
    tables = ctx.artifact("tables")
    raw = ctx.artifact("raw")
    tables.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)

    psm_step = by_label.get("propensity_overlap")
    twfe_step = by_label.get("twfe_did")
    drdid_step = by_label.get("drdid_2x2")

    psm_path = Path(str((psm_step or {}).get("run_dir", ""))) / "model_table.csv" if psm_step else None
    twfe_path = Path(str((twfe_step or {}).get("run_dir", ""))) / "model_table.csv" if twfe_step else None
    drdid_path = Path(str((drdid_step or {}).get("run_dir", ""))) / "model_table.csv" if drdid_step else None
    drdid_log = Path(str((drdid_step or {}).get("run_dir", ""))) / "stata.log" if drdid_step else None

    psm_att = _effect_from_table(psm_path, ["ATT_nearest_neighbor"]) if psm_path else None
    ipw_att = _effect_from_table(psm_path, ["ATT_ipw"]) if psm_path else None
    twfe_att = _effect_from_table(twfe_path, ["_did_treat_post", "treat_post", "treatment_post"]) if twfe_path else None
    drdid_att = _effect_from_table(drdid_path, ["ATT", "att", "treatment"]) if drdid_path else None

    if drdid_log and drdid_log.exists():
        shutil.copyfile(drdid_log, raw / "drdid.log")
    else:
        write_text(raw / "drdid.log", "DRDID log unavailable; inspect step_results.json for backend status.\n")

    drdid_main_row = _comparison_row(
        estimator="drdid_2x2",
        role="core_adjusted_did",
        step=drdid_step,
        effect=drdid_att,
        source_path=drdid_path,
        note="" if drdid_att else "No numeric DRDID main effect parsed.",
    )
    _write_csv(tables / "drdid_main.csv", [drdid_main_row])

    rows = [
        drdid_main_row,
        _comparison_row(
            estimator="psm_nearest_neighbor_att",
            role="legacy_psm_diagnostic",
            step=psm_step,
            effect=psm_att,
            source_path=psm_path,
            note="PSM-DID is diagnostic support, not the core identification estimator.",
        ),
        _comparison_row(
            estimator="ipw_att",
            role="weighted_observable_adjustment",
            step=psm_step,
            effect=ipw_att,
            source_path=psm_path,
            note="IPW depends on overlap and stable weights.",
        ),
        _comparison_row(
            estimator="twfe_did",
            role="baseline_did",
            step=twfe_step,
            effect=twfe_att,
            source_path=twfe_path,
            note="Baseline TWFE, not a substitute for DRDID.",
        ),
    ]
    _write_csv(tables / "adjusted_did_comparison.csv", rows)
    write_text(
        ctx.artifact("adjusted_did_identification_notes.md"),
        "\n".join(
            [
                "# Adjusted DID Identification Notes",
                "",
                "- Propensity-score matching/weighting only addresses observed covariate support and balance.",
                "- DID identification still requires conditional parallel trends in the chosen analysis window.",
                "- DRDID is a covariate-adjusted DID estimator; it is not equivalent to automatic causality after matching.",
            ]
        )
        + "\n",
    )

    new_warnings: list[dict[str, Any]] = []
    drdid_estimate = _float_or_none(drdid_main_row.get("estimate"))
    for row in rows[1:3]:
        estimate = _float_or_none(row.get("estimate"))
        if drdid_estimate is not None and estimate is not None and estimate and math.copysign(1, drdid_estimate) != math.copysign(1, estimate):
            new_warnings.append(
                _warning(
                    "red",
                    "DRDID_PSM_DID_DISAGREE",
                    f"DRDID and {row.get('estimator')} have opposite signs.",
                    action="Treat PSM/IPW as diagnostics and explain why the core adjusted DID differs.",
                )
            )
            break
    return new_warnings


def _workflow_method_card(
    *,
    name: str,
    title: str,
    why_p0: str,
    input_fields: list[str],
    estimators: list[str],
    diagnostics: list[str],
    outputs: list[str],
    failure_conditions: list[str],
    tonight_scope: str,
    claim_limits: list[str],
    next_steps: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "title": title,
        "workflow_level": "paper_run_v0.1",
        "why_p0": why_p0,
        "input_fields": input_fields,
        "estimators": estimators,
        "diagnostics": diagnostics,
        "outputs": outputs,
        "failure_conditions": failure_conditions,
        "tonight_scope": tonight_scope,
        "claim_limits": claim_limits,
        "next_steps": next_steps,
    }


def _write_workflow_blueprint(ctx: RunContext, card: dict[str, Any]) -> None:
    write_json(ctx.artifact("method_card.json"), card)
    lines = [
        f"# {card['title']}",
        "",
        f"Workflow: `{card['name']}`",
        f"Level: `{card['workflow_level']}`",
        "",
        "## Why P0",
        "",
        str(card["why_p0"]),
        "",
        "## Input Fields",
        "",
    ]
    lines.extend(f"- `{field}`" for field in card["input_fields"])
    lines.extend(["", "## Estimators", ""])
    lines.extend(f"- {item}" for item in card["estimators"])
    lines.extend(["", "## Diagnostics", ""])
    lines.extend(f"- {item}" for item in card["diagnostics"])
    lines.extend(["", "## Outputs", ""])
    lines.extend(f"- `{item}`" for item in card["outputs"])
    lines.extend(["", "## Failure Conditions", ""])
    lines.extend(f"- {item}" for item in card["failure_conditions"])
    lines.extend(["", "## Claim Limits", ""])
    lines.extend(f"- {item}" for item in card["claim_limits"])
    lines.extend(["", "## Tonight Scope", "", str(card["tonight_scope"]), ""])
    write_text(ctx.artifact("workflow_blueprint.md"), "\n".join(lines))


def _field_value(spec: dict[str, Any], field: str) -> Any:
    if field == "threshold":
        return spec.get("threshold") or spec.get("q")
    if field == "controls":
        return spec.get("controls") or spec.get("x") or spec.get("covars")
    if field == "treatment":
        return spec.get("treatment") or spec.get("treat")
    return spec.get(field)


def _workflow_data_validation(
    ctx: RunContext,
    *,
    required_spec_fields: list[str],
    column_fields: list[str],
    list_column_fields: list[str],
    file_fields: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    spec = ctx.spec
    for field in required_spec_fields:
        value = _field_value(spec, field)
        if value is None or value == "" or value == []:
            warnings.append(
                _warning(
                    "red",
                    f"missing_{field}",
                    f"Workflow spec requires `{field}`.",
                    action=f"Add `{field}` to the workflow spec.",
                )
            )

    data_summary: dict[str, Any] = {}
    df = None
    if spec.get("data") or spec.get("input") or spec.get("input_path"):
        try:
            df, data_path = read_table(spec)
            data_summary = {
                "data_path": str(data_path),
                "data_sha256": file_sha256(data_path),
                "rows": int(len(df)),
                "columns": list(map(str, df.columns)),
            }
        except Exception as exc:
            warnings.append(
                _warning(
                    "red",
                    "data_read_failed",
                    f"Could not read input data: {exc}",
                    action="Fix the data path/format before running estimators.",
                )
            )
        if df is not None:
            warnings.extend(_validate_optional_data_contract(ctx, df))
    elif "data" in required_spec_fields:
        warnings.append(
            _warning(
                "red",
                "missing_data",
                "Workflow spec requires data/input/input_path.",
                action="Provide a CSV or XLSX data path.",
            )
        )

    if df is not None:
        missing_columns: list[str] = []
        for field in column_fields:
            value = _field_value(spec, field)
            if value:
                missing_columns.extend([str(value)] if str(value) not in df.columns else [])
        for field in list_column_fields:
            for value in listify(_field_value(spec, field)):
                if value and value not in df.columns:
                    missing_columns.append(value)
        missing_columns = sorted(set(missing_columns))
        if missing_columns:
            warnings.append(
                _warning(
                    "red",
                    "missing_columns",
                    f"Input data is missing required columns: {missing_columns}.",
                    action="Fix the data columns or update the workflow spec.",
                )
            )
        id_col = spec.get("id")
        time_col = spec.get("time")
        if id_col and time_col and id_col in df.columns and time_col in df.columns:
            duplicate_cells = int(df.duplicated([id_col, time_col]).sum())
            data_summary["id_time_duplicates"] = duplicate_cells
            if duplicate_cells:
                warnings.append(
                    _warning(
                        "red",
                        "id_time_not_unique",
                        f"{duplicate_cells} duplicated id-time cells were found.",
                        action="Resolve duplicate panel cells before running paper workflows.",
                    )
                )
            data_summary["entities"] = int(df[id_col].nunique(dropna=True))
            data_summary["periods"] = int(df[time_col].nunique(dropna=True))

    for field in file_fields or []:
        value = spec.get(field)
        if not value:
            warnings.append(
                _warning(
                    "red",
                    f"missing_{field}",
                    f"Workflow spec requires `{field}`.",
                    action=f"Provide a path for `{field}`.",
                )
            )
            continue
        path = _resolve_repo_path(ctx, value)
        if not path.exists():
            warnings.append(
                _warning(
                    "red",
                    f"{field}_not_found",
                    f"`{field}` file was not found: {path}",
                    action=f"Fix the `{field}` path.",
                )
            )

    write_json(ctx.artifact("workflow_validation.json"), {"warnings": warnings, "data_summary": data_summary})
    return warnings, data_summary


def _render_generic_workflow_report(
    ctx: RunContext,
    *,
    card: dict[str, Any],
    status: str,
    step_results: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    data_summary: dict[str, Any],
) -> None:
    lines = [
        f"# {card['title']} Report",
        "",
        f"Workflow status: `{status}`",
        f"Workflow: `{card['name']}`",
        "",
        "## Data",
        "",
    ]
    if data_summary:
        for key in ["data_path", "rows", "entities", "periods", "id_time_duplicates", "data_sha256"]:
            if key in data_summary:
                lines.append(f"- {key}: {data_summary[key]}")
    else:
        lines.append("- No data summary was generated.")
    lines.extend(["", "## Model Steps", ""])
    if step_results:
        for step in step_results:
            lines.append(
                f"- `{step.get('engine')}.{step.get('method')}`"
                f" label=`{step.get('label')}` critical=`{step.get('critical')}`"
                f" status=`{step.get('status')}` ({step.get('run_dir')})"
            )
    else:
        lines.append("- No estimator step was run in this state.")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        for item in warnings:
            action = f" Action: {item.get('action')}" if item.get("action") else ""
            lines.append(
                f"- `{item.get('severity')}` `{item.get('code')}`: {item.get('message')}{action}"
            )
    else:
        lines.append("- No warnings were generated.")
    lines.extend(["", "## What Can And Cannot Be Claimed", ""])
    lines.extend(f"- {item}" for item in card["claim_limits"])
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in card["next_steps"])
    write_text(ctx.artifact("research_report.md"), "\n".join(lines) + "\n")


def _run_generic_paper_workflow(
    ctx: RunContext,
    *,
    card: dict[str, Any],
    required_spec_fields: list[str],
    column_fields: list[str],
    list_column_fields: list[str],
    steps: list[dict[str, Any]],
    file_fields: list[str] | None = None,
    extra_warnings: list[dict[str, Any]] | None = None,
    postprocess: Any | None = None,
) -> WorkflowResult:
    _write_workflow_blueprint(ctx, card)
    if ctx.state == "plan":
        write_audit(ctx, "planned", [f"{card['name']} plan generated."])
        _write_workflow_rerun_scripts(ctx, str(card["name"]))
        return write_manifest(ctx, "planned", workflow=card["name"], method_card=card)

    dep_report = dependency_report()
    write_json(ctx.artifact("dependency_report.json"), dep_report)
    warnings, data_summary = _workflow_data_validation(
        ctx,
        required_spec_fields=required_spec_fields,
        column_fields=column_fields,
        list_column_fields=list_column_fields,
        file_fields=file_fields,
    )
    if extra_warnings:
        warnings.extend(extra_warnings)
    step_results: list[dict[str, Any]] = []

    if ctx.state in {"dry-run", "audit"}:
        status = "validated" if not _has_red(warnings) else "failed"
        write_json(ctx.artifact("warnings.json"), {"warnings": warnings})
        _render_generic_workflow_report(
            ctx,
            card=card,
            status=status,
            step_results=step_results,
            warnings=warnings,
            data_summary=data_summary,
        )
        _write_workflow_rerun_scripts(ctx, str(card["name"]))
        write_audit(ctx, status, [f"{card['name']} {ctx.state} completed."], warnings=warnings)
        return write_manifest(
            ctx,
            status,
            workflow=card["name"],
            spec_sha256=_json_hash(ctx.spec),
            data_sha256=data_summary.get("data_sha256"),
            warnings=warnings,
            method_card=card,
        )

    if _has_red(warnings):
        write_json(ctx.artifact("warnings.json"), {"warnings": warnings})
        _render_generic_workflow_report(
            ctx,
            card=card,
            status="failed",
            step_results=step_results,
            warnings=warnings,
            data_summary=data_summary,
        )
        _write_workflow_rerun_scripts(ctx, str(card["name"]))
        write_audit(ctx, "failed", [f"{card['name']} preflight blocked estimation."], warnings=warnings)
        return write_manifest(
            ctx,
            "failed",
            workflow=card["name"],
            spec_sha256=_json_hash(ctx.spec),
            data_sha256=data_summary.get("data_sha256"),
            warnings=warnings,
            method_card=card,
        )

    for seq, step_spec in enumerate(steps, 1):
        spec = dict(step_spec.get("spec") or ctx.spec)
        spec.setdefault("output_dir", str(ctx.run_dir / "steps"))
        result = _run_step(ctx, str(step_spec["engine"]), str(step_spec["method"]), seq, spec)
        result["label"] = step_spec.get("label", result["method"])
        result["critical"] = bool(step_spec.get("critical", True))
        step_results.append(result)
        warnings.extend(_step_manifest_warnings(result))
        if not _step_status_ok(result):
            severity = "red" if result["critical"] else "yellow"
            warnings.append(
                _warning(
                    severity,
                    f"{result['label']}_failed",
                    f"{result['engine']}.{result['method']} returned status `{result['status']}`.",
                    action="Inspect the step manifest/log before using this workflow output.",
                )
            )

    _collect_model_tables(ctx, step_results)
    if postprocess:
        warnings.extend(postprocess(ctx, step_results, warnings, data_summary) or [])
    critical_failed = any(step["critical"] and not _step_status_ok(step) for step in step_results)
    optional_failed = any((not step["critical"]) and not _step_status_ok(step) for step in step_results)
    if critical_failed:
        status = "not_paper_ready"
    elif optional_failed:
        status = "degraded"
    else:
        status = "success"
    warnings.append(
        _warning(
            "green",
            "workflow_completed",
            "The workflow generated diagnostics and recorded all model statuses.",
        )
    )
    write_json(ctx.artifact("warnings.json"), {"warnings": warnings})
    write_json(ctx.artifact("step_results.json"), {"steps": step_results})
    _render_generic_workflow_report(
        ctx,
        card=card,
        status=status,
        step_results=step_results,
        warnings=warnings,
        data_summary=data_summary,
    )
    _write_workflow_rerun_scripts(ctx, str(card["name"]))
    audit_status = "ok" if status in {"success", "degraded"} else status
    write_audit(ctx, audit_status, [f"{card['name']} completed with workflow status: {status}."], warnings=warnings, steps=step_results)
    return write_manifest(
        ctx,
        status,
        workflow=card["name"],
        spec_sha256=_json_hash(ctx.spec),
        data_sha256=data_summary.get("data_sha256"),
        warnings=warnings,
        steps=step_results,
        method_card=card,
    )


def _psm_did_policy_steps(ctx: RunContext) -> list[dict[str, Any]]:
    audit_spec = _spec_with_treatment_aliases(ctx.spec)
    psm_spec = _spec_with_treatment_aliases(ctx.spec)
    did_spec = _spec_with_treatment_aliases(ctx.spec)
    drdid_spec = _spec_with_treatment_aliases(ctx.spec)
    drdid_spec["treatment"] = ctx.spec.get("treatment") or ctx.spec.get("treat")
    drdid_spec.setdefault("method", ctx.spec.get("drdid_method", "drimp"))
    drdid_spec.setdefault("data_type", "panel" if ctx.spec.get("id") else "repeated_cross_section")
    sample_if = ctx.spec.get("drdid_sample_if") or ctx.spec.get("two_period_sample_if") or ctx.spec.get("sample_if")
    if sample_if:
        drdid_spec["sample_if"] = sample_if
    return [
        {"label": "data_audit", "engine": "python", "method": "data_audit", "critical": False, "spec": audit_spec},
        {"label": "propensity_overlap", "engine": "python", "method": "psm_ipw_match", "critical": False, "spec": psm_spec},
        {"label": "twfe_did", "engine": "python", "method": "did_twfe_event", "critical": True, "spec": did_spec},
        {"label": "drdid_2x2", "engine": "stata", "method": "dr_did_2x2", "critical": False, "spec": drdid_spec},
    ]


def _spec_with_treatment_aliases(spec: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(spec)
    if not normalized.get("treat") and normalized.get("treatment"):
        normalized["treat"] = normalized["treatment"]
    if not normalized.get("treatment") and normalized.get("treat"):
        normalized["treatment"] = normalized["treat"]
    return normalized


def _psm_did_extra_warnings(ctx: RunContext) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if not (ctx.spec.get("drdid_sample_if") or ctx.spec.get("two_period_sample_if") or ctx.spec.get("sample_if")):
        warnings.append(
            _warning(
                "yellow",
                "drdid_window_not_declared",
                "DRDID is a 2x2 estimator; no explicit two-period sample_if was declared.",
                action="For multi-period panels, pass drdid_sample_if/two_period_sample_if such as inlist(year, 2018, 2019).",
            )
        )
    return warnings


def psm_did_policy_run(ctx: RunContext) -> WorkflowResult:
    card = _workflow_method_card(
        name="psm_did_policy_run",
        title="PSM/DID PolicyRun v0.1",
        why_p0="Environmental economics and ESG papers often use PSM-DID/DRDID around policy shocks; this workflow makes the design auditable without pretending PSM alone solves identification.",
        input_fields=["data", "id", "time", "y", "treat or treatment", "post", "x/covars", "cluster", "optional drdid_sample_if"],
        estimators=["python.psm_ipw_match for propensity overlap/legacy PSM diagnostics", "python.did_twfe_event for baseline DID", "stata.dr_did_2x2 for Sant'Anna-Zhao DRDID when a valid 2x2 window is declared"],
        diagnostics=["data_profile.json", "psm_diagnostics.json", "did_diagnostics.csv from drdid when available", "model_table.csv"],
        outputs=["method_card.json", "workflow_blueprint.md", "workflow_validation.json", "dependency_report.json", "step_results.json", "warnings.json", "model_table.csv", "research_report.md", "rerun.bat", "rerun.sh"],
        failure_conditions=["missing required columns", "duplicated id-time panel cells", "no treated/control variation", "DID baseline estimator failure"],
        tonight_scope="Paper-run orchestration over existing audited PSM, TWFE DID, and DRDID methods. It does not yet construct a matched panel dataset for matched-sample DID.",
        claim_limits=[
            "PSM is reported as overlap/legacy support, not as proof of selection-on-observables.",
            "PS/matching only addresses observed covariate support and balance.",
            "DID identification still requires conditional parallel trends.",
            "DRDID is covariate-adjusted DID, not automatic causality after matching.",
            "The paper-grade 2x2 causal estimator is DRDID when the declared sample is valid.",
            "Multi-period or staggered policy designs should use did_paper_run/csdid before claiming paper-ready DID.",
        ],
        next_steps=["Add true matched-sample DID once matched IDs/weights are exported by psm_ipw_match.", "Add balance tables and standardized mean differences.", "Add placebo timing and alternative calipers."],
    )
    return _run_generic_paper_workflow(
        ctx,
        card=card,
        required_spec_fields=["data", "id", "time", "y", "treatment", "post", "controls"],
        column_fields=["id", "time", "y", "treatment", "post"],
        list_column_fields=["controls"],
        steps=_psm_did_policy_steps(ctx),
        extra_warnings=_psm_did_extra_warnings(ctx),
        postprocess=_psm_did_postprocess,
    )


def spatial_spillover_run(ctx: RunContext) -> WorkflowResult:
    card = _workflow_method_card(
        name="spatial_spillover_run",
        title="Spatial Spillover PolicyRun v0.1",
        why_p0="Shao/Tian-style environmental economics work commonly needs policy spillovers across neighboring cities/firms/provinces; the current robust core is reduced-form exposure DID.",
        input_fields=["data", "weights edge list", "id", "time", "y", "treat", "post", "x/covars", "cluster", "row_standardize", "include_wx"],
        estimators=["python.spatial_exposure_did for local-treatment and W*treatment exposure DID", "stata.spatial_panel_preflight for availability checks only"],
        diagnostics=["workflow_validation.json", "spatial_exposure_did.json", "spatial_exposure_panel.csv", "tables/spatial_exposure_summary.csv", "tables/contaminated_controls.csv", "model_table.csv", "Stata spatial package preflight"],
        outputs=["method_card.json", "workflow_blueprint.md", "workflow_validation.json", "dependency_report.json", "step_results.json", "warnings.json", "model_table.csv", "research_report.md", "rerun.bat", "rerun.sh"],
        failure_conditions=["missing data or weights", "weights missing source/target/weight columns", "zero row sum before standardization", "duplicated id-time panel cells", "reduced-form spatial DID failure"],
        tonight_scope="Paper-run wrapper around the tested reduced-form spatial exposure DID. Stata spxtregress live backend certification exists separately, but full SAR/SDM/SAC/xsmle estimation is not wired into this workflow and must not be claimed here.",
        claim_limits=["This estimates exposure/spillover associations with fixed effects, not structural SAR/SDM direct/indirect effects.", "Spatial endogeneity is not solved by this workflow.", "Use this as a strong first-pass spillover design and preflight for later full spatial econometrics."],
        next_steps=["Promote the certified spxtregress harness into an explicit structural spatial workflow without weakening reduced-form claim language.", "Add Moran's I/residual spatial autocorrelation diagnostics.", "Add alternative weight matrices and leave-one-neighbor sensitivity."],
    )
    return _run_generic_paper_workflow(
        ctx,
        card=card,
        required_spec_fields=["data", "weights", "id", "time", "y", "treatment", "post"],
        column_fields=["id", "time", "y", "treatment", "post"],
        list_column_fields=["controls"],
        file_fields=["weights"],
        steps=[
            {"label": "data_audit", "engine": "python", "method": "data_audit", "critical": False, "spec": _spec_with_treatment_aliases(ctx.spec)},
            {"label": "spatial_exposure_did", "engine": "python", "method": "spatial_exposure_did", "critical": True, "spec": _spec_with_treatment_aliases(ctx.spec)},
            {"label": "spatial_stata_preflight", "engine": "stata", "method": "spatial_panel_preflight", "critical": False, "spec": _spec_with_treatment_aliases(ctx.spec)},
        ],
    )


def _mechanism_threshold_steps(ctx: RunContext) -> list[dict[str, Any]]:
    mediation_spec = _spec_with_treatment_aliases(ctx.spec)
    threshold_spec = _spec_with_treatment_aliases(ctx.spec)
    quantile_spec = _spec_with_treatment_aliases(ctx.spec)
    controls = listify(ctx.spec.get("controls") or ctx.spec.get("x") or ctx.spec.get("covars"))
    treatment = ctx.spec.get("treatment") or ctx.spec.get("treat")
    quantile_x = list(dict.fromkeys([str(treatment), *controls])) if treatment else controls
    quantile_spec["x"] = [item for item in quantile_x if item]
    return [
        {"label": "data_audit", "engine": "python", "method": "data_audit", "critical": False, "spec": _spec_with_treatment_aliases(ctx.spec)},
        {"label": "mediation", "engine": "python", "method": "mediation_moderation", "critical": True, "spec": mediation_spec},
        {"label": "threshold", "engine": "python", "method": "threshold_panel", "critical": True, "spec": threshold_spec},
        {"label": "quantile_heterogeneity", "engine": "python", "method": "quantile_regression", "critical": False, "spec": quantile_spec},
    ]


def mechanism_threshold_run(ctx: RunContext) -> WorkflowResult:
    card = _workflow_method_card(
        name="mechanism_threshold_run",
        title="Mechanism/Threshold PolicyRun v0.1",
        why_p0="Environmental economics papers usually need mechanism channels, heterogeneity, and nonlinear threshold checks after the baseline effect.",
        input_fields=["data", "id", "time", "y", "treat or treatment", "mediator", "threshold/q", "x/covars", "optional tau/quantile"],
        estimators=["python.mediation_moderation for Baron-Kenny style mechanism screening", "python.threshold_panel for fixed-effect threshold grid search", "python.quantile_regression for distributional heterogeneity screening"],
        diagnostics=["workflow_validation.json", "threshold_scan.json", "model_table.csv", "warnings.json"],
        outputs=["method_card.json", "workflow_blueprint.md", "workflow_validation.json", "dependency_report.json", "step_results.json", "warnings.json", "model_table.csv", "research_report.md", "rerun.bat", "rerun.sh"],
        failure_conditions=["missing mediator/threshold columns", "duplicated id-time panel cells", "too few threshold candidates", "mediation or threshold estimator failure"],
        tonight_scope="A reusable mechanism and nonlinear screening workflow. It is not a full causal mediation package with bootstrap or sequential ignorability proof.",
        claim_limits=["Mediation output is mechanism-consistency evidence, not definitive causal mediation.", "Threshold search reports the best grid threshold; Hansen-style bootstrap inference is not included tonight.", "Quantile regression lacks clustered/bootstrap inference in v0.1."],
        next_steps=["Add bootstrap/Sobel-style mediation uncertainty.", "Add Hansen threshold bootstrap and confidence region.", "Add subgroup/interaction FE robustness cards."],
    )
    return _run_generic_paper_workflow(
        ctx,
        card=card,
        required_spec_fields=["data", "id", "time", "y", "treatment", "mediator", "threshold", "controls"],
        column_fields=["id", "time", "y", "treatment", "mediator", "threshold"],
        list_column_fields=["controls"],
        steps=_mechanism_threshold_steps(ctx),
    )


def _dea_extra_warnings(ctx: RunContext) -> list[dict[str, Any]]:
    params = ctx.spec.get("dea") or {}
    required = ["dmus", "periods", "nx", "ny", "nb", "undesirable", "sup"]
    missing = [key for key in required if key not in params]
    if not missing:
        return []
    return [
        _warning(
            "red",
            "missing_dea_params",
            f"DEA workflow requires dea params: {missing}.",
            action="Provide dea: {dmus, periods, nx, ny, nb, undesirable, sup}.",
        )
    ]


def efficiency_frontier_run(ctx: RunContext) -> WorkflowResult:
    card = _workflow_method_card(
        name="efficiency_frontier_run",
        title="Efficiency/Frontier PolicyRun v0.1",
        why_p0="Carbon efficiency, green total factor productivity, DEA-SBM, and Malmquist indices are central in environmental economics; the user already has a local DEA codebase, so this workflow is adapter-first.",
        input_fields=["data XLSX", "dea.dmus", "dea.periods", "dea.nx", "dea.ny", "dea.nb", "dea.undesirable", "dea.sup", "optional dea.backend_path"],
        estimators=["python.dea_sbm_malmquist_adapter using vendored or configured local DEA backend"],
        diagnostics=["workflow_validation.json", "adapter audit", "backend result manifest"],
        outputs=["method_card.json", "workflow_blueprint.md", "workflow_validation.json", "dependency_report.json", "step_results.json", "warnings.json", "model_table.csv", "research_report.md", "rerun.bat", "rerun.sh"],
        failure_conditions=["missing XLSX input", "missing DEA dimensions", "external DEA backend failure", "vendored DEA backend failure"],
        tonight_scope="Workflow-level adapter and validation only. No hard rebuild of SFA/DEA/Malmquist internals.",
        claim_limits=["DEA math is delegated to the configured backend; inspect backend artifacts before paper claims.", "Second-stage regressions on efficiency scores are not included in this workflow.", "SFA remains interface-only/P2 until a tested local backend is selected."],
        next_steps=["Add second-stage FE/Tobit/bootstrap regression workflow for DEA scores.", "Add backend selection between D:/myproject/dea_calculator and vendored engine.", "Add Malmquist panel diagnostics and bad-output sign checks."],
    )
    return _run_generic_paper_workflow(
        ctx,
        card=card,
        required_spec_fields=["data"],
        column_fields=[],
        list_column_fields=[],
        steps=[
            {"label": "dea_adapter", "engine": "python", "method": "dea_sbm_malmquist_adapter", "critical": True, "spec": dict(ctx.spec)}
        ],
        extra_warnings=_dea_extra_warnings(ctx),
    )


def did_paper_run(ctx: RunContext) -> WorkflowResult:
    if ctx.state == "plan":
        messages = [
            "DID PaperRun v0.1 plans a paper-oriented DID workflow.",
            "Run state is required for data preflight, estimation, reports, and artifacts.",
        ]
        write_audit(ctx, "planned", messages)
        return write_manifest(ctx, "planned", workflow="did_paper_run")

    dep_report = dependency_report()
    write_json(ctx.artifact("dependency_report.json"), dep_report)
    try:
        prepared = _prepare_did_inputs(ctx)
    except Exception as exc:
        write_audit(ctx, "failed", [str(exc)], error_type=exc.__class__.__name__)
        return write_manifest(
            ctx,
            "failed",
            workflow="did_paper_run",
            error=str(exc),
            error_type=exc.__class__.__name__,
        )

    warnings = list(prepared.get("warnings", []))
    step_results: list[dict[str, Any]] = []
    if ctx.state in {"dry-run", "audit"}:
        status = "validated" if prepared.get("can_run") else "failed"
        _write_robustness_plan(ctx, str(prepared.get("design_type", "")))
        _render_report(ctx, prepared, status, step_results, warnings)
        _write_rerun_scripts(ctx)
        write_audit(ctx, status, [f"DID PaperRun {ctx.state} completed."], warnings=warnings)
        return write_manifest(
            ctx,
            status,
            workflow="did_paper_run",
            warnings=warnings,
            spec_sha256=_json_hash(ctx.spec),
            data_sha256=prepared.get("data_summary", {}).get("data_sha256"),
        )

    if not prepared.get("can_run"):
        _write_robustness_plan(ctx, str(prepared.get("design_type", "")))
        _render_report(ctx, prepared, "failed", step_results, warnings)
        _write_rerun_scripts(ctx)
        write_audit(ctx, "failed", ["DID PaperRun preflight blocked estimation."], warnings=warnings)
        return write_manifest(
            ctx,
            "failed",
            workflow="did_paper_run",
            warnings=warnings,
            spec_sha256=_json_hash(ctx.spec),
            data_sha256=prepared.get("data_summary", {}).get("data_sha256"),
        )

    routing = route_did_estimators(
        prepared.get("did_design") or {},
        spec=ctx.spec,
        dependency_report=dep_report,
    )
    write_estimator_routing(ctx.run_dir, routing)
    did_design = prepared.get("did_design") or {}
    write_json(
        ctx.artifact("did_claim_contract.json"),
        {
            "estimand_scope": "ATT(g,t)" if prepared.get("design_type") == "staggered_adoption_did" else "simple_ATT",
            "control_group": ctx.spec.get("control_group") or ("never_treated" if did_design.get("has_never_treated") else "not_yet_treated"),
            "cohort_support": {
                "n_treated_cohorts": did_design.get("n_treated_cohorts"),
                "first_treat_years": did_design.get("first_treat_years") or [],
                "min_pre_periods_by_cohort": did_design.get("min_pre_periods_by_cohort") or {},
                "min_post_periods_by_cohort": did_design.get("min_post_periods_by_cohort") or {},
            },
            "event_time_support": prepared.get("event_support_rows") or [],
            "anticipation_periods": int(ctx.spec.get("anticipation_periods") or 0),
            "aggregation_method": "cohort_time" if prepared.get("design_type") == "staggered_adoption_did" else "simple",
            "main_estimand": "ATT(g,t)" if prepared.get("design_type") == "staggered_adoption_did" else "simple_ATT",
            "twfe_role": "forbidden_for_main" if prepared.get("design_type") == "staggered_adoption_did" else "comparison_or_main_by_design",
            "cluster_variable": prepared.get("cluster"),
            "cluster_count": (prepared.get("data_summary") or {}).get("cluster_count"),
            "pretrend_test_role": "diagnostic_only",
        },
    )
    if not routing.get("selected_estimators"):
        warnings.append(
            _warning(
                "red",
                "no_did_estimator_selected",
                "Estimator router did not select any runnable DID estimator.",
                action="Inspect selected_estimators.json and skipped_estimators.json; configure Python/Stata/R backends or estimators.",
            )
        )

    for seq, selected in enumerate(routing.get("selected_estimators") or [], 1):
        spec = _routed_did_step_spec(ctx, prepared, selected)
        result = _run_step(ctx, str(selected["engine"]), str(selected["method"]), seq, spec)
        result["label"] = selected.get("estimator", result["method"])
        result["critical"] = bool(selected.get("critical", True))
        result["router"] = selected
        estimator_name = str(selected.get("estimator") or result["label"])
        did_design = prepared.get("did_design") or {}
        cohort_support = {
            "n_treated_cohorts": did_design.get("n_treated_cohorts"),
            "first_treat_years": did_design.get("first_treat_years") or [],
            "min_pre_periods_by_cohort": did_design.get("min_pre_periods_by_cohort") or {},
            "min_post_periods_by_cohort": did_design.get("min_post_periods_by_cohort") or {},
        }
        event_time_support = {
            str(row.get("event_time")): {
                "observations": row.get("observations"),
                "treated_entities": row.get("treated_entities"),
                "calendar_periods": row.get("calendar_periods"),
            }
            for row in prepared.get("event_support_rows", [])
        }
        twfe_role = "not_used"
        if estimator_name in {"twfe", "event_study_twfe"}:
            twfe_role = "main" if bool(selected.get("main_allowed")) else "comparison_only"
            if prepared.get("design_type") == "staggered_adoption_did" and not bool(selected.get("main_allowed")):
                twfe_role = "forbidden_for_main"
        aggregation_method = "event_time" if estimator_name == "event_study_twfe" else ("cohort_time" if estimator_name in {"cs_did_attgt", "csdid", "did_imputation"} else "simple")
        main_estimand = "event_time_ATT" if estimator_name == "event_study_twfe" else ("ATT(g,t)" if estimator_name in {"cs_did_attgt", "csdid", "did_imputation"} else "simple_ATT")
        common = build_common_output(
            estimator=str(result["label"]),
            design_type=str((prepared.get("did_design") or {}).get("design_type") or prepared.get("design_type") or ""),
            step_dir=Path(str(result["run_dir"])),
            status=str(result.get("status") or "unknown"),
            manifest=result.get("manifest") or {},
            spec=spec,
            backend=str(selected.get("backend") or ""),
            engine=str(selected.get("engine") or ""),
            role=str(selected.get("role") or ""),
            control_group=ctx.spec.get("control_group") or ("never_treated" if (prepared.get("did_design") or {}).get("has_never_treated") else "not_yet_treated"),
            cohort_support=cohort_support,
            event_time_support=event_time_support,
            anticipation_periods=int(ctx.spec.get("anticipation_periods") or 0),
            aggregation_method=aggregation_method,
            main_estimand=main_estimand,
            twfe_role=twfe_role,
            cluster_variable=prepared.get("cluster"),
            cluster_count=int((prepared.get("data_summary") or {}).get("cluster_count") or 0),
            pretrend_test_role="diagnostic_only",
        )
        write_common_output(Path(str(result["run_dir"])), common)
        result["did_common_output"] = str(Path(str(result["run_dir"])) / "did_common_output.json")
        step_results.append(result)
        if not _step_status_ok(result):
            warnings.append(
                _warning(
                    "red" if result["critical"] else "yellow",
                    f"{result['label']}_failed",
                    f"{result['engine']}.{result['method']} returned status `{result['status']}`.",
                    action="Inspect the step manifest/log; no fallback estimator was substituted.",
                )
            )

    combined = _collect_model_tables(ctx, step_results, prepared=prepared)
    event_rows = [
        row
        for row in combined
        if row.get("model") == "did_event_study" and _parse_event_term(str(row.get("term", ""))) is not None
    ]
    event_study_path = _write_event_study_table(ctx, event_rows)
    pretrend_path = _write_pretrend_test(ctx, event_rows, int(prepared.get("base_period") or -1))
    figure = _write_event_plot(ctx, event_rows)
    figure_manifest = _write_figure_manifest(ctx, [figure])
    event_requested = any(item.get("estimator") == "event_study_twfe" for item in routing.get("selected_estimators") or [])
    if event_requested and not figure:
        warnings.append(
            _warning(
                "yellow",
                "event_plot_not_generated",
                "Event-study plot was not generated because usable event coefficients or matplotlib were unavailable.",
            )
        )
    else:
        event_support = prepared.get("event_support_rows", [])
        present_terms = {_parse_event_term(str(row.get("term", ""))) for row in event_rows}
        for support in event_support:
            support["present_in_model_table"] = support.get("event_time") in present_terms
        _write_csv(ctx.artifact("event_study_support.csv"), event_support)

    comparison_rows, comparison_warnings = build_did_estimator_comparison(
        run_dir=ctx.run_dir,
        step_results=step_results,
        routing=routing,
        did_design=prepared.get("did_design") or {},
        spec=ctx.spec,
    )
    placebo_path, placebo_warnings, placebo_computed = _write_placebo_tests(ctx, prepared)
    heterogeneity_path, heterogeneity_warnings, heterogeneity_computed = _write_heterogeneity(ctx, prepared)
    robustness_grid = _write_robustness_grid(
        ctx,
        step_results=step_results,
        comparison_rows=comparison_rows,
        prepared=prepared,
        diagnostic_artifacts={
            "placebo_timing": placebo_path if placebo_computed else None,
            "subgroup_heterogeneity": heterogeneity_path if heterogeneity_computed else None,
        },
    )
    warnings.extend(comparison_warnings)
    warnings.extend(placebo_warnings)
    warnings.extend(heterogeneity_warnings)

    critical_failed = any(step.get("critical") and not _step_status_ok(step) for step in step_results)
    optional_failed = any((not step.get("critical")) and not _step_status_ok(step) for step in step_results)
    successful_labels = {str(step.get("label")) for step in step_results if _step_status_ok(step)}
    successful_modern = successful_labels.intersection({"cs_did_attgt", "csdid", "did_imputation", "drdid"})
    if not step_results:
        status = "failed"
    elif critical_failed:
        status = "not_paper_ready"
    elif prepared.get("design_type") == "staggered_adoption_did" and not successful_modern:
        status = "not_paper_ready"
        warnings.append(
            _warning(
                "red",
                "staggered_did_without_alternative_estimator",
                "Staggered adoption DID did not produce a successful modern DID estimator, so TWFE-only output is not a complete PaperRun.",
                action="Install/enable Stata csdid/drdid or rerun with a supported staggered estimator.",
            )
        )
    elif optional_failed:
        status = "degraded"
    else:
        status = "success"

    warnings.append(
        _warning(
            "green",
            "workflow_completed",
            "The workflow generated diagnostics and recorded all model statuses.",
        )
    )
    write_json(ctx.artifact("warnings.json"), {"warnings": warnings})
    write_json(ctx.artifact("did_diagnostics.json"), {"warnings": warnings})
    write_json(ctx.artifact("step_results.json"), {"steps": step_results})
    _write_robustness_plan(ctx, str(prepared.get("design_type", "")))
    _render_report(ctx, prepared, status, step_results, warnings)
    _write_rerun_scripts(ctx)
    audit_status = "ok" if status in {"success", "degraded"} else status
    write_audit(
        ctx,
        audit_status,
        [f"DID PaperRun completed with workflow status: {status}."],
        warnings=warnings,
        steps=step_results,
    )
    return write_manifest(
        ctx,
        status,
        workflow="did_paper_run",
        spec_sha256=_json_hash(ctx.spec),
        data_sha256=prepared.get("data_summary", {}).get("data_sha256"),
        warnings=warnings,
        steps=step_results,
        evidence_artifacts={
            "event_study": event_study_path,
            "pretrend_test": pretrend_path,
            "robustness_grid": robustness_grid,
            "figure_manifest": figure_manifest,
            "placebo_tests": placebo_path,
            "heterogeneity": heterogeneity_path,
        },
    )


WORKFLOWS = {
    "did_paper_run": did_paper_run,
    "efficiency_frontier_run": efficiency_frontier_run,
    "mechanism_threshold_run": mechanism_threshold_run,
    "psm_did_policy_run": psm_did_policy_run,
    "spatial_spillover_run": spatial_spillover_run,
}
