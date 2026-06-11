"""
Regression tests for high-level narrative section shape guards.
"""
from __future__ import annotations

from pathlib import Path

from src.agents.metadata_agent.latex_helpers import (
    collapse_duplicate_introduction_contributions,
    normalize_narrative_section_shapes,
    proseify_conclusion_itemize,
)
from src.agents.planner_agent.plan_review_rules import deterministic_plan_review_issues
from src.agents.planner_agent.planner_agent import PlannerAgent
from src.agents.planner_agent.planner_build import build_paper_plan
from src.agents.planner_agent.planner_defaults import (
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
from src.agents.planner_agent.planner_sections import parse_paragraph_plans
from src.agents.planner_agent.models import (
    PaperPlan,
    ParagraphPlan,
    PlanRequest,
    PlanReviewIssue,
    PlanReviewIteration,
    PlanReviewSeverity,
    SectionPlan,
    SubSectionPlan,
)
from src.agents.planner_agent.planner_sections import sanitize_conclusion_like_subsections


def test_duplicate_introduction_contribution_arc_is_trimmed():
    content = r"""
Motivation paragraph.

Our main contributions are summarized as follows:
\begin{itemize}
\item First contribution.
\item Second contribution.
\end{itemize}

In this paper, we present the same story again. Our main contributions are summarized as follows:
\begin{itemize}
\item Duplicate first contribution.
\item Duplicate second contribution.
\end{itemize}
"""

    cleaned = collapse_duplicate_introduction_contributions(content)

    assert cleaned.count(r"\begin{itemize}") == 1
    assert "Duplicate first contribution" not in cleaned
    assert "First contribution" in cleaned


def test_conclusion_itemize_is_converted_to_prose():
    content = r"""
\subsection{Conclusion}

This work connects structured inference with control. In summary, this work contributes:
\begin{itemize}
\item A constrained optimization framework.
\item An EKVAE architecture.
\item A hierarchical prior.
\end{itemize}
These constraints improve interpretability.
"""

    cleaned = proseify_conclusion_itemize(content)

    assert r"\begin{itemize}" not in cleaned
    assert r"\item" not in cleaned
    assert "A constrained optimization framework" in cleaned
    assert "An EKVAE architecture" in cleaned
    assert "These constraints improve interpretability." in cleaned


def test_normalize_narrative_section_shapes_handles_intro_and_discussion():
    sections = {
        "introduction": r"""Intro.

Our main contributions are summarized as follows:
\begin{itemize}
\item Keep me.
\end{itemize}

Our main contributions are summarized as follows:
\begin{itemize}
\item Drop me.
\end{itemize}
""",
        "discussion": r"""\section{Discussion and Conclusion}
\subsection{Conclusion}
In summary, this work contributes:
\begin{itemize}
\item No bullets here.
\end{itemize}
""",
    }

    cleaned = normalize_narrative_section_shapes(sections)

    assert cleaned["introduction"].count(r"\begin{itemize}") == 1
    assert "Drop me" not in cleaned["introduction"]
    assert r"\begin{itemize}" not in cleaned["discussion"]
    assert "No bullets here" in cleaned["discussion"]


def test_planner_removes_conclusion_subsection_from_discussion():
    para = ParagraphPlan(key_point="Wrap up")
    para.presentation.mode = "prose_with_list"
    para.presentation.list_label = "In summary, this work contributes:"
    para.presentation.list_items = ["A", "B"]
    section = SectionPlan(
        section_type="discussion",
        section_title="Discussion and Conclusion",
        subsections=[
            SubSectionPlan(title="Limitations", paragraphs=[ParagraphPlan(key_point="Limits")]),
            SubSectionPlan(title="Conclusion", paragraphs=[para]),
        ],
    )

    cleaned = sanitize_conclusion_like_subsections(section)

    assert cleaned.section_title == "Discussion"
    assert [sub.title for sub in cleaned.subsections] == ["Limitations"]


async def test_planner_preserves_dedicated_conclusion_when_llm_omits_it():
    class Request:
        title = "Paper"

    async def noop_assign(*_args, **_kwargs):
        return None

    plan = await build_paper_plan(
        plan_data={
            "paper_type": "empirical",
            "sections": [
                {"section_type": "introduction", "section_title": "Introduction"},
                {"section_type": "method", "section_title": "Method"},
                {"section_type": "discussion", "section_title": "Discussion and Conclusion"},
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

    assert [section.section_type for section in plan.sections] == [
        "abstract",
        "introduction",
        "method",
        "discussion",
        "conclusion",
    ]
    assert plan.get_section("discussion").section_title == "Discussion"


async def test_build_paper_plan_preserves_duplicate_body_sections():
    class Request:
        title = "Paper"

    async def noop_assign(*_args, **_kwargs):
        return None

    plan = await build_paper_plan(
        plan_data={
            "paper_type": "empirical",
            "sections": [
                {"section_type": "introduction", "section_title": "Introduction"},
                {"section_type": "result", "section_title": "Main Results"},
                {"section_type": "result", "section_title": "Ablation Results"},
                {"section_type": "discussion", "section_title": "Discussion and Conclusion"},
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

    assert [section.section_type for section in plan.sections] == [
        "abstract",
        "introduction",
        "result",
        "result_2",
        "discussion",
        "conclusion",
    ]
    assert plan.get_section("discussion").section_title == "Discussion"


async def test_create_plan_runtime_path_adds_conclusion_without_tokens():
    planner = PlannerAgent.__new__(PlannerAgent)
    planner.vlm_service = None
    planner.enable_plan_review = False
    planner.plan_review_max_iterations = 0

    async def mock_llm_json_call(_system, _user, label, **_kwargs):
        if label == "step1_structure":
            return {
                "paper_type": "empirical",
                "contributions": ["A planner invariant"],
                "narrative_style": "technical",
                "sections": [
                    {"section_type": "introduction", "section_title": "Introduction"},
                    {"section_type": "method", "section_title": "Method"},
                    {"section_type": "discussion", "section_title": "Discussion and Conclusion"},
                ],
            }
        if label == "step2_citation":
            return {"total_target": 6, "section_allocation": {}}
        if label.startswith("step4_"):
            return {"needs_subsections": False}
        return {
            "paragraphs": [{"key_point": "Develop the section.", "approx_sentences": 3}],
            "topic_clusters": [],
            "sectioning_recommended": False,
        }

    planner._llm_json_call = mock_llm_json_call
    planner._assign_figures_to_sections = lambda *_args, **_kwargs: {}

    request = PlanRequest(
        title="Runtime Planner Path",
        idea_hypothesis="A full-paper plan should always include a conclusion.",
        method="Planner structure normalization.",
        data="Synthetic planner response.",
        experiments="No-token regression test.",
    )

    plan = await planner.create_plan(request, review_enabled=False, review_max_iterations=0)

    assert [section.section_type for section in plan.sections] == [
        "abstract",
        "introduction",
        "method",
        "discussion",
        "conclusion",
    ]
    assert plan.get_section("discussion").section_title == "Discussion"
    assert plan.get_section("conclusion") is not None


async def test_create_plan_review_path_preserves_conclusion_invariant():
    planner = PlannerAgent.__new__(PlannerAgent)
    planner.vlm_service = None
    planner.enable_plan_review = True
    planner.plan_review_max_iterations = 2

    async def mock_llm_json_call(_system, _user, label, **_kwargs):
        if label == "step1_structure":
            return {
                "paper_type": "empirical",
                "contributions": ["A planner invariant"],
                "narrative_style": "technical",
                "sections": [
                    {"section_type": "introduction", "section_title": "Introduction"},
                    {"section_type": "method", "section_title": "Method"},
                    {"section_type": "discussion", "section_title": "Discussion and Conclusion"},
                ],
            }
        if label == "step2_citation":
            return {"total_target": 6, "section_allocation": {}}
        if label.startswith("step4_"):
            return {"needs_subsections": False}
        return {
            "paragraphs": [{"key_point": "Develop the section.", "approx_sentences": 3}],
            "topic_clusters": [],
            "sectioning_recommended": False,
        }

    async def mock_criticize_plan(_plan, iteration, **_kwargs):
        if iteration == 1:
            return PlanReviewIteration(
                iteration=iteration,
                issues=[
                    PlanReviewIssue(
                        issue_id="force-optimizer",
                        section_type="introduction",
                        category="coverage",
                        severity=PlanReviewSeverity.MAJOR,
                        title="Force optimizer",
                    )
                ],
            )
        return PlanReviewIteration(iteration=iteration, issues=[])

    async def mock_optimize_plan(_plan, _issues, _iteration):
        return PaperPlan(
            title="Runtime Planner Path",
            sections=[
                SectionPlan(section_type="abstract", section_title="Abstract"),
                SectionPlan(section_type="introduction", section_title="Introduction"),
                SectionPlan(section_type="result", section_title="Main Results"),
                SectionPlan(section_type="result", section_title="Ablation Results"),
                SectionPlan(section_type="method", section_title="Method"),
                SectionPlan(section_type="discussion", section_title="Discussion and Conclusion"),
            ],
            contributions=["A planner invariant"],
        )

    planner._llm_json_call = mock_llm_json_call
    planner._assign_figures_to_sections = lambda *_args, **_kwargs: {}
    planner._criticize_plan = mock_criticize_plan
    planner._optimize_plan = mock_optimize_plan

    request = PlanRequest(
        title="Runtime Planner Path",
        idea_hypothesis="A full-paper plan should always include a conclusion.",
        method="Planner structure normalization.",
        data="Synthetic planner response.",
        experiments="No-token regression test.",
    )

    plan = await planner.create_plan(request)

    assert [section.section_type for section in plan.sections] == [
        "abstract",
        "introduction",
        "result",
        "result_2",
        "method",
        "discussion",
        "conclusion",
    ]
    assert plan.get_section("discussion").section_title == "Discussion"
    assert plan.get_section("conclusion") is not None


async def test_create_plan_preserves_duplicate_body_sections_before_suffixing():
    planner = PlannerAgent.__new__(PlannerAgent)
    planner.vlm_service = None
    planner.enable_plan_review = False
    planner.plan_review_max_iterations = 0

    async def mock_llm_json_call(_system, _user, label, **_kwargs):
        if label == "step1_structure":
            return {
                "paper_type": "empirical",
                "contributions": ["Preserve duplicate semantic sections"],
                "narrative_style": "technical",
                "sections": [
                    {"section_type": "introduction", "section_title": "Introduction"},
                    {"section_type": "result", "section_title": "Main Results"},
                    {"section_type": "result", "section_title": "Ablation Results"},
                    {"section_type": "discussion", "section_title": "Discussion and Conclusion"},
                ],
            }
        if label == "step2_citation":
            return {"total_target": 6, "section_allocation": {}}
        if label.startswith("step4_"):
            return {"needs_subsections": False}
        return {
            "paragraphs": [{"key_point": "Develop the section.", "approx_sentences": 3}],
            "topic_clusters": [],
            "sectioning_recommended": False,
        }

    planner._llm_json_call = mock_llm_json_call
    planner._assign_figures_to_sections = lambda *_args, **_kwargs: {}

    request = PlanRequest(
        title="Duplicate Body Sections",
        idea_hypothesis="Duplicate semantic sections should survive planning.",
        method="Planner section suffixing.",
        data="Synthetic planner response.",
        experiments="No-token regression test.",
    )

    plan = await planner.create_plan(request, review_enabled=False, review_max_iterations=0)

    assert [section.section_type for section in plan.sections] == [
        "abstract",
        "introduction",
        "result",
        "result_2",
        "discussion",
        "conclusion",
    ]
    assert plan.get_section("discussion").section_title == "Discussion"


def test_plan_review_flags_missing_or_merged_conclusion():
    plan = PaperPlan(
        title="Broken Plan",
        sections=[
            SectionPlan(section_type="abstract", section_title="Abstract"),
            SectionPlan(section_type="introduction", section_title="Introduction"),
            SectionPlan(section_type="discussion", section_title="Discussion and Conclusion"),
        ],
    )

    issues = deterministic_plan_review_issues(plan)

    assert any(issue.issue_id == "det-missing-standalone-conclusion" for issue in issues)
    assert any(issue.issue_id == "det-merged-discussion-conclusion-title" for issue in issues)


def test_planner_prompt_policy_requires_dedicated_conclusion():
    repo_root = Path(__file__).resolve().parents[1]
    prompt_text = (repo_root / "src/prompts/planner/step1_structure.txt").read_text(
        encoding="utf-8"
    )
    contract_text = (repo_root / "src/agents/planner_agent/prompt_contracts.py").read_text(
        encoding="utf-8"
    )
    combined = f"{prompt_text}\n{contract_text}"

    assert "Conclusion is optional" not in combined
    assert "may be integrated into Discussion" not in combined
    assert 'Include a dedicated "conclusion" section' in combined
    assert "Do NOT merge the conclusion into Discussion" in combined
