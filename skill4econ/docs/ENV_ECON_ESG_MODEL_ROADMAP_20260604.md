# Environment/ESG Econometrics Workflow Roadmap

Source status: GPT-5.5 Pro was asked to review environmental economics, ESG, Tian Zhihua, and Shao Shuai method needs. The browser response stalled before a full citation table. The usable partial guidance was: strong evidence/priority around DID/PSM-DID, staggered or continuous DID, spatial econometrics/SDM/spatial DID, DEA/efficiency, and threshold models; IV/RDD/DML/SFA should be downgraded unless paper-specific evidence or a tested local backend exists.

## Tonight P0 Workflows

- `psm_did_policy_run`: PSM/IPW overlap diagnostics + TWFE DID + optional Stata DRDID for declared 2x2 windows. PSM is not treated as identification proof.
- `spatial_spillover_run`: reduced-form neighbor exposure DID plus Stata spatial package preflight. Full SAR/SDM/SAC is not claimed.
- `mechanism_threshold_run`: mediation screen + panel threshold grid search + optional quantile heterogeneity screen.
- `efficiency_frontier_run`: DEA/SBM/Malmquist adapter workflow. Core DEA math is delegated to the existing local/vendored backend.

## Tian/Shao Method Confidence

- Strong/current priority: DID/PSM-DID, staggered/continuous DID, spatial spillover/spatial econometrics, DEA/efficiency, threshold/nonlinear mechanisms.
- Plausible but paper-specific: mechanism tests, heterogeneity by region/industry/finance constraints, green innovation or green finance channels, carbon/energy efficiency panels.
- Downgraded until verified: IV, RDD, DML/causal forest, SFA, full dynamic spatial Durbin. These need paper-specific confirmation or a tested backend before becoming P0.

## What `paper_run_v0.1` Means Here

- Stable YAML interface.
- `plan`, `audit`, `dry-run`, and `run` states.
- Required field validation before estimation.
- Machine-readable `manifest.json`, `audit.json`, `workflow_validation.json`, `warnings.json`, `step_results.json`, and `model_table.csv`.
- Human-readable `workflow_blueprint.md` and `research_report.md`.
- `rerun.bat` and `rerun.sh` for small agents.
- Explicit claim limits and failure conditions; no silent estimator fallback.

## P1 Deepening

- True matched-sample DID after `psm_ipw_match` exports matched IDs/weights and balance diagnostics.
- Full spatial SAR/SDM/SAC backend using local Stata `spxtregress` or `xsmle` only after a pass/fail fixture is validated.
- DEA second-stage regressions with FE/Tobit/bootstrap and score-file ingestion.
- Hansen-style threshold bootstrap confidence region.
- Mechanism bootstrap/Sobel-style uncertainty.
- Continuous treatment DID or dose-response DID for policy intensity/ESG intensity.
- Green innovation network spillover workflow with patent/text/network modules.
