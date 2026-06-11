from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PSM_FIXTURE_DIR = ROOT / "skill4econ" / "tests" / "fixtures" / "psm_did"
if str(PSM_FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(PSM_FIXTURE_DIR))

from generate_psm_did_fixtures import PSM_DID_FIXTURE_NAMES, materialize_psm_did_fixtures
from skill4econ.core import make_run_context
from skill4econ.diagnostics.overlap_balance import run_overlap_balance_diagnostics
from skill4econ.python_wrappers import psm_overlap_balance
from skill4econ.workflows import _psm_did_postprocess


def _codes(result: dict) -> set[str]:
    return {item["code"] for item in result.get("warnings") or []}


def _good_overlap() -> pd.DataFrame:
    rows = []
    unit = 0
    for k in range(90):
        x1 = (k % 45) / 12
        x2 = ((k * 7) % 31) / 10
        for treat in [0, 1]:
            y = 1.0 + 0.4 * x1 + 0.2 * x2 + 0.8 * treat + ((k * 13) % 17) / 100
            rows.append({"unit": unit, "year": 2020, "y": y, "treat": treat, "x1": x1, "x2": x2})
            unit += 1
    return pd.DataFrame(rows)


def _poor_overlap() -> pd.DataFrame:
    rows = []
    for i in range(90):
        x1 = -4.0 + i / 80
        rows.append({"unit": i, "year": 2020, "y": 1.0 + x1 * 0.1, "treat": 0, "x1": x1, "x2": x1 * 0.2})
    for i in range(90):
        x1 = 4.0 + i / 80
        rows.append({"unit": i + 90, "year": 2020, "y": 2.0 + x1 * 0.1, "treat": 1, "x1": x1, "x2": x1 * 0.2})
    return pd.DataFrame(rows)


def _poor_balance_after_adjustment() -> pd.DataFrame:
    rows = []
    for i in range(200):
        treat = i % 2
        x1 = (i % 50) / 20
        x2 = 3.0 * treat + ((i * 5) % 23) / 20
        y = 1.0 + 0.2 * x1 + 0.7 * x2 + 0.5 * treat
        rows.append({"unit": i, "year": 2020, "y": y, "treat": treat, "x1": x1, "x2": x2})
    return pd.DataFrame(rows)


def _extreme_weight_scores() -> pd.DataFrame:
    rows = []
    for i in range(200):
        treat = i % 2
        ps = 0.5
        if i in {0, 2}:
            treat = 1
            ps = 0.01
        if i in {1, 3}:
            treat = 0
            ps = 0.99
        x1 = (i % 50) / 20
        x2 = ((i * 11) % 37) / 15
        y = 1.0 + 0.2 * x1 + 0.2 * x2 + treat
        rows.append({"unit": i, "year": 2020, "y": y, "treat": treat, "x1": x1, "x2": x2, "ps": ps})
    return pd.DataFrame(rows)


def _grid_unstable_scores() -> pd.DataFrame:
    rows = []
    unit = 0
    for i in range(12):
        ps = 0.50 + (i - 6) * 0.0005
        rows.append({"unit": unit, "year": 2020, "y": 1.0, "treat": 1, "x1": ps, "x2": 0.0, "ps": ps})
        unit += 1
    rows.append({"unit": unit, "year": 2020, "y": 0.0, "treat": 0, "x1": 0.50, "x2": 0.0, "ps": 0.50})
    unit += 1
    for i in range(60):
        ps = 0.54 + (i % 12) * 0.0005
        rows.append({"unit": unit, "year": 2020, "y": 4.0, "treat": 0, "x1": ps, "x2": 0.0, "ps": ps})
        unit += 1
    return pd.DataFrame(rows)


def _base_spec() -> dict:
    return {"id": "unit", "time": "year", "y": "y", "treat": "treat", "x": ["x1", "x2"]}


