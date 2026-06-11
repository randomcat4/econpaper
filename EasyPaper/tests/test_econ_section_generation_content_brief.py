"""Tests for econ/finance section generation from content_brief."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.agents.metadata_agent import section_generation
from src.agents.metadata_agent.models import PaperMetaData
from src.agents.metadata_agent.section_generation import (
    generate_body_section,
    generate_introduction_section,
    resolve_section_content,
)
from src.agents.planner_agent.models import SectionPlan
from src.agents.shared.reference_pool import ReferencePool


def _metadata_without_econ_attrs() -> SimpleNamespace:
    return SimpleNamespace(
        title="Econ paper",
        idea_hypothesis="Legacy idea.",
        method="Legacy method.",
        data="Legacy data.",
        experiments="Legacy experiments.",
        style_guide=None,
    )


def test_empirical_strategy_resolves_from_content_brief_without_metadata_attr() -> None:
    section_plan = SectionPlan(
        section_type="empirical_strategy",
        section_title="Empirical Strategy",
        content_sources=["empirical_strategy", "method", "data"],
    )

    resolved = resolve_section_content(
        "empirical_strategy",
        section_plan,
        _metadata_without_econ_attrs(),
        {"empirical_strategy": "Use lender exposure for identification."},
    )

    assert resolved == {
        "empirical_strategy": "Use lender exposure for identification."
    }


def test_results_and_robustness_resolve_from_content_brief() -> None:
    metadata = _metadata_without_econ_attrs()

    assert resolve_section_content(
        "results",
        SectionPlan(section_type="results", content_sources=["results", "experiments"]),
        metadata,
        {"results": "Main estimates are positive and economically large."},
    ) == {"results": "Main estimates are positive and economically large."}

    assert resolve_section_content(
        "robustness",
        SectionPlan(section_type="robustness", content_sources=["robustness", "results"]),
        metadata,
        {"robustness": "Placebo dates and alternative clustering are stable."},
    ) == {"robustness": "Placebo dates and alternative clustering are stable."}


def test_legacy_method_section_still_uses_metadata_fallback() -> None:
    resolved = resolve_section_content(
        "method",
        SectionPlan(section_type="method", content_sources=["method"]),
        _metadata_without_econ_attrs(),
        content_brief=None,
    )

    assert resolved == {"method": "Legacy method."}


@pytest.mark.asyncio
async def test_generate_body_section_uses_content_brief_in_prompt(monkeypatch) -> None:
    captured = {}

    def fake_compile_body_section_prompt(**kwargs):
        captured.update(kwargs)
        return "compiled body prompt"

    async def fake_generate_section_decomposed_fn(**_kwargs):
        return "Generated body content."

    monkeypatch.setattr(
        section_generation,
        "compile_body_section_prompt",
        fake_compile_body_section_prompt,
    )

    result = await generate_body_section(
        section_type="results",
        metadata=PaperMetaData(
            title="Bank Lending",
            idea_hypothesis="Legacy idea.",
            method="Legacy method.",
            data="Legacy data.",
            experiments="Legacy experiments.",
        ),
        intro_context="Intro.",
        contributions=[],
        ref_pool=ReferencePool([]),
        section_plan=SectionPlan(
            section_type="results",
            section_title="Results",
            content_sources=["results", "experiments"],
        ),
        figures=[],
        tables=[],
        converted_tables={},
        code_context=None,
        research_context=None,
        prompt_traces=[],
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
        content_brief={"results": "Content brief main estimates."},
    )

    assert result.status == "ok"
    assert "Content brief main estimates." in captured["metadata_content"]
    assert "Legacy experiments." not in captured["metadata_content"]


@pytest.mark.asyncio
async def test_generate_introduction_section_uses_content_brief_in_prompt(monkeypatch) -> None:
    captured = {}

    def fake_compile_introduction_prompt(**kwargs):
        captured.update(kwargs)
        return "compiled introduction prompt"

    async def fake_generate_section_decomposed_fn(**_kwargs):
        return "Generated introduction content."

    monkeypatch.setattr(
        section_generation,
        "compile_introduction_prompt",
        fake_compile_introduction_prompt,
    )

    result = await generate_introduction_section(
        metadata=PaperMetaData(
            title="Bank Lending",
            idea_hypothesis="Legacy idea.",
            method="Legacy method.",
            data="Legacy data.",
            experiments="Legacy experiments.",
        ),
        ref_pool=ReferencePool([]),
        section_plan=SectionPlan(section_type="introduction", section_title="Introduction"),
        figures=[],
        tables=[],
        code_context=None,
        research_context=None,
        prompt_traces=[],
        memory=None,
        evidence_dag=None,
        template_guide=None,
        exemplar_guidance=None,
        emitter=None,
        tools_config=None,
        retrieve_runtime_code_evidence_fn=lambda **_kwargs: [],
        format_research_context_for_prompt_fn=lambda **_kwargs: "",
        get_active_skills_fn=lambda *_args, **_kwargs: [],
        generate_section_decomposed_fn=fake_generate_section_decomposed_fn,
        content_brief={"introduction": "Content brief introduction arc."},
    )

    assert result.status == "ok"
    assert captured["idea_hypothesis"] == "Content brief introduction arc."
    assert captured["method_summary"] == "Legacy method."
