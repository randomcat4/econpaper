# Skill: ppmlhdfe_environmental_flows

## Purpose

Plan PPMLHDFE research designs for nonnegative environmental flows, green trade flows, emissions flows, pollution counts, patent counts, and related low-carbon outcomes.
This skill is a prompt and rubric layer for future agents; it is not an estimator, backend installer, validator, or artifact certifier.
Use it to define the estimand, fixed-effect structure, zero handling, separation diagnostics, offset or exposure rules, clustering, and claim language.
The default posture is strict: PPMLHDFE is backend-required for this workflow, and OLS, log-linear, add-one-log, or ordinary Poisson fallbacks must not be called equivalent.
PPMLHDFE estimates conditional-mean multiplicative relationships; causal language depends on a separate identification design.

## When to use

- The user asks about nonnegative trade, emissions, patent, innovation, pollution-event, shipping, electricity, carbon-market, or environmental-flow outcomes.
- The outcome is a flow, count, nonnegative amount, or exposure-normalized incidence candidate with zeros.
- The user mentions PPMLHDFE, Poisson pseudo-maximum likelihood, gravity, high-dimensional fixed effects, exporter-importer-year designs, or separation.
- The study involves green trade, embodied carbon, emissions trading, carbon border policies, environmental patents, pollution incidents, or low-carbon technology diffusion.
- The user asks whether to delete zeros, add one before logging, or use log-linear OLS as a substitute.
- The user needs a plan before code, a referee-facing design audit, or a claim-language downgrade after artifacts.

## Do not use when

- Do not use when the user only needs to execute an already validated PPMLHDFE spec with no research-design issue.
- Do not use to certify completed results without claim_gate.json, status.json, backend evidence, diagnostics, and artifact provenance.
- Do not use when the outcome can be negative and no nonnegative conditional-mean model is being proposed.
- Do not use to replace a missing PPMLHDFE backend with OLS, log-linear OLS, add-one-log OLS, or another estimator and call it equivalent.
- Do not use when the user's real question is only a package installation issue.
- Do not use to assert current policy, dataset, API, package, or regulatory facts unless official/latest sources are checked at use time.
- If separation, convergence, fixed-effect support, or clustering cannot be checked, downgrade strong claims.

## Inputs expected

- Research question, intended claim level, and target audience.
- Outcome definition, nonnegative support, units, time aggregation, and whether zeros are present.
- Outcome type: trade_flow, count, emissions_flow, patent_count, or unknown.
- Unit of observation, such as exporter-importer-product-year, firm-year, plant-day, city-month, or patent-class-country-year.
- Treatment, exposure, or covariate of interest and the level at which it varies.
- Candidate fixed effects, such as exporter-year, importer-year, pair, product-year, firm, region-year, industry-year, or event-time cells.
- Candidate clusters justified by treatment variation and error dependence.
- Exposure or offset variables, such as population, firm size, time at risk, market size, or monitoring effort.
- Zero-generating mechanisms, missing-value rules, censoring, truncation, and sample restrictions.
- Gravity-style variables and whether they are identified after fixed effects.
- Existing artifacts when interpreting a run: specs, backend status, diagnostics, dropped observations, separation logs, model tables, and claim gates.

## Required repo artifacts to inspect

