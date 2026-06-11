from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.intake import AUTHOR_INPUT_NEEDED, build_intake_profile, write_intake_profile


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _complete_answers() -> dict:
    return {
        "project": {
            "title_working": "Policy Timing and Firm Investment",
            "field": "finance",
            "target_venue": "jf-jfe",
        },
        "author_declared_design": {
            "design_type": "staggered_did",
            "estimand": "ATT for treated firms around staggered policy adoption",
            "unit_of_observation": "firm-year",
            "sample_scope": "US public firms, 2005-2020",
        },
        "treatment_timing": {
            "treatment_name": "Policy adoption",
            "timing_type": "staggered",
            "anticipation_window": "two years before adoption",
            "event_time_unit": "year",
        },
        "institutional_context": [
            {
                "fact": "Policy adoption occurred at different times across states.",
                "source": "author",
                "confidence": "author_provided",
            }
        ],
        "contribution_statement": "The paper studies how staggered policy adoption affected firm investment.",
        "research_motivation": "The author wants to understand whether policy timing altered investment decisions.",
        "outcome_magnitude_context": [
            {
                "variable": "investment_rate",
                "unit": "percentage points of assets",
                "mean": 0.25,
                "sd": 0.075,
                "meaningful_benchmark": "10% of the sample mean is economically meaningful",
            }
        ],
    }


def test_complete_intake_profile_preserves_author_sources(tmp_path: Path) -> None:
    answers = _write_json(tmp_path / "answers.json", _complete_answers())
    result = build_intake_profile(answers_path=answers)
    profile = result.intake_profile
    assert result.has_hard_blocks is False
    assert profile["author_declared_design"]["declared_by_author"] is True
    assert profile["author_declared_design"]["design_type"] == "staggered_did"
    assert profile["missing_author_inputs"] == []
    assert profile["llm_suggested_prose"] == []
    assert profile["field_sources"]["institutional_context"] == "author_provided"


def test_missing_fields_use_author_input_needed_without_invention(tmp_path: Path) -> None:
    answers = _write_json(
        tmp_path / "answers.json",
        {
            "project": {"title_working": "Untitled DID Project"},
            "author_declared_design": {"design_type": "staggered_did"},
        },
    )
    result = build_intake_profile(answers_path=answers)
    profile = result.intake_profile
    assert result.has_hard_blocks is False
    assert "one-sentence contribution statement" in profile["missing_author_inputs"]
    assert "institutional, historical, or regulatory context" in profile["missing_author_inputs"]
    assert profile["contribution_statement"].startswith(AUTHOR_INPUT_NEEDED)
    assert profile["institutional_context"][0]["fact"].startswith(AUTHOR_INPUT_NEEDED)
    assert profile["field_sources"]["contribution_statement"] == "author_input_needed"


def test_cli_writes_intake_profile_and_author_report(tmp_path: Path) -> None:
    answers = _write_json(tmp_path / "answers.json", _complete_answers())
    out = tmp_path / "intake_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "intake",
            "--answers",
            str(answers),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "intake_profile.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()
    assert (out / "reports" / "internal" / "intake_interview.json").exists()


def test_cli_overrides_spec_values(tmp_path: Path) -> None:
    spec = _write_json(
        tmp_path / "spec.json",
        {
            "project": {"title_working": "Spec Title", "field": "economics", "target_venue": "aer"},
            "contribution_statement": "Spec contribution.",
        },
    )
    answers = _write_json(tmp_path / "answers.json", {"project": {"field": "finance"}})
    out = tmp_path / "out"
    result = write_intake_profile(
        spec_path=spec,
        answers_path=answers,
        target_venue="jf-jfe",
        preferred_contribution="CLI contribution.",
        out_dir=out,
    )
    profile = result.intake_profile
    assert profile["project"]["title_working"] == "Spec Title"
    assert profile["project"]["field"] == "finance"
    assert profile["project"]["target_venue"] == "jf-jfe"
    assert profile["contribution_statement"] == "CLI contribution."


def test_author_asserted_claims_keep_original_status_and_reason(tmp_path: Path) -> None:
    answers = _complete_answers()
    answers["author_asserted_claims"] = [
        {
            "claim": "This policy changed firm investment through credit-supply channels.",
            "original_status": "flag_and_confirm",
            "reason": "Author will provide institutional notes.",
        }
    ]
    result = build_intake_profile(answers_path=_write_json(tmp_path / "answers.json", answers))
    claim = result.intake_profile["author_asserted_claims"][0]
    assert claim["original_status"] == "flag_and_confirm"
    assert claim["author_reason"] == "Author will provide institutional notes."


def test_missing_note_file_is_a_hard_block(tmp_path: Path) -> None:
    answers = _write_json(tmp_path / "answers.json", _complete_answers())
    result = build_intake_profile(answers_path=answers, research_context_path=tmp_path / "missing.md")
    assert result.has_hard_blocks is True
    assert result.status == "failed"
    assert result.issues[0].code == "missing_note_file"
