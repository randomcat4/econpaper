from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from skill4econ.core import make_run_context
from skill4econ.python_wrappers import quantile_regression


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "quantile" / "median_known_coefficients.csv"


def test_quantile_regression_statsmodels_reports_inference(tmp_path: Path) -> None:
    pytest.importorskip("statsmodels.regression.quantile_regression", reason="statsmodels QuantReg is unavailable")
    ctx = make_run_context(
        "quantile_regression",
        "python",
        {"data": str(FIXTURE), "y": "y", "x": ["x1", "x2"], "quantile": 0.5},
        "run",
        str(tmp_path / "runs"),
    )

    manifest = quantile_regression(ctx)
    table = pd.read_csv(ctx.artifact("model_table.csv")).set_index("term")

    assert manifest["status"] == "ok"
    assert manifest["estimator"] == "statsmodels.QuantReg"
    assert table.loc["_intercept", "coef"] == pytest.approx(1.0, abs=0.01)
    assert table.loc["x1", "coef"] == pytest.approx(2.0, abs=0.01)
    assert table.loc["x2", "coef"] == pytest.approx(-0.5, abs=0.03)
    for term in ["_intercept", "x1", "x2"]:
        assert table.loc[term, "std_error"] > 0
        assert table.loc[term, "p_value"] >= 0
        assert table.loc[term, "ci_low"] < table.loc[term, "coef"] < table.loc[term, "ci_high"]