Inspect workspace files first. Do not rely on a locally installed copy of skill4econ or on memory of an older repository state.
Inspect these workspace paths before writing a repository-aware response:
- `README.md`
- `skill4econ/registry.yml`
- `skill4econ/cli.py`
- `skill4econ/core.py`
- `skill4econ/python_wrappers.py`
- `skill4econ/workflows.py`
- `skill4econ/diagnostics/`
- `skill4econ/tests/fixtures/`
- `skill4econ/tests/backends/`
- `status.json` when a run exists
- `claim_gate.json` when a run exists
- `manifest.json` or `artifact_manifest.json` when a run exists
- `diagnostics.json`, `reviewer_risk.json`, `backend_status.json`, and `model_table.csv` when present
- any PPMLHDFE, gravity, flow, count, emissions-flow, or high-dimensional-FE spec files in the workspace
Also read shared rules before writing output:
- `../_shared/00_skill_authoring_rules.md`
- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`
Rule `../_shared/07_scholarly_depth_rules.md` is required, not optional, because it forces estimands, assumptions, measurement model, diagnostics that block claims, referee objections, and downgrade triggers.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Santos Silva and Tenreyro (2006), Review of Economics and Statistics, The Log of Gravity"
    - "Santos Silva and Tenreyro (2011), Economics Letters, Further Simulation Evidence on the Performance of the Poisson Pseudo-Maximum Likelihood Estimator"
    - "Correia, Guimarães, and Zylkin (2020), Stata Journal, Fast Poisson Estimation with High-Dimensional Fixed Effects"
    - "Correia, Guimarães, and Zylkin (2019), arXiv, Verifying the Existence of Maximum Likelihood Estimates for Generalized Linear Models"
    - "Head and Mayer (2014), Handbook of International Economics, Gravity Equations: Workhorse, Toolkit, and Cookbook"
    - "Fally (2015), Journal of International Economics, Structural Gravity and Fixed Effects"
    - "Yotov, Piermartini, Monteiro, and Larch (2016), WTO, An Advanced Guide to Trade Policy Analysis"
  canonical_data_sources:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  live_lookup_required_for:
    - "current ppmlhdfe version, defaults, separation methods, backend behavior"
    - "current implementation of separation checks in ppmlhdfe/fixest/pyfixest"
    - "current trade, emissions, customs, MRIO, and flow-data vintages"
    - "current package rules for zero and separated cells"
    - "current ppmlhdfe/fixest/pyfixest separation diagnostics and drop logs"
    - "current package backend limits and collinearity defaults"
    - "current package offset syntax and default treatment"
    - "current package small-sample corrections and variance defaults"
    - "current separation algorithm and package logs"
    - "current collinearity and singleton-drop defaults"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Santos Silva and Tenreyro (2006), Review of Economics and Statistics, The Log of Gravity"
    use_for: "PPML under heteroskedasticity, conditional mean interpretation, zeros in gravity-style flows"
    live_lookup_required: []

    citation: "Santos Silva and Tenreyro (2011), Economics Letters, Further Simulation Evidence on the Performance of the Poisson Pseudo-Maximum Likelihood Estimator"
    use_for: "finite-sample PPML performance and robustness relative to log-linear alternatives"
    live_lookup_required: []

    citation: "Correia, Guimarães, and Zylkin (2020), Stata Journal, Fast Poisson Estimation with High-Dimensional Fixed Effects"
    use_for: "ppmlhdfe algorithm, high-dimensional FE, separation diagnostics and dropped observations"
    live_lookup_required: ["current ppmlhdfe version, defaults, separation methods, backend behavior"]

    citation: "Correia, Guimarães, and Zylkin (2019), arXiv, Verifying the Existence of Maximum Likelihood Estimates for Generalized Linear Models"
    use_for: "existence of PPML estimates, separation, nonexistence diagnostics"
    live_lookup_required: ["current implementation of separation checks in ppmlhdfe/fixest/pyfixest"]

    citation: "Head and Mayer (2014), Handbook of International Economics, Gravity Equations: Workhorse, Toolkit, and Cookbook"
    use_for: "gravity specifications, multilateral resistance, fixed effects, cluster choices"
    live_lookup_required: []

    citation: "Fally (2015), Journal of International Economics, Structural Gravity and Fixed Effects"
    use_for: "structural gravity with PPML and importer/exporter fixed effects"
    live_lookup_required: []

    citation: "Yotov, Piermartini, Monteiro, and Larch (2016), WTO, An Advanced Guide to Trade Policy Analysis"
    use_for: "applied PPML gravity workflow, zeros, fixed effects, policy-flow interpretation"
    live_lookup_required: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "Environmental flows"
    - "bilateral or origin-destination flows of embodied carbon, waste trade, pollution permits, green goods, migration exposure, commodity shipments, or facility-to-destination emissions"
    - "Conditional mean PPML"
    - "E[y_it | x_it, fixed effects] = exp(x_it beta + FE), not a logged-outcome regression"
    - "Zero outcomes"
    - "PPML keeps y=0 observations in nonnegative-flow models"
    - "Separation and dropped cells"
    - "observations, covariates, or FE levels dropped because MLE does not exist or outcome is perfectly predicted"
    - "Fixed-effect saturation"
    - "origin, destination, product, year, origin-year, destination-year, pair, sector-year, route, facility, or policy-region fixed effects"
  validation_targets:
    - "Estimand"
    - "Is the coefficient interpreted as a conditional-mean level effect rather than a logged-flow effect?"
    - "Zeros"
    - "Are zero flows kept, classified, and discussed rather than log-transformed away?"
    - "Separation"
    - "Are separated observations, singleton FE, dropped cells, and nonexistence diagnostics reported?"
    - "FE variation"
    - "Does the paper show which policy variation survives the chosen high-dimensional fixed effects?"
    - "Offset"
    - "Is any exposure offset pre-treatment, correctly logged, and conceptually distinct from a regressor?"
  known_mismeasurement_channels:
    - "zeros can be structural or sampling zeros"
    - "negative net flows are incompatible with Poisson mean"
    - "unit aggregation changes extensive margins"
    - "coefficient is semi-elasticity for conditional mean"
    - "error distribution need not be Poisson"
    - "overdispersion does not invalidate PPML consistency under correct conditional mean"
    - "zeros with separated covariate patterns may be dropped"
    - "adding one and logging changes estimand"
    - "zero-inflation requires substantive diagnosis, not automatic replacement"
    - "silent drops can change identifying sample"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "Environmental flows"
    measure: "bilateral or origin-destination flows of embodied carbon, waste trade, pollution permits, green goods, migration exposure, commodity shipments, or facility-to-destination emissions"
    pitfalls: ["zeros can be structural or sampling zeros", "negative net flows are incompatible with Poisson mean", "unit aggregation changes extensive margins"]
    live_lookup_required: ["current trade, emissions, customs, MRIO, and flow-data vintages"]

    item: "Conditional mean PPML"
    measure: "E[y_it | x_it, fixed effects] = exp(x_it beta + FE), not a logged-outcome regression"
    pitfalls: ["coefficient is semi-elasticity for conditional mean", "error distribution need not be Poisson", "overdispersion does not invalidate PPML consistency under correct conditional mean"]
    live_lookup_required: []

    item: "Zero outcomes"
    measure: "PPML keeps y=0 observations in nonnegative-flow models"
    pitfalls: ["zeros with separated covariate patterns may be dropped", "adding one and logging changes estimand", "zero-inflation requires substantive diagnosis, not automatic replacement"]
    live_lookup_required: ["current package rules for zero and separated cells"]

    item: "Separation and dropped cells"
    measure: "observations, covariates, or FE levels dropped because MLE does not exist or outcome is perfectly predicted"
    pitfalls: ["silent drops can change identifying sample", "policy cells may be separated", "dropped singleton FE or all-zero groups can alter estimand"]
    live_lookup_required: ["current ppmlhdfe/fixest/pyfixest separation diagnostics and drop logs"]

    item: "Fixed-effect saturation"
    measure: "origin, destination, product, year, origin-year, destination-year, pair, sector-year, route, facility, or policy-region fixed effects"
    pitfalls: ["policy variation can be absorbed", "incidental sparse cells create instability", "FE choice defines comparison set"]
    live_lookup_required: ["current package backend limits and collinearity defaults"]

    item: "Offset and exposure"
    measure: "log exposure offset for population, output, tonnage at risk, facility capacity, distance-time exposure, or sampling effort"
    pitfalls: ["offset coefficient is constrained to one", "exposure must be exogenous to treatment or modelled separately", "using exposure as regressor changes estimand"]
    live_lookup_required: ["current package offset syntax and default treatment"]

    item: "Cluster choice"
    measure: "cluster-robust inference by origin, destination, pair, sector, policy unit, time, multiway clusters, or randomization unit"
    pitfalls: ["clustering below treatment assignment overstates precision", "few treated clusters require correction", "dyadic dependence may need multiway clustering"]
    live_lookup_required: ["current package small-sample corrections and variance defaults"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "presenting PPML estimator choice as causal design"
    - "interpreting PPML coefficients as log-linear OLS coefficients after dropping zeros"
    - "headline effect comes from a selected estimation sample"
    - "coefficient identified only by a few sparse cells"
    - "dividing by a post-treatment exposure mediator"
    - "statistical significance from under-clustering"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "PPML fixes mean-specification and zero-outcome issues but does not create exogenous treatment variation."
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "PPML is not identification"
    core_issue: "PPML fixes mean-specification and zero-outcome issues but does not create exogenous treatment variation."
    acceptable_designs: ["credible policy shock", "event study with valid controls", "structural gravity restrictions", "pre-trend and placebo tests"]
    referee_risk: "presenting PPML estimator choice as causal design"
    live_lookup_required: []

    item: "Conditional mean interpretation"
    core_issue: "The coefficient describes multiplicative changes in the conditional mean of levels, not changes in log outcomes."
    acceptable_designs: ["marginal effects in levels", "counterfactual predictions", "baseline-mean scaling", "clear semi-elasticity language"]
    referee_risk: "interpreting PPML coefficients as log-linear OLS coefficients after dropping zeros"
    live_lookup_required: []

    item: "Separation-induced estimand drift"
    core_issue: "Separated cells and all-zero FE groups can remove treated or high-exposure observations."
    acceptable_designs: ["report dropped observations and FE levels", "compare pre/post drop sample", "stress-test separated policy cells", "archive package logs"]
    referee_risk: "headline effect comes from a selected estimation sample"
    live_lookup_required: ["current separation algorithm and package logs"]

    item: "FE saturation and policy variation"
    core_issue: "High-dimensional FE can absorb treatment variation or leave only narrow within-cell comparisons."
    acceptable_designs: ["variation audit", "leave-one-FE-out robustness", "identified-cell table", "policy-by-FE collinearity checks"]
    referee_risk: "coefficient identified only by a few sparse cells"
    live_lookup_required: ["current collinearity and singleton-drop defaults"]

    item: "Offset and exposure endogeneity"
    core_issue: "Offsets impose proportionality and require exposure to be pre-determined or separately identified."
    acceptable_designs: ["pre-treatment exposure", "alternative denominator specifications", "no-offset robustness", "exposure-as-outcome check"]
    referee_risk: "dividing by a post-treatment exposure mediator"
    live_lookup_required: []

    item: "Inference clustering"
    core_issue: "Flow panels contain serial, spatial, dyadic, and policy-cluster dependence."
    acceptable_designs: ["cluster at treatment assignment level", "multiway clustering", "few-cluster wild bootstrap", "dyadic dependence robustness"]
    referee_risk: "statistical significance from under-clustering"
    live_lookup_required: ["current package cluster and bootstrap implementation"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Estimand"
    - "Is the coefficient interpreted as a conditional-mean level effect rather than a logged-flow effect?"
    - "Zeros"
    - "Are zero flows kept, classified, and discussed rather than log-transformed away?"
    - "Separation"
    - "Are separated observations, singleton FE, dropped cells, and nonexistence diagnostics reported?"
    - "FE variation"
    - "Does the paper show which policy variation survives the chosen high-dimensional fixed effects?"
    - "Offset"
    - "Is any exposure offset pre-treatment, correctly logged, and conceptually distinct from a regressor?"
  minimal_empirical_section_checklist:
    - "Estimand"
    - "Is the coefficient interpreted as a conditional-mean level effect rather than a logged-flow effect?"
    - "Zeros"
    - "Are zero flows kept, classified, and discussed rather than log-transformed away?"
    - "current package zero-handling behavior"
    - "Separation"
    - "Are separated observations, singleton FE, dropped cells, and nonexistence diagnostics reported?"
    - "current ppmlhdfe/fixest/pyfixest separation defaults"
    - "FE variation"
    - "Does the paper show which policy variation survives the chosen high-dimensional fixed effects?"
  claims_to_downgrade:
    - "Do not say PPML estimates log outcomes; it estimates a conditional mean in levels with log link."
    - "Do not claim PPML solves endogeneity or selection by itself."
    - "Do not drop zeros through log(y+1) and call the estimand equivalent to PPML."
    - "Do not hide separated observations, singleton FE, all-zero groups, or dropped policy cells."
    - "Do not use saturated fixed effects without showing the remaining identifying variation."
    - "Do not impose an offset when the exposure variable is post-treatment or conceptually part of the outcome."
    - "Do not cluster below the treatment-assignment or dependence level."
    - "Do not make current claims about ppmlhdfe, fixest, pyfixest, separation algorithms, small-sample corrections, or backend defaults without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Estimand"
    ask: "Is the coefficient interpreted as a conditional-mean level effect rather than a logged-flow effect?"
    live_lookup_required: []

    check: "Zeros"
    ask: "Are zero flows kept, classified, and discussed rather than log-transformed away?"
    live_lookup_required: ["current package zero-handling behavior"]

    check: "Separation"
    ask: "Are separated observations, singleton FE, dropped cells, and nonexistence diagnostics reported?"
    live_lookup_required: ["current ppmlhdfe/fixest/pyfixest separation defaults"]

    check: "FE variation"
    ask: "Does the paper show which policy variation survives the chosen high-dimensional fixed effects?"
    live_lookup_required: ["current package collinearity behavior"]

    check: "Offset"
    ask: "Is any exposure offset pre-treatment, correctly logged, and conceptually distinct from a regressor?"
    live_lookup_required: ["current package offset syntax"]

    check: "Clustering"
    ask: "Are standard errors clustered at the treatment-assignment or dependence level, with few-cluster corrections when needed?"
    live_lookup_required: ["current variance and bootstrap defaults"]

    check: "Causality"
    ask: "Does the design identify policy effects independently of the PPML estimator?"
    live_lookup_required: []
```

