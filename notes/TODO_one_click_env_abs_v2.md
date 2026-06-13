# TODO Pack v2: One-Click Environmental-Econ ABS-Level Paper

Audience: Codex executing step by step. Successor to
`TODO_skill4econ_estimator_upgrade_v1.md` (v1 is ~90% complete and verified; do not
redo its tasks). All global rules from v1 still apply (fail-closed, no silent
fallback, promotion protocol, fixture discipline, dual test gates).

Date: 2026-06-12. Verified baseline:

- skill4econ suite: 112 passed, 1 skipped, 1 known-flaky
  (`tests/backends/test_backend_contract.py::test_probe_r_backend_with_fake_executable_ok_and_missing`
  passes in isolation; subprocess flake under full-suite load — fix in W6.3 or document).
- Root suite: 155 passed.
- Smoke `reports/multi_paper_smoke_delivery_fix2/20260612_150426`:
  `env_carbon_did_aea` (real evidence) = Tier A, write pass, release gate blocked
  ONLY by `human_eval_missing`, PDF=False. Both synthetic cases = Tier C, EvidencePack
  failed.
- Machine: MiKTeX present (latexmk/xelatex on PATH). MISSING: `differences`,
  `rdrobust`, `pyfixest` (pip), Rscript + R packages (did/drdid/didimputation/
  HonestDiD/fixest). Stata availability unknown to this pack.

## Definition of "one-click ABS-level" (acceptance contract)

A single documented command per case produces, with no manual edits in between:

1. Evidence pack where every MAIN claim in `claim_ledger` is sourced from a
   `paper_ready` modern estimator (CS-DID for staggered designs, rdrobust for RDD),
   not from an exploratory-labeled fallback.
2. Tier A pack for the flagship `env_carbon_did_aea`; Tier B+ for at least one
   second design (RDD case) — proving the pipeline is not DID-only.
3. `main.pdf` produced (PDF column True in the smoke monitor).
4. Release gate hard-blocks contain EXACTLY `human_eval_missing` and nothing else.
   Human sign-off is the designed last step — do NOT automate or weaken it.
5. The smoke monitor asserts all of the above (machine-checkable, not eyeballed).

## W1 — Backend provisioning & live certification (size S; 1 PR + one human step)

The pip/R installs themselves are a HUMAN/machine-owner step (document, don't
attempt inside CI sandboxes). Codex work:

- T1.1 Add optional dependency extras to skill4econ packaging
  (`[modern-did]`: differences; `[rdd]`: rdrobust; document pyfixest as future).
  Cross-link `docs/MODERN_DID_BACKEND_SETUP.md` (already drafted) from README.
- T1.2 Extend `live_backend_certification` so one run certifies: differences
  import + tiny ATTgt fit; rdrobust import + tiny fit; Rscript probe + per-package
  probes (did, drdid, didimputation, HonestDiD, fixest); writes a single
  `backend_certification.json` consumed by the smoke monitor.
- T1.3 Smoke monitor: add a `backends` column per case (live / partially-live /
  fail-closed) sourced from T1.2 artifact.
- DoD: with packages installed by the owner, certification artifact shows all-live;
  without them, fail-closed statuses are reported (never crashes).

## W2 — CS-DID promotion to paper_ready (size M; 2 PRs) — THE critical path

Without this, no staggered env-econ main claim exists on a Stata-less machine.

- T2.1 Reference validation fixtures: commit R `did::att_gt` + `aggte` output
  (JSON/CSV, generated once on a machine with R; include the generating R script
  under `tests/fixtures/r/cs_did/`) for `staggered_with_never_treated.csv` and
  `staggered_no_never_treated.csv`. Add a gated test (skip when `differences`
  missing) asserting `cs_did_attgt_py` matches R output: coef tolerance 1e-3
  relative, SE tolerance 5e-2 relative (document why looser: bootstrap vs analytic).
- T2.2 Wire `cs_did_attgt_py` into `did_paper_run` workflow so event_study.csv,
  pretrend_test.json, cohort_table.csv come from CS (not TWFE) when the backend is
  live; TWFE remains the comparison column, with `TWFE_STAGGERED_NOT_MAIN` retained.
- T2.3 Promotion PR (separate, contains ONLY this): move `cs_did_attgt_py` from
  `EXPLORATORY_METHOD_HINTS`, extend the invariant-test allowlist, cite T2.1
  evidence in the PR body. Promotion protocol of v1 applies verbatim.
- DoD: on a backend-live machine, `env_carbon_did_aea` claim ledger main rows carry
  `paper_ready` from `cs_did_attgt_py`.

## W3 — Inference polish to referee standard (size M; 3 PRs)

- T3.1 Wild cluster bootstrap: default reps 999 (keep `wild_cluster_bootstrap_reps`
  override); add null-imposed WCR variant as the default p-value (current
  unrestricted WCU stays as a reported column, labeled). Update few-cluster risk
  message accordingly.
