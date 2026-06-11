from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _components(units: list[Any], edges: list[dict[str, Any]]) -> list[list[Any]]:
    neighbors = {unit: set() for unit in units}
    for edge in edges:
        s = edge["source"]
        t = edge["target"]
        if s in neighbors and t in neighbors:
            neighbors[s].add(t)
            neighbors[t].add(s)
    seen: set[Any] = set()
    comps: list[list[Any]] = []
    for unit in units:
        if unit in seen:
            continue
        stack = [unit]
        seen.add(unit)
        comp = []
        while stack:
            current = stack.pop()
            comp.append(current)
            for nxt in neighbors[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comps.append(comp)
    return comps


def _warning(code: str, severity: str, message: str, action: str) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "action": action}


def _plot_degree(degrees: dict[Any, int], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    plt.hist(list(degrees.values()), bins=min(20, max(1, len(set(degrees.values())))), color="#4c78a8", alpha=0.85)
    plt.xlabel("Outgoing neighbor count")
    plt.ylabel("Units")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def audit_spatial_weights(edge_list: str | Path, units: Any, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    import pandas as pd

    out = Path(output_dir)
    tables = out / "tables"
    figures = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    source_col = str(spec.get("source", "source"))
    target_col = str(spec.get("target", "target"))
    weight_col = str(spec.get("weight", "weight"))
    if id_col not in units.columns:
        raise ValueError(f"spatial W audit requires unit id column `{id_col}` in panel/unit data.")
    unit_values = units[id_col].dropna().drop_duplicates().tolist()
    edge_df = pd.read_csv(edge_list)
    for col in [source_col, target_col]:
        if col not in edge_df.columns:
            raise ValueError(f"spatial W edge list missing column `{col}`.")
    if weight_col not in edge_df.columns:
        edge_df[weight_col] = 1.0
    edge_df = edge_df[[source_col, target_col, weight_col]].copy()
    edge_df[weight_col] = pd.to_numeric(edge_df[weight_col], errors="coerce").fillna(0.0)
    edge_df = edge_df.rename(columns={source_col: "source", target_col: "target", weight_col: "weight"})
    edges = edge_df.to_dict("records")

    degrees = {unit: 0 for unit in unit_values}
    row_sums = {unit: 0.0 for unit in unit_values}
    diagonal_edges = 0
    for edge in edges:
        if edge["source"] == edge["target"] and float(edge["weight"]) != 0:
            diagonal_edges += 1
        if edge["source"] in degrees and edge["source"] != edge["target"] and float(edge["weight"]) != 0:
            degrees[edge["source"]] += 1
            row_sums[edge["source"]] += float(edge["weight"])
    isolates = [unit for unit, degree in degrees.items() if degree == 0]
    comps = _components(unit_values, edges)
    n = len(unit_values)
    density = float(sum(degrees.values()) / (n * (n - 1))) if n > 1 else 0.0
    non_isolate_sums = [value for unit, value in row_sums.items() if degrees.get(unit, 0) > 0]
    row_standardized = bool(non_isolate_sums and all(abs(value - 1.0) < float(spec.get("row_sum_tolerance", 1e-6)) for value in non_isolate_sums))

    audit_rows = [
        {"metric": "n_units", "value": n},
        {"metric": "n_edges", "value": int(sum(degrees.values()))},
        {"metric": "density", "value": density},
        {"metric": "row_standardized", "value": row_standardized},
        {"metric": "diagonal_nonzero_edges", "value": diagonal_edges},
        {"metric": "isolated_units", "value": len(isolates)},
        {"metric": "min_neighbors", "value": int(min(degrees.values())) if degrees else 0},
        {"metric": "max_neighbors", "value": int(max(degrees.values())) if degrees else 0},
        {"metric": "n_components", "value": int(len(comps))},
    ]
    pd.DataFrame(audit_rows).to_csv(tables / "spatial_w_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"unit": isolates}).to_csv(tables / "spatial_isolates.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [{"component_id": idx + 1, "n_units": len(comp), "units": json.dumps(comp, ensure_ascii=False)} for idx, comp in enumerate(comps)]
    ).to_csv(tables / "spatial_components.csv", index=False, encoding="utf-8-sig")
    _plot_degree(degrees, figures / "spatial_degree_distribution.png")

    warnings: list[dict[str, Any]] = []
    if isolates:
        warnings.append(
            _warning(
                "SPATIAL_W_HAS_ISLANDS",
                "yellow",
                f"Spatial W has {len(isolates)} isolated unit(s).",
                "Revise W construction or explicitly justify/drop islands before spatial claims.",
            )
        )
    if not row_standardized:
        warnings.append(
            _warning(
                "SPATIAL_W_NOT_ROW_STANDARDIZED",
                "yellow",
                "Spatial W row sums are not all one for non-isolated units.",
                "Row-standardize W or explicitly justify raw weights.",
            )
        )
    payload = {
        "edge_list": str(edge_list),
        "n_units": n,
        "n_edges": int(sum(degrees.values())),
        "density": density,
        "row_standardized": row_standardized,
        "diagonal_nonzero_edges": diagonal_edges,
        "isolated_units": isolates,
        "min_neighbors": int(min(degrees.values())) if degrees else 0,
        "max_neighbors": int(max(degrees.values())) if degrees else 0,
        "n_components": int(len(comps)),
        "warnings": warnings,
        "artifacts": {
            "audit": "tables/spatial_w_audit.csv",
            "isolates": "tables/spatial_isolates.csv",
            "components": "tables/spatial_components.csv",
            "degree_distribution": "figures/spatial_degree_distribution.png",
        },
    }
    (out / "spatial_w_audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_spatial_w_comparison(results: list[dict[str, Any]], output_dir: str | Path) -> Path:
    import pandas as pd

    out = Path(output_dir)
    path = out / "tables" / "spatial_w_comparison.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "edge_list": item.get("edge_list"),
            "n_units": item.get("n_units"),
            "n_edges": item.get("n_edges"),
            "density": item.get("density"),
            "row_standardized": item.get("row_standardized"),
            "isolated_units": len(item.get("isolated_units") or []),
            "min_neighbors": item.get("min_neighbors"),
            "max_neighbors": item.get("max_neighbors"),
            "n_components": item.get("n_components"),
        }
        for item in results
    ]
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path