## Forbidden claims

- Do not say PPML estimates log outcomes; it estimates a conditional mean in levels with log link.
- Do not claim PPML solves endogeneity or selection by itself.
- Do not drop zeros through log(y+1) and call the estimand equivalent to PPML.
- Do not hide separated observations, singleton FE, all-zero groups, or dropped policy cells.
- Do not use saturated fixed effects without showing the remaining identifying variation.
- Do not impose an offset when the exposure variable is post-treatment or conceptually part of the outcome.
- Do not cluster below the treatment-assignment or dependence level.
- Do not make current claims about ppmlhdfe, fixest, pyfixest, separation algorithms, small-sample corrections, or backend defaults without live lookup.

## Domain reasoning steps

- Define the estimand before naming the estimator.
- For descriptive designs, define the estimand as a conditional-mean multiplicative association in the observed support.
- For causal designs, define the estimand as a treatment or exposure effect on the conditional mean only if identification assumptions and artifacts support it.
- Do not interpret a coefficient as causal merely because high-dimensional fixed effects are absorbed.
- Confirm the outcome is nonnegative and measured on an economically meaningful scale.
- Treat zeros as data signal, not nuisance observations to delete.
- Do not add one and log the outcome as the main result for this workflow.
- Check whether zeros represent no trade, no emissions, no patenting, no event, no monitoring, suppressed data, or missing data.
- Distinguish true zeros from missing values, structural impossibility, confidential suppression, and sample selection.
- State whether the outcome is trade_flow, count, emissions_flow, patent_count, or unknown.
- If the outcome is a count, identify the population at risk and time at risk.
- If the outcome is an emissions flow, identify whether it is production-based, consumption-based, embodied, facility-level, or permit-level.
- If the outcome is a patent count, define patent family, application year, grant year, technology class, and geography when available.
- If the outcome is trade flow, define reporter, partner, product, currency, deflation, and whether re-exports or mirror flows matter.
- Specify fixed effects as identification content, not just controls.
- In gravity-style settings, consider exporter-year and importer-year fixed effects for multilateral resistance or time-varying country shocks.
- Consider pair fixed effects for time-invariant bilateral heterogeneity.
- Consider product-year, sector-year, firm, plant, region-year, or market-year fixed effects when they match the exposure and outcome process.
- Check whether the treatment or exposure is absorbed by candidate fixed effects.
- Check whether remaining identifying variation is within the intended comparison set.
- State which coefficients are identified after fixed effects and which are not.
- Block interpretation if the FE structure mechanically removes the treatment or leaves no support.
- Define clusters based on treatment variation, assignment level, serial dependence, spatial dependence, and repeated dyads.
- Do not choose clusters only to make standard errors small.
- For policies assigned at country, region, firm, plant, product, or dyad level, include that level among cluster candidates unless design facts rule it out.
- Consider multiway clustering when shocks are plausibly correlated along more than one dimension.
- If few clusters or leverage-heavy clusters are likely, flag inference as fragile and require diagnostics.
- Pre-specify exposure or offset variables when outcomes are counts or flows per opportunity.
- Treat offsets as measurement model components, not ex post fixes for significance.
- Do not include a variable as both offset and ordinary regressor without a clear interpretation.
- Check whether population, monitoring effort, market size, distance, or baseline volume is an exposure, control, offset, or outcome component.
- Require separation diagnostics before interpreting coefficients.
- Explain that separation can drop observations, fixed-effect cells, or covariate support and thereby change the estimand.
- Record separated observations and whether treatment variation is lost.
- Require convergence diagnostics, iteration status, tolerance status, coefficient existence, and finite standard errors.
- Treat convergence warnings, nonexistence, or separation-driven dropping of core support as blocking diagnostics.
- Require a live PPMLHDFE backend artifact for backend-certified claims.
- If PPMLHDFE is missing, set `fallback_allowed: false` and do not run or recommend an equivalent fallback.
- A differently labeled exploratory sensitivity can be proposed only if it is not presented as PPMLHDFE or equivalent evidence.
- For gravity designs, verify that bilateral, exporter, importer, product, and time fixed effects match the claimed comparison.
- For event or policy designs, verify timing, anticipation, staggered adoption, and post-treatment fixed-effect risks using a causal-design skill when needed.
- For emissions trading or carbon policy studies, check official/latest policy definitions at use time before asserting coverage, timing, or compliance facts.
- For patent or pollution-event counts, check whether changes in monitoring, reporting, classification, or data availability drive the count.
- Block claims when the nonnegative outcome, zero status, FE structure, cluster choice, separation diagnostics, convergence diagnostics, or backend evidence is missing.
- Anticipate referee objections about deleted zeros, add-one logs, over-absorbed treatment variation, separation, fragile clusters, offset ambiguity, and conflating association with causality.
- Downgrade any result that is parser-only, interface-only, dry-run-only, missing-dependency, unsupported-backend, nonconverged, separated beyond support, or not allowed by claim_gate.json.

