from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class DidFixture:
    name: str
    rows: list[dict[str, float | int]]
    spec: dict[str, object]
    contract: str
    expected_design_type: str
    expected_risks: tuple[str, ...] = ()


def _simple_panel(periods: list[int], *, units: int = 8) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    first_post = periods[len(periods) // 2]
    for unit in range(1, units + 1):
        ever = int(unit <= units // 2)
        for year in periods:
            post = int(year >= first_post)
            treatment_effect = 1.0 * ever * post
            rows.append(
                {
                    "unit": unit,
                    "year": year,
                    "y": round(1.5 + unit * 0.12 + (year - periods[0]) * 0.08 + treatment_effect, 4),
                    "treat": ever,
                    "post": post,
                    "x1": round(unit * 0.15 + (year - periods[0]) * 0.03, 4),
                }
            )
    return rows


def _staggered_panel(
    assignments: dict[int, int],
    periods: list[int],
    *,
    drop_rule: Callable[[int, int], bool] | None = None,
    anticipation: bool = False,
) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    first_policy = min(g for g in assignments.values() if g)
    for unit, gvar in assignments.items():
        for year in periods:
            if drop_rule and drop_rule(unit, year):
                continue
            treated_now = int(bool(gvar) and year >= gvar)
            rel = year - gvar if gvar else -99
            lead = int(bool(gvar) and year == gvar - 1)
            effect = treated_now * (0.9 + 0.12 * max(rel, 0))
            if anticipation:
                effect += 0.45 * lead
            rows.append(
                {
                    "unit": unit,
                    "year": year,
                    "y": round(2.0 + unit * 0.09 + (year - periods[0]) * 0.07 + effect, 4),
                    "treat": treated_now,
                    "post": int(year >= first_policy),
                    "gvar": gvar,
                    "x1": round(unit * 0.11 + (year - periods[0]) * 0.04, 4),
                }
            )
    return rows


def _simple_contract(name: str, *, anticipation_periods: int = 0) -> str:
    return f"""panel:
  unit_id: unit
  time_id: year
  outcome: y
  treatment: treat
  covariates:
    - x1
policy:
  name: {name}
  level: unit
  treatment_coding: simple_2x2
  anticipation_periods: {anticipation_periods}
"""


def _staggered_contract(name: str, *, anticipation_periods: int = 0) -> str:
    return f"""panel:
  unit_id: unit
  time_id: year
  outcome: y
  treatment: treat
  first_treat_year: gvar
  covariates:
    - x1
policy:
  name: {name}
  level: unit
  treatment_coding: staggered_adoption
  anticipation_periods: {anticipation_periods}
"""


def _fixture_catalog() -> list[DidFixture]:
    staggered_good = {1: 2018, 2: 2018, 3: 2019, 4: 2019, 5: 2020, 6: 2020, 7: 0, 8: 0}
    staggered_no_never = {1: 2018, 2: 2018, 3: 2019, 4: 2019, 5: 2020, 6: 2020}
    weak_pre = {1: 2017, 2: 2018, 3: 0}
    few_cohorts = {1: 2018, 2: 2018, 3: 2019, 4: 2019, 5: 0, 6: 0}

    return [
        DidFixture(
            name="two_by_two_clean",
            rows=_simple_panel([2018, 2019]),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "post": "post"},
            contract=_simple_contract("two_by_two_clean"),
            expected_design_type="two_by_two",
        ),
        DidFixture(
            name="single_timing_never_treated",
            rows=_simple_panel([2016, 2017, 2018, 2019, 2020, 2021]),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "post": "post"},
            contract=_simple_contract("single_timing_never_treated"),
            expected_design_type="single_timing",
        ),
        DidFixture(
            name="staggered_with_never_treated",
            rows=_staggered_panel(staggered_good, list(range(2015, 2023))),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "gvar": "gvar"},
            contract=_staggered_contract("staggered_with_never_treated"),
            expected_design_type="staggered_adoption",
        ),
        DidFixture(
            name="staggered_no_never_treated",
            rows=_staggered_panel(staggered_no_never, list(range(2015, 2023))),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "gvar": "gvar"},
            contract=_staggered_contract("staggered_no_never_treated"),
            expected_design_type="staggered_adoption",
            expected_risks=("NO_NEVER_TREATED",),
        ),
        DidFixture(
            name="weak_pretrend_only_two_pre",
            rows=_staggered_panel(weak_pre, [2015, 2016, 2017, 2018, 2019, 2020]),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "gvar": "gvar"},
            contract=_staggered_contract("weak_pretrend_only_two_pre"),
            expected_design_type="staggered_adoption",
            expected_risks=("WEAK_PRETREND_PERIODS", "FEW_TREATED_COHORTS"),
        ),
        DidFixture(
            name="few_cohorts",
            rows=_staggered_panel(few_cohorts, list(range(2014, 2023))),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "gvar": "gvar"},
            contract=_staggered_contract("few_cohorts"),
            expected_design_type="staggered_adoption",
            expected_risks=("FEW_TREATED_COHORTS",),
        ),
        DidFixture(
            name="twfe_modern_did_flip",
            rows=_staggered_panel(staggered_good, list(range(2015, 2023))),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "gvar": "gvar"},
            contract=_staggered_contract("twfe_modern_did_flip"),
            expected_design_type="staggered_adoption",
        ),
        DidFixture(
            name="unbalanced_panel_high_loss",
            rows=_staggered_panel(
                staggered_good,
                list(range(2015, 2023)),
                drop_rule=lambda unit, year: (unit == 7 and year > 2016) or (unit == 8 and year < 2021),
            ),
            spec={"id": "unit", "time": "year", "y": "y", "treat": "treat", "gvar": "gvar"},
            contract=_staggered_contract("unbalanced_panel_high_loss"),
            expected_design_type="staggered_adoption",
            expected_risks=("UNBALANCED_PANEL_HIGH_LOSS",),
        ),
        DidFixture(
            name="anticipation_effect",
            rows=_staggered_panel(staggered_good, list(range(2015, 2023)), anticipation=True),
            spec={
                "id": "unit",
                "time": "year",
                "y": "y",
                "treat": "treat",
                "gvar": "gvar",
                "anticipation_periods": 1,
            },
            contract=_staggered_contract("anticipation_effect", anticipation_periods=1),
            expected_design_type="staggered_adoption",
            expected_risks=("ANTICIPATION_RISK",),
        ),
    ]


DID_FIXTURE_NAMES = tuple(item.name for item in _fixture_catalog())


def _write_csv(path: Path, rows: list[dict[str, float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def materialize_did_fixtures(base_dir: Path = BASE_DIR) -> list[Path]:
    written: list[Path] = []
    for fixture in _fixture_catalog():
        csv_path = base_dir / f"{fixture.name}.csv"
        _write_csv(csv_path, fixture.rows)
        (base_dir / f"{fixture.name}.data_contract.yaml").write_text(fixture.contract, encoding="utf-8")
        (base_dir / f"{fixture.name}.expected_design.json").write_text(
            json.dumps(
                {
                    "fixture": fixture.name,
                    "spec": fixture.spec,
                    "expected_design_type": fixture.expected_design_type,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (base_dir / f"{fixture.name}.expected_risks.json").write_text(
            json.dumps(
                {
                    "fixture": fixture.name,
                    "expected_risks": list(fixture.expected_risks),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        written.append(csv_path)
    return written


if __name__ == "__main__":
    paths = materialize_did_fixtures()
    print(json.dumps({"fixtures": [path.name for path in paths]}, indent=2))
