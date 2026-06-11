# Skill: sdid_gsc_for_pilot_policies

## Purpose

Plan synthetic control, synthetic difference-in-differences, generalized synthetic control, and matrix-completion designs for environmental pilot policies adopted by a small number of regions, cities, firms, plants, watersheds, or markets.

This skill is a domain reasoning and claim-language rubric for future agents. It is not an estimator, backend, package wrapper, artifact validator, or result certifier.

Use it to force an estimand-first design, make counterfactual assumptions explicit, and identify diagnostics that block causal claims when a pilot policy has a weak untreated comparison group.

## When to use

* The user studies an environmental, energy, climate, ESG, green finance, or resource policy introduced first in a few pilot jurisdictions or units.
* Treatment is adopted by one or a small number of cities, provinces, plants, utilities, firms, exchanges, watersheds, or regulated zones.
* The user is considering SCM, SDID, GSC, interactive fixed effects, matrix completion, or related synthetic counterfactual designs.
* Traditional DID looks weak because treated pilot units have different pre-treatment paths or covariates.
* The design depends on pre-treatment outcome paths, donor-pool construction, donor contamination, and extrapolation risk.
* The user needs a planning memo before spec drafting or a reviewer-style downgrade after reading artifacts.
* The user needs to distinguish treated-pilot effects from broader ATT, national, sectoral, or scalable policy effects.

## Do not use when

* The request is only to run an already validated script with no design interpretation.
* The request is to certify a completed result without status.json, claim_gate.json, artifact manifests, diagnostics, and model tables.
* There is no clearly indexed unit, time period, outcome, and treatment timing.
* The treatment is not plausibly assigned at the unit-time level.
* No untreated or not-yet-treated donor units exist for the relevant windows.
* The outcome has no meaningful pre-treatment history.
* The policy is universal at first adoption, leaving no credible donor pool.
* The user wants to claim synthetic methods are automatically superior to DID.
* The user wants to ignore anticipation, pilot selection, spillovers, contamination, or poor pre-fit.

## Inputs expected

* Research question and intended claim level.
* Unit of analysis, such as city, province, plant, firm, facility, watershed, grid cell, or market.
* Time frequency and sample window.
* Candidate outcomes and measurement sources.
* Treatment definition, pilot status, adoption date, intensity, end date, and announcement or enforcement dates.
* Count and names of treated units, if known.
* Candidate donor units and exclusion rules.
* Whether adoption is single-date, staggered, reversed, expanded in waves, or partially treated.
* Pre-treatment and post-treatment window lengths.
* Covariates measured before treatment and their timing.
* Known spillover channels across neighbors, air sheds, water basins, power grids, supply chains, or markets.
* Outcome measurement model, including monitoring intensity, reporting incentives, missingness, boundary changes, and station turnover.
* Available run artifacts and backend constraints.
* Intended estimand: unit-specific path, pilot-unit ATT, event-time ATT, cohort ATT, broader ATT, or policy-scaling effect.

## Required repo artifacts to inspect

Inspect workspace files first. Do not rely on a separately installed copy of skill4econ or on memory of repository behavior.

Minimum workspace files and directories to inspect before writing output:

* README.md
* registry.yml or skill4econ/registry.yml
* skill4econ/cli.py
* skill4econ/core.py
* skill4econ/python_wrappers.py
* skill4econ/workflows.py
* skill4econ/diagnostics/
* skill4econ/tests/fixtures/
* skill4econ/tests/backends/
* status.json when a run exists
* claim_gate.json when a run exists
* manifest.json or artifact_manifest.json when a run exists
* diagnostics.json, reviewer_risk.json, backend_status.json, and model_table.csv when present

Also read all shared rules before writing output, especially scholarly depth rules:

