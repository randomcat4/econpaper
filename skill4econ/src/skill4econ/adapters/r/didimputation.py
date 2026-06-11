from __future__ import annotations

from typing import Any

from .base import render_r_plan, skipped


ADAPTER = {
    "name": "didimputation_r",
    "backend": "r_didimputation",
    "r_package": "didimputation",
    "role": "robustness",
    "supports": ["imputation_estimator", "dynamic_effects"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_r_plan(adapter=ADAPTER, spec=spec)
    plan["r_calls"] = ["didimputation::did_imputation()"]
    return plan


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
