"""Locked captions preserve empirical artifact facts."""
from __future__ import annotations

import re
from types import SimpleNamespace

from src.agents.metadata_agent.compile_support import ensure_figures_defined
from src.agents.metadata_agent.models import FigureSpec


def _section(section_type, figure_ids):
    return SimpleNamespace(
        section_type=section_type,
        get_figure_ids_to_define=lambda: figure_ids,
    )


def test_result_figure_caption_defaults_locked_and_injects_manifest_caption():
    fig = FigureSpec(
        id="fig:event",
        caption="Event-study estimates around the policy date.",
        file_path="/tmp/event.pdf",
        target_type="data_visualization",
        semantic_role="result_figure",
        section_type="results",
    )
    paper_plan = SimpleNamespace(sections=[_section("results", ["fig:event"])], wide_figures=[])

    sections = ensure_figures_defined(
        generated_sections={"results": "Results appear in Figure~\\ref{fig:event}."},
        paper_plan=paper_plan,
        figures=[fig],
    )

    caption = re.search(r"\\caption\{([^}]*)\}", sections["results"]).group(1)
    assert fig.caption_mode == "locked"
    assert caption == "Event-study estimates around the policy date."
    assert not re.search(r"\d", caption)
    assert "significant" not in caption.lower()
