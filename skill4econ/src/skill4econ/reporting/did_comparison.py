from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "estimator",
        "estimand",
        "control_group",
        "estimate",
        "std_error",
        "ci_low",
        "ci_high",
        "p_value",
        "n_obs",
        "fixed_effects",
        "cluster",
        "backend",
        "engine",
        "status",
        "recommended_role",
        "source_path",
        "note",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _as_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _first_effect_row(table: list[dict[str, Any]], estimator: str) -> dict[str, Any] | None:
    if not table:
        return None
    preferred_terms = {
        "twfe": ["_did_treat_post", "treat_post", "treatment_post"],
        "drdid": ["ATT", "att", "treatment"],
        "cs_did_attgt": ["ATT", "simple", "overall", "Pre_avg", "Post_avg"],
        "csdid": ["ATT", "treatment"],
        "did_imputation": ["tau", "treatment", "event_0"],
    }.get(estimator, [])
    for term in preferred_terms:
        for row in table:
            if str(row.get("term", "")).lower() == term.lower():
                return row
    for row in table:
        if _as_float(row.get("coef")) is not None:
            return row
    return None


def _ci(estimate: float | None, se: float | None) -> tuple[float | None, float | None]:
    if estimate is None or se is None:
        return None, None
    return estimate - 1.96 * se, estimate + 1.96 * se


def _role_for(selected: list[dict[str, Any]], estimator: str) -> str:
    for item in selected:
        if item.get("estimator") == estimator:
            return str(item.get("role") or "")
    return ""


def _load_common_output(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["estimator", "estimate", "std_error", "p_value", "status", "recommended_role"]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for key in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_forest(path: Path, rows: list[dict[str, Any]]) -> bool:
    plottable = [
        row
        for row in rows
        if _as_float(row.get("estimate")) is not None and _as_float(row.get("std_error")) is not None
    ]
    if not plottable:
        return False
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    estimates = [_as_float(row.get("estimate")) or 0.0 for row in plottable]
    errors = [1.96 * (_as_float(row.get("std_error")) or 0.0) for row in plottable]
    labels = [str(row.get("estimator")) for row in plottable]
    y = list(range(len(plottable)))
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, max(3, 0.45 * len(plottable) + 1.2)))
    plt.axvline(0, color="#666666", linewidth=1)
    plt.errorbar(estimates, y, xerr=errors, fmt="o", capsize=3, color="#1f77b4")
    plt.yticks(y, labels)
    plt.xlabel("Estimate with 95% CI")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return True


def build_did_estimator_comparison(
    *,
    run_dir: Path,
    step_results: list[dict[str, Any]],
    routing: dict[str, Any],
    did_design: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = list(routing.get("selected_estimators") or [])
    selected_by_label = {
        item.get("label") or item.get("estimator"): item
        for item in selected
    }
    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for step in step_results:
        label = str(step.get("label") or step.get("method"))
        selected_item = selected_by_label.get(label, {})
        estimator = str(selected_item.get("estimator") or label)
        step_dir = Path(str(step.get("run_dir")))
        common = _load_common_output(Path(str(step.get("did_common_output") or step_dir / "did_common_output.json")))
        if common:
            main = common.get("main_effect") if isinstance(common.get("main_effect"), dict) else {}
            estimate = _as_float(main.get("estimate"))
            se = _as_float(main.get("std_error"))
            ci_low = _as_float(main.get("ci_low"))
            ci_high = _as_float(main.get("ci_high"))
            p_value = main.get("p_value")
            source_path = main.get("source_path") or common.get("dynamic_effects_path") or str(step_dir / "model_table.csv")
            note = common.get("note") or ""
        else:
            table = _read_csv(step_dir / "model_table.csv")
            effect = _first_effect_row(table, estimator)
            estimate = _as_float((effect or {}).get("coef"))
            se = _as_float((effect or {}).get("std_error"))
            ci_low, ci_high = _ci(estimate, se)
            p_value = (effect or {}).get("p_value")
            source_path = str(step_dir / "model_table.csv")
            note = "" if effect else "No numeric main-effect row parsed from model_table.csv."
        rows.append(
            {
                "estimator": estimator,
                "estimand": "ATT" if estimator not in {"event_study_twfe"} else "dynamic",
                "control_group": spec.get("control_group") or ("never_treated" if did_design.get("has_never_treated") else "not_yet_treated"),
                "estimate": estimate,
                "std_error": se,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "p_value": p_value,
                "n_obs": (step.get("manifest") or {}).get("nobs") or (step.get("manifest") or {}).get("N"),
                "fixed_effects": "unit,time",
                "cluster": spec.get("cluster") or spec.get("id"),
                "backend": selected_item.get("backend") or (step.get("manifest") or {}).get("backend"),
                "engine": step.get("engine"),
                "status": step.get("status"),
                "recommended_role": _role_for(selected, estimator),
                "source_path": source_path,
                "note": note,
            }
        )

    for skipped in routing.get("skipped_estimators") or []:
        rows.append(
            {
                "estimator": skipped.get("estimator"),
                "estimand": "",
                "control_group": "",
                "estimate": None,
                "std_error": None,
                "ci_low": None,
                "ci_high": None,
                "p_value": None,
                "n_obs": None,
                "fixed_effects": "",
                "cluster": spec.get("cluster") or spec.get("id"),
                "backend": skipped.get("backend"),
                "engine": "",
                "status": "skipped",
                "recommended_role": skipped.get("role"),
                "source_path": "",
                "note": skipped.get("reason"),
            }
        )

    table_path = run_dir / "tables" / "did_estimator_comparison.csv"
    md_path = run_dir / "tables" / "did_estimator_comparison.md"
    fig_path = run_dir / "figures" / "did_estimator_forest.png"
    _write_csv(table_path, rows)
    _write_markdown(md_path, rows)
    _write_forest(fig_path, rows)

    twfe = [row for row in rows if row.get("estimator") == "twfe" and _as_float(row.get("estimate")) is not None]
    twfe_like = {"twfe", "event_study_twfe", "spatial_exposure_local_twfe"}
    modern = [
        row
        for row in rows
        if row.get("estimator") not in twfe_like
        and row.get("status") not in {"skipped", "failed"}
        and _as_float(row.get("estimate")) is not None
    ]
    if twfe and modern:
        twfe_sign = math.copysign(1, _as_float(twfe[0]["estimate"]) or 0.0)
        for row in modern:
            estimate = _as_float(row.get("estimate")) or 0.0
            if estimate and math.copysign(1, estimate) != twfe_sign:
                warnings.append(
                    {
                        "severity": "red",
                        "code": "twfe_modern_did_disagree",
                        "message": f"TWFE and {row.get('estimator')} have opposite signs.",
                        "action": "Treat TWFE as benchmark only and explain estimator disagreement.",
                    }
                )
                break
    if did_design.get("design_type") == "staggered_adoption":
        successful_modern = [
            row
            for row in modern
            if row.get("estimator") in {"cs_did_attgt", "csdid", "did_imputation", "did_r_att_gt"}
            and row.get("status") == "ok"
        ]
        if not successful_modern:
            warnings.append(
                {
                    "severity": "red",
                    "code": "twfe_staggered_heterogeneity",
                    "message": "TWFE is the only successful DID estimate for a staggered adoption design.",
                    "action": "Report CS/BJS/Sun-Abraham style estimates before claiming a paper-ready DID result.",
                }
            )
    return rows, warnings
