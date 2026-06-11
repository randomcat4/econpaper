from __future__ import annotations

import json
import math
import shutil
import subprocess
import zlib
from pathlib import Path
from typing import Any


def _moran_i(values: dict[Any, float], edges: list[dict[str, Any]]) -> float:
    units = [unit for unit, value in values.items() if value is not None and math.isfinite(float(value))]
    if len(units) < 3:
        return math.nan
    x = {unit: float(values[unit]) for unit in units}
    mean = sum(x.values()) / len(x)
    denom = sum((value - mean) ** 2 for value in x.values())
    if denom <= 0:
        return math.nan
    numerator = 0.0
    s0 = 0.0
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source not in x or target not in x:
            continue
        weight = float(edge["weight"])
        numerator += weight * (x[source] - mean) * (x[target] - mean)
        s0 += weight
    if s0 <= 0:
        return math.nan
    return float(len(x) / s0 * numerator / denom)


def _local_moran_rows(
    values: dict[Any, float],
    edges: list[dict[str, Any]],
    *,
    year: Any,
    variable: str,
    permutations: int = 99,
    random_seed: int = 20260610,
    alpha: float = 0.05,
) -> list[dict[str, Any]]:
    import numpy as np

    units = [unit for unit, value in values.items() if value is not None and math.isfinite(float(value))]
    if len(units) < 3:
        return []
    x = {unit: float(values[unit]) for unit in units}
    mean = sum(x.values()) / len(x)
    centered = {unit: value - mean for unit, value in x.items()}
    m2 = sum(value**2 for value in centered.values()) / len(centered)
    if m2 <= 0:
        return []
    neighbors = {unit: [] for unit in units}
    degree = {unit: 0 for unit in units}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source not in centered or target not in centered:
            continue
        neighbors[source].append((target, float(edge["weight"])))
        degree[source] += 1

    def local_stats(centered_values: dict[Any, float]) -> tuple[dict[Any, float], dict[Any, float]]:
        lag = {unit: 0.0 for unit in units}
        local_i = {}
        for unit in units:
            lag[unit] = sum(weight * centered_values[target] for target, weight in neighbors[unit])
            local_i[unit] = float(centered_values[unit] * lag[unit] / m2)
        return local_i, lag

    observed_i, lag = local_stats(centered)
    permuted: dict[Any, list[float]] = {unit: [] for unit in units}
    if permutations > 0:
        seed_offset = zlib.crc32(f"{year}|{variable}".encode("utf-8")) % 1_000_000
        rng = np.random.default_rng(random_seed + seed_offset)
        unit_values = np.array([centered[unit] for unit in units], dtype=float)
        for _ in range(permutations):
            shuffled = rng.permutation(unit_values)
            perm_centered = {unit: float(value) for unit, value in zip(units, shuffled)}
            perm_i, _ = local_stats(perm_centered)
            for unit in units:
                permuted[unit].append(perm_i[unit])

    rows: list[dict[str, Any]] = []
    for unit in units:
        zi = centered[unit]
        lag_i = lag[unit]
        raw_quadrant = "undefined"
        if zi > 0 and lag_i > 0:
            raw_quadrant = "high_high"
        elif zi < 0 and lag_i < 0:
            raw_quadrant = "low_low"
        elif zi > 0 and lag_i < 0:
            raw_quadrant = "high_low"
        elif zi < 0 and lag_i > 0:
            raw_quadrant = "low_high"
        obs = observed_i[unit]
        perm_values = np.asarray(permuted[unit], dtype=float)
        if perm_values.size:
            expected_i = float(np.mean(perm_values))
            variance_i = float(np.var(perm_values, ddof=1)) if perm_values.size > 1 else math.nan
            z_i = float((obs - expected_i) / math.sqrt(variance_i)) if variance_i and variance_i > 0 else math.nan
            p_value = float((1 + np.sum(np.abs(perm_values) >= abs(obs))) / (perm_values.size + 1))
            p_value_available = True
            quadrant = raw_quadrant if p_value <= alpha else "not_significant"
        else:
            expected_i = variance_i = z_i = p_value = math.nan
            p_value_available = False
            quadrant = "not_tested"
        rows.append(
            {
                "year": year,
                "variable": variable,
                "unit": unit,
                "local_moran_i": obs,
                "expected_i": expected_i,
                "variance_i": variance_i,
                "z_i": z_i,
                "centered_value": float(zi),
                "spatial_lag_centered": float(lag_i),
                "neighbor_count": int(degree[unit]),
                "raw_quadrant": raw_quadrant,
                "quadrant": quadrant,
                "p_value": p_value,
                "p_value_available": p_value_available,
                "permutations": int(permutations),
                "backend": "python_basic_permutation" if permutations > 0 else "python_basic_no_permutation",
            }
        )
    return rows


