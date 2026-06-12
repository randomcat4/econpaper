from __future__ import annotations

import csv
import json
from pathlib import Path

from econpaper.evidence_pack import build_evidence_pack, write_evidence_pack
from econpaper.tiering import evaluate_pack_tier, write_pack_metrics


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_evidence_pack(pack: Path, ledger: dict) -> None:
    result = build_evidence_pack(evidence_ledger=ledger, run_validation={"data_provenance": "author_supplied"})
    _write_json(pack / "evidence_pack.json", result.pack)


def _write_tier_ready_shell(pack: Path) -> None:
    sections = pack / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    for filename in [
        "00_abstract.md",
        "01_introduction.md",
        "02_data.md",
        "03_empirical_strategy.md",
        "04_results.md",
        "05_robustness.md",
    ]:
        (sections / filename).write_text(f"# {filename}\n\n" + ("evidence " * 500) + "\n", encoding="utf-8")
    (pack / "main.md").write_text("evidence " * 3200, encoding="utf-8")
    _write_json(pack / "claim_ledger.json", {"claims": [{"evidence_refs": ["ev1"]}]})
    _write_json(pack / "design_profile.json", {"status": "passed", "diagnostics_missing": []})
    _write_json(pack / "reports" / "internal" / "global_coherence.json", {"status": "passed", "has_hard_blocks": False})
    _write_json(pack / "reports" / "internal" / "citation_safety_report.json", {"missing_citekeys": [], "citation_uses": []})
    _write_json(pack / "reports" / "internal" / "run_validation.json", {"data_provenance": "author_supplied"})


def _write_b_evidence_pack(pack: Path, *, toy_files: bool) -> None:
    artifact_specs = [
        ("model_table_main", "model_table", "model_table.csv"),
        ("event_study_main", "event_study", "event_study.csv"),
        ("pretrend_main", "pretrend_test", "pretrend_test.json"),
        ("summary_main", "summary_stats", "summary_stats.csv"),
        ("robustness_main", "robustness_grid", "robustness_grid.csv"),
    ]
    if toy_files:
        for _artifact_id, _artifact_type, rel in artifact_specs:
            path = pack / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
    else:
        _write_csv(pack / "model_table.csv", [{"term": "treat", "coef": "0.03", "std_error": "0.01", "n_obs": "1200"}])
        _write_csv(
            pack / "event_study.csv",
            [
                {"event_time": "-1", "coef": "0.00", "std_error": "0.01"},
                {"event_time": "0", "coef": "0.03", "std_error": "0.01"},
            ],
        )
        _write_json(pack / "pretrend_test.json", {"p_value": 0.42, "lead_count": 1})
        _write_csv(pack / "summary_stats.csv", [{"variable": "treat", "mean": "0.25", "sd": "0.075", "unit": "percentage points"}])
        _write_csv(
            pack / "robustness_grid.csv",
            [
                {"family": "estimator_comparison", "check": "twfe", "status": "computed"},
                {"family": "sample_construction", "check": "listwise", "status": "computed"},
            ],
        )
    ledger = {
        "artifacts": [
            {"artifact_id": artifact_id, "artifact_type": artifact_type, "path": rel, "hash": f"sha256:{artifact_id}", "claimable": True}
            for artifact_id, artifact_type, rel in artifact_specs
        ],
        "evidence_items": [
            {
                "evidence_id": "ev1",
                "artifact_id": "model_table_main",
                "statistic": "coefficient",
                "value": 0.03,
                "variable": "treat",
                "provenance_hash": "sha256:cell",
            }
        ],
    }
    write_evidence_pack(evidence_ledger=ledger, run_dir=pack, out_dir=pack, run_validation_path=pack / "reports" / "internal" / "run_validation.json")