def _write_model_table(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_overlap_good_fixture_has_artifacts_without_overlap_risk(tmp_path: Path) -> None:
    result = run_overlap_balance_diagnostics(_good_overlap(), _base_spec(), tmp_path)
    assert not {"POOR_OVERLAP", "OFF_SUPPORT_HIGH_SHARE", "BALANCE_STILL_POOR"} & _codes(result)
    for rel in [
        "tables/propensity_summary.csv",
        "tables/off_support_units.csv",
        "tables/psm_grid_results.csv",
        "figures/propensity_overlap_density.png",
        "figures/propensity_overlap_hist.png",
        "figures/psm_grid_forest.png",
    ]:
        assert (tmp_path / rel).exists()


def test_overlap_poor_fixture_triggers_overlap_risks(tmp_path: Path) -> None:
    result = run_overlap_balance_diagnostics(_poor_overlap(), _base_spec(), tmp_path)
    codes = _codes(result)
    assert "POOR_OVERLAP" in codes
    assert "OFF_SUPPORT_HIGH_SHARE" in codes


def test_extreme_weight_fixture_triggers_weight_risks(tmp_path: Path) -> None:
    spec = {**_base_spec(), "pscore_col": "ps"}
    result = run_overlap_balance_diagnostics(_extreme_weight_scores(), spec, tmp_path)
    codes = _codes(result)
    assert "EXTREME_IPW_WEIGHTS" in codes
    assert "LOW_EFFECTIVE_SAMPLE_SIZE" in codes
    assert (tmp_path / "tables" / "weight_summary.csv").exists()
    assert (tmp_path / "figures" / "weight_histogram.png").exists()


def test_balance_still_poor_fixture_and_love_plot_order(tmp_path: Path) -> None:
    spec = {"id": "unit", "time": "year", "y": "y", "treat": "treat", "x": ["x1"], "balance_vars": ["x1", "x2"]}
    result = run_overlap_balance_diagnostics(_poor_balance_after_adjustment(), spec, tmp_path)
    assert "BALANCE_STILL_POOR" in _codes(result)
    before = pd.read_csv(tmp_path / "tables" / "balance_table_before.csv")
    after_ipw = pd.read_csv(tmp_path / "tables" / "balance_table_after_ipw.csv")
    assert before["abs_smd"].tolist() == sorted(before["abs_smd"].tolist(), reverse=True)
    assert before.iloc[0]["variable"] == "x2"
    assert set(before["smd_denominator_source"]) == {"unweighted_pooled_pre_adjustment_sd"}
    assert set(after_ipw["smd_denominator_source"]) == {"unweighted_pooled_pre_adjustment_sd"}
    denom_before = before.set_index("variable")["smd_denominator"].to_dict()
    denom_after = after_ipw.set_index("variable")["smd_denominator"].to_dict()
    assert denom_after["x2"] == pytest.approx(denom_before["x2"])
    assert (tmp_path / "figures" / "love_plot.png").exists()


def test_psm_grid_sample_loss_and_instability_risks(tmp_path: Path) -> None:
    sample_loss = run_overlap_balance_diagnostics(_poor_overlap(), _base_spec(), tmp_path / "loss")
    assert "PSM_SAMPLE_LOSS_HIGH" in _codes(sample_loss)

    spec = {
        **_base_spec(),
        "pscore_col": "ps",
        "psm_grid_neighbors": [1, 5],
        "psm_grid_calipers": [0.01, 0.05],
        "psm_grid_replacement": [True],
    }
    unstable = run_overlap_balance_diagnostics(_grid_unstable_scores(), spec, tmp_path / "unstable")
    assert "TRIM_SENSITIVITY_UNSTABLE" in _codes(unstable)
    assert "PSM_NAIVE_SE_NOT_ABADIE_IMBENS" in _codes(unstable)
    grid = pd.read_csv(tmp_path / "unstable" / "tables" / "psm_grid_results.csv")
    assert "naive_matched_pair_sd_not_abadie_imbens" in set(grid["std_error_method"].astype(str))


def test_psm_overlap_balance_wrapper_registers_manifest_artifacts(tmp_path: Path) -> None:
    data_path = tmp_path / "overlap_good.csv"
    _good_overlap().to_csv(data_path, index=False)
    spec = {**_base_spec(), "data": str(data_path)}
    ctx = make_run_context("psm_overlap_balance", "python", spec, "run", str(tmp_path / "runs"))
    manifest = psm_overlap_balance(ctx)
    assert manifest["status"] == "ok"
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in artifact_manifest["artifacts"]}
    for rel in [
        "tables/propensity_summary.csv",
        "tables/balance_table_after_ipw.csv",
        "tables/balance_table_after_trimmed_ipw.csv",
        "tables/weight_summary.csv",
        "tables/psm_grid_results.csv",
        "figures/love_plot.png",
        "figures/weight_histogram.png",
        "figures/psm_grid_forest.png",
    ]:
        assert rel in paths


