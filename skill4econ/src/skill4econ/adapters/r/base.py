from __future__ import annotations

from typing import Any

from ..did_common import skipped_backend_unavailable


def render_r_plan(*, adapter: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter": adapter["name"],
        "backend": adapter["backend"],
        "engine": "r",
        "r_package": adapter.get("r_package"),
        "status": "interface_only_until_r_smoke",
        "spec": spec,
        "no_fallback_substitution": True,
    }


def skipped(adapter: dict[str, Any], *, design_type: str, message: str) -> dict[str, Any]:
    return skipped_backend_unavailable(
        estimator=adapter["name"],
        design_type=design_type,
        backend=adapter["backend"],
        message=message,
    )
