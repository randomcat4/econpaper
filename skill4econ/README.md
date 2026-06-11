# skill4econ

Repo-local, agent-callable econometrics capability pack for econpaper.

This folder is intentionally an orchestration layer, not a new econometrics
library. Wrappers call existing Stata/Python backends, write machine-readable
manifests, and fail loudly when dependencies are missing.

## Layout

The Python package lives under `src/skill4econ`. Human-facing assets stay at the
repository root:

- `skills/`: agent-facing skill files.
- `examples/`: runnable specs and fixture data.
- `docs/`: contracts, runbooks, known bugs, and roadmaps.
- `integrations/easypaper-econ-finance/`: EasyPaper-derived snapshot for
  economics and finance manuscript generation.

See `docs/REPO_STRUCTURE.md` for the full map.

## Rules

- No automatic package installation.
- No fabricated significance, interpretation, or paper conclusions.
- Every run writes `manifest.json`, `audit.json`, stdout/stderr logs when
  relevant, and a model table when an estimator actually runs.
- Every method supports four states: `--plan`, `--dry-run`, `--audit`, `--run`.
- DEA/SBM/Malmquist ships as a vendored backend at
  `skill4econ.backends.dea` (in-process, self-contained). External overrides
  remain available via `spec.dea.backend_path` or `SKILL4ECON_DEA_BACKEND`.
- Stata and the DEA override path are discovered, never hardcoded. See
  "Backend discovery" below.

## Backend discovery

Both the Stata executable and an optional external DEA backend are resolved
through a layered chain (most specific to most general):

1. The per-run spec (`spec.stata.executable`, `spec.dea.backend_path`).
2. Environment variables `SKILL4ECON_STATA`, `SKILL4ECON_DEA_BACKEND`.
3. The user config file at `~/.skill4econ/config.toml` (override the path
   with `SKILL4ECON_CONFIG`):

   ```toml
   [stata]
   executable = "C:/Program Files/Stata18/StataMP-64.exe"
   # batch_args = ["/e", "do"]   # optional override; defaults to Stata edition

   [dea]
   backend_path = "D:/path/to/your/dea_calculator"  # optional override
   ```

4. Stata only: `shutil.which` lookup for `stata`, `stata-mp`, `stata-se`,
   `stata-be`, `StataMP-64`, `StataSE-64`, `StataBE-64`.
5. Stata only: common install directories on Windows
   (`<drive>:\stata*`, `Program Files\Stata*`), macOS
   (`/Applications/Stata*/StataMP.app/...`), and Linux (`/usr/local/stata*`,
   `/opt/stata*`).
6. DEA only: fall through to the vendored module
   `skill4econ.backends.dea`.

If Stata cannot be resolved, every Stata wrapper writes
`manifest.status == missing_dependency` with the full discovery chain.

## CLI

```powershell
python -m pip install -e .
conda run -n base python -m skill4econ.cli list
conda run -n base python -m skill4econ.cli run --engine python --method data_audit --spec examples/mini_panel/panel_spec.yml --run
conda run -n base python -m skill4econ.cli workflow --name did_paper_run --spec examples/mini_panel/did_paper_run_spec.yml --run
```

Stata example:

```powershell
conda run -n base python -m skill4econ.cli run --engine stata --method stata_preflight --run
```

Smoke test:

```powershell
conda run -n base python -m skill4econ.cli smoke --suite all --strict
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
```

The current base environment has a broken `statsmodels.api` import path, so the
P0 Python wrappers use auditable `numpy/pandas` fallbacks where needed. Use the
Stata wrappers or vendor-backed packages for publication-grade inference.

## Current Runnable Model Set

Python wrappers include OLS with clustered covariance, panel FE/RE, TWFE DID,
event-study TWFE, reduced-form spatial spillover DID, spatial exposure DID,
spatial W audit, global/basic local Moran preflight, dependency-gated R
`spdep` LISA, SAR/SEM/SDM impact-decomposition adapter, spatial SE comparison,
W sensitivity, sklearn cross-fitting DML PLR/IRM fallbacks,
dependency-gated DoubleML/EconML adapters, IV 2SLS, local-linear RDD,
quantile regression, threshold panel grid search, Baron-Kenny style mediation,
basic synthetic control, PSM/IPW, finance ML split audit, diagnostics, and the
external DEA adapter.

Stata wrappers include OLS, panel FE, TWFE DID, staggered DID via local
csdid/drdid, modern DID entries `dr_did_2x2`, `cs_did_attgt`, and
`did_imputation_event`, IV 2SLS, qreg, rdrobust, reghdfe from local vendor
source, teffects PSM, xtabond, PPML FE through local `ppmlhdfe` with no
poisson fallback, and spatial command preflight.

## Modern DID Core

The main DID product menu is deliberately small:

- `dr_did_2x2`: Sant'Anna-Zhao DRDID for simple two-by-two DID with
  pre-treatment covariates. This is the default answer to "PSM-DID" for a
  simple treated/control, pre/post design.
- `cs_did_attgt`: Callaway-Sant'Anna ATT(g,t) via local Stata `csdid/drdid`
  for staggered absorbing binary treatment. It exports `att_gt.csv`,
  `simple_att.csv`, `event_study.csv`, and a combined `model_table.csv`.
- `did_imputation_event`: Borusyak-Jaravel-Spiess imputation DID via local
  Stata `did_imputation` and `reghdfe`, for dynamic effects and pre-trend
  tests in staggered rollout designs.

`psm_did` remains a legacy/interface label. Do not use PSM followed by TWFE as
the primary staggered DID estimator; route users to the modern DID core unless
they explicitly request legacy matching diagnostics.

Spatial DID is deliberately named reduced-form: it estimates treatment exposure
`D` and neighbor exposure `W*D` with fixed effects. It is not a full SAR/SDM
panel estimator and should not be described as solving spatial endogeneity.
Use `spatial_exposure_did` when the agent needs lagged/cumulative exposure,
distance-ring exposure, near/far controls, buffer deletion, contaminated-control
diagnostics, separate local/spillover effect tables, and a local-treatment
`did_common_output.json` bridge. The common output is for the local treatment
coefficient only; the W*treatment exposure coefficient remains reduced-form.
Use `spatial_panel_model_adapter` only with backend output that includes
direct/indirect/total effects before making SDM-style impact claims.
The adapter writes `backend_canonical_result.json`; parser-only output is not a
live SAR/SEM/SDM backend run.

The DML fallbacks use sklearn cross-fitting and write `dml_diagnostics.json`.
They are not the `DoubleML` or `EconML` packages; the package adapters return
`missing_dependency` unless those packages are actually importable.

## PaperRun Workflows

`did_paper_run` is the first paper-oriented workflow. It does not add a new
estimator; it compiles existing DID methods into one reviewer-aware run
directory with preflight diagnostics, sample-construction records, treatment
timing summaries, event-study support, warnings, a consolidated model table, a
human-readable report, and rerun scripts.

Workflow statuses are more specific than method statuses:

- `success`: required outputs for the declared DID design were generated.
- `degraded`: usable outputs exist, but an engine substitution or partial
  limitation was recorded.
- `not_paper_ready`: some estimates exist, but the package is not a complete
  paper-ready DID result.
- `failed`: preflight or core estimation blocked the run.

For `design_type: staggered_adoption_did`, TWFE-only output is never marked as
full success when csdid/drdid or another staggered DID alternative is missing.
