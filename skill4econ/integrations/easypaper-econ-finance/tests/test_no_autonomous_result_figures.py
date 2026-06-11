"""Empirical result figures must never be generated autonomously."""
from __future__ import annotations

import pytest

from src.agents.metadata_agent.figure_generation import (
    FigureGenerationError,
    preprocess_generated_figures,
)
from src.agents.metadata_agent.metadata_utils import validate_file_paths
from src.agents.metadata_agent.models import FigureSpec, PaperMetaData


def _metadata(figures):
    return PaperMetaData(
        title="Empirical paper",
        idea_hypothesis="Question.",
        method="Design.",
        data="Panel data.",
        experiments="Results.",
        figures=figures,
    )


@pytest.mark.asyncio
async def test_result_figure_auto_generate_is_rejected_before_dreamer(tmp_path):
    async def forbidden_generator(**_kwargs):
        raise AssertionError("Dreamer should not be called for result figures")

    metadata = _metadata(
        [
            FigureSpec(
                id="fig:result",
                caption="Main estimates.",
                target_type="data_visualization",
                semantic_role="result_figure",
                auto_generate=True,
            )
        ]
    )

    with pytest.raises(FigureGenerationError, match="forbidden"):
        await preprocess_generated_figures(
            metadata,
            output_dir=str(tmp_path),
            results_dir=tmp_path,
            generator=forbidden_generator,
        )


def test_data_visualization_without_file_path_fails_validation():
    metadata = _metadata(
        [
            FigureSpec(
                id="fig:result",
                caption="Main estimates.",
                target_type="data_visualization",
                auto_generate=False,
            )
        ]
    )

    errors = validate_file_paths(metadata)

    assert errors
    assert "requires file_path" in errors[0]
