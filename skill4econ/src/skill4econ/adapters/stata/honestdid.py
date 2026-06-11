from __future__ import annotations

from typing import Any

from .base import skipped


ADAPTER = {
    "name": "honestdid",
    "backend": "stata_honestdid",
    "wrapper_method": None,
    "role": "sensitivity",
    "supports": ["sensitivity_grid", "robust_ci_table"],
    "status": "interface_only_until_backend_smoke",
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter": ADAPTER["name"],
        "backend": ADAPTER["backend"],
        "engine": "stata",
        "status": "not_wired",
        "required_input": "compatible event-study coefficient vector",
        "spec": spec,
    }


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
