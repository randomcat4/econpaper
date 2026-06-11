from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "fatal": 3,
}

LEGACY_SEVERITY_MAP = {
    "green": "low",
    "yellow": "medium",
    "red": "high",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "fatal": "fatal",
    "missing_dependency": "medium",
    "failed": "high",
}

STANDARD_RISK_CODES = {
    "TWFE_STAGGERED_HETEROGENEITY",
    "NO_NEVER_TREATED",
    "ONLY_NOT_YET_TREATED_CONTROLS",
    "WEAK_PRETREND_PERIODS",
    "FEW_TREATED_COHORTS",
    "ANTICIPATION_RISK",
    "POST_PERIOD_TOO_SHORT",
    "UNBALANCED_PANEL_HIGH_LOSS",
    "TWFE_MODERN_DID_DISAGREE",
    "NEGATIVE_OR_BAD_TWFE_WEIGHTS",
    "TREATMENT_REVERSAL",
    "DID_DESIGN_DECLARATION_MISMATCH",
    "CONTINUOUS_TREATMENT_NOT_SUPPORTED",
    "POOR_OVERLAP",
    "OFF_SUPPORT_HIGH_SHARE",
    "EXTREME_IPW_WEIGHTS",
    "LOW_EFFECTIVE_SAMPLE_SIZE",
    "BALANCE_STILL_POOR",
    "PSM_SAMPLE_LOSS_HIGH",
    "TRIM_SENSITIVITY_UNSTABLE",
    "DRDID_PSM_DID_DISAGREE",
    "SPATIAL_W_HAS_ISLANDS",
    "SPATIAL_W_MISSING",
    "SPATIAL_W_NOT_ROW_STANDARDIZED",
    "SPATIAL_TREATMENT_CLUSTERED",
    "CONTROL_GROUP_CONTAMINATED",
    "EXPOSURE_CONTROL_DEFINITION_WEAK",
    "W_SENSITIVITY_SIGN_FLIP",
    "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION",
    "SPATIAL_SE_NOT_USED",
    "TWFE_STAGGERED_NOT_MAIN",
    "DID_INSUFFICIENT_COHORT_SUPPORT",
    "DID_EVENT_TIME_SUPPORT_WEAK",
    "DID_IMPUTATION_FAILED",
    "PSM_OVERLAP_WEAK",
    "IPW_EXTREME_WEIGHTS",
    "IPW_LOW_EFFECTIVE_SAMPLE_SIZE",
    "BACKEND_MISSING_DEPENDENCY",
    "BACKEND_PARSE_FAILED",
    "BACKEND_RESULT_MISSING",
    "BACKEND_TIMEOUT",
    "BACKEND_INVALID_RESULT",
    "BACKEND_ERROR",
    "FALLBACK_ESTIMATOR_NOT_PAPER_READY",
    "SDM_IMPACTS_MISSING",
    "PPMLHDFE_MISSING",
    "LOCAL_MORAN_PERMUTATION_NOT_RUN",
    "SPATIAL_HAC_UNIFORM_KERNEL",
    "PSM_NAIVE_SE_NOT_ABADIE_IMBENS",
    "RANK_DEFICIENT_DESIGN",
    "MODEL_NOT_IDENTIFIED",
    "MEDIATOR_TIMING_INVALID",
    "MEDIATOR_SAME_PERIOD_AS_OUTCOME",
    "MECHANISM_CLAIM_TOO_STRONG",
    "MULTIPLE_MECHANISMS_NO_ADJUSTMENT",
    "THRESHOLD_BOOTSTRAP_NOT_SIGNIFICANT",
    "THRESHOLD_UNBALANCED_PANEL",
    "QUANTILE_TYPE_AMBIGUOUS",
    "DEA_DMU_TOO_FEW",
    "DEA_BAD_OUTPUT_NEGATIVE",
    "DEA_ZERO_OR_MISSING_BAD_OUTPUT",
    "DEA_FRONTIER_CHOICE_UNREPORTED",
    "DEA_VARIABLE_SENSITIVITY_UNCHECKED",
    "DEA_SECOND_STAGE_NAIVE_TOBIT",
    "MALMQUIST_INFEASIBLE",
    "BACKEND_UNAVAILABLE",
    "DATA_CONTRACT_FAILED",
    "DATA_CONTRACT_ID_TIME_NOT_UNIQUE",
    "ESTIMATOR_STEP_FAILED",
    "SLOW_MATRIX_EXPECTATION_MISMATCH",
}

