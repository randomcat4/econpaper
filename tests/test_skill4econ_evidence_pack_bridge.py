from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SKILL4ECON_SRC = ROOT / "skill4econ" / "src"
if str(SKILL4ECON_SRC) not in sys.path:
    sys.path.insert(0, str(SKILL4ECON_SRC))

from econpaper.evidence import write_evidence_ledger
from econpaper.tiering import evaluate_pack_tier
from skill4econ.core import make_run_context, read_spec
from skill4econ.contracts.artifact_manifest import write_artifact_manifest
from skill4econ.python_wrappers import w3_inference_audit
from skill4econ.workflows import did_paper_run


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_skill4econ_manifest_feeds_econpaper_evidence_pack_without_contract_downgrade(tmp_path: Path) -> None:
    run_dir = tmp_path / "skill4econ_run"
    run_dir.mkdir()
    _write_csv(
        run_dir / "model_table.csv",
        [{"term": "treat", "coef": "0.03", "std_error": "0.01", "p_value": "0.025", "n_obs": "1200"}],
    )
    _write_csv(run_dir / "event_study.csv", [{"event_time": "-1", "coef": "0.0", "std_error": "0.01"}])
    _write_json(run_dir / "pretrend_test.json", {"p_value": 0.42})
    _write_csv(run_dir / "robustness_grid.csv", [{"family": "controls", "status": "pass"}])
    _write_csv(run_dir / "summary_stats.csv", [{"variable": "treat", "mean": "0.25", "sd": "0.075", "unit": "percentage points"}])
    (run_dir / "provenance.yaml").write_text("data_provenance: author_supplied\n", encoding="utf-8")
    write_artifact_manifest(
        run_dir / "artifact_manifest.json",
        workflow="did_paper_run",
        run_id="fixture",
        run_dir=run_dir,
        status="success",
        required_artifacts=[
            "model_table.csv",
            "event_study.csv",
            "pretrend_test.json",
            "robustness_grid.csv",
            "summary_stats.csv",
        ],
    )

    pack = tmp_path / "econpaper_pack"
    result = write_evidence_ledger(run_dir=run_dir, out_dir=pack, summary_stats_path=run_dir / "summary_stats.csv")

    evidence_pack = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    artifact_types = {item["artifact_type"] for item in evidence_pack["artifacts"]}
    assert result.has_hard_blocks is False
    assert evidence_pack["validation"]["status"] == "passed"
    assert {"model_table", "event_study", "pretrend_test", "robustness_grid", "summary_stats"} <= artifact_types

    evidence_ids = [
        item["evidence_id"]
        for item in evidence_pack["evidence_items"]
        if isinstance(item, dict) and item.get("evidence_id")
    ]
    _write_json(pack / "claim_ledger.json", {"claims": [{"evidence_refs": evidence_ids}]})
    _write_json(pack / "design_profile.json", {"status": "passed", "diagnostics_missing": []})
    _write_json(pack / "reports" / "internal" / "global_coherence.json", {"status": "passed", "has_hard_blocks": False})
    _write_json(pack / "reports" / "internal" / "citation_safety_report.json", {"missing_citekeys": [], "citation_uses": []})
    _write_json(pack / "reports" / "internal" / "run_validation.json", {"data_provenance": "author_supplied"})
    sections = pack / "sections"
    sections.mkdir()
    for filename in [
        "00_abstract.md",
        "01_introduction.md",
        "02_data.md",
        "03_empirical_strategy.md",
        "04_results.md",
        "05_robustness.md",
    ]:
        (sections / filename).write_text(f"# {filename}\n\n[AUTHOR_INPUT_NEEDED]: polished prose.\n", encoding="utf-8")
    (pack / "main.md").write_text("short draft\n", encoding="utf-8")

    tier = evaluate_pack_tier(pack)

    assert tier.metrics["evidence_pack_status"] == "passed"
    assert "evidence_pack_invalid" not in tier.metrics["tier_b_blockers"]
    assert "did_tier_b_artifacts_missing" not in tier.metrics["tier_b_blockers"]
    assert {"words_total_below_2500", "core_placeholders_present"} <= set(tier.metrics["tier_b_blockers"])


