# TODO Pack: skill4econ Estimator Layer Upgrade (v1)

Audience: Codex (or any coding agent) executing step by step. Scope: `skill4econ/` only.
`econpaper/` implements no estimators by design (see root README "Design Boundary") and
must not be touched except where artifact contracts change (noted per task).

Date: 2026-06-12. Baseline: branch `codex/econpaper-roadmap-v3`, post-delivery commit
`2f11e9e` (`Harden v3 evidence release gates`). This is a follow-up work pack, not a
blocker for the current econpaper v3 delivery.

Verification baseline:

- `python -m pytest -q`: 155 passed, 11 warnings.
- Final smoke: `reports/multi_paper_smoke_delivery_fix2/20260612_150426`.
- env_carbon_did_aea machine tier: A.
- Release gate remains correctly blocked by `human_eval_missing`.

## Background: why this pack exists

Audit finding: skill4econ is a two-layer system. The diagnostics/claim-gate layer
(`did_design.py`, `overlap_balance.py`, `claim_levels.py`, estimator routing) is real and
well tested. The Python estimator layer (`python_wrappers.py`) is MVP-grade:

- All p-values use a normal approximation (`_normal_pvalue` via `erfc`), never a
  t-distribution. With clustered SEs and few clusters this overstates significance.
- Fixed effects are dummy-expanded into the design matrix (memory blowup on real panels).
- `quantile_regression` and `psm_ipw_match` report `NaN` standard errors (no inference).
- `mediation_baron_kenny` has no bootstrap; `synthetic_control_basic` has no placebo
  inference; `dml_*_crossfit` has no cluster SE.
- Modern staggered DID (CS/dr-did/imputation) exists only behind Stata adapters; all R
  adapters are `interface_only`. A Stata-less machine cannot produce a staggered main
  estimate (routing fails closed — correct, but a capability gap).
- `iv_2sls` defaults to `main_estimate`/`paper_ready` with zero weak-instrument
  diagnostics.

The honest-labeling architecture is good. The goal is NOT to relax it; it is to upgrade
estimators until they legitimately earn promotion, and to complete inference everywhere.

## Global rules (read before every task; violations = rejected PR)

1. **Never silently fall back.** A missing package/backend is `missing_dependency`,
   never a degraded estimate labeled `ok` without a risk code.
2. **Never promote a method's claim level as a side effect.** Promotion to
   `main_estimate` happens ONLY in the explicit promotion protocol (end of this file).
3. **Every new estimator path needs:** (a) entries in `contracts/claim_levels.py` hint
   sets covering ALL registered names and aliases, (b) risk codes registered in
   `contracts/risk_registry.py` (move out of `TODO_REQUIRED_RISK_CODES` with a contract
   test), (c) golden fixtures under `tests/fixtures/`, (d) a line in `registry.yml`.
4. **Alias hygiene:** any new key added to `PYTHON_METHODS` must appear in a claim-level
   hint set. The invariant test
   `tests/contracts/test_contract_basics.py::test_no_registered_python_method_escapes_claim_gate_by_name`
   enforces this — keep it passing; extend its allowlist only via the promotion protocol.
5. **Numbers change ⇒ fixtures change deliberately.** Tasks that alter p-values/SEs will
   break golden fixtures. Regenerate them in a dedicated commit with a note in the
   commit message stating which statistical change caused the diff. Never hand-edit
   expected JSON to make tests pass.
6. **Test gate per PR:** `python -m pytest skill4econ/tests -q` and root
   `python -m pytest -q` (155 passed baseline). Do not ignore subprocess or adapter
   failures by default; if a task hits an environment-specific failure, document the
   exact command, traceback, and why it is unrelated before carving it out.
7. Windows line endings: add files as LF. (Pre-existing CRLF contamination of fixtures
   is a separate cleanup; do not mix it into estimator PRs.)

## Stage 0 — DONE (2026-06-12, do not redo)

- [x] Alias claim-gate escape fixed: `mediation_baron_kenny`, `synthetic_control_basic`,
  `threshold_panel_search` added to `EXPLORATORY_METHOD_HINTS`; `plot_diagnostics` added
  to `DIAGNOSTIC_METHOD_HINTS`; invariant test added.

## Stage 1 — P0: inference correctness (do first, in order)

### T1.1 Replace normal p-values with t-distribution + add confidence intervals

