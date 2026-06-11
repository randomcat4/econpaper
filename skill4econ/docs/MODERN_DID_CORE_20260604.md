# Modern DID Core 2026-06-04

GPT-5.5 Pro product review recommended keeping the DID core small:

1. `dr_did_2x2`: Sant'Anna-Zhao DRDID for simple 2x2 DID.
2. `cs_did_attgt`: Callaway-Sant'Anna ATT(g,t) / CSDID for staggered
   absorbing binary treatment.
3. `did_imputation_event`: Borusyak-Jaravel-Spiess imputation DID for dynamic
   event-study and pre-trend checks.

Policy:

- Do not make `PSM-DID` a primary method name.
- Do not route staggered DID to TWFE as a hidden fallback.
- Do not support continuous, reversible, non-absorbing, or post-treatment
  matching designs in this v0.1 core.
- If the design is outside the estimator boundary, fail or mark not paper-ready.

Implementation status:

- `dr_did_2x2` wraps local Stata `drdid`; example spec uses an explicit
  two-period sample filter.
- `cs_did_attgt` wraps local Stata `csdid/drdid`; exports `att_gt.csv`,
  `simple_att.csv`, `event_study.csv`, `model_table.csv`, and diagnostics.
- `did_imputation_event` wraps the local BJS `did_imputation` source plus
  local `reghdfe`; exports event-study coefficients, pretrend coefficients,
  pretrend test, individual effects, and weights when requested.
- Smoke validation passed on simulated data: 29 checks.

