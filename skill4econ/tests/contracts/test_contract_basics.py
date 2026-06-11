from __future__ import annotations

import json

import pytest

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
        "mediation_moderation",
        "synthetic_control",
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
            "PSM_NAIVE_SE_NOT_ABADIE_IMBENS",
            "FALLBACK_ESTIMATOR_NOT_PAPER_READY",
            "LOCAL_MORAN_PERMUTATION_NOT_RUN",
            "SPATIAL_HAC_UNIFORM_KERNEL",
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
