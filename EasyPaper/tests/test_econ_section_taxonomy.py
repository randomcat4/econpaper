"""Tests for economics and finance planner section taxonomy."""
from __future__ import annotations

from src.agents.planner_agent.planner_defaults import (
    ECON_FINANCE_CANONICAL_SECTION_IDS,
    ECON_FINANCE_REQUIRED_SECTION_IDS,
    ECON_FINANCE_SECTION_DEFAULTS,
    get_default_sources,
    get_dependencies,
    get_econ_finance_section_default,
    get_section_title,
)


def test_econ_finance_required_section_order() -> None:
    assert ECON_FINANCE_REQUIRED_SECTION_IDS == [
        "introduction",
        "data",
        "empirical_strategy",
        "results",
        "robustness",
        "conclusion",
    ]


def test_econ_finance_canonical_sections_include_optional_extensions() -> None:
    assert ECON_FINANCE_CANONICAL_SECTION_IDS == [
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


def test_econ_finance_defaults_define_titles_sources_and_dependencies() -> None:
    for section_id in ECON_FINANCE_CANONICAL_SECTION_IDS:
        defaults = ECON_FINANCE_SECTION_DEFAULTS[section_id]
        assert defaults["title"]
        assert isinstance(defaults["content_sources"], list)
        assert isinstance(defaults["dependencies"], list)

    assert ECON_FINANCE_SECTION_DEFAULTS["empirical_strategy"] == {
        "title": "Empirical Strategy",
        "content_sources": ["empirical_strategy", "method", "data"],
        "dependencies": ["data"],
    }
    assert ECON_FINANCE_SECTION_DEFAULTS["results"]["dependencies"] == [
        "empirical_strategy"
    ]
    assert ECON_FINANCE_SECTION_DEFAULTS["robustness"]["dependencies"] == ["results"]


def test_generic_section_helpers_understand_econ_finance_ids() -> None:
    assert get_section_title("empirical_strategy") == "Empirical Strategy"
    assert get_default_sources("empirical_strategy") == [
        "empirical_strategy",
        "method",
        "data",
    ]
    assert get_dependencies("empirical_strategy") == ["data"]
    assert get_section_title("robustness") == "Robustness"
    assert get_default_sources("robustness") == [
        "robustness",
        "results",
        "experiments",
    ]
    assert get_dependencies("robustness") == ["results"]


def test_get_econ_finance_section_default_returns_copy() -> None:
    defaults = get_econ_finance_section_default("results")
    defaults["title"] = "Mutated"

    assert ECON_FINANCE_SECTION_DEFAULTS["results"]["title"] == "Results"
