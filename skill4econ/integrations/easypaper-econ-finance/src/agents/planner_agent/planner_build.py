"""
Plan construction and VLM-analysis helpers for PlannerAgent.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from .models import (
    DEFAULT_EMPIRICAL_SECTIONS,
    NarrativeStyle,
    PaperPlan,
    PaperType,
    SectionPlan,
    WORDS_PER_SENTENCE,
    estimate_target_paragraphs,
)
from .planner_defaults import get_section_title
from .planner_sections import (
    enforce_required_sections,
    normalize_constraints_required_sections,
)
from .planner_utils import normalize_code_focus, normalize_section_type_name


def _normalize_discussion_title(section: SectionPlan) -> None:
    if (
        section.section_type == "discussion"
        and "conclusion" in str(section.section_title or "").lower()
    ):
        section.section_title = "Discussion"


def _base_section_type(section_type: str) -> str:
    section_type = normalize_section_type_name(str(section_type or ""))
    if "_" in section_type:
        prefix, suffix = section_type.rsplit("_", 1)
        if suffix.isdigit():
            return normalize_section_type_name(prefix)
    return section_type


def _truncate_prompt_value(value: Any, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def format_venue_required_sections_block(required_sections: List[str]) -> str:
    if not required_sections:
        return ""

    section_lines = "\n".join(
        f"- {get_section_title(section_id)}" for section_id in required_sections
    )
    return f"""Venue required sections:
{section_lines}

You must produce a paper plan that includes these sections in this order.
For economics and finance papers, do not replace Data / Empirical Strategy / Results / Robustness with generic ML sections such as Method / Experiment / Result."""


def format_content_brief_block(
    content_brief: Dict[str, Any],
    section_order: Optional[List[str]] = None,
    max_chars_per_section: int = 360,
) -> str:
    if not isinstance(content_brief, dict) or not content_brief:
        return ""

    ordered_keys: List[str] = []
    for key in section_order or []:
        if key in content_brief and key not in ordered_keys:
            ordered_keys.append(key)
    for key in content_brief:
        if key not in ordered_keys:
            ordered_keys.append(key)

    lines = []
    for key in ordered_keys:
        value = _truncate_prompt_value(content_brief.get(key), max_chars_per_section)
        if value:
            lines.append(f"{key}: {value}")

    if not lines:
        return ""
    return "Content brief by section:\n" + "\n".join(lines)


def _next_body_section_type(section_type: str, counts: Dict[str, int]) -> str:
    base_type = _base_section_type(section_type)
    counts[base_type] = counts.get(base_type, 0) + 1
    if counts[base_type] == 1:
        return base_type
    return f"{base_type}_{counts[base_type]}"


def normalize_full_paper_section_items(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enforce the current EasyPaper full-paper section invariant.

    The planner can still fall back to defaults for malformed/short outlines,
    but any LLM-provided full-paper outline must include front matter and a
    standalone conclusion. Discussion may discuss implications, but it should
    not own a merged conclusion title once a dedicated conclusion exists.
    """
    normalized: List[Dict[str, Any]] = []
    present: set[str] = set()
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_type = normalize_section_type_name(str(section.get("section_type", "")))
        if not section_type:
            continue
        if section_type in {"abstract", "conclusion"} and section_type in present:
            continue
        item = dict(section)
        item["section_type"] = section_type
        if (
            section_type == "discussion"
            and "conclusion" in str(item.get("section_title", "")).lower()
        ):
            item["section_title"] = "Discussion"
        normalized.append(item)
        present.add(section_type)

    if len(normalized) >= 3:
        if "abstract" not in present:
            normalized.insert(0, {"section_type": "abstract", "section_title": "Abstract"})
            present.add("abstract")
        if "conclusion" not in present:
            normalized.append({"section_type": "conclusion", "section_title": "Conclusion"})

    return normalized


def enforce_full_paper_plan_invariant(plan: PaperPlan) -> PaperPlan:
    """
    Reapply the full-paper section invariant to a materialized PaperPlan.

    Review/optimizer passes can replace the whole plan after initial structure
    normalization, so the invariant is enforced again before a plan is returned.
    """
    sections = list(getattr(plan, "sections", []) or [])
    if len(sections) < 3:
        return plan

    for section in sections:
        _normalize_discussion_title(section)

    ordered: List[SectionPlan] = []
    conclusion: Optional[SectionPlan] = None
    has_abstract = False
    body_counts: Dict[str, int] = {}
    for section in sections:
        section_type = _base_section_type(str(section.section_type or ""))
        if section_type == "abstract":
            if not has_abstract:
                section.section_type = "abstract"
                ordered.insert(0, section)
                has_abstract = True
            continue
        if section_type == "conclusion":
            if conclusion is None:
                section.section_type = "conclusion"
                conclusion = section
            continue
        if section_type:
            section.section_type = _next_body_section_type(section_type, body_counts)
            ordered.append(section)

    if not has_abstract:
        abstract = SectionPlan(section_type="abstract", section_title="Abstract")
        ordered.insert(0, abstract)

    if conclusion is None:
        conclusion = SectionPlan(section_type="conclusion", section_title="Conclusion")
    else:
        conclusion.section_title = conclusion.section_title or "Conclusion"

    ordered.append(conclusion)
    for order, section in enumerate(ordered):
        section.order = order
    plan.sections = ordered
    return plan


