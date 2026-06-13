# Modern DID Backend Setup

This note is the one-stop setup card for staggered DID backends used by
`skill4econ`. It is intentionally operational: another user agent should be
able to read this file, install the packages, and run the verification commands
without guessing.

## What Is Main Vs Fallback

- Main staggered DID target: Callaway-Sant'Anna ATT(g,t), exposed in
  `skill4econ` as `cs_did_attgt`.
- Robustness target: Borusyak-Jaravel-Spiess imputation DID, exposed as
  `did_imputation_event`.
- Fallback/benchmark only: TWFE and TWFE event study. These can now run through
  Stata `xtreg, fe`, but they must not be treated as the main estimator for a
  staggered adoption design.

If `cs_did_attgt` and `did_imputation_event` are unavailable, a workflow may
still produce TWFE benchmark rows, event plots, and diagnostics, but the correct
workflow status is still `not_paper_ready` / `not_for_claim`.

## Python Packages

Install the maintained Python backends in the active environment:

```powershell
python -m pip install -U differences pyfixest statsmodels
```

Verify imports:

```powershell
python -c "import differences, pyfixest; print('differences=', getattr(differences, '__version__', 'unknown')); print('pyfixest=', getattr(pyfixest, '__version__', 'unknown'))"
python -c "import inspect; from differences import ATTgt; print(inspect.signature(ATTgt)); print(inspect.signature(ATTgt.fit)); print(inspect.signature(ATTgt.aggregate))"
```

Current routing notes:

- `differences` is the preferred Python package for Callaway-Sant'Anna-style
  ATT(g,t) because it exposes an `ATTgt` API.
- `pyfixest` is useful for fixed effects and DID/event-study tooling. Treat it
  as a maintained backend candidate, not as a hand-rolled replacement for
  ATT(g,t), unless the adapter explicitly calls a modern DID API.
- On the 2026-06-12 local Windows audit, `differences==0.3.0` exposes
  `ATTgt(data, cohort_column, dosage_column=None, ...)`, then
  `fit(formula, est_method='reg'|'dr'|..., control_group=..., cluster_var=...)`,
  then `aggregate('simple'|'event'|'cohort'|'time', ...)`. A Python adapter that
  calls `cohort_name` is not compatible with this installed release.
- `statsmodels` was upgraded to `0.14.6` during the audit because the previous
  local `0.14.1` install could not import against the installed SciPy.
- Missing packages must produce `missing_dependency`; do not silently replace
  them with TWFE.

## Stata Packages

Run this from PowerShell. Change the Stata path if your machine uses a different
install location.

```powershell
$stata = "D:\stata17\StataMP-64.exe"
$do = Join-Path $env:TEMP "skill4econ_install_modern_did.do"
@'
version 17
set more off
ssc install ftools, replace
ssc install require, replace
ssc install reghdfe, replace
ssc install drdid, replace
ssc install csdid, replace
ssc install did_imputation, replace
which ftools
which require
which reghdfe
which drdid
which csdid
which did_imputation
exit
'@ | Set-Content -Path $do -Encoding UTF8
& $stata /e do $do
Get-Content "$($do -replace '\.do$', '.log')" -Tail 120
```

Expected verification:

- `which csdid` resolves to an ado file.
- `which drdid` resolves to an ado file.
- `which require` resolves to an ado file.
- `which reghdfe` resolves to an ado file.
- `which did_imputation` resolves to an ado file.

If `ssc install did_imputation` fails, install from the authors' distribution
source and rerun the same `which did_imputation` check before claiming the BJS
backend is available.

## skill4econ Verification

After installing the packages, run:

```powershell
$env:PYTHONPATH="D:\myproject\econpaper\skill4econ\src"
python -m skill4econ.cli run --engine stata --method stata_preflight --run
python -m pytest skill4econ/tests/smoke/test_did_paper_run.py skill4econ/tests/smoke/test_did_adapters.py skill4econ/tests/contracts/test_contract_basics.py -q
```

For the JEL-DiD full-data blind run used during the 2026-06-12 audit:

```powershell
$env:PYTHONPATH="D:\myproject\econpaper\skill4econ\src"
python -m skill4econ.cli validate-workflow `
  --name did_paper_run `
  --spec D:\myproject\econpaper\reports\blind_raw_runs\jel_did_full_data\blind_inputs_full\full_staggered_stata_first_spec.json `
  --output D:\myproject\econpaper\reports\blind_raw_runs\jel_did_full_data\validated_run_full_staggered_stata_first_after_backend_install `
  --run `
  --strict
