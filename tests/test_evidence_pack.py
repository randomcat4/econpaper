from __future__ import annotations

import json
from pathlib import Path

from econpaper.claim_ledger import build_claim_ledger
from econpaper.evidence_pack import (
    EVIDENCE_PACK_SCHEMA_VERSION,
    build_evidence_pack,
    load_evidence_pack,
    normalize_artifact_type,
    write_evidence_pack,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _ledger() -> dict:
    return {
        "version": "v3.0",
        "run_id": "fixture",
        "artifacts": [
            {
                "artifact_id": "model_table_main",
                "artifact_type": "model_table",
                "path": "model_table.csv",
                "hash": "sha256:model",
                "claimable": True,
            }
        ],
        "evidence_items": [
            {
                "evidence_id": "ev_coef",
                "artifact_id": "model_table_main",
                "model_id": "m1",
                "row": "treat",
                "column": "coef",
                "statistic": "coefficient",
                "value": 0.03,
                "display_type": "coefficient",
                "variable": "treat",
                "provenance_hash": "sha256:cell",
            }
        ],
        "variable_semantics": {},
    }


def test_build_evidence_pack_normalizes_did_manifest_artifacts() -> None:
    result = build_evidence_pack(
        evidence_ledger=_ledger(),
        artifact_manifest={
            "workflow": "did",
            "run_id": "fixture",
            "artifacts": [
                {"path": "event_study.csv", "type": "table", "role": "dynamic_effect", "exists": True},
                {"path": "pretrend_test.json", "type": "metadata", "exists": True},
                {"path": "figures/manifest.yaml", "type": "metadata", "exists": True},
            ],
        },
        run_validation={"data_provenance": "author_supplied"},
    )

    assert result.has_hard_blocks is False
    assert result.pack["schema_version"] == EVIDENCE_PACK_SCHEMA_VERSION
    artifact_types = {item["artifact_type"] for item in result.pack["artifacts"]}
    assert {"model_table", "event_study", "pretrend_test", "figure_manifest"} <= artifact_types
    assert result.pack["source"]["data_provenance"] == "author_supplied"


def test_write_and_load_evidence_pack_requires_embedded_validation(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "model_table.csv").write_text("term,coef\ntreat,0.03\n", encoding="utf-8")
    result = write_evidence_pack(evidence_ledger=_ledger(), run_dir=run_dir, out_dir=tmp_path / "out")

    loaded = load_evidence_pack(tmp_path / "out" / "evidence_pack.json")

    assert result.has_hard_blocks is False
    assert loaded.has_hard_blocks is False
    assert (tmp_path / "out" / "reports" / "internal" / "evidence_pack_validation.json").exists()


def test_bare_handwritten_evidence_pack_is_not_importable(tmp_path: Path) -> None:
    pack = {
        "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
        "artifacts": [{"artifact_id": "a1", "artifact_type": "model_table", "path": "model_table.csv"}],
        "evidence_items": [],
    }
    _write_json(tmp_path / "evidence_pack.json", pack)

    result = load_evidence_pack(tmp_path / "evidence_pack.json")

    assert result.has_hard_blocks is True
    assert "evidence_pack_validation_missing" in {issue.code for issue in result.issues}


def test_claim_ledger_rejects_adjacent_invalid_evidence_pack(tmp_path: Path) -> None:
    ledger_path = _write_json(tmp_path / "evidence_ledger.json", _ledger())
    _write_json(
        tmp_path / "evidence_pack.json",
        {
            "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
            "artifacts": [{"artifact_id": "model_table_main", "artifact_type": "model_table", "path": "model_table.csv"}],
            "evidence_items": _ledger()["evidence_items"],
        },
    )

    result = build_claim_ledger(evidence_ledger_path=ledger_path)

    assert result.has_hard_blocks is True
    assert "evidence_pack_invalid" in {issue.code for issue in result.issues}


def test_artifact_type_normalization_covers_did_aliases() -> None:
    assert normalize_artifact_type("table", "event_study.csv", "dynamic_effect") == "event_study"
    assert normalize_artifact_type("table", "event_study_support.csv") == "table"
    assert normalize_artifact_type("figure", "event_study_plot.png", "dynamic_effect") == "figure"
    assert normalize_artifact_type("summary_statistics", "summary_statistics.csv") == "summary_stats"
    assert normalize_artifact_type("figure", "figures/manifest.yaml") == "figure_manifest"
