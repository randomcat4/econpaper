"""Tests for deterministic econ/finance claim gates."""
from __future__ import annotations

from src.agents.planner_agent.models import ParagraphPlan
from src.generation.claim_verifier import ClaimVerifier


async def test_blocks_unsupported_numeric_empirical_claim() -> None:
    verifier = ClaimVerifier()
    para = ParagraphPlan(key_point="")

    result = await verifier.verify(
        generated_text="The estimated coefficient is -0.18 and significant at p < 0.05.",
        paragraph_plan=para,
        valid_citation_keys=set(),
        section_type="results",
    )

    assert result.passed is False
    assert any(
        issue["gate"] == "unsupported_numeric_empirical_claim"
        for issue in result.econ_gate_issues
    )
    assert "Numeric empirical claims" in result.feedback_for_retry


async def test_allows_numeric_empirical_claim_with_artifact_reference() -> None:
    verifier = ClaimVerifier()
    para = ParagraphPlan(key_point="", tables_to_reference=["tab:main"])

    result = await verifier.verify(
        generated_text=r"The estimated coefficient is -0.18 in Table~\ref{tab:main}.",
        paragraph_plan=para,
        valid_citation_keys=set(),
        section_type="results",
    )

    assert result.passed is True
    assert result.econ_gate_issues == []


async def test_blocks_identification_claim_without_anchor_language() -> None:
    verifier = ClaimVerifier()
    para = ParagraphPlan(key_point="")

    result = await verifier.verify(
        generated_text="We identify the causal effect of bank lending on employment.",
        paragraph_plan=para,
        valid_citation_keys=set(),
        section_type="empirical_strategy",
    )

    assert result.passed is False
    assert any(
        issue["gate"] == "identification_claim_without_anchor"
        for issue in result.econ_gate_issues
    )


async def test_allows_identification_claim_with_design_anchor_language() -> None:
    verifier = ClaimVerifier()
    para = ParagraphPlan(key_point="")

    result = await verifier.verify(
        generated_text=(
            "We identify the causal effect using bank exposure shocks and "
            "county fixed effects."
        ),
        paragraph_plan=para,
        valid_citation_keys=set(),
        section_type="empirical_strategy",
    )

    assert result.passed is True
    assert result.econ_gate_issues == []


async def test_blocks_robustness_section_as_new_main_result() -> None:
    verifier = ClaimVerifier()
    para = ParagraphPlan(key_point="Robustness checks")

    result = await verifier.verify(
        generated_text=(
            "Robustness checks reveal a new main result: constrained firms "
            "exit the market after lender shocks."
        ),
        paragraph_plan=para,
        valid_citation_keys=set(),
        section_type="robustness",
    )

    assert result.passed is False
    assert any(
        issue["gate"] == "robustness_as_new_main_result"
        for issue in result.econ_gate_issues
    )


async def test_allows_robustness_as_bridge_back_to_main_result() -> None:
    verifier = ClaimVerifier()
    para = ParagraphPlan(key_point="Robustness checks")

    result = await verifier.verify(
        generated_text=(
            "Robustness checks confirm that the main result remains stable "
            "across placebo specifications."
        ),
        paragraph_plan=para,
        valid_citation_keys=set(),
        section_type="robustness",
    )

    assert result.passed is True
    assert result.econ_gate_issues == []
