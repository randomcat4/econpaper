"""
Guards for migrating internal revision execution off WriterAgent.run().
"""
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class _MemoryWithPlan:
    def __init__(self, plan):
        self.plan = plan

    def get_revision_context(self, section_type):
        return ""

    def get_issue_context(self, limit=20):
        return {"unresolved_issues": []}


def test_revision_executor_does_not_call_writer_run():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor

    source = inspect.getsource(RevisionExecutor)
    assert "._writer.run(" not in source, (
        "RevisionExecutor must not depend on the deprecated WriterAgent.run() "
        "path after migration."
    )


def test_revision_executor_uses_direct_rewrite_helper():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor

    source = inspect.getsource(RevisionExecutor)
    assert "._writer.rewrite_content(" in source, (
        "RevisionExecutor should use WriterAgent.rewrite_content() for "
        "internal revision flows."
    )


def test_metadata_agent_no_longer_keeps_revision_delegation_stubs():
    from src.agents.metadata_agent.metadata_agent import MetaDataAgent

    removed_methods = {
        "_apply_revisions",
        "_revise_section_paragraphs",
        "_revise_section_sentences",
        "_get_sections_fingerprint",
        "_call_reviewer",
        "_revise_section",
        "_revise_paragraph",
        "_build_typesetter_feedback",
        "_merge_section_feedbacks",
        "_resolve_section_feedbacks",
        "_run_review_orchestration",
        "_create_paper_plan",
        "_perform_baseline_gap_audit",
        "_llm_plan_revision_tasks",
        "_apply_revision_plan_to_feedbacks",
        "_run_semantic_consistency_guard",
        "_translate_vlm_to_revision_plan",
        "_resolve_conflicts_with_llm",
        "_build_vlm_feedback",
        "_build_vlm_revision_prompt",
        "_estimate_section_space",
        "_plan_overflow_strategy",
        "_resize_figures_in_section",
        "_move_figures_to_appendix",
        "_create_appendix_section",
        "_execute_structural_actions",
        "_save_artifact",
        "_ensure_export_directories",
        "_write_json_file",
        "_export_plan_artifacts",
        "_export_generation_core_artifacts",
        "_write_text_file",
        "_build_structure_summary",
        "_export_analysis_artifacts",
        "_export_trace_artifacts",
        "_export_artifacts_manifest",
        "_save_compilation_output",
        "_collect_section_citation_budget_usage",
        "_upsert_section_budget_usage",
        "_build_citation_plan_alignment_stats",
        "_build_structure_alignment_stats",
        "_build_paragraph_feedback_alignment_report",
        "_rebuild_citation_budget_usage_from_final_sections",
        "_build_reviewer_acceptance_stats",
        "_build_citation_repair_stats",
        "_build_explicit_subsection_coverage",
    }
    for name in removed_methods:
        assert not hasattr(MetaDataAgent, name), (
            f"MetaDataAgent should not keep pass-through delegation stub {name} "
            "after helper extraction."
        )
    assert not hasattr(MetaDataAgent, "LATEX_ERROR_FIXES"), (
        "MetaDataAgent should not mirror LATEX_ERROR_FIXES after conflict-resolver extraction."
    )


