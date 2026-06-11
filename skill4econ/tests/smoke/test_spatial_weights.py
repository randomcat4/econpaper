from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skill4econ.adapters.python.spatial_weights import build_spatial_weights
from skill4econ.core import make_run_context
from skill4econ.diagnostics.spatial_exposure import run_spatial_exposure_did
from skill4econ.diagnostics.spatial_preflight import audit_spatial_weights, write_spatial_w_comparison
from skill4econ.diagnostics.spatial_moran import run_moran_preflight
from skill4econ.python_wrappers import spatial_exposure_did, spatial_moran_preflight, spatial_w_audit, spatial_weights_factory


def _units() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"city": "A", "lon": 0.0, "lat": 0.0},
            {"city": "B", "lon": 0.0, "lat": 1.0},
            {"city": "C", "lon": 1.0, "lat": 0.0},
            {"city": "D", "lon": 1.0, "lat": 1.0},
            {"city": "Z", "lon": 50.0, "lat": 50.0},
        ]
    )


def _codes(result: dict) -> set[str]:
    return {item["code"] for item in result.get("warnings") or []}


def test_inverse_distance_and_knn_weights_write_metadata(tmp_path: Path) -> None:
    inverse = build_spatial_weights(
        _units(),
        {"id": "city", "w_type": "inverse_distance", "matrix_name": "inverse_all", "write_dense": True},
        tmp_path / "inverse",
    )
    meta = inverse["metadata_payload"]
    assert meta["row_standardized"] is True
    assert meta["zero_diagonal"] is True
    assert meta["min_neighbors"] == 4
    assert Path(inverse["edge_list"]).exists()
    assert Path(inverse["dense_csv"]).exists()

    knn = build_spatial_weights(
        _units(),
        {"id": "city", "w_type": "knn", "k": 2, "matrix_name": "knn2"},
        tmp_path / "knn",
    )
    assert knn["metadata_payload"]["min_neighbors"] == 2
    assert not knn["warnings"]


def test_distance_band_islands_and_raw_weight_warnings(tmp_path: Path) -> None:
    band = build_spatial_weights(
        _units(),
        {"id": "city", "w_type": "distance_band", "cutoff_km": 160, "matrix_name": "band160"},
        tmp_path / "band",
    )
    assert "SPATIAL_W_HAS_ISLANDS" in _codes(band)
    assert band["metadata_payload"]["isolated_units"] == ["Z"]

    raw = build_spatial_weights(
        _units(),
        {"id": "city", "w_type": "inverse_distance", "row_standardize": False, "matrix_name": "raw_inverse"},
        tmp_path / "raw",
    )
    assert "SPATIAL_W_NOT_ROW_STANDARDIZED" in _codes(raw)


def test_spatial_weights_factory_wrapper_registers_manifest_artifacts(tmp_path: Path) -> None:
    data_path = tmp_path / "units.csv"
    _units().to_csv(data_path, index=False)
    spec = {"data": str(data_path), "id": "city", "w_type": "distance_band", "cutoff_km": 160, "matrix_name": "band160"}
    ctx = make_run_context("spatial_weights_factory", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_weights_factory(ctx)
    assert manifest["status"] == "ok"
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "SPATIAL_W_HAS_ISLANDS" in {item["code"] for item in risk["risks"]}
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in artifact_manifest["artifacts"]}
    assert "weights/band160_edges.csv" in paths
    assert "weights/band160_metadata.json" in paths


def test_spatial_w_audit_outputs_isolates_components_and_comparison(tmp_path: Path) -> None:
    units = _units()
    band = build_spatial_weights(
        units,
        {"id": "city", "w_type": "distance_band", "cutoff_km": 160, "matrix_name": "band160"},
        tmp_path / "factory_band",
    )
    raw = build_spatial_weights(
        units,
        {"id": "city", "w_type": "inverse_distance", "row_standardize": False, "matrix_name": "raw_inverse"},
        tmp_path / "factory_raw",
    )
    audit = audit_spatial_weights(band["edge_list"], units, {"id": "city"}, tmp_path / "audit_band")
    assert "SPATIAL_W_HAS_ISLANDS" in _codes(audit)
    for rel in [
        "tables/spatial_w_audit.csv",
        "figures/spatial_degree_distribution.png",
        "tables/spatial_isolates.csv",
        "tables/spatial_components.csv",
    ]:
        assert (tmp_path / "audit_band" / rel).exists()

    raw_audit = audit_spatial_weights(raw["edge_list"], units, {"id": "city"}, tmp_path / "audit_raw")
    assert "SPATIAL_W_NOT_ROW_STANDARDIZED" in _codes(raw_audit)
    comparison = write_spatial_w_comparison([audit, raw_audit], tmp_path / "comparison")
    assert comparison.exists()