## Candidate outputs

- `ppmlhdfe_environmental_flows_plan` YAML block.
- Research brief with unit, frequency, candidate outcomes, treatment or exposure, estimand candidates, and identification risks.
- Candidate workflows for PPMLHDFE gravity, count, emissions-flow, patent-count, or pollution-event designs.
- Candidate fixed-effect structures with identification implications.
- Cluster candidates tied to assignment, treatment variation, and dependence.
- Required diagnostics for zeros, separation, convergence, support, dropped observations, exposure or offset, and backend status.
- Robustness checks ranked by measurement and identification risk.
- Referee objections, downgrade triggers, and forbidden claim language.
- Handoff instructions for code and for reading completed artifacts.

## Output schema

Return YAML or JSON. Do not omit the base fields. Use null, unknown, or empty arrays when information is unknown; do not invent missing values.

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
ppmlhdfe_environmental_flows_plan:
  outcome_type: trade_flow | count | emissions_flow | patent_count | unknown
  zeros_present: unknown | true | false
  fixed_effects_candidates: []
  cluster_candidates: []
  separation_risk: unknown | low | medium | high
  backend_required: ppmlhdfe
  fallback_allowed: false
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

The domain-specific block must keep the exact field names above. The `scholarly_depth` and `not_recommended_methods` blocks are required in both planning and downgrade outputs.

