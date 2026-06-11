"""
Figure-usage planning and validation helpers for MetaDataAgent.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ..planner_agent.models import FigureUsagePlan, ParagraphPlan, SectionPlan
from .models import FigureSpec


def validate_required_figure_usages(
    raw_latex: str,
    final_latex: str,
    paragraph_plan: ParagraphPlan,
) -> Tuple[bool, str, List[str]]:
    required_usages = [
        usage for usage in (getattr(paragraph_plan, "figure_usages", []) or [])
        if getattr(usage, "must_appear", False)
    ]
    if not required_usages:
        return True, "", []

    raw_latex = raw_latex or ""
    final_latex = final_latex or ""
    missing: List[str] = []
    hints: List[str] = []

    dangling_pattern = re.compile(
        r'\b(?:shown|illustrated|visualized|depicted|captured|reported|'
        r'detailed|summarized|presented|compared|displayed|listed|tabulated)\s+in(?=[,.;:])',
        re.IGNORECASE,
    )

    for usage in required_usages:
        fig_id = getattr(usage, "figure_id", "")
        if not fig_id:
            continue

        marker_present = f"[FLOAT:{fig_id}]" in raw_latex
        direct_ref_present = f"\\ref{{{fig_id}}}" in raw_latex or f"Figure~\\ref{{{fig_id}}}" in raw_latex
        final_ref_present = f"Figure~\\ref{{{fig_id}}}" in final_latex

        if marker_present or direct_ref_present:
            continue

        missing.append(fig_id)
        semantic_hint = getattr(usage, "supported_claim", "") or getattr(usage, "what_it_shows", "")
        base = (
            f"Required figure reference missing for {fig_id}. "
            f"Insert `[FLOAT:{fig_id}]` exactly where the paragraph discusses this figure."
        )
        if semantic_hint:
            base += f" Figure purpose: {semantic_hint}"
        if final_ref_present and not marker_present and not direct_ref_present:
            base += " Do not rely on auto-appended references; author the figure reference in the sentence itself."
        elif dangling_pattern.search(raw_latex) or dangling_pattern.search(final_latex):
            base += " Replace dangling phrases like 'as visualized in,' with an explicit figure reference."
        hints.append(base)

    if missing:
        return False, "\n".join(hints), missing
    return True, "", []


def ensure_paragraph_figure_usages(
    *,
    section_type: str,
    section_plan: SectionPlan,
    figure_map: Dict[str, FigureSpec],
    placement_map: Dict[str, Any],
) -> None:
    first_ref_by_figure: Dict[str, int] = {}
    for pidx, para in enumerate(section_plan._all_paragraphs()):
        figs_to_ref = getattr(para, "figures_to_reference", []) or []
        if getattr(para, "figure_usages", None):
            enriched: List[FigureUsagePlan] = []
            for usage in para.figure_usages:
                fig_id = getattr(usage, "figure_id", "")
                fig = figure_map.get(fig_id)
                placement = placement_map.get(fig_id)
                if fig_id and fig_id not in first_ref_by_figure:
                    first_ref_by_figure[fig_id] = pidx
                enriched.append(
                    FigureUsagePlan(
                        figure_id=fig_id,
                        mode=getattr(usage, "mode", "") or (
                            "define"
                            if placement and first_ref_by_figure.get(fig_id, pidx) == pidx
                            else "reference"
                        ),
                        rhetorical_role=getattr(usage, "rhetorical_role", "") or (
                            "introduce"
                            if placement and first_ref_by_figure.get(fig_id, pidx) == pidx
                            else "support"
                        ),
                        claim_binding=getattr(usage, "claim_binding", "") or getattr(para, "claim_id", "") or "",
                        semantic_role=getattr(usage, "semantic_role", "") or (getattr(placement, "semantic_role", "") if placement else ""),
                        what_it_shows=getattr(usage, "what_it_shows", "") or (
                            getattr(placement, "message", "") if placement and getattr(placement, "message", "") else (
                                getattr(fig, "description", "") if fig else ""
                            )
                        ),
                        supported_claim=getattr(usage, "supported_claim", "") or getattr(para, "key_point", "") or "",
                        owner_section=getattr(usage, "owner_section", "") or (getattr(fig, "section", "") if fig else "") or section_type,
                        must_appear=bool(getattr(usage, "must_appear", False)),
                        caption=getattr(usage, "caption", "") or (getattr(fig, "caption", "") if fig else ""),
                        caption_guidance=getattr(usage, "caption_guidance", "") or (getattr(placement, "caption_guidance", "") if placement else ""),
                    )
                )
            para.figure_usages = enriched
            continue

        derived_figure_usages: List[FigureUsagePlan] = []
        for fig_id in figs_to_ref:
            fig = figure_map.get(fig_id)
            placement = placement_map.get(fig_id)
            if fig_id not in first_ref_by_figure:
                first_ref_by_figure[fig_id] = pidx
            is_first_ref = first_ref_by_figure.get(fig_id) == pidx

            supported_claim = getattr(para, "key_point", "") or ""
            what_it_shows = ""
            if placement and getattr(placement, "message", ""):
                what_it_shows = placement.message
            elif fig and getattr(fig, "description", ""):
                what_it_shows = fig.description
            elif fig and getattr(fig, "caption", ""):
                what_it_shows = fig.caption

            derived_figure_usages.append(
                FigureUsagePlan(
                    figure_id=fig_id,
                    mode="define" if placement and is_first_ref else "reference",
                    rhetorical_role="introduce" if placement and is_first_ref else "support",
                    claim_binding=getattr(para, "claim_id", "") or "",
                    semantic_role=getattr(placement, "semantic_role", "") if placement else "",
                    what_it_shows=what_it_shows,
                    supported_claim=supported_claim,
                    owner_section=(getattr(fig, "section", "") if fig else "") or section_type,
                    must_appear=True,
                    caption=getattr(fig, "caption", "") if fig else "",
                    caption_guidance=getattr(placement, "caption_guidance", "") if placement else "",
                )
            )
        para.figure_usages = derived_figure_usages