* `../_shared/00_skill_authoring_rules.md`
* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`
* `../_shared/08_domain_literature_anchor_rules.md`

If any required artifact is absent, say which claim is blocked. Absence of artifacts does not prove failure, but it prevents certification and strong result language.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Abadie and Gardeazabal (2003), American Economic Review, The Economic Costs of Conflict"
    - "Abadie, Diamond, and Hainmueller (2010), Journal of the American Statistical Association, Synthetic Control Methods for Comparative Case Studies"
    - "Abadie, Diamond, and Hainmueller (2015), American Journal of Political Science, Comparative Politics and the Synthetic Control Method"
    - "Xu (2017), Political Analysis, Generalized Synthetic Control Method"
    - "Arkhangelsky, Athey, Hirshberg, Imbens, and Wager (2021), American Economic Review, Synthetic Difference-in-Differences"
    - "Athey, Bayati, Doudchenko, Imbens, and Khosravi (2021), Journal of the American Statistical Association, Matrix Completion Methods for Causal Panel Data Models"
    - "Ben-Michael, Feller, and Rothstein (2021), Journal of the American Statistical Association, The Augmented Synthetic Control Method"
  canonical_data_sources:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  live_lookup_required_for:
    - "current gsynth package version and defaults"
    - "current synthdid package version and defaults"
    - "current MCPanel, gsynth, and related package defaults"
    - "current augsynth package version and defaults"
    - "current Synth, augsynth, tidysynth, microsynth package behavior"
    - "current synthdid package defaults and inference implementation"
    - "current gsynth package defaults, factor-selection criteria, bootstrap behavior"
    - "current matrix-completion package defaults and backend"
    - "current policy rollout dates, treated-unit definitions, implementation rules"
    - "current package placebo and inference defaults"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Abadie and Gardeazabal (2003), American Economic Review, The Economic Costs of Conflict"
    use_for: "original synthetic-control application, treated-unit counterfactual construction"
    live_lookup_required: []

    citation: "Abadie, Diamond, and Hainmueller (2010), Journal of the American Statistical Association, Synthetic Control Methods for Comparative Case Studies"
    use_for: "SCM weights, convex hull, pre-treatment fit, placebo inference"
    live_lookup_required: []

    citation: "Abadie, Diamond, and Hainmueller (2015), American Journal of Political Science, Comparative Politics and the Synthetic Control Method"
    use_for: "SCM diagnostics, donor pool choice, transparency, placebo tests"
    live_lookup_required: []

    citation: "Xu (2017), Political Analysis, Generalized Synthetic Control Method"
    use_for: "interactive fixed effects, GSC, latent factors, multiple treated units"
    live_lookup_required: ["current gsynth package version and defaults"]

    citation: "Arkhangelsky, Athey, Hirshberg, Imbens, and Wager (2021), American Economic Review, Synthetic Difference-in-Differences"
    use_for: "SDID unit and time weights, DID-SCM connection, inference"
    live_lookup_required: ["current synthdid package version and defaults"]

    citation: "Athey, Bayati, Doudchenko, Imbens, and Khosravi (2021), Journal of the American Statistical Association, Matrix Completion Methods for Causal Panel Data Models"
    use_for: "matrix completion, nuclear-norm regularization, low-rank causal panels"
    live_lookup_required: ["current MCPanel, gsynth, and related package defaults"]

    citation: "Ben-Michael, Feller, and Rothstein (2021), Journal of the American Statistical Association, The Augmented Synthetic Control Method"
    use_for: "bias correction, imperfect pre-fit, ridge-augmented SCM, extrapolation risk"
    live_lookup_required: ["current augsynth package version and defaults"]
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "SCM"
    - "convex weighted average of untreated donor units chosen to match pre-treatment outcomes and covariates"
    - "SDID"
    - "unit weights and time weights combining synthetic control and difference-in-differences logic"
    - "GSC"
    - "interactive fixed-effects counterfactual estimated from untreated units and pre-treatment treated outcomes"
    - "Matrix completion"
    - "low-rank untreated potential outcomes estimated by regularized matrix completion"
    - "Pilot policy panels"
    - "staggered or limited rollouts of low-carbon zones, ETS pilots, transport rules, energy standards, EJ programs, or disclosure regimes"
  validation_targets:
    - "Method distinction"
    - "Does the paper state whether it uses SCM, SDID, GSC, augmented SCM, or matrix completion and what counterfactual assumption follows?"
    - "Donor pool"
    - "Are contaminated, adjacent, soon-treated, spillover-exposed, or policy-anticipating donors excluded or stress-tested?"
    - "Pre-fit"
    - "Are pre-treatment fit, residuals, RMSPE/MSPE, and covariate balance shown before treatment effects?"
    - "Panel dimensions"
    - "Are treated count, donor count, and pre-period length adequate for the selected method and inference?"
    - "Inference"
    - "Are in-space/in-time placebos, permutation p-values, leave-one-out tests, or valid bootstrap procedures used with pre-fit filters?"
  known_mismeasurement_channels:
    - "treated unit must be near donor convex hull"
    - "poor pre-fit weakens credibility"
    - "donor contamination biases counterfactual"
    - "requires credible pre-period fit and stable untreated trends after weighting"
    - "treated count and pre-period length affect inference"
    - "weights can hide donor dependence"
    - "latent factor number selection matters"
    - "extrapolation can be implicit"
    - "unbalanced panels and missingness alter factor estimates"
    - "regularization and rank assumptions drive counterfactuals"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "SCM"
    measure: "convex weighted average of untreated donor units chosen to match pre-treatment outcomes and covariates"
    pitfalls: ["treated unit must be near donor convex hull", "poor pre-fit weakens credibility", "donor contamination biases counterfactual"]
    live_lookup_required: ["current Synth, augsynth, tidysynth, microsynth package behavior"]

    item: "SDID"
    measure: "unit weights and time weights combining synthetic control and difference-in-differences logic"
    pitfalls: ["requires credible pre-period fit and stable untreated trends after weighting", "treated count and pre-period length affect inference", "weights can hide donor dependence"]
    live_lookup_required: ["current synthdid package defaults and inference implementation"]

    item: "GSC"
    measure: "interactive fixed-effects counterfactual estimated from untreated units and pre-treatment treated outcomes"
    pitfalls: ["latent factor number selection matters", "extrapolation can be implicit", "unbalanced panels and missingness alter factor estimates"]
    live_lookup_required: ["current gsynth package defaults, factor-selection criteria, bootstrap behavior"]

    item: "Matrix completion"
    measure: "low-rank untreated potential outcomes estimated by regularized matrix completion"
    pitfalls: ["regularization and rank assumptions drive counterfactuals", "missingness must be handled explicitly", "pre-fit diagnostics remain necessary"]
    live_lookup_required: ["current matrix-completion package defaults and backend"]

    item: "Pilot policy panels"
    measure: "staggered or limited rollouts of low-carbon zones, ETS pilots, transport rules, energy standards, EJ programs, or disclosure regimes"
    pitfalls: ["pilots are often targeted to high-capacity or high-problem units", "donors may anticipate expansion", "policy timing may include announcements and phased compliance"]
    live_lookup_required: ["current policy rollout dates, treated-unit definitions, implementation rules"]

    item: "Placebo inference"
    measure: "in-space placebos, in-time placebos, permutation p-values, leave-one-out donors, conformal or bootstrap procedures"
    pitfalls: ["few donors limit p-value resolution", "bad placebo pre-fit contaminates inference", "serial correlation reduces effective sample size"]
    live_lookup_required: ["current package placebo and inference defaults"]

    item: "Convex hull and extrapolation"
    measure: "SCM donor-weight support, negative weights, augmented bias correction, factor-model extrapolation, ridge penalties"
    pitfalls: ["SCM convexity can fail with extreme treated units", "GSC/matrix completion extrapolate through factors", "augmentation reduces bias but can increase model dependence"]
    live_lookup_required: ["current package weight constraints and penalty defaults"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "using methods interchangeably because they produce a synthetic counterfactual"
    - "attenuated effects from contaminated controls"
    - "post-treatment gap interpreted despite poor pre-fit"
    - "large-sample standard errors used for a pilot with one or two treated units"
    - "hidden extrapolation presented as design-based comparison"
    - "pre-treatment behavioral response misclassified as untreated baseline"
    - "synthetic method used to hide nonrandom pilot selection"
  sorting_vs_siting_or_selection_channel:
    - "Outcome and donor targeting"
    - "selection narrative"
    - "pre-trend diagnostics"
    - "matched donor restrictions"
    - "policy-targeting covariates"
    - "placebo treated-candidate tests"
    - "synthetic method used to hide nonrandom pilot selection"
    - "current policy targeting and eligibility documents"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "SCM versus SDID versus GSC versus matrix completion"
    core_issue: "These methods impose different counterfactual restrictions: convex donor matching, weighted DID, latent factors, or low-rank completion."
    acceptable_designs: ["method choice tied to treated count and pre-period length", "cross-method triangulation", "explicit assumption statement", "pre-fit and residual diagnostics"]
    referee_risk: "using methods interchangeably because they produce a synthetic counterfactual"
    live_lookup_required: ["current package defaults and implementation differences"]

    item: "Donor contamination"
    core_issue: "Untreated donors may be exposed through spillovers, anticipation, policy diffusion, supply chains, media, or neighboring jurisdictions."
    acceptable_designs: ["exclude adjacent or soon-treated donors", "spillover buffers", "never-treated robustness", "donor exposure tests"]
    referee_risk: "attenuated effects from contaminated controls"
    live_lookup_required: ["current rollout, spillover, and policy diffusion data"]

    item: "Pre-fit and pre-period length"
    core_issue: "Credibility depends on sufficient pre-treatment periods and good fit on outcomes that predict post-treatment untreated paths."
    acceptable_designs: ["RMSPE/MSPE diagnostics", "pre-treatment residual plots", "minimum pre-period justification", "covariate and outcome lag balance"]
    referee_risk: "post-treatment gap interpreted despite poor pre-fit"
    live_lookup_required: []

    item: "Treated count and inference"
    core_issue: "Single treated-unit, few treated-unit, and many treated-unit panels need different uncertainty logic."
    acceptable_designs: ["permutation inference for few treated units", "cluster/block bootstrap when many units justify it", "placebo distribution with pre-fit filters"]
    referee_risk: "large-sample standard errors used for a pilot with one or two treated units"
    live_lookup_required: ["current package inference defaults"]

    item: "Convex hull and extrapolation"
    core_issue: "SCM requires support from donors; GSC, augmented SCM, and matrix completion can extrapolate under stronger modelling assumptions."
    acceptable_designs: ["weight inspection", "negative/extrapolation diagnostics", "leverage checks", "leave-one-donor-out robustness"]
    referee_risk: "hidden extrapolation presented as design-based comparison"
    live_lookup_required: ["current package weight and penalty defaults"]

    item: "Anticipation and phased treatment"
    core_issue: "Pilot policies often have announcement, application, approval, implementation, compliance, and enforcement dates."
    acceptable_designs: ["event-time definition audit", "anticipation windows", "donut pre-periods", "separate announcement and enforcement effects"]
    referee_risk: "pre-treatment behavioral response misclassified as untreated baseline"
    live_lookup_required: ["current policy timeline and implementation records"]

    item: "Outcome and donor targeting"
    core_issue: "Pilot sites are often chosen because of prior trends, administrative capacity, political support, or unusually high baseline pollution."
    acceptable_designs: ["selection narrative", "pre-trend diagnostics", "matched donor restrictions", "policy-targeting covariates", "placebo treated-candidate tests"]
    referee_risk: "synthetic method used to hide nonrandom pilot selection"
    live_lookup_required: ["current policy targeting and eligibility documents"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Method distinction"
    - "Does the paper state whether it uses SCM, SDID, GSC, augmented SCM, or matrix completion and what counterfactual assumption follows?"
    - "Donor pool"
    - "Are contaminated, adjacent, soon-treated, spillover-exposed, or policy-anticipating donors excluded or stress-tested?"
    - "Pre-fit"
    - "Are pre-treatment fit, residuals, RMSPE/MSPE, and covariate balance shown before treatment effects?"
    - "Panel dimensions"
    - "Are treated count, donor count, and pre-period length adequate for the selected method and inference?"
    - "Inference"
    - "Are in-space/in-time placebos, permutation p-values, leave-one-out tests, or valid bootstrap procedures used with pre-fit filters?"
  minimal_empirical_section_checklist:
    - "Method distinction"
    - "Does the paper state whether it uses SCM, SDID, GSC, augmented SCM, or matrix completion and what counterfactual assumption follows?"
    - "current package implementation defaults"
    - "Donor pool"
    - "Are contaminated, adjacent, soon-treated, spillover-exposed, or policy-anticipating donors excluded or stress-tested?"
    - "current policy rollout and spillover metadata"
    - "Pre-fit"
    - "Are pre-treatment fit, residuals, RMSPE/MSPE, and covariate balance shown before treatment effects?"
    - "Panel dimensions"
    - "Are treated count, donor count, and pre-period length adequate for the selected method and inference?"
  claims_to_downgrade:
    - "Do not treat SCM, SDID, GSC, augmented SCM, and matrix completion as interchangeable estimators."
    - "Do not use contaminated donors, adjacent spillover units, or soon-treated units without sensitivity tests."
    - "Do not interpret post-treatment gaps when pre-treatment fit is poor or undocumented."
    - "Do not use asymptotic standard errors for a one-treated-unit pilot without placebo or design-appropriate inference."
    - "Do not hide negative weights, poor convex-hull support, factor extrapolation, or regularization choices."
    - "Do not ignore anticipation, announcements, phased compliance, or enforcement timing."
    - "Do not claim pilot-policy causality from synthetic methods without explaining nonrandom site selection and donor validity."
    - "Do not make current claims about synthdid, gsynth, augsynth, Synth, tidysynth, microsynth, MCPanel, or backend/package defaults without live loo"
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Method distinction"
    ask: "Does the paper state whether it uses SCM, SDID, GSC, augmented SCM, or matrix completion and what counterfactual assumption follows?"
    live_lookup_required: ["current package implementation defaults"]

    check: "Donor pool"
    ask: "Are contaminated, adjacent, soon-treated, spillover-exposed, or policy-anticipating donors excluded or stress-tested?"
    live_lookup_required: ["current policy rollout and spillover metadata"]

    check: "Pre-fit"
    ask: "Are pre-treatment fit, residuals, RMSPE/MSPE, and covariate balance shown before treatment effects?"
    live_lookup_required: []

    check: "Panel dimensions"
    ask: "Are treated count, donor count, and pre-period length adequate for the selected method and inference?"
    live_lookup_required: []

    check: "Inference"
    ask: "Are in-space/in-time placebos, permutation p-values, leave-one-out tests, or valid bootstrap procedures used with pre-fit filters?"
    live_lookup_required: ["current package inference defaults"]

    check: "Support and extrapolation"
    ask: "Are donor weights, negative weights, leverage, convex-hull failure, and extrapolation risk reported?"
    live_lookup_required: ["current package weight constraints and penalty defaults"]

    check: "Anticipation"
    ask: "Are announcement, application, approval, implementation, compliance, and enforcement dates separated?"
    live_lookup_required: ["current policy timeline"]
```

