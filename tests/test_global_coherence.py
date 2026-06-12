from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.coherence import run_global_coherence, write_global_coherence
from econpaper.section_writer import WRITING_ORDER


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _claim_ledger(path: Path, *, hard_block: bool = False) -> Path:
    return _write_json(
        path,
        {
            "version": "v3.0",
            "status": "failed" if hard_block else "passed",
            "hard_blocks": [{"code": "missing_citekeys_in_citation_safety"}] if hard_block else [],
            "claims": [
                {
                    "claim_id": "claim_main_001",
                    "claim_type": "main_result",
                    "status": "safe",
                    "prose_template": "The estimated coefficient is {{coef:claim_main_001}}.",
                    "gate_reasons": [],
                    "reviewer_questions": [],
                },
                {
                    "claim_id": "claim_design_001",
                    "claim_type": "identification",
                    "status": "flag_and_confirm",
                    "prose_template": "The design identifies a causal effect.",
                    "gate_reasons": ["twfe_only_for_staggered_did"],
                    "reviewer_questions": ["Should modern staggered DID be added?"],
                },
                {
                    "claim_id": "author_asserted_001",
                    "claim_type": "author_asserted",
                    "status": "author_asserted",
                    "prose_template": "The author asserts institutional relevance.",
                    "gate_reasons": ["author_asserted_from_intake"],
                    "reviewer_questions": [],
                },
            ],
        },
    )


def _sections(root: Path, *, abstract_extra: bool = False, dangling_table: bool = False, hedgy: bool = False) -> Path:
    sections_dir = root / "sections"
    sections_dir.mkdir(parents=True)
    for filename in WRITING_ORDER:
        sections_dir.joinpath(filename).write_text(f"# {filename}\n\nPlaceholder.\n", encoding="utf-8")
    sections_dir.joinpath("00_abstract.md").write_text(
        "# Abstract\n\nThe result is {{coef:claim_main_001}}."
        + (" Additional result {{coef:claim_main_999}}." if abstract_extra else "")
        + "\n",
        encoding="utf-8",
    )
    table_line = "Table reference: `tables/table_main.tex`.\n\n" if not dangling_table else "Table reference: `tables/missing.tex`.\n\n"
    sections_dir.joinpath("04_results.md").write_text(
        "# Results\n\n" + table_line + "The result is {{coef:claim_main_001}}.\n",
        encoding="utf-8",
    )
    sections_dir.joinpath("09_conclusion.md").write_text(
        "# Conclusion\n\nThe result is {{coef:claim_main_001}}.\n",
        encoding="utf-8",
    )
    if hedgy:
        sections_dir.joinpath("01_introduction.md").write_text(
            "# Introduction\n\nThis may be useful and might matter; it could be suggestive and appears to travel.\n",
            encoding="utf-8",
        )
    table_dir = root / "tables"
    table_dir.mkdir()
    (table_dir / "table_main.tex").write_text("\\begin{tabular}{cc}\\end{tabular}", encoding="utf-8")
    return sections_dir


def test_global_coherence_passes_and_consolidates_author_report(tmp_path: Path) -> None:
    result = write_global_coherence(
        sections_dir=_sections(tmp_path),
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        out_dir=tmp_path / "out",
    )
    assert result.has_hard_blocks is False
    report = (tmp_path / "out" / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert "## Status Overview" in report
    assert "## Safe Claims" in report
    assert "## Flagged And Downgraded Claims" in report
    assert "## Expected Referee Questions" in report
    assert "{{" not in report
    assert (tmp_path / "out" / "reports" / "internal" / "global_coherence.json").exists()


def test_abstract_placeholder_absent_from_results_is_hard_block(tmp_path: Path) -> None:
    result = run_global_coherence(
        sections_dir=_sections(tmp_path, abstract_extra=True),
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
    )
    assert result.has_hard_blocks is True
    assert "abstract_result_not_in_results" in {finding.code for finding in result.findings}


def test_dangling_table_reference_is_hard_block(tmp_path: Path) -> None:
    result = run_global_coherence(
        sections_dir=_sections(tmp_path, dangling_table=True),
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
    )
    assert result.has_hard_blocks is True
    assert "dangling_table_reference" in {finding.code for finding in result.findings}


def test_hedging_density_is_style_advice_only(tmp_path: Path) -> None:
    result = run_global_coherence(
        sections_dir=_sections(tmp_path, hedgy=True),
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
    )
    assert result.has_hard_blocks is False
    finding = next(finding for finding in result.findings if finding.code == "hedging_density_high")
    assert finding.tier == "style_advice"


def test_missing_required_section_is_hard_block(tmp_path: Path) -> None:
    sections_dir = _sections(tmp_path)
    (sections_dir / "04_results.md").unlink()
    result = run_global_coherence(sections_dir=sections_dir, claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"))
    assert result.has_hard_blocks is True
    assert "required_section_missing" in {finding.code for finding in result.findings}


def test_claim_ledger_hard_block_is_carried_into_author_report(tmp_path: Path) -> None:
    result = write_global_coherence(
        sections_dir=_sections(tmp_path),
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json", hard_block=True),
        out_dir=tmp_path / "out",
    )
    assert result.has_hard_blocks is True
    report = (tmp_path / "out" / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert "claim_ledger_hard_block" in report


def test_cli_writes_global_coherence_outputs(tmp_path: Path) -> None:
    out = tmp_path / "coherence_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "coherence",
            "--sections-dir",
            str(_sections(tmp_path)),
            "--claim-ledger",
            str(_claim_ledger(tmp_path / "claim_ledger.json")),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "reports" / "internal" / "global_coherence.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()