## Required caveats

- PPMLHDFE targets a conditional-mean multiplicative relationship; causal language depends on design, not on the estimator name.
- Nonnegative outcomes and zeros are central to the measurement model.
- Zeros must not be deleted or add-one-logged as the main result for this workflow.
- High-dimensional fixed effects define the identifying comparison and can absorb the treatment.
- Cluster choices should follow assignment, treatment variation, repeated observations, and dependence.
- Separation can drop support and change the estimand.
- Convergence and finite-estimate diagnostics are required before interpreting coefficients.
- Exposure and offset choices must be pre-specified and measured consistently.
- Gravity-style designs need fixed effects that match exporter, importer, product, time, dyad, and policy variation.
- PPMLHDFE backend evidence is required for backend-certified claims.
- `fallback_allowed` is false; alternative exploratory models must be labeled as non-equivalent sensitivity only.
- A skill drafts reasoning and language; it does not validate specs, run backends, install packages, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- For volatile policy, regulation, standard, API, package, and data-source facts, check official/latest sources at use time.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic success into paper-ready causal success.
- Do not turn parser-only, interface-only, missing-dependency, dry-run, or skipped-backend output into a live PPMLHDFE result.
- If ppmlhdfe is missing, do not use OLS, log-linear OLS, add-one-log OLS, ordinary Poisson, or any other fallback and say it is equivalent.
- Do not ignore separation, dropped observations, support loss, nonconvergence, or infinite estimates.
- Do not add 1 and log the outcome as the main result.
- Do not delete zeros merely because log-linear models cannot use them.
- Do not describe fixed effects as harmless controls when they define identification and support.
- Do not choose clusters for convenience or significance.
- Do not treat an offset as optional after seeing results.
- Do not claim green trade, emissions flows, or patent counts changed because of a policy without a separate identification design.
- Do not certify code execution, backend availability, package behavior, or current policy facts without artifacts or official/latest checks.