async def analyze_figures(vlm_service, logger, figures: List[Any]) -> Dict[str, Any]:
    results = {}
    if not vlm_service:
        return results
    for fig in figures:
        file_path = getattr(fig, "file_path", "") or ""
        if not file_path:
            continue
        try:
            analysis = await vlm_service.analyze_figure(file_path)
            results[fig.id] = analysis
            logger.info("planner.vlm_figure id=%s role=%s", fig.id, analysis.semantic_role)
        except Exception as e:
            logger.warning("planner.vlm_figure_error id=%s: %s", fig.id, e)
    return results


async def analyze_tables(vlm_service, logger, tables: List[Any]) -> Dict[str, Any]:
    results = {}
    if not vlm_service:
        return results
    for tbl in tables:
        file_path = getattr(tbl, "file_path", "") or ""
        content = getattr(tbl, "content", "") or ""
        if not file_path and not content:
            continue
        try:
            if file_path and _is_visual_table_path(file_path):
                analysis = await vlm_service.analyze_table_image(file_path)
            else:
                with tempfile.TemporaryDirectory(prefix="easypaper_table_preview_") as tmp_dir:
                    visual_path = _prepare_table_visual_analysis_path(tbl, logger, tmp_dir)
                    if not visual_path:
                        logger.warning(
                            "planner.vlm_table_skipped id=%s reason=no_visual_preview",
                            getattr(tbl, "id", ""),
                        )
                        continue
                    analysis = await vlm_service.analyze_table_image(visual_path)
            results[tbl.id] = analysis
            logger.info("planner.vlm_table id=%s role=%s", tbl.id, analysis.semantic_role)
        except Exception as e:
            logger.warning("planner.vlm_table_error id=%s: %s", tbl.id, e)
    return results


def _is_visual_table_path(file_path: str) -> bool:
    suffix = Path(file_path or "").suffix.lower()
    return suffix in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _prepare_table_visual_analysis_path(table: Any, logger, output_dir: str) -> str:
    """
    Return a visual artifact path suitable for VLM table analysis.

    Metadata table paths often point at CSV/Markdown files. The VLM service
    expects an image/PDF, so text tables are first rendered into a standalone
    table preview PDF and that PDF is passed to the VLM.
    """
    from ..shared.table_converter import (
        build_table_preview_documents,
        compile_table_preview_document,
    )

    table_id = getattr(table, "id", "") or "table"
    file_path = getattr(table, "file_path", "") or ""
    preview_table = SimpleNamespace(
        id=table_id,
        caption=getattr(table, "caption", "") or table_id,
        content=getattr(table, "content", "") or "",
        file_path=file_path,
        auto_generate=getattr(table, "auto_generate", False),
        wide=getattr(table, "wide", False),
    )

    try:
        previews = build_table_preview_documents(
            tables=[preview_table],
            converted_tables={},
            column_format="double",
            allow_placeholder=False,
        )
    except Exception as e:
        logger.warning(
            "planner.vlm_table_preview_build_failed id=%s: %s",
            table_id,
            e,
        )
        return ""

    preview_tex = previews.get(table_id, "")
    if not preview_tex:
        return ""

    result = compile_table_preview_document(
        table_id=table_id,
        preview_tex=preview_tex,
        output_dir=output_dir,
        max_passes=2,
        timeout_seconds=60,
    )
    if not result.get("success"):
        logger.warning(
            "planner.vlm_table_preview_compile_failed id=%s errors=%s",
            table_id,
            result.get("errors") or [],
        )
        return ""

    pdf_path = str(result.get("pdf_path") or "")
    if not pdf_path or not Path(pdf_path).is_file():
        return ""

    return pdf_path


