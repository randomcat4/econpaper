from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from econpaper.oneclick import run_oneclick


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


def _raw_data(root: Path) -> Path:
    raw = root / "raw_data"
    _write_csv(raw / "source.csv", [{"county": "001", "year": "2019", "deaths": "12"}])
    return raw


def _intake(path: Path) -> Path:
    return _write_json(
        path,
        {
            "project": {"title_working": "Raw Data Probe", "field": "econometrics", "target_venue": "aea"},
            "author_declared_design": {
                "design_type": "staggered_did",
                "declared_by_author": True,
                "estimand": "ATT for treated counties",
                "unit_of_observation": "county-year",
                "sample_scope": "Public county-year panel",
                "estimator": "Callaway-Sant'Anna ATT(g,t)",
                "fixed_effects": ["county", "year"],
                "cluster_statement": "cluster standard errors at the county level",
            },
            "treatment_timing": {
                "treatment_name": "policy expansion",
                "treatment_variable": "expanded",
                "timing_type": "staggered",
                "event_time_unit": "year",
            },
            "variable_registry": [
                {"name": "mortality_rate", "role": "outcome", "source": "author"},
                {"name": "expanded", "role": "treatment", "source": "author"},
                {"name": "county", "role": "unit_id fixed_effect cluster", "source": "author"},
                {"name": "year", "role": "time fixed_effect", "source": "author"},
            ],
            "institutional_context": [{"fact": "Author-provided context.", "source": "author", "confidence": "author_provided"}],
            "contribution_statement": "The paper studies policy timing and mortality.",
            "research_motivation": "Author motivation.",
            "outcome_magnitude_context": [{"variable": "mortality_rate", "unit": "deaths per 100,000", "mean": 1.0, "sd": 0.2}],
            "field_sources": {
                "author_declared_design.design_type": "author_provided",
                "author_declared_design.estimator": "author_provided",
                "author_declared_design.fixed_effects": "author_provided",
                "author_declared_design.cluster_statement": "author_provided",
                "variable_registry": "author_provided",
                "outcome_magnitude_context": "author_provided",
            },
        },
    )


def _refs(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("@article{fixture2026,title={Fixture},author={Author},year={2026}}\n", encoding="utf-8")
    return path


def test_oneclick_unknown_case_without_custom_inputs_still_reports_available_cases(tmp_path: Path) -> None:
    result = run_oneclick(case_id="not_registered", out_root=tmp_path, require_auth=False)

    assert result.has_hard_blocks is True
    assert result.payload["reason"] == "unknown_case"
    assert "env_carbon_did_aea" in result.payload["available_cases"]


def test_oneclick_custom_raw_data_uses_generic_path_and_fails_closed(tmp_path: Path) -> None:
    result = run_oneclick(
        case_id="raw_probe",
        out_root=tmp_path,
        raw_data_dir=_raw_data(tmp_path),
        intake_profile_path=_intake(tmp_path / "intake.json"),
        refs_path=_refs(tmp_path / "refs.bib"),
        venue="aea",
        latex_command="definitely_missing_pdflatex",
        require_auth=False,
    )

    payload = result.payload
    assert payload["mode"] == "custom_project"
    assert payload["status"] == "failed"
    assert payload.get("reason") != "unknown_case"
    assert Path(payload["input_manifest"]).exists()
    stage_names = [stage["name"] for stage in payload["stages"]]
    assert "validate_run" in stage_names
    assert "evidence" in stage_names
    assert "write" in stage_names
    assert "release_gate" in stage_names
    assert "structured_model_table_missing" in next(stage["issue_codes"] for stage in payload["stages"] if stage["name"] == "evidence")
    assert "run_data_provenance_not_author_supplied" in next(stage["issue_codes"] for stage in payload["stages"] if stage["name"] == "write")


def test_oneclick_cli_custom_raw_data_does_not_require_registered_case(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "oneclick",
            "--case",
            "raw_probe",
            "--raw-data-dir",
            str(_raw_data(tmp_path)),
            "--intake",
            str(_intake(tmp_path / "intake.json")),
            "--refs",
            str(_refs(tmp_path / "refs.bib")),
            "--venue",
            "aea",
            "--latex-command",
            "definitely_missing_pdflatex",
            "--no-auth",
            "--out-root",
            str(tmp_path / "out"),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "custom_project"
    assert payload.get("reason") != "unknown_case"
