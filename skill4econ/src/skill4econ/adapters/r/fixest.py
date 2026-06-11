from __future__ import annotations

from typing import Any

from .base import render_r_plan, skipped


ADAPTER = {
    "name": "fixest_twfe",
    "backend": "r_fixest",
    "r_package": "fixest",
    "role": "twfe_fallback",
    "supports": ["feols_twfe", "fepois_later", "conley_vcov_later"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_r_plan(adapter=ADAPTER, spec=spec)
    plan["r_calls"] = ["fixest::feols()", "fixest::fepois()"]
    return plan


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
