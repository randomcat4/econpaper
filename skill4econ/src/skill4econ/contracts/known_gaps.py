from __future__ import annotations

from typing import Any


KNOWN_GAPS: list[dict[str, Any]] = [
    {
        "id": "spatial_exposure_reduced_form",
        "methods": ["spatial_exposure_did", "spatial_spillover_run"],
        "required_claim_level": "sensitivity_only",
        "required_fields": {
            "is_structural_spillover_model": False,
            "has_impact_decomposition": False,
        },
        "risk_codes": ["INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION", "SPATIAL_SE_NOT_USED"],
    },
    {
        "id": "spdep_lisa_dependency_gated",
        "methods": ["spatial_spdep_lisa"],
        "allowed_statuses": ["missing_dependency", "ok"],
        "risk_codes": ["BACKEND_UNAVAILABLE", "BACKEND_MISSING_DEPENDENCY"],
    },
    {
        "id": "spatial_structural_adapter_only",
        "methods": ["spatial_panel_model_adapter"],
        "required_claim_level": "adapter_only",
        "risk_codes": ["BACKEND_UNAVAILABLE", "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION", "BACKEND_PARSE_FAILED"],
    },
    {
        "id": "spatial_se_sensitivity_only",
        "methods": ["spatial_se_comparison"],
        "required_claim_level": "sensitivity_only",
        "required_fields": {
            "is_full_conley": False,
            "is_full_spatial_panel_inference": False,
        },
        "risk_codes": ["SPATIAL_SE_NOT_USED"],
    },
    {
        "id": "w_sensitivity_user_supplied_grid",
        "methods": ["spatial_w_sensitivity"],
        "required_claim_level": "sensitivity_only",
        "risk_codes": ["W_SENSITIVITY_SIGN_FLIP"],
    },
    {
        "id": "psm_did_support_not_main_modern_did",
        "methods": ["psm_ipw_match", "psm_did_policy_run"],
        "required_claim_level": "diagnostic",
        "risk_codes": ["PSM_OVERLAP_WEAK", "POOR_OVERLAP", "IPW_EXTREME_WEIGHTS", "LOW_EFFECTIVE_SAMPLE_SIZE"],
    },
    {
        "id": "dea_second_stage_not_certified",
        "methods": ["dea_sbm_malmquist_adapter"],
        "required_claim_level": "failed",
        "risk_codes": ["DEA_SECOND_STAGE_NAIVE_TOBIT"],
    },
    {
        "id": "vendor_sources_not_commit_pinned",
        "methods": ["py_preflight", "live_backend_certification", "flagship_slow_matrix"],
        "allowed_statuses": ["ok", "missing_dependency", "partial_success"],
        "risk_codes": ["BACKEND_UNAVAILABLE"],
    },
]


def known_gap_ids() -> set[str]:
    return {item["id"] for item in KNOWN_GAPS}
