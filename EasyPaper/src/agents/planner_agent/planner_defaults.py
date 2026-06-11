"""
Default-plan and section-metadata helpers for PlannerAgent.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .models import DEFAULT_EMPIRICAL_SECTIONS, PaperPlan, PaperType, SectionPlan

ECON_FINANCE_REQUIRED_SECTION_IDS = [
    "introduction",
    "data",
    "empirical_strategy",
    "results",
    "robustness",
    "conclusion",
]

ECON_FINANCE_OPTIONAL_SECTION_IDS = [
    "abstract",
    "institutional_background",
    "theory_or_model",
    "mechanisms",
    "heterogeneity",
    "appendix",
    "references",
]

ECON_FINANCE_CANONICAL_SECTION_IDS = [
    "abstract",
    "introduction",
    "institutional_background",
    "theory_or_model",
    "data",
    "empirical_strategy",
    "results",
    "robustness",
    "mechanisms",
    "heterogeneity",
    "conclusion",
    "appendix",
    "references",
]

ECON_FINANCE_SECTION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "abstract": {
        "title": "Abstract",
        "content_sources": ["idea_hypothesis", "empirical_strategy", "results"],
        "dependencies": ["introduction", "results", "conclusion"],
    },
    "introduction": {
        "title": "Introduction",
        "content_sources": ["introduction", "idea_hypothesis"],
        "dependencies": [],
    },
    "institutional_background": {
        "title": "Institutional Background",
        "content_sources": ["institutional_background", "data"],
        "dependencies": ["introduction"],
    },
    "theory_or_model": {
        "title": "Theory or Model",
        "content_sources": ["theory_or_model", "mechanisms", "idea_hypothesis"],
        "dependencies": ["introduction"],
    },
    "data": {
        "title": "Data",
        "content_sources": ["data"],
        "dependencies": ["introduction"],
    },
    "empirical_strategy": {
        "title": "Empirical Strategy",
        "content_sources": ["empirical_strategy", "method", "data"],
        "dependencies": ["data"],
    },
    "results": {
        "title": "Results",
        "content_sources": ["results", "experiments", "data"],
        "dependencies": ["empirical_strategy"],
    },
    "robustness": {
        "title": "Robustness",
        "content_sources": ["robustness", "results", "experiments"],
        "dependencies": ["results"],
    },
    "mechanisms": {
        "title": "Mechanisms",
        "content_sources": ["mechanisms", "results", "theory_or_model"],
        "dependencies": ["results"],
    },
    "heterogeneity": {
        "title": "Heterogeneity",
        "content_sources": ["heterogeneity", "results", "data"],
        "dependencies": ["results"],
    },
    "conclusion": {
        "title": "Conclusion",
        "content_sources": ["conclusion", "idea_hypothesis", "results"],
        "dependencies": ["results", "robustness"],
    },
    "appendix": {
        "title": "Appendix",
        "content_sources": ["robustness", "data", "empirical_strategy"],
        "dependencies": ["conclusion"],
    },
    "references": {
        "title": "References",
        "content_sources": ["references"],
        "dependencies": ["conclusion"],
    },
}

ECON_FINANCE_SECTION_PARAGRAPH_SKELETONS: Dict[str, List[str]] = {
    "introduction": [
        "Motivate the economics or finance question and its stakes.",
        "Summarize the empirical setting, variation, and main findings.",
        "State the paper's contribution relative to the target literature.",
    ],
    "data": [
        "Describe the data sources, sample construction, and unit of observation.",
        "Define the key outcome, treatment, and control variables.",
        "Report coverage, summary statistics, and measurement limitations.",
    ],
    "empirical_strategy": [
        "Identification design and estimating equation.",
        "Treatment/control construction and identifying assumptions.",
        "Standard errors, fixed effects, and threats to identification.",
    ],
    "results": [
        "Present the main estimates and economic magnitudes.",
        "Interpret coefficient patterns against the paper's hypotheses.",
        "Connect figures and tables to the central causal or descriptive claims.",
    ],
    "robustness": [
        "Probe alternative specifications and sample definitions.",
        "Report placebo, falsification, or sensitivity checks.",
        "Summarize which findings are stable and where uncertainty remains.",
    ],
    "conclusion": [
        "Synthesize the main findings and their contribution.",
        "Discuss implications for theory, policy, or financial practice.",
        "Close with limitations and high-value future work.",
    ],
    "institutional_background": [
        "Explain the institutional setting needed to understand the variation.",
        "Identify rules, actors, or market features that shape interpretation.",
    ],
    "theory_or_model": [
        "Lay out the conceptual mechanism or model primitives.",
        "Derive the predictions that guide the empirical analysis.",
    ],
    "mechanisms": [
        "Test channels that connect the treatment to the main outcome.",
        "Compare mechanism evidence with the paper's theoretical predictions.",
    ],
    "heterogeneity": [
        "Estimate effects across economically meaningful subgroups.",
        "Interpret heterogeneity in light of the proposed mechanism.",
    ],
}


def extract_reference_keys(references: List[str]) -> List[str]:
    keys = []
    for ref in references:
        match = re.search(r"@\w+\{([^,]+)", ref)
        if match:
            keys.append(match.group(1).strip())
    return keys


def get_section_title(section_type: str) -> str:
    titles = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "related_work": "Related Work",
        "method": "Method",
        "experiment": "Experiments",
        "result": "Results",
        "institutional_background": "Institutional Background",
        "theory_or_model": "Theory or Model",
        "data": "Data",
        "empirical_strategy": "Empirical Strategy",
        "results": "Results",
        "robustness": "Robustness",
        "mechanisms": "Mechanisms",
        "heterogeneity": "Heterogeneity",
        "appendix": "Appendix",
        "references": "References",
        "discussion": "Discussion",
        "conclusion": "Conclusion",
    }
    return titles.get(section_type, section_type.replace("_", " ").title())


def get_default_sources(section_type: str) -> List[str]:
    mapping = {
        "introduction": ["idea_hypothesis", "method"],
        "related_work": ["idea_hypothesis"],
        "method": ["method"],
        "experiment": ["experiments", "data"],
        "result": ["experiments"],
        "institutional_background": ["institutional_background", "data"],
        "theory_or_model": ["theory_or_model", "mechanisms", "idea_hypothesis"],
        "data": ["data"],
        "empirical_strategy": ["empirical_strategy", "method", "data"],
        "results": ["results", "experiments", "data"],
        "robustness": ["robustness", "results", "experiments"],
        "mechanisms": ["mechanisms", "results", "theory_or_model"],
        "heterogeneity": ["heterogeneity", "results", "data"],
        "appendix": ["robustness", "data", "empirical_strategy"],
        "references": ["references"],
        "discussion": ["experiments", "method"],
        "conclusion": ["idea_hypothesis", "experiments"],
        "abstract": ["idea_hypothesis", "method", "experiments"],
    }
    return mapping.get(section_type, [])


def get_dependencies(section_type: str) -> List[str]:
    deps = {
        "related_work": ["introduction"],
        "method": ["introduction"],
        "experiment": ["method"],
        "result": ["experiment"],
        "institutional_background": ["introduction"],
        "theory_or_model": ["introduction"],
        "data": ["introduction"],
        "empirical_strategy": ["data"],
        "results": ["empirical_strategy"],
        "robustness": ["results"],
        "mechanisms": ["results"],
        "heterogeneity": ["results"],
        "appendix": ["conclusion"],
        "references": ["conclusion"],
        "discussion": ["result"],
        "conclusion": ["introduction", "result"],
        "abstract": ["introduction", "conclusion"],
    }
    return deps.get(section_type, [])


def get_econ_finance_section_default(section_type: str) -> Dict[str, Any]:
    return dict(ECON_FINANCE_SECTION_DEFAULTS.get(section_type, {}))


def create_default_plan(
    request: Any,
    total_words: int,
    words_per_sentence: int,
    generate_default_paragraphs_fn,
) -> PaperPlan:
    total_sentences = total_words // words_per_sentence
    n_sections = len(DEFAULT_EMPIRICAL_SECTIONS)
    per_section_sents = max(3, total_sentences // max(1, n_sections))

    sections = []
    for order, section_type in enumerate(DEFAULT_EMPIRICAL_SECTIONS):
        paragraphs = generate_default_paragraphs_fn(section_type, per_section_sents, {})
        sections.append(
            SectionPlan(
                section_type=section_type,
                section_title=get_section_title(section_type),
                paragraphs=paragraphs,
                content_sources=get_default_sources(section_type),
                depends_on=get_dependencies(section_type),
                order=order,
            )
        )

    return PaperPlan(
        title=request.title,
        paper_type=PaperType.EMPIRICAL,
        sections=sections,
        contributions=[f"We propose {request.title}"],
    )