## Forbidden claims

- Do not treat SCM, SDID, GSC, augmented SCM, and matrix completion as interchangeable estimators.
- Do not use contaminated donors, adjacent spillover units, or soon-treated units without sensitivity tests.
- Do not interpret post-treatment gaps when pre-treatment fit is poor or undocumented.
- Do not use asymptotic standard errors for a one-treated-unit pilot without placebo or design-appropriate inference.
- Do not hide negative weights, poor convex-hull support, factor extrapolation, or regularization choices.
- Do not ignore anticipation, announcements, phased compliance, or enforcement timing.
- Do not claim pilot-policy causality from synthetic methods without explaining nonrandom site selection and donor validity.
- Do not make current claims about synthdid, gsynth, augsynth, Synth, tidysynth, microsynth, MCPanel, or backend/package defaults without live loo

## Domain reasoning steps

1. Define the estimand before naming a method.

   * Candidate estimands include unit-specific treated paths, average effect for observed pilot units, event-time ATT for treated pilots, cohort ATT across waves, and broader ATT.
2. Separate pilot-unit effects from external validity.

   * A credible estimate for three pilot cities is not automatically an estimate for all cities.
3. Count treated units and adoption cohorts.

   * Staggered pilots require cohort definitions and rules for later-treated donors.
4. Audit timing.

   * Record announcement, designation, implementation, enforcement, compliance, and reporting dates.
   * If pre-treatment effects appear, use earlier timing, an anticipation window, or a downgrade.
