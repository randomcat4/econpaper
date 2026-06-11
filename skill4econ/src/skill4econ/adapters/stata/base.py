from __future__ import annotations

from pathlib import Path
from typing import Any

from ..did_common import build_common_output, skipped_backend_unavailable, write_common_output


def render_wrapper_plan(
    *,
    adapter: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    return {
        "adapter": adapter["name"],
        "backend": adapter["backend"],
        "wrapper_method": adapter.get("wrapper_method"),
        "engine": "stata",
        "spec": spec,
        "no_fallback_substitution": True,
    }


def parse_wrapper_result(
    *,
    adapter: dict[str, Any],
    step_dir: str | Path,
    manifest: dict[str, Any],
    spec: dict[str, Any],
    design_type: str,
    control_group: str | None = None,
) -> dict[str, Any]:
    step_path = Path(step_dir)
    payload = build_common_output(
        estimator=adapter["name"],
        design_type=design_type,
        step_dir=step_path,
        status=str(manifest.get("status") or "unknown"),
        manifest=manifest,
        spec=spec,
        backend=adapter["backend"],
        engine="stata",
        role=adapter.get("role"),
        control_group=control_group,
    )
    write_common_output(step_path, payload)
    return payload


def skipped(adapter: dict[str, Any], *, design_type: str, message: str) -> dict[str, Any]:
    return skipped_backend_unavailable(
        estimator=adapter["name"],
        design_type=design_type,
        backend=adapter["backend"],
        message=message,
    )
