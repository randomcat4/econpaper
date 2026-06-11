from __future__ import annotations

from typing import Iterable

from .reviewer_risk import LEGACY_CODE_MAP, STANDARD_RISK_CODES, normalize_code


TODO_REQUIRED_RISK_CODES = {
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
    "PSM_OVERLAP_WEAK",
    "IPW_EXTREME_WEIGHTS",
    "IPW_LOW_EFFECTIVE_SAMPLE_SIZE",
    "BACKEND_MISSING_DEPENDENCY",
    "BACKEND_PARSE_FAILED",
    "RANK_DEFICIENT_DESIGN",
    "MODEL_NOT_IDENTIFIED",
}

REGISTERED_RISK_CODES = set(STANDARD_RISK_CODES) | TODO_REQUIRED_RISK_CODES


def canonical_risk_code(code: str) -> str:
    normalized = normalize_code(code)
    return LEGACY_CODE_MAP.get(str(code).lower(), normalized)


def invalid_risk_codes(codes: Iterable[str]) -> list[str]:
    invalid: list[str] = []
    for code in codes:
        canonical = canonical_risk_code(str(code))
        if canonical not in REGISTERED_RISK_CODES:
            invalid.append(str(code))
    return invalid


def validate_risk_codes(codes: Iterable[str]) -> None:
    invalid = invalid_risk_codes(codes)
    if invalid:
        raise ValueError(f"Unregistered reviewer risk code(s): {invalid}")
