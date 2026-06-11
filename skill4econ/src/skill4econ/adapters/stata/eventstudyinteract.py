from __future__ import annotations

from typing import Any

from .base import skipped


ADAPTER = {
    "name": "eventstudyinteract",
    "backend": "stata_eventstudyinteract",
    "wrapper_method": None,
    "role": "dynamic_effect",
    "supports": ["cohort_variable", "relative_time_indicators", "omitted_baseline"],
    "status": "interface_only_until_backend_smoke",
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter": ADAPTER["name"],
        "backend": ADAPTER["backend"],
        "engine": "stata",
        "status": "not_wired",
        "required_fields": ["y", "id", "time", "gvar", "event_time"],
        "spec": spec,
    }


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
