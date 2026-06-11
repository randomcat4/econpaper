"""
Section and subsection planning helpers for PlannerAgent.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .models import (
    PaperPlan,
    ParagraphPlan,
    ParagraphPresentation,
    SectionPlan,
    SubSectionPlan,
)
from .planner_defaults import (
    ECON_FINANCE_SECTION_DEFAULTS,
    ECON_FINANCE_SECTION_PARAGRAPH_SKELETONS,
)

STEP4_STRUCTURE_SYSTEM = (
    "You are an expert academic paper planner. "
    "Decide whether a section needs subsections based on its mission and content scope. "
    "Output ONLY a JSON object. No markdown, no explanation."
)

STEP5A_SYSTEM = (
    "You are an expert academic paper planner. "
    "Generate a paragraph-level plan for a paper section. "
    "Output ONLY a JSON object. No markdown, no explanation."
)

STEP5B_SYSTEM = (
    "You are an expert academic paper planner. "
    "Generate a paragraph-level plan for one subsection within a paper section. "
    "Output ONLY a JSON object. No markdown, no explanation."
)

_REQUIRED_SECTION_ALIASES = {
    "abstract": "abstract",
    "introduction": "introduction",
    "data": "data",
    "empirical strategy": "empirical_strategy",
    "identification strategy": "empirical_strategy",
    "empirical design": "empirical_strategy",
    "results": "results",
    "main results": "results",
    "robustness": "robustness",
    "robustness checks": "robustness",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "institutional background": "institutional_background",
    "theory": "theory_or_model",
    "model": "theory_or_model",
    "theory or model": "theory_or_model",
    "mechanisms": "mechanisms",
    "heterogeneity": "heterogeneity",
    "appendix": "appendix",
    "references": "references",
}


def _required_section_lookup_key(name: str) -> str:
    return " ".join(
        re.sub(r"[_\-]+", " ", str(name or "").strip().lower()).split()
    )


def normalize_required_section_name(name: str) -> str:
    """Normalize venue-required section display names to canonical section ids."""
    key = _required_section_lookup_key(name)
    if key in _REQUIRED_SECTION_ALIASES:
        return _REQUIRED_SECTION_ALIASES[key]
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


def normalize_required_section_names(names: Any) -> List[str]:
    """Normalize and deduplicate required section names while preserving order."""
    if not isinstance(names, list):
        return []

    normalized: List[str] = []
    seen: set[str] = set()
    for name in names:
        section_id = normalize_required_section_name(str(name))
        if section_id and section_id not in seen:
            normalized.append(section_id)
            seen.add(section_id)
    return normalized


def normalize_constraints_required_sections(constraints: Any) -> List[str]:
    """Normalize required_sections on a constraints object or dict in place."""
    if not constraints:
        return []

    if isinstance(constraints, dict):
        normalized = normalize_required_section_names(
            constraints.get("required_sections", [])
        )
        constraints["required_sections"] = normalized
        return normalized

    normalized = normalize_required_section_names(
        getattr(constraints, "required_sections", [])
    )
    if hasattr(constraints, "required_sections"):
        constraints.required_sections = normalized
    return normalized


def _required_section_base(section_type: str) -> str:
    section_type = re.sub(r"_\d+$", "", str(section_type or "").strip().lower())
    return normalize_required_section_name(section_type)


def _new_required_section(section_id: str) -> SectionPlan:
    defaults = dict(ECON_FINANCE_SECTION_DEFAULTS.get(section_id, {}))
    title = defaults.get("title") or section_id.replace("_", " ").title()
    skeleton = ECON_FINANCE_SECTION_PARAGRAPH_SKELETONS.get(section_id) or [
        f"Develop the {title} section for the target venue.",
        f"Connect {title} to the paper's main contribution.",
    ]
    paragraphs = [
        ParagraphPlan(
            key_point=key_point,
            approx_sentences=4,
            role="topic" if idx == 0 else "evidence",
        )
        for idx, key_point in enumerate(skeleton[:4])
    ]

    return SectionPlan(
        section_type=section_id,
        section_title=title,
        mission=f"Cover the {title} material required by the target venue.",
        key_content=list(skeleton[:4]),
        paragraphs=paragraphs,
        content_sources=list(defaults.get("content_sources", [])),
        depends_on=list(defaults.get("dependencies", [])),
    )


def enforce_required_sections(
    plan: PaperPlan,
    required_sections: List[str],
) -> PaperPlan:
    """Ensure a paper plan contains required venue sections in canonical order."""
    required = normalize_required_section_names(required_sections)
    if not required:
        return plan

    sections = list(getattr(plan, "sections", []) or [])
    existing_by_required: Dict[str, SectionPlan] = {}
    used_indices: set[int] = set()
    abstract: SectionPlan | None = None

    for idx, section in enumerate(sections):
        base = _required_section_base(section.section_type)
        if base == "abstract" and abstract is None:
            abstract = section
            used_indices.add(idx)
            continue
        if base in required and base not in existing_by_required:
            section.section_type = base
            if not section.section_title:
                section.section_title = (
                    ECON_FINANCE_SECTION_DEFAULTS.get(base, {}).get("title")
                    or base.replace("_", " ").title()
                )
            existing_by_required[base] = section
            used_indices.add(idx)

    ordered: List[SectionPlan] = []
    if abstract is not None:
        ordered.append(abstract)

    for section_id in required:
        ordered.append(existing_by_required.get(section_id) or _new_required_section(section_id))

    required_set = set(required)
    for idx, section in enumerate(sections):
        if idx in used_indices:
            continue
        base = _required_section_base(section.section_type)
        if base in required_set or base == "abstract":
            continue
        ordered.append(section)

    for order, section in enumerate(ordered):
        section.order = order
    plan.sections = ordered
    return plan


def _is_intro_like_section(section: SectionPlan) -> bool:
    section_type = str(getattr(section, "section_type", "") or "").strip().lower()
    section_title = str(getattr(section, "section_title", "") or "").strip().lower()
    type_base = section_type.split("_", 1)[0]
    order = getattr(section, "order", None)
    opening_alias_title = section_title in {
        "background",
        "motivation",
        "overview",
        "background and motivation",
        "motivation and background",
        "problem motivation",
        "problem and motivation",
    }
    return (
        section_type in {"introduction", "intro"}
        or type_base in {"introduction", "intro"}
        or section_title in {"introduction", "intro"}
        or "introduction" in section_title
        or (order in {0, 1, None} and opening_alias_title)
    )


def parse_paragraph_plans(raw_paragraphs: List[Dict[str, Any]]) -> List[ParagraphPlan]:
    paragraphs = []
    for raw in raw_paragraphs:
        if not isinstance(raw, dict):
            continue
        presentation_raw = raw.get("presentation", {})
        presentation = (
            ParagraphPresentation(**presentation_raw)
            if isinstance(presentation_raw, dict)
            else ParagraphPresentation()
        )
        paragraphs.append(
            ParagraphPlan(
                key_point=raw.get("key_point", ""),
                supporting_points=raw.get("supporting_points", []),
                approx_sentences=raw.get("approx_sentences", 5),
                role=raw.get("role", "evidence"),
                presentation=presentation,
                references_to_cite=raw.get("references_to_cite", []),
                figures_to_reference=raw.get("figures_to_reference", []),
                figure_usages=raw.get("figure_usages", []),
                tables_to_reference=raw.get("tables_to_reference", []),
                cluster_index=raw.get("cluster_index"),
            )
        )
    return paragraphs


async def decide_section_structure(
    *,
    llm_json_call_fn,
    section: SectionPlan,
    paper_type: str,
    contributions: List[str],
    venue: str,
    word_budget: int,
    prior_sections_summary: str,
) -> Dict[str, Any]:
    figures_str = ", ".join(f.figure_id for f in section.figures) if section.figures else "None"
    tables_str = ", ".join(t.table_id for t in section.tables) if section.tables else "None"
    intro_policy = ""
    if _is_intro_like_section(section):
        intro_policy = """