- T3.2 IV upgrades: (a) divide robust Wald by df_num so the reported statistic is an
  F-scale quantity for any instrument count (fixes the multi-instrument trap noted
  in review); (b) Montiel Olea–Pflueger effective F with the 10% worst-case
  threshold (tau=10) as the primary screen, conventional F kept as secondary;
  (c) optional: Anderson–Rubin CI for the just-identified case. Risk codes:
  reuse `IV_WEAK_INSTRUMENT`; thresholds documented in the message.
- T3.3 Conley SE: real Bartlett-kernel distance-weighted spatial HAC in
  `diagnostics/spatial_se.py` (lat/lon + cutoff spec keys); lift
  `SPATIAL_HAC_UNIFORM_KERNEL` when the kernel path runs; comparison artifact
  cluster-vs-Conley. Env-econ papers with county/grid data will be asked for this.
- T3.4 Romano–Wolf stepdown (seeded bootstrap) for heterogeneity grids; adjusted
  p-value column in `heterogeneity.csv`; risk code
  `MULTIPLE_TESTING_NOT_ADJUSTED` (register) attached when a grid ships without it.
- DoD per task: golden fixture + reference cross-check where a Python reference
  exists (statsmodels/linearmodels), otherwise hand-verified small-N example
  documented in the test.

## W4 — PDF compilation (size S; 1 PR)

- T4.1 `compile_pack.py`: default to `latexmk -xelatex -interaction=nonstopmode`
  when latexmk is on PATH (MiKTeX present on the target machine); keep pdflatex
  fallback; surface the compile log tail into the result on failure.
- T4.2 Smoke monitor runs compile for the flagship case and asserts PDF=True;
  `latex_compile_failed` becomes a hard block for release-target venues (currently
  style_advice — decide: hard block only when venue requires PDF; encode in
  `venue.py`).
- DoD: smoke row for `env_carbon_did_aea` shows PDF True on this machine.

## W5 — Second design end-to-end: RDD case (size M; 2 PRs)

`urban_lez_rdd_generic` currently runs on synthetic_fixture and fails EvidencePack.

- T5.1 Build a real `rdrobust_rdd` evidence path: generate the LEZ-style fixture
  dataset, run skill4econ `rdrobust_rdd` (backend-live) producing model_table +
  rdplot-style figure manifest + bandwidth/placebo artifacts; define the RDD
  tier-A artifact list in `tiering.py` (mirror of `DID_TIER_A_ARTIFACTS`:
  rdd_main, bandwidth_sensitivity, donut_placebo, covariate_smoothness,
  density_test). McCrary/density test: use rdrobust's companion `rddensity` if
  installable, else fail-closed with a registered risk code.
- T5.2 Promotion of `rdrobust_rdd` per protocol (reference: R rdrobust output
  fixture, same pattern as T2.1) + wire the case in the smoke config from
  synthetic_fixture to real_skill4econ.
- DoD: smoke shows `urban_lez_rdd_generic` = real_skill4econ, Tier B or better,
  EvidencePack valid.

## W6 — One-click ergonomics & hygiene (size S; 1-2 PRs)

- T6.1 `econpaper oneclick --case <name>` (or a documented single script):
  intake → skill4econ runs → evidence pack → tiering → write → quality suite →
  compile → release gate → human_eval template emitted at
  `<pack>/human_eval/REQUEST.md` listing exactly what the reviewer must check.
  No step may silently skip; each stage writes its status into one
  `oneclick_status.json`.
- T6.2 Smoke monitor asserts acceptance contract items 1-4 above for the flagship
  (new totals keys: `pdf_produced_cases`, `main_claims_paper_ready_cases`,
  `only_human_eval_blocked_cases`).
- T6.3 Deflake `test_probe_r_backend_with_fake_executable_ok_and_missing`
  (likely subprocess timeout under load: raise timeout, or mark with retry; do not
  delete coverage).

## Suggested order & workload summary

| Order | Workstream | Size | Depends on |
|---|---|---|---|
| 1 | W1 backend certification | S (1 PR + owner installs) | — |
| 2 | W2 CS-DID promotion | M (2 PRs) | W1 (live backend) |
| 3 | W4 PDF | S (1 PR) | — (parallel with W2) |
| 4 | W3 inference polish | M (3 PRs) | — (parallel) |
| 5 | W5 RDD second design | M (2 PRs) | W1; pattern from W2 |
| 6 | W6 one-click + smoke asserts | S (1-2 PRs) | W2, W4 |

Total: ~10 PRs. Critical path to "flagship one-click": W1 → W2 → W4 → W6
(~5 PRs + one human install session). W3/W5 raise referee-robustness and breadth
but do not block the flagship demo.

Likely-too-subtle-for-unattended flags (request review or hand back): T2.1
tolerance calibration vs R bootstrap SEs; T3.1 WCR null imposition correctness;
T3.2 effective-F implementation (follow the 2013 paper's matrix form, add a
hand-computed fixture); T3.3 kernel weight matrix memory on large N.