@pytest.mark.asyncio
async def test_revise_section_uses_rewrite_content_and_returns_text():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor

    host = SimpleNamespace(
        _writer=SimpleNamespace(rewrite_content=AsyncMock(return_value="Revised section text.")),
    )
    executor = RevisionExecutor(host)

    revised = await executor._revise_section(
        section_type="method",
        current_content="Original section text.",
        revision_prompt="Improve clarity.",
        metadata=None,
    )

    assert revised == "Revised section text."
    host._writer.rewrite_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_revise_paragraph_uses_rewrite_content_and_returns_text():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor

    host = SimpleNamespace(
        _writer=SimpleNamespace(rewrite_content=AsyncMock(return_value="Revised paragraph text.")),
    )
    executor = RevisionExecutor(host)

    revised = await executor._revise_paragraph(
        section_type="result",
        paragraph_index=2,
        paragraph_text="Original paragraph text.",
        instruction="Tighten the claim.",
    )

    assert revised == "Revised paragraph text."
    host._writer.rewrite_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_revise_section_sentences_rewrites_target_sentence_only():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor

    host = SimpleNamespace(
        _writer=SimpleNamespace(rewrite_content=AsyncMock(return_value="Revised second sentence.")),
    )
    executor = RevisionExecutor(host)

    revised = await executor._revise_section_sentences(
        section_type="discussion",
        current_content="First sentence. Second sentence. Third sentence.",
        sentence_feedbacks=[
            {
                "paragraph_index": 0,
                "sentence_index": 1,
                "issue": "Too vague",
                "suggestion": "Make the claim concrete",
            }
        ],
        metadata=None,
    )

    assert revised == "First sentence. Revised second sentence. Third sentence."
    host._writer.rewrite_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_revise_section_returns_none_when_rewrite_is_empty():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor

    host = SimpleNamespace(
        _writer=SimpleNamespace(rewrite_content=AsyncMock(return_value="")),
    )
    executor = RevisionExecutor(host)

    revised = await executor._revise_section(
        section_type="method",
        current_content="Original section text.",
        revision_prompt="Improve clarity.",
        metadata=None,
    )

    assert revised is None


@pytest.mark.asyncio
async def test_revise_section_leads_writer_with_planned_presentation_contract():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor
    from src.agents.planner_agent.models import (
        PaperPlan,
        ParagraphPlan,
        ParagraphPresentation,
        SectionPlan,
    )

    plan = PaperPlan(sections=[
        SectionPlan(
            section_type="introduction",
            paragraphs=[
                ParagraphPlan(
                    key_point="Summarize contributions",
                    presentation=ParagraphPresentation(
                        mode="prose_with_list",
                        list_label="The contributions are:",
                        list_items=["A modular method", "A strong evaluation"],
                    ),
                )
            ],
        )
    ])
    host = SimpleNamespace(
        _writer=SimpleNamespace(rewrite_content=AsyncMock(return_value="Revised section text.")),
    )
    executor = RevisionExecutor(host)

    await executor._revise_section(
        section_type="introduction",
        current_content="Original section text.",
        revision_prompt="Improve clarity.",
        metadata=None,
        memory=_MemoryWithPlan(plan),
    )

    user_prompt = host._writer.rewrite_content.await_args.kwargs["user_prompt"]
    assert "Planned presentation contract:" in user_prompt
    assert "prose_with_list paragraph is still prose-framed" in user_prompt
    assert "Do not flatten planned itemized contribution/key-point lists" in user_prompt
    assert "Terminal list: do not add prose after \\end{itemize}" in user_prompt
    assert "A modular method" in user_prompt


@pytest.mark.asyncio
async def test_apply_revisions_rejects_revision_that_drops_planned_itemize():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor
    from src.agents.planner_agent.models import (
        PaperPlan,
        ParagraphPlan,
        ParagraphPresentation,
        SectionPlan,
    )
    from src.agents.reviewer_agent.models import ReviewResult, SectionFeedback, SemanticCheckRecord

    before = (
        "The primary contributions are:\n"
        "\\begin{itemize}\n"
        "\\item A modular method.\n"
        "\\item A strong evaluation.\n"
        "\\end{itemize}\n"
        "We next summarize the paper."
    )
    plan = PaperPlan(sections=[
        SectionPlan(
            section_type="introduction",
            paragraphs=[
                ParagraphPlan(
                    key_point="Summarize contributions",
                    presentation=ParagraphPresentation(
                        mode="prose_with_list",
                        list_items=["A modular method", "A strong evaluation"],
                    ),
                )
            ],
        )
    ])
    host = SimpleNamespace(
        _writer=SimpleNamespace(
            rewrite_content=AsyncMock(return_value="The primary contributions are a method and evaluation.")
        ),
        _fix_latex_references=lambda text: text,
        _validate_and_fix_citations=lambda text, keys, remove_invalid=True: (text, [], []),
    )
    executor = RevisionExecutor(host)
    executor._run_semantic_consistency_guard = AsyncMock(
        return_value=SemanticCheckRecord(section_type="introduction", passed=True)
    )
    review_result = ReviewResult(
        passed=False,
        section_feedbacks=[
            SectionFeedback(
                section_type="introduction",
                current_word_count=20,
                target_word_count=20,
                action="revise",
                delta_words=0,
                revision_prompt="Tighten the prose.",
            )
        ],
    )
    generated_sections = {"introduction": before}
    sections_results = [
        SimpleNamespace(section_type="introduction", latex_content=before, word_count=len(before.split()))
    ]
    decision_trace = []

    revised = await executor._apply_revisions(
        review_result=review_result,
        generated_sections=generated_sections,
        sections_results=sections_results,
        valid_citation_keys=set(),
        metadata=None,
        memory=_MemoryWithPlan(plan),
        decision_trace=decision_trace,
    )

    assert revised == set()
    assert generated_sections["introduction"] == before
    assert sections_results[0].latex_content == before
    assert decision_trace[-1]["decision"] == "keep_original_after_presentation_contract_regression"


