"""Adapter tests from artifact manifests into TableSpec objects."""
from __future__ import annotations

from src.agents.metadata_agent.artifact_manifest import (
    MANIFEST_VERSION,
    manifest_to_table_specs,
)


def test_manifest_table_maps_to_file_backed_table_spec(tmp_path):
    root = tmp_path / "materials"
    (root / "tables").mkdir(parents=True)
    table = root / "tables" / "baseline.tex"
    table.write_text("\\begin{tabular}{lc}A & B\\\\\\end{tabular}\n", encoding="utf-8")
    manifest = {
        "version": MANIFEST_VERSION,
        "materials_root": str(root),
        "figures": [],
        "tables": [
            {
                "id": "tab:baseline",
                "path": "tables/baseline.tex",
                "section": "results",
                "caption": "Baseline estimates.",
                "semantic_role": "result_table",
                "data_hash": "sha256:data",
                "code_hash": "sha256:code",
            }
        ],
    }

    tables = manifest_to_table_specs(manifest)

    assert len(tables) == 1
    tbl = tables[0]
    assert tbl.auto_generate is False
    assert tbl.file_path == str(table.resolve()).replace("\\", "/")
    assert tbl.section_type == "results"
    assert tbl.section == "results"
    assert tbl.caption == "Baseline estimates."
    assert tbl.caption_mode == "locked"
    assert tbl.semantic_role == "result_table"
    assert tbl.data_hash == "sha256:data"
    assert tbl.code_hash == "sha256:code"
