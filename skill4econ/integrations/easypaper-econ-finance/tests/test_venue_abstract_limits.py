"""Tests for venue-specific abstract word limits in assembly."""
from __future__ import annotations

import re
from typing import Dict

from src.agents.metadata_agent.assembly_helper import assemble_paper


def _assemble(sections: Dict[str, str], venue_config: Dict[str, object]) -> str:
    return assemble_paper(
        title="Venue Paper",
        sections=sections,
        references=[],
        valid_citation_keys=set(),
        escape_latex_fn=lambda text: text,
        fix_latex_references_fn=lambda text: text,
        validate_and_fix_citations_fn=lambda content, *_args, **_kwargs: (
            content,
            [],
            [],
        ),
        venue_config=venue_config,
    )


def _abstract_words(latex: str) -> list[str]:
    match = re.search(r"\\begin\{abstract\}\s*(.*?)\s*\\end\{abstract\}", latex, re.S)
    assert match is not None
    return match.group(1).split()


def test_aer_abstract_is_limited_to_100_words() -> None:
    latex = _assemble(
        {"abstract": " ".join(f"word{i}" for i in range(125))},
        {"name": "american-economic-review", "abstract_limit": 100},
    )

    assert len(_abstract_words(latex)) == 100


def test_jfe_abstract_is_limited_to_100_words() -> None:
    latex = _assemble(
        {"abstract": " ".join(f"finance{i}" for i in range(130))},
        {"name": "journal-of-financial-economics", "abstract_limit": 100},
    )

    assert len(_abstract_words(latex)) == 100


def test_qje_abstract_is_limited_to_250_words() -> None:
    latex = _assemble(
        {"abstract": " ".join(f"econ{i}" for i in range(275))},
        {"name": "quarterly-journal-of-economics", "abstract_limit": 250},
    )

    assert len(_abstract_words(latex)) == 250