- Files: `src/skill4econ/python_wrappers.py` (`_normal_pvalue`, `_ols_numpy`).
- Steps:
  1. Add `_t_pvalue(t_stat, df)` using `scipy.stats.t.sf(abs(t), df) * 2` (scipy is
     already a dependency via `synthetic_control_basic`).
  2. In `_ols_numpy`: for `cov_type="cluster:*"` use `df = G - 1` (G = number of
     clusters); for HC1 use `df = n - k`. Thread `df_inference` into the returned meta.
  3. Add `ci_low`/`ci_high` (95%, t-critical) to every row dict. `write_model_table`
     and `model_table.schema.json` must accept the new columns (check
     `contracts/model_table.schema.json`; extend additively).
  4. Keep `_normal_pvalue` only if some caller genuinely has no df; otherwise delete it.
- Tests: unit test comparing against statsmodels OLS `cov_type="cluster"` on a small
  fixture (tolerance 1e-6 on coef, 1e-4 on p). Regenerate affected golden fixtures
  (expected_risks/expected_design are design-level and should NOT change; verify).
- DoD: no call site of `_normal_pvalue` without df remains; CI columns present in
  `model_table.csv` output; both suites pass.
- econpaper impact: `econpaper/evidence.py` `STAT_COLUMNS` may map `ci_low`/`ci_high` —
  check it tolerates the new columns (it already models CI per roadmap; additive only).

### T1.2 Few-cluster guard

- Files: `python_wrappers.py`, `contracts/risk_registry.py`, `core.py`
  (`_build_reviewer_risk`).
- Steps: when clustered inference runs with `G < 30`, attach risk code
  `FEW_CLUSTERS_INFERENCE_FRAGILE` (register it; severity yellow; degradation
  `supplementary_only` when `G < 15`). Message must state G and recommend wild cluster
  bootstrap (T6.2).
- Tests: fixture with 8 clusters asserting the code appears in `reviewer_risk.json` and
  `paper_readiness` degrades at `G < 15`.

### T1.3 iv_2sls weak-instrument diagnostics + gate

- Files: `python_wrappers.py::iv_2sls`, `risk_registry.py`, `claim_levels.py`.
- Steps:
  1. Report first-stage results: linearmodels `IV2SLS` exposes `result.first_stage`;
     extract partial F-statistic per endog. Write `iv_first_stage.json` artifact.
  2. Register `IV_WEAK_INSTRUMENT` (F < 10 ⇒ degradation `not_for_claim`) and
     `IV_FIRST_STAGE_MISSING` (if extraction fails ⇒ `not_for_claim`; do NOT swallow).
  3. Add F-stat row(s) to model table (`term: first_stage_F_<endog>`).
  4. `iv_2sls` stays in the main-estimate allowlist ONLY because the gate now exists;
     if you cannot complete step 1–2 in one PR, move `iv_2sls` to
     `EXPLORATORY_METHOD_HINTS` first and restore after.
- Tests: strong-IV fixture (F > 100, stays paper_ready) and weak-IV fixture (F ≈ 2,
  degraded to not_for_claim). Add both under `tests/fixtures/iv/`.

## Stage 2 — P0/P1: complete inference per estimator

Each task: keep the method in `EXPLORATORY_METHOD_HINTS` (these do NOT get promoted by
finishing inference alone; promotion requires the protocol at the end).

### T2.1 quantile_regression → statsmodels QuantReg

- Replace sklearn `QuantileRegressor` with `statsmodels.regression.quantile_regression.QuantReg`
  (gives asymptotic SEs/p-values). Keep spec keys (`quantile`/`tau`). Dependency-gate on
  statsmodels with `missing_dependency` (no sklearn fallback — delete it).
- Tests: golden fixture with known coefficients; SE non-NaN assertions.

### T2.2 PSM: real matching inference

- `psm_ipw_match`: add caliper option (`caliper` in pscore units, default 0.2*sd(logit
  pscore) per Austin 2011); add with-replacement flag; implement Abadie-Imbens (2006)
  SE for the NN ATT (formula implementation is acceptable; document it) OR bootstrap
  (≥499 reps, seeded) — choose Abadie-Imbens for matching, bootstrap for IPW ATE/ATT.
- Risk code `PSM_NAIVE_SE_NOT_ABADIE_IMBENS` is already registered: attach it whenever
  the bootstrap/AI path is skipped, and REMOVE its attachment once SEs are real.
- Tests: extend `tests/fixtures/psm_did/` with expected SE ranges (tolerance-based).

### T2.3 Mediation: bootstrap indirect effect

