from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skill4econ.adapters.did_common import build_common_output
from skill4econ.adapters.r import base as r_base
from skill4econ.adapters.r import did_att_gt, didimputation, drdid as r_drdid, fixest, honestdid as r_honestdid
from skill4econ.adapters.stata import bacondecomp, csdid, did_imputation, drdid, eventstudyinteract, honestdid, reghdfe
from skill4econ.core import make_run_context
from skill4econ.python_wrappers import cs_did_attgt_py


STATA_MODULES = [reghdfe, csdid, drdid, did_imputation, eventstudyinteract, bacondecomp, honestdid]
R_MODULES = [did_att_gt, r_drdid, didimputation, r_honestdid, fixest]


def _write_model_table(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["term", "coef", "std_error", "p_value"])
        writer.writeheader()
        writer.writerow({"term": "ATT", "coef": "1.25", "std_error": "0.10", "p_value": "0.001"})


def test_stata_adapter_facades_have_smokeable_interface(tmp_path: Path) -> None:
    step_dir = tmp_path / "step"
    _write_model_table(step_dir / "model_table.csv")
    for module in STATA_MODULES:
        assert module.ADAPTER["name"]
        plan = module.render({"y": "y", "id": "unit", "time": "year"})
        assert plan["engine"] == "stata"
        skipped = module.skipped_backend_unavailable("staggered_adoption", "forced smoke missing backend")
        assert skipped["status"] == "skipped_backend_unavailable"
        if hasattr(module, "parse_result"):
            parsed = module.parse_result(
                str(step_dir),
                {"status": "ok", "backend": module.ADAPTER["backend"]},
                {"control_group": "never_treated"},
                "staggered_adoption",
            )
            assert parsed["status"] == "success"
            assert parsed["main_effect"]["estimate"] == 1.25


def test_r_adapter_facades_skip_without_fake_results() -> None:
    for module in R_MODULES:
        assert module.ADAPTER["name"]
        plan = module.render({"y": "y", "id": "unit", "time": "year"})
        assert plan["engine"] == "r"
        assert plan["status"] in {"interface_only_until_r_smoke", "ready_for_rscript"}
        skipped = module.skipped_backend_unavailable("staggered_adoption", "Rscript/package missing")
        assert skipped["status"] == "skipped_backend_unavailable"
        assert skipped["main_effect"]["estimate"] is None


def test_r_adapter_prefers_explicit_rscript_env(monkeypatch) -> None:
    rscript = r"C:\custom-r\Rscript.exe"
    monkeypatch.setenv("SKILL4ECON_RSCRIPT", rscript)
    monkeypatch.setattr("shutil.which", lambda name: None)

    assert r_base._rscript_path() == rscript


def test_common_output_schema_from_model_table(tmp_path: Path) -> None:
    step_dir = tmp_path / "twfe"
    _write_model_table(step_dir / "model_table.csv")
    payload = build_common_output(
        estimator="twfe",
        design_type="two_by_two",
        step_dir=step_dir,
        status="ok",
        manifest={"nobs": 100},
        spec={"control_group": "never_treated"},
        backend="python_or_stata_twfe",
        engine="stata",
        role="main_or_benchmark",
    )
    assert payload["status"] == "success"
    assert payload["main_effect"]["estimate"] == 1.25
    assert payload["main_effect"]["ci_low"] < payload["main_effect"]["estimate"]


def test_python_cs_did_adapter_missing_dependency_fails_closed(tmp_path: Path) -> None:
    if importlib.util.find_spec("differences") is not None:
        pytest.skip("differences installed; missing-dependency branch is environment-specific")
    rows = []
    for unit, gvar in {1: 2018, 2: 2019, 3: 0}.items():
        for year in [2016, 2017, 2018, 2019, 2020]:
            treated = int(bool(gvar) and year >= gvar)
            rows.append({"unit": unit, "year": year, "gvar": gvar, "y": unit + year / 100 + treated})
    data_path = tmp_path / "staggered.csv"
    pd.DataFrame(rows).to_csv(data_path, index=False)
    ctx = make_run_context(
        "cs_did_attgt_py",
        "python",
        {"data": str(data_path), "y": "y", "id": "unit", "time": "year", "gvar": "gvar"},
        "run",
        str(tmp_path / "runs"),
    )

    manifest = cs_did_attgt_py(ctx)

    assert manifest["status"] == "missing_dependency"
    assert manifest["package"] == "differences"
    assert ctx.artifact("backend_unavailable.md").exists()


def test_r_fixest_parser_fixture_and_malformed_failure() -> None:
    fixture_dir = ROOT / "skill4econ" / "tests" / "fixtures" / "r"
    rows = fixest.parse_result_file(fixture_dir / "fixest_result.json")
    assert rows[0]["term"] == "_did_treat_post"
    assert rows[0]["coef"] == 1.25
    with pytest.raises(Exception):
        fixest.parse_result_file(fixture_dir / "fixest_malformed.json")


def test_r_fixest_missing_rscript_is_interface_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SKILL4ECON_RSCRIPT", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None if name == "Rscript" else None)
    data = tmp_path / "panel.csv"
    pd.DataFrame(
        {
            "unit": [1, 1, 2, 2],
            "year": [2019, 2020, 2019, 2020],
            "y": [1.0, 2.0, 1.5, 2.8],
            "treat": [0, 0, 1, 1],
            "post": [0, 1, 0, 1],
        }
    ).to_csv(data, index=False)
    ctx = make_run_context(
        "fixest_twfe",
        "r",
        {"data": str(data), "y": "y", "id": "unit", "time": "year", "treat": "treat", "post": "post"},
        "run",
        str(tmp_path / "runs"),
    )

    manifest = fixest.execute(ctx)

    assert manifest["status"] == "interface_only"
    assert manifest["backend"] == "r_fixest"
    assert ctx.artifact("r_backend_status.json").exists()


def test_cli_exposes_r_fixest_handler() -> None:
    from skill4econ.cli import _handler

    assert _handler("r", "fixest_twfe") is fixest.execute
