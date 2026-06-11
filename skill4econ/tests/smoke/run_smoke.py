from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "skill4econ" / "examples" / "mini_panel"


def write_fixture() -> None:
    EXAMPLE.mkdir(parents=True, exist_ok=True)
    path = EXAMPLE / "mini_panel.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "firm_id",
                "year",
                "y",
                "x1",
                "x2",
                "z",
                "treat",
                "post",
                "gvar",
                "mediator",
                "count_y",
                "running",
                "lon",
                "lat",
            ],
        )
        writer.writeheader()
        for firm in range(1, 11):
            treated = 1 if firm <= 5 else 0
            for year in range(2016, 2022):
                post = 1 if year >= 2019 else 0
                running = (firm - 5.5) / 2 + (year - 2018) / 10
                wiggle = ((firm * 17 + year * 11) % 13) / 100
                x1 = firm * 0.2 + (year - 2016) * 0.1 + wiggle
                z = firm * 0.3 + (year - 2016) * 0.2 + ((firm + year) % 7) / 80
                x2 = 0.6 * z + treated * 0.1 + ((firm * year) % 9) / 90
                gvar = 2019 if treated else 0
                mediator = 0.35 * x1 + 0.2 * x2 + 0.7 * treated + (year - 2016) * 0.03
                y = 1 + 0.5 * x1 + 0.8 * x2 + 0.4 * mediator + 1.2 * treated * post + firm * 0.03 + ((firm * 19 + year * 5) % 17) / 120
                count_y = 2 + y + firm * 0.1
                writer.writerow(
                    {
                        "firm_id": firm,
                        "year": year,
                        "y": round(y, 4),
                        "x1": round(x1, 4),
                        "x2": round(x2, 4),
                        "z": round(z, 4),
                        "treat": treated,
                        "post": post,
                        "gvar": gvar,
                        "mediator": round(mediator, 4),
                        "count_y": round(count_y, 4),
                        "running": round(running, 4),
                        "lon": round(-100 + firm * 0.4, 4),
                        "lat": round(35 + firm * 0.2, 4),
                    }
                )
    staggered_path = EXAMPLE / "staggered_panel.csv"
    with staggered_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "firm_id",
                "year",
                "y",
                "x1",
                "x2",
                "z",
                "ever_treated",
                "treat",
                "post",
                "gvar",
                "mediator",
                "count_y",
                "running",
            ],
        )
        writer.writeheader()
        for firm in range(1, 161):
            if firm <= 40:
                gvar = 2018
            elif firm <= 80:
                gvar = 2019
            elif firm <= 120:
                gvar = 2020
            else:
                gvar = 0
            ever_treated = 1 if gvar else 0
            firm_fe = firm * 0.07
            for year in range(2015, 2023):
                post = 1 if year >= 2019 else 0
                treated_now = 1 if gvar and year >= gvar else 0
                rel = year - gvar if gvar else -99
                wiggle = ((firm * 13 + year * 7) % 17) / 100
                x1 = firm * 0.05 + (year - 2015) * 0.08 + wiggle
                z = firm * 0.11 + (year - 2015) * 0.05 + ((firm + year) % 11) / 90
                x2 = 0.45 * z + ((firm * year) % 13) / 120
                mediator = 0.25 * x1 + 0.15 * x2 + 0.2 * treated_now
                effect = treated_now * (0.9 + 0.18 * max(rel, 0))
                y = 2 + firm_fe + 0.18 * (year - 2015) + 0.35 * x1 + 0.25 * x2 + effect
                y += ((firm * 19 + year * 5) % 23) / 200
                count_y = 3 + y + firm * 0.05
                running = (firm - 80.5) / 20 + (year - 2018) / 10
                writer.writerow(
                    {
                        "firm_id": firm,
                        "year": year,
                        "y": round(y, 4),
                        "x1": round(x1, 4),
                        "x2": round(x2, 4),
                        "z": round(z, 4),
                        "ever_treated": ever_treated,
                        "treat": treated_now,
                        "post": post,
                        "gvar": gvar,
                        "mediator": round(mediator, 4),
                        "count_y": round(count_y, 4),
                        "running": round(running, 4),
                    }
                )
    try:
        import pandas as pd

        rows = []
        for year in [2020, 2021]:
            for idx, dmu in enumerate(["A", "B", "C"], start=1):
                year_shift = year - 2020
                rows.append(
                    {
                        "dmu": dmu,
                        "year": year,
                        "input_labor": 5 + idx + year_shift,
                        "input_capital": 10 + idx * 2 + year_shift,
                        "good_output_1": 20 + idx * 3 + year_shift * 2,
                        "good_output_2": 15 + idx * 2 + year_shift * 2,
                        "bad_output": 2 + idx * 0.2 + year_shift * 0.1,
                    }
                )
        pd.DataFrame(rows).to_excel(EXAMPLE / "dea_t1.xlsx")
    except Exception as exc:
        raise RuntimeError(f"Failed to write DEA XLSX fixture: {exc}") from exc
    with (EXAMPLE / "spatial_weights.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target", "weight", "distance_km"])
        writer.writeheader()
        edges = [
            (1, 2, 1.0, 30),
            (2, 1, 0.5, 30),
            (2, 3, 0.5, 35),
            (3, 2, 0.5, 35),
            (3, 4, 0.5, 40),
            (4, 3, 0.5, 40),
            (4, 5, 0.5, 45),
            (5, 4, 0.5, 45),
            (5, 6, 0.5, 50),
            (6, 5, 0.5, 50),
            (6, 7, 0.5, 60),
            (7, 6, 0.5, 60),
            (7, 8, 0.5, 70),
            (8, 7, 0.5, 70),
            (8, 9, 0.5, 80),
            (9, 8, 0.5, 80),
            (9, 10, 0.5, 90),
            (10, 9, 1.0, 90),
        ]
        for source, target, weight, distance in edges:
            writer.writerow({"source": source, "target": target, "weight": weight, "distance_km": distance})
    with (EXAMPLE / "spatial_weights_alt.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target", "weight", "distance_km"])
        writer.writeheader()
        for source, target, weight, distance in [
            (6, 1, 1.0, 75),
            (7, 2, 1.0, 80),
            (8, 3, 1.0, 85),
            (9, 4, 1.0, 90),
            (10, 5, 1.0, 95),
            (1, 6, 1.0, 75),
            (2, 7, 1.0, 80),
            (3, 8, 1.0, 85),
            (4, 9, 1.0, 90),
            (5, 10, 1.0, 95),
        ]:
            writer.writerow({"source": source, "target": target, "weight": weight, "distance_km": distance})
    with (EXAMPLE / "spatial_impacts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "effect", "direct", "indirect", "total", "std_error", "p_value"])
        writer.writeheader()
        writer.writerow({"model": "SDM", "effect": "treat", "direct": 0.8, "indirect": 0.25, "total": 1.05, "std_error": 0.2, "p_value": 0.01})
    with (EXAMPLE / "spatial_w_sensitivity_panel.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["city", "year", "y", "treat", "lon", "lat"])
        writer.writeheader()
        units = list("ABCDEFGH")
        for year in range(2018, 2023):
            post = year >= 2020
            for idx, unit in enumerate(units):
                treat = 1 if unit == "A" and post else 0
                y = 0.2 * idx + 0.1 * (year - 2018)
                if unit in {"B", "D", "E"} and post:
                    y += 2.0
                if unit in {"F", "G", "H"} and post:
                    y -= 2.0
                writer.writerow({"city": unit, "year": year, "y": round(y, 4), "treat": treat, "lon": round(idx * 0.1, 4), "lat": 0.0})
    for name, sources in {
        "w_sensitivity_w1.csv": list("BDE"),
        "w_sensitivity_w2.csv": list("FGH"),
        "w_sensitivity_w3.csv": list("BDEFGH"),
    }.items():
        with (EXAMPLE / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["source", "target", "weight", "distance_km"])
            writer.writeheader()
            for source in sources:
                writer.writerow({"source": source, "target": "A", "weight": 1.0, "distance_km": 50.0})
    (EXAMPLE / "data_contract.yml").write_text(
        """panel:
  unit_id: firm_id
  time_id: year
  outcome: y
  treatment: treat
  first_treat_year: gvar
  covariates:
    - x1
    - x2
  fixed_effects:
    - unit
    - time
  cluster:
    - firm_id
policy:
  name: smoke_policy
  level: firm
  treatment_coding: simple_2x2
  anticipation_periods: 0
""",
        encoding="utf-8",
    )
    (EXAMPLE / "psm_did_policy_run_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
data_contract: skill4econ/examples/mini_panel/data_contract.yml
id: firm_id
time: year
y: y
treat: treat
post: post
x: [x1, x2]
cluster: firm_id
drdid_sample_if: inlist(year, 2018, 2019)
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "spatial_spillover_run_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
weights: skill4econ/examples/mini_panel/spatial_weights.csv
id: firm_id
time: year
y: y
treat: treat
post: post
x: [x1, x2]
cluster: firm_id
row_standardize: true
include_wx: true
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "spatial_exposure_did_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
weights: skill4econ/examples/mini_panel/spatial_weights.csv
id: firm_id
time: year
y: y
treat: treat
post: post
cluster: firm_id
row_standardize: true
distance_rings_km: [50, 100]
near_exposure_threshold: 0
run_event_study: false
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "spatial_moran_preflight_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
weights: skill4econ/examples/mini_panel/spatial_weights.csv
id: firm_id
time: year
y: y
treat: treat
row_standardize: true
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "spatial_spdep_lisa_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
weights: skill4econ/examples/mini_panel/spatial_weights.csv
id: firm_id
time: year
y: y
treat: treat
row_standardize: true
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "spatial_panel_model_adapter_spec.yml").write_text(
        """impact_decomposition: skill4econ/examples/mini_panel/spatial_impacts.csv
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "spatial_se_comparison_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
weights: skill4econ/examples/mini_panel/spatial_weights.csv
id: firm_id
time: year
y: y
treat: treat
post: post
cluster: firm_id
lon: lon
lat: lat
spatial_se_cutoffs_km: [50, 150]
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "spatial_w_sensitivity_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/spatial_w_sensitivity_panel.csv
weights: skill4econ/examples/mini_panel/w_sensitivity_w1.csv
weight_paths:
  - skill4econ/examples/mini_panel/w_sensitivity_w2.csv
  - skill4econ/examples/mini_panel/w_sensitivity_w3.csv
id: city
time: year
y: y
treat: treat
near_exposure_threshold: 0
run_event_study: false
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "mechanism_threshold_run_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
id: firm_id
time: year
y: y
treat: treat
mediator: mediator
threshold: x2
x: [x1]
trim: 0.15
grid_size: 8
quantile: 0.5
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "efficiency_frontier_run_spec.yml").write_text(
        """data: skill4econ/examples/mini_panel/dea_t1.xlsx
output_dir: skill4econ/runs
dea:
  dmus: 3
  periods: 2
  nx: 2
  ny: 2
  nb: 1
  undesirable: 1
  sup: 0
""",
        encoding="utf-8",
    )
    (EXAMPLE / "bad_psm_did_missing_treat.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
id: firm_id
time: year
y: y
treat: missing_treat
post: post
x: [x1, x2]
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "bad_spatial_missing_weights.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
id: firm_id
time: year
y: y
treat: treat
post: post
x: [x1, x2]
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "bad_mechanism_missing_mediator.yml").write_text(
        """data: skill4econ/examples/mini_panel/mini_panel.csv
id: firm_id
time: year
y: y
treat: treat
threshold: x2
x: [x1]
output_dir: skill4econ/runs
""",
        encoding="utf-8",
    )
    (EXAMPLE / "bad_efficiency_missing_dea_params.yml").write_text(
        """data: skill4econ/examples/mini_panel/dea_t1.xlsx
output_dir: skill4econ/runs
dea:
  dmus: 3
""",
        encoding="utf-8",
    )


def run_cmd(
    args: list[str],
    expect_ok: bool = True,
    acceptable_statuses: set[str] | None = None,
) -> dict:
    cmd = [sys.executable, "-m", "skill4econ.cli", *args]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if expect_ok and proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")
    last = proc.stdout.strip().splitlines()[-1]
    try:
        payload = json.loads(last)
    except Exception:
        payload = {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
    if expect_ok and isinstance(payload, dict):
        manifest = payload.get("manifest") if isinstance(payload.get("manifest"), dict) else {}
        status = manifest.get("status")
        ok_statuses = acceptable_statuses or {"ok"}
        if status and status not in ok_statuses:
            raise RuntimeError(f"Command returned non-ok manifest: {cmd}\n{json.dumps(payload, indent=2)}")
        assert_contract_artifacts(payload)
    return payload


def assert_contract_artifacts(payload: dict) -> None:
    run_dir = Path(str(payload.get("run_dir") or payload.get("manifest", {}).get("run_dir") or ""))
    if not run_dir.exists():
        raise RuntimeError(f"Run directory not found in payload: {payload}")
    required = [
        "manifest.json",
        "artifact_manifest.json",
        "reviewer_risk.json",
        "run_config_resolved.yaml",
        "run_log.md",
    ]
    for name in required:
        if not (run_dir / name).exists():
            raise RuntimeError(f"Missing required contract artifact: {run_dir / name}")
    artifact_manifest = json.loads((run_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    missing = artifact_manifest.get("missing_required_artifacts") or []
    if missing:
        raise RuntimeError(f"artifact_manifest reports missing required artifacts: {missing}")
    for item in artifact_manifest.get("artifacts") or []:
        rel = item.get("path")
        if not rel:
            raise RuntimeError(f"artifact_manifest entry is missing path: {item}")
        if not (run_dir / rel).exists():
            raise RuntimeError(f"artifact_manifest path does not exist: {run_dir / rel}")
    workflow = payload.get("manifest", {}).get("workflow") or artifact_manifest.get("workflow")
    if workflow == "did_paper_run":
        for rel in [
            "did_design.json",
            "estimator_routing.json",
            "selected_estimators.json",
            "skipped_estimators.json",
            "tables/did_estimator_comparison.csv",
            "tables/did_estimator_comparison.md",
        ]:
            if not (run_dir / rel).exists():
                raise RuntimeError(f"did_paper_run missing DID artifact: {run_dir / rel}")
        common_outputs = [
            item.get("path")
            for item in artifact_manifest.get("artifacts") or []
            if str(item.get("path", "")).endswith("did_common_output.json")
        ]
        if not common_outputs:
            raise RuntimeError(f"did_paper_run did not register any did_common_output.json in {run_dir}")


def collect_reviewer_risk_codes(results: list[dict]) -> set[str]:
    codes: set[str] = set()
    for payload in results:
        run_dir = Path(str(payload.get("run_dir") or payload.get("manifest", {}).get("run_dir") or ""))
        path = run_dir / "reviewer_risk.json"
        if not path.exists():
            continue
        risk = json.loads(path.read_text(encoding="utf-8"))
        for item in risk.get("risks") or []:
            code = item.get("code")
            if code:
                codes.add(str(code))
    return codes


def main() -> int:
    write_fixture()
    checks = [
        ["run", "--engine", "python", "--method", "py_preflight", "--run"],
        ["run", "--engine", "python", "--method", "data_audit", "--spec", str(EXAMPLE / "panel_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "ols_cluster", "--spec", str(EXAMPLE / "panel_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "panel_fe_re", "--spec", str(EXAMPLE / "panel_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "did_twfe_event", "--spec", str(EXAMPLE / "did_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "did_event_study", "--spec", str(EXAMPLE / "event_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "spatial_did_reduced_form", "--spec", str(EXAMPLE / "spatial_did_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "spatial_exposure_did", "--spec", str(EXAMPLE / "spatial_exposure_did_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "spatial_moran_preflight", "--spec", str(EXAMPLE / "spatial_moran_preflight_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "spatial_panel_model_adapter", "--spec", str(EXAMPLE / "spatial_panel_model_adapter_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "spatial_se_comparison", "--spec", str(EXAMPLE / "spatial_se_comparison_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "spatial_w_sensitivity", "--spec", str(EXAMPLE / "spatial_w_sensitivity_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "iv_2sls", "--spec", str(EXAMPLE / "iv_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "dml_plr_crossfit", "--spec", str(EXAMPLE / "dml_plr_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "dml_irm_crossfit", "--spec", str(EXAMPLE / "dml_irm_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "rdd_local_linear", "--spec", str(EXAMPLE / "rdd_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "quantile_regression", "--spec", str(EXAMPLE / "quantile_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "threshold_panel", "--spec", str(EXAMPLE / "threshold_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "mediation_moderation", "--spec", str(EXAMPLE / "mediation_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "synthetic_control", "--spec", str(EXAMPLE / "synth_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "psm_ipw_match", "--spec", str(EXAMPLE / "psm_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "ml_prediction_audit", "--spec", str(EXAMPLE / "finance_ml_spec.yml"), "--run"],
        ["run", "--engine", "python", "--method", "dea_sbm_malmquist_adapter", "--spec", str(EXAMPLE / "dea_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "stata_preflight", "--run"],
        ["run", "--engine", "stata", "--method", "ols_cluster", "--spec", str(EXAMPLE / "panel_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "reghdfe_fe", "--spec", str(EXAMPLE / "panel_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "csdid_staggered", "--spec", str(EXAMPLE / "csdid_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "dr_did_2x2", "--spec", str(EXAMPLE / "dr_did_2x2_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "cs_did_attgt", "--spec", str(EXAMPLE / "cs_did_attgt_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "did_imputation_event", "--spec", str(EXAMPLE / "did_imputation_event_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "quantile_regression", "--spec", str(EXAMPLE / "quantile_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "rdrobust_rdd", "--spec", str(EXAMPLE / "rdd_spec.yml"), "--run"],
        ["run", "--engine", "stata", "--method", "poisson_ppml_fe", "--spec", str(EXAMPLE / "ppml_spec.yml"), "--run"],
    ]
    results = []
    for check in checks:
        print(f"[smoke] {' '.join(check)}", flush=True)
        results.append(run_cmd(check))
        manifest = results[-1].get("manifest") if isinstance(results[-1], dict) else {}
        print(f"[smoke] status={manifest.get('status')} method={manifest.get('method')}", flush=True)
    results.append(
        run_cmd(
            ["run", "--engine", "python", "--method", "spatial_spdep_lisa", "--spec", str(EXAMPLE / "spatial_spdep_lisa_spec.yml"), "--run"],
            acceptable_statuses={"ok", "missing_dependency"},
        )
    )
    results.append(
        run_cmd(
            [
                "workflow",
                "--name",
                "did_paper_run",
                "--spec",
                str(EXAMPLE / "did_paper_run_spec.yml"),
                "--run",
            ],
            acceptable_statuses={"success"},
        )
    )
    for workflow, spec in [
        ("psm_did_policy_run", "psm_did_policy_run_spec.yml"),
        ("spatial_spillover_run", "spatial_spillover_run_spec.yml"),
        ("mechanism_threshold_run", "mechanism_threshold_run_spec.yml"),
        ("efficiency_frontier_run", "efficiency_frontier_run_spec.yml"),
    ]:
        results.append(
            run_cmd(
                [
                    "workflow",
                    "--name",
                    workflow,
                    "--spec",
                    str(EXAMPLE / spec),
                    "--run",
                ],
                acceptable_statuses={"success"},
            )
        )
    for workflow, spec in [
        ("psm_did_policy_run", "bad_psm_did_missing_treat.yml"),
        ("spatial_spillover_run", "bad_spatial_missing_weights.yml"),
        ("mechanism_threshold_run", "bad_mechanism_missing_mediator.yml"),
        ("efficiency_frontier_run", "bad_efficiency_missing_dea_params.yml"),
    ]:
        results.append(
            run_cmd(
                [
                    "workflow",
                    "--name",
                    workflow,
                    "--spec",
                    str(EXAMPLE / spec),
                    "--audit",
                ],
                acceptable_statuses={"failed"},
            )
        )
    risk_codes = collect_reviewer_risk_codes(results)
    if len(risk_codes) < 5:
        raise RuntimeError(f"Expected at least 5 reviewer risk codes; got {sorted(risk_codes)}")
    print(json.dumps({"status": "ok", "checks": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