5. Specify the measurement model.

   * Monitoring upgrades, boundary changes, station turnover, missing readings, and reporting lags can mimic effects.
6. Build the donor pool before inspecting post-treatment gaps.

   * Check air sheds, water basins, power grids, permit markets, supply chains, administrative spillovers, and neighboring policies.
   * Later-treated units are donors only before their own treatment and only if anticipation is implausible.
7. Treat pre-period length as a design gate.

   * Too little pre-treatment history weakens all synthetic designs.
   * Flexible factor models need enough pre-treatment observations to estimate latent factors.
8. Treat pre-fit as a claim gate.

   * Required evidence includes pre-treatment outcome fit, covariate balance, trajectory plots, residual patterns, and sensitivity to donor exclusions.
   * Poor or missing pre-fit blocks strong causal language even when the post-treatment gap is large.
9. Use a method decision tree.

   * SCM: best for transparent few-unit counterfactuals and interpretable donor weights.
   * SDID: useful when unit and time weighting target an average treated effect over treated unit-time cells.
   * GSC: useful when interactive fixed effects are plausible and pre-period information is adequate.
   * Matrix completion: useful for dense panels under low-rank or regularized untreated-potential-outcome structure.
10. State identification assumptions for each candidate.
11. Inspect extrapolation.

* Negative weights, large weights, sparse weights on implausible donors, and high leverage donors signal support problems.
* Weight concentration requires leave-one-donor-out checks.