INTRODUCTION STRUCTURE POLICY:
- Treat Introduction and intro-like opening sections as continuous narrative prose.
- Set "needs_subsections": false for this section.
- Do NOT create subsection groups for Introduction/Intro-style sections.
- Cover context, gap, approach, and contributions as cohesive paragraphs, not as subsection headings.
"""

    prompt = f"""Decide whether this section needs subsections:

**Section**: {section.section_title} ({section.section_type})
**Mission**: {section.mission}
**Key content points**: {json.dumps(section.key_content)}
**Paper type**: {paper_type}
**Contributions**: {json.dumps(contributions)}
**Venue**: {venue}
**Word budget**: ~{word_budget} words
**Assigned figures**: {figures_str}
**Assigned tables**: {tables_str}
**Prior sections structure**: {prior_sections_summary or "None (this is the first body section)"}
{intro_policy}

Output JSON:
{{
  "needs_subsections": true/false,
  "reasoning": "Why subsections are/aren't needed",
  "subsections": [
    {{
      "title": "Subsection Title",
      "mission": "What this subsection must accomplish",
      "key_themes": ["theme1", "theme2"],
      "depends_on": ["Title of predecessor subsection if any"],
      "approx_paragraphs": 3
    }}
  ],
  "cross_subsection_transitions": ["Transition guidance between sub_i and sub_i+1"]
}}