## Handoff to code

- Draft a spec with outcome type, unit, time, treatment or exposure, fixed effects, clusters, and offset or exposure variables.
- Validate nonnegative outcome support and classify zeros as true zeros, missing values, structural impossibilities, or suppressed observations.
- Validate sample restrictions before model fitting.
- Validate whether treatment variation survives the fixed effects.
- Run separation diagnostics and record separated observations, dropped cells, and treatment-support loss.
- Run convergence diagnostics and record iteration status, tolerance, finite estimates, and finite standard errors.
- Record PPMLHDFE backend evidence; do not mark parser-only or dry-run artifacts as live backend success.
- Report cluster counts, cluster leverage, singleton handling, and multiway cluster choices when relevant.
- Check exposure or offset variables for units, zeros, missing values, and pre-specification.
- For gravity designs, validate exporter, importer, product, dyad, and time fixed effects against the claimed estimand.
- For causal designs, hand off timing, parallel-trend, event-study, IV, or assignment assumptions to an appropriate causal-design skill.
- Write status.json, backend_status.json, diagnostics.json, reviewer_risk.json, artifact_manifest.json, and claim_gate.json when a run exists.

## Handoff from code artifacts

- Read claim_gate.json first for allowed claim levels.
- Read status.json for run status and failure modes.
- Read backend_status.json for live PPMLHDFE evidence.
- Read artifact_manifest.json or manifest.json for provenance.
- Read diagnostics.json for zeros, separation, convergence, support, exposure, fixed-effect, and cluster diagnostics.
- Read reviewer_risk.json for unresolved objections.
- Read model_table.csv for coefficients, standard errors, fixed effects, clusters, observations, and dropped observations.
- Read logs for separation messages, nonconvergence, unsupported fallbacks, dry runs, skipped backends, and missing dependencies.
- Downgrade if PPMLHDFE did not run live or if fallback output is presented as equivalent.
- Downgrade if zeros, separation, convergence, FE support, cluster choice, offset, or claim_gate diagnostics are missing.
- Downgrade causal claims if the artifacts show only conditional association.

