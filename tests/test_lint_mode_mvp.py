from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.linting import run_lint
from econpaper.run_validation import MOCK_WATERMARK


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_dir(root: Path, *, mock_runner: bool = False, evidence_value: float | None = None) -> Path:
    run_dir = root / "run"
    run_dir.mkdir()
    _write_json(
        run_dir / "status.json",
        {
            "status": "success",
            "agent_status": "claimable_success",
            "method_or_workflow": "ols_cluster",
            "engine": "python",
            "run_id": "fixture",
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready",
            "main_claim_available": True,
            "risk_codes": [],
            "run_dir": str(run_dir),
            "rerun_command": "echo rerun",
        },
    )
    _write_json(
        run_dir / "manifest.json",
        {
            "status": "success",
            "method": "ols_cluster",
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready",
            "main_claim_available": True,
        },
    )
    _write_json(run_dir / "audit.json", {"status": "success", "method": "ols_cluster", "mock_runner": mock_runner})
    _write_json(run_dir / "run_config_resolved.json", {"spec": {}, "mock_runner": mock_runner})
    _write_json(run_dir / "validation_report.json", {"status": "passed", "errors": []})
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "workflow": "ols_cluster",
            "run_id": "fixture",
            "status": "success",
            "artifacts": [{"path": "model_table.json", "required": True, "exists": True}],
            "missing_required_artifacts": [],
        },
    )
    if evidence_value is not None:
        _write_json(
            run_dir / "evidence_ledger.json",
            {
                "version": "v3.0",
                "run_id": "fixture",
                "artifacts": [
                    {
                        "artifact_id": "model_table_main",
                        "artifact_type": "model_table",
                        "path": "model_table.json",
                        "hash": "sha256:fixture",
                        "claimable": True,
                    }
                ],
                "variable_semantics": {},
                "evidence_items": [
                    {
                        "evidence_id": "ev_coef_main",
                        "artifact_id": "model_table_main",
                        "model_id": "m1",
                        "statistic": "coefficient",
                        "value": evidence_value,
                        "display_type": "coefficient",
                    }
                ],
            },
        )
    return run_dir


def _refs(path: Path) -> Path:
    refs = path / "refs.bib"
    refs.write_text(
        "@article{smith2020,\n"
        "  title={Fixture Paper},\n"
        "  author={Smith, A.},\n"
        "  year={2020},\n"
        "  journal={Journal}\n"
        "}\n",
        encoding="utf-8",
    )
    return refs


def _codes(report) -> set[str]:
    return {finding.code for finding in report.findings}


def test_lint_cli_exists_and_writes_reports(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.tex"
    draft.write_text("Prior work exists \\citep{smith2020}.", encoding="utf-8")
    out = tmp_path / "lint_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "lint",
            str(draft),
            "--run-dir",
            str(run_dir),
            "--refs",
            str(refs),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "AUTHOR_REPORT.md").exists()
    assert (out / "annotated_draft.tex").exists()
    assert (out / "reports" / "internal" / "lint_report.json").exists()
    assert (out / "reports" / "internal" / "citation_safety_report.json").exists()


def test_missing_citekey_is_non_overridable_hard_block(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.tex"
    draft.write_text("This claim cites absent work \\citep{missing2025}.", encoding="utf-8")
    report = run_lint(draft, run_dir=run_dir, refs_path=refs, out_dir=tmp_path / "out")
    assert report.has_hard_blocks is True
    assert "missing_citekey" in _codes(report)
    finding = next(finding for finding in report.findings if finding.code == "missing_citekey")
    assert finding.overridable is False


def test_cite_needed_marker_does_not_create_fake_citation(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text("Prior work should be added. [CITE_NEEDED: source for institutional background]", encoding="utf-8")
    report = run_lint(draft, run_dir=run_dir, refs_path=refs, out_dir=tmp_path / "out")
    assert report.has_hard_blocks is False
    assert "missing_citekey" not in _codes(report)
    assert report.cite_needed[0]["reason"] == "source for institutional background"
    assert (tmp_path / "out" / "annotated_draft.md").exists()


def test_ledger_inconsistent_number_is_hard_blocked(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, evidence_value=0.03)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.tex"
    draft.write_text("The main coefficient is 0.30 in Table \\ref{tab:main}.", encoding="utf-8")
    report = run_lint(draft, run_dir=run_dir, refs_path=refs, out_dir=tmp_path / "out")
    assert report.has_hard_blocks is True
    assert "ledger_inconsistent_number" in _codes(report)


def test_ledger_matching_number_passes_numeric_gate(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, evidence_value=0.03)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.tex"
    draft.write_text("The main coefficient is 0.03 in Table \\ref{tab:main}.", encoding="utf-8")
    report = run_lint(draft, run_dir=run_dir, refs_path=refs, out_dir=tmp_path / "out")
    assert report.has_hard_blocks is False
    assert "ledger_inconsistent_number" not in _codes(report)


def test_table_and_figure_labels_are_not_treated_as_numeric_claims(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.tex"
    draft.write_text("Table 1 and Figure 2 summarize the descriptive artifacts.", encoding="utf-8")
    report = run_lint(draft, run_dir=run_dir, refs_path=refs, out_dir=tmp_path / "out")
    assert report.has_hard_blocks is False
    assert report.numeric_uses == []


def test_design_and_literature_risk_language_is_flag_and_confirm(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.tex"
    draft.write_text(
        "This is the first paper to identify the causal mechanism, and the results generalize globally.",
        encoding="utf-8",
    )
    report = run_lint(draft, run_dir=run_dir, refs_path=refs, out_dir=tmp_path / "out")
    assert report.has_hard_blocks is False
    assert "causal_language_flag" in _codes(report)
    assert "mechanism_language_flag" in _codes(report)
    assert "external_validity_language_flag" in _codes(report)
    assert "novelty_or_literature_claim_flag" in _codes(report)
    assert {finding.tier for finding in report.findings} == {"flag_and_confirm"}


def test_author_override_records_flagged_claim_without_overriding_hard_blocks(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.tex"
    draft.write_text("This is the first paper to contribute to this literature \\citep{missing2025}.", encoding="utf-8")
    overrides = tmp_path / "overrides.json"
    _write_json(
        overrides,
        {
            "overrides": [
                {"code": "novelty_or_literature_claim_flag", "reason": "Author will supply positioning notes."},
                {"code": "missing_citekey", "reason": "Author wants to keep this citekey."},
            ]
        },
    )
    report = run_lint(
        draft,
        run_dir=run_dir,
        refs_path=refs,
        out_dir=tmp_path / "out",
        author_overrides_path=overrides,
    )
    assert report.has_hard_blocks is True
    missing = next(finding for finding in report.findings if finding.code == "missing_citekey")
    novelty = next(finding for finding in report.findings if finding.code == "novelty_or_literature_claim_flag")
    assert missing.author_override is None
    assert missing.details["override_rejected"] == "This finding is non-overridable."
    assert novelty.tier == "author_asserted"
    assert novelty.author_override is not None


def test_mock_run_watermark_is_visible_in_outputs(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, mock_runner=True)
    refs = _refs(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text("Safe prose with \\citep{smith2020}.", encoding="utf-8")
    out = tmp_path / "out"
    report = run_lint(draft, run_dir=run_dir, refs_path=refs, out_dir=out)
    assert report.has_hard_blocks is True
    assert "run_validation_mock_output_not_paper_draft" in _codes(report)
    assert MOCK_WATERMARK in (out / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert MOCK_WATERMARK in (out / "annotated_draft.md").read_text(encoding="utf-8")