def _write_a_evidence_pack(pack: Path, *, stub_figure_manifest: bool = False) -> None:
    artifact_specs = [
        ("model_table_main", "model_table", "model_table.csv"),
        ("event_study_main", "event_study", "event_study.csv"),
        ("pretrend_main", "pretrend_test", "pretrend_test.json"),
        ("summary_main", "summary_stats", "summary_stats.csv"),
        ("robustness_main", "robustness_grid", "robustness_grid.csv"),
        ("cohort_main", "cohort_table", "cohort_table.csv"),
        ("placebo_main", "placebo_tests", "placebo_tests.csv"),
        ("heterogeneity_main", "heterogeneity", "heterogeneity.csv"),
        ("figure_manifest_main", "figure_manifest", "figures/manifest.yaml"),
    ]
    _write_csv(pack / "model_table.csv", [{"term": "treat", "coef": "0.03", "std_error": "0.01", "n_obs": "1200", "ci_low": "0.01", "ci_high": "0.05", "n_clusters": "40"}])
    _write_csv(
        pack / "event_study.csv",
        [
            {"event_time": "-1", "coef": "0.00", "std_error": "0.01"},
            {"event_time": "0", "coef": "0.03", "std_error": "0.01"},
        ],
    )
    _write_json(pack / "pretrend_test.json", {"p_value": 0.42, "lead_count": 1})
    _write_csv(pack / "summary_stats.csv", [{"variable": "treat", "mean": "0.25", "sd": "0.075", "unit": "percentage points"}])
    _write_csv(
        pack / "robustness_grid.csv",
        [
            {"family": "estimator_comparison", "check": "twfe", "status": "computed"},
            {"family": "sample_construction", "check": "balanced", "status": "computed"},
            {"family": "controls", "check": "baseline", "status": "computed"},
            {"family": "clustering", "check": "province", "status": "computed"},
        ],
    )
    _write_csv(pack / "cohort_table.csv", [{"cohort": "2019", "n_units": "20"}])
    _write_csv(pack / "placebo_tests.csv", [{"placebo": "fake_policy", "p_value": "0.54", "status": "computed"}])
    _write_csv(
        pack / "heterogeneity.csv",
        [
            {"dimension": "baseline_size_group", "group": "large", "estimate": "0.04", "status": "computed"},
            {"dimension": "province_group", "group": "north", "estimate": "0.02", "status": "computed"},
        ],
    )
    if stub_figure_manifest:
        (pack / "figures").mkdir(parents=True, exist_ok=True)
        (pack / "figures" / "manifest.yaml").write_text("event_study\n", encoding="utf-8")
    else:
        (pack / "figures").mkdir(parents=True, exist_ok=True)
        (pack / "figures" / "event_study_plot.png").write_bytes(b"png")
        (pack / "figures" / "manifest.yaml").write_text("figures:\n  - id: event_study\n    path: figures/event_study_plot.png\n", encoding="utf-8")
    ledger = {
        "artifacts": [
            {"artifact_id": artifact_id, "artifact_type": artifact_type, "path": rel, "hash": f"sha256:{artifact_id}", "claimable": True}
            for artifact_id, artifact_type, rel in artifact_specs
        ],
        "evidence_items": [
            {
                "evidence_id": "ev1",
                "artifact_id": "model_table_main",
                "statistic": "coefficient",
                "value": 0.03,
                "variable": "treat",
                "provenance_hash": "sha256:cell",
            }
        ],
    }
    write_evidence_pack(evidence_ledger=ledger, run_dir=pack, out_dir=pack, run_validation_path=pack / "reports" / "internal" / "run_validation.json")


