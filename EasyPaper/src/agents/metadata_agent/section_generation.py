"""
Section generation helpers for MetaDataAgent.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..shared.code_context import format_code_context_for_prompt
from ..shared.prompt_compiler import (
    compile_body_section_prompt,
    compile_introduction_prompt,
    compile_synthesis_prompt,
)
from ..shared.reference_pool import ReferencePool
from ..shared.session_memory import SessionMemory
from .models import (
    BODY_SECTION_SOURCES,
    INTRODUCTION_SOURCES,
    FigureSpec,
    PaperMetaData,
    SectionResult,
    TableSpec,
)

ECON_FINANCE_SECTION_TYPES = {
    "data",
    "empirical_strategy",
    "results",
    "robustness",
    "institutional_background",
    "theory_or_model",
    "mechanisms",
    "heterogeneity",
}

ECON_FINANCE_STYLE_HINTS = {
    "aer",
    "american-economic-review",
    "qje",
    "quarterly-journal-of-economics",
    "jfe",
    "journal-of-financial-economics",
    "economic",
    "economics",
    "finance",
    "financial",
}

ECON_FINANCE_WRITING_RULES = """## Economics/Finance Writing Rules
- Prefer terms: identification, empirical strategy, estimating equation, treatment, control group, fixed effects, standard errors, robustness checks.
- Avoid ML paper terms unless explicitly relevant: benchmark, ablation, architecture, pipeline, SOTA, model performance.
- Do not invent coefficient magnitudes, p-values, standard errors, confidence intervals, sample sizes, or data sources.
- If numerical result details are absent, describe results qualitatively and mark the limitation.
- Results section must distinguish baseline estimates from robustness checks.
- Robustness section must not introduce new main findings."""


def _figures_visible_to_section(
    figures: Optional[List[FigureSpec]],
    section_type: str,
) -> List[FigureSpec]:
    """Expose assigned figures only to their owner section during writing."""
    visible: List[FigureSpec] = []
    for fig in figures or []:
        owner = str(getattr(fig, "section", "") or "")
        if not owner or owner == section_type:
            visible.append(fig)
    return visible


def build_writer_valid_keys(
    section_plan,
    ref_pool: ReferencePool,
) -> List[str]:
    section_type = getattr(section_plan, "section_type", None) if section_plan else None
    allowed = ref_pool.citable_keys(section_type)
    section_keys = section_plan.assigned_refs if section_plan and section_plan.assigned_refs else list(allowed)
    selected_keys = (
        section_plan.budget_selected_refs
        if section_plan and section_plan.budget_selected_refs
        else section_keys
    )
    return [key for key in dict.fromkeys(list(selected_keys)) if key in allowed]


def append_prompt_trace(
    prompt_traces: Optional[List[Dict[str, Any]]],
    *,
    section_type: str,
    prompt: str,
    code_context_used: bool,
    research_context_used: bool = False,
    runtime_evidence: Optional[List[Dict[str, Any]]] = None,
) -> None:
    if prompt_traces is None:
        return
    prompt_traces.append(
        {
            "section_type": section_type,
            "phase": "generation",
            "code_context_used": code_context_used,
            "research_context_used": research_context_used,
            "runtime_evidence": runtime_evidence or [],
            "prompt": prompt,
        }
    )


def build_section_result(
    *,
    section_type: str,
    section_title: str,
    content: str,
) -> SectionResult:
    return SectionResult(
        section_type=section_type,
        section_title=section_title,
        status="ok",
        latex_content=content,
        word_count=len(content.split()),
    )


def sanitize_synthesis_content(
    section_type: str,
    content: str,
) -> str:
    if section_type not in ("abstract", "conclusion"):
        return content
    content = re.sub(r"~?\\cite\{[^}]*\}", "", content)
    content = re.sub(
        r"(?:Figure|Fig\.|Table|Tab\.|Section|Sec\.|Equation|Eq\.)~?\\ref\{[^}]*\}",
        "",
        content,
    )
    content = re.sub(r"~?\\ref\{[^}]*\}", "", content)
    content = re.sub(r"\[CITE:[^\]]*\]", "", content)
    content = re.sub(r"\[FLOAT:[^\]]*\]", "", content)
    content = re.sub(r"\(\s*[,;]?\s*\)", "", content)
    content = re.sub(r"  +", " ", content)
    return content


def _brief_value(content_brief: Optional[Dict[str, str]], key: str) -> str:
    if not isinstance(content_brief, dict):
        return ""
    value = content_brief.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _ordered_unique_sources(*groups: List[str]) -> List[str]:
    sources: List[str] = []
    for group in groups:
        for source in group or []:
            source = str(source or "").strip()
            if source and source not in sources:
                sources.append(source)
    return sources


def _section_sources(section_type: str, section_plan) -> tuple[List[str], List[str]]:
    plan_sources = list(getattr(section_plan, "content_sources", []) or [])
    if section_type == "introduction":
        fallback_sources = INTRODUCTION_SOURCES
    else:
        fallback_sources = BODY_SECTION_SOURCES.get(section_type, [])
    return plan_sources, list(fallback_sources)


def resolve_section_content(
    section_type: str,
    section_plan,
    metadata: PaperMetaData,
    content_brief: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Resolve writing inputs for a section from content_brief, then metadata."""
    direct = _brief_value(content_brief, section_type)
    if direct:
        return {section_type: direct}

    plan_sources, fallback_sources = _section_sources(section_type, section_plan)
    for source_group in (plan_sources, fallback_sources):
        resolved: Dict[str, str] = {}
        for source in source_group:
            if source == "references":
                continue
            value = _brief_value(content_brief, source)
            if value:
                resolved[source] = value
        if resolved:
            return resolved

    resolved = {}
    for source in _ordered_unique_sources(plan_sources, fallback_sources):
        if source == "references":
            continue
        value = getattr(metadata, source, None)
        if value:
            resolved[source] = str(value)
    if resolved:
        return resolved

    method = getattr(metadata, "method", "") or ""
    if method:
        return {"method": str(method)}
    idea = getattr(metadata, "idea_hypothesis", "") or ""
    if idea:
        return {"idea_hypothesis": str(idea)}
    return {}


