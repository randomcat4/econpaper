"""Tests for QJE total word-count metadata in assembled output."""
from __future__ import annotations

from src.agents.metadata_agent.assembly_helper import assemble_paper


def test_qje_output_includes_total_word_count_line() -> None:
    latex = assemble_paper(
        title="Economics Paper",
        sections={
            "abstract": "Short abstract",
            "introduction": "One two three",
            "conclusion": "Four",
        },
        references=[],
        valid_citation_keys=set(),
        escape_latex_fn=lambda text: text,
        fix_latex_references_fn=lambda text: text,
        validate_and_fix_citations_fn=lambda content, *_args, **_kwargs: (
            content,
            [],
            [],
        ),
        venue_config={
            "name": "quarterly-journal-of-economics",
            "require_total_word_count": True,
        },
    )

    assert r"\noindent\textbf{Total word count:} 6\par" in latex
