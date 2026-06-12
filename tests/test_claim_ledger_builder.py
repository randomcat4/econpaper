from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.claim_ledger import build_claim_ledger, write_claim_ledger
from econpaper.numeric_renderer import render_numeric_template


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _ledger(path: Path, *, magnitude_ready: bool = True) -> Path:
    semantics = (
        {
            "treat": {
                "label": "treat",
                "unit": "percentage points",
                "mean": 0.25,
                "sd": 0.075,
                "source": "intake_profile",
            }
        }
        if magnitude_ready
        else {}
    )
    return _write_json(
        path,
        {
            "version": "v3.0",
            "run_id": "fixture",
            "artifacts": [
                {
                    "artifact_id": "model_table_main",
                    "artifact_type": "model_table",
                    "path": "model_table.csv",
                    "hash": "sha256:fixture",
                    "claimable": True,
                }
            ],
            "variable_semantics": semantics,
            "evidence_items": [
                {
                    "evidence_id": "ev_coef",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "statistic": "coefficient",
                    "value": 0.03,
                    "display_type": "coefficient",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_se",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "statistic": "standard_error",
                    "value": 0.01,
                    "display_type": "standard_error",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_p",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "statistic": "p_value",
                    "value": 0.025,
                    "display_type": "p_value",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_t",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "statistic": "t_stat",
                    "value": 3.0,
                    "display_type": "t_stat",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_n",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "statistic": "n",
                    "value": 1200,
                    "display_type": "n",
                    "variable": "treat",
                },
            ],
        },
    )


def _event_ledger(path: Path) -> Path:
    return _write_json(
        path,
        {
            "version": "v3.0",
            "run_id": "fixture",
            "artifacts": [
                {
                    "artifact_id": "model_table_main",
                    "artifact_type": "model_table",
                    "path": "model_table.csv",
                    "hash": "sha256:fixture",
                    "claimable": True,
                }
            ],
            "variable_semantics": {},
            "evidence_items": [
                {
                    "evidence_id": "ev_event0_coef",
                    "artifact_id": "model_table_main",
                    "model_id": "event_study",
                    "row": "event_0",
                    "statistic": "coefficient",
                    "value": 0.03,
                    "display_type": "coefficient",
                    "variable": "event_0",
                },
                {
                    "evidence_id": "ev_event0_se",
                    "artifact_id": "model_table_main",
                    "model_id": "event_study",
                    "row": "event_0",
                    "statistic": "standard_error",
                    "value": 0.01,
                    "display_type": "standard_error",
                    "variable": "event_0",
                },
            ],
        },
    )


def _event_ledger_with_outcome_semantics(path: Path) -> Path:
    return _write_json(
        path,
        {
            "version": "v3.0",
            "run_id": "fixture",
            "artifacts": [
                {
                    "artifact_id": "model_table_main",
                    "artifact_type": "model_table",
                    "path": "model_table.csv",
                    "hash": "sha256:fixture",
                    "claimable": True,
                }
            ],
            "variable_semantics": {
                "log_y": {
                    "label": "log_y",
                    "unit": "log outcome points",
                    "mean": 1.5,
                    "sd": 0.3,
                    "source": "summary_stats.csv",
                }
            },
            "evidence_items": [
                {
                    "evidence_id": "ev_event0_coef",
                    "artifact_id": "model_table_main",
                    "model_id": "event_study",
                    "row": "event_0",
                    "statistic": "coefficient",
                    "value": 0.06,
                    "display_type": "coefficient",
                    "variable": "event_0",
                },
                {
                    "evidence_id": "ev_event0_se",
                    "artifact_id": "model_table_main",
                    "model_id": "event_study",
                    "row": "event_0",
                    "statistic": "standard_error",
                    "value": 0.01,
                    "display_type": "standard_error",
                    "variable": "event_0",
                },
                {
                    "evidence_id": "ev_event0_p",
                    "artifact_id": "model_table_main",
                    "model_id": "event_study",
                    "row": "event_0",
                    "statistic": "p_value",
                    "value": 0.02,
                    "display_type": "p_value",
                    "variable": "event_0",
                },
            ],
        },
    )


