from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skill4econ.adapters.did_common import build_common_output
from skill4econ.adapters.r import did_att_gt, didimputation, drdid as r_drdid, fixest, honestdid as r_honestdid
from skill4econ.adapters.stata import bacondecomp, csdid, did_imputation, drdid, eventstudyinteract, honestdid, reghdfe


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
        assert plan["status"] == "interface_only_until_r_smoke"
        skipped = module.skipped_backend_unavailable("staggered_adoption", "Rscript/package missing")
        assert skipped["status"] == "skipped_backend_unavailable"
        assert skipped["main_effect"]["estimate"] is None


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