- `mediation_baron_kenny`: seeded nonparametric bootstrap (default 999 reps) for the
  `indirect_effect_ab` CI (percentile). Keep the explicit "Baron-Kenny, not causal
  mediation (Imai et al.)" audit message; add `not_valid_for: ["causal mediation under
  sequential ignorability"]` to the manifest extras.
- Tests: simulated fixture where true indirect effect CI excludes 0; reproducibility
  test (same seed ⇒ same CI).

### T2.4 Synthetic control: placebo inference

- `synthetic_control_basic`: add in-space placebo loop (refit treating each donor as
  pseudo-treated), compute post/pre RMSPE ratios, permutation p-value for the treated
  unit (Abadie et al. 2010). Write `synthetic_placebo.csv` + p-value into model table
  (`term: placebo_permutation_p`). Guard: skip with risk code
  `SC_PLACEBO_TOO_FEW_DONORS` (register) when donors < 10 ⇒ degradation
  `supplementary_only`.
- Tests: fixture with 20 donors and an injected effect; assert p < 0.1 and artifact
  exists.

### T2.5 DML: clustered score SE

- `dml_plr_crossfit` / `dml_irm_crossfit`: accept `cluster` spec key; compute SE from
  cluster-summed scores (sandwich on the orthogonal score). Update
  `dml_diagnostics.json` `cluster_se` field from "not implemented" to the actual mode.
- Tests: cluster vs iid SE differ on a fixture with within-cluster correlation.

## Stage 3 — P1: modern staggered DID in Python

Backend setup note: before testing Stage 3 or Stata-first staggered DID, read
`skill4econ/docs/MODERN_DID_BACKEND_SETUP.md`. It records the required Python
packages (`differences`, `pyfixest`), Stata packages (`csdid`, `drdid`,
`reghdfe`, `did_imputation`, `ftools`, `require`), one-pass install commands, and the
verification checks that distinguish a real ATT(g,t) main estimate from TWFE
fallback output.

2026-06-12 local backend audit:

- Python packages are installed and importable on this machine:
  `differences==0.3.0`, `pyfixest==0.60.0`, `statsmodels==0.14.6`,
  `linearmodels==5.3`.
- Stata packages are installed and discoverable on this machine:
  `ftools`, `require`, `reghdfe`, `drdid`, `csdid`, `did_imputation`.
- Stata `csdid` is now a real main-estimator path on the full JEL-DiD data:
  `cs_did_attgt` succeeded with ATT `6.8909249` and SE `2.9504628`.
- Stata `did_imputation` now runs on the full JEL-DiD data with standard errors
  when the spec sets `autosample = true`, `did_imputation_maxit = 1000`, and
  `did_imputation_tol = 0.0001`. Do not use `nose` for a paper-grade robustness
  result.
- Python `cs_did_attgt_py` now runs the real `differences.ATTgt` backend against
  `differences==0.3.0`; the adapter uses `cohort_column`, preserves never-treated
  controls instead of dropping missing/zero gvar, and no longer lets an optional
  pretrend diagnostic exception fail the main estimate.
- Final no-fallback modern-only full-data run:
  `reports/blind_raw_runs/jel_did_full_data/validated_run_modern_only_no_fallback_after_twfe_warning_fix/did_paper_run/20260612T120815Z-60cd9830`.
  It selected only `cs_did_attgt` and `did_imputation`; TWFE and TWFE event-study
  were excluded. Strict validation passed. Remaining warnings are data-support
  caveats: unbalanced panel, weak pre-period support, and short post-period support.

### T3.1 Dependency-gated Callaway–Sant'Anna adapter (real package)

- New file: `src/skill4econ/adapters/python/cs_did.py`. Backend choice: use
  `differences.ATTgt` for ATT(g,t). `pyfixest` remains installed and useful for
  other DID/event-study tooling, but it is not routed as sufficient for this
  adapter unless a future patch explicitly wires a modern ATT(g,t) API.
- Behavior: spec mirrors Stata `cs_did_attgt` (y, id, time, gvar, control_group =
  never_treated|not_yet_treated, covariates). Outputs: `model_table.csv` with ATT(gt)
  aggregates + event-study rows, `event_study.csv`, `pretrend_test.json`.
- Missing package ⇒ `missing_dependency`. NO numpy reimplementation of CS — that is
  exactly the MVP trap this pack exists to remove.