def _intake(path: Path) -> Path:
    return _write_json(
        path,
        {
            "outcome_magnitude_context": [{"variable": "treat", "label": "treatment exposure"}],
            "author_asserted_claims": [
                {
                    "claim_id": "author_asserted_001",
                    "claim": "The author asserts an institutional mechanism.",
                    "assertion_type": "mechanism",
                    "original_status": "flag_and_confirm",
                    "author_reason": "Institutional details are supplied separately.",
                }
            ],
        },
    )


def test_main_result_claim_uses_placeholders_and_slots(tmp_path: Path) -> None:
    result = build_claim_ledger(evidence_ledger_path=_ledger(tmp_path / "ledger.json"), intake_profile_path=_intake(tmp_path / "intake.json"))
    claim = next(claim for claim in result.claim_ledger["claims"] if claim["claim_type"] == "main_result")
    assert result.has_hard_blocks is False
    assert claim["status"] == "safe"
    assert "0.03" not in claim["prose_template"]
    assert "{{coef:claim_main_001}}" in claim["prose_template"]
    assert "{{magnitude:claim_main_001}}" in claim["prose_template"]
    assert result.slot_map["slots"]["coef:claim_main_001"]["evidence_id"] == "ev_coef"
    assert "ev_coef" in claim["evidence_refs"]
    assert "ev_t" in claim["evidence_refs"]


def test_claim_slots_feed_numeric_renderer(tmp_path: Path) -> None:
    out = tmp_path / "claims"
    result = write_claim_ledger(evidence_ledger_path=_ledger(tmp_path / "ledger.json"), out_dir=out)
    claim = next(claim for claim in result.claim_ledger["claims"] if claim["claim_type"] == "main_result")
    template = tmp_path / "template.md"
    template.write_text(claim["prose_template"], encoding="utf-8")
    rendered = render_numeric_template(template, evidence_ledger_path=_ledger(tmp_path / "ledger2.json"), slots_path=out / "slots.json")
    assert rendered.has_hard_blocks is False
    assert "0.030" in rendered.rendered_text
    assert "0.40 standard deviations" in rendered.rendered_text


def test_missing_magnitude_context_flags_claim(tmp_path: Path) -> None:
    result = build_claim_ledger(evidence_ledger_path=_ledger(tmp_path / "ledger.json", magnitude_ready=False))
    claim = result.claim_ledger["claims"][0]
    assert result.has_hard_blocks is False
    assert claim["status"] == "flag_and_confirm"
    assert "magnitude_context_missing" in claim["gate_reasons"]
    assert "AUTHOR_INPUT_NEEDED" in claim["prose_template"]


def test_event_study_label_digits_do_not_trigger_raw_numeric_hard_block(tmp_path: Path) -> None:
    result = build_claim_ledger(evidence_ledger_path=_event_ledger(tmp_path / "event_ledger.json"))
    claim = result.claim_ledger["claims"][0]
    assert result.has_hard_blocks is False
    assert claim["status"] == "flag_and_confirm"
    assert "raw_numeric_template" not in claim["gate_reasons"]
    assert "event 0" not in claim["prose_template"]


