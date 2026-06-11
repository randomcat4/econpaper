"""Tests for exporting skill4econ runs into EasyPaper bundles."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agents.metadata_agent.skill4econ_export_bundle import (
    Skill4EconBundleError,
    export_skill4econ_run_bundle,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_run(tmp_path: Path, *, agent_status: str = "claimable_success") -> Path:
    run_dir = tmp_path / "run"
    (run_dir / "figures").mkdir(parents=True)
    (run_dir / "tables").mkdir(parents=True)
    (run_dir / "figures" / "event.pdf").write_bytes(b"%PDF-1.4\n")
    (run_dir / "tables" / "main.tex").write_text(
        "\\begin{tabular}{lc}A & B\\\\\\end{tabular}\n",
        encoding="utf-8",
    )
    _write_json(
        run_dir / "status.json",
        {
            "status": "success",
            "agent_status": agent_status,
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready" if agent_status == "claimable_success" else "not_available",
            "main_claim_available": agent_status == "claimable_success",
        },
    )
    _write_json(
        run_dir / "manifest.json",
        {
            "status": "success",
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready",
            "main_claim_available": agent_status == "claimable_success",
        },
    )
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "artifacts": [
                {"path": "figures/event.pdf", "type": "figure", "role": "dynamic_effect"},
                {"path": "tables/main.tex", "type": "table", "role": "main_result"},
            ],
            "missing_required_artifacts": [],
        },
    )
    _write_json(run_dir / "reviewer_risk.json", {"risks": []})
    (run_dir / "model_table.csv").write_text("term,estimate\nx,1.0\n", encoding="utf-8")
    return run_dir


def test_claimable_skill4econ_run_exports_relative_manifest(tmp_path):
    run_dir = _make_run(tmp_path)
    out = tmp_path / "bundle"

    result = export_skill4econ_run_bundle(run_dir, out, strict=True)

    manifest = json.loads(result.artifact_manifest_path.read_text(encoding="utf-8"))
    assert result.claimable is True
    assert manifest["source_agent"] == "skill4econ"
    assert manifest["materials_root"] == "replication/materials"
    assert len(manifest["figures"]) == 1
    assert len(manifest["tables"]) == 1
    assert manifest["figures"][0]["path"] == "figures/event.pdf"
    assert "://" not in json.dumps(manifest)
    assert "D:/" not in json.dumps(manifest)
    assert "D:\\" not in json.dumps(manifest)
    assert "C:\\" not in json.dumps(manifest)
    assert result.claim_gate_report_path.is_file()
    assert result.reviewer_attack_pack_md_path.is_file()
    assert result.manifest_lock_path.is_file()


def test_blocked_skill4econ_run_exports_reports_without_result_artifacts(tmp_path):
    run_dir = _make_run(tmp_path, agent_status="blocked_missing_dependency")
    out = tmp_path / "bundle"

    result = export_skill4econ_run_bundle(run_dir, out, strict=False)

    manifest = json.loads(result.artifact_manifest_path.read_text(encoding="utf-8"))
    claim_gate = json.loads(result.claim_gate_report_path.read_text(encoding="utf-8"))
    assert result.claimable is False
    assert manifest["figures"] == []
    assert manifest["tables"] == []
    assert claim_gate["claimable"] is False
    assert any("agent_status=blocked_missing_dependency" in block for block in claim_gate["blocks"])


def test_strict_export_rejects_blocked_skill4econ_run(tmp_path):
    run_dir = _make_run(tmp_path, agent_status="blocked_parser_only")

    with pytest.raises(Skill4EconBundleError, match="not paper-claimable"):
        export_skill4econ_run_bundle(run_dir, tmp_path / "bundle", strict=True)
