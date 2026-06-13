from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from econpaper.evidence_pack import write_evidence_pack
from econpaper.release_gate import run_release_gate, write_release_gate
from econpaper.tiering import write_pack_metrics


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


def _pack(root: Path, *, placeholder: bool = False, magnitude: bool = True, author_report: bool = True) -> Path:
    root.mkdir(parents=True)
    if author_report:
        (root / "AUTHOR_REPORT.md").write_text("# AUTHOR_REPORT\n\nReady.\n", encoding="utf-8")
    artifact_paths = {
        "model_table": "model_table.csv",
        "event_study": "event_study.csv",
        "pretrend_test": "pretrend_test.json",
        "cohort_table": "cohort_table.csv",
        "robustness_grid": "robustness_grid.csv",
        "placebo_tests": "placebo_tests.csv",
        "heterogeneity": "heterogeneity.csv",
        "summary_stats": "summary_stats.csv",
        "figure_manifest": "figures/manifest.yaml",
    }
    _write_csv(
        root / "model_table.csv",
        [{"term": "treat", "coef": "0.03", "std_error": "0.01", "ci_low": "0.01", "ci_high": "0.05", "p_value": "0.02", "n_obs": "1200", "n_clusters": "80"}],
    )
    _write_csv(
        root / "event_study.csv",
        [
            {"event_time": "-2", "coef": "0.00", "std_error": "0.01", "ci_low": "-0.02", "ci_high": "0.02"},
            {"event_time": "0", "coef": "0.03", "std_error": "0.01", "ci_low": "0.01", "ci_high": "0.05"},
        ],
    )
    _write_json(root / "pretrend_test.json", {"p_value": 0.42, "lead_count": 1, "test_type": "event_study_lead_screen"})
    _write_csv(root / "cohort_table.csv", [{"cohort": "2010", "n_units": "40"}, {"cohort": "2012", "n_units": "45"}])
    _write_csv(
        root / "robustness_grid.csv",
        [
            {"family": "estimator_comparison", "check": "twfe", "status": "computed"},
            {"family": "sample_construction", "check": "listwise", "status": "computed"},
            {"family": "cluster_diagnostic", "check": "cluster_count", "status": "computed"},
            {"family": "controls", "check": "baseline_controls", "status": "computed"},
        ],
    )
    _write_csv(root / "placebo_tests.csv", [{"placebo": "fake_timing", "estimate": "0.00", "p_value": "0.77", "status": "computed"}])
    _write_csv(
        root / "heterogeneity.csv",
        [
            {"dimension": "region", "group": "coastal", "estimate": "0.04"},
            {"dimension": "size", "group": "large", "estimate": "0.02"},
        ],
    )
    _write_csv(root / "summary_stats.csv", [{"variable": "treat", "mean": "0.25", "sd": "0.075", "unit": "percentage points"}])
    (root / "figures").mkdir(parents=True, exist_ok=True)
    (root / "event_study_plot.png").write_bytes(b"fixture")
    (root / "figures" / "manifest.yaml").write_text("figures:\n  - path: event_study_plot.png\n    kind: event_study\n    exists: true\n", encoding="utf-8")
    evidence_ids = [f"ev{idx}" for idx in range(10)]
    _write_json(
        root / "claim_ledger.json",
        {
            "version": "v3.0",
            "status": "passed",
            "hard_blocks": [],
            "claims": [{"status": "safe", "evidence_refs": [evidence_id]} for evidence_id in evidence_ids],
        },
    )
    _write_json(
        root / "evidence_ledger.json",
        {
            "artifacts": [
                {
                    "artifact_id": "model_table_main",
                    "artifact_type": "model_table",
                    "path": "model_table.csv",
                    "hash": "sha256:model",
                    "claimable": True,
                }
            ],
            "evidence_items": [
                {
                    "evidence_id": evidence_id,
                    "artifact_id": "model_table_main",
                    "statistic": "coefficient",
                    "value": idx / 100,
                    "variable": "treat",
                    "provenance_hash": f"sha256:{evidence_id}",
                }
                for idx, evidence_id in enumerate(evidence_ids, start=1)
            ],
        },
    )
    _write_json(
        root / "artifact_manifest.json",
        {
            "workflow": "did",
            "run_id": "fixture",
            "status": "success",
            "evidence_contract": {
                "consumer": "econpaper",
                "schema_version": "evidence_pack.v2",
                "artifact_type_field": "evidence_type",
            },
            "artifacts": [
                {"path": path, "type": "table", "evidence_type": artifact_type, "required": True, "exists": True}
                for artifact_type, path in artifact_paths.items()
            ],
            "missing_required_artifacts": [],
        },
    )
    _write_json(root / "design_profile.json", {"version": "v3.0", "status": "passed", "diagnostics_missing": []})
    _write_json(root / "reports" / "internal" / "global_coherence.json", {"version": "v3.0", "status": "passed", "has_hard_blocks": False})
    _write_json(
        root / "reports" / "internal" / "citation_safety_report.json",
        {
            "version": "v3.0",
            "missing_citekeys": [],
            "citation_uses": [],
            "external_notes_used": [{"note_id": "lit_note_001", "citekey": "smith2020"}],
        },
    )
    _write_json(root / "reports" / "internal" / "run_validation.json", {"version": "v3.0", "data_provenance": "author_supplied"})
    sections = root / "sections"
    sections.mkdir()
    text = "The estimate is "
    text += "{{coef:claim_main_001}}" if placeholder else "0.030"
    text += " and equals 0.40 standard deviations." if magnitude else "."
    (sections / "04_results.md").write_text("# Results\n\n" + text + "\n", encoding="utf-8")
    (sections / "00_abstract.md").write_text("# Abstract\n\nRendered abstract.\n", encoding="utf-8")
    (sections / "01_introduction.md").write_text("# Introduction\n\n" + ("evidence " * 1400) + "\n", encoding="utf-8")
    (sections / "02_data.md").write_text("# Data\n\n" + ("evidence " * 1200) + "\n", encoding="utf-8")
    (sections / "03_empirical_strategy.md").write_text("# Empirical Strategy\n\n" + ("evidence " * 1200) + "\n", encoding="utf-8")
    (sections / "05_robustness.md").write_text("# Robustness\n\n" + ("evidence " * 1200) + "\n", encoding="utf-8")
    (root / "main.md").write_text(("evidence " * 6200) + "\n", encoding="utf-8")
    evidence_ledger = json.loads((root / "evidence_ledger.json").read_text(encoding="utf-8"))
    write_evidence_pack(
        evidence_ledger=evidence_ledger,
        run_dir=root,
        out_dir=root,
        artifact_manifest_path=root / "artifact_manifest.json",
        run_validation_path=root / "reports" / "internal" / "run_validation.json",
    )
    write_pack_metrics(root)
    return root


