from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from econpaper.compile_pack import compile_pack
from econpaper.venue import resolve_venue
from econpaper.write_pack import write_manuscript_pack


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_csv(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _pack(root: Path) -> Path:
    sections = root / "sections"
    sections.mkdir(parents=True)
    (sections / "00_abstract.md").write_text("# Abstract\n\nRendered abstract.\n", encoding="utf-8")
    (sections / "02_data.md").write_text("# Data\n\nData paragraph.\n", encoding="utf-8")
    (sections / "04_results.md").write_text("# Results\n\nThe estimate is 0.030 and equals 0.40 standard deviations.\n", encoding="utf-8")
    (root / "AUTHOR_REPORT.md").write_text("# AUTHOR_REPORT\n", encoding="utf-8")
    return root


def _valid_run(root: Path) -> Path:
    run = root / "run"
    run.mkdir()
    _write_json(
        run / "status.json",
        {
            "status": "success",
            "agent_status": "claimable_success",
            "method_or_workflow": "ols_cluster",
            "run_id": "fixture",
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready",
            "main_claim_available": True,
        },
    )
    _write_json(run / "manifest.json", {"status": "success", "method": "ols_cluster", "main_claim_available": True})
    _write_json(run / "audit.json", {"status": "success", "method": "ols_cluster"})
    _write_json(run / "run_config_resolved.json", {"spec": {}})
    _write_json(run / "validation_report.json", {"status": "passed"})
    _write_json(
        run / "artifact_manifest.json",
        {
            "workflow": "ols_cluster",
            "run_id": "fixture",
            "status": "success",
            "artifacts": [{"path": "model_table.csv", "type": "model_table", "required": True, "exists": True}],
            "missing_required_artifacts": [],
        },
    )
    _write_csv(run / "model_table.csv", [{"term": "treat", "coef": "0.03", "std_error": "0.01", "p_value": "0.025", "nobs": "1200"}])
    return run


def _intake(path: Path) -> Path:
    return _write_json(
        path,
        {
            "project": {"title_working": "Policy Timing", "field": "finance", "target_venue": "aea"},
            "author_declared_design": {
                "design_type": "ols",
                "declared_by_author": True,
                "estimand": "association between treatment and investment",
                "unit_of_observation": "firm-year",
                "sample_scope": "US public firms",
            },
            "treatment_timing": {"treatment_name": "treat", "timing_type": "cross-sectional"},
            "institutional_context": [{"fact": "Author-provided context.", "source": "author", "confidence": "author_provided"}],
            "contribution_statement": "The paper studies policy timing and investment.",
            "research_motivation": "Author motivation.",
            "outcome_magnitude_context": [{"variable": "treat", "unit": "percentage points", "mean": 0.25, "sd": 0.075}],
        },
    )


def _refs(path: Path) -> Path:
    refs = path / "refs.bib"
    refs.write_text("@article{smith2020,title={Fixture},author={Smith},year={2020}}\n", encoding="utf-8")
    return refs


def test_venue_profiles_are_formatting_only() -> None:
    profile = resolve_venue("aea")
    assert profile.venue_id == "aea"
    assert profile.to_dict()["scope"] == "formatting_and_templates_only"
    assert resolve_venue("unknown").venue_id == "generic-field-journal"


def test_compile_fallback_writes_main_files_and_memo(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    result = compile_pack(pack, venue="aea", latex_command="definitely_missing_pdflatex")
    assert result.status == "fallback"
    assert (pack / "main.md").exists()
    assert (pack / "main.tex").exists()
    assert not (pack / "main.pdf").exists()
    report = (pack / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert "Compile Status" in report
    assert "markdown fallback" in report
    assert "generic_aea_style" in (pack / "main.tex").read_text(encoding="utf-8")


def test_compile_cli_accepts_venue_and_out_dir(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    out = tmp_path / "compiled"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "compile",
            str(pack),
            "--venue",
            "jf-jfe",
            "--out",
            str(out),
            "--latex-command",
            "definitely_missing_pdflatex",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "main.md").exists()
    assert (out / "main.tex").exists()
    assert "generic_finance_style" in (out / "main.tex").read_text(encoding="utf-8")


def test_write_manuscript_pack_generates_core_outputs(tmp_path: Path) -> None:
    out = tmp_path / "manuscript_pack"
    result = write_manuscript_pack(
        run_dir=_valid_run(tmp_path),
        intake_profile_path=_intake(tmp_path / "intake.json"),
        refs_path=_refs(tmp_path),
        venue="aea",
        out_dir=out,
        latex_command="definitely_missing_pdflatex",
    )
    assert result.has_hard_blocks is False
    assert (out / "AUTHOR_REPORT.md").exists()
    assert (out / "main.md").exists()
    assert (out / "main.tex").exists()
    assert (out / "sections" / "04_results.md").exists()
    assert (out / "tables" / "table_main.tex").exists()
    assert (out / "bibliography" / "refs.bib").exists()
    assert (out / "reports" / "internal" / "write_pack_manifest.json").exists()


def test_write_cli_generates_pack(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "write",
            "--run-dir",
            str(_valid_run(tmp_path)),
            "--intake",
            str(_intake(tmp_path / "intake.json")),
            "--refs",
            str(_refs(tmp_path)),
            "--venue",
            "generic-field-journal",
            "--out",
            str(out),
            "--latex-command",
            "definitely_missing_pdflatex",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "main.md").exists()
    assert (out / "reports" / "internal" / "compile_report.json").exists()
