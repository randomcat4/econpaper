from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from skill4econ.core import make_run_context
from skill4econ.python_wrappers import dml_irm_crossfit, dml_plr_crossfit, mediation_baron_kenny, synthetic_control_basic


def _mediation_fixture() -> pd.DataFrame:
    rows = []
    for i in range(60):
        treat = i % 2
        x = ((i * 7) % 11) - 5
        mediator_noise = (((i * 13) % 17) - 8) / 40
        outcome_noise = (((i * 19) % 23) - 11) / 50
        mediator = 0.5 + 0.85 * treat + 0.12 * x + mediator_noise
        y = 1.1 + 0.35 * treat + 1.15 * mediator + 0.18 * x + outcome_noise
        rows.append({"unit": i, "treat": treat, "x": x, "mediator": mediator, "y": y})
    return pd.DataFrame(rows)


def _synthetic_fixture() -> pd.DataFrame:
    rows = []
    for unit in range(21):
        unit_shift = ((unit * 7) % 13 - 6) / 20
        trend = ((unit * 5) % 7 - 3) / 100
        for time in range(1, 13):
            y = 2 + 0.25 * time + unit_shift + trend * time + (((unit * 11 + time * 3) % 17) - 8) / 200
            if unit == 0 and time >= 8:
                y += 1.6
            rows.append({"unit": unit, "time": time, "y": y})
    return pd.DataFrame(rows)


def _dml_fixture() -> pd.DataFrame:
    rows = []
    unit = 0
    for cluster in range(12):
        shock = ((cluster % 4) - 1.5) * 0.55
        for j in range(8):
            x1 = (j - 3.5) / 3 + (cluster % 3) * 0.08
            x2 = ((cluster * 3 + j * 5) % 11 - 5) / 5
            noise = (((cluster * 17 + j * 7) % 19) - 9) / 30
            d_cont = 0.45 * x1 - 0.25 * x2 + ((j % 3) - 1) * 0.18 + cluster * 0.015
            d_bin = (j + cluster) % 2
            y = 1.2 * d_cont + 0.75 * d_bin + 0.35 * x1 - 0.2 * x2 + shock + noise
            rows.append(
                {
                    "unit": unit,
                    "cluster": cluster,
                    "y": y,
                    "d_cont": d_cont,
                    "d_bin": d_bin,
                    "x1": x1,
                    "x2": x2,
                }
            )
            unit += 1
    return pd.DataFrame(rows)


def test_mediation_bootstrap_indirect_effect_is_reproducible(tmp_path: Path) -> None:
    data_path = tmp_path / "mediation.csv"
    _mediation_fixture().to_csv(data_path, index=False)
    spec = {
        "data": str(data_path),
        "y": "y",
        "treat": "treat",
        "mediator": "mediator",
        "x": ["x"],
        "bootstrap_reps": 199,
        "bootstrap_seed": 12345,
    }

    first_ctx = make_run_context("mediation_baron_kenny", "python", spec, "run", str(tmp_path / "runs"))
    second_ctx = make_run_context("mediation_baron_kenny", "python", spec, "run", str(tmp_path / "runs"))
    first_manifest = mediation_baron_kenny(first_ctx)
    mediation_baron_kenny(second_ctx)

    first = pd.read_csv(first_ctx.artifact("model_table.csv")).set_index("term").loc["indirect_effect_ab"]
    second = pd.read_csv(second_ctx.artifact("model_table.csv")).set_index("term").loc["indirect_effect_ab"]
    bootstrap = json.loads(first_ctx.artifact("mediation_bootstrap.json").read_text(encoding="utf-8"))
    audit = first_ctx.artifact("audit.json").read_text(encoding="utf-8")

    assert first_manifest["not_valid_for"] == ["causal mediation under sequential ignorability"]
    assert bootstrap["successful_reps"] == 199
    assert first["ci_low"] > 0
    assert first["ci_low"] < first["coef"] < first["ci_high"]
    assert first["ci_low"] == second["ci_low"]
    assert first["ci_high"] == second["ci_high"]
    assert "Baron-Kenny, not causal mediation" in audit


