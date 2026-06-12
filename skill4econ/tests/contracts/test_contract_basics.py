from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill4econ.contracts.artifact_manifest import build_artifact_manifest, infer_econpaper_evidence_type
from skill4econ.core import make_run_context, write_manifest
from skill4econ.contracts.claim_levels import ClaimLevel, PaperReadiness
from skill4econ.contracts.claim_levels import infer_claim_contract
from skill4econ.contracts.risk_registry import validate_risk_codes
from skill4econ.contracts.run_status import RunStatus
from skill4econ.validation.schema_loader import list_schemas, load_schema


def test_claim_and_status_enums_are_stable() -> None:
    assert ClaimLevel.MAIN_ESTIMATE.value == "main_estimate"
    assert ClaimLevel.SENSITIVITY_ONLY.value == "sensitivity_only"
    assert ClaimLevel.ADAPTER_ONLY.value == "adapter_only"
    assert PaperReadiness.PAPER_READY.value == "paper_ready"
    assert PaperReadiness.NOT_FOR_CLAIM.value == "not_for_claim"
    assert RunStatus.PARTIAL_SUCCESS.value == "partial_success"


def test_stata_preflight_is_diagnostic_not_main_estimate() -> None:
    claim = infer_claim_contract(
        method_or_workflow="stata_preflight",
        status="ok",
        extra={},
        reviewer_risk={"risks": []},
    )
    assert claim["claim_level"] == "diagnostic"
    assert claim["paper_readiness"] == "supplementary_only"
    assert claim["main_claim_available"] is False


def test_python_fallback_estimators_are_not_paper_ready_by_default() -> None:
    for method in [
        "ols_cluster",
        "did_twfe_event",
        "did_event_study",
        "rdd_local_linear",
        "quantile_regression",
        "threshold_panel",
        "threshold_panel_search",
        "mediation_moderation",
        "mediation_baron_kenny",
        "synthetic_control",
        "synthetic_control_basic",
        "dml_plr_crossfit",
        "dml_irm_crossfit",
    ]:
        claim = infer_claim_contract(
            method_or_workflow=method,
            status="ok",
            extra={},
            reviewer_risk={"risks": []},
        )
        assert claim["claim_level"] == "exploratory_only", method
        assert claim["paper_readiness"] == "not_for_claim", method
        assert claim["main_claim_available"] is False, method


def test_no_registered_python_method_escapes_claim_gate_by_name() -> None:
    from skill4econ.python_wrappers import PYTHON_METHODS

    # Only real-package estimators may default to a main estimate. Every other
    # registered name, including invocation aliases, must be downgraded by
    # infer_claim_contract even when the wrapper passes no explicit claim_level.
    main_estimate_allowlist = {"panel_fe_re", "iv_2sls", "cs_did_attgt_py", "rdrobust_rdd"}
    for method in PYTHON_METHODS:
        if method in main_estimate_allowlist:
            continue
        claim = infer_claim_contract(
            method_or_workflow=method,
            status="ok",
            extra={},
            reviewer_risk={"risks": []},
        )
        assert claim["claim_level"] != "main_estimate", method
        assert claim["paper_readiness"] != "paper_ready", method
        assert claim["main_claim_available"] is False, method


def test_written_fallback_manifest_carries_reviewer_risk(tmp_path) -> None:
    ctx = make_run_context("rdd_local_linear", "python", {}, "run", str(tmp_path / "runs"))
    manifest = write_manifest(ctx, "ok", estimator="numpy local-linear RDD")
    assert manifest["claim_level"] == "exploratory_only"
    assert manifest["paper_readiness"] == "not_for_claim"
    assert manifest["main_claim_available"] is False
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "FALLBACK_ESTIMATOR_NOT_PAPER_READY" in {item["code"] for item in risk["risks"]}
    status = json.loads(ctx.artifact("status.json").read_text(encoding="utf-8"))
    assert status["claim_level"] == "exploratory_only"
    assert status["main_claim_available"] is False


