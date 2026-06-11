# Agent Usage

Use `skill4econ` when an econpaper agent needs an econometric model as a
callable tool.

## Contract

Agents should call:

```powershell
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method METHOD --run
```

or:

```powershell
conda run -n base python -m skill4econ.cli run --spec SPEC --engine stata --method METHOD --run
```

Inspect `manifest.json` and `audit.json` before using any outputs. If status is
`failed`, `missing_dependency`, or `interface_only`, do not write empirical
claims from that run.

For downstream EasyPaper handoff, treat `export/adapter` as the only supported
bundle boundary. EasyPaper should consume declared artifacts and validation
metadata, not raw table snippets or agent-written claims. A run marked
`failed`, `missing_dependency`, `interface_only`, or parser-only is still useful
handoff context, but it is a risk/revision signal rather than evidence for a
paper claim. Finance tier-1 gaps remain adapter specs unless the referenced run
directory contains validated artifacts from a real backend or supported Python
implementation.

When running CLI smoke from a source checkout that has not been installed,
PowerShell sessions may need:

```powershell
$env:PYTHONPATH = "src"
conda run -n base python -m skill4econ.cli smoke --suite contracts --strict
```

For paper-oriented DID runs, agents can call:

```powershell
conda run -n base python -m skill4econ.cli workflow --name did_paper_run --spec SPEC --run
```

Workflow statuses are `success`, `degraded`, `not_paper_ready`, and `failed`.
Only `success` means the declared DID workflow produced the required package.
`degraded` and `not_paper_ready` may still contain useful artifacts, but agents
must surface the warnings before making any empirical claim. For staggered
adoption DID, TWFE-only output is not paper-ready without a successful
csdid/drdid-style alternative.

Every `did_paper_run` writes routing and common-schema outputs:

- `did_design.json`: detected design, support diagnostics, recommended estimators.
- `selected_estimators.json` / `skipped_estimators.json`: router decision and
  explicit backend/design skips.
- `steps/*/did_common_output.json`: common DID adapter schema for each executed
  estimator; use this before parsing raw Stata/Python tables.
- `tables/did_estimator_comparison.csv`: consolidated comparison table.

For PSM/IPW diagnostics, agents can call:

```powershell
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method psm_overlap_balance --run
```

or use `psm_ipw_match`, which now reuses the same diagnostics before writing
legacy nearest-neighbor/IPW estimates. Required fields are `data`, `y`,
`treat`/`treatment`, and `x`/`covars`/`controls`; optional
`pscore_col` uses a user-supplied propensity score instead of fitting logit.
The run writes `tables/propensity_summary.csv`,
`tables/off_support_units.csv`, `tables/balance_table_before.csv`,
`tables/balance_table_after_matching.csv`,
`tables/balance_table_after_ipw.csv`,
`tables/balance_table_after_trimmed_ipw.csv`, `tables/weight_summary.csv`,
`tables/extreme_weight_units.csv`, and overlap/balance/weight figures.
Surface `POOR_OVERLAP`, `OFF_SUPPORT_HIGH_SHARE`, `BALANCE_STILL_POOR`,
`EXTREME_IPW_WEIGHTS`, and `LOW_EFFECTIVE_SAMPLE_SIZE` before making any
claim. PSM/IPW improves observed-covariate support only; it does not replace a
DID identification argument.

For spatial spillover diagnostics, agents can call:

```powershell
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method spatial_exposure_did --run
```

Required fields are `data`, `weights`/`weight_matrix`/`w_path`, `id`, `time`,
`y`, and `treat`; optional `post` makes the local treatment and exposure source
`treat*post`. The run writes `spatial_exposure_panel.csv`,
`spatial_exposure_panel_buffered.csv`,
`tables/spatial_exposure_summary.csv`,
`figures/spatial_exposure_distribution.png`,
`tables/contaminated_controls.csv`, `tables/spatial_exposure_twfe.csv`,
`tables/local_effect.csv`, `tables/spillover_effect.csv`, and event-study
support/output tables when estimable. It also writes `did_common_output.json`
for the local treatment coefficient only. Surface `CONTROL_GROUP_CONTAMINATED`,
`EXPOSURE_CONTROL_DEFINITION_WEAK`, `SPATIAL_SE_NOT_USED`, and
`INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION` before making a spillover claim.
This is a reduced-form exposure DID, not SAR/SDM impact decomposition.

For spatial diagnostics and robustness, agents can also call:

```powershell
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method spatial_moran_preflight --run
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method spatial_spdep_lisa --run
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method spatial_se_comparison --run
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method spatial_w_sensitivity --run
conda run -n base python -m skill4econ.cli run --spec SPEC --engine python --method spatial_panel_model_adapter --run
```

- `spatial_moran_preflight` writes global Moran tables and
  `tables/local_moran_by_year.csv` using a basic Python local Moran diagnostic.
- `spatial_spdep_lisa` is dependency-gated; `missing_dependency` is acceptable
  when `Rscript` or R `spdep` is unavailable, but it must not be reported as a
  completed R LISA run.