def format_section_content_for_prompt(section_content: Dict[str, str]) -> str:
    parts = []
    for source, value in section_content.items():
        if value:
            label = source.replace("_", " ").title()
            parts.append(f"### {label}\n{value}")
    return "\n\n".join(parts)


def is_econ_finance_writing_context(
    section_type: str,
    style_guide: Optional[str],
) -> bool:
    style = str(style_guide or "").strip().lower().replace(" ", "-")
    return (
        section_type in ECON_FINANCE_SECTION_TYPES
        or any(hint in style for hint in ECON_FINANCE_STYLE_HINTS)
    )


def append_econ_finance_writing_rules(
    prompt: str,
    section_type: str,
    style_guide: Optional[str],
) -> str:
    if not is_econ_finance_writing_context(section_type, style_guide):
        return prompt
    return f"{prompt}\n\n{ECON_FINANCE_WRITING_RULES}"


async def generate_introduction_section(
    *,
    metadata: PaperMetaData,
    ref_pool: ReferencePool,
    section_plan,
    figures: Optional[List[FigureSpec]],
    tables: Optional[List[TableSpec]],
    code_context: Optional[Dict[str, Any]],
    research_context: Optional[Dict[str, Any]],
    prompt_traces: Optional[List[Dict[str, Any]]],
    memory: Optional[SessionMemory],
    evidence_dag,
    template_guide,
    exemplar_guidance: Optional[str],
    emitter,
    tools_config,
    retrieve_runtime_code_evidence_fn,
    format_research_context_for_prompt_fn,
    get_active_skills_fn,
    generate_section_decomposed_fn,
    content_brief: Optional[Dict[str, str]] = None,
    effective_style_guide: Optional[str] = None,
) -> SectionResult:
    style_guide = effective_style_guide or metadata.style_guide
    intro_content = resolve_section_content(
        "introduction",
        section_plan,
        metadata,
        content_brief,
    )
    intro_runtime_evidence = retrieve_runtime_code_evidence_fn(
        code_context=code_context,
        section_type="introduction",
        metadata=metadata,
        top_k=2,
    )
    intro_code_context = format_code_context_for_prompt(
        context=code_context,
        section_type="introduction",
        retrieved_evidence=intro_runtime_evidence,
        top_k=4,
    )
    intro_research_context = format_research_context_for_prompt_fn(
        research_context=research_context,
        section_type="introduction",
        evidence_dag=evidence_dag,
    )
    prompt = compile_introduction_prompt(
        paper_title=metadata.title,
        idea_hypothesis=(
            intro_content.get("introduction")
            or intro_content.get("idea_hypothesis")
            or metadata.idea_hypothesis
        ),
        method_summary=intro_content.get("method") or metadata.method,
        data_summary=intro_content.get("data") or metadata.data,
        experiments_summary=(
            intro_content.get("experiments")
            or intro_content.get("results")
            or metadata.experiments
        ),
        references=ref_pool.citable_refs("introduction"),
        style_guide=style_guide,
        section_plan=section_plan,
        figures=_figures_visible_to_section(figures, "introduction"),
        tables=tables,
        active_skills=get_active_skills_fn("introduction", style_guide),
        code_context=intro_code_context,
        research_context=intro_research_context,
        enable_structure_contract=bool(
            tools_config is None
            or getattr(tools_config, "writer_structure_contract_enabled", True)
        ),
        template_guide=template_guide,
        exemplar_guidance=exemplar_guidance or None,
    )
    prompt = append_econ_finance_writing_rules(prompt, "introduction", style_guide)
    append_prompt_trace(
        prompt_traces,
        section_type="introduction",
        prompt=prompt,
        code_context_used=bool(intro_code_context),
        research_context_used=bool(intro_research_context),
        runtime_evidence=intro_runtime_evidence,
    )

    writer_valid_keys = build_writer_valid_keys(section_plan, ref_pool)
    section_title = section_plan.section_title if section_plan else "Introduction"
    content = await generate_section_decomposed_fn(
        section_type="introduction",
        section_plan=section_plan,
        writer_valid_keys=writer_valid_keys,
        section_title_str=section_title,
        evidence_dag=evidence_dag,
        memory=memory,
        emitter=emitter,
        template_guide=template_guide,
        exemplar_guidance=exemplar_guidance,
    )
    if not content.strip():
        return SectionResult(
            section_type="introduction",
            section_title=section_title,
            status="error",
            error="Writer returned empty introduction content",
        )
    return build_section_result(
        section_type="introduction",
        section_title=section_title,
        content=content,
    )


