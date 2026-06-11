"""Tests for economics and finance metadata fields."""
from __future__ import annotations

from src.agents.metadata_agent.models import PaperMetaData


def test_legacy_metadata_still_initializes_without_econ_fields() -> None:
    metadata = PaperMetaData(
        title="Legacy ML Paper",
        idea_hypothesis="A model improves accuracy.",
        method="A transformer method.",
        data="Benchmark datasets.",
        experiments="Ablations and comparisons.",
    )

    assert metadata.empirical_strategy is None
    assert metadata.results is None
    assert metadata.robustness is None
    assert metadata.venue is None


def test_econ_metadata_fields_initialize() -> None:
    metadata = PaperMetaData(
        title="Minimum Wage Pass-Through and Local Employment",
        idea_hypothesis="Minimum wage changes affect prices and employment.",
        method="Difference-in-differences design.",
        data="County-year panel data.",
        experiments="Baseline estimates and robustness checks.",
        venue="american-economic-review",
        empirical_strategy="Compare exposed counties to control counties with fixed effects.",
        results="Price pass-through is positive and employment effects are imprecise.",
        robustness="Alternative control groups and placebo policy dates.",
        institutional_background="State minimum wage policies vary over time.",
        theory_or_model="Competitive pass-through with labor cost shocks.",
        mechanisms="Price adjustment and labor demand margins.",
        heterogeneity="Effects vary by tradability and county income.",
    )

    assert metadata.venue == "american-economic-review"
    assert metadata.empirical_strategy.startswith("Compare exposed")
    assert metadata.results.startswith("Price pass-through")
    assert metadata.robustness.startswith("Alternative")
    assert metadata.institutional_background.startswith("State")
    assert metadata.theory_or_model.startswith("Competitive")
    assert metadata.mechanisms.startswith("Price")
    assert metadata.heterogeneity.startswith("Effects")


def test_econ_metadata_fields_roundtrip_through_serialization() -> None:
    metadata = PaperMetaData(
        title="Bank Capital Requirements and Corporate Investment",
        idea_hypothesis="Capital regulation affects firm investment.",
        method="Bank exposure design.",
        data="Bank-firm matched panel.",
        experiments="Loan and investment outcomes.",
        venue="journal-of-financial-economics",
        empirical_strategy="Exploit bank-level regulatory capital shocks.",
        results="Exposed firms reduce borrowing and investment.",
        robustness="Matched samples and placebo shocks.",
    )

    dumped = metadata.model_dump(mode="json")
    restored = PaperMetaData.model_validate(dumped)

    assert restored.venue == "journal-of-financial-economics"
    assert restored.empirical_strategy == "Exploit bank-level regulatory capital shocks."
    assert restored.results == "Exposed firms reduce borrowing and investment."
    assert restored.robustness == "Matched samples and placebo shocks."
