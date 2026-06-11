from __future__ import annotations

from typing import Any

from .base import parse_wrapper_result, render_wrapper_plan, skipped


ADAPTER = {
    "name": "drdid",
    "backend": "stata_drdid",
    "wrapper_method": "dr_did_2x2",
    "role": "covariate_adjusted_main",
    "supports": ["panel_2x2", "repeated_cross_section", "covariates", "cluster"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_wrapper_plan(adapter=ADAPTER, spec=spec)
    plan["data_type"] = spec.get("data_type", "panel" if spec.get("id") else "repeated_cross_section")
    return plan


def parse_result(step_dir: str, manifest: dict[str, Any], spec: dict[str, Any], design_type: str) -> dict[str, Any]:
    return parse_wrapper_result(
        adapter=ADAPTER,
        step_dir=step_dir,
        manifest=manifest,
        spec=spec,
        design_type=design_type,
        control_group=spec.get("control_group"),
    )


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
