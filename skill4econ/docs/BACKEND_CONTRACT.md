# Heavy Backend Contract

This document records how `skill4econ` handles slow or heavy external
backends such as Stata `xsmle`, Stata `spxtregress`, Stata `ppmlhdfe`, R
`splm`, R `spatialreg`, and R `spdep`.

## Default Policy

- Do not install packages automatically.
- Do not replace a missing backend with a different estimator.
- Do not trust stdout success unless the declared output files exist.
- Do not label parser-only artifacts as live backend estimates.
- Do not report SDM/SAR/SEM indirect effects unless a direct/indirect/total
  impact decomposition exists.

## Contract Status

Backend-level status is recorded inside backend artifacts, not in
`status.json.status`. The normalized run status still uses the project-wide
enum `success`, `success_with_warnings`, `partial_success`, `skipped`, and
`failed`.

Backend contract statuses include:

```text
ok
known_gap
missing_dependency
backend_unavailable
backend_error
backend_timeout
result_missing
parser_only
parser_error
invalid_result
invalid_spec
unsupported
```

`spatial_panel_model_adapter` writes `backend_canonical_result.json`. When an
impact decomposition CSV is provided, the status is `parser_only`; no live
SAR/SEM/SDM backend is claimed.

## Fast PR Matrix

Run:

```powershell
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
```

The fast matrix covers fake executable probes and parser fixtures:

- fake R package available/missing;
- missing Rscript;
- non-zero backend exit;
- backend timeout;
- success with missing declared output;
- success with declared output;
- SDM impact parser success;
- SDM parser failure for empty or incomplete impacts.

## Slow Or Live Matrix

Live backends are opt-in work. Run:

```powershell
conda run -n base python -m skill4econ.cli smoke --suite live-backend --strict --timeout 1200
```

or directly:

```powershell
conda run -n base python -m skill4econ.cli run --engine python --method live_backend_certification --spec skill4econ/examples/mini_panel/live_backend_certification_spec.yml --run
```

As of 2026-06-06 on this machine:

- Stata `spxtregress` live certification passed for `W_row`, `W_minmax`, and
  `W_trunc_row` across SAR, SEM, and SDM.
- Stata `estat impact` direct/indirect/total decomposition was parsed for SAR
  and SDM rows. SEM rows write coefficient artifacts but are not expected to
  have direct/indirect/total impact rows.
- Stata `ppmlhdfe` live certification passed and wrote coefficient artifacts.
- Stata `xsmle` is missing.
- R `spdep`, `splm`, and `spatialreg` did not run because `Rscript` is not on
  PATH.

The flagship workflow slow matrix is also opt-in:

```powershell
conda run -n base python -m skill4econ.cli smoke --suite flagship-slow --timeout 1200
```

It runs 3 flagship workflows by 3 cases under Stata and R backend profiles,
then writes `tables/flagship_slow_matrix.csv`. R rows should be read as
backend availability probes unless an R workflow adapter is explicitly added.

Remaining live certification gaps:

- Stata `xsmle` with direct/indirect/total impacts;
- R `spatialreg`/`splm` SDM/SAR/SEM outputs;
- wiring the certified `spxtregress` backend into a paper workflow without
  weakening the reduced-form claim language.

Until those exist, related methods must stay `adapter_only`,
`supplementary_only`, or `not_available` according to the run result.