LEGACY_CODE_MAP = {
    "twfe_staggered_heterogeneity": "TWFE_STAGGERED_HETEROGENEITY",
    "staggered_did_without_alternative_estimator": "TWFE_STAGGERED_HETEROGENEITY",
    "staggered_estimator_not_requested": "TWFE_STAGGERED_HETEROGENEITY",
    "no_never_treated": "NO_NEVER_TREATED",
    "few_pre_treatment_leads": "WEAK_PRETREND_PERIODS",
    "few_treated_cohorts": "FEW_TREATED_COHORTS",
    "no_post_period": "POST_PERIOD_TOO_SHORT",
    "unbalanced_panel": "UNBALANCED_PANEL_HIGH_LOSS",
    "large_listwise_deletion": "UNBALANCED_PANEL_HIGH_LOSS",
    "treatment_has_no_variation": "DATA_CONTRACT_FAILED",
    "post_has_no_variation": "DATA_CONTRACT_FAILED",
    "missing_design_type": "DATA_CONTRACT_FAILED",
    "invalid_design_type": "DATA_CONTRACT_FAILED",
    "missing_simple_did_fields": "DATA_CONTRACT_FAILED",
    "missing_gvar": "DATA_CONTRACT_FAILED",
    "missing_core_fields": "DATA_CONTRACT_FAILED",
    "missing_columns": "DATA_CONTRACT_FAILED",
    "missing_data": "DATA_CONTRACT_FAILED",
    "data_read_failed": "DATA_CONTRACT_FAILED",
    "data_contract_failed": "DATA_CONTRACT_FAILED",
    "data_contract_warning": "DATA_CONTRACT_FAILED",
    "did_imputation_failed": "DID_IMPUTATION_FAILED",
    "did_design_declaration_mismatch": "DID_DESIGN_DECLARATION_MISMATCH",
    "continuous_treatment_not_supported": "CONTINUOUS_TREATMENT_NOT_SUPPORTED",
    "treatment_reversal": "TREATMENT_REVERSAL",
    "no_did_estimator_selected": "ESTIMATOR_STEP_FAILED",
    "id_time_not_unique": "DATA_CONTRACT_ID_TIME_NOT_UNIQUE",
    "missing_mediator": "MECHANISM_CLAIM_TOO_STRONG",
    "missing_threshold": "THRESHOLD_UNBALANCED_PANEL",
    "missing_dea_params": "DEA_FRONTIER_CHOICE_UNREPORTED",
    "missing_weights": "SPATIAL_W_MISSING",
    "weights_not_found": "SPATIAL_W_MISSING",
    "spatial_reduced_form_did_failed": "ESTIMATOR_STEP_FAILED",
    "twfe_did_failed": "ESTIMATOR_STEP_FAILED",
    "drdid_2x2_failed": "ESTIMATOR_STEP_FAILED",
    "threshold_model_failed": "ESTIMATOR_STEP_FAILED",
    "mechanism_failed": "ESTIMATOR_STEP_FAILED",
    "dea_adapter_failed": "ESTIMATOR_STEP_FAILED",
    "few_clusters": "LOW_EFFECTIVE_SAMPLE_SIZE",
    "backend_unavailable": "BACKEND_UNAVAILABLE",
    "r_backend_unavailable": "BACKEND_UNAVAILABLE",
    "backend_missing_dependency": "BACKEND_MISSING_DEPENDENCY",
    "backend_parse_failed": "BACKEND_PARSE_FAILED",
    "backend_result_missing": "BACKEND_RESULT_MISSING",
    "backend_timeout": "BACKEND_TIMEOUT",
    "backend_invalid_result": "BACKEND_INVALID_RESULT",
    "backend_error": "BACKEND_ERROR",
    "sdm_impacts_missing": "SDM_IMPACTS_MISSING",
    "ppmlhdfe_missing": "PPMLHDFE_MISSING",
    "missing_dependency": "BACKEND_UNAVAILABLE",
    "staggered_did_without_modern_estimator": "TWFE_STAGGERED_NOT_MAIN",
    "twfe_staggered_not_main": "TWFE_STAGGERED_NOT_MAIN",
    "psm_overlap_weak": "PSM_OVERLAP_WEAK",
    "ipw_extreme_weights": "IPW_EXTREME_WEIGHTS",
    "ipw_low_effective_sample_size": "IPW_LOW_EFFECTIVE_SAMPLE_SIZE",
    "fallback_estimator_not_paper_ready": "FALLBACK_ESTIMATOR_NOT_PAPER_READY",
    "local_moran_permutation_not_run": "LOCAL_MORAN_PERMUTATION_NOT_RUN",
    "spatial_hac_uniform_kernel": "SPATIAL_HAC_UNIFORM_KERNEL",
    "psm_naive_se_not_abadie_imbens": "PSM_NAIVE_SE_NOT_ABADIE_IMBENS",
    "rank_deficient_design": "RANK_DEFICIENT_DESIGN",
    "model_not_identified": "MODEL_NOT_IDENTIFIED",
}