async def generate_body_section(
    *,
    section_type: str,
    metadata: PaperMetaData,
    intro_context: str,
    contributions: List[str],
    ref_pool: ReferencePool,
    section_plan,
    figures: Optional[List[FigureSpec]],
    tables: Optional[List[TableSpec]],
    converted_tables: Optional[Dict[str, str]],
    code_context: Optional[Dict[str, Any]],
    research_context: Optional[Dict[str, Any]],
    prompt_traces: Optional[List[Dict[str, Any]]],
    memory: Optional[SessionMemory],
    evidence_dag,
    template_guide,
    emitter,
    exemplar_guidance: Optional[str],
    tools_config,
    retrieve_runtime_code_evidence_fn,
    format_research_context_for_prompt_fn,
    get_active_skills_fn,
    generate_section_decomposed_fn,
    content_brief: Optional[Dict[str, str]] = None,
    effective_style_guide: Optional[str] = None,
) -> SectionResult:
    style_guide = effective_style_guide or metadata.style_guide
    section_title = (
        section_plan.section_title
        if section_plan and section_plan.section_title
        else section_type.replace("_", " ").title()
    )
    section_content = resolve_section_content(
        section_type,
        section_plan,
        metadata,
        content_brief,
    )
    metadata_content = format_section_content_for_prompt(section_content)

    memory_context = memory.get_writing_context(section_type) if memory else ""
    runtime_evidence = retrieve_runtime_code_evidence_fn(
        code_context=code_context,
        section_type=section_type,
        metadata=metadata,
        contributions=contributions,
        top_k=3,
    )
    section_code_context = format_code_context_for_prompt(
        context=code_context,
        section_type=section_type,
        retrieved_evidence=runtime_evidence,
        top_k=6,
    )
    section_research_context = format_research_context_for_prompt_fn(
        research_context=research_context,
        section_type=section_type,
        evidence_dag=evidence_dag,
    )
    prompt = compile_body_section_prompt(
        section_type=section_type,
        metadata_content=metadata_content,
        intro_context=intro_context,
        contributions=contributions,
        references=ref_pool.citable_refs(section_type),
        style_guide=style_guide,
        section_plan=section_plan,
        figures=_figures_visible_to_section(figures, section_type),
        tables=tables,
        converted_tables=converted_tables,
        active_skills=get_active_skills_fn(section_type, style_guide),
        memory_context=memory_context,
        code_context=section_code_context,
        research_context=section_research_context,
        enable_structure_contract=bool(
            tools_config is None
            or getattr(tools_config, "writer_structure_contract_enabled", True)
        ),
        template_guide=template_guide,
        exemplar_guidance=exemplar_guidance or None,
    )
    prompt = append_econ_finance_writing_rules(prompt, section_type, style_guide)
    append_prompt_trace(
        prompt_traces,
        section_type=section_type,
        prompt=prompt,
        code_context_used=bool(section_code_context),
        research_context_used=bool(section_research_context),
        runtime_evidence=runtime_evidence,
    )

    writer_valid_keys = build_writer_valid_keys(section_plan, ref_pool)
    content = await generate_section_decomposed_fn(
        section_type=section_type,
        section_plan=section_plan,
        writer_valid_keys=writer_valid_keys,
        section_title_str=section_title,
        figures=_figures_visible_to_section(figures, section_type),
        evidence_dag=evidence_dag,
        memory=memory,
        emitter=emitter,
        template_guide=template_guide,
        exemplar_guidance=exemplar_guidance,
    )
    final_title = section_plan.section_title if section_plan and section_plan.section_title else {
        "related_work": "Related Work",
        "method": "Methodology",
        "experiment": "Experiments",
        "result": "Results",
        "discussion": "Discussion",
    }.get(section_type, section_type.title())
    return build_section_result(
        section_type=section_type,
        section_title=final_title,
        content=content,
    )


