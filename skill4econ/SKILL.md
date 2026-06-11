---
name: skill4econ
description: Repo-local econpaper capability pack for environmental economics, economics, finance, causal inference, Stata/Python econometrics, and AI x econometrics wrappers. Use existing tested backends and inspect manifests before making empirical claims.
tags: [economics, environmental-economics, finance, causal-inference, stata, python]
---

# skill4econ

Use the CLI in this folder when an econpaper agent needs a callable
econometric method.

Runtime code lives in `src/skill4econ`. Domain/reporting skill files live in
`skills/`. The EasyPaper-derived economics/finance manuscript-generation layer is kept
separate at `integrations/easypaper-econ-finance/`.

## Required Workflow

1. Run from `D:\myproject\econpaper\skill4econ`.
2. Prefer `conda run -n base python -m skill4econ.cli ...`.
3. Use `--plan` or `--dry-run` before `--run` for unfamiliar methods.
4. Read `manifest.json` and `audit.json` after every run.
5. Do not turn failed, interface-only, or missing-dependency outputs into paper
   claims.

For DID paper packages, prefer:

```powershell
conda run -n base python -m skill4econ.cli workflow --name did_paper_run --spec SPEC --run
```

Read `research_report.md`, `warnings.json`, and `sample_construction.json`
before using the outputs. `not_paper_ready` is an explicit warning status, not
a success.

## DEA Boundary

DEA/SBM/Malmquist runs in-process through the vendored backend at
`skill4econ.backends.dea`. SFA is still external-only. To override the DEA
backend with a custom implementation, set `spec.dea.backend_path` or the
`SKILL4ECON_DEA_BACKEND` environment variable.

## Stata Discovery

The Stata executable is resolved via a layered chain: `spec.stata.executable`
→ `SKILL4ECON_STATA` → `~/.skill4econ/config.toml` → `PATH` lookup → common
install dirs. No path is hardcoded. See `README.md` for details and the
config file format.

## Naming Discipline

- `spatial_did_reduced_form` is a neighbor-exposure DID (`D`, `W*D`, optional
  `W*X`), not a full SAR/SDM estimator.
- `dml_plr_crossfit` and `dml_irm_crossfit` are sklearn fallbacks, not the
  `DoubleML` or `EconML` packages.
- `doubleml_adapter` and `econml_adapter` must report `missing_dependency` when
  the packages are unavailable.
- Modern DID core is deliberately limited to `dr_did_2x2`, `cs_did_attgt`, and
  `did_imputation_event`. Treat `PSM-DID` as legacy matching diagnostics, not
  the default paper estimator.
- `did_paper_run` requires an explicit `design_type`. Staggered DID with
  TWFE-only output must not be described as a complete paper-ready result.

## Smoke Test

Run:

```powershell
conda run -n base python skill4econ/tests/smoke/run_smoke.py
```

The smoke test must finish with `{"status": "ok"}` and checks both process exit
codes and `manifest.status`.
