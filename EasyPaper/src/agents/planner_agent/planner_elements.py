"""
Figure/table placement and assignment helpers for PlannerAgent.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from ..shared.table_converter import normalize_caption
from .models import FigurePlacement, PaperPlan, SectionPlan, TablePlacement


def build_figure_placements(
    raw_figures: List[Dict[str, Any]],
    figure_analyses: Dict[str, Any],
) -> List[FigurePlacement]:
    placements = []
    for raw in raw_figures:
        if not isinstance(raw, dict):
            continue
        fig_id = raw.get("figure_id", "")
        if not fig_id:
            continue
        vlm = figure_analyses.get(fig_id)
        placements.append(
            FigurePlacement(
                figure_id=fig_id,
                semantic_role=getattr(vlm, "semantic_role", "") if vlm else raw.get("semantic_role", ""),
                message=getattr(vlm, "message", "") if vlm else raw.get("message", ""),
                is_wide=getattr(vlm, "is_wide", False) if vlm else raw.get("is_wide", False),
                position_hint=raw.get("position_hint", "mid"),
                caption_guidance=getattr(vlm, "caption_guidance", "") if vlm else raw.get("caption_guidance", ""),
            )
        )
    return placements


def build_table_placements(
    raw_tables: List[Dict[str, Any]],
    table_analyses: Dict[str, Any],
) -> List[TablePlacement]:
    placements = []
    for raw in raw_tables:
        if not isinstance(raw, dict):
            continue
        tbl_id = raw.get("table_id", "")
        if not tbl_id:
            continue
        vlm = table_analyses.get(tbl_id)
        placements.append(
            TablePlacement(
                table_id=tbl_id,
                semantic_role=getattr(vlm, "semantic_role", "") if vlm else raw.get("semantic_role", ""),
                message=getattr(vlm, "message", "") if vlm else raw.get("message", ""),
                is_wide=getattr(vlm, "is_wide", False) if vlm else raw.get("is_wide", False),
                position_hint=raw.get("position_hint", "mid"),
            )
        )
    return placements


def build_assignment_prompt(
    plan: Any,
    figures: Dict[str, Any],
    tables: Dict[str, Any],
    figure_analyses: Optional[Dict[str, Any]] = None,
    table_analyses: Optional[Dict[str, Any]] = None,
) -> str:
    fa = figure_analyses or {}
    ta = table_analyses or {}
    lines: List[str] = [
        "You are an academic paper layout expert.",
        "Assign each figure and table to the BEST section for its content.",
        "Match element semantics to section themes and paragraph key points.",
        "",
        "## Available Sections",
    ]
    for sec in plan.sections:
        title = getattr(sec, "section_title", "") or sec.section_type
        key_points = []
        for p in getattr(sec, "paragraphs", [])[:3]:
            kp = getattr(p, "key_point", "")
            if kp:
                key_points.append(kp)
        for sub in getattr(sec, "subsections", [])[:2]:
            for p in getattr(sub, "paragraphs", [])[:2]:
                kp = getattr(p, "key_point", "")
                if kp:
                    key_points.append(kp)
        kp_str = "; ".join(key_points) if key_points else "(no key points yet)"
        lines.append(f"- **{sec.section_type}** ({title}): {kp_str}")

    lines.append("")
    lines.append("## Elements to Assign")

    for fid, info in figures.items():
        raw_cap = getattr(info, "caption", "") if hasattr(info, "caption") else ""
        cap = normalize_caption(str(raw_cap or ""))
        desc = getattr(info, "description", "") if hasattr(info, "description") else ""
        suggested = getattr(info, "section", "") if hasattr(info, "section") else ""
        semantic_role = getattr(info, "semantic_role", "") if hasattr(info, "semantic_role") else ""
        rationale = getattr(info, "supplementation_rationale", "") if hasattr(info, "supplementation_rationale") else ""
        vlm = fa.get(fid)
        vlm_bits = ""
        if vlm:
            role = getattr(vlm, "semantic_role", "") or ""
            msg = (getattr(vlm, "message", "") or "")[:240]
            sug = getattr(vlm, "suggested_section", "") or ""
            vlm_bits = f' vlm_role="{role}" vlm_summary="{msg}" vlm_suggested_section="{sug}"'
        lines.append(
            f'- {fid}: caption="{cap}", description="{desc}", '
            f'suggested_section="{suggested}", semantic_role="{semantic_role}", '
            f'supplementation_rationale="{rationale}"{vlm_bits}'
        )

    for tid, info in tables.items():
        raw_cap = getattr(info, "caption", "") if hasattr(info, "caption") else ""
        cap = normalize_caption(str(raw_cap or ""))
        desc = getattr(info, "description", "") if hasattr(info, "description") else ""
        vlm = ta.get(tid)
        vlm_bits = ""
        if vlm:
            role = getattr(vlm, "semantic_role", "") or ""
            msg = (getattr(vlm, "message", "") or "")[:240]
            sug = getattr(vlm, "suggested_section", "") or ""
            vlm_bits = f' vlm_role="{role}" vlm_summary="{msg}" vlm_suggested_section="{sug}"'
        lines.append(f'- {tid}: caption="{cap}", description="{desc}"{vlm_bits}')

    lines.append("")
    lines.append("## Rules")
    lines.append("- Performance/comparison tables -> result or experiment sections")
    lines.append("- Ablation tables -> analysis or result sections")
    lines.append("- Do NOT define result/performance/benchmark/ablation tables in introduction")
    lines.append("- Introduction may quote headline numbers or reference later-defined result tables")
    lines.append("- Architecture/method figures -> method section")
    lines.append("- Pipeline/architecture/protocol figures -> method or system sections")
    lines.append("- Conceptual framework/taxonomy/info figures -> introduction or related_work only with explicit rationale")
    lines.append("- Result/performance/benchmark/ablation figures -> result, experiment, evaluation, or analysis sections")
    lines.append("- Do NOT place result figures in introduction, related_work, methodology, or method sections solely to distribute figures")
    lines.append("- Dataset/statistics tables -> experiment section")
    lines.append("- Use ONLY the section_type values listed above")
    lines.append("")
    lines.append("## Output")
    lines.append("Return a JSON object mapping element IDs to section_type values.")
    lines.append('Example: {"fig:arch": "method", "tab:results": "result"}')
    return "\n".join(lines)


def parse_element_assignment(
    llm_response: str,
    elements: Dict[str, Any],
    plan: Any,
    max_per_section: int = 3,
) -> Dict[str, str]:
    valid_types = {s.section_type for s in plan.sections}

    assignment: Dict[str, str] = {}
    try:
        parsed = json.loads(llm_response)
        if isinstance(parsed, dict):
            assignment = parsed
    except (json.JSONDecodeError, TypeError):
        pass

    result: Dict[str, str] = {}

    def _section_base(section_type: str) -> str:
        return re.sub(r"_\d+$", "", section_type).lower()

    def _text_for(info: Any) -> str:
        support = getattr(info, "support_signals", []) if hasattr(info, "support_signals") else []
        text = (
            (getattr(info, "id", "") if hasattr(info, "id") else "")
            + " " + (getattr(info, "caption", "") if hasattr(info, "caption") else "")
            + " " + (getattr(info, "description", "") if hasattr(info, "description") else "")
            + " " + (getattr(info, "semantic_role", "") if hasattr(info, "semantic_role") else "")
            + " " + (getattr(info, "supplementation_rationale", "") if hasattr(info, "supplementation_rationale") else "")
            + " " + (getattr(info, "target_type", "") if hasattr(info, "target_type") else "")
            + " " + " ".join(str(item) for item in (support or []))
        ).lower()
        return text

    def _explicit_non_result_figure_role(info: Any) -> bool:
        if not str(getattr(info, "id", "") or "").startswith("fig:"):
            return False
        role = str(getattr(info, "semantic_role", "") or "").lower().replace("-", "_")
        return role in {
            "architecture",
            "conceptual_framework",
            "info_figure",
            "pipeline",
            "protocol",
            "taxonomy",
        }

    def _semantic_target_bases(info: Any) -> List[str]:
        text = _text_for(info)
        is_figure = str(getattr(info, "id", "") or "").startswith("fig:")
        if _explicit_non_result_figure_role(info):
            role = str(getattr(info, "semantic_role", "") or "").lower().replace("-", "_")
            if role in {"architecture", "pipeline", "protocol"}:
                return ["method", "methodology", "system"]
            return ["related_work", "introduction", "method"]
        if any(term in text for term in ("performance", "comparison", "ablation", "result", "accuracy", "benchmark", "metric", "f1", "auc")):
            return ["result", "results", "evaluation", "experiment", "analysis"]
        if is_figure and any(term in text for term in ("architecture", "pipeline", "workflow", "protocol", "system", "module", "component", "framework")):
            return ["method", "methodology", "system"]
        if is_figure and any(term in text for term in ("taxonomy", "conceptual", "info_figure", "infograph", "background")):
            return ["related_work", "introduction", "method"]
        if any(term in text for term in ("dataset", "statistics", "setup", "hyperparameter")):
            return ["experiment", "method"]
        return ["method", "experiment", "result", "analysis", "related_work", "introduction"]

    def _figure_result_in_early_section(info: Any, section_type: str) -> bool:
        if not str(getattr(info, "id", "") or "").startswith("fig:"):
            return False
        if not any(base in _section_base(section_type) for base in ("introduction", "related_work", "method", "methodology")):
            return False
        if _explicit_non_result_figure_role(info):
            return False
        text = _text_for(info)
        return any(term in text for term in ("performance", "comparison", "ablation", "result", "accuracy", "benchmark", "metric", "f1", "auc"))

    def _keyword_fallback(info: Any) -> str:
        target_bases = _semantic_target_bases(info)
        for base in target_bases:
            for sec in plan.sections:
                if _section_base(sec.section_type) == base or base in _section_base(sec.section_type):
                    return sec.section_type
        body = [s for s in plan.sections if s.section_type not in ("abstract", "conclusion")]
        for sec in body:
            if not _figure_result_in_early_section(info, sec.section_type):
                return sec.section_type
        return plan.sections[0].section_type if plan.sections else "method"

    for eid, info in elements.items():
        assigned_type = assignment.get(eid, "")
        if assigned_type in valid_types and not _figure_result_in_early_section(info, assigned_type):
            result[eid] = assigned_type
        else:
            result[eid] = _keyword_fallback(info)

    return result


def assign_figures_to_sections(
    figures: List[Any],
    section_order: List[Dict[str, str]],
    figure_analyses: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    body_sections = [
        s["section_type"] for s in section_order
        if s["section_type"] not in ("abstract", "conclusion")
    ]
    first_body = body_sections[0] if body_sections else "introduction"

    base_to_sections: Dict[str, List[str]] = {}
    for st in body_sections:
        base = re.sub(r"_\d+$", "", st)
        base_to_sections.setdefault(base, []).append(st)

    assignment: Dict[str, str] = {}
    analyses = figure_analyses or {}

    def _section_base(section_type: str) -> str:
        return re.sub(r"_\d+$", "", section_type).lower()

    def _fig_text(fig: Any) -> str:
        vlm = analyses.get(getattr(fig, "id", ""))
        return " ".join(
            [
                str(getattr(fig, key, "") or "")
                for key in (
                    "id",
                    "caption",
                    "description",
                    "semantic_role",
                    "supplementation_rationale",
                    "target_type",
                )
            ]
            + [
                str(getattr(vlm, key, "") or "")
                for key in (
                    "semantic_role",
                    "message",
                    "suggested_section",
                    "caption_guidance",
                )
            ]
        ).lower()

    def _explicit_non_result_role(fig: Any) -> bool:
        vlm = analyses.get(getattr(fig, "id", ""))
        role = str(
            getattr(vlm, "semantic_role", "") or getattr(fig, "semantic_role", "") or ""
        ).lower().replace("-", "_")
        return role in {
            "architecture",
            "architecture_overview",
            "algorithm_illustration",
            "conceptual_framework",
            "info_figure",
            "pipeline",
            "pipeline_diagram",
            "protocol",
            "taxonomy",
        }

    def _is_result_like(fig: Any) -> bool:
        if _explicit_non_result_role(fig):
            return False
        text = _fig_text(fig)
        return any(term in text for term in ("performance", "comparison", "ablation", "result", "accuracy", "benchmark", "metric", "f1", "auc"))

    def _is_bad_result_section(fig: Any, section_type: str) -> bool:
        if not _is_result_like(fig):
            return False
        base = _section_base(section_type)
        return base in {"introduction", "related_work", "method", "methodology"}

    def _fallback_for(fig: Any) -> str:
        text = _fig_text(fig)
        if _explicit_non_result_role(fig):
            vlm = analyses.get(getattr(fig, "id", ""))
            role = str(
                getattr(vlm, "semantic_role", "") or getattr(fig, "semantic_role", "") or ""
            ).lower().replace("-", "_")
            if role in {"architecture", "architecture_overview", "algorithm_illustration", "pipeline", "pipeline_diagram", "protocol"}:
                priorities = ("method", "methodology", "system")
            else:
                priorities = ("related_work", "introduction", "method")
        elif _is_result_like(fig):
            priorities = ("result", "results", "evaluation", "experiment", "analysis")
        elif any(term in text for term in ("architecture", "pipeline", "workflow", "protocol", "system", "module", "component", "framework")):
            priorities = ("method", "methodology", "system")
        elif any(term in text for term in ("taxonomy", "conceptual", "info_figure", "infograph", "background")):
            priorities = ("related_work", "introduction", "method")
        else:
            priorities = ("method", "experiment", "result", "analysis", "related_work", "introduction")
        for base in priorities:
            for section in body_sections:
                section_base = _section_base(section)
                if section_base == base or base in section_base:
                    if not _is_bad_result_section(fig, section):
                        return section
        for section in body_sections:
            if not _is_bad_result_section(fig, section):
                return section
        return first_body

    for fig in figures:
        fig_id = fig.id
        suggested = getattr(fig, "section", None) or ""
        assigned = False

        if suggested in body_sections and not _is_bad_result_section(fig, suggested):
            assignment[fig_id] = suggested
            assigned = True
        elif suggested:
            suggested_base = re.sub(r"_\d+$", "", suggested.lower())
            candidates = base_to_sections.get(suggested_base, [])
            if candidates:
                best = next((c for c in candidates if not _is_bad_result_section(fig, c)), "")
                if not best:
                    best = _fallback_for(fig)
                assignment[fig_id] = best
                assigned = True

        if not assigned:
            assignment[fig_id] = _fallback_for(fig)

    return assignment


def format_section_figure_info(
    figures: List[Any],
    analyses: Dict[str, Any],
    section_type: str,
    figure_assignment: Dict[str, str],
) -> str:
    if not figures:
        return "None provided"

    define_lines = []
    reference_lines = []

    for fig in figures:
        line = f"- {fig.id}: {fig.caption}"
        if fig.description:
            line += f" ({fig.description})"
        vlm = analyses.get(fig.id)
        if vlm:
            line += f" [VLM: role={getattr(vlm, 'semantic_role', '')}, message={getattr(vlm, 'message', '')}]"

        assigned_to = figure_assignment.get(fig.id)
        if assigned_to == section_type:
            define_lines.append(line)
        else:
            reference_lines.append(line)

    parts = []
    if define_lines:
        parts.append(
            "**DEFINE in this section** (include \\begin{figure}...\\end{figure}):\n"
            + "\n".join(define_lines)
        )
    if reference_lines:
        parts.append(
            "**REFERENCE ONLY** (use \\ref{fig:...}, do NOT create \\begin{figure}):\n"
            + "\n".join(reference_lines)
        )
    if not parts:
        return "None assigned to this section"
    return "\n\n".join(parts)


def format_figure_info(figures: List[Any], analyses: Dict[str, Any]) -> str:
    if not figures:
        return "None provided"
    lines = []
    for fig in figures:
        line = f"- {fig.id}: {fig.caption}"
        if fig.description:
            line += f" ({fig.description})"
        if fig.section:
            line += f" [suggested: {fig.section}]"
        vlm = analyses.get(fig.id)
        if vlm:
            line += f" [VLM: role={getattr(vlm, 'semantic_role', '')}, message={getattr(vlm, 'message', '')}]"
        lines.append(line)
    return "\n".join(lines)


def format_table_info(tables: List[Any], analyses: Dict[str, Any]) -> str:
    if not tables:
        return "None provided"
    lines = []
    for tbl in tables:
        line = f"- {tbl.id}: {tbl.caption}"
        if tbl.description:
            line += f" ({tbl.description})"
        if tbl.section:
            line += f" [suggested: {tbl.section}]"
        vlm = analyses.get(tbl.id)
        if vlm:
            line += f" [VLM: role={getattr(vlm, 'semantic_role', '')}, message={getattr(vlm, 'message', '')}]"
        lines.append(line)
    return "\n".join(lines)


def should_be_wide_figure(fig_info: Any, vlm_analysis: Optional[Any] = None) -> bool:
    if getattr(fig_info, "wide", False):
        return True
    if vlm_analysis is not None:
        return bool(getattr(vlm_analysis, "is_wide", False))
    path = getattr(fig_info, "file_path", "") or ""
    if path:
        try:
            from PIL import Image
        except ImportError:
            Image = None  # type: ignore[assignment,misc]
        if Image is not None:
            try:
                with Image.open(path) as im:
                    w, h = im.size
                if h > 0 and w > 0:
                    ratio = w / h
                    if ratio > 1.8:
                        return True
                    if ratio < 1.0:
                        return False
            except Exception:
                pass
    wide_keywords = [
        "comparison", "overview", "architecture", "pipeline",
        "framework", "full", "complete", "main", "overall",
        "workflow", "system",
    ]
    text = (
        (getattr(fig_info, "id", "") or "")
        + " " + (getattr(fig_info, "caption", "") or "")
        + " " + (getattr(fig_info, "description", "") or "")
    ).lower()
    return any(kw in text for kw in wide_keywords)


def should_be_wide_table(tbl_info: Any) -> bool:
    if getattr(tbl_info, "wide", False):
        return True
    wide_keywords = [
        "main", "comparison", "full", "complete", "all",
        "overall", "summary", "comprehensive",
    ]
    text = (
        (getattr(tbl_info, "id", "") or "")
        + " " + (getattr(tbl_info, "caption", "") or "")
        + " " + (getattr(tbl_info, "description", "") or "")
    ).lower()
    return any(kw in text for kw in wide_keywords)
