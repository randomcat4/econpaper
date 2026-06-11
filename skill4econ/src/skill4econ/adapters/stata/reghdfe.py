from __future__ import annotations

from typing import Any

from .base import parse_wrapper_result, render_wrapper_plan, skipped


ADAPTER = {
    "name": "twfe",
    "backend": "stata_reghdfe_or_regress",
    "wrapper_method": "did_twfe_event",
    "role": "benchmark",
    "supports": ["twfe_main_table", "event_study_twfe", "cluster", "unit_time_fixed_effects"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    return render_wrapper_plan(adapter=ADAPTER, spec=spec)


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
