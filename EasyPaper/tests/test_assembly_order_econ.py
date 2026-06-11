"""Tests for assembling papers with planned econ/finance section order."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from src.agents.metadata_agent.assembly_helper import assemble_paper


def _assemble(
    sections: Dict[str, str],
    section_order: Optional[List[str]] = None,
    section_titles: Optional[Dict[str, str]] = None,
) -> str:
    return assemble_paper(
        title="Econ Paper",
        sections=sections,
        references=[],
        valid_citation_keys=set(),
        escape_latex_fn=lambda text: text,
        fix_latex_references_fn=lambda text: text,
        validate_and_fix_citations_fn=lambda content, *_args, **_kwargs: (
            content,
            [],
            [],
        ),
        section_order=section_order,
        section_titles=section_titles,
    )


def _section_titles(latex: str) -> List[str]:
    return re.findall(r"\\section\{([^}]*)\}", latex)


def test_assemble_paper_uses_planned_econ_section_order_and_titles() -> None:
    latex = _assemble(
        {
            "abstract": "Abstract.",
            "introduction": "Intro.",
            "data": "Data.",
            "empirical_strategy": "Strategy.",
            "results": "Results.",
            "robustness": "Robustness.",
            "conclusion": "Conclusion.",
        },
        section_order=[
            "introduction",
            "data",
            "empirical_strategy",
            "results",
            "robustness",
            "conclusion",
        ],
        section_titles={
            "empirical_strategy": "Empirical Strategy",
            "results": "Results",
            "robustness": "Robustness",
        },
    )

    assert _section_titles(latex) == [
        "Introduction",
        "Data",
        "Empirical Strategy",
        "Results",
        "Robustness",
        "Conclusion",
    ]


def test_assemble_paper_does_not_append_legacy_experiment_when_plan_omits_it() -> None:
    latex = _assemble(
        {
            "introduction": "Intro.",
            "data": "Data.",
            "empirical_strategy": "Strategy.",
            "results": "Results.",
            "robustness": "Robustness.",
            "experiment": "Legacy experiment section should not be included.",
            "conclusion": "Conclusion.",
        },
        section_order=[
            "introduction",
            "data",
            "empirical_strategy",
            "results",
            "robustness",
            "conclusion",
        ],
    )

    assert "Experiments" not in _section_titles(latex)
    assert "Legacy experiment section should not be included." not in latex


def test_assemble_paper_without_section_order_preserves_legacy_order() -> None:
    latex = _assemble(
        {
            "experiment": "Experiment.",
            "introduction": "Intro.",
            "method": "Method.",
            "conclusion": "Conclusion.",
        }
    )

    assert _section_titles(latex) == [
        "Introduction",
        "Methodology",
        "Experiments",
        "Conclusion",
    ]


def test_metadata_agent_assemble_wrapper_accepts_planned_order_and_titles() -> None:
    from src.agents.metadata_agent.metadata_agent import MetaDataAgent

    agent = MetaDataAgent.__new__(MetaDataAgent)
    latex = agent._assemble_paper(
        title="Wrapper Paper",
        sections={
            "experiment": "Legacy experiment.",
            "data": "Data body.",
            "empirical_strategy": "Strategy body.",
            "conclusion": "Conclusion body.",
        },
        references=[],
        valid_citation_keys=set(),
        section_order=["data", "empirical_strategy", "conclusion"],
        section_titles={"empirical_strategy": "Empirical Strategy"},
    )

    assert _section_titles(latex) == ["Data", "Empirical Strategy", "Conclusion"]
    assert "Legacy experiment." not in latex