def test_required_risk_codes_are_registered() -> None:
    validate_risk_codes(
        [
            "CONTROL_GROUP_CONTAMINATED",
            "EXPOSURE_CONTROL_DEFINITION_WEAK",
            "SPATIAL_W_MISSING",
            "SPATIAL_W_HAS_ISLANDS",
            "SPATIAL_SE_NOT_USED",
            "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION",
            "W_SENSITIVITY_SIGN_FLIP",
            "TWFE_STAGGERED_NOT_MAIN",
            "DID_INSUFFICIENT_COHORT_SUPPORT",
            "DID_EVENT_TIME_SUPPORT_WEAK",
            "DID_IMPUTATION_FAILED",
            "PSM_OVERLAP_WEAK",
            "IPW_EXTREME_WEIGHTS",
            "IPW_LOW_EFFECTIVE_SAMPLE_SIZE",
            "IV_FIRST_STAGE_MISSING",
            "IV_WEAK_INSTRUMENT",
            "PSM_NAIVE_SE_NOT_ABADIE_IMBENS",
            "SC_PLACEBO_TOO_FEW_DONORS",
            "FALLBACK_ESTIMATOR_NOT_PAPER_READY",
            "FEW_CLUSTERS_INFERENCE_FRAGILE",
            "LOCAL_MORAN_PERMUTATION_NOT_RUN",
            "BACKEND_MISSING_DEPENDENCY",
            "BACKEND_PARSE_FAILED",
            "BACKEND_RESULT_MISSING",
            "BACKEND_TIMEOUT",
            "BACKEND_INVALID_RESULT",
            "SDM_IMPACTS_MISSING",
            "PPMLHDFE_MISSING",
            "RANK_DEFICIENT_DESIGN",
            "MODEL_NOT_IDENTIFIED",
            "DEA_SECOND_STAGE_NAIVE_TOBIT",
        ]
    )


def test_unregistered_risk_code_fails() -> None:
    with pytest.raises(ValueError):
        validate_risk_codes(["FAKE_NEW_CODE"])


def test_schema_files_load() -> None:
    schemas = list_schemas()
    assert {path.name for path in schemas} >= {
        "status.schema.json",
        "manifest.schema.json",
        "audit.schema.json",
        "reviewer_risk.schema.json",
        "artifact_manifest.schema.json",
        "model_table.schema.json",
        "run_contract.schema.json",
    }
    for path in schemas:
        assert load_schema(path.name).get("$schema")


def test_artifact_manifest_marks_econpaper_evidence_types(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "figures").mkdir(parents=True)
    for rel_path in [
        "model_table.csv",
        "event_study.csv",
        "pretrend_test.json",
        "cohort_table.csv",
        "robustness_grid.csv",
        "placebo_tests.csv",
        "heterogeneity.csv",
        "summary_stats.csv",
        "figures/manifest.yaml",
    ]:
        path = run_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")

    manifest = build_artifact_manifest(
        workflow="did_paper_run",
        run_id="fixture",
        run_dir=run_dir,
        status="success",
        required_artifacts=[
            "model_table.csv",
            "event_study.csv",
            "pretrend_test.json",
            "cohort_table.csv",
            "robustness_grid.csv",
            "placebo_tests.csv",
            "heterogeneity.csv",
            "summary_stats.csv",
            "figures/manifest.yaml",
        ],
    )

    by_path = {item["path"]: item for item in manifest["artifacts"]}
    assert manifest["evidence_contract"]["schema_version"] == "evidence_pack.v2"
    assert by_path["model_table.csv"]["evidence_type"] == "model_table"
    assert by_path["event_study.csv"]["evidence_type"] == "event_study"
    assert by_path["pretrend_test.json"]["evidence_type"] == "pretrend_test"
    assert by_path["cohort_table.csv"]["evidence_type"] == "cohort_table"
    assert by_path["robustness_grid.csv"]["evidence_type"] == "robustness_grid"
    assert by_path["placebo_tests.csv"]["evidence_type"] == "placebo_tests"
    assert by_path["heterogeneity.csv"]["evidence_type"] == "heterogeneity"
    assert by_path["summary_stats.csv"]["evidence_type"] == "summary_stats"
    assert by_path["figures/manifest.yaml"]["evidence_type"] == "figure_manifest"
    assert manifest["missing_required_artifacts"] == []


def test_econpaper_evidence_type_inference_is_conservative() -> None:
    assert infer_econpaper_evidence_type(Path("event_study_support.csv")) is None
    assert infer_econpaper_evidence_type(Path("event_study_plot.png")) is None
    assert infer_econpaper_evidence_type(Path("event_study.csv")) == "event_study"
    assert infer_econpaper_evidence_type(Path("figures/manifest.yaml")) == "figure_manifest"
