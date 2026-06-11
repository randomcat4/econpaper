from __future__ import annotations

from typing import Any

from .base import parse_wrapper_result, render_wrapper_plan, skipped


ADAPTER = {
    "name": "cs_did_attgt",
    "backend": "stata_csdid",
    "wrapper_method": "cs_did_attgt",
    "role": "main_if_staggered",
    "supports": ["att_gt", "simple_att", "event_aggregation", "never_treated", "not_yet_treated"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_wrapper_plan(adapter=ADAPTER, spec=spec)
    plan["control_group"] = spec.get("control_group", "never_treated")
    return plan


def parse_result(step_dir: str, manifest: dict[str, Any], spec: dict[str, Any], design_type: str) -> dict[str, Any]:
    return parse_wrapper_result(
        adapter=ADAPTER,
        step_dir=step_dir,
        manifest=manifest,
        spec=spec,
        design_type=design_type,
        control_group=str(spec.get("control_group", "never_treated")),
    )


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
