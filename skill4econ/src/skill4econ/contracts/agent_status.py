from __future__ import annotations

from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    CLAIMABLE_SUCCESS = "claimable_success"
    SUCCESS_DIAGNOSTIC_ONLY = "success_diagnostic_only"
    SUCCESS_SENSITIVITY_ONLY = "success_sensitivity_only"
    SUCCESS_ADAPTER_ONLY = "success_adapter_only"
    SUCCESS_NOT_FOR_CLAIM = "success_not_for_claim"
    PARTIAL_BACKEND_UNAVAILABLE = "partial_backend_unavailable"
    BLOCKED_MISSING_DEPENDENCY = "blocked_missing_dependency"
    BLOCKED_INTERFACE_ONLY = "blocked_interface_only"
    BLOCKED_PARSER_ONLY = "blocked_parser_only"
    SKIPPED = "skipped"
    FAILED = "failed"


CLAIMABLE_AGENT_STATUSES = {AgentStatus.CLAIMABLE_SUCCESS.value}

BACKEND_BLOCKING_CODES = {
    "BACKEND_UNAVAILABLE",
    "BACKEND_PARSE_FAILED",
    "BACKEND_RESULT_MISSING",
    "BACKEND_TIMEOUT",
    "BACKEND_INVALID_RESULT",
    "BACKEND_ERROR",
    "PPMLHDFE_MISSING",
    "SDM_IMPACTS_MISSING",
}


def is_claimable_agent_status(value: Any) -> bool:
    return str(value or "") in CLAIMABLE_AGENT_STATUSES


def infer_agent_status(
    *,
    legacy_status: str,
    normalized_status: str,
    claim_level: str,
    paper_readiness: str,
    main_claim_available: bool,
    risk_level: str,
    risk_codes: list[str],
    missing_dependencies: list[str],
    extra: dict[str, Any],
) -> str:
    """Return a strict machine-facing status for downstream agents."""

    legacy = str(legacy_status or "").strip().lower()
    normalized = str(normalized_status or "").strip().lower()
    risk = str(risk_level or "").strip().lower()
    codes = {str(code) for code in risk_codes if code}
    parser_status = str(
        extra.get("parser_status")
        or extra.get("backend_run_status")
        or extra.get("certification_status")
        or ""
    ).strip().lower()

    if legacy in {"failed", "fatal", "error"} or normalized == "failed":
        return AgentStatus.FAILED.value
    if legacy == "missing_dependency" or missing_dependencies:
        return AgentStatus.BLOCKED_MISSING_DEPENDENCY.value
    if legacy in {"interface_only", "adapter_only"}:
        return AgentStatus.BLOCKED_INTERFACE_ONLY.value
    if "parser_only" in parser_status:
        return AgentStatus.BLOCKED_PARSER_ONLY.value
    if legacy in {"planned", "skipped"}:
        return AgentStatus.SKIPPED.value
    if legacy in {"partial_success", "degraded"} or codes.intersection(BACKEND_BLOCKING_CODES):
        return AgentStatus.PARTIAL_BACKEND_UNAVAILABLE.value

    if main_claim_available and paper_readiness == "paper_ready" and risk not in {"high", "fatal"}:
        return AgentStatus.CLAIMABLE_SUCCESS.value

    if claim_level == "diagnostic":
        return AgentStatus.SUCCESS_DIAGNOSTIC_ONLY.value
    if claim_level == "sensitivity_only":
        return AgentStatus.SUCCESS_SENSITIVITY_ONLY.value
    if claim_level == "adapter_only":
        return AgentStatus.SUCCESS_ADAPTER_ONLY.value
    return AgentStatus.SUCCESS_NOT_FOR_CLAIM.value