## Minimal examples

### Example 1: good planning request

User: Should I use PPMLHDFE for green trade flows with many zeros?

Expected skill output:

```yaml
skill_name: ppmlhdfe_environmental_flows
user_question_summary: "Green trade flows with many zeros and high-dimensional fixed effects."
research_domain: environmental_flows
research_brief:
  unit: product_country_pair_year
  time_frequency: year
  outcome_candidates: [trade_flow]
  treatment_or_exposure: CBAM_exposure
  estimand_candidates: [conditional_mean_multiplicative_association, policy_effect_only_if_design_supported]
  identification_risks: [zeros_are_signal, treatment_absorbed_by_FE, separation_support_loss, cluster_dependence]
ppmlhdfe_environmental_flows_plan:
  outcome_type: trade_flow
  zeros_present: true
  fixed_effects_candidates: [exporter_year, importer_year, product_year, country_pair_or_product_pair]
  cluster_candidates: [country_pair, product, exporter_importer]
  separation_risk: unknown
  backend_required: ppmlhdfe
  fallback_allowed: false
  forbidden_claims: [do_not_use_OLS_log_flow_as_equivalent, do_not_delete_zeros_as_nuisance]
candidate_workflows: [ppmlhdfe_gravity_flow_plan, separation_and_convergence_gate, claim_gate_review]
candidate_methods: [PPMLHDFE_with_gravity_FE]
required_diagnostics: [nonnegative_outcome_check, zeros_check, FE_identification_check, separation_check, convergence_check, cluster_diagnostics, backend_live_run_check]
recommended_robustness: [FE_sensitivity, cluster_sensitivity, zero_definition_sensitivity, product_or_pair_support_check, exposure_timing_sensitivity]
forbidden_claims: [OLS_fallback_equivalence, causal_policy_effect_without_design, add_one_log_main_result]
claim_language:
  allowed: ["PPMLHDFE is the planned main estimator for the conditional mean of nonnegative green trade flows."]
  disallowed: ["A log-linear OLS model after adding one is equivalent to PPMLHDFE."]
uncertainty_notes: [Need backend status, separation diagnostics, and evidence that treatment variation survives fixed effects.]
next_code_actions: [draft_ppmlhdfe_spec, run_zero_FE_separation_convergence_diagnostics, write_claim_gate]
scholarly_depth:
  estimand_definition: "Conditional-mean multiplicative association for nonnegative trade flows, with causal interpretation only if identification artifacts support it."
  identification_assumptions: [valid_within_FE_comparison, treatment_not_absorbed, no_unaddressed_policy_endogeneity_for_causal_claims]
  measurement_model: [zeros_are_valid_flow_outcomes, trade_values_are_nonnegative, exposure_definition_pre_specified_if_used]
  data_construction_risks: [suppressed_trade_values, re_exports, deflation, product_code_changes, mirror_flow_discrepancies]
  method_decision_tree: [use_PPMLHDFE_main, check_FE_identification, check_separation, check_clusters, downgrade_if_backend_missing]
  diagnostics_that_block_claims: [missing_backend_live_run, nonconvergence, separation_drops_treatment_support, missing_cluster_rationale]
  robustness_ranked_by_risk: [FE_structure_sensitivity, cluster_sensitivity, zero_definition_sensitivity, sample_support_sensitivity]
  referee_objections: [zeros_deleted, overabsorbed_treatment, fragile_clusters, separation_changes_estimand]
  downgrade_triggers: [fallback_used_as_equivalent, add_one_log_main_result, missing_claim_gate, no_separation_log]
not_recommended_methods: [OLS_log_flow_fallback, log_one_plus_y_main_result, deleting_zeros, ignoring_separation, convenience_clusters]
```

### Example 2: downgrade or refusal for unsupported backend or fallback

User: PPMLHDFE is not available. I ran log(1 + emissions flow) OLS with fixed effects. Please describe it as equivalent and causal.

Expected skill output:

