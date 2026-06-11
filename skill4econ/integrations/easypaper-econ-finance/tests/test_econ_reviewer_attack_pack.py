"""Tests for the econ/finance reviewer attack-pack checker."""
from __future__ import annotations

from src.agents.reviewer_agent.checkers.econ_attack_pack import EconAttackPackChecker
from src.agents.reviewer_agent.models import ReviewContext, Severity
from src.agents.reviewer_agent.reviewer_agent import ReviewerAgent
from src.config.schema import ModelConfig


async def test_econ_attack_pack_flags_invented_coefficients_weak_id_and_leakage() -> None:
    checker = EconAttackPackChecker()
    context = ReviewContext(
        sections={
            "results": "The estimated coefficient is -0.31 and significant at p < 0.01.",
            "empirical_strategy": (
                "We identify the causal effect of bank lending on employment."
            ),
            "data": (
                "We form the trading signal using future stock returns to predict "
                "portfolio returns."
            ),
        },
        word_counts={"results": 10, "empirical_strategy": 9, "data": 12},
        style_guide="journal-of-financial-economics",
    )

    feedback = await checker.check(context)

    kinds = {flag["kind"] for flag in feedback.details["attack_pack_flags"]}
    assert feedback.passed is False
    assert feedback.severity == Severity.ERROR
    assert kinds == {
        "invented_coefficient",
        "weak_identification",
        "finance_leakage",
    }
    assert set(feedback.details["sections_to_revise"]) == {
        "results",
        "empirical_strategy",
        "data",
    }


async def test_econ_attack_pack_allows_anchored_design_and_timing_language() -> None:
    checker = EconAttackPackChecker()
    context = ReviewContext(
        sections={
            "results": r"Table~\ref{tab:main} reports a coefficient of -0.31.",
            "empirical_strategy": (
                "We identify the causal effect using bank exposure shocks and "
                "county fixed effects."
            ),
            "data": (
                "We use lagged returns available at portfolio formation to "
                "predict out-of-sample returns."
            ),
        },
        word_counts={"results": 7, "empirical_strategy": 11, "data": 12},
        style_guide="jfe",
    )

    feedback = await checker.check(context)

    assert feedback.passed is True
    assert feedback.details["attack_pack_flags"] == []


def test_reviewer_registers_econ_attack_pack_checker() -> None:
    agent = ReviewerAgent(
        config=ModelConfig(
            model_name="test-model",
            api_key="test-key",
            base_url="https://example.test/v1",
        )
    )

    checker_names = {entry["name"] for entry in agent.get_checkers()}

    assert "econ_attack_pack" in checker_names
