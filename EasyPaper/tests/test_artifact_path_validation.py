"""Path safety tests for file-backed empirical artifact manifests."""
from __future__ import annotations

import pytest

from src.agents.metadata_agent.artifact_manifest import (
    MANIFEST_VERSION,
    ArtifactManifestError,
    normalize_artifact_manifest,
)
from src.agents.metadata_agent.metadata_utils import resolve_direct_metadata_paths, validate_file_paths
from src.agents.metadata_agent.models import FigureSpec, PaperMetaData


def _base_manifest(root, *, figure_path):
    return {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "figures": [
            {
                "id": "fig:main",
                "path": str(figure_path),
                "section": "results",
                "caption": "Main estimates.",
                "semantic_role": "result_figure",
                "target_type": "data_visualization",
                "data_hash": "sha256:data",
                "code_hash": "sha256:code",
            }
        ],
        "tables": [],
    }


def test_relative_path_resolves_inside_materials_root(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "main.pdf").write_bytes(b"%PDF-1.4\n")

    normalized = normalize_artifact_manifest(_base_manifest(root, figure_path="figures/main.pdf"))

    assert normalized.figures[0].path == "figures/main.pdf"


def test_absolute_path_inside_materials_root_is_valid(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    figure = root / "figures" / "main.pdf"
    figure.write_bytes(b"%PDF-1.4\n")

    normalized = normalize_artifact_manifest(_base_manifest(root, figure_path=figure))

    assert normalized.figures[0].resolved_path == figure.resolve()


def test_path_traversal_is_rejected(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()
    (tmp_path / "secret.pdf").write_bytes(b"%PDF-1.4\n")

    with pytest.raises(ArtifactManifestError, match="may not contain"):
        normalize_artifact_manifest(_base_manifest(root, figure_path="../secret.pdf"))


def test_missing_file_is_rejected(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()

    with pytest.raises(ArtifactManifestError, match="does not exist"):
        normalize_artifact_manifest(_base_manifest(root, figure_path="figures/missing.pdf"))


def test_unsupported_extension_is_rejected(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "main.exe").write_bytes(b"MZ")

    with pytest.raises(ArtifactManifestError, match="unsupported extension"):
        normalize_artifact_manifest(_base_manifest(root, figure_path="figures/main.exe"))


def test_space_in_materials_path_smoke(tmp_path):
    root = tmp_path / "materials with space"
    (root / "figures").mkdir(parents=True)
    figure = root / "figures" / "main.pdf"
    figure.write_bytes(b"%PDF-1.4\n")

    normalized = normalize_artifact_manifest(_base_manifest(root, figure_path="figures/main.pdf"))

    assert "materials with space" in normalized.figures[0].latex_path
    assert "\\" not in normalized.figures[0].latex_path


def test_absolute_path_outside_materials_root_is_rejected(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4\n")

    with pytest.raises(ArtifactManifestError, match="escapes materials_root"):
        normalize_artifact_manifest(_base_manifest(root, figure_path=outside))


def test_direct_metadata_absolute_escape_is_rejected(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4\n")
    metadata = PaperMetaData(
        title="Empirical paper",
        idea_hypothesis="Question.",
        method="Design.",
        data="Panel data.",
        experiments="Results.",
        materials_root=str(root),
        figures=[
            FigureSpec(
                id="fig:outside",
                caption="Main estimates.",
                target_type="data_visualization",
                semantic_role="result_figure",
                file_path=str(outside),
            )
        ],
    )

    errors = validate_file_paths(metadata)

    assert errors
    assert "escapes materials_root" in errors[0]


def test_resolve_direct_metadata_paths_rejects_absolute_escape(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("a,b\n1,2\n", encoding="utf-8")
    raw = {
        "materials_root": str(root),
        "tables": [{"id": "tab:outside", "caption": "Outside.", "file_path": str(outside)}],
    }

    with pytest.raises(ValueError, match="escapes materials_root"):
        resolve_direct_metadata_paths(raw, tmp_path, tmp_path)
