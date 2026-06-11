from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

SPATIAL_FIXTURE_NAMES = [
    "w_has_islands",
    "w_not_row_standardized",
    "treatment_spatially_clustered",
    "contaminated_controls",
    "direct_only_effect",
    "indirect_only_effect",
    "w_sign_flip",
]


def _write_case(name: str, panel: pd.DataFrame, weights: dict[str, pd.DataFrame], spec: dict, expected_risks: list[str]) -> None:
    case_dir = BASE_DIR / name
    case_dir.mkdir(parents=True, exist_ok=True)
    panel.to_csv(case_dir / "panel.csv", index=False)
    for weight_name, frame in weights.items():
        frame.to_csv(case_dir / weight_name, index=False)
    (case_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    (case_dir / "expected_risks.json").write_text(
        json.dumps({"expected_risks": expected_risks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _unit_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"city": "A", "lon": 0.0, "lat": 0.0},
            {"city": "B", "lon": 0.0, "lat": 1.0},
            {"city": "C", "lon": 1.0, "lat": 0.0},
            {"city": "D", "lon": 1.0, "lat": 1.0},
            {"city": "Z", "lon": 50.0, "lat": 50.0},
        ]
    )


def _clustered_panel() -> pd.DataFrame:
    rows = []
    for year in [2020, 2021, 2022]:
        for city in ["A", "B", "C", "D"]:
            treat = 1 if city in {"A", "B"} else 0
            y = 2.0 + treat + 0.1 * (year - 2020)
            rows.append({"city": city, "year": year, "y": y, "treat": treat, "lon": ord(city) - ord("A"), "lat": 0.0})
    return pd.DataFrame(rows)


def _exposure_panel(*, direct: bool = True, indirect: bool = True) -> pd.DataFrame:
    rows = []
    years = [2018, 2019, 2020, 2021, 2022]
    for year in years:
        active = {"A": 1 if year >= 2020 else 0, "C": 1 if year >= 2021 else 0}
        exposure = {
            "A": 0.0,
            "B": active["A"],
            "C": 0.0,
            "D": active["C"],
            "E": 0.5 * active["A"] + 0.5 * active["C"],
            "F": 0.0,
        }
        for idx, city in enumerate(["A", "B", "C", "D", "E", "F"]):
            treat = active.get(city, 0)
            y = 1.0 + 0.2 * idx + 0.1 * (year - 2018)
            if direct:
                y += 1.5 * treat
            if indirect:
                y += 1.2 * exposure[city]
            rows.append({"city": city, "year": year, "y": y, "treat": treat, "lon": idx * 0.1, "lat": idx * 0.1})
    return pd.DataFrame(rows)


def _exposure_edges() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"source": "B", "target": "A", "weight": 1.0, "distance_km": 30.0},
            {"source": "D", "target": "C", "weight": 1.0, "distance_km": 60.0},
            {"source": "E", "target": "A", "weight": 0.5, "distance_km": 200.0},
            {"source": "E", "target": "C", "weight": 0.5, "distance_km": 250.0},
            {"source": "F", "target": "B", "weight": 1.0, "distance_km": 40.0},
        ]
    )


def _w_flip_panel() -> pd.DataFrame:
    rows = []
    units = list("ABCDEFGH")
    for year in range(2018, 2023):
        post = year >= 2020
        for idx, unit in enumerate(units):
            treat = 1 if unit == "A" and post else 0
            y = 0.2 * idx + 0.1 * (year - 2018)
            if unit in {"B", "D", "E"} and post:
                y += 2.0
            if unit in {"F", "G", "H"} and post:
                y -= 2.0
            rows.append({"city": unit, "year": year, "y": y, "treat": treat, "lon": idx * 0.1, "lat": 0.0})
    return pd.DataFrame(rows)


def _edges_to_a(sources: list[str]) -> pd.DataFrame:
    return pd.DataFrame([{"source": source, "target": "A", "weight": 1.0, "distance_km": 50.0} for source in sources])


def materialize_spatial_fixtures(base_dir: Path = BASE_DIR) -> list[Path]:
    del base_dir
    _write_case(
        "w_has_islands",
        _unit_frame(),
        {"weights.csv": pd.DataFrame([{"source": "A", "target": "B", "weight": 1.0}, {"source": "B", "target": "A", "weight": 1.0}])},
        {"method": "spatial_w_audit", "id": "city", "weights": "weights.csv"},
        ["SPATIAL_W_HAS_ISLANDS"],
    )
    _write_case(
        "w_not_row_standardized",
        _unit_frame(),
        {"weights.csv": pd.DataFrame([{"source": "A", "target": "B", "weight": 2.0}, {"source": "B", "target": "A", "weight": 3.0}])},
        {"method": "spatial_w_audit", "id": "city", "weights": "weights.csv"},
        ["SPATIAL_W_NOT_ROW_STANDARDIZED"],
    )
    _write_case(
        "treatment_spatially_clustered",
        _clustered_panel(),
        {
            "weights.csv": pd.DataFrame(
                [
                    {"source": "A", "target": "B", "weight": 1.0},
                    {"source": "B", "target": "A", "weight": 1.0},
                    {"source": "C", "target": "D", "weight": 1.0},
                    {"source": "D", "target": "C", "weight": 1.0},
                ]
            )
        },
        {"method": "spatial_moran_preflight", "id": "city", "time": "year", "y": "y", "treat": "treat", "weights": "weights.csv"},
        ["SPATIAL_TREATMENT_CLUSTERED"],
    )
    _write_case(
        "contaminated_controls",
        _exposure_panel(),
        {"weights.csv": _exposure_edges()},
        {"method": "spatial_exposure_did", "id": "city", "time": "year", "y": "y", "treat": "treat", "weights": "weights.csv", "near_exposure_threshold": 0, "run_event_study": False},
        ["CONTROL_GROUP_CONTAMINATED"],
    )
    _write_case(
        "direct_only_effect",
        _exposure_panel(direct=True, indirect=False),
        {"weights.csv": _exposure_edges()},
        {"method": "spatial_exposure_did", "id": "city", "time": "year", "y": "y", "treat": "treat", "weights": "weights.csv", "near_exposure_threshold": 0, "run_event_study": False},
        [],
    )
    _write_case(
        "indirect_only_effect",
        _exposure_panel(direct=False, indirect=True),
        {"weights.csv": _exposure_edges()},
        {"method": "spatial_exposure_did", "id": "city", "time": "year", "y": "y", "treat": "treat", "weights": "weights.csv", "near_exposure_threshold": 0, "run_event_study": False},
        ["CONTROL_GROUP_CONTAMINATED"],
    )
    _write_case(
        "w_sign_flip",
        _w_flip_panel(),
        {"w1.csv": _edges_to_a(list("BDE")), "w2.csv": _edges_to_a(list("FGH")), "w3.csv": _edges_to_a(list("BDEFGH"))},
        {"method": "spatial_w_sensitivity", "id": "city", "time": "year", "y": "y", "treat": "treat", "weights": "w1.csv", "weight_paths": ["w2.csv", "w3.csv"], "near_exposure_threshold": 0, "run_event_study": False},
        ["W_SENSITIVITY_SIGN_FLIP"],
    )
    return [BASE_DIR / name for name in SPATIAL_FIXTURE_NAMES]


if __name__ == "__main__":
    paths = materialize_spatial_fixtures()
    print(json.dumps({"fixtures": [path.name for path in paths]}, indent=2))
