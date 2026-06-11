from __future__ import annotations

from typing import Any

from .base import render_r_plan, skipped


ADAPTER = {
    "name": "did_r_att_gt",
    "backend": "r_did",
    "r_package": "did",
    "role": "main_if_staggered",
    "supports": ["att_gt", "aggte_simple", "aggte_dynamic", "aggte_group", "aggte_calendar"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_r_plan(adapter=ADAPTER, spec=spec)
    plan["r_calls"] = ["did::att_gt()", "did::aggte()"]
    return plan


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
