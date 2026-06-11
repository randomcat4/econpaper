from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURE_DIR = ROOT / "skill4econ" / "tests" / "fixtures" / "did"
if str(FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURE_DIR))

from generate_did_fixtures import DID_FIXTURE_NAMES, materialize_did_fixtures
from skill4econ.contracts.data_contract import load_data_contract, validate_data_contract
from skill4econ.contracts.estimator_registry import route_did_estimators
from skill4econ.diagnostics.did_design import detect_did_design
from skill4econ.reporting.did_comparison import build_did_estimator_comparison


def _timing_panel(gvars: dict[int, int], periods: list[int]) -> pd.DataFrame:
    rows = []
    for unit, gvar in gvars.items():
        for year in periods:
            treat = int(bool(gvar) and year >= gvar)
            post = int(year >= min([g for g in gvars.values() if g] or [year]))
            rows.append(
                {
                    "unit": unit,
                    "year": year,
                    "y": unit * 0.1 + year * 0.01 + treat,
                    "treat": treat,
                    "ever": int(bool(gvar)),
                    "post": post,
                    "gvar": gvar,
                    "x1": unit * 0.2,
                }
            )
    return pd.DataFrame(rows)


def _simple_panel(periods: list[int]) -> pd.DataFrame:
    rows = []
    first_post = periods[len(periods) // 2]
    for unit in range(1, 9):
        ever = int(unit <= 4)
        for year in periods:
            post = int(year >= first_post)
            rows.append(
                {
                    "unit": unit,
                    "year": year,
                    "y": unit * 0.1 + year * 0.01 + ever * post,
                    "treat": ever,
                    "post": post,
                    "x1": unit * 0.2,
                }
            )
    return pd.DataFrame(rows)


def _codes(design: dict) -> set[str]:
    return {item["code"] for item in design.get("reviewer_warnings") or []}


def _write_common_output(step_dir: Path, *, estimator: str, estimate: float) -> Path:
    step_dir.mkdir(parents=True, exist_ok=True)
    path = step_dir / "did_common_output.json"
    payload = {
        "status": "success",
        "estimator": estimator,
        "main_effect": {
            "term": "ATT",
            "estimate": estimate,
            "std_error": 0.1,
            "ci_low": estimate - 0.196,
            "ci_high": estimate + 0.196,
            "p_value": 0.01,
            "source_path": str(step_dir / "model_table.csv"),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_did_design_detector_synthetic_cases() -> None:
    cases = [
        (
            "two_by_two_clean",
            _simple_panel([2018, 2019]),
            {"id": "unit", "time": "year", "y": "y", "treat": "treat", "post": "post"},
            "two_by_two",
            set(),
        ),
        (
            "single_timing_never_treated",
            _simple_panel([2016, 2017, 2018, 2019, 2020, 2021]),
            {"id": "unit", "time": "year", "y": "y", "treat": "treat", "post": "post"},
            "single_timing",
            set(),
        ),
        (
            "staggered_with_never_treated",
            _timing_panel({1: 2018, 2: 2019, 3: 2020, 4: 0}, [2015, 2016, 2017, 2018, 2019, 2020, 2021]),
            {"id": "unit", "time": "year", "y": "y", "gvar": "gvar"},
            "staggered_adoption",
            set(),
        ),
        (
            "staggered_no_never_treated",
            _timing_panel({1: 2018, 2: 2019, 3: 2020}, [2015, 2016, 2017, 2018, 2019, 2020, 2021]),
            {"id": "unit", "time": "year", "y": "y", "gvar": "gvar"},
            "staggered_adoption",
            {"NO_NEVER_TREATED"},
        ),
        (
            "weak_pretrend_only_two_pre",
            _timing_panel({1: 2017, 2: 2018, 3: 0}, [2015, 2016, 2017, 2018, 2019]),
            {"id": "unit", "time": "year", "y": "y", "gvar": "gvar"},
            "staggered_adoption",
            {"WEAK_PRETREND_PERIODS", "FEW_TREATED_COHORTS"},
        ),
        (
            "few_cohorts",
            _timing_panel({1: 2018, 2: 2019, 3: 0}, [2015, 2016, 2017, 2018, 2019, 2020]),
            {"id": "unit", "time": "year", "y": "y", "gvar": "gvar"},
            "staggered_adoption",
            {"FEW_TREATED_COHORTS"},
        ),
        (
            "unbalanced_panel_high_loss",
            _timing_panel({1: 2018, 2: 2019, 3: 0}, [2015, 2016, 2017, 2018, 2019, 2020]).iloc[:10].copy(),
            {"id": "unit", "time": "year", "y": "y", "gvar": "gvar"},
            "staggered_adoption",
            {"UNBALANCED_PANEL_HIGH_LOSS"},
        ),
    ]
    for name, df, spec, expected_design, expected_risks in cases:
        design = detect_did_design(df, spec)
        assert design["design_type"] == expected_design, name
        assert expected_risks.issubset(_codes(design)), name
        if name == "staggered_no_never_treated":
            assert design["all_treated"] is True


def test_static_did_fixtures_match_expected_sidecars() -> None:
    paths = materialize_did_fixtures(FIXTURE_DIR)
    assert {path.name for path in paths} == {f"{name}.csv" for name in DID_FIXTURE_NAMES}

    for name in DID_FIXTURE_NAMES:
        df = pd.read_csv(FIXTURE_DIR / f"{name}.csv")
        contract = load_data_contract(FIXTURE_DIR / f"{name}.data_contract.yaml")
        expected_design = json.loads((FIXTURE_DIR / f"{name}.expected_design.json").read_text(encoding="utf-8"))
        expected_risks = json.loads((FIXTURE_DIR / f"{name}.expected_risks.json").read_text(encoding="utf-8"))

        validation = validate_data_contract(contract, df, base_dir=FIXTURE_DIR)
        assert validation["valid"], name

        design = detect_did_design(df, expected_design["spec"], contract)
        assert design["design_type"] == expected_design["expected_design_type"], name
        assert set(expected_risks["expected_risks"]).issubset(_codes(design)), name


def test_did_comparison_flags_twfe_modern_direction_flip(tmp_path: Path) -> None:
    twfe_dir = tmp_path / "steps" / "twfe"
    cs_dir = tmp_path / "steps" / "cs_did_attgt"
    twfe_common = _write_common_output(twfe_dir, estimator="twfe", estimate=0.8)
    cs_common = _write_common_output(cs_dir, estimator="cs_did_attgt", estimate=-0.5)
    routing = {
        "selected_estimators": [
            {"label": "twfe_step", "estimator": "twfe", "role": "benchmark_not_main", "backend": "python"},
            {"label": "cs_step", "estimator": "cs_did_attgt", "role": "main", "backend": "stata"},
        ],
        "skipped_estimators": [],
    }
    rows, warnings = build_did_estimator_comparison(
        run_dir=tmp_path,
        step_results=[
            {
                "label": "twfe_step",
                "run_dir": str(twfe_dir),
                "did_common_output": str(twfe_common),
                "status": "ok",
                "engine": "python",
                "manifest": {"backend": "python"},
            },
            {
                "label": "cs_step",
                "run_dir": str(cs_dir),
                "did_common_output": str(cs_common),
                "status": "ok",
                "engine": "stata",
                "manifest": {"backend": "stata"},
            },
        ],
        routing=routing,
        did_design={"design_type": "staggered_adoption", "has_never_treated": True},
        spec={"id": "unit", "cluster": "unit"},
    )
    assert {row["estimator"] for row in rows} == {"twfe", "cs_did_attgt"}
    assert "twfe_modern_did_disagree" in {warning["code"] for warning in warnings}
    assert (tmp_path / "tables" / "did_estimator_comparison.csv").exists()


def test_did_design_detector_continuous_and_repeated_cross_section() -> None:
    df = _simple_panel([2018, 2019, 2020])
    df["dose"] = df["unit"] * 0.1 + (df["year"] - 2018) * 0.2
    continuous = detect_did_design(df, {"id": "unit", "time": "year", "y": "y", "treat": "dose", "post": "post"})
    assert continuous["design_type"] == "continuous_treatment"
    assert "CONTINUOUS_TREATMENT_NOT_SUPPORTED" in _codes(continuous)

    rc = df.drop(columns=["unit"])
    repeated = detect_did_design(
        rc,
        {"data_type": "repeated_cross_section", "time": "year", "y": "y", "treat": "treat", "post": "post"},
    )
    assert repeated["design_type"] == "repeated_cross_section"


def test_did_estimator_router_respects_design_and_backends() -> None:
    dep = {"stata": {"available": True}, "r": {"available": False}, "modules": {}}
    staggered = detect_did_design(
        _timing_panel({1: 2018, 2: 2019, 3: 2020, 4: 0}, [2015, 2016, 2017, 2018, 2019, 2020]),
        {"id": "unit", "time": "year", "y": "y", "gvar": "gvar"},
    )
    route = route_did_estimators(staggered, spec={"engine_policy": "stata_first"}, dependency_report=dep)
    selected = {item["estimator"]: item for item in route["selected_estimators"]}
    assert {"cs_did_attgt", "did_imputation", "twfe"}.issubset(selected)
    assert selected["twfe"]["role"] == "benchmark_not_main"
    assert selected["cs_did_attgt"]["main_allowed"] is True

    two_by_two = detect_did_design(
        _simple_panel([2018, 2019]),
        {"id": "unit", "time": "year", "y": "y", "treat": "treat", "post": "post"},
    )
    route = route_did_estimators(two_by_two, spec={"engine_policy": "stata_first"}, dependency_report=dep)
    selected = {item["estimator"]: item for item in route["selected_estimators"]}
    assert {"drdid", "twfe"}.issubset(selected)
    assert selected["twfe"]["main_allowed"] is True
    assert selected["twfe"]["critical"] is True

    no_stata = {"stata": {"available": False}, "r": {"available": False}, "modules": {}}
    route = route_did_estimators(staggered, spec={"engine_policy": "stata_first"}, dependency_report=no_stata)
    skipped = {item["estimator"]: item["reason"] for item in route["skipped_estimators"]}
    assert "cs_did_attgt" in skipped
    assert any(item["engine"] == "python" for item in route["selected_estimators"])
