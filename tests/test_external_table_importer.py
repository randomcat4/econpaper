from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from econpaper.evidence import build_evidence_ledger
from econpaper.external_table_importer import import_external_table, write_external_table_import


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _minimal_run_dir(root: Path) -> Path:
    run = root / "run"
    run.mkdir()
    (run / "status.json").write_text(
        '{"status":"success","method_or_workflow":"ols_cluster","main_claim_available":true,"run_id":"fixture"}',
        encoding="utf-8",
    )
    return run


def test_stata_regression_output_imports_claimable_rows(tmp_path: Path) -> None:
    raw = tmp_path / "stata.log"
    raw.write_text(
        """
------------------------------------------------------------------------------
           y | Coefficient  Std. err.      t    P>|t|     [95% conf. interval]
-------------+----------------------------------------------------------------
       treat |      .030      .010     3.00   0.003        .010        .050
        size |     -.020      .005    -4.00   0.000       -.030       -.010
       _cons |     1.200      .100    12.00   0.000       1.000       1.400
------------------------------------------------------------------------------
Number of obs = 1,200
""",
        encoding="utf-8",
    )

    result = import_external_table(raw, source_format="stata")

    assert result.has_hard_blocks is False
    assert [row.term for row in result.rows] == ["treat", "size"]
    assert result.rows[0].coef == 0.03
    assert result.rows[0].std_error == 0.01
    assert result.rows[0].p_value == 0.003
    assert result.rows[0].nobs == 1200


def test_r_coefficients_with_censored_intercept_p_value(tmp_path: Path) -> None:
    raw = tmp_path / "r.txt"
    raw.write_text(
        """
Coefficients:
             Estimate Std. Error t value Pr(>|t|)
(Intercept)  1.2000     0.1000   12.00   <2e-16 ***
treat        0.0300     0.0100    3.00    0.003 **
""",
        encoding="utf-8",
    )

    result = import_external_table(raw, source_format="r")

    assert result.has_hard_blocks is False
    assert len(result.rows) == 1
    assert result.rows[0].term == "treat"
    assert result.rows[0].p_value == 0.003


def test_statsmodels_output_imports_with_no_observations(tmp_path: Path) -> None:
    raw = tmp_path / "statsmodels.txt"
    raw.write_text(
        """
                            OLS Regression Results
==============================================================================
Dep. Variable:                      y   R-squared:                       0.123
No. Observations:                2400
==============================================================================
                 coef    std err          t      P>|t|      [0.025      0.975]
------------------------------------------------------------------------------
Intercept       1.2000      0.100     12.000      0.000       1.000       1.400
treat           0.0300      0.010      3.000      0.003       0.010       0.050
""",
        encoding="utf-8",
    )

    result = import_external_table(raw, source_format="python")

    assert result.has_hard_blocks is False
    assert len(result.rows) == 1
    assert result.rows[0].term == "treat"
    assert result.rows[0].nobs == 2400
    assert result.rows[0].t_stat == 3.0


def test_latex_publication_table_imports_multiple_models_without_inventing_p_values(tmp_path: Path) -> None:
    raw = tmp_path / "table.tex"
    raw.write_text(
        r"""
\begin{tabular}{lcc}
\toprule
 & (1) & (2) \\
Treat & 0.030*** & 0.040** \\
 & (0.010) & (0.020) \\
Size & -0.020 & -0.010 \\
 & (0.005) & (0.006) \\
Observations & 1,200 & 900 \\
\bottomrule
\end{tabular}
""",
        encoding="utf-8",
    )

    result = import_external_table(raw, source_format="latex")

    assert result.has_hard_blocks is False
    assert {(row.term, row.model_id) for row in result.rows} == {
        ("Treat", "m1"),
        ("Treat", "m2"),
        ("Size", "m1"),
        ("Size", "m2"),
    }
    first = next(row for row in result.rows if row.term == "Treat" and row.model_id == "m1")
    assert first.coef == 0.03
    assert first.std_error == 0.01
    assert first.p_value is None
    assert "significance_stars_present_without_exact_p_value" in first.warnings
    assert first.nobs == 1200
    assert "stars_without_exact_p_value" in {issue.code for issue in result.issues}


def test_random_prose_numbers_do_not_become_evidence(tmp_path: Path) -> None:
    raw = tmp_path / "notes.txt"
    raw.write_text("The policy began in 2012 and the sample has 42 cities.", encoding="utf-8")

    result = import_external_table(raw)

    assert result.has_hard_blocks is True
    assert "no_claimable_rows_imported" in {issue.code for issue in result.issues}


def test_coefficient_without_inference_is_not_written_as_claimable(tmp_path: Path) -> None:
    raw = tmp_path / "minimal.csv"
    raw.write_text("term,coef\ntreat,0.03\n", encoding="utf-8")

    out = tmp_path / "imported"
    result = write_external_table_import(raw, out_dir=out, source_format="csv")

    assert result.has_hard_blocks is False
    assert result.rows[0].claimable is False
    assert _rows(out / "model_table.csv") == []
    assert "coefficient_without_inference_statistics" in {issue.code for issue in result.issues}


def test_duplicate_term_model_is_hard_blocked(tmp_path: Path) -> None:
    raw = tmp_path / "dup.csv"
    raw.write_text("term,model_id,coef,std_error\ntreat,m1,0.03,0.01\ntreat,m1,0.04,0.02\n", encoding="utf-8")

    result = import_external_table(raw, source_format="csv")

    assert result.has_hard_blocks is True
    assert "duplicate_term_model" in {issue.code for issue in result.issues}


def test_imported_model_table_feeds_evidence_ledger(tmp_path: Path) -> None:
    raw = tmp_path / "stata.log"
    raw.write_text(
        """
      y | Coefficient  Std. err.      t    P>|t|
--------+-----------------------------------------
  treat |      .030      .010     3.00   0.003
Number of obs = 1,200
""",
        encoding="utf-8",
    )
    out = tmp_path / "imported"
    result = write_external_table_import(raw, out_dir=out, source_format="stata", model_id="ols_1")
    assert result.has_hard_blocks is False

    ledger = build_evidence_ledger(run_dir=_minimal_run_dir(tmp_path), model_table_paths=[out / "model_table.csv"])

    assert ledger.has_hard_blocks is False
    items = ledger.ledger["evidence_items"]
    assert {item["display_type"] for item in items} >= {"coefficient", "standard_error", "p_value", "n"}
    assert any(item["model_id"] == "ols_1" and item["variable"] == "treat" for item in items)


def test_import_table_cli_writes_reports(tmp_path: Path) -> None:
    raw = tmp_path / "stata.log"
    raw.write_text(
        """
      y | Coefficient  Std. err.      t    P>|t|
--------+-----------------------------------------
  treat |      .030      .010     3.00   0.003
""",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "import-table",
            "--input",
            str(raw),
            "--format",
            "stata",
            "--model-id",
            "ols_1",
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "model_table.csv").exists()
    assert (out / "model_metadata.json").exists()
    assert (out / "reports" / "internal" / "external_table_import.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()
