from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.table_generator import generate_publication_table, write_publication_table


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
            "variable_semantics": {},
            "evidence_items": [
                {
                    "evidence_id": "ev_m1_coef",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "column": "coef",
                    "statistic": "coefficient",
                    "value": 0.03,
                    "display_type": "coefficient",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_m1_se",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "column": "std_error",
                    "statistic": "standard_error",
                    "value": 0.01,
                    "display_type": "standard_error",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_m1_p",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "column": "p_value",
                    "statistic": "p_value",
                    "value": 0.025,
                    "display_type": "p_value",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_m1_n",
                    "artifact_id": "model_table_main",
                    "model_id": "m1",
                    "row": "treat",
                    "column": "nobs",
                    "statistic": "n",
                    "value": 1200,
                    "display_type": "n",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_m2_coef",
                    "artifact_id": "model_table_main",
                    "model_id": "m2",
                    "row": "treat",
                    "column": "coef",
                    "statistic": "coefficient",
                    "value": 0.04,
                    "display_type": "coefficient",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_m2_se",
                    "artifact_id": "model_table_main",
                    "model_id": "m2",
                    "row": "treat",
                    "column": "std_error",
                    "statistic": "standard_error",
                    "value": 0.011,
                    "display_type": "standard_error",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_m2_p",
                    "artifact_id": "model_table_main",
                    "model_id": "m2",
                    "row": "treat",
                    "column": "p_value",
                    "statistic": "p_value",
                    "value": 0.004,
                    "display_type": "p_value",
                    "variable": "treat",
                },
                {
                    "evidence_id": "ev_m2_n",
                    "artifact_id": "model_table_main",
                    "model_id": "m2",
                    "row": "treat",
                    "column": "nobs",
                    "statistic": "n",
                    "value": 1300,
                    "display_type": "n",
                    "variable": "treat",
                },
            ],
        },
    )


def test_generates_booktabs_and_markdown_from_evidence_cells(tmp_path: Path) -> None:
    result = generate_publication_table(evidence_ledger_path=_ledger(tmp_path / "ledger.json"))
    assert result.has_hard_blocks is False
    assert "\\toprule" in result.latex
    assert "\\bottomrule" in result.latex
    assert "0.030**" in result.latex
    assert "0.040***" in result.latex
    assert "1,200" in result.latex
    assert "| Treat | 0.030** | 0.040*** |" in result.markdown
    assert all(cell["evidence_id"] for cell in result.audit["displayed_cells"])


def test_no_star_policy_removes_stars_and_discloses_note(tmp_path: Path) -> None:
    result = generate_publication_table(evidence_ledger_path=_ledger(tmp_path / "ledger.json"), star_policy="none")
    assert "0.030**" not in result.latex
    assert "0.030" in result.latex
    assert "No significance stars are displayed." in result.latex


def test_variable_labels_fixed_effects_and_cluster_notes(tmp_path: Path) -> None:
    labels = _write_json(tmp_path / "labels.json", {"labels": {"treat": "Treatment exposure"}})
    metadata = _write_json(
        tmp_path / "metadata.json",
        {
            "models": {
                "m1": {"label": "Baseline", "fixed_effects": "Firm and year", "cluster": "firm"},
                "m2": {"label": "Controls", "fixed_effects": "Firm and year", "cluster": "firm"},
            }
        },
    )
    result = generate_publication_table(
        evidence_ledger_path=_ledger(tmp_path / "ledger.json"),
        variable_labels_path=labels,
        model_metadata_path=metadata,
    )
    assert "Treatment exposure" in result.latex
    assert "Baseline" in result.latex
    assert "Fixed effects" in result.latex
    assert "Firm and year" in result.latex
    assert "clustered by firm" in result.latex


def test_non_model_ledger_is_hard_blocked(tmp_path: Path) -> None:
    ledger = _write_json(
        tmp_path / "ledger.json",
        {
            "version": "v3.0",
            "run_id": "fixture",
            "artifacts": [{"artifact_id": "summary", "artifact_type": "summary_stats", "path": "summary.csv", "hash": "sha256:x"}],
            "evidence_items": [],
            "variable_semantics": {},
        },
    )
    result = generate_publication_table(evidence_ledger_path=ledger)
    assert result.has_hard_blocks is True
    assert result.issues[0].code == "no_model_table_evidence"


def test_cli_writes_tex_markdown_and_audit(tmp_path: Path) -> None:
    out = tmp_path / "table_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "tables",
            "--evidence-ledger",
            str(_ledger(tmp_path / "ledger.json")),
            "--out",
            str(out),
            "--caption",
            "Main effect",
            "--label",
            "tab:main",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "tables" / "table_main.tex").exists()
    assert (out / "tables" / "table_main.md").exists()
    assert (out / "reports" / "internal" / "table_generation.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_write_publication_table_records_provenance(tmp_path: Path) -> None:
    result = write_publication_table(evidence_ledger_path=_ledger(tmp_path / "ledger.json"), out_dir=tmp_path / "out")
    coeff_cells = [cell for cell in result.audit["displayed_cells"] if cell["kind"] == "coefficient"]
    assert {cell["evidence_id"] for cell in coeff_cells} == {"ev_m1_coef", "ev_m2_coef"}