def test_spatial_w_audit_wrapper_registers_manifest_artifacts(tmp_path: Path) -> None:
    units = _units()
    data_path = tmp_path / "units.csv"
    units.to_csv(data_path, index=False)
    band = build_spatial_weights(
        units,
        {"id": "city", "w_type": "distance_band", "cutoff_km": 160, "matrix_name": "band160"},
        tmp_path / "factory_band",
    )
    raw = build_spatial_weights(
        units,
        {"id": "city", "w_type": "inverse_distance", "row_standardize": False, "matrix_name": "raw_inverse"},
        tmp_path / "factory_raw",
    )
    spec = {"data": str(data_path), "id": "city", "weight_paths": [band["edge_list"], raw["edge_list"]]}
    ctx = make_run_context("spatial_w_audit", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_w_audit(ctx)
    assert manifest["status"] == "ok"
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in artifact_manifest["artifacts"]}
    assert "tables/spatial_w_comparison.csv" in paths
    assert "w_01/tables/spatial_w_audit.csv" in paths
    assert "w_02/tables/spatial_w_audit.csv" in paths


def _clustered_panel() -> pd.DataFrame:
    rows = []
    for year in [2020, 2021]:
        for city in ["A", "B", "C", "D"]:
            treat = 1 if city in {"A", "B"} else 0
            y = 2.0 + treat + (0.1 if year == 2021 else 0.0)
            rows.append({"city": city, "year": year, "y": y, "treat": treat})
    return pd.DataFrame(rows)


def _clustered_edges(path: Path) -> Path:
    pd.DataFrame(
        [
            {"source": "A", "target": "B", "weight": 1.0},
            {"source": "B", "target": "A", "weight": 1.0},
            {"source": "C", "target": "D", "weight": 1.0},
            {"source": "D", "target": "C", "weight": 1.0},
        ]
    ).to_csv(path, index=False)
    return path


def test_spatial_moran_preflight_outputs_and_clustering_risk(tmp_path: Path) -> None:
    panel = _clustered_panel()
    edges = _clustered_edges(tmp_path / "clustered_edges.csv")
    result = run_moran_preflight(panel, edges, {"id": "city", "time": "year", "y": "y", "treat": "treat"}, tmp_path / "moran")
    assert "SPATIAL_TREATMENT_CLUSTERED" in _codes(result)
    for rel in [
        "tables/moran_outcome_by_year.csv",
        "tables/moran_treatment_by_year.csv",
        "tables/moran_residual_by_year.csv",
        "figures/moran_outcome_trend.png",
        "figures/moran_residual_trend.png",
    ]:
        assert (tmp_path / "moran" / rel).exists()

    data_path = tmp_path / "panel.csv"
    panel.to_csv(data_path, index=False)
    ctx = make_run_context(
        "spatial_moran_preflight",
        "python",
        {"data": str(data_path), "weights": str(edges), "id": "city", "time": "year", "y": "y", "treat": "treat"},
        "run",
        str(tmp_path / "runs"),
    )
    manifest = spatial_moran_preflight(ctx)
    assert manifest["status"] == "ok"
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in artifact_manifest["artifacts"]}
    assert "tables/moran_treatment_by_year.csv" in paths
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "SPATIAL_TREATMENT_CLUSTERED" in {item["code"] for item in risk["risks"]}