def test_event_study_claim_uses_outcome_magnitude_semantics(tmp_path: Path) -> None:
    intake = _write_json(
        tmp_path / "intake.json",
        {
            "variable_registry": [{"name": "log_y", "role": "outcome", "source": "author"}],
            "outcome_magnitude_context": [{"variable": "log_y", "unit": "log outcome points", "mean": 1.5, "sd": 0.3}],
        },
    )
    out = tmp_path / "claims"
    result = write_claim_ledger(
        evidence_ledger_path=_event_ledger_with_outcome_semantics(tmp_path / "event_ledger.json"),
        intake_profile_path=intake,
        out_dir=out,
    )
    claim = result.claim_ledger["claims"][0]
    assert result.has_hard_blocks is False
    assert claim["status"] == "safe"
    assert "magnitude_context_missing" not in claim["gate_reasons"]
    assert claim["metadata"]["variable"] == "event_0"
    assert claim["metadata"]["magnitude_variable"] == "log_y"
    assert result.slot_map["slots"]["magnitude:claim_main_001"]["variable"] == "log_y"

    template = tmp_path / "template.md"
    template.write_text(claim["prose_template"], encoding="utf-8")
    rendered = render_numeric_template(template, evidence_ledger_path=tmp_path / "event_ledger.json", slots_path=out / "slots.json")
    assert rendered.has_hard_blocks is False
    assert "0.20 standard deviations" in rendered.rendered_text


def test_author_override_records_original_status(tmp_path: Path) -> None:
    design = _write_json(tmp_path / "design.json", {"risk_flags": ["twfe_only_for_staggered_did"]})
    overrides = _write_json(
        tmp_path / "overrides.json",
        {"overrides": [{"claim_id": "claim_main_001", "reason": "Author accepts TWFE benchmark wording."}]},
    )
    result = build_claim_ledger(
        evidence_ledger_path=_ledger(tmp_path / "ledger.json"),
        design_profile_path=design,
        author_overrides_path=overrides,
    )
    claim = result.claim_ledger["claims"][0]
    assert claim["status"] == "author_asserted"
    assert claim["author_override"]["original_status"] == "flag_and_confirm"
    assert claim["author_override"]["reason"] == "Author accepts TWFE benchmark wording."


def test_author_asserted_mechanism_preserves_assertion_type(tmp_path: Path) -> None:
    result = build_claim_ledger(evidence_ledger_path=_ledger(tmp_path / "ledger.json"), intake_profile_path=_intake(tmp_path / "intake.json"))
    claim = next(claim for claim in result.claim_ledger["claims"] if claim["claim_id"] == "author_asserted_001")
    assert claim["status"] == "author_asserted"
    assert claim["metadata"]["assertion_type"] == "mechanism"
    assert "author_asserted_mechanism" in claim["gate_reasons"]


def test_missing_citekeys_hard_block_claim_ledger(tmp_path: Path) -> None:
    citation = _write_json(
        tmp_path / "citation_safety.json",
        {"version": "v3.0", "refs_bib_present": True, "citekeys": [], "missing_citekeys": ["missing2025"], "findings": []},
    )
    result = build_claim_ledger(evidence_ledger_path=_ledger(tmp_path / "ledger.json"), citation_safety_report_path=citation)
    assert result.has_hard_blocks is True
    assert "missing_citekeys_in_citation_safety" in {issue.code for issue in result.issues}


def test_mock_run_validation_hard_blocks_claim_ledger(tmp_path: Path) -> None:
    run_validation = _write_json(
        tmp_path / "run_validation.json",
        {"mock_watermark_required": True, "public_watermark": "SMOKE TEST ONLY -- NOT A PAPER DRAFT"},
    )
    result = build_claim_ledger(evidence_ledger_path=_ledger(tmp_path / "ledger.json"), run_validation_path=run_validation)
    assert result.has_hard_blocks is True
    assert "mock_output_not_paper_draft" in {issue.code for issue in result.issues}


def test_missing_evidence_ledger_is_hard_blocked(tmp_path: Path) -> None:
    result = build_claim_ledger(evidence_ledger_path=tmp_path / "missing.json")
    assert result.has_hard_blocks is True
    assert "evidence_ledger_missing" in {issue.code for issue in result.issues}


def test_cli_writes_claim_ledger_slots_and_report(tmp_path: Path) -> None:
    out = tmp_path / "claim_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "claims",
            "--evidence-ledger",
            str(_ledger(tmp_path / "ledger.json")),
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
    assert (out / "claim_ledger.json").exists()
    assert (out / "slots.json").exists()
    assert (out / "reports" / "internal" / "claim_ledger_build.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()
    assert "{{" not in (out / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
