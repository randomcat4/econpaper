from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return float(2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _components(units: list[Any], edges: list[dict[str, Any]]) -> list[list[Any]]:
    neighbors = {unit: set() for unit in units}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source in neighbors and target in neighbors:
            neighbors[source].add(target)
            neighbors[target].add(source)
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


def _row_standardize(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[Any, float] = {}
    for edge in edges:
        totals[edge["source"]] = totals.get(edge["source"], 0.0) + float(edge["weight"])
    result = []
    for edge in edges:
        total = totals.get(edge["source"], 0.0)
        weight = float(edge["weight"]) / total if total else 0.0
        result.append({**edge, "weight": weight})
    return result


def _distance_edges(units: Any, *, id_col: str, lon_col: str, lat_col: str, cutoff_km: float | None, power: float, mode: str, k: int | None = None) -> list[dict[str, Any]]:
    rows = units[[id_col, lon_col, lat_col]].dropna().to_dict("records")
    edges: list[dict[str, Any]] = []
    for source in rows:
        distances = []
        for target in rows:
            if source[id_col] == target[id_col]:
                continue
            dist = _haversine_km(float(source[lon_col]), float(source[lat_col]), float(target[lon_col]), float(target[lat_col]))
            if cutoff_km is None or dist <= cutoff_km:
                weight = 1.0 / max(dist, 1e-9) ** power if mode == "inverse_distance" else 1.0
                distances.append((dist, source[id_col], target[id_col], weight))
        distances.sort(key=lambda item: item[0])
        if mode == "knn":
            distances = distances[: int(k or 1)]
            distances = [(dist, src, tgt, 1.0 / max(dist, 1e-9) ** power) for dist, src, tgt, _ in distances]
        for dist, src, tgt, weight in distances:
            edges.append({"source": src, "target": tgt, "weight": float(weight), "distance_km": float(dist)})
    return edges


def _write_dense(path: Path, units: list[Any], edges: list[dict[str, Any]]) -> None:
    import pandas as pd

    matrix = pd.DataFrame(0.0, index=units, columns=units)
    for edge in edges:
        matrix.loc[edge["source"], edge["target"]] = float(edge["weight"])
    matrix.index.name = "source"
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix.reset_index().to_csv(path, index=False, encoding="utf-8-sig")


def build_spatial_weights(units: Any, spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    import pandas as pd

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    weights_dir = out / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)

    w_type = str(spec.get("w_type") or spec.get("weight_type") or spec.get("type") or "inverse_distance").lower()
    matrix_name = str(spec.get("matrix_name") or spec.get("name") or w_type)
    id_col = str(spec.get("id") or spec.get("unit_id") or "unit")
    lon_col = str(spec.get("longitude") or spec.get("lon") or "lon")
    lat_col = str(spec.get("latitude") or spec.get("lat") or "lat")
    row_standardized = _as_bool(spec.get("row_standardize", spec.get("row_standardized")), True)
    write_dense = _as_bool(spec.get("write_dense"), False)
    isolated_policy = str(spec.get("isolated_policy") or "keep").lower()

    if id_col not in units.columns:
        raise ValueError(f"spatial weights require id column `{id_col}`.")
    unit_values = units[id_col].dropna().tolist()
    if len(unit_values) != len(set(unit_values)):
        raise ValueError(f"spatial unit id column `{id_col}` contains duplicates.")

    if w_type in {"inverse_distance", "distance_band", "knn", "k_nearest_neighbors"}:
        for col in [lon_col, lat_col]:
            if col not in units.columns:
                raise ValueError(f"{w_type} weights require coordinate column `{col}`.")
        cutoff = spec.get("cutoff_km")
        cutoff_km = float(cutoff) if cutoff is not None else (float(spec.get("distance_band_km")) if spec.get("distance_band_km") is not None else None)
        if w_type == "distance_band" and cutoff_km is None:
            raise ValueError("distance_band weights require cutoff_km.")
        power = float(spec.get("power", 1.0))
        mode = "knn" if w_type in {"knn", "k_nearest_neighbors"} else w_type
        edges = _distance_edges(
            units,
            id_col=id_col,
            lon_col=lon_col,
            lat_col=lat_col,
            cutoff_km=cutoff_km,
            power=power,
            mode=mode,
            k=int(spec.get("k", 5)),
        )
        source_columns = [lon_col, lat_col]
        parameters = {"cutoff_km": cutoff_km, "power": power, "k": int(spec.get("k", 5)) if mode == "knn" else None}
    elif w_type in {"adjacency", "edge_list", "contiguity"}:
        edge_path = spec.get("edge_list") or spec.get("weights") or spec.get("path")
        if not edge_path:
            raise ValueError("edge-list/contiguity weights require edge_list/weights/path.")
        edge_df = pd.read_csv(edge_path)
        source_col = str(spec.get("source", "source"))
        target_col = str(spec.get("target", "target"))
        weight_col = str(spec.get("weight", "weight"))
        for col in [source_col, target_col]:
            if col not in edge_df.columns:
                raise ValueError(f"edge list missing column `{col}`.")
        if weight_col not in edge_df.columns:
            edge_df[weight_col] = 1.0
        edges = [
            {"source": row[source_col], "target": row[target_col], "weight": float(row[weight_col])}
            for row in edge_df.to_dict("records")
            if row[source_col] != row[target_col]
        ]
        source_columns = [source_col, target_col, weight_col]
        parameters = {"edge_list": str(edge_path)}
    else:
        raise ValueError(f"Unsupported spatial weight type for v0.1 factory: {w_type}")

    outgoing = {unit: 0 for unit in unit_values}
    for edge in edges:
        if edge["source"] in outgoing:
            outgoing[edge["source"]] += 1
    isolated_units = [unit for unit, degree in outgoing.items() if degree == 0]
    dropped_isolates: list[Any] = []
    if isolated_units and isolated_policy == "error":
        raise ValueError(f"Spatial weights produced isolated units: {isolated_units}")
    if isolated_units and isolated_policy == "drop":
        dropped = set(isolated_units)
        dropped_isolates = isolated_units
        unit_values = [unit for unit in unit_values if unit not in dropped]
        edges = [edge for edge in edges if edge["source"] not in dropped and edge["target"] not in dropped]
        isolated_units = []

    if row_standardized:
        edges = _row_standardize(edges)

    edge_path = weights_dir / f"{matrix_name}_edges.csv"
    pd.DataFrame(edges, columns=["source", "target", "weight", "distance_km"]).to_csv(edge_path, index=False, encoding="utf-8-sig")
    dense_path = weights_dir / f"{matrix_name}_dense.csv"
    if write_dense:
        _write_dense(dense_path, unit_values, edges)

    degrees = {unit: 0 for unit in unit_values}
    for edge in edges:
        if edge["source"] in degrees:
            degrees[edge["source"]] += 1
    comps = _components(unit_values, edges)
    n = len(unit_values)
    density = float(len(edges) / (n * (n - 1))) if n > 1 else 0.0
    metadata = {
        "matrix_name": matrix_name,
        "weight_type": w_type,
        "unit": id_col,
        "row_standardized": row_standardized,
        "zero_diagonal": True,
        "density": density,
        "isolated_units": isolated_units,
        "dropped_isolated_units": dropped_isolates,
        "min_neighbors": int(min(degrees.values())) if degrees else 0,
        "max_neighbors": int(max(degrees.values())) if degrees else 0,
        "n_components": int(len(comps)),
        "components": [list(comp) for comp in comps],
        "source_columns": source_columns,
        "parameters": parameters,
        "edge_list": str(edge_path),
        "dense_csv": str(dense_path) if write_dense else None,
    }
    metadata_path = weights_dir / f"{matrix_name}_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    warnings: list[dict[str, Any]] = []
    if isolated_units:
        warnings.append(
            {
                "severity": "yellow",
                "code": "SPATIAL_W_HAS_ISLANDS",
                "message": f"Spatial weights contain isolated units: {isolated_units}",
                "action": "Check cutoff/k or set isolated_policy=drop/error explicitly.",
            }
        )
    if not row_standardized:
        warnings.append(
            {
                "severity": "yellow",
                "code": "SPATIAL_W_NOT_ROW_STANDARDIZED",
                "message": "Spatial weights were written without row standardization.",
                "action": "Use row_standardize=true unless the estimator/report explicitly justifies raw weights.",
            }
        )
    return {
        "edge_list": str(edge_path),
        "metadata": str(metadata_path),
        "dense_csv": str(dense_path) if write_dense else None,
        "metadata_payload": metadata,
        "warnings": warnings,
    }