async def build_paper_plan(
    *,
    plan_data: Dict[str, Any],
    request,
    total_words: int,
    figure_analyses: Optional[Dict[str, Any]] = None,
    table_analyses: Optional[Dict[str, Any]] = None,
    parse_paragraph_plans_fn,
    generate_default_paragraphs_fn,
    build_figure_placements_fn,
    build_table_placements_fn,
    get_section_title_fn,
    get_default_sources_fn,
    get_dependencies_fn,
    normalize_string_list_fn,
    coerce_bool_fn,
    expand_paragraph_plan_fn,
    assign_figure_table_definitions_fn,
    logger=None,
) -> PaperPlan:
    paper_type_str = plan_data.get("paper_type", "empirical").lower()
    try:
        paper_type = PaperType(paper_type_str)
    except ValueError:
        paper_type = PaperType.EMPIRICAL

    style_str = plan_data.get("narrative_style", "technical").lower()
    try:
        narrative_style = NarrativeStyle(style_str)
    except ValueError:
        narrative_style = NarrativeStyle.TECHNICAL

    llm_sections = normalize_full_paper_section_items(plan_data.get("sections", []))
    section_map: Dict[str, Dict[str, Any]] = {}
    llm_section_order: List[str] = []
    body_counts: Dict[str, int] = {}
    for s in llm_sections:
        base_type = _base_section_type(str(s.get("section_type", "")))
        if not base_type:
            continue
        st = (
            base_type
            if base_type in {"abstract", "conclusion"}
            else _next_body_section_type(base_type, body_counts)
        )
        if st in section_map:
            continue
        if st != s.get("section_type"):
            s = dict(s)
            s["section_type"] = st
        section_map[st] = s
        llm_section_order.append(st)

    use_llm_structure = len(llm_section_order) >= 3
    section_type_order = llm_section_order if use_llm_structure else list(DEFAULT_EMPIRICAL_SECTIONS)
    target_paragraphs = estimate_target_paragraphs(total_words)

    sections: List[SectionPlan] = []
    for order, section_type in enumerate(section_type_order):
        llm_section = section_map.get(section_type, {})
        raw_paragraphs = llm_section.get("paragraphs", [])
        paragraphs = parse_paragraph_plans_fn(raw_paragraphs)
        if not paragraphs:
            n_sections = max(1, len(section_type_order))
            default_sents = max(3, (total_words // WORDS_PER_SENTENCE) // n_sections)
            paragraphs = generate_default_paragraphs_fn(section_type, default_sents, llm_section)

        raw_figures = llm_section.get("figures", [])
        raw_tables = llm_section.get("tables", [])
        figure_placements = build_figure_placements_fn(raw_figures, figure_analyses or {})
        table_placements = build_table_placements_fn(raw_tables, table_analyses or {})
        figs_to_ref = llm_section.get("figures_to_reference", [])
        tbls_to_ref = llm_section.get("tables_to_reference", [])

        sections.append(
            SectionPlan(
                section_type=section_type,
                section_title=llm_section.get("section_title", get_section_title_fn(section_type)),
                paragraphs=paragraphs,
                figures=figure_placements,
                tables=table_placements,
                figures_to_reference=figs_to_ref,
                tables_to_reference=tbls_to_ref,
                content_sources=llm_section.get("content_sources", get_default_sources_fn(section_type)),
                depends_on=llm_section.get("depends_on", get_dependencies_fn(section_type)),
                citation_budget=llm_section.get("citation_budget", {}),
                topic_clusters=normalize_string_list_fn(llm_section.get("topic_clusters", []), max_items=4),
                transition_intents=normalize_string_list_fn(llm_section.get("transition_intents", []), max_items=3),
                sectioning_recommended=coerce_bool_fn(llm_section.get("sectioning_recommended", False)),
                code_focus=normalize_code_focus(llm_section.get("code_focus", {})),
                writing_guidance=llm_section.get("writing_guidance", ""),
                order=order,
            )
        )

    llm_total_paras = sum(len(sp.paragraphs) for sp in sections)
    if llm_total_paras > 0 and llm_total_paras < target_paragraphs * 0.5:
        scale = target_paragraphs / max(1, llm_total_paras)
        for sp in sections:
            if sp.section_type in ("abstract", "conclusion"):
                continue
            section_target_sents = int(sum(p.approx_sentences for p in sp.paragraphs) * scale)
            sp.paragraphs = expand_paragraph_plan_fn(sp.paragraphs, section_target_sents, sp.section_type)
        expanded_total = sum(len(sp.paragraphs) for sp in sections)
        if logger:
            logger.info(
                "planner.plan_budget_expansion llm_paras=%d target=%d expanded=%d",
                llm_total_paras, target_paragraphs, expanded_total,
            )

    raw_strategy = plan_data.get("citation_strategy", {})
    if isinstance(raw_strategy, dict):
        citation_strategy = {
            "total_target": int(raw_strategy.get("total_target", 0) or 0),
            "rationale": str(raw_strategy.get("rationale", "")),
            "section_allocation": raw_strategy.get("section_allocation", {}),
        }
    else:
        citation_strategy = {}

    paper_plan = PaperPlan(
        title=request.title,
        paper_type=paper_type,
        sections=sections,
        contributions=plan_data.get("contributions", []),
        narrative_style=narrative_style,
        terminology=plan_data.get("terminology", {}),
        structure_rationale=plan_data.get("structure_rationale", ""),
        abstract_focus=plan_data.get("abstract_focus", ""),
        citation_strategy=citation_strategy,
    )
    required_sections = normalize_constraints_required_sections(
        getattr(request, "constraints", None)
    )
    paper_plan = enforce_required_sections(paper_plan, required_sections)

    await assign_figure_table_definitions_fn(paper_plan, request, figure_analyses, table_analyses)
    return paper_plan
