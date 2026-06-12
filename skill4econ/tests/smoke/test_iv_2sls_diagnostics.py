from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from skill4econ.core import make_run_context
from skill4econ.python_wrappers import iv_2sls


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "iv"


def _run_iv(path: Path, tmp_path: Path):
    pytest.importorskip("linearmodels.iv", reason="linearmodels is unavailable")
    ctx = make_run_context(
        "iv_2sls",
        "python",
        {
            "data": str(path),
            "y": "y",
            "x": ["x"],
            "endog": "endog",
            "instrument": "z",
        },
        "run",
        str(tmp_path / "runs"),
    )
    manifest = iv_2sls(ctx)
    first_stage = json.loads(ctx.artifact("iv_first_stage.json").read_text(encoding="utf-8"))
    model = pd.read_csv(ctx.artifact("model_table.csv"))
    return ctx, manifest, first_stage, model


def test_iv_2sls_strong_first_stage_stays_paper_ready(tmp_path: Path) -> None:
    _ctx, manifest, first_stage, model = _run_iv(FIXTURE_DIR / "strong_iv.csv", tmp_path)
    diagnostic = first_stage["diagnostics"][0]
    f_row = model.loc[model["term"] == "first_stage_F_endog"].iloc[0]

    assert manifest["status"] == "ok"
    assert manifest["claim_level"] == "main_estimate"
    assert manifest["paper_readiness"] == "paper_ready"
    assert manifest["main_claim_available"] is True
    assert diagnostic["partial_f_stat"] > 100
    assert f_row["coef"] == pytest.approx(diagnostic["partial_f_stat"])
    assert "IV_WEAK_INSTRUMENT" not in manifest["risk_codes"]


def test_iv_2sls_weak_first_stage_degrades_to_not_for_claim(tmp_path: Path) -> None:
    ctx, manifest, first_stage, model = _run_iv(FIXTURE_DIR / "weak_iv.csv", tmp_path)
    diagnostic = first_stage["diagnostics"][0]
    f_row = model.loc[model["term"] == "first_stage_F_endog"].iloc[0]
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    weak_risk = next(item for item in risk["risks"] if item["code"] == "IV_WEAK_INSTRUMENT")

    assert manifest["status"] == "ok"
    assert manifest["paper_readiness"] == "not_for_claim"
    assert manifest["main_claim_available"] is False
    assert diagnostic["partial_f_stat"] <= 2
    assert f_row["coef"] == pytest.approx(diagnostic["partial_f_stat"])
    assert "IV_WEAK_INSTRUMENT" in manifest["risk_codes"]
    assert weak_risk["claim_degradation"] == "not_for_claim"
