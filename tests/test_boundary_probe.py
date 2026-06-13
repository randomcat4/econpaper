from __future__ import annotations

import json
import subprocess
from pathlib import Path

from econpaper.search.boundary_probe import run_boundary_probe


def _auth_payload() -> dict:
    return {
        "subscriptions": {
            "codex": {
                "configured": True,
                "cli_path": r"C:\real\codex.exe",
            }
        }
    }


def _final_payload() -> dict:
    return {
        "trial_id": "mixed_arxiv_local_30",
        "conditions": ["test condition"],
        "selected_papers": [
            {
                "slot": 1,
                "source_type": "arxiv",
                "title": "Carbon Policy and Machine Learning Forecasts",
                "identifier": "arXiv:2401.00001",
                "language": "en",
                "local_path": "",
                "url": "https://arxiv.org/abs/2401.00001",
                "reason_selected": "open English preprint",
            }
        ],
        "attempts": [
            {
                "paper_slot": 1,
                "action": "direct_pdf_access",
                "method": "http_get",
                "target": "https://arxiv.org/pdf/2401.00001",
                "outcome": "succeeded",
                "evidence": "PDF endpoint returned bytes",
                "http_status": 200,
                "content_type": "application/pdf",
                "bytes_read": 4096,
                "artifact_created": False,
                "boundary": "legal OA direct PDF reachable",
            }
        ],
        "aggregate": {
            "papers_selected": 1,
            "arxiv_count": 1,
            "local_pdf_count": 0,
            "metadata_obtained_count": 1,
            "pdf_obtained_count": 1,
            "text_extracted_count": 0,
            "login_required_count": 0,
            "paywall_count": 0,
            "captcha_count": 0,
            "no_login_boundary_summary": "arXiv works without login in this fixture",
        },
        "capability_boundaries": ["publisher login was not tested in fixture"],
        "recommendations": ["keep raw child outputs"],
    }


def test_boundary_probe_invokes_external_codex_and_records_outputs(tmp_path: Path) -> None:
    local_dir = tmp_path / "pdfs"
    local_dir.mkdir()
    (local_dir / "中文论文.pdf").write_bytes(b"%PDF-1.4")
    captured: dict[str, object] = {}

    def fake_runner(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        final_path = Path(cmd[cmd.index("-o") + 1])
        final_path.write_text(json.dumps(_final_payload(), ensure_ascii=False), encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="child ok", stderr="")

    result = run_boundary_probe(
        out_dir=tmp_path / "out",
        local_pdf_dir=local_dir,
        trials=1,
        papers_per_trial=1,
        command_runner=fake_runner,
        subscription_checker=_auth_payload,
    )
    assert not result.has_hard_blocks
    assert result.codex_cli == r"C:\real\codex.exe"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--search" in cmd and "exec" in cmd
    assert (tmp_path / "out" / "boundary_probe_output_schema.json").exists()
    report = json.loads((tmp_path / "out" / "reports" / "internal" / "boundary_probe_report.json").read_text(encoding="utf-8"))
    assert report["trials"][0]["parsed_final"]["aggregate"]["pdf_obtained_count"] == 1


def test_boundary_probe_hard_blocks_without_codex_auth(tmp_path: Path) -> None:
    result = run_boundary_probe(
        out_dir=tmp_path / "out",
        trials=1,
        papers_per_trial=1,
        subscription_checker=lambda: {"subscriptions": {"codex": {"configured": False}}},
    )
    assert result.has_hard_blocks
    assert "subscription_auth_missing" in {issue.code for issue in result.issues}


def test_boundary_probe_records_child_timeout(tmp_path: Path) -> None:
    def timeout_runner(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, timeout, output="", stderr="still running")

    result = run_boundary_probe(
        out_dir=tmp_path / "out",
        trials=3,
        papers_per_trial=1,
        trial_ids=["no_login_access_boundary"],
        command_runner=timeout_runner,
        subscription_checker=_auth_payload,
    )
    assert result.has_hard_blocks
    assert "codex_child_timeout" in {issue.code for issue in result.issues}
    assert result.trials[0]["trial_id"] == "no_login_access_boundary"
    raw_path = Path(result.trials[0]["raw_path"])
    assert "TIMEOUT" in raw_path.read_text(encoding="utf-8")