def test_skill4econ_rdd_manifest_exposes_rdd_artifact_types(tmp_path: Path) -> None:
    run_dir = tmp_path / "rdd_run"
    run_dir.mkdir()
    _write_csv(
        run_dir / "model_table.csv",
        [{"term": "Robust", "coef": "-0.05", "std_error": "0.01", "p_value": "0.02", "ci_low": "-0.07", "ci_high": "-0.03", "n_obs": "500", "n_clusters": "50"}],
    )
    _write_csv(run_dir / "summary_stats.csv", [{"variable": "y", "mean": "5.4", "sd": "0.2", "unit": "log visits"}])
    _write_csv(run_dir / "rdd_bandwidth.csv", [{"side": "left", "bandwidth": "1.5"}])
    _write_json(run_dir / "rdd_density_test.json", {"status": "passed", "p_value": 0.6})
    _write_csv(run_dir / "covariate_continuity.csv", [{"covariate": "x0", "status": "passed", "p_value": "0.8"}])
    _write_json(
        run_dir / "rdd_diagnostics.json",
        {
            "density_test": {"status": "passed", "path": "rdd_density_test.json"},
            "covariate_continuity": {"status": "passed", "path": "covariate_continuity.csv"},
        },
    )
    (run_dir / "provenance.yaml").write_text("data_provenance: author_supplied\n", encoding="utf-8")
    write_artifact_manifest(
        run_dir / "artifact_manifest.json",
        workflow="rdrobust_rdd",
        run_id="fixture",
        run_dir=run_dir,
        status="success",
        required_artifacts=["model_table.csv", "summary_stats.csv", "rdd_bandwidth.csv", "rdd_diagnostics.json"],
    )

    pack = tmp_path / "econpaper_pack"
    result = write_evidence_ledger(run_dir=run_dir, out_dir=pack, summary_stats_path=run_dir / "summary_stats.csv")

    evidence_pack = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    artifact_types = {item["artifact_type"] for item in evidence_pack["artifacts"]}
    assert result.has_hard_blocks is False
    assert {
        "model_table",
        "summary_stats",
        "rdd_bandwidth",
        "rdd_diagnostics",
        "rdd_density_test",
        "covariate_continuity",
    } <= artifact_types


def test_w3_inference_audit_feeds_econpaper_evidence_pack_types(tmp_path: Path) -> None:
    spec = {
        "wcr": {
            "y": [1.0, 1.1, 1.2, 1.3, 1.4, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2],
            "X": [[1, idx / 10] for idx in range(12)],
            "clusters": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
            "R": [0, 1],
            "B": 29,
            "seed": 7,
        },
        "conley": {
            "y": [1.0, 1.2, 1.4, 1.5, 1.7, 1.9, 2.0, 2.1],
            "X": [[1, idx / 7] for idx in range(8)],
            "lon": [idx * 0.01 for idx in range(8)],
            "lat": [idx * 0.01 for idx in range(8)],
            "theta_km": 20,
            "terms": ["const", "x"],
        },
        "romano_wolf": {
            "stat_vector": [1.5, 2.0],
            "bootstrap_draws": [[0.5, 1.1], [1.2, 1.4], [2.2, 0.9], [0.7, 2.4]] * 8,
            "labels": ["h1", "h2"],
        },
        "mop_effective_f": {
            "effective_f": 16.0,
            "critical_value": 15.49,
            "source_backend": "stata_weakivtest",
        },
    }
    ctx = make_run_context("w3_inference_audit", "python", spec, "run", str(tmp_path / "runs"))
    manifest = w3_inference_audit(ctx)
    assert manifest["status"] == "ok"

    pack = tmp_path / "econpaper_pack"
    result = write_evidence_ledger(run_dir=ctx.run_dir, out_dir=pack)
    evidence_pack = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    artifact_types = {item["artifact_type"] for item in evidence_pack["artifacts"]}

    assert result.has_hard_blocks is False
    assert {
        "w3_null_imposed_wcr",
        "w3_conley",
        "w3_romano_wolf",
        "w3_effective_f",
    } <= artifact_types


def test_real_skill4econ_did_run_reaches_econpaper_tier_b_evidence_boundary(tmp_path: Path) -> None:
    spec = read_spec(ROOT / "skill4econ" / "examples" / "mini_panel" / "did_paper_run_spec.yml")
    spec["output_dir"] = str(tmp_path / "runs")
    ctx = make_run_context("did_paper_run", "workflow", spec, "run", str(tmp_path / "runs"))
    manifest = did_paper_run(ctx)
    assert manifest["status"] == "success"

    pack = tmp_path / "econpaper_pack"
    write_evidence_ledger(run_dir=ctx.run_dir, out_dir=pack, summary_stats_path=ctx.artifact("summary_stats.csv"))
    evidence_pack = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    artifact_types = {item["artifact_type"] for item in evidence_pack["artifacts"]}
    assert {"model_table", "event_study", "pretrend_test", "summary_stats", "robustness_grid"} <= artifact_types

    evidence_ids = [
        item["evidence_id"]
        for item in evidence_pack["evidence_items"]
        if isinstance(item, dict) and item.get("evidence_id")
    ]
    _write_json(pack / "claim_ledger.json", {"claims": [{"evidence_refs": evidence_ids}]})
    _write_json(pack / "design_profile.json", {"status": "passed", "diagnostics_missing": []})
    _write_json(pack / "reports" / "internal" / "global_coherence.json", {"status": "passed", "has_hard_blocks": False})
    _write_json(pack / "reports" / "internal" / "citation_safety_report.json", {"missing_citekeys": [], "citation_uses": []})
    _write_json(pack / "reports" / "internal" / "run_validation.json", {"data_provenance": "author_supplied"})
    sections = pack / "sections"
    sections.mkdir()
    for filename in [
        "00_abstract.md",
        "01_introduction.md",
        "02_data.md",
        "03_empirical_strategy.md",
        "04_results.md",
        "05_robustness.md",
    ]:
        (sections / filename).write_text(f"# {filename}\n\n[AUTHOR_INPUT_NEEDED]: polished prose.\n", encoding="utf-8")
    (pack / "main.md").write_text("short draft\n", encoding="utf-8")

    tier = evaluate_pack_tier(pack)
    assert tier.metrics["evidence_pack_status"] == "passed"
    assert "did_tier_b_artifacts_missing" not in tier.metrics["tier_b_blockers"]


