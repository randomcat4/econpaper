from __future__ import annotations

from typing import Any

from .base import parse_wrapper_result, render_wrapper_plan, skipped


ADAPTER = {
    "name": "did_imputation",
    "backend": "stata_bjs",
    "wrapper_method": "did_imputation_event",
    "role": "robustness",
    "supports": ["treatment_date", "event_study", "pretrend_coefficients", "individual_effects"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_wrapper_plan(adapter=ADAPTER, spec=spec)
    plan["horizons"] = spec.get("horizons", spec.get("window", "0/3"))
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
