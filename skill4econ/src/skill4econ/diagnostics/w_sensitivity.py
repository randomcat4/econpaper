from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .spatial_exposure import run_spatial_exposure_did


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _plot_forest(rows: list[dict[str, Any]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plot_rows = [row for row in rows if row.get("term") == "_spatial_exposure" and row.get("coef") == row.get("coef")]
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, max(3, 0.45 * max(len(plot_rows), 1) + 1.2)))
    if not plot_rows:
        plt.text(0.5, 0.5, "No W sensitivity estimates", ha="center", va="center")
        plt.axis("off")
    else:
        y = list(range(len(plot_rows)))
        coef = [float(row["coef"]) for row in plot_rows]
        se = [float(row.get("std_error") or math.nan) for row in plot_rows]
        err = [1.96 * value if math.isfinite(value) else 0.0 for value in se]
        labels = [str(row.get("w_label") or row.get("weight_path")) for row in plot_rows]
        plt.axvline(0, color="#777777", linewidth=1)
        plt.errorbar(coef, y, xerr=err, fmt="o", capsize=2)
        plt.yticks(y, labels, fontsize=8)
        plt.xlabel("Spatial exposure coefficient")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _sign(values: list[float]) -> set[int]:
    result = set()
    for value in values:
        if not math.isfinite(value) or value == 0:
            continue
        result.add(1 if value > 0 else -1)
    return result


def run_w_sensitivity(df: Any, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    tables = out / "tables"
    figures = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    paths = spec.get("weight_paths") or spec.get("w_paths") or []
    if isinstance(paths, str):
        paths = [paths]
    primary = spec.get("weights") or spec.get("weight_matrix") or spec.get("w_path")
    if primary:
        paths = [primary, *paths]
    labels = spec.get("weight_labels") or []
    if isinstance(labels, str):
        labels = [labels]
    unique_paths = []
    for path in paths:
        text = str(path)
        if text and text not in unique_paths:
            unique_paths.append(text)
    if len(unique_paths) < 2:
        raise ValueError("W sensitivity requires at least two weight paths; provide weights plus weight_paths.")

    rows: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for idx, path in enumerate(unique_paths, 1):
        label = str(labels[idx - 1]) if idx - 1 < len(labels) else f"W{idx}"
        subdir = out / f"w_{idx:02d}_{label}"
        sub_spec = dict(spec)
        sub_spec["weights"] = path
        result = run_spatial_exposure_did(df, path, sub_spec, subdir)
        run_summaries.append({"label": label, "path": path, "status": "ok", "run_dir": str(subdir), "warnings": result.get("warnings") or []})
        for row in result.get("rows") or []:
            if row.get("term") not in {"_local_treatment", "_spatial_exposure"}:
                continue
            rows.append({**row, "w_label": label, "weight_path": path, "run_dir": str(subdir)})

    local = [float(row["coef"]) for row in rows if row.get("term") == "_local_treatment" and row.get("coef") is not None]
    spill = [float(row["coef"]) for row in rows if row.get("term") == "_spatial_exposure" and row.get("coef") is not None]
    pvals = [float(row["p_value"]) for row in rows if row.get("p_value") not in {None, ""} and str(row.get("p_value")) != "nan"]
    if len(_sign(local)) > 1 or len(_sign(spill)) > 1:
        warnings.append(
            {
                "severity": "red",
                "code": "W_SENSITIVITY_SIGN_FLIP",
                "message": "Local or spillover effect signs flip across alternative spatial weight matrices.",
                "action": "Report W sensitivity and avoid treating one W definition as decisive.",
            }
        )
    sig = {value < 0.05 for value in pvals if math.isfinite(value)}
    if len(sig) > 1:
        warnings.append(
            {
                "severity": "yellow",
                "code": "W_SENSITIVITY_SIGN_FLIP",
                "message": "5% significance status changes across W matrices.",
                "action": "Report W sensitivity significance instability.",
            }
        )

    _write_csv(tables / "w_sensitivity_main_effects.csv", rows)
    _plot_forest(rows, figures / "w_sensitivity_forest.png")
    payload = {
        "status": "ok",
        "n_weights": len(unique_paths),
        "warnings": warnings,
        "runs": run_summaries,
        "rows": rows,
        "artifacts": {
            "main_effects": "tables/w_sensitivity_main_effects.csv",
            "forest": "figures/w_sensitivity_forest.png",
        },
    }
    (out / "w_sensitivity.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