def test_presentation_contract_rejects_prose_after_terminal_contribution_list():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor
    from src.agents.planner_agent.models import (
        ParagraphPlan,
        ParagraphPresentation,
        SectionPlan,
    )

    section_plan = SectionPlan(
        section_type="introduction",
        paragraphs=[
            ParagraphPlan(
                key_point="Summarize contributions",
                role="conclusion",
                presentation=ParagraphPresentation(
                    mode="prose_with_list",
                    list_items=["A modular method", "A strong evaluation"],
                ),
            )
        ],
    )
    revised = (
        "Our contributions are:\n"
        "\\begin{itemize}\n"
        "\\item A modular method.\n"
        "\\item A strong evaluation.\n"
        "\\end{itemize}\n"
        "We next describe the rest of the paper."
    )

    ok, reason = RevisionExecutor._preserves_presentation_contract(
        "introduction",
        revised,
        section_plan,
    )

    assert ok is False
    assert "terminal itemize" in reason


def test_presentation_contract_allows_later_separate_paragraph_after_terminal_list():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor
    from src.agents.planner_agent.models import (
        ParagraphPlan,
        ParagraphPresentation,
        SectionPlan,
    )

    section_plan = SectionPlan(
        section_type="introduction",
        paragraphs=[
            ParagraphPlan(
                key_point="Summarize contributions",
                role="conclusion",
                presentation=ParagraphPresentation(
                    mode="prose_with_list",
                    list_items=["A modular method", "A strong evaluation"],
                ),
            )
        ],
    )
    revised = (
        "Our contributions are:\n"
        "\\begin{itemize}\n"
        "\\item A modular method.\n"
        "\\item A strong evaluation.\n"
        "\\end{itemize}\n\n"
        "The rest of the introduction provides a separate roadmap paragraph."
    )

    ok, reason = RevisionExecutor._preserves_presentation_contract(
        "introduction",
        revised,
        section_plan,
    )

    assert ok is True
    assert reason == ""


def test_terminal_contract_does_not_reject_nonterminal_intro_list_closing():
    from src.agents.metadata_agent.revision_executor import RevisionExecutor
    from src.agents.planner_agent.models import (
        ParagraphPlan,
        ParagraphPresentation,
        SectionPlan,
    )

    section_plan = SectionPlan(
        section_type="introduction",
        paragraphs=[
            ParagraphPlan(
                key_point="Compare problem settings.",
                role="analysis",
                presentation=ParagraphPresentation(
                    mode="prose_with_list",
                    list_items=["Setting A", "Setting B"],
                ),
            ),
            ParagraphPlan(
                key_point="Summarize contributions.",
                role="conclusion",
                presentation=ParagraphPresentation(
                    mode="prose_with_list",
                    list_items=["A modular method", "A strong evaluation"],
                ),
            ),
        ],
    )
    revised = (
        "The settings differ as follows:\n"
        "\\begin{itemize}\n"
        "\\item Setting A.\n"
        "\\item Setting B.\n"
        "\\end{itemize}\n"
        "These settings motivate the method.\n\n"
        "Our contributions are:\n"
        "\\begin{itemize}\n"
        "\\item A modular method.\n"
        "\\item A strong evaluation.\n"
        "\\end{itemize}"
    )

    ok, reason = RevisionExecutor._preserves_presentation_contract(
        "introduction",
        revised,
        section_plan,
    )

    assert ok is True
    assert reason == ""
