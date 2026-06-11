from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PsmFixture:
    name: str
    rows: list[dict[str, Any]]
    spec: dict[str, Any]
    expected_risks: tuple[str, ...]


def _base_spec() -> dict[str, Any]:
    return {
        "id": "unit",
        "time": "year",
        "y": "y",
        "treat": "treat",
        "x": ["x1", "x2"],
        "psm_grid_neighbors": [1, 5],
        "psm_grid_calipers": [0.01, 0.05],
        "psm_grid_replacement": [True],
    }


def _good_overlap() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    unit = 0
    for k in range(40):
        x1 = (k % 20) / 10
        x2 = ((k * 7) % 17) / 10
        for treat in [0, 1]:
            rows.append({"unit": unit, "year": 2020, "y": 1 + 0.3 * x1 + 0.2 * x2 + treat, "treat": treat, "x1": x1, "x2": x2})
            unit += 1
    return rows


def _poor_overlap() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(50):
        x1 = -4 + i / 60
        rows.append({"unit": i, "year": 2020, "y": 1 + 0.1 * x1, "treat": 0, "x1": x1, "x2": x1 * 0.2})
    for i in range(50):
        x1 = 4 + i / 60
        rows.append({"unit": i + 50, "year": 2020, "y": 2 + 0.1 * x1, "treat": 1, "x1": x1, "x2": x1 * 0.2})
    return rows


def _extreme_weights() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(120):
        treat = i % 2
        ps = 0.5
        if i in {0, 2}:
            treat = 1
            ps = 0.01
        if i in {1, 3}:
            treat = 0
            ps = 0.99
        x1 = (i % 30) / 10
        x2 = ((i * 11) % 23) / 10
        rows.append({"unit": i, "year": 2020, "y": 1 + 0.2 * x1 + 0.1 * x2 + treat, "treat": treat, "x1": x1, "x2": x2, "ps": ps})
    return rows


def _poor_balance() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(120):
        treat = i % 2
        x1 = (i % 30) / 10
        x2 = 3.0 * treat + ((i * 5) % 17) / 10
        rows.append({"unit": i, "year": 2020, "y": 1 + 0.2 * x1 + 0.7 * x2 + treat, "treat": treat, "x1": x1, "x2": x2})
    return rows


def _grid_unstable() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    unit = 0
    for i in range(10):
        ps = 0.50 + (i - 5) * 0.0005
        rows.append({"unit": unit, "year": 2020, "y": 1.0, "treat": 1, "x1": ps, "x2": 0.0, "ps": ps})
        unit += 1
    rows.append({"unit": unit, "year": 2020, "y": 0.0, "treat": 0, "x1": 0.50, "x2": 0.0, "ps": 0.50})
    unit += 1
    for i in range(40):
        ps = 0.54 + (i % 10) * 0.0005
        rows.append({"unit": unit, "year": 2020, "y": 4.0, "treat": 0, "x1": ps, "x2": 0.0, "ps": ps})
        unit += 1
    return rows


def _fixture_catalog() -> list[PsmFixture]:
    base = _base_spec()
    return [
        PsmFixture("overlap_good", _good_overlap(), base, ()),
        PsmFixture("overlap_poor", _poor_overlap(), base, ("OFF_SUPPORT_HIGH_SHARE", "POOR_OVERLAP", "PSM_SAMPLE_LOSS_HIGH")),
        PsmFixture("extreme_weights", _extreme_weights(), {**base, "pscore_col": "ps"}, ("EXTREME_IPW_WEIGHTS", "LOW_EFFECTIVE_SAMPLE_SIZE")),
        PsmFixture("psm_sample_loss_high", _poor_overlap(), base, ("PSM_SAMPLE_LOSS_HIGH",)),
        PsmFixture("balance_still_poor", _poor_balance(), {**base, "x": ["x1"], "balance_vars": ["x1", "x2"]}, ("BALANCE_STILL_POOR",)),
        PsmFixture("drdid_psm_disagree", _good_overlap(), base, ("DRDID_PSM_DID_DISAGREE",)),
        PsmFixture("trim_sensitivity_unstable", _grid_unstable(), {**base, "pscore_col": "ps"}, ("TRIM_SENSITIVITY_UNSTABLE",)),
    ]


PSM_DID_FIXTURE_NAMES = tuple(item.name for item in _fixture_catalog())


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def materialize_psm_did_fixtures(base_dir: Path = BASE_DIR) -> list[Path]:
    written: list[Path] = []
    for fixture in _fixture_catalog():
        csv_path = base_dir / f"{fixture.name}.csv"
        _write_csv(csv_path, fixture.rows)
        (base_dir / f"{fixture.name}.spec.json").write_text(json.dumps(fixture.spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (base_dir / f"{fixture.name}.expected_risks.json").write_text(
            json.dumps({"fixture": fixture.name, "expected_risks": list(fixture.expected_risks)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(csv_path)
    return written


if __name__ == "__main__":
    paths = materialize_psm_did_fixtures()
    print(json.dumps({"fixtures": [path.name for path in paths]}, indent=2))
