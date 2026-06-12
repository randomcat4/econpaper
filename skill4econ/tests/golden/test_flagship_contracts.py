from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPATIAL_FIXTURE_DIR = ROOT / "skill4econ" / "tests" / "fixtures" / "spatial"
PSM_FIXTURE_DIR = ROOT / "skill4econ" / "tests" / "fixtures" / "psm_did"
for path in [SPATIAL_FIXTURE_DIR, PSM_FIXTURE_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from generate_psm_did_fixtures import materialize_psm_did_fixtures
from generate_spatial_fixtures import materialize_spatial_fixtures
from skill4econ.core import make_run_context, read_spec
from skill4econ.python_wrappers import psm_ipw_match, spatial_exposure_did, spatial_w_sensitivity
from skill4econ.workflows import did_paper_run
from skill4econ.validation.contract_verifier import validate_run_dir


def _resolve_spatial_case(case_dir: Path) -> dict:
    spec = json.loads((case_dir / "spec.json").read_text(encoding="utf-8"))
    spec["data"] = str(case_dir / "panel.csv")
    for key in ["weights", "w_path", "weight_matrix"]:
        if spec.get(key):
            spec[key] = str(case_dir / spec[key])
    if spec.get("weight_paths"):
        spec["weight_paths"] = [str(case_dir / item) for item in spec["weight_paths"]]
    return spec


def _run_psm_case(case_name: str, tmp_path: Path):
    materialize_psm_did_fixtures(PSM_FIXTURE_DIR)
    spec = json.loads((PSM_FIXTURE_DIR / f"{case_name}.spec.json").read_text(encoding="utf-8"))
    spec["data"] = str(PSM_FIXTURE_DIR / f"{case_name}.csv")
    ctx = make_run_context("psm_ipw_match", "python", spec, "run", str(tmp_path / "runs"))
    manifest = psm_ipw_match(ctx)
    assert manifest["status"] == "ok"
    return ctx


def test_did_golden_common_schema_has_estimand_support_and_twfe_role(tmp_path: Path) -> None:
    spec = read_spec(ROOT / "skill4econ" / "examples" / "mini_panel" / "did_paper_run_spec.yml")
    spec["output_dir"] = str(tmp_path / "runs")
    ctx = make_run_context("did_paper_run", "workflow", spec, "run", str(tmp_path / "runs"))
    manifest = did_paper_run(ctx)
    assert manifest["status"] == "success"
    claim = json.loads(ctx.artifact("did_claim_contract.json").read_text(encoding="utf-8"))
    assert claim["estimand_scope"] == "simple_ATT"
    assert claim["control_group"] in {"never_treated", "not_yet_treated"}
    assert "event_time_support" in claim
    commons = list(ctx.run_dir.rglob("did_common_output.json"))
    assert commons
    common = json.loads(commons[0].read_text(encoding="utf-8"))
    assert "cohort_support" in common
    assert "event_time_support" in common
    assert common["aggregation_method"] in {"simple", "event_time"}
    assert common["twfe_role"] in {"main", "comparison_only", "forbidden_for_main", "not_used"}
    for artifact_name in [
        "summary_stats.csv",
        "cohort_table.csv",
        "event_study.csv",
        "pretrend_test.json",
        "robustness_grid.csv",
        "figures/manifest.yaml",
    ]:
        assert ctx.artifact(artifact_name).exists(), artifact_name
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    evidence_types = {
        item.get("evidence_type")
        for item in artifact_manifest["artifacts"]
        if item.get("evidence_type")
    }
    assert {
        "model_table",
        "event_study",
        "pretrend_test",
        "cohort_table",
        "robustness_grid",
        "summary_stats",
        "figure_manifest",
    } <= evidence_types
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_did_golden_author_configured_placebo_and_heterogeneity_artifacts(tmp_path: Path) -> None:
    rows = []
    for unit in range(1, 21):
        ever = int(unit <= 10)
        region = "north" if unit % 2 == 0 else "south"
        size_group = "large" if unit in {1, 2, 3, 4, 5, 11, 12, 13, 14, 15} else "small"
        for year in range(2015, 2022):
            post = int(year >= 2019)
            placebo_post = int(year >= 2017)
            treatment_effect = ever * post * (1.0 + 0.2 * (region == "north") + 0.1 * (size_group == "large"))
            rows.append(
                {
                    "firm_id": unit,
                    "year": year,
                    "y": 5.0 + unit * 0.2 + (year - 2015) * 0.1 + treatment_effect,
                    "treat": ever,
                    "post": post,
                    "placebo_post": placebo_post,
                    "region": region,
                    "size_group": size_group,
                }
            )
    data = tmp_path / "configured_did.csv"
    pd.DataFrame(rows).to_csv(data, index=False)
    spec = {
        "data": str(data),
        "design_type": "simple_2x2_did",
        "id": "firm_id",
        "time": "year",
        "y": "y",
        "treat": "treat",
        "post": "post",
        "cluster": "firm_id",
        "engine_policy": "python",
        "event_window": [-2, 2],
        "base_period": -1,
        "placebo_tests": [{"name": "fake_2017_timing", "post": "placebo_post"}],
        "heterogeneity_dimensions": ["region", "size_group"],
        "variable_units": {"y": "index points"},
        "output_dir": str(tmp_path / "runs"),
    }
    ctx = make_run_context("did_paper_run", "workflow", spec, "run", str(tmp_path / "runs"))
    manifest = did_paper_run(ctx)
    assert manifest["status"] == "success"
    for artifact_name in ["placebo_tests.csv", "heterogeneity.csv"]:
        assert ctx.artifact(artifact_name).exists(), artifact_name

    placebo_rows = pd.read_csv(ctx.artifact("placebo_tests.csv"))
    heterogeneity_rows = pd.read_csv(ctx.artifact("heterogeneity.csv"))
    robustness_rows = pd.read_csv(ctx.artifact("robustness_grid.csv"))
    assert set(placebo_rows["status"]) == {"computed"}
    assert {"region", "size_group"} <= set(heterogeneity_rows.loc[heterogeneity_rows["status"] == "computed", "dimension"])
    assert len(set(robustness_rows["family"])) >= 4

    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    evidence_types = {
        item.get("evidence_type")
        for item in artifact_manifest["artifacts"]
        if item.get("evidence_type")
    }
    assert {"placebo_tests", "heterogeneity"} <= evidence_types
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_did_golden_rank_deficient_design_blocks_estimation(tmp_path: Path) -> None:
    rows = []
    for unit in range(1, 7):
        treated = int(unit <= 3)
        x1 = float(unit)
        for year in range(2018, 2022):
            post = int(year >= 2020)
            rows.append(
                {
                    "firm_id": unit,
                    "year": year,
                    "y": 1.0 + treated * post + 0.2 * x1 + 0.1 * (year - 2018),
                    "treat": treated,
                    "post": post,
                    "x1": x1,
                    "x2": 2.0 * x1,
                }
            )
    data = tmp_path / "rank_deficient_did.csv"
    pd.DataFrame(rows).to_csv(data, index=False)
    spec = {
        "data": str(data),
        "design_type": "simple_2x2_did",
        "id": "firm_id",
        "time": "year",
        "y": "y",
        "treat": "treat",
        "post": "post",
        "x": ["x1", "x2"],
        "cluster": "firm_id",
        "output_dir": str(tmp_path / "runs"),
    }
    ctx = make_run_context("did_paper_run", "workflow", spec, "run", str(tmp_path / "runs"))
    manifest = did_paper_run(ctx)
    assert manifest["status"] == "failed"
    status = json.loads(ctx.artifact("status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed"
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "RANK_DEFICIENT_DESIGN" in {item["code"] for item in risk["risks"]}
    report = validate_run_dir(ctx.run_dir, strict=True)
    assert report.status == "failed"
    assert any(item.code == "strict_failed_run" for item in report.errors)


def test_psm_golden_good_overlap_writes_balance_weight_contract(tmp_path: Path) -> None:
    ctx = _run_psm_case("overlap_good", tmp_path)
    diag = json.loads(ctx.artifact("psm_diagnostics.json").read_text(encoding="utf-8"))
    overlap = diag["overlap_balance"]
    assert overlap["overlap_status"] in {"pass", "weak"}
    assert overlap["balance_status"] in {"pass", "weak", "fail"}
    assert overlap["effective_sample_size_treated"] >= 0
    assert overlap["effective_sample_size_control"] >= 0
    assert overlap["max_weight"] >= overlap["p99_weight"] >= overlap["p95_weight"] >= 0
    assert ctx.artifact("tables/balance_table_before.csv").exists()
    assert ctx.artifact("tables/balance_table_after_ipw.csv").exists()
    assert ctx.artifact("tables/ipw_weight_diagnostics.csv").exists()
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_psm_golden_poor_overlap_downgrades_claim(tmp_path: Path) -> None:
    ctx = _run_psm_case("overlap_poor", tmp_path)
    status = json.loads(ctx.artifact("status.json").read_text(encoding="utf-8"))
    assert status["paper_readiness"] != "paper_ready"
    diag = json.loads(ctx.artifact("psm_diagnostics.json").read_text(encoding="utf-8"))
    overlap = diag["overlap_balance"]
    assert overlap["overlap_status"] in {"weak", "fail"}
    assert overlap["effective_sample_size_treated"] >= 0
    assert overlap["p99_weight"] >= 0
    assert ctx.artifact("tables/ipw_trimming_sensitivity.csv").exists()
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_psm_golden_extreme_weights_reports_ess_and_weight_risk(tmp_path: Path) -> None:
    ctx = _run_psm_case("extreme_weights", tmp_path)
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    codes = {item["code"] for item in risk["risks"]}
    assert {"EXTREME_IPW_WEIGHTS", "IPW_EXTREME_WEIGHTS"} & codes
    diag = json.loads(ctx.artifact("psm_diagnostics.json").read_text(encoding="utf-8"))
    overlap = diag["overlap_balance"]
    assert overlap["max_weight"] >= overlap["p99_weight"] >= 0
    assert overlap["effective_sample_size_treated"] >= 0
    assert overlap["effective_sample_size_control"] >= 0
    assert ctx.artifact("tables/ipw_trimming_sensitivity.csv").exists()
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_spatial_golden_direct_effect_writes_local_did_common_output(tmp_path: Path) -> None:
    cases = {path.name: path for path in materialize_spatial_fixtures(SPATIAL_FIXTURE_DIR)}
    spec = _resolve_spatial_case(cases["direct_only_effect"])
    ctx = make_run_context("spatial_exposure_did", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_exposure_did(ctx)
    assert manifest["status"] == "ok"
    common = json.loads(ctx.artifact("did_common_output.json").read_text(encoding="utf-8"))
    assert common["estimand_scope"] == "reduced_form_spatial_exposure"
    assert common["estimator"] == "spatial_exposure_local_twfe"
    assert ctx.artifact("tables/spatial_exposure_twfe.csv").exists()
    assert ctx.artifact("tables/spatial_exposure_summary.csv").exists()
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_spatial_golden_exposure_is_reduced_form_not_structural(tmp_path: Path) -> None:
    cases = {path.name: path for path in materialize_spatial_fixtures(SPATIAL_FIXTURE_DIR)}
    spec = _resolve_spatial_case(cases["indirect_only_effect"])
    ctx = make_run_context("spatial_exposure_did", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_exposure_did(ctx)
    assert manifest["status"] == "ok"
    status = json.loads(ctx.artifact("status.json").read_text(encoding="utf-8"))
    assert status["claim_level"] == "sensitivity_only"
    assert status["main_claim_available"] is False
    summary = json.loads(ctx.artifact("spatial_exposure_did_summary.json").read_text(encoding="utf-8"))
    assert summary["estimand_scope"] == "reduced_form_spatial_exposure"
    assert summary["is_structural_spillover_model"] is False
    assert "structural indirect effect" in summary["forbidden_claims"]
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_spatial_golden_contaminated_controls_are_not_swallowed(tmp_path: Path) -> None:
    cases = {path.name: path for path in materialize_spatial_fixtures(SPATIAL_FIXTURE_DIR)}
    spec = _resolve_spatial_case(cases["contaminated_controls"])
    ctx = make_run_context("spatial_exposure_did", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_exposure_did(ctx)
    assert manifest["status"] == "ok"
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "CONTROL_GROUP_CONTAMINATED" in {item["code"] for item in risk["risks"]}
    assert ctx.artifact("tables/contaminated_controls.csv").exists()
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"


def test_spatial_golden_w_sign_flip_downgrades_claim(tmp_path: Path) -> None:
    cases = {path.name: path for path in materialize_spatial_fixtures(SPATIAL_FIXTURE_DIR)}
    spec = _resolve_spatial_case(cases["w_sign_flip"])
    ctx = make_run_context("spatial_w_sensitivity", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_w_sensitivity(ctx)
    assert manifest["status"] == "ok"
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "W_SENSITIVITY_SIGN_FLIP" in {item["code"] for item in risk["risks"]}
    status = json.loads(ctx.artifact("status.json").read_text(encoding="utf-8"))
    assert status["paper_readiness"] != "paper_ready"
    assert validate_run_dir(ctx.run_dir, strict=True).status == "passed"
