"""Tests for the standalone economics paper runner."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_econ_paper import parse_args, run_econ_paper
from src.agents.metadata_agent.models import PaperGenerationResult


ROOT = Path(__file__).resolve().parents[1]


def _make_request(tmp_path: Path, *, artifact_section: str = "results", include_manifest: bool = True) -> Path:
    materials = tmp_path / "materials"
    (materials / "figures").mkdir(parents=True)
    (materials / "figures" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "econ-finance-artifact-manifest/v1",
                "materials_root": materials.as_posix(),
                "source_agent": "test",
                "figures": [
                    {
                        "id": "fig:main",
                        "path": "figures/main.pdf",
                        "section": artifact_section,
                        "caption": "Main estimates.",
                        "semantic_role": "result_figure",
                        "target_type": "data_visualization",
                        "data_hash": "sha256:data",
                        "code_hash": "sha256:code",
                    }
                ],
                "tables": [],
            }
        ),
        encoding="utf-8",
    )
    request_lines = [
        'title: "Runner Test Paper"',
        'venue: "american-economic-review"',
        'idea_hypothesis: "Question."',
        'method: "Design."',
        'data: "Panel data."',
        'experiments: "Results."',
        'results: "Main results."',
        'robustness: "Checks."',
        "references: []",
        "target_pages: 5",
        "compile_pdf: false",
    ]
    if include_manifest:
        request_lines.insert(-2, f'figures_manifest: "{manifest.as_posix()}"')
    request = tmp_path / "request.yaml"
    request.write_text(
        "\n".join(request_lines),
        encoding="utf-8",
    )
    return request


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_skill4econ_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "skill4econ_run"
    (run_dir / "figures").mkdir(parents=True)
    (run_dir / "figures" / "main.pdf").write_bytes(b"%PDF-1.4\n")
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
        {"artifacts": [{"path": "figures/main.pdf", "type": "figure", "role": "main_result"}]},
    )
    _write_json(run_dir / "reviewer_risk.json", {"risks": []})
    (run_dir / "model_table.csv").write_text("term,estimate\nx,1.0\n", encoding="utf-8")
    return run_dir


def _read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_run_econ_paper_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "scripts/run_econ_paper.py", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--out" in result.stdout
    assert "--mock-llm" in result.stdout
    assert "--strict-artifacts" in result.stdout
    assert "--claim-gate-strict" in result.stdout
    assert "--skill4econ-run-dir" in result.stdout


@pytest.mark.asyncio
async def test_mock_llm_request_parse_writes_normalized_artifacts(tmp_path):
    request = _make_request(tmp_path)
    out = tmp_path / "out"
    skill_run = _make_skill4econ_run(tmp_path)
    args = parse_args(
        [
            str(request),
            "--out",
            str(out),
            "--mock-llm",
            "--no-pdf",
            "--strict-artifacts",
            "--claim-gate-strict",
            "--skill4econ-run-dir",
            str(skill_run),
        ]
    )

    summary = await run_econ_paper(args, repo_root=ROOT)

    assert Path(summary["main_tex"]).is_file()
    assert (out / "events.jsonl").is_file()
    assert (out / "request.normalized.json").is_file()
    assert (out / "manifest.normalized.json").is_file()
    assert (out / "venue.normalized.json").is_file()
    assert (out / "config.redacted.yaml").is_file()
    assert (out / "claim_gate_report.json").is_file()
    assert (out / "artifact_usage_report.json").is_file()
    assert (out / "reviewer_attack_pack.json").is_file()
    assert (out / "reviewer_attack_pack.md").is_file()
    for key in (
        "claim_gate_report",
        "artifact_usage_report",
        "reviewer_attack_pack_json",
        "reviewer_attack_pack_markdown",
    ):
        assert Path(summary[key]).is_file()
    assert "\\section{Introduction}" in Path(summary["main_tex"]).read_text(encoding="utf-8")
    normalized = json.loads((out / "manifest.normalized.json").read_text(encoding="utf-8"))
    assert normalized["source_agent"] == "skill4econ"
    assert normalized["figures"][0]["section"] == "results"
    assert summary["skill4econ_export"]["claimable"] is True
    artifact_usage = json.loads((out / "artifact_usage_report.json").read_text(encoding="utf-8"))
    assert artifact_usage["status"] == "pass"
    assert artifact_usage["artifacts"][0]["used_in_main_tex"] is True
    assert artifact_usage["skill4econ_run_dir"]["exists"] is True
    claim_gate = json.loads((out / "claim_gate_report.json").read_text(encoding="utf-8"))
    assert claim_gate["status"] == "pass"
    assert claim_gate["summary"]["evidence_artifact_count"] == 1


@pytest.mark.asyncio
async def test_strict_artifacts_rejects_unused_manifest_artifact(tmp_path):
    request = _make_request(tmp_path, artifact_section="appendix")
    out = tmp_path / "out"
    args = parse_args(
        [
            str(request),
            "--out",
            str(out),
            "--mock-llm",
            "--no-pdf",
            "--strict-artifacts",
        ]
    )

    with pytest.raises(ValueError, match="manifest_artifacts_unused_in_main_tex"):
        await run_econ_paper(args, repo_root=ROOT)

    artifact_usage = json.loads((out / "artifact_usage_report.json").read_text(encoding="utf-8"))
    assert artifact_usage["status"] == "fail"
    assert artifact_usage["summary"]["unused_artifacts"] == ["fig:main"]


@pytest.mark.asyncio
async def test_claim_gate_strict_rejects_result_claims_without_artifact_evidence(tmp_path):
    request = _make_request(tmp_path, include_manifest=False)
    out = tmp_path / "out"
    args = parse_args(
        [
            str(request),
            "--out",
            str(out),
            "--mock-llm",
            "--no-pdf",
            "--claim-gate-strict",
        ]
    )

    with pytest.raises(ValueError, match="result_claims_without_artifact_evidence"):
        await run_econ_paper(args, repo_root=ROOT)

    claim_gate = json.loads((out / "claim_gate_report.json").read_text(encoding="utf-8"))
    assert claim_gate["status"] == "fail"
    assert claim_gate["summary"]["evidence_artifact_count"] == 0


@pytest.mark.asyncio
async def test_mock_easypaper_client_generates_events_jsonl(tmp_path):
    request = _make_request(tmp_path)
    out = tmp_path / "out"
    args = parse_args(
        [
            str(request),
            "--out",
            str(out),
            "--model",
            "test-model",
            "--base-url",
            "http://127.0.0.1:9/v1",
            "--api-key",
            "test-key",
            "--no-pdf",
        ]
    )

    class FakeEasyPaper:
        def __init__(self, config):
            self.config = config

        async def generate(self, metadata, **kwargs):
            await kwargs["progress_callback"]({"type": "phase", "message": "fake"})
            main_tex = Path(kwargs["output_dir"]) / "main.tex"
            main_tex.write_text("\\documentclass{article}\n", encoding="utf-8")
            return PaperGenerationResult(
                status="ok",
                paper_title=metadata.title,
                output_path=kwargs["output_dir"],
                latex_content="\\documentclass{article}\n",
            )

    summary = await run_econ_paper(args, client_factory=FakeEasyPaper, repo_root=ROOT)

    assert Path(summary["main_tex"]).is_file()
    events = _read_events(out / "events.jsonl")
    assert [event["type"] for event in events] == [
        "runner_started",
        "phase",
        "runner_completed",
    ]
    redacted = (out / "config.redacted.yaml").read_text(encoding="utf-8")
    assert "test-key" not in redacted
    assert "***REDACTED***" in redacted