def _read_edges(path: str | Path, spec: dict[str, Any]) -> list[dict[str, Any]]:
    import pandas as pd

    source = str(spec.get("source", "source"))
    target = str(spec.get("target", "target"))
    weight = str(spec.get("weight", "weight"))
    df = pd.read_csv(path)
    for col in [source, target]:
        if col not in df.columns:
            raise ValueError(f"Moran edge list missing column `{col}`.")
    if weight not in df.columns:
        df[weight] = 1.0
    return [
        {"source": row[source], "target": row[target], "weight": float(row[weight])}
        for row in df.to_dict("records")
        if row[source] != row[target]
    ]


def _twfe_residuals(df: Any, *, id_col: str, time_col: str, y_col: str) -> Any:
    work = df[[id_col, time_col, y_col]].copy()
    grand = work[y_col].mean()
    unit_mean = work.groupby(id_col)[y_col].transform("mean")
    time_mean = work.groupby(time_col)[y_col].transform("mean")
    return work[y_col] - unit_mean - time_mean + grand


def _plot_trend(rows: list[dict[str, Any]], path: Path, value_col: str = "moran_i") -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    valid = [row for row in rows if row.get(value_col) == row.get(value_col)]
    plt.figure(figsize=(7, 4))
    if valid:
        plt.plot([row["year"] for row in valid], [row[value_col] for row in valid], marker="o")
        plt.axhline(0, color="#777777", linewidth=1)
    else:
        plt.text(0.5, 0.5, "No valid Moran values", ha="center", va="center")
        plt.axis("off")
    plt.xlabel("Year")
    plt.ylabel("Moran's I")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def run_moran_preflight(df: Any, edge_list: str | Path, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    import pandas as pd

    out = Path(output_dir)
    tables = out / "tables"
    figures = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    y_col = str(spec.get("y") or spec.get("outcome") or "y")
    treat_col = str(spec.get("treat") or spec.get("treatment") or "treat")
    for col in [id_col, time_col, y_col, treat_col]:
        if col not in df.columns:
            raise ValueError(f"Moran preflight missing column `{col}`.")
    edges = _read_edges(edge_list, spec)
    work = df[[id_col, time_col, y_col, treat_col]].dropna().copy()
    work["_residual_twfe"] = _twfe_residuals(work, id_col=id_col, time_col=time_col, y_col=y_col)
    local_permutations = int(spec.get("local_moran_permutations", 99))
    local_alpha = float(spec.get("local_moran_alpha", 0.05))
    local_seed = int(spec.get("random_seed", 20260610))

    def rows_for(variable: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for year, group in work.groupby(time_col):
            values = dict(zip(group[id_col], group[variable]))
            rows.append({"year": year, "variable": variable, "moran_i": _moran_i(values, edges), "n_units": int(group[id_col].nunique())})
        return sorted(rows, key=lambda row: row["year"])

    outcome_rows = rows_for(y_col)
    treatment_rows = rows_for(treat_col)
    residual_rows = rows_for("_residual_twfe")
    local_rows: list[dict[str, Any]] = []
    if bool(spec.get("local_moran", True)):
        for variable in [y_col, treat_col, "_residual_twfe"]:
            for year, group in work.groupby(time_col):
                values = dict(zip(group[id_col], group[variable]))
                local_rows.extend(
                    _local_moran_rows(
                        values,
                        edges,
                        year=year,
                        variable=variable,
                        permutations=local_permutations,
                        random_seed=local_seed,
                        alpha=local_alpha,
                    )
                )
    pd.DataFrame(outcome_rows).to_csv(tables / "moran_outcome_by_year.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(treatment_rows).to_csv(tables / "moran_treatment_by_year.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(residual_rows).to_csv(tables / "moran_residual_by_year.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(local_rows).to_csv(tables / "local_moran_by_year.csv", index=False, encoding="utf-8-sig")
    _plot_trend(outcome_rows, figures / "moran_outcome_trend.png")
    _plot_trend(residual_rows, figures / "moran_residual_trend.png")

    max_treatment_moran = max((row["moran_i"] for row in treatment_rows if row["moran_i"] == row["moran_i"]), default=math.nan)
    warnings: list[dict[str, Any]] = []
    threshold = float(spec.get("treatment_moran_threshold", 0.30))
    if math.isfinite(max_treatment_moran) and max_treatment_moran > threshold:
        warnings.append(
            {
                "severity": "yellow",
                "code": "SPATIAL_TREATMENT_CLUSTERED",
                "message": f"Treatment Moran's I reaches {max_treatment_moran:.3f}.",
                "action": "Report spatial treatment clustering and consider spillover/exposure diagnostics.",
            }
        )
    if bool(spec.get("local_moran", True)) and local_permutations <= 0:
        warnings.append(
            {
                "severity": "yellow",
                "code": "LOCAL_MORAN_PERMUTATION_NOT_RUN",
                "message": "Python local Moran rows were written without permutation p-values.",
                "action": "Do not call the Python table LISA evidence; enable local_moran_permutations or use the R spdep adapter.",
            }
        )
    payload = {
        "edge_list": str(edge_list),
        "outcome": y_col,
        "treatment": treat_col,
        "max_treatment_moran": max_treatment_moran,
        "local_moran_inference": {
            "permutations": local_permutations,
            "alpha": local_alpha,
            "backend": "python_basic_permutation" if local_permutations > 0 else "python_basic_no_permutation",
        },
        "warnings": warnings,
        "artifacts": {
            "outcome": "tables/moran_outcome_by_year.csv",
            "treatment": "tables/moran_treatment_by_year.csv",
            "residual": "tables/moran_residual_by_year.csv",
            "local_moran": "tables/local_moran_by_year.csv",
            "outcome_trend": "figures/moran_outcome_trend.png",
            "residual_trend": "figures/moran_residual_trend.png",
        },
    }
    (out / "moran_preflight.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def run_spdep_lisa_adapter(data_path: str | Path, edge_list: str | Path, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    tables = out / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    rscript = shutil.which("Rscript")
    if not rscript:
        payload = {
            "status": "skipped_backend_unavailable",
            "backend": "R spdep",
            "warnings": [
                {
                    "severity": "yellow",
                    "code": "BACKEND_UNAVAILABLE",
                    "message": "Rscript is not available, so R spdep local Moran/LISA was skipped.",
                    "action": "Install/configure R and spdep only if R-based LISA is required.",
                }
            ],
            "artifacts": {},
        }
        (out / "spdep_lisa_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
    package_check = subprocess.run(
        [rscript, "-e", "quit(status = ifelse(requireNamespace('spdep', quietly=TRUE), 0, 1))"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if package_check.returncode != 0:
        payload = {
            "status": "skipped_backend_unavailable",
            "backend": "R spdep",
            "warnings": [
                {
                    "severity": "yellow",
                    "code": "BACKEND_UNAVAILABLE",
                    "message": "R package spdep is not available, so local Moran/LISA was skipped.",
                    "action": "Install spdep only if R-based LISA is required; Python basic local Moran remains available in spatial_moran_preflight.",
                }
            ],
            "artifacts": {},
            "stderr": package_check.stderr,
        }
        (out / "spdep_lisa_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    time_col = str(spec.get("time") or spec.get("time_id") or "year")
    y_col = str(spec.get("y") or spec.get("outcome") or "y")
    treat_col = str(spec.get("treat") or spec.get("treatment") or "treat")
    source = str(spec.get("source", "source"))
    target = str(spec.get("target", "target"))
    weight = str(spec.get("weight", "weight"))
    script = out / "run_spdep_lisa.R"
    output_csv = tables / "spdep_local_moran.csv"
    script.write_text(
        r'''
args <- commandArgs(trailingOnly=TRUE)
data_path <- args[[1]]
edge_path <- args[[2]]
out_csv <- args[[3]]
id_col <- args[[4]]
time_col <- args[[5]]
y_col <- args[[6]]
treat_col <- args[[7]]
source_col <- args[[8]]
target_col <- args[[9]]
weight_col <- args[[10]]
suppressPackageStartupMessages(library(spdep))
df <- read.csv(data_path, check.names=FALSE)
edges <- read.csv(edge_path, check.names=FALSE)
if (!(weight_col %in% names(edges))) edges[[weight_col]] <- 1
rows <- list()
idx <- 1
for (yr in sort(unique(df[[time_col]]))) {
  g <- df[df[[time_col]] == yr, , drop=FALSE]
  units <- as.character(g[[id_col]])
  n <- length(units)
  if (n < 3) next
  mat <- matrix(0, nrow=n, ncol=n)
  rownames(mat) <- units
  colnames(mat) <- units
  for (i in seq_len(nrow(edges))) {
    s <- as.character(edges[[source_col]][i])
    t <- as.character(edges[[target_col]][i])
    if (s %in% units && t %in% units && s != t) {
      mat[s, t] <- as.numeric(edges[[weight_col]][i])
    }
  }
  lw <- mat2listw(mat, style="W", zero.policy=TRUE)
  for (var in c(y_col, treat_col)) {
    vals <- as.numeric(g[[var]])
    lm <- localmoran(vals, lw, zero.policy=TRUE, na.action=na.exclude)
    for (j in seq_len(n)) {
      rows[[idx]] <- data.frame(
        year=yr,
        variable=var,
        unit=units[j],
        local_moran_i=as.numeric(lm[j, "Ii"]),
        expected_i=as.numeric(lm[j, "E.Ii"]),
        variance_i=as.numeric(lm[j, "Var.Ii"]),
        z_i=as.numeric(lm[j, "Z.Ii"]),
        p_value=as.numeric(lm[j, "Pr(z != E(Ii))"]),
        backend="R_spdep",
        stringsAsFactors=FALSE
      )
      idx <- idx + 1
    }
  }
}
if (length(rows) == 0) {
  result <- data.frame(year=numeric(), variable=character(), unit=character(), local_moran_i=numeric(), backend=character())
} else {
  result <- do.call(rbind, rows)
}
write.csv(result, out_csv, row.names=FALSE, fileEncoding="UTF-8")
'''.lstrip(),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            rscript,
            str(script),
            str(data_path),
            str(edge_list),
            str(output_csv),
            id_col,
            time_col,
            y_col,
            treat_col,
            source,
            target,
            weight,
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=int(spec.get("r_timeout", 120)),
    )
    status = "ok" if proc.returncode == 0 and output_csv.exists() else "failed"
    warnings = []
    if status != "ok":
        warnings.append(
            {
                "severity": "red",
                "code": "ESTIMATOR_STEP_FAILED",
                "message": "R spdep local Moran/LISA execution failed.",
                "action": "Inspect spdep_lisa_status.json and the generated R script.",
            }
        )
    payload = {
        "status": status,
        "backend": "R spdep localmoran",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "warnings": warnings,
        "artifacts": {"local_moran": "tables/spdep_local_moran.csv", "script": "run_spdep_lisa.R"},
    }
    (out / "spdep_lisa_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