12. Design placebo and permutation checks.

* Use donor placebo tests, time placebo tests, and cohort placebo tests where applicable.
* Placebo inference is weak with few donors, contaminated donors, short pre-periods, or many researcher choices.

13. Rank robustness by identification risk.

* First test donor contamination and pre-fit.
* Next test timing, anticipation, and measurement changes.
* Then test donor exclusions, covariate sets, pre-period windows, and method variants.

14. Anticipate referee objections.

* Are donors clean, comparable, and unaffected by spillovers?
* Are there pre-trends or anticipation effects?

15. Downgrade when evidence is missing.

* Unknown treated count means candidate design only.
* Unknown pre-period length blocks strong synthetic claims.
* Unassessed donor contamination blocks causal claims.
* Poor or missing pre-fit limits language to descriptive or exploratory.
* Missing backend artifacts block claims that SDID, GSC, or matrix completion actually ran.

16. Write claim language last.

* Allowed before artifacts: "candidate design", "diagnostics required", "pilot-unit estimand", and "claim readiness unknown".
* Disallowed before artifacts: "the policy reduced emissions", "synthetic control proves causality", "more credible than DID", and "national effect".

## Candidate outputs

* A concise YAML or JSON planning block using the output schema below.
* A synthetic_design_plan with treated unit count, pre-period length, donor requirements, candidate designs, pre-fit diagnostics, placebo tests, extrapolation risks, and forbidden claims.
* A research_brief separating unit, time frequency, outcome, treatment, estimand, and identification risks.
* A decision tree comparing SCM, SDID, GSC, matrix completion, and DID benchmark roles.
* A diagnostics plan distinguishing claim-blocking checks from secondary robustness checks.
* A ranked robustness plan tied to the most serious identification risks.
* A handoff list for code agents that avoids unsupported backend claims.