If needs_subsections is false, omit subsections and cross_subsection_transitions.
Only recommend subsections when the content is genuinely complex enough to warrant them (typically 3+ distinct themes or multi-stage processes).
Output valid JSON only."""

    return await llm_json_call_fn(STEP4_STRUCTURE_SYSTEM, prompt, f"step4_{section.section_type}")


async def plan_flat_paragraphs(
    *,
    llm_json_call_fn,
    parse_paragraph_plans_fn,
    section: SectionPlan,
    word_budget: int,
    reference_keys: List[str],
    prior_key_points: str,
    contributions: List[str],
    venue: str = "DEFAULT",
) -> List[ParagraphPlan]:
    figures_str = ", ".join(f.figure_id for f in section.figures) if section.figures else "None"
    tables_str = ", ".join(t.table_id for t in section.tables) if section.tables else "None"

    is_ai_venue = any(v in venue.upper() for v in ["CVPR", "NEURIPS", "ICML", "ICLR", "AAAI", "NeurIPS"])
    narrative_guidance = ""
    is_intro_like = _is_intro_like_section(section)
    if is_ai_venue and is_intro_like:
        narrative_guidance = """
VENUE-SPECIFIC STRUCTURE (AI-targeted venue):
Introduction MUST follow this 4-paragraph narrative arc:
1. Context (topic role): Establish the general research area and its importance.
2. Gap/Limitation (evidence/analysis role): Identify limitations in prior work.
3. Our Approach (evidence role): Introduce your method/solution.
4. Contribution summary or roadmap (conclusion role): summarize what the paper
   adds and connect to the remaining sections.
Do NOT plan subsections for this section; keep the arc as continuous prose paragraphs.
"""
    elif is_ai_venue:
        narrative_guidance = """
VENUE-SPECIFIC GUIDANCE (AI-targeted venue):
When generating paragraphs, ensure:
- Topic sentences clearly state the main point.
- Evidence paragraphs cite specific prior work with limitations.
- Transitions smoothly connect to next content.
"""

    prompt = f"""Generate a paragraph plan for this section:

**Section**: {section.section_title} ({section.section_type})
**Mission**: {section.mission}
**Key content points**: {json.dumps(section.key_content)}
**Word budget**: ~{word_budget} words
**Assigned figures**: {figures_str}
**Assigned tables**: {tables_str}
**Available references**: {", ".join(reference_keys[:20]) if reference_keys else "None"}
**Prior sections key points**: {prior_key_points or "None (first section)"}
**Paper contributions**: {json.dumps(contributions) if contributions else "None"}
{narrative_guidance}
Output JSON:
{{
  "paragraphs": [
    {{
      "key_point": "Main point of this paragraph",
      "supporting_points": ["detail 1", "detail 2"],
      "approx_sentences": 4,
      "role": "topic|evidence|analysis|transition|conclusion",
      "presentation": {{
        "mode": "prose",
        "list_label": "",
        "list_items": [],
        "closing_guidance": ""
      }},
      "references_to_cite": ["ref_key1"],
      "figures_to_reference": ["fig1"],
      "tables_to_reference": ["tab1"]
    }}
  ]
}}

Guidelines:
- Each paragraph should have a single clear key_point.
- Order paragraphs logically to fulfill the section mission.
- Assign figures/tables to the most relevant paragraph.
- approx_sentences: typically 3-6 for body paragraphs.
- Use presentation.mode="prose" for ordinary prose paragraphs.
- Use presentation.mode="prose_with_list" only when selected key points inside
  the paragraph should be rendered as a LaTeX itemized list. Keep prose framing
  in key_point/supporting_points and put the itemized points in presentation.list_items.