async def generate_synthesis_section(
    *,
    section_type: str,
    paper_title: str,
    prior_sections: Dict[str, str],
    contributions: List[str],
    style_guide: Optional[str],
    section_plan,
    prompt_traces: Optional[List[Dict[str, Any]]],
    memory: Optional[SessionMemory],
    template_guide,
    exemplar_guidance: Optional[str],
    writer,
    get_active_skills_fn,
) -> SectionResult:
    memory_context = memory.get_cross_section_summary() if memory else ""
    prompt = compile_synthesis_prompt(
        section_type=section_type,
        paper_title=paper_title,
        prior_sections=prior_sections,
        key_contributions=contributions,
        style_guide=style_guide,
        section_plan=section_plan,
        active_skills=get_active_skills_fn(section_type, style_guide),
        memory_context=memory_context,
        template_guide=template_guide,
        exemplar_guidance=exemplar_guidance or None,
    )
    append_prompt_trace(
        prompt_traces,
        section_type=section_type,
        prompt=prompt,
        code_context_used=False,
        research_context_used=False,
        runtime_evidence=[],
    )
    core_result = await writer.generate_core_content(
        core_prompt=prompt,
        section_type=section_type,
        paragraph_index=0,
    )
    content = sanitize_synthesis_content(section_type, core_result.raw_latex)
    final_title = (
        section_plan.section_title
        if section_plan and section_plan.section_title
        else ("Abstract" if section_type == "abstract" else "Conclusion")
    )
    return build_section_result(
        section_type=section_type,
        section_title=final_title,
        content=content,
    )