## Output schema

Return YAML or JSON. Do not omit the base fields. Use null or unknown rather than inventing facts.

```yaml
skill_name: string
user_question_summary: string
research_domain: string
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
synthetic_design_plan:
  treated_units_count: unknown | int
  pre_period_length: unknown | int
  donor_pool_requirements: []
  design_candidates: []
  prefit_diagnostics_required: []
  placebo_tests_required: []
  extrapolation_risks: []
  forbidden_claims: []
candidate_workflows: []
candidate_methods: []
required_diagnostics: []
recommended_robustness: []
forbidden_claims: []
claim_language:
  allowed: []
  disallowed: []
uncertainty_notes: []
next_code_actions: []
scholarly_depth:
  estimand_definition: string
  identification_assumptions: []
  measurement_model: []
  data_construction_risks: []
  method_decision_tree: []
  diagnostics_that_block_claims: []
  robustness_ranked_by_risk: []
  referee_objections: []
  downgrade_triggers: []
not_recommended_methods: []
```

## Required caveats

* This skill drafts domain reasoning and claim language. It does not validate specs, run estimators, install backends, or certify artifacts.
* Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
* If claim_gate.json is missing, claim readiness is unknown or blocked.
* For policy dates, regulations, standards, APIs, packages, and data-source facts that may change, check official/latest sources at use time.
* Pre-fit quality is a gate for synthetic causal claims, not a cosmetic diagnostic.
* Donor-pool validity is part of identification, not a robustness afterthought.
* Placebo evidence is limited when the donor pool is small, contaminated, or researcher-selected.
* Negative weights, factor extrapolation, and matrix-completion regularization can create counterfactuals outside intuitive support.
* Staggered timing changes the estimand and donor rules.
* A credible pilot-unit effect does not imply a scalable effect for untreated or future adopters.

## Forbidden claims

* Do not bypass claim_gate.json.
* Do not turn diagnostic_success into paper-ready causal success.
* Do not turn parser-only, interface-only, missing-dependency, or fallback output into a live backend result.
* Do not present unsupported fallback estimators as equivalent substitutes for SCM, SDID, GSC, or matrix completion.
* Do not make strong policy effect claims when pre-fit is poor, missing, or unreported.
* Do not ignore donor-pool contamination, spillovers, or anticipation.
* Do not claim synthetic results are automatically more credible than DID.
* Do not claim a broader ATT, national effect, sector-wide effect, or policy-scaling effect from pilot-unit evidence alone.
* Do not describe placebo/permutation evidence as definitive when the donor pool is small or researcher-selected.
* Do not hide negative weights, extreme weights, factor extrapolation, or donor leverage.
* Do not use post-treatment variables as matching covariates.
* Do not select donors based on post-treatment outcomes.
* Do not present a visually large post-treatment gap as causal without pre-fit and donor validity.

