# Skill: panel_threshold_environment

## Purpose

Plan panel-threshold and regime-switching environmental econometric designs while guarding against data-mined thresholds and causal overclaims.

This skill is a prompt/rubric layer, not an estimator, validator, backend installer, artifact certifier, legal/compliance tool, or substitute for `claim_gate.json`.

## When to use

- The user asks about threshold effects, nonlinear regimes, policy thresholds, pollution thresholds, environmental regulation intensity, or regime-dependent treatment effects.
- The project searches for or tests thresholds in panel data.
- The user needs inference, bootstrap, and claim-language guidance before interpreting threshold estimates.

## Do not use when

- The user only needs to run an already validated spec.
- The task requires current standards, datasets, package defaults, or policy facts but forbids official/latest lookup.
- The user wants causal, welfare, compliance, audit-grade, or backend-certified claims without artifacts and `claim_gate.json`.

## Inputs expected

- Research question, unit, time period, outcome, exposure or treatment, and intended claim level.
- Data sources, measurement choices, and candidate empirical design.
- Existing `status.json`, `claim_gate.json`, `manifest.json`, diagnostics, reviewer-risk, and model-table artifacts when interpreting results.

## Required repo artifacts to inspect

- `README.md`
- `registry.yml`
- `cli.py`
- `core.py`
- `python_wrappers.py`
- `workflows.py`
- `diagnostics/`
- `tests/fixtures/`
- `tests/backends/`
- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Hansen (1996), Econometrica, Inference When a Nuisance Parameter Is Not Identified under the Null Hypothesis"
    - "Hansen (1999), Journal of Econometrics, Threshold Effects in Non-Dynamic Panels: Estimation, Testing, and Inference"
    - "Hansen (2000), Econometrica, Sample Splitting and Threshold Estimation"
    - "Caner and Hansen (2004), Econometric Theory, Instrumental Variable Estimation of a Threshold Model"
    - "Gonzalo and Pitarakis (2002), Journal of Econometrics, Estimation and Model Selection Based Inference in Single and Multiple Threshold Models"
    - "Kremer, Bick, and Nautz (2013), Empirical Economics, Inflation and Growth: New Evidence from a Dynamic Panel Threshold Analysis"
    - "Seo and Shin (2016), Journal of Econometrics, Dynamic Panels with Threshold Effect and Endogeneity"
  canonical_data_sources:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  live_lookup_required_for:
    - "current implementation/package availability and defaults"
    - "current data vintage"
    - "current policy-rule definitions"
    - "current package handling of threshold grids"
    - "current software defaults for trimming, grid density, and search algorithm"
    - "current package support for sequential tests and adjusted inference"
    - "current statutory thresholds, attainment rules, permit thresholds, and standards"
    - "current data support and sample composition"
    - "current package bootstrap defaults, seeds, and cluster options"
    - "current GMM implementation defaults and diagnostics"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Hansen (1996), Econometrica, Inference When a Nuisance Parameter Is Not Identified under the Null Hypothesis"
    use_for: "nonstandard threshold inference, nuisance threshold under null, bootstrap logic"
    live_lookup_required: []

    citation: "Hansen (1999), Journal of Econometrics, Threshold Effects in Non-Dynamic Panels: Estimation, Testing, and Inference"
    use_for: "fixed-effect panel threshold regression, threshold search, confidence interval construction"
    live_lookup_required: []

    citation: "Hansen (2000), Econometrica, Sample Splitting and Threshold Estimation"
    use_for: "sample splitting, threshold confidence regions, regime-specific slope interpretation"
    live_lookup_required: []

    citation: "Caner and Hansen (2004), Econometric Theory, Instrumental Variable Estimation of a Threshold Model"
    use_for: "endogenous regressors in threshold models, IV threshold estimation"
    live_lookup_required: []

    citation: "Gonzalo and Pitarakis (2002), Journal of Econometrics, Estimation and Model Selection Based Inference in Single and Multiple Threshold Models"
    use_for: "multiple thresholds, model selection, sequential testing"
    live_lookup_required: []

    citation: "Kremer, Bick, and Nautz (2013), Empirical Economics, Inflation and Growth: New Evidence from a Dynamic Panel Threshold Analysis"
    use_for: "dynamic panel threshold implementation and endogenous regressors"
    live_lookup_required: []

    citation: "Seo and Shin (2016), Journal of Econometrics, Dynamic Panels with Threshold Effect and Endogeneity"
    use_for: "dynamic panel threshold GMM, endogenous threshold variable and regressors"
    live_lookup_required: ["current implementation/package availability and defaults"]
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "Threshold variable"
    - "pollution stock, income, regulatory stringency, climate exposure, enforcement intensity, institutional quality, renewable share, or carbon price used to split regimes"
    - "Threshold search"
    - "grid search over trimmed support of threshold variable with regime-specific slopes"
    - "Multiple thresholds and multiple testing"
    - "single, double, or sequential threshold tests across candidate variables and outcomes"
    - "Policy threshold versus statistical threshold"
    - "known statutory cutoff, attainment threshold, permit size cutoff, income tier, air-quality standard, or estimated unknown statistical breakpoint"
    - "Regime interpretation"
    - "regime-specific marginal effects below and above estimated cutoff"
  validation_targets:
    - "Threshold provenance"
    - "Is the cutoff a statutory policy threshold, theory-predicted threshold, or statistically searched threshold?"
    - "Search disclosure"
    - "Are grid range, trimming, candidate variables, candidate outcomes, and all searched thresholds disclosed?"
    - "Multiple testing"
    - "Are sequential tests, multiple candidate thresholds, and multiple outcomes corrected or validated out of sample?"
    - "Endogeneity"
    - "Could the threshold variable be chosen by households, firms, regulators, or political actors responding to the outcome?"
    - "Regime support"
    - "Are sample sizes, covariate balance, and overlap shown for each regime?"
  known_mismeasurement_channels:
    - "threshold variable may be endogenous"
    - "measurement error shifts estimated cutoff"
    - "policy variables often change discretely by rule rather than unknown threshold"
    - "multiple grid searches inflate false positives"
    - "trim choice affects eligible thresholds"
    - "sparse tails produce unstable regime estimates"
    - "unreported threshold mining creates p-hacking"
    - "sequential threshold tests need adjusted inference"
    - "candidate-variable search changes null distribution"
    - "known policy cutoff belongs in RD or kink logic, not automatic unknown-threshold search"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "Threshold variable"
    measure: "pollution stock, income, regulatory stringency, climate exposure, enforcement intensity, institutional quality, renewable share, or carbon price used to split regimes"
    pitfalls: ["threshold variable may be endogenous", "measurement error shifts estimated cutoff", "policy variables often change discretely by rule rather than unknown threshold"]
    live_lookup_required: ["current data vintage", "current policy-rule definitions", "current package handling of threshold grids"]

    item: "Threshold search"
    measure: "grid search over trimmed support of threshold variable with regime-specific slopes"
    pitfalls: ["multiple grid searches inflate false positives", "trim choice affects eligible thresholds", "sparse tails produce unstable regime estimates"]
    live_lookup_required: ["current software defaults for trimming, grid density, and search algorithm"]

    item: "Multiple thresholds and multiple testing"
    measure: "single, double, or sequential threshold tests across candidate variables and outcomes"
    pitfalls: ["unreported threshold mining creates p-hacking", "sequential threshold tests need adjusted inference", "candidate-variable search changes null distribution"]
    live_lookup_required: ["current package support for sequential tests and adjusted inference"]

    item: "Policy threshold versus statistical threshold"
    measure: "known statutory cutoff, attainment threshold, permit size cutoff, income tier, air-quality standard, or estimated unknown statistical breakpoint"
    pitfalls: ["known policy cutoff belongs in RD or kink logic, not automatic unknown-threshold search", "estimated threshold is descriptive unless tied to mechanism"]
    live_lookup_required: ["current statutory thresholds, attainment rules, permit thresholds, and standards"]

    item: "Regime interpretation"
    measure: "regime-specific marginal effects below and above estimated cutoff"
    pitfalls: ["regimes are sample-relative, not universal laws", "units near threshold may differ systematically", "threshold confidence interval can be wide"]
    live_lookup_required: ["current data support and sample composition"]

    item: "Bootstrap inference"
    measure: "nonstandard p-values and confidence intervals for threshold existence and threshold location"
    pitfalls: ["ordinary t-tests are invalid for threshold existence", "clustered panels need design-appropriate bootstrap", "few clusters weaken bootstrap reliability"]
    live_lookup_required: ["current package bootstrap defaults, seeds, and cluster options"]

    item: "Dynamic panel threshold"
    measure: "lagged dependent variable, persistence, threshold effects, endogenous regressors, and GMM moments"
    pitfalls: ["Nickell bias and weak instruments", "instrument proliferation", "threshold variable endogeneity", "short panels can be fragile"]
    live_lookup_required: ["current GMM implementation defaults and diagnostics"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "interpreting data-mined cutoffs as structural policy thresholds"
    - "regime assignment is endogenous to unobserved damages, politics, or abatement"
    - "headline threshold selected from unreported specification search"
    - "calling regime slopes heterogeneous treatment effects without treatment variation"
    - "using conventional clustered standard errors as if threshold were fixed ex ante"
    - "dynamic threshold result driven by weak instruments or overfit moments"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Threshold existence versus causal mechanism"
    core_issue: "A statistically estimated cutoff is not evidence of a causal environmental tipping point."
    acceptable_designs: ["pre-specified mechanism", "external validation", "known policy cutoff", "out-of-sample threshold stability"]
    referee_risk: "interpreting data-mined cutoffs as structural policy thresholds"
    live_lookup_required: []

    item: "Endogenous threshold variable"
    core_issue: "Income, regulation, enforcement, and pollution stocks can respond to the outcome or omitted shocks."
    acceptable_designs: ["IV threshold design", "lagged predetermined threshold checks", "policy-rule instruments", "dynamic-panel GMM when justified"]
    referee_risk: "regime assignment is endogenous to unobserved damages, politics, or abatement"
    live_lookup_required: ["current policy and enforcement data construction"]

    item: "Threshold search and multiple testing"
    core_issue: "Searching across many cutoffs, outcomes, pollutants, subgroups, and lag structures changes inference."
    acceptable_designs: ["pre-analysis grid", "family-wise or FDR adjustments", "holdout validation", "report all candidate thresholds"]
    referee_risk: "headline threshold selected from unreported specification search"
    live_lookup_required: ["current package multiple-test options"]

    item: "Regime-specific slopes"
    core_issue: "Different slopes above and below a cutoff may reflect composition, support, or nonlinear controls rather than treatment heterogeneity."
    acceptable_designs: ["support overlap checks", "covariate balance by regime", "spline and polynomial robustness", "placebo threshold variables"]
    referee_risk: "calling regime slopes heterogeneous treatment effects without treatment variation"
    live_lookup_required: []

    item: "Bootstrap and clustered panels"
    core_issue: "Threshold estimators have nonstandard distributions and panel dependence."
    acceptable_designs: ["cluster-aware bootstrap", "block bootstrap for serial dependence", "threshold confidence set reporting", "few-cluster sensitivity"]
    referee_risk: "using conventional clustered standard errors as if threshold were fixed ex ante"
    live_lookup_required: ["current bootstrap/backend behavior"]

    item: "Dynamic panels"
    core_issue: "Persistence, lagged outcomes, and endogenous regressors interact with threshold assignment."
    acceptable_designs: ["instrument-count discipline", "AR and overidentification diagnostics", "lag-depth robustness", "static-versus-dynamic comparison"]
    referee_risk: "dynamic threshold result driven by weak instruments or overfit moments"
    live_lookup_required: ["current package GMM defaults and diagnostic output"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Threshold provenance"
    - "Is the cutoff a statutory policy threshold, theory-predicted threshold, or statistically searched threshold?"
    - "Search disclosure"
    - "Are grid range, trimming, candidate variables, candidate outcomes, and all searched thresholds disclosed?"
    - "Multiple testing"
    - "Are sequential tests, multiple candidate thresholds, and multiple outcomes corrected or validated out of sample?"
    - "Endogeneity"
    - "Could the threshold variable be chosen by households, firms, regulators, or political actors responding to the outcome?"
    - "Regime support"
    - "Are sample sizes, covariate balance, and overlap shown for each regime?"
  minimal_empirical_section_checklist:
    - "Threshold provenance"
    - "Is the cutoff a statutory policy threshold, theory-predicted threshold, or statistically searched threshold?"
    - "current policy cutoff and standard definitions"
    - "Search disclosure"
    - "Are grid range, trimming, candidate variables, candidate outcomes, and all searched thresholds disclosed?"
    - "current package grid/search defaults"
    - "Multiple testing"
    - "Are sequential tests, multiple candidate thresholds, and multiple outcomes corrected or validated out of sample?"
    - "current package inference options"
    - "Endogeneity"
  claims_to_downgrade:
    - "Do not call an estimated statistical threshold a policy threshold unless the cutoff is externally defined."
    - "Do not interpret a searched cutoff as a causal tipping point without theory, validation, and identification."
    - "Do not ignore multiple testing from searching across thresholds, variables, outcomes, lags, or subgroups."
    - "Do not treat endogenous threshold variables as exogenous regime splitters without an identification strategy."
    - "Do not use conventional fixed-threshold t-tests for threshold existence or location after searching."
    - "Do not present regime-specific slopes as treatment effects without credible exogenous treatment variation."
    - "Do not run dynamic panel threshold models without addressing persistence, weak instruments, instrument proliferation, and GMM diagnostics."
    - "Do not make current claims about threshold-regression package defaults, grid search, bootstrap, GMM backend, or implementation behavior without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Threshold provenance"
    ask: "Is the cutoff a statutory policy threshold, theory-predicted threshold, or statistically searched threshold?"
    live_lookup_required: ["current policy cutoff and standard definitions"]

    check: "Search disclosure"
    ask: "Are grid range, trimming, candidate variables, candidate outcomes, and all searched thresholds disclosed?"
    live_lookup_required: ["current package grid/search defaults"]

    check: "Multiple testing"
    ask: "Are sequential tests, multiple candidate thresholds, and multiple outcomes corrected or validated out of sample?"
    live_lookup_required: ["current package inference options"]

    check: "Endogeneity"
    ask: "Could the threshold variable be chosen by households, firms, regulators, or political actors responding to the outcome?"
    live_lookup_required: ["current data construction and policy rules"]

    check: "Regime support"
    ask: "Are sample sizes, covariate balance, and overlap shown for each regime?"
    live_lookup_required: []

    check: "Bootstrap inference"
    ask: "Are threshold existence, threshold location, and slope estimates inferred using valid nonstandard or bootstrap methods?"
    live_lookup_required: ["current bootstrap defaults and backend"]

    check: "Dynamic specification"
    ask: "For dynamic panels, are lagged outcome bias, instrument proliferation, weak instruments, and threshold endogeneity diagnosed?"
    live_lookup_required: ["current GMM/package diagnostics"]
```

## Forbidden claims

- Do not call an estimated statistical threshold a policy threshold unless the cutoff is externally defined.
- Do not interpret a searched cutoff as a causal tipping point without theory, validation, and identification.
- Do not ignore multiple testing from searching across thresholds, variables, outcomes, lags, or subgroups.
- Do not treat endogenous threshold variables as exogenous regime splitters without an identification strategy.
- Do not use conventional fixed-threshold t-tests for threshold existence or location after searching.
- Do not present regime-specific slopes as treatment effects without credible exogenous treatment variation.
- Do not run dynamic panel threshold models without addressing persistence, weak instruments, instrument proliferation, and GMM diagnostics.
- Do not make current claims about threshold-regression package defaults, grid search, bootstrap, GMM backend, or implementation behavior without live lookup.

## Domain reasoning steps

- Define whether the threshold is policy-defined, scientifically pre-specified, or statistically searched from the sample.
- State the threshold variable, regime outcome, unit, time, dynamic structure, and estimand before model selection.
- Treat threshold search and multiple testing as first-order inference problems, not as cosmetic specification choices.
- Audit endogenous threshold variables, dynamic panels, and post-treatment regime classification before causal language.
- Downgrade regime claims when bootstrap inference, support by regime, or threshold stability is missing.

## Candidate outputs

- A YAML or JSON planning block with research brief, measurement choices, identification risks, diagnostics, robustness, forbidden claims, and next code actions.
- A claim-safe downgrade note when artifacts or assumptions cannot support the requested language.

## Output schema

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
literature_anchors:
  canonical_papers_or_authors: []
  canonical_data_sources: []
  live_lookup_required_for: []
measurement_regimes:
  competing_proxy_definitions: []
  validation_targets: []
  known_mismeasurement_channels: []
identification_debate:
  core_threats: []
  sorting_vs_siting_or_selection_channel: null
  why_method_not_magic: []
referee_entry_points:
  likely_major_objections: []
  minimal_empirical_section_checklist: []
  claims_to_downgrade: []
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
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any strong claim must be allowed by `claim_gate.json` and supported by diagnostics and manifests.
- Volatile standards, source versions, policy rules, package defaults, and data coverage require official/latest lookup at use time.

## Handoff to code

- Ask code to validate specs, inspect artifacts, run diagnostics, and write claim gates.

## Handoff from code artifacts

- Read claim levels, agent status, diagnostics, reviewer risks, backend status, and missing artifact lists before prose.

## Completion checklist

- Literature, data, measurement, identification, referee, and forbidden-claim fields are present and non-empty.
- No causal, welfare, compliance, or backend-certified claim bypasses `claim_gate.json`.
- Current facts are marked for live lookup rather than hardcoded.
