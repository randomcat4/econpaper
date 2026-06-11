from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.numeric_renderer import render_numeric_template, write_numeric_rendering


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _ledger(path: Path) -> Path:
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
                "investment_rate": {
                    "label": "investment_rate",
                    "unit": "percentage points of assets",
                    "mean": 0.25,
                    "sd": 0.075,
                    "source": "intake_profile",
                }
            },
            "evidence_items": [
                {
                    "evidence_id": "ev_coef",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "statistic": "coefficient",
                    "value": 0.03,
                    "display_type": "coefficient",
                    "variable": "investment_rate",
                },
                {
                    "evidence_id": "ev_se",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "statistic": "standard_error",
                    "value": 0.01,
                    "display_type": "standard_error",
                    "variable": "investment_rate",
                },
                {
                    "evidence_id": "ev_p",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "statistic": "p_value",
                    "value": 0.0004,
                    "display_type": "p_value",
                    "variable": "investment_rate",
                },
                {
                    "evidence_id": "ev_n",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "statistic": "n",
                    "value": 1200,
                    "display_type": "n",
                    "variable": "investment_rate",
                },
            ],
        },
    )


def _slots(path: Path) -> Path:
    return _write_json(
        path,
        {
            "slots": {
                "coef:main": {"evidence_id": "ev_coef"},
                "se:main": {"evidence_id": "ev_se"},
                "pvalue:main": {"evidence_id": "ev_p"},
                "n:sample_primary": {"evidence_id": "ev_n"},
                "magnitude:main": {
                    "coefficient_evidence_id": "ev_coef",
                    "variable": "investment_rate",
                    "kind": "sd_units",
                },
                "magnitude:mean_share": {
                    "coefficient_evidence_id": "ev_coef",
                    "variable": "investment_rate",
                    "kind": "mean_percent",
                },
            }
        },
    )


def test_render_numeric_placeholders_from_evidence_ledger(tmp_path: Path) -> None:
    template = tmp_path / "section.md"
    template.write_text(
        "The estimate is {{coef:main}} (SE {{se:main}}, p={{pvalue:main}}) with N={{n:sample_primary}}.",
        encoding="utf-8",
    )
    result = render_numeric_template(template, evidence_ledger_path=_ledger(tmp_path / "ledger.json"), slots_path=_slots(tmp_path / "slots.json"))
    assert result.has_hard_blocks is False
    assert result.rendered_text == "The estimate is 0.030 (SE 0.010, p=<0.001) with N=1,200."
    assert len(result.audit["resolved_slots"]) == 4


def test_magnitude_slots_render_from_variable_semantics(tmp_path: Path) -> None:
    template = tmp_path / "section.md"
    template.write_text("The coefficient equals {{magnitude:main}}, or {{magnitude:mean_share}}.", encoding="utf-8")
    result = render_numeric_template(template, evidence_ledger_path=_ledger(tmp_path / "ledger.json"), slots_path=_slots(tmp_path / "slots.json"))
    assert result.has_hard_blocks is False
    assert "0.40 standard deviations" in result.rendered_text
    assert "12.0% of the mean" in result.rendered_text


def test_unresolved_placeholder_is_hard_blocked(tmp_path: Path) -> None:
    template = tmp_path / "section.md"
    template.write_text("The estimate is {{coef:missing}}.", encoding="utf-8")
    result = render_numeric_template(template, evidence_ledger_path=_ledger(tmp_path / "ledger.json"), slots_path=_slots(tmp_path / "slots.json"))
    assert result.has_hard_blocks is True
    assert result.issues[0].code == "unresolved_numeric_placeholder"
    assert "{{coef:missing}}" in result.rendered_text


def test_raw_numeric_template_text_is_hard_blocked(tmp_path: Path) -> None:
    template = tmp_path / "section.md"
    template.write_text("The estimate is 0.03 and significant.", encoding="utf-8")
    result = render_numeric_template(template, evidence_ledger_path=_ledger(tmp_path / "ledger.json"), slots_path=_slots(tmp_path / "slots.json"))
    assert result.has_hard_blocks is True
    assert "raw_numeric_text" in {issue.code for issue in result.issues}


def test_slot_statistic_mismatch_is_hard_blocked(tmp_path: Path) -> None:
    template = tmp_path / "section.md"
    template.write_text("The standard error is {{se:wrong}}.", encoding="utf-8")
    slots = _write_json(tmp_path / "slots.json", {"slots": {"se:wrong": {"evidence_id": "ev_coef"}}})
    result = render_numeric_template(template, evidence_ledger_path=_ledger(tmp_path / "ledger.json"), slots_path=slots)
    assert result.has_hard_blocks is True
    assert "slot_statistic_mismatch" in {issue.code for issue in result.issues}


def test_cli_writes_rendered_text_and_audit(tmp_path: Path) -> None:
    template = tmp_path / "section.md"
    template.write_text("The estimate is {{coef:main}}.", encoding="utf-8")
    out = tmp_path / "render_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "render-numbers",
            "--template",
            str(template),
            "--evidence-ledger",
            str(_ledger(tmp_path / "ledger.json")),
            "--slots",
            str(_slots(tmp_path / "slots.json")),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "rendered.md").read_text(encoding="utf-8") == "The estimate is 0.030."
    assert (out / "reports" / "internal" / "numeric_rendering.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_allow_raw_numbers_is_explicit_migration_escape_hatch(tmp_path: Path) -> None:
    template = tmp_path / "section.md"
    template.write_text("The estimate is 0.03.", encoding="utf-8")
    result = write_numeric_rendering(
        template,
        evidence_ledger_path=_ledger(tmp_path / "ledger.json"),
        slots_path=_slots(tmp_path / "slots.json"),
        out_dir=tmp_path / "out",
        allow_raw_numbers=True,
    )
    assert result.has_hard_blocks is False
    assert result.rendered_text == "The estimate is 0.03."
