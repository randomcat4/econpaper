from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.release_gate import run_release_gate, write_release_gate


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _pack(root: Path, *, placeholder: bool = False, magnitude: bool = True, author_report: bool = True) -> Path:
    root.mkdir(parents=True)
    if author_report:
        (root / "AUTHOR_REPORT.md").write_text("# AUTHOR_REPORT\n\nReady.\n", encoding="utf-8")
    _write_json(root / "claim_ledger.json", {"version": "v3.0", "status": "passed", "hard_blocks": [], "claims": []})
    _write_json(root / "reports" / "internal" / "global_coherence.json", {"version": "v3.0", "status": "passed", "has_hard_blocks": False})
    sections = root / "sections"
    sections.mkdir()
    text = "The estimate is "
    text += "{{coef:claim_main_001}}" if placeholder else "0.030"
    text += " and equals 0.40 standard deviations." if magnitude else "."
    (sections / "04_results.md").write_text("# Results\n\n" + text + "\n", encoding="utf-8")
    (sections / "00_abstract.md").write_text("# Abstract\n\nRendered abstract.\n", encoding="utf-8")
    return root


def _human_eval(path: Path, *, retention: float = 0.60, time_saved: int = 5, clearer: int = 5, fabrication: bool = False) -> Path:
    evaluations = []
    for idx in range(5):
        evaluations.append(
            {
                "reviewer_role": "economics scholar",
                "generated_text_retention": retention,
                "time_saved": idx < time_saved,
                "silent_fabrication_reported": fabrication and idx == 0,
                "author_report_clearer": idx < clearer,
                "feedback_attached": True,
            }
        )
    return _write_json(path, {"evaluations": evaluations})


def test_release_gate_passes_with_required_human_eval(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is False
    assert result.status == "passed"
    assert result.metrics["human_eval"]["median_generated_text_retention"] == 0.60


def test_missing_human_eval_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"))
    assert result.has_hard_blocks is True
    assert "human_eval_missing" in {finding.code for finding in result.findings}


def test_low_retention_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"), human_eval_path=_human_eval(tmp_path / "human_eval.json", retention=0.40))
    assert result.has_hard_blocks is True
    assert "human_eval_retention_low" in {finding.code for finding in result.findings}


def test_silent_fabrication_report_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"), human_eval_path=_human_eval(tmp_path / "human_eval.json", fabrication=True))
    assert result.has_hard_blocks is True
    assert "human_eval_fabrication_reported" in {finding.code for finding in result.findings}


def test_unrendered_placeholder_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack", placeholder=True), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "unrendered_numeric_placeholder" in {finding.code for finding in result.findings}


def test_missing_results_magnitude_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack", magnitude=False), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "results_magnitude_missing" in {finding.code for finding in result.findings}


def test_missing_author_report_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack", author_report=False), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "author_report_missing" in {finding.code for finding in result.findings}


def test_cli_writes_release_gate_report(tmp_path: Path) -> None:
    out = tmp_path / "release"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "release-gate",
            "--pack-dir",
            str(_pack(tmp_path / "pack")),
            "--human-eval",
            str(_human_eval(tmp_path / "human_eval.json")),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "reports" / "internal" / "release_gate.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_write_release_gate_report_lists_blockers(tmp_path: Path) -> None:
    result = write_release_gate(pack_dir=_pack(tmp_path / "pack", placeholder=True), human_eval_path=_human_eval(tmp_path / "human_eval.json"), out_dir=tmp_path / "out")
    report = (tmp_path / "out" / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert result.has_hard_blocks is True
    assert "unrendered_numeric_placeholder" in report