## Handoff to code

* Draft a spec that records unit, time, outcome, treatment date, anticipation window, treated units, donor pool, exclusions, and estimand.
* Build donor-pool metadata with reasons for inclusion and exclusion.
* Build pre-period and post-period windows explicitly.
* Run or request pre-fit diagnostics, covariate balance, residual plots, and trajectory plots.
* Extract unit weights, time weights, factor loadings, leverage, negative weights, and extrapolation diagnostics when available.
* Run donor leave-one-out and high-leverage donor exclusions.
* Compare SCM, SDID, GSC, matrix completion, and DID benchmark only when backends and artifacts support those runs.
* Write status.json, backend_status.json, diagnostics.json, reviewer_risk.json, model tables, artifact manifests, and claim_gate.json.

## Handoff from code artifacts

* Read claim_gate.json before writing any result language.
* Read status.json to confirm whether the workflow completed, partially completed, failed, or only parsed a spec.
* Read backend_status.json before naming a backend or package as actually used.
* Read manifest.json or artifact_manifest.json to know which tables and diagnostics exist.
* Read diagnostics.json for pre-fit, balance, placebo, donor, weight, extrapolation, and timing diagnostics.
* Read reviewer_risk.json for unresolved design risks.
* Read model_table.csv only after verifying the model that generated it.
* Inspect weight tables before making interpretability or support claims.
* If artifacts are absent or inconsistent, state that the synthetic design may be planned but not certified.

## Minimal examples

### Example 1: good planning input

User: Three cities adopted a low-carbon pilot in 2013. I have annual emissions from 2005 to 2020. Should I use SDID or GSC?

### Expected skill output

```yaml
skill_name: sdid_gsc_for_pilot_policies
user_question_summary: "Three pilot cities with annual emissions before and after 2013."
research_domain: synthetic_policy_design
research_brief:
  unit: city
  time_frequency: year
  outcome_candidates: [emissions]
  treatment_or_exposure: low_carbon_pilot
  estimand_candidates: [pilot_city_ATT, treated_unit_effect_paths]
  identification_risks: [pilot_selection, donor_contamination, anticipation, limited_pre_period]
synthetic_design_plan:
  treated_units_count: 3
  pre_period_length: 8
  donor_pool_requirements: [untreated_or_valid_not_yet_treated_cities, no_spillovers, stable_boundaries]
  design_candidates: [SCM_for_unit_paths, SDID_for_average_pilot_effect, GSC_if_factor_structure_supported, matrix_completion_if_panel_dense]
  prefit_diagnostics_required: [pre_RMSE, trajectory_fit, covariate_balance, residual_pattern_check]
  placebo_tests_required: [donor_placebo, time_placebo, leave_one_donor_out]
  extrapolation_risks: [negative_weights, high_leverage_donors, factor_extrapolation]
  forbidden_claims: [do_not_claim_effect_when_prefit_poor, do_not_generalize_to_all_cities]
candidate_workflows: [draft_synthetic_spec, inspect_donor_pool, run_prefit_and_placebos]
candidate_methods: [SCM, SDID, GSC, matrix_completion, DID_benchmark]
required_diagnostics: [donor_contamination_check, prefit_check, weight_check, placebo_check, anticipation_check]
recommended_robustness: [alternative_donor_pools, alternative_policy_dates, leave_one_treated_unit_out]
forbidden_claims: [synthetic_automatically_superior_to_DID, national_ATT_without_external_validity]
claim_language:
  allowed: ["A synthetic design can target pilot-city effects if pre-fit and donor validity are adequate."]
  disallowed: ["The pilot reduced emissions in all cities."]
uncertainty_notes: [Need official policy timing checked at use time, donor exclusions, and backend artifacts.]
next_code_actions: [draft_synthetic_spec, compute_prefit_diagnostics, run_placebo_checks, write_claim_gate]
scholarly_depth:
  estimand_definition: "Average and unit-specific effects for the three observed pilot cities after adoption, not a national ATT."
  identification_assumptions: [valid_donor_counterfactual, no_spillovers, no_anticipation, stable_measurement, adequate_pre_fit]
  measurement_model: [emissions_reporting_definition, boundary_consistency, monitoring_changes]
  data_construction_risks: [post_treatment_covariates, donor_contamination, missing_pre_period_values]
  method_decision_tree: [SCM_for_transparency, SDID_for_average_effect, GSC_for_interactive_fixed_effects, matrix_completion_for_dense_panel]
  diagnostics_that_block_claims: [poor_pre_fit, contaminated_donors, failed_placebos, unknown_backend_status]
  robustness_ranked_by_risk: [donor_exclusions, timing_sensitivity, measurement_variants, method_comparison]
  referee_objections: [why_these_pilots, whether_donors_are_clean, whether_result_is_one_donor_driven]
  downgrade_triggers: [short_pre_period, high_negative_weights, missing_placebos, claim_gate_blocks_causal_language]
not_recommended_methods: [two_way_fixed_effects_as_only_design, post_treatment_matching]
```