```

Success criteria for a paper-ready staggered DID run are stricter than command
success:

- `cs_did_attgt` status is `ok`.
- A modern ATT(g,t)-style table exists, not only TWFE benchmark rows.
- `did_imputation_event` either succeeds as robustness or is explicitly marked
  optional/failed with a clear dependency reason.
- The workflow is not blocked by `TWFE_STAGGERED_HETEROGENEITY` as the only
  available result.

## 2026-06-12 Local Audit Results

Environment checks completed on `D:\myproject\econpaper`:

- Python packages installed and importable:
  - `differences==0.3.0`
  - `pyfixest==0.60.0`
  - `statsmodels==0.14.6`
  - `linearmodels==5.3`
- Stata packages installed and discoverable:
  - `ftools`
  - `require`
  - `reghdfe` (`6.13.1` in the local log)
  - `drdid`
  - `csdid`
  - `did_imputation` (November 22, 2023 in the local log)
- Stata preflight after install passed for the DID-relevant packages:
  `reghdfe_rc=0`, `csdid_rc=0`, `drdid_rc=0`, `qreg_rc=0`.

Initial full-data JEL-DiD Stata-first audit run:

```text
D:\myproject\econpaper\reports\blind_raw_runs\jel_did_full_data\validated_run_full_staggered_stata_first_after_require_install\did_paper_run\20260612T113812Z-12ca45d0
```

- `stata.cs_did_attgt` succeeded and produced the main ATT(g,t)-style estimate:
  `ATT = 6.8909249`, `std_error = 2.9504628`, `t_stat = 2.3355403`.
- TWFE/event-study benchmark paths also ran, but TWFE and `cs_did_attgt` had
  opposite signs, so TWFE remains benchmark-only.
- `stata.did_imputation_event` initially failed on the full data. Without
  `autosample`, Stata reported that some fixed effects could not be imputed.
  With `autosample`, that sample issue was handled but the command then failed
  on standard-error convergence (`r(430)`).

Final no-fallback modern DID run after wrapper fixes:

```text
D:\myproject\econpaper\reports\blind_raw_runs\jel_did_full_data\validated_run_modern_only_no_fallback_after_twfe_warning_fix\did_paper_run\20260612T120815Z-60cd9830
```

- The spec selected only `cs_did_attgt` and `did_imputation`; TWFE and TWFE
  event-study were excluded.
- Strict workflow validation passed with `status = success`.
- `stata.cs_did_attgt` succeeded as the main ATT(g,t) path:
  `ATT = 6.8909249`, `std_error = 2.9504628`, `t_stat = 2.3355403`.
- `stata.did_imputation_event` succeeded with standard errors after explicit
  convergence controls: `autosample = true`, `did_imputation_maxit = 1000`,
  `did_imputation_tol = 0.0001`. The run did not use `nose`.
- `did_imputation_event` horizon estimates in the final run:
  `tau0 = -3.3986008` (`se = 2.1809213`),
  `tau1 = -2.4401782` (`se = 2.5411434`),
  `tau2 = 3.4457138` (`se = 2.6671548`),
  `tau3 = 0.91826493` (`se = 2.8433292`).
- The workflow still reports supplementary data-support risks:
  unbalanced panel, weak pre-period support for some cohorts, and short
  post-period support for some cohorts. These are data limitations, not fallback
  estimator failures.

Initial full-data Python audit run:

```text
D:\myproject\econpaper\reports\blind_raw_runs\jel_did_full_data\validated_run_full_staggered_python_after_backend_install\did_paper_run\20260612T114343Z-7f143f19
```

- Python TWFE benchmark paths ran.
- `python.cs_did_attgt_py` failed with
  `ATTgt.__init__() got an unexpected keyword argument 'cohort_name'`.
- This was an adapter API mismatch, not a missing-package condition. The
  installed `differences==0.3.0` package expects `cohort_column`.

Final Python adapter check after fixes:

```text
D:\myproject\econpaper\reports\blind_raw_runs\jel_did_full_data\adapter_checks_python_cs_claim_after_fix\cs_did_attgt_py\20260612T115936Z-0bed7a1b
```

- `python.cs_did_attgt_py` now runs the real `differences.ATTgt` backend on the
  full data and writes `att_gt.csv`, `simple_att.csv`, `event_study.csv`, and
  `model_table.csv`.
- The Python registry now requires `differences` for this adapter. `pyfixest`
  remains installed and useful for other DID/event-study tooling, but it is not
  treated as sufficient for the `differences.ATTgt` adapter.

## Upstream References

- `differences` PyPI page documents version `0.3.0`, Python `>=3.10`, and an
  `ATTgt(data=df, cohort_column='cohort')` quick start:
  <https://pypi.org/project/differences/>
- `differences` API docs describe ATT(g,t), `fit()`, and `aggregate()`:
  <https://differences.readthedocs.io/en/latest/api_reference/attgt.html>
- `pyfixest` documents DID/event-study support through TWFE, Gardner did2s, and
  local projections:
  <https://pyfixest.org/quickstart.html#difference-in-differences-event-study-designs>
- `csdid` docs describe multiple periods, variation in treatment timing,
  group-time ATT, event-study estimates, and overall effects:
  <https://d2cml-ai.github.io/csdid/examples/csdid_basic.html>
- `did_imputation` upstream Stata repository:
  <https://github.com/borusyak/did_imputation>

## What Was Fixed In The Local Runner

The 2026-06-12 debugging pass fixed several runner issues that are separate from
package installation:

- Windows `stata.cmd` is normalized to the real `StataMP-64.exe` so Python waits
  for the actual Stata process.
- `analysis_data.csv` now keeps only estimator/diagnostic columns, preventing
  multiline text fields from confusing Stata CSV import.
- Stata wrappers create numeric aliases for id/time/cluster/gvar variables before
  factor-variable or panel commands.
- TWFE benchmark paths use `xtreg, fe` rather than expanding thousands of entity
  dummies with bare `regress`.
- Step-specific failure labels such as `cs_did_attgt_failed` are normalized into
  registered reviewer-risk codes.

These are fallback/runner fixes. They do not make TWFE a valid main estimator for
staggered adoption.