- `spatial_se_comparison` writes `tables/spatial_se_comparison.csv` and
  `figures/spatial_se_cutoff_sensitivity.png`. If coordinates are missing, it
  skips spatial HAC and raises `SPATIAL_SE_NOT_USED`.
- `spatial_w_sensitivity` requires at least two W paths and writes
  `tables/w_sensitivity_main_effects.csv` plus
  `figures/w_sensitivity_forest.png`; surface `W_SENSITIVITY_SIGN_FLIP`.
- `spatial_panel_model_adapter` parses SAR/SEM/SDM backend impact output only
  when direct/indirect/total effects are provided. Without such output, it
  returns `missing_dependency` and raises
  `INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`.

## Modern DID Routing

Use this order before considering legacy `PSM-DID`:

- `dr_did_2x2`: simple treated/control, pre/post DID with covariates; Stata
  `drdid`, default `method: drimp`.
- `cs_did_attgt`: staggered absorbing binary treatment; Stata `csdid`, default
  `method: dripw`, exports ATT(g,t), simple ATT, and event aggregation.
- `did_imputation_event`: staggered event-study and pre-trend robustness;
  Stata `did_imputation` with local `reghdfe`.

Do not silently substitute TWFE for any of these. If the backend command fails
or the design is outside the estimator boundary, surface `failed` or
`not_paper_ready` rather than recycling another DID estimate under the same
name.

## External Sources

Source repositories pulled for local inspection/testing live under
`skill4econ/vendor_sources/`. Wrappers should prefer installed or built-in
backends for execution, while recording which source backend they correspond to.

## DEA

DEA/SBM/Malmquist runs in-process via the vendored module
`skill4econ.backends.dea`. The adapter writes `allindex.xlsx` to the run
directory and records sheet names plus solver parameters in `manifest.json`.
An optional override path (`spec.dea.backend_path` or env
`SKILL4ECON_DEA_BACKEND`) is honored for users with a customized backend.

## Stata Executable Resolution

The Stata wrappers do not hardcode any path. They resolve the executable from
`spec.stata.executable` → `SKILL4ECON_STATA` → `~/.skill4econ/config.toml`
→ `PATH` lookup (stata, stata-mp, StataMP-64, ...) → common install
directories on Win/macOS/Linux. The resolved path and discovery source are
written into every Stata manifest under `executable` and `stata_source`.

## Tested Backends

Local source references have been pulled into `vendor_sources/` for rdrobust,
csdid/drdid Stata packages, reghdfe/ftools/ivreghdfe/ppmlhdfe, csdid-python,
and linearmodels. Treat these as inspected source backends; do not claim a
wrapper uses one unless the manifest says so.

The smoke test creates synthetic panel and DEA data, runs P0 Python wrappers,
invokes the local DEA backend, and verifies Stata batch startup.

## Model Notes

- `reghdfe_fe` uses local `reghdfe`, `ftools`, and `stata-require` sources
  under `vendor_sources/`; `fe: [entity, time]` is mapped to the spec `id/time`
  columns before Stata sees it.
- `poisson_ppml_fe` uses local `ppmlhdfe` and records that no built-in
  `poisson` fallback was attempted.
- `rdrobust_rdd` uses the local Stata `rdrobust` source. Python `rdrobust`
  source is present but currently blocked by missing `plotnine`, so no Python
  adapter is advertised as runnable.
- `csdid_staggered` uses local `csdid/drdid` source. When `cluster` equals
  `ivar`, the wrapper omits `cluster()` because `csdid` already targets the
  panel id.
- `dr_did_2x2`, `cs_did_attgt`, and `did_imputation_event` are the current
  primary DID menu. `PSM-DID` should be treated as legacy matching
  preprocessing and diagnostic output, not as the default paper estimator.
- `threshold_panel`, `mediation_moderation`, and `synthetic_control` are basic
  runnable Python implementations. Treat them as orchestration baselines, not
  final publication estimators without further diagnostics and robustness.
- `spatial_did_reduced_form` builds `D=treat*post`, `W*D`, and optional `W*X`
  from an edge-list weights file, then runs a fixed-effects reduced-form model.
  Do not call it a SAR/SDM model or claim it handles endogenous spatial lags.
- `spatial_exposure_did` extends that reduced-form workflow with W*treatment
  exposure construction, lagged/cumulative/ring exposure, near/far controls,
  buffer-zone deletion, contaminated-control diagnostics, and separate
  local/spillover effect tables. Its `did_common_output.json` bridges only the
  local treatment coefficient into the DID common schema; it is not a modern
  DID backend and does not apply to the W*treatment exposure coefficient.
- `dml_plr_crossfit` and `dml_irm_crossfit` are sklearn cross-fitting
  fallbacks. They write `dml_diagnostics.json` with folds, learners, nuisance
  metrics, overlap diagnostics, and explicit limitations.
- `doubleml_adapter` and `econml_adapter` are dependency-gated. If the package
  is missing, `manifest.status` is `missing_dependency`; do not substitute the
  fallback while claiming to have used those packages.
