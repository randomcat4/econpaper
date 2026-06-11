"""Tests for preserving content_brief during generation execution."""
from __future__ import annotations

import ast
import inspect
import textwrap

from src.agents.metadata_agent.metadata_agent import MetaDataAgent
from src.agents.metadata_agent.models import PaperMetaData


def _execute_generation_tree() -> ast.AST:
    source = inspect.getsource(MetaDataAgent.execute_generation)
    return ast.parse(textwrap.dedent(source))


def test_execute_generation_rebuilds_document_input_content_brief() -> None:
    source = inspect.getsource(MetaDataAgent.execute_generation)

    assert "self._effective_venue_config(" in source
    assert "metadata.to_document_input(venue_config=venue_config)" in source
    assert "content_brief = document_input.content_brief" in source


def test_execute_generation_passes_content_brief_to_intro_and_body_calls() -> None:
    tree = _execute_generation_tree()
    call_keywords = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {
            "_generate_introduction",
            "_generate_body_section",
        }:
            call_keywords.setdefault(func.attr, set()).update(
                keyword.arg for keyword in node.keywords if keyword.arg
            )

    assert "content_brief" in call_keywords["_generate_introduction"]
    assert "content_brief" in call_keywords["_generate_body_section"]


def test_execute_generation_document_input_preserves_econ_content_brief_fields() -> None:
    agent = MetaDataAgent.__new__(MetaDataAgent)
    agent._skill_registry = None
    metadata = PaperMetaData(
        title="Credit Supply",
        idea_hypothesis="Credit supply shocks matter.",
        method="Legacy method.",
        data="Bank-county panel.",
        experiments="Legacy experiments.",
        venue="aer",
        empirical_strategy="Difference-in-differences with county and year fixed effects.",
        results="Positive pass-through and imprecise employment effects.",
        robustness="Placebo dates and alternative clustering.",
    )

    venue_config = agent._effective_venue_config(
        style_guide=getattr(metadata, "style_guide", None),
        venue=getattr(metadata, "venue", None),
    )
    content_brief = metadata.to_document_input(venue_config=venue_config).content_brief

    assert content_brief["empirical_strategy"] == metadata.empirical_strategy
    assert content_brief["results"] == metadata.results
    assert content_brief["robustness"] == metadata.robustness
