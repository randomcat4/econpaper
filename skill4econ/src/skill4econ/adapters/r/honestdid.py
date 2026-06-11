from __future__ import annotations

from typing import Any

from .base import render_r_plan, skipped


ADAPTER = {
    "name": "honestdid_r",
    "backend": "r_honestdid",
    "r_package": "HonestDiD",
    "role": "sensitivity",
    "supports": ["sensitivity_intervals", "robust_ci_table"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_r_plan(adapter=ADAPTER, spec=spec)
    plan["r_calls"] = ["HonestDiD::createSensitivityResults_relativeMagnitudes()"]
    return plan


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
