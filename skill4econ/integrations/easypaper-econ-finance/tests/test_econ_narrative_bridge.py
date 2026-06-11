"""Tests for econ/finance robustness narrative bridge rules."""
from __future__ import annotations

from src.agents.planner_agent.models import PaperPlan, ParagraphPlan, SectionPlan
from src.agents.planner_agent.plan_review_rules import (
    deterministic_plan_review_issues,
    find_robustness_narrative_bridge_issues,
)


def test_plan_review_flags_robustness_as_new_main_result() -> None:
    plan = PaperPlan(
        title="Finance Paper",
        sections=[
            SectionPlan(section_type="results", section_title="Results"),
            SectionPlan(
                section_type="robustness",
                section_title="Robustness",
                paragraphs=[
                    ParagraphPlan(
                        key_point=(
                            "Robustness checks reveal a new main result about "
                            "credit-market spillovers."
                        )
                    )
                ],
            ),
            SectionPlan(section_type="conclusion", section_title="Conclusion"),
        ],
    )

    issues = find_robustness_narrative_bridge_issues(plan)

    assert len(issues) == 1
    assert issues[0].category == "econ_narrative_bridge"
    assert issues[0].severity == "major"
    assert issues[0].paragraph_locator == "p0"


def test_deterministic_plan_review_includes_robustness_bridge_rule() -> None:
    plan = PaperPlan(
        title="Finance Paper",
        sections=[
            SectionPlan(section_type="results", section_title="Results"),
            SectionPlan(
                section_type="robustness",
                section_title="Robustness",
                paragraphs=[
                    ParagraphPlan(
                        key_point="The primary finding is a new channel in placebo tests."
                    )
                ],
            ),
            SectionPlan(section_type="conclusion", section_title="Conclusion"),
        ],
    )

    issues = deterministic_plan_review_issues(plan)

    assert any(
        issue.issue_id == "det-robustness-new-main-result-robustness-p0"
        for issue in issues
    )


def test_plan_review_allows_robustness_as_confirmation_bridge() -> None:
    plan = PaperPlan(
        title="Finance Paper",
        sections=[
            SectionPlan(
                section_type="robustness",
                section_title="Robustness",
                paragraphs=[
                    ParagraphPlan(
                        key_point=(
                            "Placebo and alternative specification checks confirm "
                            "that the main result remains stable."
                        )
                    )
                ],
            )
        ],
    )

    issues = find_robustness_narrative_bridge_issues(plan)

    assert issues == []