def test_trimmed_weights_reduction_is_recorded_in_run_log(tmp_path: Path) -> None:
    data_path = tmp_path / "extreme_weights.csv"
    _extreme_weight_scores().to_csv(data_path, index=False)
    spec = {
        **_base_spec(),
        "data": str(data_path),
        "pscore_col": "ps",
        "extreme_weight_threshold": 30,
    }
    ctx = make_run_context("psm_overlap_balance", "python", spec, "run", str(tmp_path / "runs"))
    psm_overlap_balance(ctx)
    run_log = ctx.artifact("run_log.md").read_text(encoding="utf-8")
    assert "trim_weights_reduced_risk" in run_log


def test_psm_did_postprocess_writes_adjusted_did_outputs_and_disagreement_risk(tmp_path: Path) -> None:
    ctx = make_run_context("psm_did_policy_run", "workflow", {}, "run", str(tmp_path / "runs"))
    psm_dir = tmp_path / "steps" / "psm"
    twfe_dir = tmp_path / "steps" / "twfe"
    drdid_dir = tmp_path / "steps" / "drdid"
    _write_model_table(
        psm_dir / "model_table.csv",
        [
            {"term": "ATT_nearest_neighbor", "coef": 0.8, "std_error": 0.2, "p_value": 0.01},
            {"term": "ATT_ipw", "coef": 0.7, "std_error": 0.2, "p_value": 0.02},
        ],
    )
    _write_model_table(twfe_dir / "model_table.csv", [{"term": "_did_treat_post", "coef": 0.4, "std_error": 0.1, "p_value": 0.05}])
    _write_model_table(drdid_dir / "model_table.csv", [{"term": "ATT", "coef": -0.6, "std_error": 0.2, "p_value": 0.01}])
    (drdid_dir / "stata.log").write_text("fake drdid log\n", encoding="utf-8")

    warnings = _psm_did_postprocess(
        ctx,
        [
            {"label": "propensity_overlap", "status": "ok", "run_dir": str(psm_dir)},
            {"label": "twfe_did", "status": "ok", "run_dir": str(twfe_dir)},
            {"label": "drdid_2x2", "status": "ok", "run_dir": str(drdid_dir)},
        ],
        [],
        {},
    )
    assert "DRDID_PSM_DID_DISAGREE" in {item["code"] for item in warnings}
    assert (ctx.run_dir / "tables" / "drdid_main.csv").exists()
    assert (ctx.run_dir / "tables" / "adjusted_did_comparison.csv").exists()
    assert (ctx.run_dir / "raw" / "drdid.log").read_text(encoding="utf-8") == "fake drdid log\n"


def test_static_psm_did_fixtures_match_expected_risks(tmp_path: Path) -> None:
    paths = materialize_psm_did_fixtures(PSM_FIXTURE_DIR)
    assert {path.name for path in paths} == {f"{name}.csv" for name in PSM_DID_FIXTURE_NAMES}

    for name in PSM_DID_FIXTURE_NAMES:
        expected = json.loads((PSM_FIXTURE_DIR / f"{name}.expected_risks.json").read_text(encoding="utf-8"))
        expected_risks = set(expected["expected_risks"])
        if name == "drdid_psm_disagree":
            ctx = make_run_context("psm_did_policy_run", "workflow", {}, "run", str(tmp_path / "runs"))
            psm_dir = tmp_path / name / "psm"
            drdid_dir = tmp_path / name / "drdid"
            _write_model_table(psm_dir / "model_table.csv", [{"term": "ATT_nearest_neighbor", "coef": 1.0, "std_error": 0.2, "p_value": 0.01}])
            _write_model_table(drdid_dir / "model_table.csv", [{"term": "ATT", "coef": -1.0, "std_error": 0.2, "p_value": 0.01}])
            (drdid_dir / "stata.log").write_text("fake\n", encoding="utf-8")
            warnings = _psm_did_postprocess(
                ctx,
                [
                    {"label": "propensity_overlap", "status": "ok", "run_dir": str(psm_dir)},
                    {"label": "drdid_2x2", "status": "ok", "run_dir": str(drdid_dir)},
                ],
                [],
                {},
            )
            observed = {item["code"] for item in warnings}
        else:
            df = pd.read_csv(PSM_FIXTURE_DIR / f"{name}.csv")
            spec = json.loads((PSM_FIXTURE_DIR / f"{name}.spec.json").read_text(encoding="utf-8"))
            observed = _codes(run_overlap_balance_diagnostics(df, spec, tmp_path / name))
        assert expected_risks.issubset(observed), name