- When a paragraph is explicitly a contribution summary and selected contribution
  points should be listed, use presentation.mode="prose_with_list" and make the
  itemize block the terminal rhetorical unit. Put roadmap/closing prose before the
  list or in a separate paragraph, not after the list.
Output valid JSON only."""

    data = await llm_json_call_fn(STEP5A_SYSTEM, prompt, f"step5a_{section.section_type}")
    paragraphs = parse_paragraph_plans_fn(data.get("paragraphs", []))
    if not paragraphs:
        paragraphs = [ParagraphPlan(
            key_point=f"Content for {section.section_title}",
            approx_sentences=max(3, word_budget // 20),
        )]
    return paragraphs


async def plan_subsection_paragraphs(
    *,
    llm_json_call_fn,
    parse_paragraph_plans_fn,
    section: SectionPlan,
    subsection_structure: Dict[str, Any],
    reference_keys: List[str],
    contributions: List[str],
) -> List[SubSectionPlan]:
    raw_subs = subsection_structure.get("subsections", [])
    transitions = subsection_structure.get("cross_subsection_transitions", [])
    all_titles = [s.get("title", f"Subsection {i+1}") for i, s in enumerate(raw_subs)]

    cumulative_key_points: List[str] = []
    result: List[SubSectionPlan] = []

    for i, sub_info in enumerate(raw_subs):
        sub_title = sub_info.get("title", f"Subsection {i+1}")
        sub_mission = sub_info.get("mission", "")
        sub_key_themes = sub_info.get("key_themes", [])
        sub_depends_on = sub_info.get("depends_on", [])
        sub_approx_paras = sub_info.get("approx_paragraphs", 2)
        transition = transitions[i - 1] if i > 0 and i - 1 < len(transitions) else ""

        cumulative_str = "\n".join(f"- {kp}" for kp in cumulative_key_points) if cumulative_key_points else "None (this is the first subsection)"
        figures_str = ", ".join(f.figure_id for f in section.figures) if section.figures else "None"
        tables_str = ", ".join(t.table_id for t in section.tables) if section.tables else "None"

        prompt = f"""Generate a paragraph plan for this subsection:

**Parent section**: {section.section_title} ({section.section_type})
**Section mission**: {section.mission}
**Full subsection structure**: {json.dumps(all_titles)}

**Current subsection**: {sub_title}
**Subsection mission**: {sub_mission}
**Key themes**: {json.dumps(sub_key_themes)}
**Depends on**: {json.dumps(sub_depends_on)}
**Target paragraphs**: ~{sub_approx_paras}
**Assigned figures**: {figures_str}
**Assigned tables**: {tables_str}
**Available references**: {", ".join(reference_keys[:15]) if reference_keys else "None"}

**Transition from previous subsection**: {transition or "N/A (first subsection)"}
**Key points from previous subsections**:
{cumulative_str}
**Paper contributions**: {json.dumps(contributions) if contributions else "None"}

Output JSON:
{{
  "paragraphs": [
    {{
      "key_point": "Main point of this paragraph",
      "supporting_points": ["detail 1", "detail 2"],
      "approx_sentences": 4,
      "role": "topic|evidence|analysis|transition|conclusion",
      "presentation": {{
        "mode": "prose",
        "list_label": "",
        "list_items": [],
        "closing_guidance": ""
      }},
      "references_to_cite": ["ref_key1"]
    }}
  ],
  "subsection_key_points": ["1-2 sentence summary of what this subsection covers"]
}}

Guidelines:
- Each paragraph should have a single clear key_point.
- Build on previous subsections' key_points for narrative continuity.
- subsection_key_points will be passed to subsequent subsections as context.
- When a paragraph is explicitly a contribution summary and selected contribution
  points should be listed, use presentation.mode="prose_with_list" and make the
  itemize block terminal. Roadmap/closing prose belongs before the list or in a
  separate paragraph.