def test_configured_skill4econ_did_run_feeds_econpaper_tier_a_artifact_boundary(tmp_path: Path) -> None:
    rows = []
    for unit in range(1, 21):
        ever = int(unit <= 10)
        region = "north" if unit % 2 == 0 else "south"
        size_group = "large" if unit in {1, 2, 3, 4, 5, 11, 12, 13, 14, 15} else "small"
        for year in range(2015, 2022):
            post = int(year >= 2019)
            rows.append(
                {
                    "firm_id": unit,
                    "year": year,
                    "y": 5.0
                    + unit * 0.2
                    + (year - 2015) * 0.1
                    + ever * post * (1.0 + 0.2 * (region == "north") + 0.1 * (size_group == "large")),
                    "treat": ever,
                    "post": post,
                    "placebo_post": int(year >= 2017),
                    "region": region,
                    "size_group": size_group,
                }
            )
    data = tmp_path / "configured_did.csv"
    pd.DataFrame(rows).to_csv(data, index=False)
    spec = {
        "data": str(data),
        "design_type": "simple_2x2_did",
        "id": "firm_id",
        "time": "year",
        "y": "y",
        "treat": "treat",
        "post": "post",
        "cluster": "firm_id",
        "engine_policy": "python",
        "event_window": [-2, 2],
        "base_period": -1,
        "placebo_tests": [{"name": "fake_2017_timing", "post": "placebo_post"}],
        "heterogeneity_dimensions": ["region", "size_group"],
        "variable_units": {"y": "index points"},
        "output_dir": str(tmp_path / "runs"),
    }
    ctx = make_run_context("did_paper_run", "workflow", spec, "run", str(tmp_path / "runs"))
    manifest = did_paper_run(ctx)
    assert manifest["status"] == "success"

    pack = tmp_path / "econpaper_pack"
    write_evidence_ledger(run_dir=ctx.run_dir, out_dir=pack, summary_stats_path=ctx.artifact("summary_stats.csv"))
    evidence_pack = json.loads((pack / "evidence_pack.json").read_text(encoding="utf-8"))
    artifact_types = {item["artifact_type"] for item in evidence_pack["artifacts"]}
    assert {
        "model_table",
        "event_study",
        "pretrend_test",
        "cohort_table",
        "robustness_grid",
        "placebo_tests",
        "heterogeneity",
        "summary_stats",
        "figure_manifest",
    } <= artifact_types

    evidence_ids = [
        item["evidence_id"]
        for item in evidence_pack["evidence_items"]
        if isinstance(item, dict) and item.get("evidence_id")
    ]
    _write_json(pack / "claim_ledger.json", {"claims": [{"evidence_refs": evidence_ids}]})
    _write_json(pack / "design_profile.json", {"status": "passed", "diagnostics_missing": []})
    _write_json(pack / "reports" / "internal" / "global_coherence.json", {"status": "passed", "has_hard_blocks": False})
    _write_json(pack / "reports" / "internal" / "citation_safety_report.json", {"missing_citekeys": [], "citation_uses": []})
    _write_json(pack / "reports" / "internal" / "run_validation.json", {"data_provenance": "author_supplied"})
    sections = pack / "sections"
    sections.mkdir()
    for filename in [
        "00_abstract.md",
        "01_introduction.md",
        "02_data.md",
        "03_empirical_strategy.md",
        "04_results.md",
        "05_robustness.md",
    ]:
        (sections / filename).write_text(f"# {filename}\n\n[AUTHOR_INPUT_NEEDED]: polished prose.\n", encoding="utf-8")
    (pack / "main.md").write_text("short draft\n", encoding="utf-8")

    tier = evaluate_pack_tier(pack)
    assert tier.metrics["did_tier_a_missing_artifacts"] == []
    assert tier.metrics["did_tier_a_incomplete_artifacts"] == []
