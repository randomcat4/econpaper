"""Tests for deterministic venue-required section enforcement."""
from __future__ import annotations

import pytest

from src.agents.planner_agent.models import PaperPlan, PlanRequest, SectionPlan
from src.agents.planner_agent.planner_agent import PlannerAgent
from src.agents.planner_agent.planner_build import build_paper_plan
from src.agents.planner_agent.planner_defaults import (
    ECON_FINANCE_REQUIRED_SECTION_IDS,
    get_default_sources,
    get_dependencies,
    get_section_title,
)
from src.agents.planner_agent.planner_elements import (
    build_figure_placements,
    build_table_placements,
)
from src.agents.planner_agent.planner_paragraphs import (
    coerce_bool,
    expand_paragraph_plan,
    generate_default_paragraphs,
    normalize_string_list,
)
from src.agents.planner_agent.planner_sections import (
    enforce_required_sections,
    parse_paragraph_plans,
)
from src.models.document_spec import GenerationConstraints


REQUIRED_DISPLAY_SECTIONS = [
    "Introduction",
    "Data",
    "Empirical Strategy",
    "Results",
    "Robustness",
    "Conclusion",
]


def _section_types(plan: PaperPlan) -> list[str]:
    return [section.section_type for section in plan.sections]


def test_enforce_required_sections_completes_core_econ_sections() -> None:
    plan = PaperPlan(
        title="Paper",
        sections=[
            SectionPlan(section_type="abstract", section_title="Abstract"),
            SectionPlan(section_type="introduction", section_title="Introduction"),
            SectionPlan(section_type="method", section_title="Method"),
            SectionPlan(section_type="experiment", section_title="Experiments"),
            SectionPlan(section_type="result", section_title="Results"),
            SectionPlan(section_type="conclusion", section_title="Conclusion"),
        ],
    )

    enforced = enforce_required_sections(plan, REQUIRED_DISPLAY_SECTIONS)

    assert _section_types(enforced) == [
        "abstract",
        *ECON_FINANCE_REQUIRED_SECTION_IDS,
        "method",
        "experiment",
        "result",
    ]


def test_enforce_required_sections_does_not_duplicate_existing_required_sections() -> None:
    plan = PaperPlan(
        sections=[
            SectionPlan(section_type="abstract", section_title="Abstract"),
            SectionPlan(section_type="introduction", section_title="Introduction"),
            SectionPlan(section_type="conclusion", section_title="Conclusion"),
            SectionPlan(section_type="appendix", section_title="Appendix"),
        ]
    )

    enforced = enforce_required_sections(plan, REQUIRED_DISPLAY_SECTIONS)

    assert _section_types(enforced).count("introduction") == 1
    assert _section_types(enforced).count("conclusion") == 1
    assert _section_types(enforced)[0] == "abstract"
    assert _section_types(enforced)[-1] == "appendix"


def test_enforce_required_sections_adds_skeleton_paragraphs_and_defaults() -> None:
    plan = PaperPlan(sections=[SectionPlan(section_type="introduction")])

    enforced = enforce_required_sections(plan, REQUIRED_DISPLAY_SECTIONS)
    empirical_strategy = enforced.get_section("empirical_strategy")

    assert empirical_strategy is not None
    assert empirical_strategy.section_title == "Empirical Strategy"
    assert empirical_strategy.content_sources == ["empirical_strategy", "method", "data"]
    assert empirical_strategy.depends_on == ["data"]
    assert 2 <= len(empirical_strategy.paragraphs) <= 4
    assert "Identification design" in empirical_strategy.paragraphs[0].key_point


def test_enforce_required_sections_without_required_list_leaves_plan_unchanged() -> None:
    plan = PaperPlan(
        sections=[
            SectionPlan(section_type="introduction", section_title="Introduction"),
            SectionPlan(section_type="method", section_title="Method"),
        ]
    )
    before = plan.model_dump()

    assert enforce_required_sections(plan, []) is plan
    assert plan.model_dump() == before


@pytest.mark.asyncio
async def test_build_paper_plan_enforces_required_sections_from_constraints() -> None:
    class Request:
        title = "Economics Paper"
        constraints = GenerationConstraints(required_sections=REQUIRED_DISPLAY_SECTIONS)

    async def noop_assign(*_args, **_kwargs):
        return None

    plan = await build_paper_plan(
        plan_data={
            "paper_type": "empirical",
            "sections": [
                {"section_type": "introduction", "section_title": "Introduction"},
                {"section_type": "method", "section_title": "Method"},
                {"section_type": "experiment", "section_title": "Experiments"},
                {"section_type": "result", "section_title": "Results"},
                {"section_type": "conclusion", "section_title": "Conclusion"},
            ],
        },
        request=Request(),
        total_words=1800,
        parse_paragraph_plans_fn=parse_paragraph_plans,
        generate_default_paragraphs_fn=generate_default_paragraphs,
        build_figure_placements_fn=build_figure_placements,
        build_table_placements_fn=build_table_placements,
        get_section_title_fn=get_section_title,
        get_default_sources_fn=get_default_sources,
        get_dependencies_fn=get_dependencies,
        normalize_string_list_fn=normalize_string_list,
        coerce_bool_fn=coerce_bool,
        expand_paragraph_plan_fn=expand_paragraph_plan,
        assign_figure_table_definitions_fn=noop_assign,
    )

    assert _section_types(plan) == [
        "abstract",
        *ECON_FINANCE_REQUIRED_SECTION_IDS,
        "method",
        "experiment",
        "result",
    ]


@pytest.mark.asyncio
async def test_create_plan_enforces_required_sections_when_llm_returns_ml_defaults() -> None:
    planner = PlannerAgent.__new__(PlannerAgent)
    planner.vlm_service = None
    planner.enable_plan_review = False
    planner.plan_review_max_iterations = 0

    async def mock_llm_json_call(_system, _user, label, **_kwargs):
        if label == "step1_structure":
            return {
                "paper_type": "empirical",
                "contributions": ["Credit supply identification"],
                "narrative_style": "technical",
                "sections": [
                    {"section_type": "introduction", "section_title": "Introduction"},
                    {"section_type": "method", "section_title": "Method"},
                    {"section_type": "experiment", "section_title": "Experiments"},
                    {"section_type": "result", "section_title": "Results"},
                    {"section_type": "conclusion", "section_title": "Conclusion"},
                ],
            }
        if label == "step2_citation":
            return {"total_target": 6, "section_allocation": {}}
        if label.startswith("step4_"):
            return {"needs_subsections": False}
        return {"paragraphs": [{"key_point": "Develop the section.", "approx_sentences": 3}]}

    planner._llm_json_call = mock_llm_json_call
    planner._assign_figures_to_sections = lambda *_args, **_kwargs: {}

    request = PlanRequest(
        title="Economics Runtime Path",
        idea_hypothesis="Credit supply affects employment.",
        method="Difference-in-differences.",
        data="Bank-county panel.",
        experiments="Main estimates and robustness.",
        constraints=GenerationConstraints(required_sections=REQUIRED_DISPLAY_SECTIONS),
    )

    plan = await planner.create_plan(
        request,
        review_enabled=False,
        review_max_iterations=0,
    )

    assert _section_types(plan) == [
        "abstract",
        *ECON_FINANCE_REQUIRED_SECTION_IDS,
        "method",
        "experiment",
        "result",
    ]
