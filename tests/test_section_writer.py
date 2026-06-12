from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from econpaper.section_writer import WRITING_ORDER, generate_sections, write_sections


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
                    "metadata": {"assertion_type": "mechanism"},
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
    assert "Table 1 reports the main model estimates." in results
    assert "table_main.tex" not in results


def test_results_deduplicate_repeated_event_claims_into_table_appendix_holding(tmp_path: Path) -> None:
    ledger_path = _claim_ledger(tmp_path / "claim_ledger.json")
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["claims"][0]["metadata"] = {"variable": "event_0", "artifact_id": "model_table_model_table_csv"}
    payload["claims"][0]["numeric_slots"].append("n:claim_main_001")
    payload["claims"].insert(
        1,
        {
            "claim_id": "claim_main_dup",
            "claim_type": "main_result",
            "status": "safe",
            "gate_tier": "safe",
            "prose_template": "Duplicate event anchor {{coef:claim_main_dup}}.",
            "numeric_slots": ["coef:claim_main_dup"],
            "evidence_refs": ["ev_dup"],
            "citation_refs": [],
            "gate_reasons": [],
            "reviewer_questions": [],
            "author_override": None,
            "metadata": {"variable": "event_0", "artifact_id": "model_table_steps_01"},
        },
    )
    payload["claims"].append(
        {
            "claim_id": "claim_main_did",
            "claim_type": "main_result",
            "status": "safe",
            "gate_tier": "safe",
            "prose_template": "The DID contrast is {{coef:claim_main_did}}.",
            "numeric_slots": ["coef:claim_main_did", "n:claim_main_did"],
            "evidence_refs": ["ev_did"],
            "citation_refs": [],
            "gate_reasons": [],
            "reviewer_questions": [],
            "author_override": None,
            "metadata": {"variable": "_did_treat_post", "artifact_id": "model_table_model_table_csv"},
        }
    )
    _write_json(ledger_path, payload)

    result = generate_sections(
        claim_ledger_path=ledger_path,
        intake_profile_path=_intake(tmp_path / "intake.json"),
        table_path=tmp_path / "tables" / "table_main.tex",
    )

    results = result.sections["04_results.md"]
    assert "The DID contrast is {{coef:claim_main_did}}." in results
    assert "The estimated coefficient is {{coef:claim_main_001}}" in results
    assert "Duplicate event anchor" not in results
    assert "claim_main_dup" in result.audit["safe_claim_ids_held_for_table_or_appendix"]
    assert result.audit["safe_claim_ids_used"] == ["claim_main_did", "claim_main_001"]


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


def test_missing_data_inputs_render_whole_section_floor(tmp_path: Path) -> None:
    intake_payload = json.loads(_intake(tmp_path / "intake.json").read_text(encoding="utf-8"))
    intake_payload["outcome_magnitude_context"] = []
    intake_payload["author_declared_design"]["sample_scope"] = ""
    intake = _write_json(tmp_path / "intake_missing_data.json", intake_payload)

    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=intake,
    )

    data = result.sections["02_data.md"]
    assert data.startswith("# Data\n\n[AUTHOR_INPUT_NEEDED]: section floor")
    assert "## Missing Inputs" in data
    assert "- sample scope" in data
    assert "- outcome magnitude context with variable, unit, mean, and standard deviation" in data
    assert "The unit of observation is" not in data


def test_artifact_backed_robustness_and_heterogeneity_sections_are_written(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "robustness_grid.csv",
        [
            {"family": "estimator_comparison", "check": "twfe", "status": "ok"},
            {"family": "placebo_timing", "check": "fake timing", "status": "computed"},
        ],
    )
    _write_csv(tmp_path / "placebo_tests.csv", [{"placebo": "fake timing", "status": "computed"}])
    _write_csv(
        tmp_path / "heterogeneity.csv",
        [
            {"dimension": "province_group", "group": "pilot_core", "status": "computed"},
            {"dimension": "baseline_size_group", "group": "large", "status": "skipped_no_treatment_variation"},
        ],
    )

    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=_intake(tmp_path / "intake.json"),
        artifact_dir=tmp_path,
    )

    robustness = result.sections["05_robustness.md"]
    heterogeneity = result.sections["07_heterogeneity.md"]
    assert "[AUTHOR_INPUT_NEEDED]" not in robustness
    assert "Estimator comparison" in robustness
    assert "Placebo timing" in robustness
    assert "verification scaffolding" in robustness
    assert "[AUTHOR_INPUT_NEEDED]" not in heterogeneity
    assert "Province group" in heterogeneity
    assert "Baseline size group" in heterogeneity
    assert "insufficient treatment variation" in heterogeneity


def test_author_asserted_mechanism_gets_labeled_mechanisms_section(tmp_path: Path) -> None:
    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=_intake(tmp_path / "intake.json"),
    )
    mechanisms = result.sections["06_mechanisms.md"]
    results = result.sections["04_results.md"]
    assert "[AUTHOR_INPUT_NEEDED]" not in mechanisms
    assert "author-labeled assertions" in mechanisms
    assert "not as independently verified mechanism evidence" in mechanisms
    assert "author_asserted_001" in mechanisms
    assert "Author framing" in mechanisms
    assert "author_asserted_001" not in results
    assert result.audit["mechanism_assertion_ids_used"] == ["author_asserted_001"]


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


def test_verified_literature_notes_render_as_note_backed_inputs(tmp_path: Path) -> None:
    citation_index = _write_json(
        tmp_path / "citation_index.json",
        {
            "version": "v3.0",
            "citekeys": ["smith2020"],
            "literature_note_entries": [
                {
                    "note_id": "litnote_fixture_01",
                    "citekey": "smith2020",
                    "note": "Author note: provides the closest comparison for policy timing and investment.",
                }
            ],
        },
    )
    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=_intake(tmp_path / "intake.json"),
        citation_index_path=citation_index,
    )

    related = result.sections["10_related_literature_skeleton.md"]
    assert "Note-Backed Positioning Inputs" in related
    assert "closest comparison" in related
    assert "intentionally avoids literature-search prose" not in related


def test_author_section_notes_append_without_becoming_claims(tmp_path: Path) -> None:
    intake_path = _intake(tmp_path / "intake.json")
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    intake["author_provided_notes"] = {
        "section_notes": [
            {
                "section": "01_introduction.md",
                "note_id": "intro_context_001",
                "status": "author_provided",
                "title": "Reader Context",
                "paragraphs": [
                    "Author note: the paper should open by explaining why policy timing matters before naming any coefficient."
                ],
            },
            {
                "section": "04_results.md",
                "note_id": "results_style_001",
                "status": "draft_model_guess",
                "paragraphs": ["This should be ignored."],
            },
        ]
    }
    _write_json(intake_path, intake)

    result = generate_sections(
        claim_ledger_path=_claim_ledger(tmp_path / "claim_ledger.json"),
        intake_profile_path=intake_path,
    )

    intro = result.sections["01_introduction.md"]
    results = result.sections["04_results.md"]
    assert "## Reader Context" in intro
    assert "Author note:" not in intro
    assert "policy timing matters" in intro
    assert "This should be ignored" not in results
    assert result.audit["section_note_ids_available"] == ["intro_context_001"]
    assert result.audit["section_note_ids_used"] == ["intro_context_001"]


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