def _risk_scope(code: str) -> str:
    if code.startswith("DID_") or code.startswith("TWFE_") or code in {"NO_NEVER_TREATED", "FEW_TREATED_COHORTS"}:
        return "did"
    if code.startswith("PSM_") or code.startswith("IPW_") or code in {"POOR_OVERLAP", "BALANCE_STILL_POOR"}:
        return "psm"
    if code.startswith("SPATIAL_") or code.startswith("W_SENSITIVITY") or code in {
        "CONTROL_GROUP_CONTAMINATED",
        "EXPOSURE_CONTROL_DEFINITION_WEAK",
        "INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION",
        "LOCAL_MORAN_PERMUTATION_NOT_RUN",
    }:
        return "spatial"
    if code.startswith("BACKEND_") or code in {"SDM_IMPACTS_MISSING", "PPMLHDFE_MISSING"}:
        return "adapter"
    if code.startswith("DEA_"):
        return "dea"
    if code in {"RANK_DEFICIENT_DESIGN", "MODEL_NOT_IDENTIFIED", "ESTIMATOR_STEP_FAILED"}:
        return "workflow"
    return "workflow"


def _claim_degradation(code: str, severity: str) -> str:
    if severity == "fatal":
        return "failed"
    if code in {
        "TWFE_STAGGERED_NOT_MAIN",
        "TWFE_STAGGERED_HETEROGENEITY",
        "DID_INSUFFICIENT_COHORT_SUPPORT",
        "DID_EVENT_TIME_SUPPORT_WEAK",
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
        "DEA_SECOND_STAGE_NAIVE_TOBIT",
        "W_SENSITIVITY_SIGN_FLIP",
        "BACKEND_PARSE_FAILED",
        "BACKEND_RESULT_MISSING",
        "BACKEND_TIMEOUT",
        "BACKEND_INVALID_RESULT",
        "BACKEND_ERROR",
        "FALLBACK_ESTIMATOR_NOT_PAPER_READY",
        "SDM_IMPACTS_MISSING",
        "PPMLHDFE_MISSING",
        "RANK_DEFICIENT_DESIGN",
        "MODEL_NOT_IDENTIFIED",
        "SLOW_MATRIX_EXPECTATION_MISMATCH",
    }:
        return "not_for_claim"
    if severity in {"high", "medium"}:
        return "supplementary_only"
    return "none"


