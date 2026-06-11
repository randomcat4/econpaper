"""Tests for basic JFE anonymous manuscript assembly."""
from __future__ import annotations

from src.agents.metadata_agent.assembly_helper import assemble_paper


def test_jfe_anonymous_output_uses_anonymous_author() -> None:
    latex = assemble_paper(
        title="Finance Paper",
        sections={"abstract": "Abstract.", "introduction": "Intro."},
        references=[],
        valid_citation_keys=set(),
        escape_latex_fn=lambda text: text,
        fix_latex_references_fn=lambda text: text,
        validate_and_fix_citations_fn=lambda content, *_args, **_kwargs: (
            content,
            [],
            [],
        ),
        venue_config={"name": "journal-of-financial-economics", "anonymous": True},
    )

    assert r"\author{Anonymous Manuscript}" in latex
    assert r"\author{Author Names}" not in latex
