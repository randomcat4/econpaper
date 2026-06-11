"""Deterministic policy for optional Dreamer-backed figure supplementation."""

from __future__ import annotations

import re
from hashlib import sha1
from typing import Any, Dict, List, Tuple

from .models import FigureSpec, PaperMetaData

ALLOWED_AUTONOMOUS_ROLES = {
    "conceptual_framework",
    "taxonomy",
    "pipeline",
    "architecture",
    "protocol",
    "info_figure",
}

ROLE_TO_TARGET_TYPE = {
    "conceptual_framework": "infograph",
    "taxonomy": "infograph",
    "pipeline": "flowchart",
    "architecture": "architecture_diagram",
    "protocol": "flowchart",
    "info_figure": "infograph",
}

_STRUCTURE_TERMS = (
    "framework",
    "system",
    "pipeline",
    "architecture",
    "workflow",
    "benchmark",
    "taxonomy",
)
_PROCESS_TERMS = (
    "module",
    "modules",
    "stage",
    "stages",
    "agent",
    "agents",
    "component",
    "components",
    "process",
    "workflow",
    "pipeline",
    "architecture",
)
_RELATED_AXIS_TERMS = (
    "axis",
    "axes",
    "category",
    "categories",
    "cluster",
    "clusters",
    "taxonomy",
    "comparison dimension",
)
_RESULT_TERMS = (
    "result",
    "results",
    "accuracy",
    "performance",
    "metric",
    "benchmark score",
    "ablation",
    "f1",
    "auc",
    "precision",
    "recall",
)


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains_any(text: str, terms: Tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _existing_non_result_roles(metadata: PaperMetaData) -> set[str]:
    roles: set[str] = set()
    for figure in metadata.figures or []:
        blob = _norm(
            " ".join(
                [
                    getattr(figure, "semantic_role", ""),
                    getattr(figure, "target_type", "") or "",
                    getattr(figure, "caption", ""),
                    getattr(figure, "description", ""),
                ]
            )
        )
        if _contains_any(blob, _RESULT_TERMS):
            continue
        for role in ALLOWED_AUTONOMOUS_ROLES:
            if role.replace("_", " ") in blob or role in blob:
                roles.add(role)
    return roles


def _planner_assigns_result_figures_to_non_result_sections(metadata: PaperMetaData) -> bool:
    for figure in metadata.figures or []:
        section = _norm(getattr(figure, "section", "")).replace(" ", "_")
        if section not in {"introduction", "related_work", "method", "methodology"}:
            continue
        blob = _norm(
            " ".join(
                [
                    getattr(figure, "semantic_role", ""),
                    getattr(figure, "target_type", "") or "",
                    getattr(figure, "caption", ""),
                    getattr(figure, "description", ""),
                ]
            )
        )
        if _contains_any(blob, _RESULT_TERMS):
            return True
    return False


def _flatten_context(context: Any) -> str:
    if not context:
        return ""
    if isinstance(context, str):
        return context
    if isinstance(context, dict):
        values: List[str] = []
        for value in context.values():
            values.append(_flatten_context(value))
        return " ".join(values)
    if isinstance(context, list):
        return " ".join(_flatten_context(item) for item in context)
    return str(context)


def _choose_role(metadata_blob: str, code_blob: str, research_blob: str) -> str:
    if any(term in metadata_blob or term in code_blob for term in ("architecture", "system", "component", "module")):
        return "architecture"
    if any(term in metadata_blob or term in code_blob for term in ("pipeline", "workflow", "stage", "process")):
        return "pipeline"
    if "taxonomy" in metadata_blob or _contains_any(research_blob, _RELATED_AXIS_TERMS):
        return "taxonomy"
    if "protocol" in metadata_blob:
        return "protocol"
    if "framework" in metadata_blob:
        return "conceptual_framework"
    return "info_figure"


def analyze_figure_supplementation_need(
    metadata: PaperMetaData,
    *,
    research_context: Any = None,
    code_context: Any = None,
    style_guide: str | None = None,
) -> tuple[List[FigureSpec], Dict[str, Any]]:
    """
    Decide whether EasyPaper may autonomously add non-result support figures.

    The policy is intentionally conservative: no result/data-visualization target
    is allowed, and at least two independent deterministic support signals are
    required before a figure is proposed.
    """
    trace: Dict[str, Any] = {
        "enabled": bool(getattr(metadata, "enable_figure_supplementation", False)),
        "accepted": [],
        "rejected": [],
        "support_signals": [],
        "warnings": [],
    }
    if not trace["enabled"]:
        trace["status"] = "disabled"
        return [], trace

    metadata_blob = _norm(
        " ".join(
            [
                metadata.title,
                metadata.idea_hypothesis,
                metadata.method,
                metadata.data,
                metadata.experiments,
            ]
        )
    )
    code_blob = _norm(_flatten_context(code_context))
    research_blob = _norm(_flatten_context(research_context))
    existing_roles = _existing_non_result_roles(metadata)

    signals: List[str] = []
    if _contains_any(metadata_blob, _STRUCTURE_TERMS):
        signals.append("metadata_structure_terms")
    if not existing_roles:
        signals.append("no_existing_non_result_visual")
    if _planner_assigns_result_figures_to_non_result_sections(metadata):
        signals.append("result_figures_in_non_result_sections")
    if _contains_any(metadata_blob + " " + code_blob, _PROCESS_TERMS):
        signals.append("process_or_component_signals")
    if _contains_any(research_blob, _RELATED_AXIS_TERMS):
        signals.append("related_work_comparison_axes")

    trace["support_signals"] = signals
    if len(signals) < 2:
        trace["status"] = "skipped"
        trace["rejected"].append(
            {
                "reason": "insufficient_support_signals",
                "support_signal_count": len(signals),
            }
        )
        return [], trace

    role = _choose_role(metadata_blob, code_blob, research_blob)
    if role not in ALLOWED_AUTONOMOUS_ROLES:
        trace["status"] = "skipped"
        trace["rejected"].append({"reason": "unsupported_role", "semantic_role": role})
        return [], trace

    target_type = ROLE_TO_TARGET_TYPE[role]
    if target_type == "data_visualization":
        trace["status"] = "skipped"
        trace["rejected"].append({"reason": "autonomous_data_visualization_forbidden"})
        return [], trace

    section = "method" if role in {"pipeline", "architecture", "protocol"} else "related_work"
    if role in {"conceptual_framework", "taxonomy", "info_figure"}:
        section = "related_work" if "related_work_comparison_axes" in signals else "introduction"

    rationale = (
        f"EasyPaper adds this {role.replace('_', ' ')} only because the metadata and "
        f"context expose {len(signals)} independent support signals ({', '.join(signals)}). "
        "The visual is non-result explanatory material intended to clarify the paper's "
        "structure or conceptual organization, not to replace or preview empirical results."
    )
    if len(rationale) < 80 or "balance" in rationale.lower():
        trace["status"] = "skipped"
        trace["rejected"].append({"reason": "weak_or_balancing_rationale"})
        return [], trace

    slug = sha1(f"{metadata.title}|{role}|{section}".encode("utf-8")).hexdigest()[:10]
    figure = FigureSpec(
        id=f"fig:supplemental-{role.replace('_', '-')}-{slug}",
        caption=f"{role.replace('_', ' ').title()} for {metadata.title}",
        description=rationale,
        section=section,
        auto_generate=True,
        generation_prompt=(
            f"Create a publication-ready {role.replace('_', ' ')} diagram for the paper "
            f"'{metadata.title}'. Show concepts, components, or workflow relationships only. "
            "Do not show empirical result curves, benchmark bars, metrics, or ablation data."
        ),
        style=style_guide or metadata.style_guide,
        target_type=target_type,
        semantic_role=role,
        supplementation_rationale=rationale,
        supplemental=True,
        generated_by="easypaper_figure_supplementation",
        support_signals=signals,
    )
    trace["accepted"].append(figure.model_dump(mode="json"))
    trace["status"] = "accepted"
    return [figure], trace