def test_synthetic_control_placebo_p_value_and_artifact(tmp_path: Path) -> None:
    data_path = tmp_path / "synthetic.csv"
    _synthetic_fixture().to_csv(data_path, index=False)
    spec = {
        "data": str(data_path),
        "y": "y",
        "id": "unit",
        "time": "time",
        "treated_unit": 0,
        "treatment_time": 8,
    }
    ctx = make_run_context("synthetic_control_basic", "python", spec, "run", str(tmp_path / "runs"))

    manifest = synthetic_control_basic(ctx)
    model = pd.read_csv(ctx.artifact("model_table.csv")).set_index("term")
    placebo = pd.read_csv(ctx.artifact("synthetic_placebo.csv"))

    assert manifest["status"] == "ok"
    assert ctx.artifact("synthetic_placebo.csv").exists()
    assert "placebo_permutation_p" in model.index
    assert model.loc["placebo_permutation_p", "coef"] < 0.1
    assert len(placebo[placebo["is_treated_unit"] == False]) >= 10


def test_dml_clustered_score_se_differs_from_iid(tmp_path: Path) -> None:
    data_path = tmp_path / "dml.csv"
    _dml_fixture().to_csv(data_path, index=False)
    base = {
        "data": str(data_path),
        "y": "y",
        "x": ["x1", "x2"],
        "folds": 3,
        "random_seed": 7,
        "learner": "gradient_boosting",
    }

    iid_ctx = make_run_context("dml_plr_crossfit", "python", {**base, "treatment": "d_cont"}, "run", str(tmp_path / "runs"))
    cluster_ctx = make_run_context(
        "dml_plr_crossfit",
        "python",
        {**base, "treatment": "d_cont", "cluster": "cluster"},
        "run",
        str(tmp_path / "runs"),
    )
    dml_plr_crossfit(iid_ctx)
    cluster_manifest = dml_plr_crossfit(cluster_ctx)
    iid_se = float(pd.read_csv(iid_ctx.artifact("model_table.csv")).set_index("term").loc["theta_plr", "std_error"])
    cluster_table = pd.read_csv(cluster_ctx.artifact("model_table.csv")).set_index("term")
    cluster_se = float(cluster_table.loc["theta_plr", "std_error"])
    diagnostics = json.loads(cluster_ctx.artifact("dml_diagnostics.json").read_text(encoding="utf-8"))

    assert diagnostics["cluster_se"]["mode"] == "cluster_summed_orthogonal_score"
    assert cluster_table.loc["theta_plr", "n_clusters"] == 12
    assert "FEW_CLUSTERS_INFERENCE_FRAGILE" in cluster_manifest["risk_codes"]
    assert not math.isclose(iid_se, cluster_se)

    iid_irm_ctx = make_run_context("dml_irm_crossfit", "python", {**base, "treatment": "d_bin"}, "run", str(tmp_path / "runs"))
    cluster_irm_ctx = make_run_context(
        "dml_irm_crossfit",
        "python",
        {**base, "treatment": "d_bin", "cluster": "cluster"},
        "run",
        str(tmp_path / "runs"),
    )
    dml_irm_crossfit(iid_irm_ctx)
    dml_irm_crossfit(cluster_irm_ctx)
    iid_irm = pd.read_csv(iid_irm_ctx.artifact("model_table.csv")).set_index("term")
    cluster_irm = pd.read_csv(cluster_irm_ctx.artifact("model_table.csv")).set_index("term")
    cluster_irm_diagnostics = json.loads(cluster_irm_ctx.artifact("dml_diagnostics.json").read_text(encoding="utf-8"))

    assert cluster_irm_diagnostics["cluster_se"]["mode"] == "cluster_summed_aipw_score"
    assert not math.isclose(float(iid_irm.loc["ATE_aipw", "std_error"]), float(cluster_irm.loc["ATE_aipw", "std_error"]))
