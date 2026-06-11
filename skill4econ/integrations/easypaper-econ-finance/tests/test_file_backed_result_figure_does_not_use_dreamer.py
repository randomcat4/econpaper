"""File-backed empirical figures should bypass Dreamer entirely."""
from __future__ import annotations

import pytest

from src.agents.metadata_agent.figure_generation import preprocess_generated_figures
from src.agents.metadata_agent.models import FigureSpec, PaperMetaData


def _metadata(root, figures):
    return PaperMetaData(
        title="Empirical paper",
        idea_hypothesis="Question.",
        method="Design.",
        data="Panel data.",
        experiments="Results.",
        materials_root=str(root),
        figures=figures,
    )


async def _forbidden_generator(**_kwargs):
    raise AssertionError("Dreamer should not be called for file-backed result figures")


@pytest.mark.asyncio
async def test_file_backed_result_figure_keeps_auto_generate_false(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    fig = FigureSpec(
        id="fig:result",
        caption="Main estimates.",
        file_path="figures/main.pdf",
        target_type="data_visualization",
        semantic_role="result_figure",
        auto_generate=True,
    )
    metadata = _metadata(root, [fig])

    await preprocess_generated_figures(
        metadata,
        output_dir=str(tmp_path),
        results_dir=tmp_path,
        generator=_forbidden_generator,
    )

    assert metadata.figures[0].auto_generate is False
    assert metadata.figures[0].file_path == "figures/main.pdf"
