from __future__ import annotations

from enum import Enum
from typing import Any


class ClaimLevel(str, Enum):
    MAIN_ESTIMATE = "main_estimate"
    DIAGNOSTIC = "diagnostic"
    SENSITIVITY_ONLY = "sensitivity_only"
    ADAPTER_ONLY = "adapter_only"
    EXPLORATORY_ONLY = "exploratory_only"
    FAILED = "failed"
    SKIPPED = "skipped"


class PaperReadiness(str, Enum):
    PAPER_READY = "paper_ready"
    SUPPLEMENTARY_ONLY = "supplementary_only"
    EXPLORATORY_ONLY = "exploratory_only"
    NOT_FOR_CLAIM = "not_for_claim"
    NOT_AVAILABLE = "not_available"


CLAIM_LEVEL_VALUES = {item.value for item in ClaimLevel}
PAPER_READINESS_VALUES = {item.value for item in PaperReadiness}

DIAGNOSTIC_METHOD_HINTS = {
    "data_audit",
    "py_preflight",
    "psm_overlap_balance",
    "psm_ipw_match",
    "stata_preflight",
    "spatial_panel_preflight",
    "export_log_manifest",
    "live_backend_certification",
    "flagship_slow_matrix",
    "spatial_weights_factory",
    "spatial_w_audit",
    "spatial_moran_preflight",
    "spatial_spdep_lisa",
    "ml_prediction_audit",
}

SENSITIVITY_METHOD_HINTS = {
    "spatial_exposure_did",
    "spatial_did",
    "spatial_did_reduced_form",
    "spatial_se_comparison",
    "spatial_w_sensitivity",
    "spatial_spillover_run",
    "psm_did_policy_run",
}

EXPLORATORY_METHOD_HINTS = {
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
}

ADAPTER_METHOD_HINTS = {
    "spatial_panel_model_adapter",
    "doubleml_adapter",
    "econml_adapter",
    "dea_sbm_malmquist_adapter",
}