def _exposure_panel() -> pd.DataFrame:
    rows = []
    unit_fe = {"A": 0.2, "B": -0.1, "C": 0.4, "D": -0.2, "E": 0.1, "F": -0.3}
    years = [2018, 2019, 2020, 2021, 2022]
    for year in years:
        active = {
            "A": 1 if year >= 2020 else 0,
            "C": 1 if year >= 2021 else 0,
        }
        exposure = {
            "A": 0.0,
            "B": active["A"],
            "C": 0.0,
            "D": active["C"],
            "E": 0.5 * active["A"] + 0.5 * active["C"],
            "F": 0.0,
        }
        for city in ["A", "B", "C", "D", "E", "F"]:
            treat = active.get(city, 0)
            x = 0.05 * (year - 2018) + 0.02 * (ord(city) - ord("A")) * ((year - 2018) % 2)
            y = 1.0 + unit_fe[city] + 0.1 * (year - 2018) + 0.3 * x + 2.0 * treat + 1.5 * exposure[city]
            rows.append({"city": city, "year": year, "y": y, "treat": treat, "x": x})
    return pd.DataFrame(rows)


def _exposure_edges(path: Path) -> Path:
    pd.DataFrame(
        [
            {"source": "B", "target": "A", "weight": 1.0, "distance_km": 30.0},
            {"source": "D", "target": "C", "weight": 1.0, "distance_km": 60.0},
            {"source": "E", "target": "A", "weight": 0.5, "distance_km": 200.0},
            {"source": "E", "target": "C", "weight": 0.5, "distance_km": 250.0},
            {"source": "F", "target": "B", "weight": 1.0, "distance_km": 40.0},
        ]
    ).to_csv(path, index=False)
    return path


def test_spatial_exposure_did_constructs_w_treat_rings_and_risks(tmp_path: Path) -> None:
    panel = _exposure_panel()
    edges = _exposure_edges(tmp_path / "exposure_edges.csv")
    spec = {
        "id": "city",
        "time": "year",
        "y": "y",
        "treat": "treat",
        "x": ["x"],
        "weights": str(edges),
        "distance_rings_km": [100, 300],
        "near_exposure_threshold": 0.0,
        "event_window": [-1, 1],
    }
    result = run_spatial_exposure_did(panel, edges, spec, tmp_path / "exposure")
    assert "CONTROL_GROUP_CONTAMINATED" in _codes(result)
    assert result["event_study_status"] == "ok"
    assert "_spatial_exposure" in {row["term"] for row in result["rows"]}
    for rel in [
        "tables/spatial_exposure_summary.csv",
        "figures/spatial_exposure_distribution.png",
        "tables/contaminated_controls.csv",
        "tables/spatial_exposure_twfe.csv",
        "tables/local_effect.csv",
        "tables/spillover_effect.csv",
        "tables/spatial_exposure_event_study.csv",
        "spatial_exposure_panel_buffered.csv",
    ]:
        assert (tmp_path / "exposure" / rel).exists()
    exposure_panel = pd.read_csv(tmp_path / "exposure" / "spatial_exposure_panel.csv")
    b_2020 = exposure_panel[(exposure_panel["city"] == "B") & (exposure_panel["year"] == 2020)].iloc[0]
    e_2021 = exposure_panel[(exposure_panel["city"] == "E") & (exposure_panel["year"] == 2021)].iloc[0]
    assert b_2020["_spatial_exposure"] == 1.0
    assert b_2020["exposure_ring_0_100"] == 1.0
    assert e_2021["exposure_ring_100_300"] == 1.0


def test_spatial_exposure_did_wrapper_registers_manifest_artifacts(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    panel = _exposure_panel()
    panel.to_csv(panel_path, index=False)
    edges = _exposure_edges(tmp_path / "exposure_edges.csv")
    spec = {
        "data": str(panel_path),
        "weights": str(edges),
        "id": "city",
        "time": "year",
        "y": "y",
        "treat": "treat",
        "x": ["x"],
        "distance_rings_km": [100, 300],
        "near_exposure_threshold": 0.0,
        "event_window": [-1, 1],
    }
    ctx = make_run_context("spatial_exposure_did", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_exposure_did(ctx)
    assert manifest["status"] == "ok"
    model = pd.read_csv(ctx.artifact("model_table.csv"))
    assert {"_local_treatment", "_spatial_exposure"}.issubset(set(model["term"]))
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in artifact_manifest["artifacts"]}
    assert "tables/spatial_exposure_summary.csv" in paths
    assert "tables/contaminated_controls.csv" in paths
    assert "tables/spillover_effect.csv" in paths
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "CONTROL_GROUP_CONTAMINATED" in {item["code"] for item in risk["risks"]}
