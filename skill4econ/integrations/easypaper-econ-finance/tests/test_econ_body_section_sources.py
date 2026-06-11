"""Tests for economics and finance body section source mappings."""
from __future__ import annotations

from src.agents.metadata_agent.models import BODY_SECTION_SOURCES, PaperMetaData
from src.agents.metadata_agent.section_generation import resolve_section_content


EXPECTED_ECON_BODY_SECTION_SOURCES = {
    "data": ["data"],
    "empirical_strategy": ["empirical_strategy", "method", "data"],
    "results": ["results", "experiments", "data"],
    "robustness": ["robustness", "experiments", "method"],
    "institutional_background": ["institutional_background", "idea_hypothesis"],
    "theory_or_model": ["theory_or_model", "method"],
    "mechanisms": ["mechanisms", "results"],
    "heterogeneity": ["heterogeneity", "results", "data"],
}


def test_econ_body_section_sources_are_registered() -> None:
    for section_type, sources in EXPECTED_ECON_BODY_SECTION_SOURCES.items():
        assert BODY_SECTION_SOURCES[section_type] == sources


def test_empirical_strategy_source_order_prefers_direct_econ_field() -> None:
    assert BODY_SECTION_SOURCES["empirical_strategy"] == [
        "empirical_strategy",
        "method",
        "data",
    ]


def test_resolver_uses_econ_body_sources_without_section_plan() -> None:
    metadata = PaperMetaData(
        title="Paper",
        idea_hypothesis="Idea.",
        method="Legacy method.",
        data="Legacy data.",
        experiments="Legacy experiments.",
        empirical_strategy="Econ identification.",
    )

    assert resolve_section_content(
        "empirical_strategy",
        section_plan=None,
        metadata=metadata,
        content_brief=None,
    ) == {"empirical_strategy": "Econ identification.", "method": "Legacy method.", "data": "Legacy data."}


def test_resolver_uses_content_brief_source_order_without_section_plan() -> None:
    metadata = PaperMetaData(
        title="Paper",
        idea_hypothesis="Idea.",
        method="Legacy method.",
        data="Legacy data.",
        experiments="Legacy experiments.",
    )

    assert resolve_section_content(
        "robustness",
        section_plan=None,
        metadata=metadata,
        content_brief={"results": "Stable main results.", "experiments": "Legacy brief."},
    ) == {"experiments": "Legacy brief."}
