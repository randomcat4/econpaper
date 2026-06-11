"""Tests for the econ/finance artifact manifest v1 contract."""
from __future__ import annotations

import pytest

from src.agents.metadata_agent.artifact_manifest import (
    BUNDLE_V2_VERSION,
    MANIFEST_VERSION,
    ArtifactManifestError,
    normalize_artifact_manifest,
)


def test_manifest_version_materials_root_and_empty_artifacts_are_valid(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()
    manifest = {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "source_agent": "local_econ_analysis",
        "figures": [],
        "tables": [],
    }

    normalized = normalize_artifact_manifest(manifest)

    assert normalized.version == MANIFEST_VERSION
    assert normalized.materials_root == root.resolve()
    assert normalized.source_agent == "local_econ_analysis"
    assert normalized.figures == []
    assert normalized.tables == []


def test_manifest_version_must_match(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()
    manifest = {
        "version": 1,
        "materials_root": str(root),
        "figures": [],
        "tables": [],
    }

    with pytest.raises(ArtifactManifestError, match="version"):
        normalize_artifact_manifest(manifest)


def test_manifest_artifacts_require_id_path_section_and_caption(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    manifest = {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "figures": [
            {
                "id": "fig:main",
                "path": "figures/main.pdf",
                "section": "results",
            }
        ],
        "tables": [],
    }

    with pytest.raises(ArtifactManifestError, match="caption"):
        normalize_artifact_manifest(manifest)


def test_manifest_normalizes_artifact_to_absolute_safe_path(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    figure = root / "figures" / "main.pdf"
    figure.write_bytes(b"%PDF-1.4\n")
    manifest = {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "figures": [
            {
                "id": "fig:main",
                "path": "figures/main.pdf",
                "section": "results",
                "caption": "Main estimates.",
                "data_hash": "sha256:data",
                "code_hash": "sha256:code",
            }
        ],
        "tables": [],
    }

    normalized = normalize_artifact_manifest(manifest)

    assert normalized.figures[0].resolved_path == figure.resolve()
    assert normalized.figures[0].latex_path == str(figure.resolve()).replace("\\", "/")
    assert normalized.figures[0].semantic_role == "result_figure"
    assert normalized.figures[0].target_type == "data_visualization"


def test_empirical_result_artifacts_require_data_and_code_hashes(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    manifest = {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "figures": [
            {
                "id": "fig:main",
                "path": "figures/main.pdf",
                "section": "results",
                "caption": "Main estimates.",
                "semantic_role": "result_figure",
                "target_type": "data_visualization",
                "code_hash": "sha256:code",
            }
        ],
        "tables": [],
    }

    with pytest.raises(ArtifactManifestError, match="data_hash"):
        normalize_artifact_manifest(manifest)


def test_non_result_concept_artifact_does_not_require_hashes(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "concept.pdf").write_bytes(b"%PDF-1.4\n")
    manifest = {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "figures": [
            {
                "id": "fig:concept",
                "path": "figures/concept.pdf",
                "section": "introduction",
                "caption": "Conceptual overview.",
                "semantic_role": "conceptual_framework",
                "target_type": "infograph",
            }
        ],
        "tables": [],
    }

    normalized = normalize_artifact_manifest(manifest)

    assert normalized.figures[0].data_hash == ""
    assert normalized.figures[0].code_hash == ""


def test_manifest_v2_normalizes_skill4econ_bundle_fields(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "tables").mkdir(parents=True)
    (root / "figures" / "event.pdf").write_bytes(b"%PDF-1.4\n")
    (root / "tables" / "main.tex").write_text("\\begin{tabular}{lc}A & B\\\\\\end{tabular}\n", encoding="utf-8")
    data_hash = "sha256:" + "a" * 64
    code_hash = "sha256:" + "b" * 64
    manifest = {
        "version": BUNDLE_V2_VERSION,
        "producer": "skill4econ",
        "run_status": "success",
        "claim_level": "estimation_result",
        "materials_root": str(root),
        "allowed_paper_uses": ["results"],
        "forbidden_claims": ["structural_spatial_impact"],
        "diagnostics": [{"code": "ok", "severity": "info"}],
        "files": {
            "figures": [
                {
                    "artifact_id": "fig:event",
                    "path": "figures/event.pdf",
                    "paper_section": "results",
                    "locked_caption": "Event-study estimates.",
                    "role": "result_figure",
                    "data_hash": data_hash,
                    "code_hash": code_hash,
                }
            ],
            "tables": [
                {
                    "artifact_id": "tab:main",
                    "path": "tables/main.tex",
                    "paper_section": "results",
                    "locked_caption": "Main estimates.",
                    "role": "result_table",
                    "data_hash": data_hash,
                    "code_hash": code_hash,
                }
            ],
        },
    }

    normalized = normalize_artifact_manifest(manifest)

    assert normalized.version == BUNDLE_V2_VERSION
    assert normalized.source_agent == "skill4econ"
    assert normalized.run_status == "success"
    assert normalized.claim_level == "estimation_result"
    assert normalized.allowed_paper_uses == ["results"]
    assert normalized.forbidden_claims == ["structural_spatial_impact"]
    assert normalized.figures[0].id == "fig:event"
    assert normalized.figures[0].caption == "Event-study estimates."
    assert normalized.tables[0].id == "tab:main"


def test_manifest_v2_rejects_placeholder_hashes_for_result_artifacts(tmp_path):
    root = tmp_path / "materials"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "event.pdf").write_bytes(b"%PDF-1.4\n")
    manifest = {
        "version": BUNDLE_V2_VERSION,
        "materials_root": str(root),
        "figures": [
            {
                "id": "fig:event",
                "path": "figures/event.pdf",
                "section": "results",
                "caption": "Event-study estimates.",
                "semantic_role": "result_figure",
                "target_type": "data_visualization",
                "data_hash": "sha256:placeholder",
                "code_hash": "sha256:placeholder",
            }
        ],
        "tables": [],
    }

    with pytest.raises(ArtifactManifestError, match="sha256:<64 hex>"):
        normalize_artifact_manifest(manifest)
