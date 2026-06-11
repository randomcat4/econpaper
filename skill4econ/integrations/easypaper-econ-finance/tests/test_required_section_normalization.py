"""Tests for venue-required economics section normalization."""
from __future__ import annotations

from src.agents.planner_agent.planner_sections import (
    normalize_constraints_required_sections,
    normalize_required_section_name,
    normalize_required_section_names,
)
from src.agents.planner_agent.planner_utils import normalize_section_type_name
from src.models.document_spec import GenerationConstraints


def test_required_section_display_names_normalize_to_canonical_ids() -> None:
    assert normalize_required_section_name("Empirical Strategy") == "empirical_strategy"
    assert normalize_required_section_name("Results") == "results"
    assert normalize_required_section_name("Robustness Checks") == "robustness"
    assert normalize_required_section_name("Theory") == "theory_or_model"


def test_required_section_normalization_preserves_order_and_deduplicates() -> None:
    assert normalize_required_section_names(
        [
            "Introduction",
            "Empirical Design",
            "Empirical Strategy",
            "Main Results",
            "Conclusions",
        ]
    ) == [
        "introduction",
        "empirical_strategy",
        "results",
        "conclusion",
    ]


def test_generation_constraints_required_sections_are_normalized_in_place() -> None:
    constraints = GenerationConstraints(
        required_sections=["Introduction", "Data", "Identification Strategy", "Results"]
    )

    assert normalize_constraints_required_sections(constraints) == [
        "introduction",
        "data",
        "empirical_strategy",
        "results",
    ]
    assert constraints.required_sections == [
        "introduction",
        "data",
        "empirical_strategy",
        "results",
    ]


def test_dict_constraints_required_sections_are_normalized_in_place() -> None:
    constraints = {"required_sections": ["Institutional Background", "Model"]}

    assert normalize_constraints_required_sections(constraints) == [
        "institutional_background",
        "theory_or_model",
    ]
    assert constraints["required_sections"] == [
        "institutional_background",
        "theory_or_model",
    ]


def test_legacy_section_type_normalization_keeps_results_singular() -> None:
    assert normalize_section_type_name("results") == "result"