def _human_eval(
    path: Path,
    *,
    retention: float = 0.60,
    time_saved: int = 5,
    clearer: int = 5,
    fabrication: bool = False,
    reviewer_role: str = "economics scholar",
) -> Path:
    evaluations = []
    for idx in range(5):
        evaluations.append(
            {
                "reviewer_role": reviewer_role,
                "generated_text_retention": retention,
                "time_saved": idx < time_saved,
                "silent_fabrication_reported": fabrication and idx == 0,
                "author_report_clearer": idx < clearer,
                "feedback_attached": True,
            }
        )
    return _write_json(path, {"evaluations": evaluations})


def _keep_only_tier_b_evidence(pack: Path) -> None:
    tier_b_types = {"model_table", "event_study", "pretrend_test", "summary_stats", "robustness_grid"}
    payload = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    payload["artifacts"] = [
        artifact
        for artifact in payload.get("artifacts", [])
        if artifact.get("artifact_type") in tier_b_types
    ]
    _write_json(pack / "evidence_pack.json", payload)
    _write_json(pack / "reports" / "internal" / "evidence_pack.json", payload)
    write_pack_metrics(pack)


def test_release_gate_passes_with_required_human_eval(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is False
    assert result.status == "passed"
    assert result.metrics["human_eval"]["median_generated_text_retention"] == 0.60


def test_missing_human_eval_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"))
    assert result.has_hard_blocks is True
    assert "human_eval_missing" in {finding.code for finding in result.findings}


def test_non_scholar_human_eval_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(
        pack_dir=_pack(tmp_path / "pack"),
        human_eval_path=_human_eval(tmp_path / "human_eval.json", reviewer_role="intern"),
    )
    assert result.has_hard_blocks is True
    assert result.metrics["human_eval"]["scholar_count"] == 0
    assert "human_eval_scholar_reviewers_missing" in {finding.code for finding in result.findings}


def test_low_retention_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"), human_eval_path=_human_eval(tmp_path / "human_eval.json", retention=0.40))
    assert result.has_hard_blocks is True
    assert "human_eval_retention_low" in {finding.code for finding in result.findings}


def test_silent_fabrication_report_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack"), human_eval_path=_human_eval(tmp_path / "human_eval.json", fabrication=True))
    assert result.has_hard_blocks is True
    assert "human_eval_fabrication_reported" in {finding.code for finding in result.findings}


def test_unrendered_placeholder_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack", placeholder=True), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "unrendered_numeric_placeholder" in {finding.code for finding in result.findings}


def test_missing_results_magnitude_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack", magnitude=False), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "results_magnitude_missing" in {finding.code for finding in result.findings}


def test_missing_author_report_blocks_release(tmp_path: Path) -> None:
    result = run_release_gate(pack_dir=_pack(tmp_path / "pack", author_report=False), human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "author_report_missing" in {finding.code for finding in result.findings}


def test_missing_tier_metrics_blocks_release(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    (pack / "reports" / "internal" / "metrics.json").unlink()
    result = run_release_gate(pack_dir=pack, human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "tier_metrics_missing" in {finding.code for finding in result.findings}


def test_below_tier_a_blocks_release_even_with_human_eval(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    (pack / "sections" / "05_robustness.md").write_text(
        "# Robustness\n\n[AUTHOR_INPUT_NEEDED]: robustness.\n",
        encoding="utf-8",
    )
    write_pack_metrics(pack)
    result = run_release_gate(pack_dir=pack, human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "draft_tier_below_release_target" in {finding.code for finding in result.findings}


def test_tier_b_evidence_boundary_still_blocks_release(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    _keep_only_tier_b_evidence(pack)
    metrics = json.loads((pack / "reports" / "internal" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["draft_tier"] == "B"
    assert metrics["metrics"]["did_tier_b_missing_artifacts"] == []
    assert set(metrics["metrics"]["did_tier_a_missing_artifacts"]) == {
        "cohort_table",
        "figure_manifest",
        "heterogeneity",
        "placebo_tests",
    }

    result = run_release_gate(pack_dir=pack, human_eval_path=_human_eval(tmp_path / "human_eval.json"))

    codes = {finding.code for finding in result.findings}
    assert result.has_hard_blocks is True
    assert "draft_tier_below_release_target" in codes


def test_spatial_impacts_without_w_audit_block_release(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    _write_csv(
        pack / "tables" / "spatial_impact_decomposition.csv",
        [{"effect": "x", "direct": "0.1", "indirect": "0.2", "total": "0.3"}],
    )
    payload = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    payload["artifacts"].append(
        {
            "artifact_id": "spatial_impacts",
            "artifact_type": "spatial_impact_decomposition",
            "path": "tables/spatial_impact_decomposition.csv",
            "exists": True,
            "claimable": True,
        }
    )
    _write_json(pack / "evidence_pack.json", payload)
    _write_json(pack / "reports" / "internal" / "evidence_pack.json", payload)
    write_pack_metrics(pack)

    result = run_release_gate(pack_dir=pack, human_eval_path=_human_eval(tmp_path / "human_eval.json"))

    codes = {finding.code for finding in result.findings}
    assert result.has_hard_blocks is True
    assert {"spatial_impacts_missing_w_metadata", "spatial_impacts_missing_w_audit", "spatial_impacts_missing_backend_status"} <= codes


def test_spatial_impacts_without_uncertainty_block_release(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    _write_csv(
        pack / "tables" / "spatial_impact_decomposition.csv",
        [{"effect": "x", "direct": "0.1", "indirect": "0.2", "total": "0.3"}],
    )
    _write_json(pack / "tables" / "spatial_w_metadata.json", {"weights": [{"w_name": "W"}]})
    _write_json(pack / "tables" / "spatial_w_audit.json", {"weights": [{"w_name": "W", "row_sum_min": 1.0}]})
    _write_csv(pack / "tables" / "live_backend_certification_matrix.csv", [{"backend": "stata_xsmle", "status": "ok"}])
    payload = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    payload["artifacts"].extend(
        [
            {
                "artifact_id": "spatial_impacts",
                "artifact_type": "spatial_impact_decomposition",
                "path": "tables/spatial_impact_decomposition.csv",
                "exists": True,
                "claimable": True,
            },
            {
                "artifact_id": "spatial_w_metadata",
                "artifact_type": "spatial_w_metadata",
                "path": "tables/spatial_w_metadata.json",
                "exists": True,
                "claimable": True,
            },
            {
                "artifact_id": "spatial_w_audit",
                "artifact_type": "spatial_w_audit",
                "path": "tables/spatial_w_audit.json",
                "exists": True,
                "claimable": True,
            },
            {
                "artifact_id": "spatial_backend_status",
                "artifact_type": "spatial_backend_status",
                "path": "tables/live_backend_certification_matrix.csv",
                "exists": True,
                "claimable": True,
            },
        ]
    )
    _write_json(pack / "evidence_pack.json", payload)
    _write_json(pack / "reports" / "internal" / "evidence_pack.json", payload)
    write_pack_metrics(pack)

    result = run_release_gate(pack_dir=pack, human_eval_path=_human_eval(tmp_path / "human_eval.json"))

    codes = {finding.code for finding in result.findings}
    assert result.has_hard_blocks is True
    assert "spatial_impact_decomposition_not_certified" in codes


def test_synthetic_or_unknown_provenance_blocks_release(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    _write_json(pack / "reports" / "internal" / "run_validation.json", {"version": "v3.0", "data_provenance": "synthetic_fixture"})
    write_pack_metrics(pack)
    result = run_release_gate(pack_dir=pack, human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    assert result.has_hard_blocks is True
    assert "data_provenance_not_author_supplied" in {finding.code for finding in result.findings}


def test_stale_or_tampered_tier_metrics_blocks_release(tmp_path: Path) -> None:
    pack = _pack(tmp_path / "pack")
    (pack / "sections" / "04_results.md").write_text(
        "# Results\n\n[AUTHOR_INPUT_NEEDED]: results.\n",
        encoding="utf-8",
    )
    result = run_release_gate(pack_dir=pack, human_eval_path=_human_eval(tmp_path / "human_eval.json"))
    codes = {finding.code for finding in result.findings}
    assert result.has_hard_blocks is True
    assert "tier_metrics_stale_or_tampered" in codes
    assert "draft_tier_below_release_target" in codes


def test_cli_writes_release_gate_report(tmp_path: Path) -> None:
    out = tmp_path / "release"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "release-gate",
            "--pack-dir",
            str(_pack(tmp_path / "pack")),
            "--human-eval",
            str(_human_eval(tmp_path / "human_eval.json")),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "reports" / "internal" / "release_gate.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_write_release_gate_report_lists_blockers(tmp_path: Path) -> None:
    result = write_release_gate(pack_dir=_pack(tmp_path / "pack", placeholder=True), human_eval_path=_human_eval(tmp_path / "human_eval.json"), out_dir=tmp_path / "out")
    report = (tmp_path / "out" / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert result.has_hard_blocks is True
    assert "unrendered_numeric_placeholder" in report
