"""
Tests for planner research-context formatting helpers.
- **Description**:
    - Validates type-safe handling of LLM-generated research context fields
    - Ensures dict/non-list values for list-expected fields do not cause
      'unhashable type: slice' errors
"""

from src.agents.planner_agent.planner_build import (
    format_content_brief_block,
    format_venue_required_sections_block,
)
from src.agents.planner_agent.planner_context import format_research_context_for_planning


class TestFormatResearchContext:
    """Tests for format_research_context_for_planning type safety."""

    def test_none_context(self):
        result = format_research_context_for_planning(None)
        assert result == "Not available."

    def test_empty_context(self):
        result = format_research_context_for_planning({})
        assert result == "Not available."

    def test_normal_list_fields(self):
        ctx = {
            "research_area": "Machine Learning",
            "summary": "Overview of ML research.",
            "research_trends": ["trend1", "trend2", "trend3", "trend4"],
            "gaps": ["gap1", "gap2"],
            "contribution_ranking": {
                "P0": [{"contribution": "Main contribution"}],
                "P1": [],
                "P2": [],
            },
        }
        result = format_research_context_for_planning(ctx)
        assert "Machine Learning" in result
        assert "trend1" in result
        assert "trend3" in result
        assert "trend4" not in result  # capped at 3
        assert "gap1" in result
        assert "Main contribution" in result

    def test_trends_as_dict_no_crash(self):
        """LLM may return research_trends as a dict instead of a list."""
        ctx = {
            "research_area": "NLP",
            "research_trends": {"trend_a": "description_a", "trend_b": "description_b"},
            "gaps": ["gap1"],
        }
        result = format_research_context_for_planning(ctx)
        assert "NLP" in result
        assert "gap1" in result
        assert "trends" not in result.lower() or "Key trends" not in result

    def test_gaps_as_dict_no_crash(self):
        """LLM may return gaps as a dict instead of a list."""
        ctx = {
            "research_area": "CV",
            "research_trends": ["trend1"],
            "gaps": {"gap_a": "desc_a"},
        }
        result = format_research_context_for_planning(ctx)
        assert "CV" in result
        assert "trend1" in result

    def test_contribution_ranking_as_list_no_crash(self):
        """LLM may return contribution_ranking as a list instead of dict."""
        ctx = {
            "research_area": "RL",
            "contribution_ranking": ["contribution1", "contribution2"],
        }
        result = format_research_context_for_planning(ctx)
        assert "RL" in result

    def test_ranking_items_as_dict_no_crash(self):
        """LLM may return P0/P1 items as a dict instead of a list."""
        ctx = {
            "research_area": "AI",
            "contribution_ranking": {
                "P0": {"contribution": "top contribution"},
                "P1": [],
                "P2": [],
            },
        }
        result = format_research_context_for_planning(ctx)
        assert "AI" in result

    def test_trends_as_string_no_crash(self):
        """LLM may return research_trends as a plain string."""
        ctx = {
            "research_area": "Robotics",
            "research_trends": "single trend string",
            "gaps": "single gap",
        }
        result = format_research_context_for_planning(ctx)
        assert "Robotics" in result

    def test_all_fields_malformed(self):
        """Worst case: every list/dict field has wrong types."""
        ctx = {
            "research_area": 42,
            "summary": None,
            "research_trends": {"a": 1},
            "gaps": {"b": 2},
            "contribution_ranking": "not a dict",
        }
        result = format_research_context_for_planning(ctx)
        assert "42" in result
        assert isinstance(result, str)


class TestPlannerPromptFormatting:
    def test_empty_required_sections_omit_venue_required_block(self):
        assert format_venue_required_sections_block([]) == ""
        assert format_venue_required_sections_block(None) == ""

    def test_content_brief_orders_required_sections_first(self):
        result = format_content_brief_block(
            {
                "results": "Main effects.",
                "introduction": "Motivation.",
                "appendix": "Extra tests.",
            },
            ["introduction", "results"],
        )

        assert result.splitlines() == [
            "Content brief by section:",
            "introduction: Motivation.",
            "results: Main effects.",
            "appendix: Extra tests.",
        ]
