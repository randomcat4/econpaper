# PSM/IPW Balance Diagnostics

Use this note when an agent runs `psm_overlap_balance`, `psm_ipw_match`, or
`psm_did_policy_run`.

## Commands

Standalone diagnostics:

```powershell
conda run -n base python -m skill4econ.cli run --engine python --method psm_overlap_balance --spec SPEC --run
```

Legacy PSM/IPW estimates plus the same diagnostics:

```powershell
conda run -n base python -m skill4econ.cli run --engine python --method psm_ipw_match --spec SPEC --run
```

Policy workflow with TWFE DID and Stata DRDID when available:

```powershell
conda run -n base python -m skill4econ.cli workflow --name psm_did_policy_run --spec SPEC --run
```

## Required Spec

- `data`: CSV/XLSX input.
- `y`: outcome column.
- `treat` or `treatment`: binary 0/1 treatment.
- `x`, `covars`, or `controls`: propensity-score covariates.
- Optional `balance_vars`: variables to audit in balance tables. If omitted,
  the propensity covariates are used.
- Optional `pscore_col`: user-supplied propensity score. When present, logit is
  not fit.
- Optional `ps_model: probit`: use statsmodels probit instead of sklearn logit.

## Core Artifacts

- `tables/propensity_summary.csv`: all/treated/control PS min, max, mean, SD,
  and p1/p5/p50/p95/p99.
- `tables/off_support_units.csv`: observations outside the common support
  interval.
- `figures/propensity_overlap_density.png` and
  `figures/propensity_overlap_hist.png`: treated/control PS overlap.
- `tables/balance_table_before.csv`: unadjusted SMD, variance ratio, means,
  missing rates, and `smd_flag`.
- `tables/balance_table_after_matching.csv`: nearest-neighbor matched balance.
- `tables/balance_table_after_ipw.csv`: IPW balance.
- `tables/balance_table_after_trimmed_ipw.csv`: trimmed IPW balance.
- `figures/love_plot.png`: variables sorted by pre-adjustment absolute SMD.
- `tables/weight_summary.csv`: IPW, stabilized IPW, and trimmed IPW max, p95,
  p99, ESS, and top 1 percent weight share.
- `tables/extreme_weight_units.csv`: high-leverage weighted observations.
- `tables/psm_grid_results.csv`: neighbor/caliper/replacement sensitivity grid.
- `figures/psm_grid_forest.png`: PSM ATT grid plot.

`psm_did_policy_run` also writes:

- `tables/drdid_main.csv`: core DRDID result row when parsed.
- `tables/adjusted_did_comparison.csv`: DRDID, PSM ATT, IPW ATT, and TWFE DID
  in one table.
- `raw/drdid.log`: Stata DRDID log or an explicit unavailable note.
- `adjusted_did_identification_notes.md`: claim limits for adjusted DID.

## Reviewer Risks

- `OFF_SUPPORT_HIGH_SHARE`: more than 10 percent of observations are outside
  common support.
- `POOR_OVERLAP`: treatment is highly predictable from observed covariates or
  the PS distributions have no meaningful common support.
- `BALANCE_STILL_POOR`: the best post-adjustment max absolute SMD remains above
  0.10.
- `EXTREME_IPW_WEIGHTS`: raw IPW has extreme max weight or top 1 percent weight
  concentration.
- `LOW_EFFECTIVE_SAMPLE_SIZE`: IPW ESS share is too low.
- `PSM_SAMPLE_LOSS_HIGH`: every PSM grid spec loses more than 30 percent of
  treated observations.
- `TRIM_SENSITIVITY_UNSTABLE`: PSM grid estimates change sign or significance.
- `DRDID_PSM_DID_DISAGREE`: core DRDID and legacy PSM/IPW estimates have
  opposite signs.

## Claim Discipline

PSM/IPW improves observed-covariate support and balance only. It does not prove
parallel trends and does not remove unobserved confounding. In papers, treat
PSM/IPW as diagnostics or robustness around a clearly stated DID design. When a
valid 2x2 adjusted DID is available, report DRDID as the core adjusted result
and keep PSM/IPW in the diagnostic comparison table.