def _write_rdd_tier_a_pack(pack: Path) -> None:
    sections = pack / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    for filename in [
        "00_abstract.md",
        "01_introduction.md",
        "02_data.md",
        "03_empirical_strategy.md",
        "04_results.md",
        "05_robustness.md",
    ]:
        (sections / filename).write_text(f"# {filename}\n\n" + ("rdd evidence " * 600) + "\n", encoding="utf-8")
    (pack / "main.md").write_text("rdd evidence " * 6200, encoding="utf-8")
    _write_json(
        pack / "design_profile.json",
        {
            "status": "passed",
            "declared_design_type": "geographic RDD",
            "checked_design_type": "rdd_artifacts_present",
            "diagnostics_present": ["rd_plot", "manipulation_test", "bandwidth_sensitivity", "covariate_continuity"],
            "diagnostics_missing": [],
        },
    )
    _write_json(pack / "reports" / "internal" / "global_coherence.json", {"status": "passed", "has_hard_blocks": False})
    _write_json(
        pack / "reports" / "internal" / "citation_safety_report.json",
        {"missing_citekeys": [], "citation_uses": [], "external_notes_used": [{"note_id": "imbens2008"}]},
    )
    _write_json(pack / "reports" / "internal" / "run_validation.json", {"data_provenance": "author_supplied"})
    _write_json(pack / "claim_ledger.json", {"claims": [{"status": "safe", "evidence_refs": ["ev1"]}]})
    _write_csv(
        pack / "model_table.csv",
        [
            {
                "term": "Robust",
                "coef": "-0.05",
                "std_error": "0.01",
                "ci_low": "-0.07",
                "ci_high": "-0.03",
                "n_obs": "1280",
                "n_clusters": "160",
            }
        ],
    )
    _write_csv(pack / "summary_stats.csv", [{"variable": "y", "mean": "5.4", "sd": "0.2", "unit": "log visits"}])
    _write_csv(pack / "rdd_bandwidth.csv", [{"side": "left", "bandwidth": "1.5"}, {"side": "right", "bandwidth": "1.5"}])
    _write_json(pack / "rdd_density_test.json", {"status": "passed", "p_value": 0.57})
    _write_csv(pack / "covariate_continuity.csv", [{"covariate": "baseline_y", "status": "passed", "p_value": "0.83"}])
    _write_json(
        pack / "rdd_diagnostics.json",
        {
            "density_test": {"status": "passed", "path": "rdd_density_test.json", "p_value": 0.57},
            "covariate_continuity": {"status": "passed", "path": "covariate_continuity.csv"},
        },
    )
    ledger = {
        "artifacts": [
            {"artifact_id": "model_table_main", "artifact_type": "model_table", "path": "model_table.csv", "hash": "sha256:model", "claimable": True},
            {"artifact_id": "summary_main", "artifact_type": "summary_stats", "path": "summary_stats.csv", "hash": "sha256:summary", "claimable": True},
            {"artifact_id": "rdd_bandwidth_main", "artifact_type": "rdd_bandwidth", "path": "rdd_bandwidth.csv", "hash": "sha256:bw", "claimable": True},
            {"artifact_id": "rdd_diagnostics_main", "artifact_type": "rdd_diagnostics", "path": "rdd_diagnostics.json", "hash": "sha256:diag", "claimable": True},
        ],
        "evidence_items": [
            {
                "evidence_id": "ev1",
                "artifact_id": "model_table_main",
                "statistic": "coefficient",
                "value": -0.05,
                "variable": "Robust",
                "provenance_hash": "sha256:cell",
            }
        ],
    }
    write_evidence_pack(evidence_ledger=ledger, run_dir=pack, out_dir=pack, run_validation_path=pack / "reports" / "internal" / "run_validation.json")


