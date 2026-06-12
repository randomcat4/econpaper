from __future__ import annotations

from typing import Iterable

from .reviewer_risk import LEGACY_CODE_MAP, STANDARD_RISK_CODES, normalize_code


REGISTERED_RISK_CODES = set(STANDARD_RISK_CODES)


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
