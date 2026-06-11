from __future__ import annotations

from typing import Any

from .base import render_r_plan, skipped


ADAPTER = {
    "name": "drdid_r",
    "backend": "r_drdid",
    "r_package": "DRDID",
    "role": "covariate_adjusted_main",
    "supports": ["ATT", "standard_error", "confidence_interval"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_r_plan(adapter=ADAPTER, spec=spec)
    plan["r_calls"] = ["DRDID::drdid_panel()", "DRDID::drdid_rc()"]
    return plan


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
