from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.section_writer import WRITING_ORDER, generate_sections, write_sections


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _intake(path: Path, *, missing_context: bool = False) -> Path:
    context = [] if missing_context else [{"fact": "Policy adoption varied across states.", "source": "author", "confidence": "author_provided"}]
    return _write_json(
        path,
        {
            "project": {"title_working": "Policy Timing and Firm Investment", "field": "finance", "target_venue": "jf-jfe"},
            "author_declared_design": {
                "design_type": "staggered_did",
                "estimand": "ATT around policy adoption",
                "unit_of_observation": "firm-year",
                "sample_scope": "US public firms, 2005-2020",
            },
            "treatment_timing": {
                "treatment_name": "policy adoption",
                "timing_type": "staggered",
                "anticipation_window": "two years",
                "event_time_unit": "year",
            },
            "institutional_context": context,
            "contribution_statement": "The paper studies how policy timing affected firm investment.",
            "research_motivation": "The author wants to understand whether policy timing changed investment.",
            "outcome_magnitude_context": [
                {"variable": "investment_rate", "unit": "percentage points", "mean": 0.25, "sd": 0.075}
            ],
        },
    )


def _claim_ledger(path: Path, *, failed: bool = False) -> Path:
    return _write_json(
        path,
        {
            "version": "v3.0",
            "status": "failed" if failed else "passed",
            "hard_blocks": [{"code": "mock_output_not_paper_draft"}] if failed else [],
            "claims": [
                {
                    "claim_id": "claim_main_001",
                    "claim_type": "main_result",
                    "status": "safe",
                    "gate_tier": "safe",
                    "prose_template": "The estimated coefficient is {{coef:claim_main_001}} with {{magnitude:claim_main_001}}.",
                    "numeric_slots": ["coef:claim_main_001", "magnitude:claim_main_001"],
                    "evidence_refs": ["ev_coef"],
                    "citation_refs": [],
                    "gate_reasons": [],
                    "reviewer_questions": [],
                    "author_override": None,
                },
                {
                    "claim_id": "claim_design_001",
                    "claim_type": "identification",
                    "status": "flag_and_confirm",
                    "gate_tier": "flag_and_confirm",
                    "prose_template": "The design identifies a causal effect.",
                    "numeric_slots": [],
                    "evidence_refs": [],
                    "citation_refs": [],
                    "gate_reasons": ["twfe_only_for_staggered_did"],
                    "reviewer_questions": ["Confirm design language."],
                    "author_override": None,
                },
                {
                    "claim_id": "author_asserted_001",
                    "claim_type": "author_asserted",
                    "status": "author_asserted",
                    "gate_tier": "author_asserted",
                    "prose_template": "The author asserts institutional relevance.",
                    "numeric_slots": [],
                    "evidence_refs": [],
                    "citation_refs": [],
                    "gate_reasons": ["author_asserted_from_intake"],
                    "reviewer_questions": [],
                    "author_override": {"asserted": True, "original_status": "flag_and_confirm", "reason": "Author note."},
                },
            ],
        },
    )


def test_generates_all_sections_in_v3_writing_order(tmp_path: Path) -> None:
    result = generate_sections(claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"), intake_profile_path=_intake(tmp_path / "intake.json"))
    assert result.has_hard_blocks is False
    assert sorted(result.sections) == sorted(WRITING_ORDER)
    assert result.audit["writing_order"] == WRITING_ORDER
    assert result.audit["safe_claim_ids_used"] == ["claim_main_001"]
    assert result.audit["flagged_claim_ids_not_written_as_verified"] == ["claim_design_001"]


def test_results_use_claim_templates_without_raw_numbers(tmp_path: Path) -> None:
    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=_intake(tmp_path / "intake.json"),
        table_path=tmp_path / "tables" / "table_main.tex",
    )
    results = result.sections["04_results.md"]
    assert "{{coef:claim_main_001}}" in results
    assert "{{magnitude:claim_main_001}}" in results
    assert "0.03" not in results
    assert "claim_design_001" in results
    assert "Table reference" in results


def test_missing_context_and_literature_use_placeholders_not_fake_citations(tmp_path: Path) -> None:
    citation_index = _write_json(tmp_path / "citation_index.json", {"version": "v3.0", "citekeys": []})
    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=_intake(tmp_path / "intake.json", missing_context=True),
        citation_index_path=citation_index,
    )
    intro = result.sections["01_introduction.md"]
    related = result.sections["10_related_literature_skeleton.md"]
    assert "[AUTHOR_INPUT_NEEDED]" in intro
    assert "[CITE_NEEDED:" in related
    assert "\\citep{" not in related


def test_supplied_citekeys_are_listed_without_literature_claims(tmp_path: Path) -> None:
    citation_index = _write_json(tmp_path / "citation_index.json", {"version": "v3.0", "citekeys": ["smith2020"]})
    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=_intake(tmp_path / "intake.json"),
        citation_index_path=citation_index,
    )
    related = result.sections["10_related_literature_skeleton.md"]
    assert "`smith2020`" in related
    assert "Use author-provided notes" in related


def test_failed_claim_ledger_blocks_verified_results(tmp_path: Path) -> None:
    result = generate_sections(claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json", failed=True), intake_profile_path=_intake(tmp_path / "intake.json"))
    assert result.has_hard_blocks is True
    assert "resolve claim-ledger hard blocks" in result.sections["04_results.md"]
    assert "{{coef:claim_main_001}}" not in result.sections["04_results.md"]


def test_cli_writes_section_pack(tmp_path: Path) -> None:
    out = tmp_path / "sections_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "sections",
            "--claim-ledger",
            str(_claim_ledger(tmp_path / "claim_ledger.json")),
            "--intake-profile",
            str(_intake(tmp_path / "intake.json")),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for filename in WRITING_ORDER:
        assert (out / "sections" / filename).exists()
    assert (out / "reports" / "internal" / "section_generation.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_write_sections_author_report_lists_writing_order(tmp_path: Path) -> None:
    result = write_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=_intake(tmp_path / "intake.json"),
        out_dir=tmp_path / "out",
    )
    report = (tmp_path / "out" / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert result.has_hard_blocks is False
    assert "`02_data.md`" in report
    assert "`01_introduction.md`" in report
