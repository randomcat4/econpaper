"""Tests for economics content propagation into DocumentInput."""
from __future__ import annotations

from src.agents.metadata_agent.models import PaperMetaData


REQUIRED_SECTIONS = [
    "Introduction",
    "Data",
    "Empirical Strategy",
    "Results",
    "Robustness",
    "Conclusion",
]


def _aer_config() -> dict:
    return {
        "name": "american-economic-review",
        "page_limit": 40,
        "required_sections": REQUIRED_SECTIONS,
    }


def test_venue_required_sections_are_copied_to_constraints() -> None:
    metadata = PaperMetaData(
        title="Minimum Wage Pass-Through and Local Employment",
        idea_hypothesis="Minimum wage changes affect prices and employment.",
        method="Legacy DiD method.",
        data="County-year panel data.",
        experiments="Legacy experiment summary.",
        empirical_strategy="Difference-in-differences with county and year fixed effects.",
        results="Positive pass-through and imprecise employment effects.",
        robustness="Alternative control groups and placebo policy dates.",
    )

    document_input = metadata.to_document_input(venue_config=_aer_config())

    assert document_input.constraints.required_sections == REQUIRED_SECTIONS
    assert document_input.constraints.max_pages == 40
    assert document_input.constraints.style_guide == "american-economic-review"
    assert document_input.constraints.citation_format == "bibtex"


def test_econ_fields_enter_content_brief_with_legacy_compatibility() -> None:
    metadata = PaperMetaData(
        title="Minimum Wage Pass-Through and Local Employment",
        idea_hypothesis="Minimum wage changes affect prices and employment.",
        method="Legacy DiD method.",
        data="County-year panel data.",
        experiments="Legacy experiment summary.",
        empirical_strategy="Difference-in-differences with county and year fixed effects.",
        results="Positive pass-through and imprecise employment effects.",
        robustness="Alternative control groups and placebo policy dates.",
        institutional_background="State policy variation sets the empirical context.",
        theory_or_model="Cost pass-through model.",
        mechanisms="Price adjustment and labor demand.",
        heterogeneity="Effects vary by local labor market tightness.",
    )

    content_brief = metadata.to_document_input(venue_config=_aer_config()).content_brief

    assert content_brief["introduction"] == metadata.idea_hypothesis
    assert content_brief["data"] == metadata.data
    assert content_brief["empirical_strategy"] == metadata.empirical_strategy
    assert content_brief["results"] == metadata.results
    assert content_brief["robustness"] == metadata.robustness
    assert content_brief["conclusion"] == metadata.idea_hypothesis
    assert content_brief["institutional_background"] == metadata.institutional_background
    assert content_brief["theory_or_model"] == metadata.theory_or_model
    assert content_brief["mechanisms"] == metadata.mechanisms
    assert content_brief["heterogeneity"] == metadata.heterogeneity
    assert content_brief["method"] == metadata.method
    assert content_brief["experiments"] == metadata.experiments
    assert content_brief["idea_hypothesis"] == metadata.idea_hypothesis


def test_legacy_method_and_experiments_are_econ_fallbacks() -> None:
    metadata = PaperMetaData(
        title="Legacy Paper",
        idea_hypothesis="Legacy hypothesis.",
        method="Legacy method text.",
        data="Legacy data text.",
        experiments="Legacy experiment text.",
    )

    content_brief = metadata.to_document_input(venue_config=_aer_config()).content_brief

    assert content_brief["empirical_strategy"] == "Legacy method text."
    assert content_brief["results"] == "Legacy experiment text."
    assert content_brief["method"] == "Legacy method text."
    assert content_brief["experiments"] == "Legacy experiment text."


def test_metadata_target_pages_and_style_guide_override_venue_defaults() -> None:
    metadata = PaperMetaData(
        title="Custom Pages",
        idea_hypothesis="Hypothesis.",
        method="Method.",
        data="Data.",
        experiments="Experiments.",
        style_guide="custom-style",
        target_pages=20,
    )

    constraints = metadata.to_document_input(venue_config=_aer_config()).constraints

    assert constraints.max_pages == 20
    assert constraints.style_guide == "custom-style"


def test_without_venue_config_preserves_legacy_constraints() -> None:
    metadata = PaperMetaData(
        title="Legacy Paper",
        idea_hypothesis="Hypothesis.",
        method="Method.",
        data="Data.",
        experiments="Experiments.",
        style_guide="NeurIPS",
        target_pages=8,
    )

    document_input = metadata.to_document_input()

    assert document_input.constraints.max_pages == 8
    assert document_input.constraints.style_guide == "NeurIPS"
    assert document_input.constraints.required_sections == []
    assert document_input.content_brief["method"] == "Method."
    assert document_input.content_brief["experiments"] == "Experiments."
