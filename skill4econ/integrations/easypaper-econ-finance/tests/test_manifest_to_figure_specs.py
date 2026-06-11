"""Adapter tests from artifact manifests into FigureSpec objects."""
from __future__ import annotations

from src.agents.metadata_agent.artifact_manifest import (
    MANIFEST_VERSION,
    manifest_to_figure_specs,
)
from src.agents.metadata_agent.models import PaperGenerationRequest


def test_manifest_result_figure_maps_to_file_backed_figure_spec(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    figure = root / "figures" / "event.pdf"
    figure.write_bytes(b"%PDF-1.4\n")
    manifest = {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "figures": [
            {
                "id": "fig:event",
                "path": "figures/event.pdf",
                "section": "results",
                "caption": "Event-study estimates around the policy date.",
                "semantic_role": "result_figure",
                "target_type": "data_visualization",
                "data_hash": "sha256:data",
                "code_hash": "sha256:code",
            }
        ],
        "tables": [],
    }

    figures = manifest_to_figure_specs(manifest)

    assert len(figures) == 1
    fig = figures[0]
    assert fig.auto_generate is False
    assert fig.file_path == str(figure.resolve()).replace("\\", "/")
    assert fig.derived_file_path == fig.file_path
    assert fig.section_type == "results"
    assert fig.section == "results"
    assert fig.target_type == "data_visualization"
    assert fig.semantic_role == "result_figure"
    assert fig.caption_mode == "locked"
    assert fig.data_hash == "sha256:data"
    assert fig.code_hash == "sha256:code"


def test_paper_generation_request_consumes_figures_manifest(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    figure = root / "figures" / "event.pdf"
    figure.write_bytes(b"%PDF-1.4\n")
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        """
{
  "version": "econ-finance-artifact-manifest/v1",
  "materials_root": "%s",
  "figures": [
    {
      "id": "fig:event",
      "path": "figures/event.pdf",
      "section": "results",
      "caption": "Event-study estimates.",
      "semantic_role": "result_figure",
      "target_type": "data_visualization",
      "data_hash": "sha256:data",
      "code_hash": "sha256:code"
    }
  ],
  "tables": []
}
"""
        % str(root).replace("\\", "\\\\"),
        encoding="utf-8",
    )
    request = PaperGenerationRequest(
        title="Empirical paper",
        idea_hypothesis="Question.",
        method="Design.",
        data="Panel data.",
        experiments="Results.",
        figures_manifest=str(manifest_path),
        venue="american-economic-review",
        results="Main estimates.",
    )

    metadata = request.to_metadata()

    assert metadata.venue == "american-economic-review"
    assert metadata.results == "Main estimates."
    assert metadata.materials_root == str(root.resolve()).replace("\\", "/")
    assert len(metadata.figures) == 1
    assert metadata.figures[0].file_path == str(figure.resolve()).replace("\\", "/")