- Register method as `cs_did_attgt_py` in `PYTHON_METHODS`, add to
  `EXPLORATORY_METHOD_HINTS` initially, add `python_method` to the `did` section of
  `configs/estimator_registry.yaml` so routing can select it.
- Tests: golden run on `tests/fixtures/did/staggered_with_never_treated.csv` comparing
  event-study signs/magnitudes to `expected_design.json` semantics; dependency-absent
  test asserting fail-closed.

### T3.2 Routing update

- `contracts/estimator_registry.py::route_did_estimators` must offer `cs_did_attgt_py`
  for `staggered_adoption` under `engine_policy=python`, and the
  `no_modern_staggered_estimator_selected` skip must disappear when the package is
  available. Test both branches.

## Stage 4 — P1: FE scalability

### T4.1 Within-transform instead of dummy expansion

- `did_twfe_event`, `did_event_study`, `spatial_did_reduced_form`,
  `threshold_panel_search`: replace `pd.get_dummies` FE with two-way within demeaning
  (iterative demeaning until convergence, or use `pyfixest.feols` if T3.1 adopted
  pyfixest — prefer one backend, not two). Cluster SEs must match the old dummy
  implementation on small fixtures (regression test, tolerance 1e-8) while removing the
  memory cliff.
- Add a guard: if dummy expansion would exceed ~2000 columns, the old path must be gone,
  not warned about.

## Stage 5 — P1: R adapters from interface_only to real execution

### T5.1 Rscript execution harness

- `adapters/r/base.py`: implement real `Rscript` invocation (script template → temp
  file → `run_subprocess` → parse JSON the R script writes). Keep
  `interface_only_until_r_smoke` ONLY when Rscript or the R package is absent.
- Order: `fixest` (event study) → `did` (att_gt) → `drdid` → `didimputation` →
  `HonestDiD`. One adapter per PR.
- Each adapter: writes `model_table.csv` + backend log artifacts; parse failures ⇒
  `BACKEND_PARSE_FAILED` (already registered) and status `failed` — never partial rows.
- Tests: gated smoke (skip when Rscript unavailable) + parser unit tests on captured R
  output fixtures (commit small JSON/log fixtures so parsers are tested without R).

## Stage 6 — P2 (after Stages 1–5)

- T6.1 RDD: dependency-gated `rdrobust` (PyPI) adapter (CCT bandwidth, bias-corrected
  robust CI); keep `rdd_local_linear` as exploratory benchmark only.
- T6.2 Wild cluster bootstrap (Rademacher, seeded) for G < 30, wired to T1.2's risk code.
- T6.3 Conley SE: real distance-kernel implementation in `diagnostics/spatial_se.py`
  (currently distance-cutoff comparison only); lift `SPATIAL_HAC_UNIFORM_KERNEL`.
- T6.4 Contract tests for every code remaining in `TODO_REQUIRED_RISK_CODES`
  (`risk_registry.py`): each code needs at least one fixture that triggers it; then move
  the set into `REGISTERED_RISK_CODES` proper and delete the TODO set.
- T6.5 Multiple testing: Romano–Wolf or BH adjustment artifact for heterogeneity grids.

## Promotion protocol (the ONLY way a Python method becomes main_estimate)

A method moves from `EXPLORATORY_METHOD_HINTS` to the allowlist in
`test_no_registered_python_method_escapes_claim_gate_by_name` only when ALL hold:

1. Estimation runs through a maintained real package (linearmodels/statsmodels/
   pyfixest/differences/rdrobust), not a hand-rolled numpy core.
2. Inference is complete: SEs, t-based p-values, CIs; cluster option where the design
   needs it.
3. Design-specific risk gates exist and degrade claims (e.g., weak IV, few clusters,
   poor overlap) with fixtures proving degradation fires.
4. Golden fixtures validate against an external reference implementation (R/Stata
   output committed as fixture).
5. The PR updating the allowlist contains ONLY that change + its justification.

## Suggested PR sequence for Codex

PR1: T1.1 (+fixture regeneration commit). PR2: T1.2. PR3: T1.3. PR4: T2.1. PR5: T2.2.
PR6: T2.3 + T2.4. PR7: T2.5. PR8: T3.1 + T3.2. PR9: T4.1. PR10+: Stage 5 one adapter
each. Then Stage 6.

Items flagged as likely too subtle for unattended execution (request review or hand
back): T1.1 df choice edge cases, T2.2 Abadie-Imbens formula, T3.1 backend selection,
T4.1 numerical-equivalence regression test design.
