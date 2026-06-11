from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.design_profiler import build_design_profile, write_design_profile


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _intake(path: Path, design_type: str = "staggered_did") -> Path:
    return _write_json(
        path,
        {
            "author_declared_design": {
                "design_type": design_type,
                "declared_by_author": True,
                "estimand": "ATT around adoption",
                "unit_of_observation": "firm-year",
                "sample_scope": "US firms",
            }
        },
    )


def _evidence(path: Path, artifacts: list[dict] | None = None) -> Path:
    return _write_json(
        path,
        {
            "version": "v3.0",
            "run_id": "fixture",
            "artifacts": artifacts
            if artifacts is not None
            else [
                {"artifact_id": "twfe_model_table", "artifact_type": "model_table", "path": "twfe/model_table.csv", "hash": "sha256:x"},
                {"artifact_id": "event_study_plot", "artifact_type": "figure", "path": "event_study_plot.png", "hash": "sha256:y"},
            ],
            "evidence_items": [],
            "variable_semantics": {},
        },
    )


def test_staggered_did_missing_modern_estimator_is_flag_and_confirm(tmp_path: Path) -> None:
    result = build_design_profile(intake_profile_path=_intake(tmp_path / "intake.json"), evidence_ledger_path=_evidence(tmp_path / "ledger.json"))
    profile = result.design_profile
    assert result.has_hard_blocks is False
    assert profile["declared_by_author"] is True
    assert profile["declared_design_type"] == "staggered_did"
    assert profile["claim_levels"]["causal_language"]["tier"] == "flag_and_confirm"
    assert "modern_staggered_estimator" in profile["diagnostics_missing"]
    assert "Callaway-Sant'Anna" in profile["reviewer_questions"][0]


def test_complete_iv_diagnostics_can_be_safe(tmp_path: Path) -> None:
    artifacts = [
        {"artifact_id": "iv_first_stage", "artifact_type": "model_table", "path": "first_stage.csv", "hash": "sha256:a"},
        {"artifact_id": "weak_iv_diagnostic", "artifact_type": "diagnostic", "path": "weak_iv.json", "hash": "sha256:b"},
        {"artifact_id": "reduced_form_table", "artifact_type": "model_table", "path": "reduced_form.csv", "hash": "sha256:c"},
    ]
    result = build_design_profile(intake_profile_path=_intake(tmp_path / "intake.json", "iv"), evidence_ledger_path=_evidence(tmp_path / "ledger.json", artifacts))
    assert result.design_profile["claim_levels"]["causal_language"]["tier"] == "safe"


def test_mock_run_validation_is_hard_block(tmp_path: Path) -> None:
    run_validation = _write_json(tmp_path / "run_validation.json", {"mock_watermark_required": True})
    result = build_design_profile(
        intake_profile_path=_intake(tmp_path / "intake.json"),
        evidence_ledger_path=_evidence(tmp_path / "ledger.json"),
        run_validation_path=run_validation,
    )
    assert result.has_hard_blocks is True
    assert result.design_profile["hard_blocks"][0]["code"] == "mock_output_not_paper_draft"


def test_author_amendment_records_author_asserted_design_level(tmp_path: Path) -> None:
    amendments = _write_json(tmp_path / "amendments.json", {"author_override": True, "reason": "Author accepts TWFE as benchmark."})
    result = build_design_profile(
        intake_profile_path=_intake(tmp_path / "intake.json"),
        evidence_ledger_path=_evidence(tmp_path / "ledger.json"),
        author_amendments_path=amendments,
    )
    level = result.design_profile["claim_levels"]["causal_language"]
    assert level["tier"] == "author_asserted"
    assert level["author_override"]["original_status"] == "flag_and_confirm"


def test_cli_writes_design_profile_outputs(tmp_path: Path) -> None:
    out = tmp_path / "design_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "design",
            "--intake-profile",
            str(_intake(tmp_path / "intake.json")),
            "--evidence-ledger",
            str(_evidence(tmp_path / "ledger.json")),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "design_profile.json").exists()
    assert (out / "reports" / "internal" / "design_profile.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_missing_intake_profile_is_hard_block(tmp_path: Path) -> None:
    result = build_design_profile(intake_profile_path=tmp_path / "missing.json")
    assert result.has_hard_blocks is True
    assert "intake_profile_missing" in {issue.code for issue in result.issues}
