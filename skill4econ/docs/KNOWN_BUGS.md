# Known Bugs And Gaps

Last updated: 2026-06-06.

These are recorded so future agents do not overclaim unfinished spatial and
paper-run behavior. Do not install new packages or wire new external backends
just to close these items unless the user explicitly authorizes that work.

## Spatial

- `spatial_exposure_did` now writes a DID common-schema bridge at
  `did_common_output.json`, but that bridge is only for the local treatment
  coefficient from the reduced-form spatial exposure TWFE. It is not a
  Callaway-Sant'Anna/BJS modern DID estimate and must not be used as the
  primary staggered DID estimator.
- R `spdep` local Moran/LISA is dependency-gated. If `Rscript` or `spdep` is
  missing, `spatial_spdep_lisa` returns `manifest.status == missing_dependency`
  and records `BACKEND_UNAVAILABLE`; do not install R packages automatically.
- SAR/SEM/SDM support now has an opt-in live certification harness:
  `live_backend_certification`. On 2026-06-06,
  `D:\myproject\econpaper\skill4econ\runs\live_backend_certification\20260606T000516Z`
  successfully ran Stata `spxtregress` for a 3-by-3 W grid across SAR, SEM,
  and SDM and parsed `estat impact` direct/indirect/total rows for SAR and
  SDM. This certifies the local Stata backend path, not the
  `spatial_spillover_run` workflow as a structural SDM/SAR workflow.
- `spatial_panel_model_adapter` remains a parser/adapter contract for supplied
  backend artifacts. It is still useful for validating direct/indirect/total
  impact tables, but parser-only success is not live backend certification.
- `xsmle` remains missing on this machine (`which xsmle` returned a missing
  dependency in the same live certification run). Do not claim `xsmle` support
  until a live row writes coefficient and impact artifacts.
- R `spdep`/`splm`/`spatialreg` remain unavailable because `Rscript` is not on
  PATH. No R LISA, `splm`, or `spatialreg` live estimator ran on this machine.
- The live `spxtregress` certification fixture is intentionally small
  (`cert_units: 12`, `cert_years: 4`) and uses fixed effects plus
  `iterate(80)` so the certification is reproducible. It is a backend
  certification, not a paper-scale benchmark.
- Heavy spatial backends now use `backend_canonical_result.json` and the
  `backend-contract` smoke suite for dependency/result semantics. A backend
  command that exits successfully but fails to write declared outputs is still
  invalid and records `BACKEND_RESULT_MISSING`; this does not certify any live
  SAR/SEM/SDM backend.
- `spatial_se_comparison` provides a Python distance-cutoff spatial HAC
  comparison when lon/lat coordinates are present. It is not a full Conley
  backend and does not replace package-specific spatial covariance estimators.
- `spatial_w_sensitivity` runs alternative W matrices supplied in
  `weights`/`weight_paths` and detects sign/significance instability. It does
  not yet auto-generate an economic-distance or k-nearest-neighbor W grid.
- `make smoke-spatial` is present in the Makefile, but this Windows environment
  does not have `make` on PATH. Use the official Windows-first equivalent:
  `conda run -n base python -m skill4econ.cli smoke --suite spatial --strict`.

## Documentation / Claim Boundaries

- `spatial_spillover_run` remains a reduced-form exposure workflow. It must not
  be described as SAR/SDM/SAC or structural indirect-effect estimation.
- PSM/IPW diagnostics do not create a true matched-panel DID dataset. Treat
  PSM-DID output as overlap/balance support, not the primary modern DID
  estimator.
- `dea_sbm_malmquist_adapter` is self-contained for SBM/Super-SBM and
  Malmquist index construction, but DEA second-stage/determinants regressions
  are not certified. If `second_stage` is requested, the adapter must fail with
  `DEA_SECOND_STAGE_NAIVE_TOBIT` rather than producing a naive Tobit claim.

## Contract Verifier Enhancements

- `validate-run` checks required files, JSON parseability, registered risk
  codes, status/risk consistency, required artifact existence, fatal-risk
  success conflicts, rerun command presence, recursive child workflow run
  contracts, and basic run-config/model-table provenance.
- `validate-run` emits basic provenance warnings for `model_table.csv`, but it
  does not yet perform row-level estimator/backend/spec reconciliation against
  `audit.json` for every method-specific table schema.

## Golden Test Coverage

- The current golden suite covers nine representative DID, PSM/IPW, spatial
  reduced-form, and W-sensitivity contract cases and validates each generated
  run directory. The full 3-by-3 flagship workflow golden matrix described in
  `TODO.md` is not yet materialized as separate golden tests because several
  DID workflow cases invoke slow Stata backends. Broader boundary coverage
  currently lives in smoke tests and fixture-specific tests.

## Dependency Matrix Coverage

- `vendor_sources.lock.json` is currently an unlocked source-reference
  skeleton. It records repository URLs and the known gap, but commit SHAs are
  still null. Do not treat vendored Stata/R/Python backend references as
  publication-grade pinned dependencies until exact commits or package
  versions are filled in.
- Dependency-gated tests cover missing spatial structural backend,
  malformed impact-decomposition parser output, and missing `Rscript` for
  `spatial_spdep_lisa`. The `backend-contract` smoke suite now covers fake R
  package probes, non-zero backend exit, timeout, successful stdout with missing
  required output, parser-only SDM impact success, empty impact tables, and
  missing direct/indirect/total impact components.
- Live R/Stata certification is partial. Stata `spxtregress` and Stata
  `ppmlhdfe` have live successful rows in
  `D:\myproject\econpaper\skill4econ\runs\live_backend_certification\20260606T000516Z`.
  R `spdep`/`splm`/`spatialreg` and Stata `xsmle` are still dependency-gated
  and unavailable.
- Stata preflight on 2026-06-06 found `spxtregress_rc=0`, but
  `xsmle_rc=111` and `spmat_rc=111`. Prefer an official `spxtregress`
  adapter path first if live spatial panel work is resumed; do not assume
  `xsmle` is installed on this machine.
- `flagship_slow_matrix` now exists as an opt-in 3 flagship workflow by
  3 case by Stata/R backend-profile harness. The first full run was
  `D:\myproject\econpaper\skill4econ\runs\flagship_slow_matrix\20260606T002537Z`.
  Stata workflow cells ran; R cells were recorded as `BACKEND_UNAVAILABLE`.
  The `spatial_spillover_run/alternate_w` case deliberately exposes a
  rank-deficient reduced-form design and must stay not-paper-ready rather than
  falling back to another estimator.
