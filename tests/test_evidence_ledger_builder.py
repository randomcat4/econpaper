from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from econpaper.evidence import build_evidence_ledger, write_evidence_ledger
from econpaper.linting import run_lint


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


def _run_dir(root: Path) -> Path:
    run_dir = root / "run"
    run_dir.mkdir()
    _write_json(run_dir / "status.json", {"run_id": "fixture_run", "status": "success"})
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "workflow": "ols_cluster",
            "run_id": "fixture_run",
            "status": "success",
            "artifacts": [{"path": "model_table.csv", "type": "model_table", "exists": True}],
            "missing_required_artifacts": [],
        },
    )
    return run_dir


def _refs(path: Path) -> Path:
    refs = path / "refs.bib"
    refs.write_text("@article{smith2020,title={Fixture},author={Smith},year={2020}}\n", encoding="utf-8")
    return refs


def _valid_run_contract(run_dir: Path) -> None:
    _write_json(
        run_dir / "status.json",
        {
            "status": "success",
            "agent_status": "claimable_success",
            "method_or_workflow": "ols_cluster",
            "run_id": "fixture_run",
            "claim_level": "main_estimate",
            "paper_readiness": "paper_ready",
            "main_claim_available": True,
        },
    )
    _write_json(run_dir / "manifest.json", {"status": "success", "method": "ols_cluster", "main_claim_available": True})
    _write_json(run_dir / "audit.json", {"status": "success", "method": "ols_cluster"})
    _write_json(run_dir / "run_config_resolved.json", {"spec": {}})
    _write_json(run_dir / "validation_report.json", {"status": "passed"})
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "workflow": "ols_cluster",
            "run_id": "fixture_run",
            "status": "success",
            "artifacts": [{"path": "model_table.csv", "type": "model_table", "required": True, "exists": True}],
            "missing_required_artifacts": [],
        },
    )


def test_csv_model_table_builds_cell_level_evidence_items(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    _write_csv(
        run_dir / "model_table.csv",
        [{"term": "treat", "coef": "0.03", "std_error": "0.01", "p_value": "0.025", "nobs": "1200"}],
    )
    result = build_evidence_ledger(run_dir=run_dir)
    ledger = result.ledger
    assert result.has_hard_blocks is False
    assert ledger["run_id"] == "fixture_run"
    assert len(ledger["artifacts"]) == 1
    by_stat = {item["statistic"]: item for item in ledger["evidence_items"]}
    assert by_stat["coefficient"]["value"] == 0.03
    assert by_stat["standard_error"]["value"] == 0.01
    assert by_stat["p_value"]["value"] == 0.025
    assert by_stat["n"]["value"] == 1200
    assert by_stat["coefficient"]["cell_ref"] == "model_table.csv#row=1;column=coef"


def test_intake_and_summary_stats_populate_variable_semantics(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    _write_csv(run_dir / "model_table.csv", [{"term": "investment_rate", "coef": "0.03", "std_error": "0.01", "p_value": "0.02"}])
    intake = _write_json(
        tmp_path / "intake_profile.json",
        {
            "outcome_magnitude_context": [
                {
                    "variable": "investment_rate",
                    "unit": "percentage points of assets",
                    "mean": None,
                    "sd": None,
                    "meaningful_benchmark": "10% of the sample mean",
                }
            ]
        },
    )
    summary = _write_csv(
        run_dir / "summary_stats.csv",
        [{"variable": "investment_rate", "mean": "0.25", "sd": "0.075", "unit": "percentage points of assets"}],
    )
    result = build_evidence_ledger(run_dir=run_dir, intake_profile_path=intake, summary_stats_path=summary)
    semantics = result.ledger["variable_semantics"]["investment_rate"]
    assert semantics["unit"] == "percentage points of assets"
    assert semantics["mean"] == 0.25
    assert semantics["sd"] == 0.075
    assert result.magnitude_semantics["variables"]["investment_rate"]["ready_for_magnitude_interpretation"] is True
    assert {"mean", "sd"} <= {item["statistic"] for item in result.ledger["evidence_items"]}


def test_cli_writes_evidence_ledger_reports(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    _write_csv(run_dir / "model_table.csv", [{"term": "treat", "coef": "0.03", "std_error": "0.01", "p_value": "0.025"}])
    out = tmp_path / "evidence_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "evidence",
            "--run-dir",
            str(run_dir),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "evidence_ledger.json").exists()
    assert (out / "reports" / "internal" / "evidence_ledger.json").exists()
    assert (out / "reports" / "internal" / "magnitude_semantics.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_tex_table_path_alone_does_not_create_evidence(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "table1.tex").write_text("\\begin{tabular}{cc}x&0.03\\end{tabular}", encoding="utf-8")
    _write_json(run_dir / "status.json", {"run_id": "fixture_run", "status": "success"})
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "workflow": "ols_cluster",
            "run_id": "fixture_run",
            "status": "success",
            "artifacts": [{"path": "table1.tex", "type": "table", "exists": True}],
            "missing_required_artifacts": [],
        },
    )
    result = build_evidence_ledger(run_dir=run_dir)
    assert result.has_hard_blocks is True
    assert result.ledger["evidence_items"] == []
    assert result.issues[0].code == "structured_model_table_missing"


def test_json_main_effect_table_is_supported(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    (run_dir / "model_table.csv").unlink(missing_ok=True)
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "workflow": "ols_cluster",
            "run_id": "fixture_run",
            "status": "success",
            "artifacts": [{"path": "model_table.json", "type": "model_table", "exists": True}],
            "missing_required_artifacts": [],
        },
    )
    _write_json(
        run_dir / "model_table.json",
        {
            "estimator": "twfe",
            "n_obs": 500,
            "main_effect": {"term": "ATT", "estimate": 0.0, "std_error": 0.1, "p_value": 0.001},
        },
    )
    result = build_evidence_ledger(run_dir=run_dir)
    by_stat = {item["statistic"]: item["value"] for item in result.ledger["evidence_items"]}
    assert by_stat["coefficient"] == 0.0
    assert by_stat["standard_error"] == 0.1
    assert by_stat["p_value"] == 0.001
    assert by_stat["n"] == 500


def test_evidence_ledger_can_feed_lint_numeric_gate(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    _valid_run_contract(run_dir)
    _write_csv(run_dir / "model_table.csv", [{"term": "treat", "coef": "0.03", "std_error": "0.01", "p_value": "0.025"}])
    write_evidence_ledger(run_dir=run_dir, out_dir=run_dir)
    draft = tmp_path / "draft.tex"
    draft.write_text("The coefficient is 0.03 \\citep{smith2020}.", encoding="utf-8")
    report = run_lint(draft, run_dir=run_dir, refs_path=_refs(tmp_path), out_dir=tmp_path / "lint")
    assert report.has_hard_blocks is False