def test_tiering_counts_floor_sections_and_did_missing_artifacts(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    sections = pack / "sections"
    sections.mkdir(parents=True)
    (sections / "00_abstract.md").write_text("# Abstract\n\nThe estimate is 0.03.\n", encoding="utf-8")
    (sections / "04_results.md").write_text(
        "# Results\n\n[AUTHOR_INPUT_NEEDED]: robustness checks.\n",
        encoding="utf-8",
    )
    evidence_ledger = {
        "artifacts": [
            {
                "artifact_id": "model_table_main",
                "artifact_type": "model_table",
                "path": "model_table.csv",
                "hash": "sha256:model",
            }
        ],
        "evidence_items": [
            {
                "evidence_id": "ev1",
                "artifact_id": "model_table_main",
                "statistic": "coefficient",
                "value": 0.03,
                "variable": "treat",
                "provenance_hash": "sha256:cell",
            }
        ],
    }
    _write_json(pack / "evidence_ledger.json", evidence_ledger)
    _write_evidence_pack(pack, evidence_ledger)
    _write_json(pack / "claim_ledger.json", {"claims": [{"evidence_refs": ["ev1"]}]})
    _write_json(pack / "design_profile.json", {"status": "passed", "diagnostics_missing": []})
    _write_json(pack / "reports" / "internal" / "global_coherence.json", {"status": "passed", "has_hard_blocks": False})
    _write_json(pack / "reports" / "internal" / "run_validation.json", {"data_provenance": "author_supplied"})

    result = evaluate_pack_tier(pack)

    assert result.draft_tier == "C"
    assert result.metrics["sections_floor_count"] == 1
    assert result.metrics["floor_section_requests"]["04_results.md"] == ["[AUTHOR_INPUT_NEEDED]: robustness checks."]
    assert "robustness_grid" in result.metrics["did_tier_a_missing_artifacts"]
    assert result.metrics["provenance"]["data_provenance"] == "author_supplied"


def test_write_pack_metrics_materializes_internal_metrics(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    (pack / "sections").mkdir(parents=True)
    (pack / "sections" / "04_results.md").write_text("# Results\n\n[AUTHOR_INPUT_NEEDED]: result.\n", encoding="utf-8")
    result = write_pack_metrics(pack)
    payload = json.loads((pack / "reports" / "internal" / "metrics.json").read_text(encoding="utf-8"))
    assert payload["draft_tier"] == result.draft_tier == "C"
    assert payload["metrics"]["sections_floor_count"] == 1
    assert "evidence_pack_invalid" in payload["metrics"]["tier_b_blockers"]


def test_tier_b_requires_structured_artifact_content_not_just_types(tmp_path: Path) -> None:
    pack = tmp_path / "toy_content_pack"
    _write_tier_ready_shell(pack)
    _write_b_evidence_pack(pack, toy_files=True)

    result = evaluate_pack_tier(pack)

    assert "did_tier_b_artifacts_missing" not in result.metrics["tier_b_blockers"]
    assert "did_tier_b_artifacts_incomplete" in result.metrics["tier_b_blockers"]
    assert {"model_table", "event_study", "robustness_grid"} <= set(result.metrics["did_tier_b_incomplete_artifacts"])
    assert result.draft_tier == "C"


def test_pretrend_count_metadata_alone_does_not_satisfy_did_tier_b(tmp_path: Path) -> None:
    pack = tmp_path / "hollow_pretrend_pack"
    _write_tier_ready_shell(pack)
    _write_b_evidence_pack(pack, toy_files=False)
    _write_json(pack / "pretrend_test.json", {"lead_count": 1})

    result = evaluate_pack_tier(pack)

    assert "pretrend_test" in result.metrics["did_tier_b_incomplete_artifacts"]
    assert result.metrics["did_artifact_content"]["pretrend_test"]["tier_b_status"] == "failed"
    assert result.draft_tier == "C"


def test_valid_tier_b_content_reaches_but_not_a(tmp_path: Path) -> None:
    pack = tmp_path / "tier_b_content_pack"
    _write_tier_ready_shell(pack)
    _write_b_evidence_pack(pack, toy_files=False)

    result = evaluate_pack_tier(pack)

    assert result.draft_tier == "B"
    assert result.metrics["did_tier_b_missing_artifacts"] == []
    assert result.metrics["did_tier_b_incomplete_artifacts"] == []
    assert "did_tier_a_artifacts_missing" in result.metrics["tier_a_blockers"]
    assert "verified_literature_notes_missing" in result.metrics["tier_a_blockers"]
    assert result.metrics["verified_literature_note_count"] == 0
    assert "robustness_grid" in result.metrics["did_tier_a_incomplete_artifacts"]


def test_rdd_tier_a_requires_computed_density_and_covariate_continuity(tmp_path: Path) -> None:
    pack = tmp_path / "rdd_tier_a_pack"
    _write_rdd_tier_a_pack(pack)

    result = evaluate_pack_tier(pack)

    assert result.draft_tier == "A"
    assert result.metrics["design_family"] == "rdd"
    assert result.metrics["rdd_tier_a_missing_or_incomplete_artifacts"] == []
    assert result.metrics["rdd_artifact_content"]["model_table"]["tier_a_status"] == "passed"
    assert result.metrics["rdd_artifact_content"]["rdd_diagnostics"]["tier_a_status"] == "passed"


def test_figure_manifest_requires_existing_explicit_event_study_path(tmp_path: Path) -> None:
    pack = tmp_path / "stub_figure_manifest_pack"
    _write_tier_ready_shell(pack)
    _write_a_evidence_pack(pack, stub_figure_manifest=True)

    result = evaluate_pack_tier(pack)

    assert "figure_manifest" in result.metrics["did_tier_a_incomplete_artifacts"]
    figure_check = result.metrics["did_artifact_content"]["figure_manifest"]
    assert figure_check["tier_a_status"] == "failed"
    assert "figure_manifest_requires_explicit_figure_path" in figure_check["issues"]
