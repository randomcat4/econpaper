"""Tests for economics and finance constraints in planner prompts."""
from __future__ import annotations

from src.agents.planner_agent.planner_build import (
    format_content_brief_block,
    format_venue_required_sections_block,
)
from src.agents.planner_agent.prompt_contracts import STEP1_STRUCTURE_USER


REQUIRED_SECTION_IDS = [
    "introduction",
    "data",
    "empirical_strategy",
    "results",
    "robustness",
    "conclusion",
]


def _format_step1_prompt() -> str:
    return STEP1_STRUCTURE_USER.format(
        title="Bank Lending and Local Employment",
        idea_hypothesis="Bank credit supply shocks affect employment.",
        method="Difference-in-differences around lender exposure.",
        data="Bank branch lending and county employment panels.",
        experiments="Main estimates, event studies, and robustness checks.",
        style_guide="journal-of-financial-economics",
        target_pages=40,
        research_context_summary="Not available.",
        code_writing_assets_summary="Not available.",
        venue_required_sections_block=format_venue_required_sections_block(
            REQUIRED_SECTION_IDS
        ),
        content_brief_block=format_content_brief_block(
            {
                "introduction": "Motivate credit supply and labor-market relevance.",
                "data": "Describe matched bank-county panel construction.",
                "empirical_strategy": "State identifying variation and fixed effects.",
                "results": "Summarize main coefficient patterns.",
                "robustness": "Cover placebo and alternative clustering checks.",
                "conclusion": "Synthesize contribution for finance readers.",
            },
            REQUIRED_SECTION_IDS,
        ),
    )


def test_step1_prompt_contains_econ_required_sections() -> None:
    prompt = _format_step1_prompt()

    assert "Venue required sections:" in prompt
    assert "- Empirical Strategy" in prompt
    assert "- Robustness" in prompt
    assert "You must produce a paper plan that includes these sections in this order." in prompt


def test_step1_prompt_warns_not_to_replace_econ_sections_with_ml_sections() -> None:
    prompt = _format_step1_prompt()

    assert (
        "do not replace Data / Empirical Strategy / Results / Robustness "
        "with generic ML sections such as Method / Experiment / Result"
    ) in prompt


def test_step1_prompt_contains_content_brief_by_section() -> None:
    prompt = _format_step1_prompt()

    assert "Content brief by section:" in prompt
    assert "introduction: Motivate credit supply" in prompt
    assert "empirical_strategy: State identifying variation" in prompt
    assert "robustness: Cover placebo" in prompt
