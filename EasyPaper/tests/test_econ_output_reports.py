"""End-to-end checks for standalone econ runner output reports."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_econ_paper import parse_args, run_econ_paper


ROOT = Path(__file__).resolve().parents[1]
REPORT_KEYS = (
    "claim_gate_report",
    "artifact_usage_report",
    "reviewer_attack_pack_json",
    "reviewer_attack_pack_markdown",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_skill4econ_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "skill4econ_run"
    (run_dir / "figures").mkdir(parents=True)
    (run_dir / "figures" / "event_study_main.pdf").write_bytes(b"%PDF-1.4\n")
    _write_json(
        run_dir / "status.json",
        {
            "status": "success",
            "agent_status": "claimable_success",
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready",
            "main_claim_available": True,
        },
    )
    _write_json(
        run_dir / "manifest.json",
        {
            "status": "success",
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready",
            "main_claim_available": True,
        },
    )
    _write_json(
        run_dir / "artifact_manifest.json",
        {"artifacts": [{"path": "figures/event_study_main.pdf", "type": "figure", "role": "event_study_main"}]},
    )
    _write_json(run_dir / "reviewer_risk.json", {"risks": []})
    (run_dir / "model_table.csv").write_text("term,estimate\nx,1.0\n", encoding="utf-8")
    return run_dir


@pytest.mark.asyncio
async def test_aer_mock_runner_writes_source_backed_output_reports(tmp_path):
    out = tmp_path / "aer_reports"
    skill4econ_run = _make_skill4econ_run(tmp_path)
    args = parse_args(
        [
            "examples/econ/aer_minimal_request.yaml",
            "--out",
            str(out),
            "--mock-llm",
            "--no-pdf",
            "--strict-artifacts",
            "--claim-gate-strict",
            "--skill4econ-run-dir",
            str(skill4econ_run),
        ]
    )

    summary = await run_econ_paper(args, repo_root=ROOT)

    summary_on_disk = _read_json(out / "runner.summary.json")
    for key in REPORT_KEYS:
        assert Path(summary[key]).is_file()
        assert summary_on_disk[key] == summary[key]

    claim_gate = _read_json(out / "claim_gate_report.json")
    assert claim_gate["status"] == "pass"
    assert claim_gate["artifact_evidence_ids"] == ["fig:event_study_main"]
    assert claim_gate["summary"]["claim_count"] >= 4

    artifact_usage = _read_json(out / "artifact_usage_report.json")
    assert artifact_usage["status"] == "pass"
    assert artifact_usage["summary"]["total_artifacts"] == 1
    assert artifact_usage["summary"]["used_artifacts"] == 1
    assert "status.json" in artifact_usage["skill4econ_run_dir"]["files"]
    assert artifact_usage["artifacts"][0]["data_hash"].startswith("sha256:")
    assert artifact_usage["artifacts"][0]["code_hash"].startswith("sha256:")
    assert artifact_usage["artifacts"][0]["used_in_main_tex"] is True

    attack_pack = _read_json(out / "reviewer_attack_pack.json")
    assert attack_pack["status"] == "pass"
    assert attack_pack["reviewer_questions"]
    assert attack_pack["artifacts"][0]["id"] == "fig:event_study_main"

    attack_pack_md = (out / "reviewer_attack_pack.md").read_text(encoding="utf-8")
    assert "# Reviewer Attack Pack: Minimum Wage Pass-Through and Local Employment" in attack_pack_md
    assert "fig:event_study_main" in attack_pack_md