def normalize_claim_level(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in CLAIM_LEVEL_VALUES else ClaimLevel.EXPLORATORY_ONLY.value


def normalize_paper_readiness(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in PAPER_READINESS_VALUES else PaperReadiness.EXPLORATORY_ONLY.value


def _risk_codes(reviewer_risk: dict[str, Any] | None) -> set[str]:
    return {
        str(item.get("code"))
        for item in (reviewer_risk or {}).get("risks", [])
        if isinstance(item, dict) and item.get("code")
    }


def _risk_degradations(reviewer_risk: dict[str, Any] | None) -> set[str]:
    return {
        str(item.get("claim_degradation"))
        for item in (reviewer_risk or {}).get("risks", [])
        if isinstance(item, dict) and item.get("claim_degradation")
    }


def infer_claim_contract(
    *,
    method_or_workflow: str,
    status: str,
    extra: dict[str, Any],
    reviewer_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Infer conservative claim metadata for a run.

    Callers may override any field through write_manifest(..., claim_level=...).
    The defaults intentionally downgrade dependency-gated, diagnostic, and
    reduced-form spatial outputs so downstream agents cannot overclaim.
    """

    if extra.get("claim_level") or extra.get("paper_readiness"):
        claim_level = normalize_claim_level(extra.get("claim_level"))
        paper_readiness = normalize_paper_readiness(extra.get("paper_readiness"))
        main_claim_available = bool(extra.get("main_claim_available", claim_level == ClaimLevel.MAIN_ESTIMATE.value))
    else:
        text_status = str(status or "").strip().lower()
        name = str(method_or_workflow or "").strip()
        codes = _risk_codes(reviewer_risk)
        degradations = _risk_degradations(reviewer_risk)

        if text_status in {"failed", "fatal", "error"}:
            claim_level = ClaimLevel.FAILED.value
            paper_readiness = PaperReadiness.NOT_AVAILABLE.value
            main_claim_available = False
        elif text_status in {"missing_dependency", "skipped", "planned"}:
            claim_level = ClaimLevel.SKIPPED.value
            paper_readiness = PaperReadiness.NOT_AVAILABLE.value
            main_claim_available = False
        elif text_status in {"interface_only", "adapter_only"} or name in ADAPTER_METHOD_HINTS:
            claim_level = ClaimLevel.ADAPTER_ONLY.value
            paper_readiness = PaperReadiness.NOT_AVAILABLE.value
            main_claim_available = False
        elif name in DIAGNOSTIC_METHOD_HINTS:
            claim_level = ClaimLevel.DIAGNOSTIC.value
            paper_readiness = PaperReadiness.SUPPLEMENTARY_ONLY.value
            main_claim_available = False
        elif name in SENSITIVITY_METHOD_HINTS:
            claim_level = ClaimLevel.SENSITIVITY_ONLY.value
            paper_readiness = PaperReadiness.SUPPLEMENTARY_ONLY.value
            main_claim_available = False
        elif name in EXPLORATORY_METHOD_HINTS:
            claim_level = ClaimLevel.EXPLORATORY_ONLY.value
            paper_readiness = PaperReadiness.NOT_FOR_CLAIM.value
            main_claim_available = False
        elif text_status in {"not_paper_ready", "partial_success"}:
            claim_level = ClaimLevel.EXPLORATORY_ONLY.value
            paper_readiness = PaperReadiness.NOT_FOR_CLAIM.value
            main_claim_available = False
        elif text_status in {"degraded", "success_with_warnings", "validated"}:
            claim_level = ClaimLevel.EXPLORATORY_ONLY.value
            paper_readiness = PaperReadiness.SUPPLEMENTARY_ONLY.value
            main_claim_available = False
        else:
            claim_level = ClaimLevel.MAIN_ESTIMATE.value
            paper_readiness = PaperReadiness.PAPER_READY.value
            main_claim_available = True

        if paper_readiness != PaperReadiness.NOT_AVAILABLE.value and ("not_for_claim" in degradations or {
            "TWFE_STAGGERED_NOT_MAIN",
            "TWFE_STAGGERED_HETEROGENEITY",
            "PSM_OVERLAP_WEAK",
            "POOR_OVERLAP",
            "BALANCE_STILL_POOR",
            "IPW_EXTREME_WEIGHTS",
            "EXTREME_IPW_WEIGHTS",
            "IPW_LOW_EFFECTIVE_SAMPLE_SIZE",
            "LOW_EFFECTIVE_SAMPLE_SIZE",
            "CONTROL_GROUP_CONTAMINATED",
            "EXPOSURE_CONTROL_DEFINITION_WEAK",
            "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION",
            "W_SENSITIVITY_SIGN_FLIP",
            "BACKEND_PARSE_FAILED",
            "BACKEND_RESULT_MISSING",
            "BACKEND_TIMEOUT",
            "BACKEND_INVALID_RESULT",
            "BACKEND_ERROR",
            "FALLBACK_ESTIMATOR_NOT_PAPER_READY",
            "SDM_IMPACTS_MISSING",
            "RANK_DEFICIENT_DESIGN",
            "MODEL_NOT_IDENTIFIED",
            "DEA_SECOND_STAGE_NAIVE_TOBIT",
        }.intersection(codes)):
            paper_readiness = PaperReadiness.NOT_FOR_CLAIM.value
            main_claim_available = False
        elif paper_readiness == PaperReadiness.PAPER_READY.value and "supplementary_only" in degradations:
            paper_readiness = PaperReadiness.SUPPLEMENTARY_ONLY.value
            main_claim_available = False

    return {
        "claim_level": claim_level,
        "paper_readiness": paper_readiness,
        "main_claim_available": main_claim_available,
        "estimand_scope": str(extra.get("estimand_scope") or extra.get("estimator") or method_or_workflow),
        "not_valid_for": list(extra.get("not_valid_for") or []),
        "why_not_main_claim": list(extra.get("why_not_main_claim") or ([] if main_claim_available else [paper_readiness])),
    }