```yaml
skill_name: ppmlhdfe_environmental_flows
user_question_summary: "Request to call add-one-log OLS equivalent to PPMLHDFE and causal."
research_domain: environmental_flows
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: [emissions_flow]
  treatment_or_exposure: null
  estimand_candidates: [non_equivalent_exploratory_sensitivity_only]
  identification_risks: [missing_PPMLHDFE_backend, add_one_log_changes_estimand, causal_design_not_established, zeros_not_handled_by_PPML]
ppmlhdfe_environmental_flows_plan:
  outcome_type: emissions_flow
  zeros_present: unknown
  fixed_effects_candidates: []
  cluster_candidates: []
  separation_risk: unknown
  backend_required: ppmlhdfe
  fallback_allowed: false
  forbidden_claims: [do_not_call_log_OLS_equivalent, do_not_claim_causality_without_design, do_not_hide_missing_backend]
candidate_workflows: [artifact_reading_and_claim_gate_review, PPMLHDFE_backend_block, non_equivalent_sensitivity_label_only]
candidate_methods: [PPMLHDFE_required_not_completed]
required_diagnostics: [backend_live_run_check, nonnegative_outcome_check, zeros_check, separation_check, convergence_check, FE_identification_check]
recommended_robustness: [only_after_PPMLHDFE_main_run, label_log_OLS_as_non_equivalent_exploratory_sensitivity_if_reported]
forbidden_claims: [PPMLHDFE_equivalence, backend_certified_result, causal_policy_effect]
claim_language:
  allowed: ["The log(1 + y) fixed-effect regression can only be described as a non-equivalent exploratory sensitivity, not as a PPMLHDFE result."]
  disallowed: ["The OLS model is equivalent to PPMLHDFE and proves a causal effect."]
uncertainty_notes: [PPMLHDFE backend evidence is missing; fallback_allowed is false; causal design artifacts are not described.]
next_code_actions: [verify_or_install_backend_at_use_time, rerun_PPMLHDFE_if_available, write_claim_gate_with_blocked_strong_claims]
scholarly_depth:
  estimand_definition: "No PPMLHDFE estimand has been estimated; add-one-log OLS targets a different transformed conditional mean."
  identification_assumptions: [causal_assumptions_not_established, FE_structure_not_a_substitute_for_assignment]
  measurement_model: [emissions_flow_should_be_nonnegative, zeros_need_PPML_handling_or_explicit_measurement_interpretation]
  data_construction_risks: [add_one_constant_arbitrary, transformed_scale_interpretation, missing_zero_classification]
  method_decision_tree: [refuse_equivalence_claim, require_PPMLHDFE_backend, label_any_OLS_as_non_equivalent_sensitivity]
  diagnostics_that_block_claims: [missing_backend_live_run, missing_separation_diagnostics, missing_convergence_diagnostics, missing_claim_gate]
  robustness_ranked_by_risk: [PPMLHDFE_main_required_first, FE_support_check, cluster_rationale, zero_definition_check]
  referee_objections: [fallback_estimator_changes_estimand, zeros_handled_by_arbitrary_constant, causality_overclaimed]
  downgrade_triggers: [OLS_called_PPMLHDFE, backend_missing, causal_language_requested_without_design]
not_recommended_methods: [OLS_log_flow_equivalence, log_one_plus_y_main_result, ordinary_Poisson_as_unchecked_fallback, deleting_zeros, ignoring_backend_status]
```

## Completion checklist

- First line is exactly `# Skill: ppmlhdfe_environmental_flows`.
- All required second-level headings are present in the required order.
- Required repo artifacts say to inspect workspace files first.
- Shared rules `01` through `07` are listed, especially `../_shared/07_scholarly_depth_rules.md`.
- Output schema includes all common base fields, `ppmlhdfe_environmental_flows_plan`, `scholarly_depth`, and `not_recommended_methods`.
- Nonnegative outcome, zeros, high-dimensional fixed effects, clusters, separation, convergence, offset or exposure, and gravity-style design are covered.
- The estimand is conditional-mean or incidence-style multiplicative association unless a design supports effects.
- Fixed effects are treated as identification content, not just controls.
- Clusters follow treatment or exposure variation and dependence.
- Separation is treated as a support and estimand issue.
- PPMLHDFE live-run backend evidence is required for backend-certified claims.
- `fallback_allowed` is false, and OLS/log-linear/add-one-log fallbacks are forbidden as equivalents.
- Two examples are present: one good planning example and one downgrade/refusal example.
- claim_gate.json controls all strong claims.
- No package availability, backend completion, or current policy fact is asserted without an artifact or official/latest check.
`