def normalize_severity(value: Any) -> str:
    severity = str(value or "medium").strip().lower()
    return LEGACY_SEVERITY_MAP.get(severity, "medium")


def normalize_code(value: Any) -> str:
    code = str(value or "UNSPECIFIED_REVIEWER_RISK").strip()
    mapped = LEGACY_CODE_MAP.get(code.lower())
    if mapped:
        return mapped
    normalized = code.upper().replace("-", "_").replace(" ", "_")
    return normalized or "UNSPECIFIED_REVIEWER_RISK"


@dataclass
class ReviewerRiskCollector:
    workflow: str
    safe_claims: list[str] = field(default_factory=list)
    unsafe_claims: list[str] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)

    def add_warning(
        self,
        code: str,
        severity: str,
        message: str,
        required_fix: str,
        affected_artifacts: list[str] | None = None,
    ) -> None:
        normalized = normalize_code(code)
        sev = normalize_severity(severity)
        self.risks.append(
            {
                "code": normalized,
                "severity": sev,
                "scope": _risk_scope(normalized),
                "message": str(message),
                "required_fix": str(required_fix or ""),
                "claim_degradation": _claim_degradation(normalized, sev),
                "affected_artifacts": list(affected_artifacts or []),
                "known_code": normalized in STANDARD_RISK_CODES,
            }
        )

    def merge(self, other: "ReviewerRiskCollector") -> None:
        self.safe_claims.extend(item for item in other.safe_claims if item not in self.safe_claims)
        self.unsafe_claims.extend(item for item in other.unsafe_claims if item not in self.unsafe_claims)
        self.risks.extend(other.risks)

    @property
    def risk_level(self) -> str:
        if not self.risks:
            return "low"
        return max(
            (str(item.get("severity", "medium")) for item in self.risks),
            key=lambda item: SEVERITY_ORDER.get(item, 1),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "risk_level": self.risk_level,
            "risks": self.risks,
            "safe_claims": self.safe_claims,
            "unsafe_claims": self.unsafe_claims,
        }

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def to_markdown(self, path: Path) -> None:
        lines = [
            f"# Reviewer Risk: {self.workflow}",
            "",
            f"Overall risk level: `{self.risk_level}`",
            "",
            "## Risks",
            "",
        ]
        if not self.risks:
            lines.append("- No reviewer risks were recorded.")
        for risk in self.risks:
            fix = f" Required fix: {risk.get('required_fix')}" if risk.get("required_fix") else ""
            lines.append(
                f"- `{risk.get('severity')}` `{risk.get('code')}`: {risk.get('message')}{fix}"
            )
        lines.extend(["", "## Safe Claims", ""])
        lines.extend(f"- {item}" for item in self.safe_claims) if self.safe_claims else lines.append("- None recorded.")
        lines.extend(["", "## Unsafe Claims", ""])
        lines.extend(f"- {item}" for item in self.unsafe_claims) if self.unsafe_claims else lines.append("- None recorded.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def from_warnings(
        cls,
        workflow: str,
        warnings: list[dict[str, Any]] | None,
        *,
        safe_claims: list[str] | None = None,
        unsafe_claims: list[str] | None = None,
    ) -> "ReviewerRiskCollector":
        collector = cls(
            workflow=workflow,
            safe_claims=list(safe_claims or []),
            unsafe_claims=list(unsafe_claims or []),
        )
        for warning in warnings or []:
            severity = normalize_severity(warning.get("severity"))
            code = str(warning.get("code") or "")
            if severity == "low" and code.lower() in {"workflow_completed"}:
                continue
            if severity == "low":
                continue
            collector.add_warning(
                code=code,
                severity=severity,
                message=str(warning.get("message") or ""),
                required_fix=str(warning.get("action") or warning.get("required_fix") or "Report this limitation."),
                affected_artifacts=warning.get("affected_artifacts") or None,
            )
        return collector
