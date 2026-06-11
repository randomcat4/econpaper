from __future__ import annotations

from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    SUCCESS = "success"
    SUCCESS_WITH_WARNINGS = "success_with_warnings"
    PARTIAL_SUCCESS = "partial_success"
    SKIPPED = "skipped"
    FAILED = "failed"


RUN_STATUS_VALUES = {item.value for item in RunStatus}


def normalize_run_status(status: Any, *, risk_level: str | None = None) -> str:
    text = str(status or "").strip().lower()
    if text in {"ok", "success"}:
        return RunStatus.SUCCESS_WITH_WARNINGS.value if risk_level in {"medium", "high", "fatal"} else RunStatus.SUCCESS.value
    if text in {"degraded", "not_paper_ready", "partial_success"}:
        return RunStatus.PARTIAL_SUCCESS.value
    if text in {"validated", "success_with_warnings"}:
        return RunStatus.SUCCESS_WITH_WARNINGS.value
    if text in {"missing_dependency", "interface_only", "adapter_only", "planned", "skipped"}:
        return RunStatus.SKIPPED.value
    if text in {"failed", "fatal", "error"}:
        return RunStatus.FAILED.value
    return RunStatus.SUCCESS_WITH_WARNINGS.value