Output valid JSON only."""

        data = await llm_json_call_fn(STEP5B_SYSTEM, prompt, f"step5b_{section.section_type}_{i}")
        paragraphs = parse_paragraph_plans_fn(data.get("paragraphs", []))
        if not paragraphs:
            paragraphs = [ParagraphPlan(
                key_point=f"Content for {sub_title}",
                approx_sentences=max(3, sub_approx_paras * 4),
            )]

        new_key_points = data.get("subsection_key_points", [])
        if isinstance(new_key_points, list):
            cumulative_key_points.extend(new_key_points)
        elif isinstance(new_key_points, str):
            cumulative_key_points.append(new_key_points)

        result.append(
            SubSectionPlan(
                title=sub_title,
                mission=sub_mission,
                key_themes=sub_key_themes if isinstance(sub_key_themes, list) else [],
                depends_on=sub_depends_on if isinstance(sub_depends_on, list) else [],
                transition_from_previous=transition,
                paragraphs=paragraphs,
            )
        )

    return result


def split_into_subsections(
    section: SectionPlan,
    topic_clusters: List[str],
) -> SectionPlan:
    if not section.paragraphs:
        return section

    clusters: Dict[int, List[ParagraphPlan]] = {}
    unclustered: List[ParagraphPlan] = []
    for para in section.paragraphs:
        if para.cluster_index is not None:
            idx = para.cluster_index
            clusters.setdefault(idx, []).append(para)
        else:
            unclustered.append(para)

    if len(clusters) <= 1 and not unclustered:
        return section

    subsections: List[SubSectionPlan] = []
    for cluster_idx in sorted(clusters.keys()):
        paras = clusters[cluster_idx]
        title = topic_clusters[cluster_idx] if cluster_idx < len(topic_clusters) else f"Theme {cluster_idx + 1}"
        subsections.append(SubSectionPlan(title=title, paragraphs=paras))

    if unclustered:
        subsections.append(SubSectionPlan(title="General", paragraphs=unclustered))

    return SectionPlan(
        section_type=section.section_type,
        section_title=section.section_title,
        paragraphs=[],
        subsections=subsections,
        figures=section.figures,
        tables=section.tables,
        figures_to_reference=section.figures_to_reference,
        tables_to_reference=section.tables_to_reference,
        content_sources=section.content_sources,
        depends_on=section.depends_on,
        citation_budget=section.citation_budget,
        topic_clusters=section.topic_clusters,
        transition_intents=section.transition_intents,
        sectioning_recommended=section.sectioning_recommended,
        code_focus=section.code_focus,
        writing_guidance=section.writing_guidance,
        order=section.order,
    )


def sanitize_conclusion_like_subsections(section: SectionPlan) -> SectionPlan:
    """
    Prevent body sections from carrying their own contribution-list conclusion.

    Conclusions are generated by the dedicated synthesis section. Discussion
    sections may discuss limitations and implications, but should not contain a
    separate ``Conclusion`` subsection with bullet-point contributions.
    """
    if not section.subsections:
        return section

    cleaned: List[SubSectionPlan] = []
    for sub in section.subsections:
        title = (sub.title or "").strip().lower()
        if section.section_type != "conclusion" and title == "conclusion":
            for paragraph in sub.paragraphs:
                paragraph.presentation.mode = "prose"
                paragraph.presentation.list_label = ""
                paragraph.presentation.list_items = []
            if section.section_type == "discussion":
                continue
        if "conclusion" in title:
            for paragraph in sub.paragraphs:
                paragraph.presentation.mode = "prose"
                paragraph.presentation.list_label = ""
                paragraph.presentation.list_items = []
        cleaned.append(sub)

    section.subsections = cleaned
    if section.section_type == "discussion" and "conclusion" in (section.section_title or "").lower():
        section.section_title = "Discussion"
    return section


def collapse_singleton_subsections(section: SectionPlan) -> SectionPlan:
    """
    Avoid producing a section with exactly one subsection.

    A single child heading does not create useful hierarchy; it only repeats the
    parent section boundary. Keep the paragraph plan, but promote it to the
    section body so final LaTeX renders as ordinary section prose.
    """
    if len(section.subsections or []) != 1:
        return section

    only_subsection = section.subsections[0]
    section.paragraphs = [*section.paragraphs, *only_subsection.paragraphs]
    section.subsections = []
    section.sectioning_recommended = False
    return section


def enforce_section_structure_contracts(section: SectionPlan) -> SectionPlan:
    """Apply deterministic section-shape invariants after LLM planning edits."""
    section = sanitize_conclusion_like_subsections(section)
    section = collapse_singleton_subsections(section)
    section.sectioning_recommended = bool(section.subsections)
    return section
