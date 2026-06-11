"""Smoke tests for minimal economics and finance request fixtures."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.agents.metadata_agent.artifact_manifest import MANIFEST_VERSION


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_REQUEST_FIELDS = {
    "title",
    "venue",
    "idea_hypothesis",
    "data",
    "empirical_strategy",
    "results",
    "robustness",
    "references",
    "figures_manifest",
    "target_pages",
    "compile_pdf",
}


def _load_request(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def _load_manifest(request: dict) -> dict:
    manifest_path = ROOT / request["figures_manifest"]
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def test_minimal_aer_request_and_manifest_parse() -> None:
    request = _load_request("examples/econ/aer_minimal_request.yaml")

    assert REQUIRED_REQUEST_FIELDS <= set(request)
    assert request["venue"] == "american-economic-review"
    assert request["compile_pdf"] is False

    manifest = _load_manifest(request)
    assert manifest["version"] == MANIFEST_VERSION
    assert manifest["figures"]
    assert manifest["tables"] == []


def test_minimal_jfe_request_and_manifest_parse() -> None:
    request = _load_request("examples/finance/jfe_minimal_request.yaml")

    assert REQUIRED_REQUEST_FIELDS <= set(request)
    assert request["venue"] == "journal-of-financial-economics"
    assert request["compile_pdf"] is False

    manifest = _load_manifest(request)
    assert manifest["version"] == MANIFEST_VERSION
    assert manifest["figures"]
    assert manifest["tables"] == []


def test_minimal_artifact_paths_are_file_backed() -> None:
    for request_path in (
        "examples/econ/aer_minimal_request.yaml",
        "examples/finance/jfe_minimal_request.yaml",
    ):
        request = _load_request(request_path)
        manifest = _load_manifest(request)
        materials_root = (ROOT / manifest["materials_root"]).resolve()
        assert materials_root.is_dir()

        for figure in manifest["figures"]:
            figure_path = (materials_root / figure["path"]).resolve()
            assert str(figure_path).startswith(str(materials_root))
            assert figure_path.is_file()
            assert figure_path.suffix == ".pdf"
            assert figure_path.read_bytes().startswith(b"%PDF-")
