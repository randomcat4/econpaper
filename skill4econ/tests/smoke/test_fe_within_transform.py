from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from skill4econ.core import make_run_context
from skill4econ.python_wrappers import _ols_numpy, did_twfe_event


def _twfe_panel(n_units: int, years: list[int]) -> pd.DataFrame:
    rows = []
    first_post = years[len(years) // 2]
    for unit in range(n_units):
        treat = int(unit < n_units // 2)
        unit_fe = unit / 100
        for year in years:
            post = int(year >= first_post)
            time_fe = (year - years[0]) / 10
            did = treat * post
            y = unit_fe + time_fe + 1.5 * did + ((unit * 17 + year) % 7) / 1000
            rows.append({"unit": unit, "year": year, "treat": treat, "post": post, "y": y})
    return pd.DataFrame(rows)


def test_twfe_within_matches_old_dummy_cluster_se_on_small_panel(tmp_path: Path) -> None:
    df = _twfe_panel(10, [2017, 2018, 2019, 2020])
    data_path = tmp_path / "twfe.csv"
    df.to_csv(data_path, index=False)
    ctx = make_run_context(
        "did_twfe_event",
        "python",
        {"data": str(data_path), "y": "y", "treat": "treat", "post": "post", "id": "unit", "time": "year"},
        "run",
        str(tmp_path / "runs"),
    )

    did_twfe_event(ctx)
    new_row = pd.read_csv(ctx.artifact("model_table.csv")).set_index("term").loc["_did_treat_post"]

    work = df.copy()
    work["_did_treat_post"] = work["treat"].astype(float) * work["post"].astype(float)
    design = work[["_did_treat_post"]].copy()
    design = design.join(pd.get_dummies(work["unit"].astype(str), prefix="fe_unit", drop_first=True))
    design = design.join(pd.get_dummies(work["year"].astype(str), prefix="fe_year", drop_first=True))
    design["_const"] = 1.0
    design["y"] = work["y"].to_numpy()
    design["unit"] = work["unit"].to_numpy()
    terms = ["_const", "_did_treat_post", *[c for c in design.columns if c not in {"y", "unit", "_const", "_did_treat_post"}]]
    old_rows, _ = _ols_numpy(design, "y", terms, cluster="unit")
    old_row = next(row for row in old_rows if row["term"] == "_did_treat_post")

    assert new_row["coef"] == pytest.approx(old_row["coef"], abs=1e-8)
    assert new_row["std_error"] == pytest.approx(old_row["std_error"], abs=1e-8)


def test_twfe_within_handles_large_absorbed_fe_without_dummy_expansion(tmp_path: Path) -> None:
    df = _twfe_panel(2105, [2019, 2020])
    data_path = tmp_path / "large_twfe.csv"
    df.to_csv(data_path, index=False)
    ctx = make_run_context(
        "did_twfe_event",
        "python",
        {"data": str(data_path), "y": "y", "treat": "treat", "post": "post", "id": "unit", "time": "year"},
        "run",
        str(tmp_path / "runs"),
    )

    manifest = did_twfe_event(ctx)
    table = pd.read_csv(ctx.artifact("model_table.csv")).set_index("term")

    assert manifest["fe_transform"] == "alternating_within_demeaning"
    assert manifest["absorbed_fe_rank"] > 2000
    assert "_did_treat_post" in table.index