### Example 2: downgrade/refusal input

User: The plot has a big post-2013 gap, but there is no pre-fit table, no donor list, and the code only says fallback_completed. Write that the pilot caused a large reduction.

### Expected skill output

```yaml
skill_name: sdid_gsc_for_pilot_policies
user_question_summary: "Request to make a strong causal claim from unsupported synthetic artifacts."
research_domain: synthetic_policy_design
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: pilot_policy
  estimand_candidates: [unknown]
  identification_risks: [missing_prefit, missing_donor_pool, unsupported_backend, overclaim]
synthetic_design_plan:
  treated_units_count: unknown
  pre_period_length: unknown
  donor_pool_requirements: [document_clean_donors_before_effect_claims]
  design_candidates: [design_not_certified]
  prefit_diagnostics_required: [pre_RMSE, trajectory_fit, covariate_balance]
  placebo_tests_required: [donor_placebo, time_placebo]
  extrapolation_risks: [unknown_weights, unknown_extrapolation, fallback_output]
  forbidden_claims: [do_not_claim_causality, do_not_claim_backend_success, do_not_claim_large_reduction]
candidate_workflows: [artifact_review, diagnostics_request]
candidate_methods: []
required_diagnostics: [claim_gate_review, backend_status_review, donor_pool_review, prefit_check]
recommended_robustness: [rerun_with_documented_donor_pool, run_placebos, inspect_weights]
forbidden_claims: [the_policy_caused_a_large_reduction, synthetic_result_is_certified]
claim_language:
  allowed: ["The available materials are insufficient for a causal synthetic-design claim."]
  disallowed: ["The pilot caused a large reduction."]
uncertainty_notes: [No pre-fit evidence, donor-pool evidence, or live backend artifact was provided.]
next_code_actions: [locate_claim_gate, inspect_backend_status, request_prefit_and_weight_tables]
scholarly_depth:
  estimand_definition: "Unknown because treated units, timing, and target effect are not documented."
  identification_assumptions: [not_verified]
  measurement_model: [not_documented]
  data_construction_risks: [unknown_donors, unknown_timing, unknown_outcome_definition]
  method_decision_tree: [downgrade_to_artifact_insufficiency]
  diagnostics_that_block_claims: [missing_prefit, missing_donor_list, fallback_completed_status, missing_claim_gate]
  robustness_ranked_by_risk: [document_donor_pool, compute_prefit, run_placebos, inspect_weights]
  referee_objections: [no_counterfactual_evidence, no_backend_provenance, visual_gap_only]
  downgrade_triggers: [unsupported_backend, missing_artifacts, overclaim_request]
not_recommended_methods: [visual_gap_as_causal_evidence, unsupported_fallback_as_SCM]
```

## Completion checklist

* First line is `# Skill: sdid_gsc_for_pilot_policies`.
* All fixed second-level sections are present in the required order.
* Required repo artifacts say to inspect workspace files first.
* Shared rules 00 through 07 are listed, especially `../_shared/07_scholarly_depth_rules.md`.
* Output schema includes all common base fields.
* Output schema includes the exact synthetic_design_plan block.
* Output schema includes scholarly_depth and not_recommended_methods.
* Domain reasoning covers treated unit count, pre-period length, donor pool, pre-fit, placebo/permutation, weights, extrapolation, interactive fixed effects, and staggered adoption.
* The estimand distinguishes treated pilot units from broader ATT or policy-scaling claims.
* Donor contamination, spillovers, anticipation, and pilot selection are treated as identification risks.
* Diagnostics that block claims are explicit.
* Forbidden claims include poor pre-fit, donor contamination, and automatic superiority over DID.
* Handoff from artifacts requires claim_gate.json before strong language.
* Minimal examples include one good planning example and one downgrade/refusal example.
* Volatile policy, data, package, and API facts are framed as requiring official/latest checks at use time.
