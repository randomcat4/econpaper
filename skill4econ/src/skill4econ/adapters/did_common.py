from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def as_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def ci95(estimate: float | None, se: float | None) -> tuple[float | None, float | None]:
    if estimate is None or se is None:
        return None, None
    return estimate - 1.96 * se, estimate + 1.96 * se


def choose_main_effect(estimator: str, step_dir: Path) -> dict[str, Any] | None:
    sources = []
    if estimator in {"cs_did_attgt", "csdid"}:
        sources.append(step_dir / "simple_att.csv")
    sources.append(step_dir / "model_table.csv")
    preferred_terms = {
        "twfe": {"_did_treat_post", "treat_post", "treatment_post"},
        "event_study_twfe": {"Post_avg", "event_0", "_event_0", "event_1", "_event_1"},
        "drdid": {"ATT", "att", "treatment"},
        "cs_did_attgt": {"ATT", "simple_att", "Post_avg"},
        "csdid": {"ATT", "simple_att", "Post_avg"},
        "did_imputation": {"tau0", "tau1", "treatment"},
    }.get(estimator, set())
    for source in sources:
        table = read_csv_rows(source)
        if not table:
            continue
        for row in table:
            term = str(row.get("term") or "")
            if term in preferred_terms and as_float(row.get("coef")) is not None:
                return {**row, "_source": str(source)}
        for row in table:
            if as_float(row.get("coef")) is not None:
                return {**row, "_source": str(source)}
    return None


def dynamic_effects_path(estimator: str, step_dir: Path) -> str | None:
    candidates = {
        "cs_did_attgt": ["event_study.csv"],
        "csdid": ["event_study.csv"],
        "did_imputation": ["event_study.csv"],
        "event_study_twfe": ["model_table.csv"],
    }.get(estimator, [])
    for name in candidates:
        path = step_dir / name
        if path.exists():
            return str(path)
    return None


def group_time_path(estimator: str, step_dir: Path) -> str | None:
    candidates = {
        "cs_did_attgt": ["att_gt.csv"],
        "csdid": ["att_gt.csv"],
        "drdid": ["group_time_summary.csv"],
    }.get(estimator, [])
    for name in candidates:
        path = step_dir / name
        if path.exists():
            return str(path)
    return None


def build_common_output(
    *,
    estimator: str,
    design_type: str,
    step_dir: Path,
    status: str,
    manifest: dict[str, Any] | None = None,
    spec: dict[str, Any] | None = None,
    backend: str | None = None,
    engine: str | None = None,
    role: str | None = None,
    control_group: str | None = None,
    cohort_support: dict[str, Any] | None = None,
    event_time_support: dict[str, Any] | None = None,
    anticipation_periods: int | None = None,
    aggregation_method: str | None = None,
    main_estimand: str | None = None,
    twfe_role: str | None = None,
    cluster_variable: str | None = None,
    cluster_count: int | None = None,
    pretrend_test_role: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    manifest = manifest or {}
    spec = spec or {}
    effect = choose_main_effect(estimator, step_dir)
    estimate = as_float((effect or {}).get("coef"))
    se = as_float((effect or {}).get("std_error"))
    ci_low, ci_high = ci95(estimate, se)
    log_candidates = [step_dir / "stata.log", step_dir / "run.log", step_dir / "stdout.log"]
    raw_output = next((str(path) for path in log_candidates if path.exists()), None)
    return {
        "estimator": estimator,
        "estimand": main_estimand or ("ATT" if estimator != "event_study_twfe" else "dynamic_ATT"),
        "estimand_scope": main_estimand or ("event_time_ATT" if estimator == "event_study_twfe" else "simple_ATT"),
        "design_type": design_type,
        "n_obs": manifest.get("nobs") or manifest.get("N"),
        "n_units": manifest.get("n_units"),
        "n_periods": manifest.get("n_periods"),
        "control_group": control_group or spec.get("control_group"),
        "cohort_support": cohort_support or {},
        "event_time_support": event_time_support or {},
        "anticipation_periods": int(anticipation_periods or 0),
        "aggregation_method": aggregation_method or ("event_time" if estimator == "event_study_twfe" else "simple"),
        "main_estimand": main_estimand or ("dynamic_ATT" if estimator == "event_study_twfe" else "ATT"),
        "twfe_role": twfe_role or ("comparison_only" if estimator in {"twfe", "event_study_twfe"} and design_type.startswith("staggered") else ("main" if estimator == "twfe" else "not_used")),
        "cluster_variable": cluster_variable or spec.get("cluster"),
        "cluster_count": cluster_count,
        "pretrend_test_role": pretrend_test_role or ("diagnostic_only" if estimator == "event_study_twfe" else "not_used"),
        "main_effect": {
            "estimate": estimate,
            "std_error": se,
            "p_value": as_float((effect or {}).get("p_value")),
            "ci_low": ci_low,
            "ci_high": ci_high,
            "term": (effect or {}).get("term"),
            "source_path": (effect or {}).get("_source"),
        },
        "dynamic_effects_path": dynamic_effects_path(estimator, step_dir),
        "group_time_effects_path": group_time_path(estimator, step_dir),
        "raw_output_path": raw_output,
        "backend": backend or manifest.get("backend"),
        "engine": engine,
        "role": role,
        "status": "success" if status == "ok" else status,
        "note": note,
    }


def write_common_output(step_dir: Path, payload: dict[str, Any]) -> Path:
    path = step_dir / "did_common_output.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def skipped_backend_unavailable(
    *,
    estimator: str,
    design_type: str,
    backend: str,
    message: str,
) -> dict[str, Any]:
    return {
        "estimator": estimator,
        "estimand": "ATT",
        "design_type": design_type,
        "n_obs": None,
        "n_units": None,
        "n_periods": None,
        "control_group": None,
        "main_effect": {
            "estimate": None,
            "std_error": None,
            "p_value": None,
            "ci_low": None,
            "ci_high": None,
            "term": None,
            "source_path": None,
        },
        "dynamic_effects_path": None,
        "group_time_effects_path": None,
        "raw_output_path": None,
        "backend": backend,
        "engine": None,
        "role": None,
        "status": "skipped_backend_unavailable",
        "note": message,
    }
