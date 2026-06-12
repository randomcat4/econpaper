from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from skill4econ.core import make_run_context, write_manifest, write_model_table
from skill4econ.python_wrappers import _ols_numpy, ols_cluster, rdrobust_rdd


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ols" / "cluster_reference.csv"


def test_ols_cluster_writes_t_inference_columns(tmp_path: Path) -> None:
    ctx = make_run_context(
        "ols_cluster",
        "python",
        {
            "data": str(FIXTURE),
            "y": "y",
            "x": ["x1", "x2"],
            "cluster": "cluster",
        },
        "run",
        str(tmp_path / "runs"),
    )

    manifest = ols_cluster(ctx)
    table = pd.read_csv(ctx.artifact("model_table.csv"))

    assert manifest["status"] == "ok"
    assert manifest["df_inference"] == 7
    assert manifest["n_clusters"] == 8
    assert {"ci_low", "ci_high", "df_inference"}.issubset(table.columns)
    assert {"wild_cluster_p_value", "wild_cluster_reps"}.issubset(table.columns)
    assert ctx.artifact("wild_cluster_bootstrap.csv").exists()
    assert manifest["wild_cluster_bootstrap"]["successful_reps"] >= 39
    assert set(table["df_inference"].astype(int)) == {7}
    assert ((table["ci_low"] < table["coef"]) & (table["coef"] < table["ci_high"])).all()


def test_few_cluster_inference_risk_degrades_main_estimator(tmp_path: Path) -> None:
    df = pd.read_csv(FIXTURE)
    work = df.copy()
    work["_const"] = 1.0
    ctx = make_run_context(
        "package_cluster_estimator",
        "python",
        {"data": str(FIXTURE), "y": "y", "x": ["x1", "x2"], "cluster": "cluster"},
        "run",
        str(tmp_path / "runs"),
    )

    rows, meta = _ols_numpy(work, "y", ["_const", "x1", "x2"], cluster="cluster")
    write_model_table(ctx, rows)
    manifest = write_manifest(ctx, "ok", estimator="test package cluster estimator", **meta)
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))

    assert manifest["paper_readiness"] == "supplementary_only"
    assert manifest["main_claim_available"] is False
    assert "FEW_CLUSTERS_INFERENCE_FRAGILE" in manifest["risk_codes"]
    risk_item = next(item for item in risk["risks"] if item["code"] == "FEW_CLUSTERS_INFERENCE_FRAGILE")
    assert risk_item["severity"] == "medium"
    assert risk_item["claim_degradation"] == "supplementary_only"
    assert "G=8" in risk_item["message"]
    assert "wild cluster bootstrap" in risk_item["required_fix"].lower()


def test_ols_numpy_cluster_matches_statsmodels_t_inference() -> None:
    try:
        import statsmodels.api as sm
    except ImportError as exc:
        pytest.skip(f"statsmodels is unavailable: {exc}")

    df = pd.read_csv(FIXTURE)
    work = df.copy()
    work["_const"] = 1.0
    terms = ["_const", "x1", "x2"]

    rows, meta = _ols_numpy(work, "y", terms, cluster="cluster")
    by_term = {row["term"]: row for row in rows}

    result = sm.OLS(work["y"], work[terms]).fit(
        cov_type="cluster",
        cov_kwds={"groups": work["cluster"], "use_correction": True},
        use_t=True,
    )
    conf_int = result.conf_int(alpha=0.05)

    assert meta["df_inference"] == df["cluster"].nunique() - 1
    for term in terms:
        row = by_term[term]
        assert row["coef"] == pytest.approx(float(result.params[term]), abs=1e-6)
        assert row["std_error"] == pytest.approx(float(result.bse[term]), abs=1e-6)
        assert row["p_value"] == pytest.approx(float(result.pvalues[term]), abs=1e-4)
        assert row["ci_low"] == pytest.approx(float(conf_int.loc[term, 0]), abs=1e-6)
        assert row["ci_high"] == pytest.approx(float(conf_int.loc[term, 1]), abs=1e-6)


def test_rdrobust_rdd_missing_dependency_fails_closed(tmp_path: Path) -> None:
    if importlib.util.find_spec("rdrobust") is not None:
        pytest.skip("rdrobust installed; missing-dependency branch is environment-specific")
    data = tmp_path / "rdd.csv"
    pd.DataFrame(
        {
            "running": [-2, -1, -0.5, 0.5, 1, 2],
            "y": [1.0, 1.1, 1.2, 2.0, 2.1, 2.2],
        }
    ).to_csv(data, index=False)
    ctx = make_run_context(
        "rdrobust_rdd",
        "python",
        {"data": str(data), "y": "y", "running": "running", "cutoff": 0},
        "run",
        str(tmp_path / "runs"),
    )

    manifest = rdrobust_rdd(ctx)

    assert manifest["status"] == "missing_dependency"
    assert manifest["package"] == "rdrobust"
    assert ctx.artifact("backend_unavailable.md").exists()


def test_rdrobust_rdd_writes_density_covariate_and_cluster_diagnostics(tmp_path: Path) -> None:
    if importlib.util.find_spec("rdrobust") is None or importlib.util.find_spec("rddensity") is None:
        pytest.skip("rdrobust/rddensity backends are not installed")
    rows = []
    for block in range(1, 161):
        distance = (block - 80.5) / 40
        inside = int(distance >= 0)
        for week in range(1, 9):
            rows.append(
                {
                    "block_id": block,
                    "week": week,
                    "running": distance,
                    "y": 5.0 + 0.1 * distance - 0.05 * inside + 0.004 * week,
                    "baseline_y": 5.0 + 0.025 * abs(distance) + 0.003 * week,
                    "access_index": 0.8 + 0.04 * abs(distance) - 0.001 * week,
                }
            )
    data = tmp_path / "rdd.csv"
    pd.DataFrame(rows).to_csv(data, index=False)
    ctx = make_run_context(
        "rdrobust_rdd",
        "python",
        {
            "data": str(data),
            "y": "y",
            "running": "running",
            "cutoff": 0,
            "bandwidth": 1.5,
            "cluster": "block_id",
            "covars": ["baseline_y", "access_index"],
            "covariate_continuity": ["baseline_y", "access_index"],
        },
        "run",
        str(tmp_path / "runs"),
    )

    manifest = rdrobust_rdd(ctx)
    model_table = pd.read_csv(ctx.artifact("model_table.csv"))
    diagnostics = json.loads(ctx.artifact("rdd_diagnostics.json").read_text(encoding="utf-8"))
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    evidence_types = {item.get("evidence_type") for item in artifact_manifest["artifacts"] if isinstance(item, dict)}

    assert manifest["status"] == "ok"
    assert set(model_table["n_clusters"].astype(int)) == {160}
    assert diagnostics["density_test"]["status"] == "passed"
    assert diagnostics["covariate_continuity"]["status"] == "passed"
    assert ctx.artifact("rdd_density_test.json").exists()
    assert ctx.artifact("covariate_continuity.csv").exists()
    assert {"rdd_bandwidth", "rdd_diagnostics", "rdd_density_test", "covariate_continuity"} <= evidence_types
