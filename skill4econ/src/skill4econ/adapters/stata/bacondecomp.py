from __future__ import annotations

from typing import Any

from .base import skipped


ADAPTER = {
    "name": "bacondecomp",
    "backend": "stata_bacondecomp",
    "wrapper_method": None,
    "role": "twfe_weight_diagnostic",
    "supports": ["bacon_decomposition_csv", "weight_scatter"],
    "status": "interface_only_until_backend_smoke",
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter": ADAPTER["name"],
        "backend": ADAPTER["backend"],
        "engine": "stata",
        "status": "not_wired",
        "required_fields": ["y", "id", "time", "gvar"],
        "spec": spec,
    }


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)
