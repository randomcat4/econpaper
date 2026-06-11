"""Tests for economics and finance section prompt style rules."""
from __future__ import annotations

import pytest

from src.agents.metadata_agent import section_generation
from src.agents.metadata_agent.models import PaperMetaData
from src.agents.metadata_agent.section_generation import (
    append_econ_finance_writing_rules,
    generate_body_section,
)
from src.agents.planner_agent.models import SectionPlan
from src.agents.shared.reference_pool import ReferencePool


def test_econ_prompt_rules_include_econometrics_terms() -> None:
    prompt = append_econ_finance_writing_rules(
        "Base prompt.",
        section_type="empirical_strategy",
        style_guide="journal-of-financial-economics",
    )

    assert "identification" in prompt
    assert "fixed effects" in prompt
    assert "robustness checks" in prompt


def test_econ_prompt_rules_forbid_invented_numeric_results() -> None:
    prompt = append_econ_finance_writing_rules(
        "Base prompt.",
        section_type="results",
        style_guide="american-economic-review",
    )

    assert "Do not invent coefficient magnitudes" in prompt
    assert "p-values" in prompt
    assert "confidence intervals" in prompt


def test_econ_prompt_discourages_ml_terms_without_banning_relevant_usage() -> None:
    prompt = append_econ_finance_writing_rules(
        "Base prompt.",
        section_type="robustness",
        style_guide="quarterly-journal-of-economics",
    )

    assert "Avoid ML paper terms unless explicitly relevant" in prompt
    assert "benchmark, ablation, architecture, pipeline, SOTA, model performance" in prompt


def test_non_econ_prompt_is_unchanged() -> None:
    assert (
        append_econ_finance_writing_rules(
            "Base prompt.",
            section_type="method",
            style_guide="ICML",
        )
        == "Base prompt."
    )


@pytest.mark.asyncio
async def test_generate_body_section_prompt_trace_contains_econ_rules(monkeypatch) -> None:
    def fake_compile_body_section_prompt(**_kwargs):
        return "compiled body prompt"

    async def fake_generate_section_decomposed_fn(**_kwargs):
        return "Generated results content."

    monkeypatch.setattr(
        section_generation,
        "compile_body_section_prompt",
        fake_compile_body_section_prompt,
    )
    prompt_traces = []

    await generate_body_section(
        section_type="results",
        metadata=PaperMetaData(
            title="Bank Lending",
            idea_hypothesis="Credit supply matters.",
            method="Difference-in-differences.",
            data="Bank-county panel.",
            experiments="Main estimates.",
            style_guide="journal-of-financial-economics",
        ),
        intro_context="Intro.",
        contributions=[],
        ref_pool=ReferencePool([]),
        section_plan=SectionPlan(section_type="results", section_title="Results"),
        figures=[],
        tables=[],
        converted_tables={},
        code_context=None,
        research_context=None,
        prompt_traces=prompt_traces,
        memory=None,
        evidence_dag=None,
        template_guide=None,
        emitter=None,
        exemplar_guidance=None,
        tools_config=None,
        retrieve_runtime_code_evidence_fn=lambda **_kwargs: [],
        format_research_context_for_prompt_fn=lambda **_kwargs: "",
        get_active_skills_fn=lambda *_args, **_kwargs: [],
        generate_section_decomposed_fn=fake_generate_section_decomposed_fn,
    )

    assert "Economics/Finance Writing Rules" in prompt_traces[0]["prompt"]
    assert "Results section must distinguish baseline estimates" in prompt_traces[0]["prompt"]
