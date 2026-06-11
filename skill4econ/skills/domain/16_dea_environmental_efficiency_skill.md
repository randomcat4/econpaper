# Skill: dea_environmental_efficiency

## Purpose

Plan DEA, SBM, Malmquist, and window DEA research designs for environmental efficiency, green TFP, and energy efficiency studies.
This skill is a prompt and rubric layer for future agents; it is not an estimator, backend installer, validator, or artifact certifier.
Use it to separate three objects that are often conflated: efficiency score, productivity index, and causal outcome.
The main goal is to draft defensible estimands, measurement choices, diagnostics, downgrade triggers, and referee-facing claim language.
The default posture is conservative: DEA can construct indexes, but second-stage determinant and policy-effect claims need separate identification support.

## When to use

* The user asks about environmental efficiency, eco-efficiency, carbon efficiency, energy efficiency, green innovation efficiency, or green finance efficiency using DEA.
* The user mentions SBM, undesirable-output DEA, directional distance functions, Malmquist, Malmquist-Luenberger, green TFP, or window DEA.
* The user wants to rank firms, cities, provinces, plants, ports, banks, or industries by green efficiency.
* The user asks whether DEA scores can be used as outcomes in a second-stage determinant model.
* The user asks for a planning rubric before code, before specification drafting, or before interpreting existing DEA artifacts.
* The user needs claim language that will survive an environmental economics or econometrics referee.

## Do not use when

* Do not use when the user only needs to execute an already validated spec with no research-design question.
* Do not use to certify completed results without claim_gate.json, status.json, artifact provenance, diagnostics, and backend evidence.
* Do not use when the real request is a causal policy evaluation and no DEA measurement issue is central.
* Do not use to justify causal determinant language from a second-stage regression by default.
* Do not use to replace a missing DEA backend with unrelated OLS, Tobit, or panel regressions.
* Do not use to assert current policy, dataset, API, package, or regulatory facts unless official/latest sources are checked at use time.
* If the user asks for paper-ready causal language but artifacts are missing, downgrade rather than improvise.

## Inputs expected

* Research question, intended claim level, and target audience.
* DMU definition, such as firm, city, province, plant, industry, port, bank, fund, or region.
* Time structure, including cross-section, panel, balanced panel, unbalanced panel, or rolling window.
* Candidate inputs, such as capital, labor, energy, land, water, materials, investment, or installed capacity.
* Candidate desirable outputs, such as output, value added, GDP, revenue, patents, service volume, or treated waste.
* Candidate undesirable outputs, such as CO2, SO2, NOx, wastewater, particulates, solid waste, energy loss, or accidents.
* Intended orientation: input reduction, desirable-output expansion, undesirable-output contraction, directional, non-oriented, radial, or slack-based.
* Returns-to-scale rationale, or an admission that CRS and VRS sensitivity is required.
* Whether the user requests static efficiency, Malmquist-style productivity change, window analysis, or second-stage determinants.
* Data construction rules, variable units, transformations, missing values, zeros, negatives, and deflators.
* Existing artifacts when interpreting a run: specs, manifests, diagnostics, model tables, logs, and claim gates.

## Required repo artifacts to inspect

Inspect workspace files first. Do not rely on a locally installed copy of skill4econ or on memory of an older repository state.
Inspect these workspace paths before writing a repository-aware response:

* `README.md`
* `skill4econ/registry.yml`
* `skill4econ/cli.py`
* `skill4econ/core.py`
* `skill4econ/python_wrappers.py`
* `skill4econ/workflows.py`
* `skill4econ/diagnostics/`
* `skill4econ/tests/fixtures/`
* `skill4econ/tests/backends/`
* `status.json` when a run exists
* `claim_gate.json` when a run exists
* `manifest.json` or `artifact_manifest.json` when a run exists
* `diagnostics.json`, `reviewer_risk.json`, `backend_status.json`, and `model_table.csv` when present
* any DEA, SBM, Malmquist, frontier, green TFP, or environmental-efficiency spec files in the workspace
  Also read shared rules before writing output:
* `../_shared/00_skill_authoring_rules.md`
* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`
* `../_shared/08_domain_literature_anchor_rules.md`
  Rule `../_shared/07_scholarly_depth_rules.md` is required, not optional, because it forces estimands, assumptions, measurement model, diagnostics that block claims, referee objections, and downgrade triggers.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Charnes, Cooper, and Rhodes (1978), European Journal of Operational Research, Measuring the Efficiency of Decision Making Units"
    - "Banker, Charnes, and Cooper (1984), Management Science, Some Models for Estimating Technical and Scale Inefficiencies in Data Envelopment Analysis"
    - "Färe, Grosskopf, Lovell, and Pasurka (1989), Review of Economics and Statistics, Multilateral Productivity Comparisons When Some Outputs Are Undesirable"
    - "Färe, Grosskopf, Norris, and Zhang (1994), American Economic Review, Productivity Growth, Technical Progress, and Efficiency Change in Industrialized Countries"
    - "Simar and Wilson (1998), Management Science, Sensitivity Analysis of Efficiency Scores: How to Bootstrap in Nonparametric Frontier Models"
    - "Simar and Wilson (2007), Journal of Econometrics, Estimation and Inference in Two-Stage, Semi-Parametric Models of Production Processes"
    - "Zhou, Ang, and Poh (2008), European Journal of Operational Research, A Survey of Data Envelopment Analysis in Energy and Environmental Studies"
  canonical_data_sources:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  live_lookup_required_for:
    - "current DEA environmental-efficiency software and package implementations"
    - "current DEA package defaults and solver behavior"
    - "current software support for undesirable-output models"
    - "current implementation defaults"
    - "current package definitions and normalization"
    - "current DEA bootstrap implementation and package version"
    - "current econometric package and implementation details"
    - "current DEA/Malmquist package definitions"
    - "current package implementation of undesirable outputs"
    - "current solver and implementation defaults"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Charnes, Cooper, and Rhodes (1978), European Journal of Operational Research, Measuring the Efficiency of Decision Making Units"
    use_for: "CCR DEA model, constant returns to scale, radial efficiency frontier"
    live_lookup_required: []

    citation: "Banker, Charnes, and Cooper (1984), Management Science, Some Models for Estimating Technical and Scale Inefficiencies in Data Envelopment Analysis"
    use_for: "BCC DEA model, variable returns to scale, scale efficiency"
    live_lookup_required: []

    citation: "Färe, Grosskopf, Lovell, and Pasurka (1989), Review of Economics and Statistics, Multilateral Productivity Comparisons When Some Outputs Are Undesirable"
    use_for: "undesirable outputs, environmental efficiency, directional distance interpretation"
    live_lookup_required: []

    citation: "Färe, Grosskopf, Norris, and Zhang (1994), American Economic Review, Productivity Growth, Technical Progress, and Efficiency Change in Industrialized Countries"
    use_for: "Malmquist productivity index, efficiency change, frontier shift"
    live_lookup_required: []

    citation: "Simar and Wilson (1998), Management Science, Sensitivity Analysis of Efficiency Scores: How to Bootstrap in Nonparametric Frontier Models"
    use_for: "DEA score uncertainty and bootstrap inference"
    live_lookup_required: []

    citation: "Simar and Wilson (2007), Journal of Econometrics, Estimation and Inference in Two-Stage, Semi-Parametric Models of Production Processes"
    use_for: "second-stage DEA regression caveats, serial correlation from estimated scores, bootstrap procedures"
    live_lookup_required: []

    citation: "Zhou, Ang, and Poh (2008), European Journal of Operational Research, A Survey of Data Envelopment Analysis in Energy and Environmental Studies"
    use_for: "environmental DEA applications, undesirable outputs, energy efficiency measurement"
    live_lookup_required: ["current DEA environmental-efficiency software and package implementations"]
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "DEA efficiency score"
    - "constructed distance from an empirical frontier using selected inputs, desirable outputs, undesirable outputs, orientation, and returns-to-scale assumption"
    - "score is a constructed outcome, not a primitive causal variable"
    - "frontier depends on sample composition"
    - "outliers define the frontier"
    - "Undesirable outputs"
    - "pollution, CO2, SO2, NOx, wastewater, waste, accidents, or emissions intensity included via weak disposability, directional distance, by-production, or transformation methods"
    - "Returns to scale"
    - "constant returns to scale, variable returns to scale, non-increasing returns, non-decreasing returns, scale efficiency"
    - "Orientation and distance function"
  validation_targets:
    - "Model declaration"
    - "Are inputs, desirable outputs, undesirable outputs, orientation, distance function, and returns to scale declared before interpreting scores?"
    - "Undesirable outputs"
    - "Is pollution handled with an economically justified undesirable-output model rather than arbitrary sign changes?"
    - "Frontier robustness"
    - "Are CRS/VRS, orientation, direction vector, sample composition, and outlier influence stress-tested?"
    - "Generated-score inference"
    - "Are bootstrap or other valid methods used for uncertainty in DEA scores and second-stage regressions?"
    - "Second-stage causality"
    - "Does the second-stage design avoid naive OLS/Tobit causal claims and separate policy variation from frontier construction variables?"
  known_mismeasurement_channels:
    - "score is a constructed outcome, not a primitive causal variable"
    - "frontier depends on sample composition"
    - "outliers define the frontier"
    - "treating bad outputs as ordinary inputs changes economics"
    - "monotone transformations can alter interpretation"
    - "weak disposability assumption must be justified"
    - "CRS and VRS answer different questions"
    - "small samples under VRS can label many units efficient"
    - "scale effects can be mistaken for managerial efficiency"
    - "orientation embeds behavioral assumptions"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "DEA efficiency score"
    measure: "constructed distance from an empirical frontier using selected inputs, desirable outputs, undesirable outputs, orientation, and returns-to-scale assumption"
    pitfalls: ["score is a constructed outcome, not a primitive causal variable", "frontier depends on sample composition", "outliers define the frontier"]
    live_lookup_required: ["current DEA package defaults and solver behavior"]

    item: "Undesirable outputs"
    measure: "pollution, CO2, SO2, NOx, wastewater, waste, accidents, or emissions intensity included via weak disposability, directional distance, by-production, or transformation methods"
    pitfalls: ["treating bad outputs as ordinary inputs changes economics", "monotone transformations can alter interpretation", "weak disposability assumption must be justified"]
    live_lookup_required: ["current software support for undesirable-output models"]

    item: "Returns to scale"
    measure: "constant returns to scale, variable returns to scale, non-increasing returns, non-decreasing returns, scale efficiency"
    pitfalls: ["CRS and VRS answer different questions", "small samples under VRS can label many units efficient", "scale effects can be mistaken for managerial efficiency"]
    live_lookup_required: ["current implementation defaults"]

    item: "Orientation and distance function"
    measure: "input-oriented, output-oriented, non-oriented, slack-based, directional distance, Malmquist-Luenberger distance"
    pitfalls: ["orientation embeds behavioral assumptions", "radial scores ignore slacks", "direction vector choice affects environmental-efficiency rankings"]
    live_lookup_required: ["current package definitions and normalization"]

    item: "Bootstrapping"
    measure: "bias-corrected DEA scores, confidence intervals, bootstrap second-stage inference"
    pitfalls: ["naive standard errors are invalid for generated frontier scores", "serial dependence and panel structure require design-specific resampling", "bootstrap assumptions fail with severe outliers"]
    live_lookup_required: ["current DEA bootstrap implementation and package version"]

    item: "Second-stage regression"
    measure: "regression of DEA scores on policy, governance, technology, regulation, or market variables"
    pitfalls: ["DEA scores are serially correlated generated regressands", "bounded dependent variable fixes do not solve frontier dependence", "environmental variables may also enter frontier construction"]
    live_lookup_required: ["current econometric package and implementation details"]

    item: "Productivity index"
    measure: "Malmquist, Malmquist-Luenberger, efficiency change, technical change, catch-up, frontier shift"
    pitfalls: ["productivity index is not a treatment effect", "frontier movement can reflect sample changes", "index decomposition depends on base period and technology set"]
    live_lookup_required: ["current DEA/Malmquist package definitions"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "treating DEA score changes as causal efficiency improvements"
    - "getting rankings from arbitrary bad-output transformations"
    - "policy effects driven by frontier redefinition"
    - "naive Tobit/OLS second-stage inference presented as causal"
    - "calling productivity-index changes policy impacts"
    - "frontier defined by mismeasured or incomparable units"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Constructed outcome versus causal primitive"
    core_issue: "DEA efficiency is estimated relative performance under modelling assumptions, not directly observed environmental performance."
    acceptable_designs: ["state frontier model before causal design", "robustness to inputs/outputs/orientation/RTS", "separate raw emissions and output outcomes"]
    referee_risk: "treating DEA score changes as causal efficiency improvements"
    live_lookup_required: []

    item: "Undesirable-output modelling"
    core_issue: "Environmental efficiency depends on how pollution is represented and whether weak disposability or by-production is credible."
    acceptable_designs: ["compare weak-disposability and directional-distance models", "report raw emissions", "test alternative direction vectors and transformations"]
    referee_risk: "getting rankings from arbitrary bad-output transformations"
    live_lookup_required: ["current package implementation of undesirable outputs"]

    item: "Returns-to-scale and sample frontier"
    core_issue: "CRS, VRS, and sample choice define different frontiers and can change treatment rankings."
    acceptable_designs: ["CRS/VRS/NIRS robustness", "leave-one-out frontier checks", "outlier diagnostics", "balanced sample comparisons"]
    referee_risk: "policy effects driven by frontier redefinition"
    live_lookup_required: ["current solver and implementation defaults"]

    item: "Second-stage regression caveats"
    core_issue: "DEA scores are generated, bounded, serially dependent, and mechanically related to included frontier variables."
    acceptable_designs: ["Simar-Wilson bootstrap", "design-based treatment variation", "avoid reusing frontier variables as regressors", "cluster/panel resampling when justified"]
    referee_risk: "naive Tobit/OLS second-stage inference presented as causal"
    live_lookup_required: ["current econometric software implementation"]

    item: "Productivity index versus treatment effect"
    core_issue: "Malmquist or Malmquist-Luenberger indices decompose relative frontier movement; they are not causal treatment effects without identifying variation."
    acceptable_designs: ["combine index with event study or DID", "hold technology set fixed in robustness", "separate catch-up from frontier shift"]
    referee_risk: "calling productivity-index changes policy impacts"
    live_lookup_required: []

    item: "Measurement and outlier sensitivity"
    core_issue: "DEA is deterministic and highly sensitive to measurement error, omitted inputs, outliers, and inconsistent accounting of pollution."
    acceptable_designs: ["winsorization rules", "jackknife/frontier influence diagnostics", "stochastic frontier comparison", "raw-data audit"]
    referee_risk: "frontier defined by mismeasured or incomparable units"
    live_lookup_required: ["current data vintages and package diagnostics"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Model declaration"
    - "Are inputs, desirable outputs, undesirable outputs, orientation, distance function, and returns to scale declared before interpreting scores?"
    - "Undesirable outputs"
    - "Is pollution handled with an economically justified undesirable-output model rather than arbitrary sign changes?"
    - "Frontier robustness"
    - "Are CRS/VRS, orientation, direction vector, sample composition, and outlier influence stress-tested?"
    - "Generated-score inference"
    - "Are bootstrap or other valid methods used for uncertainty in DEA scores and second-stage regressions?"
    - "Second-stage causality"
    - "Does the second-stage design avoid naive OLS/Tobit causal claims and separate policy variation from frontier construction variables?"
  minimal_empirical_section_checklist:
    - "Model declaration"
    - "Are inputs, desirable outputs, undesirable outputs, orientation, distance function, and returns to scale declared before interpreting scores?"
    - "current DEA software defaults"
    - "Undesirable outputs"
    - "Is pollution handled with an economically justified undesirable-output model rather than arbitrary sign changes?"
    - "current implementation support"
    - "Frontier robustness"
    - "Are CRS/VRS, orientation, direction vector, sample composition, and outlier influence stress-tested?"
    - "current solver and package behavior"
    - "Generated-score inference"
  claims_to_downgrade:
    - "Do not treat a DEA score as an observed causal primitive."
    - "Do not claim policy treatment effects from DEA score differences without a credible causal design."
    - "Do not model undesirable outputs by arbitrary sign reversal without explaining the production technology."
    - "Do not use CRS, VRS, orientation, or direction vectors without robustness and economic justification."
    - "Do not run naive second-stage OLS/Tobit on DEA scores and present the coefficients as causal."
    - "Do not interpret Malmquist or Malmquist-Luenberger productivity changes as treatment effects without identifying variation."
    - "Do not make current claims about DEA package defaults, bootstrap implementations, undesirable-output support, or solver behavior without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Model declaration"
    ask: "Are inputs, desirable outputs, undesirable outputs, orientation, distance function, and returns to scale declared before interpreting scores?"
    live_lookup_required: ["current DEA software defaults"]

    check: "Undesirable outputs"
    ask: "Is pollution handled with an economically justified undesirable-output model rather than arbitrary sign changes?"
    live_lookup_required: ["current implementation support"]

    check: "Frontier robustness"
    ask: "Are CRS/VRS, orientation, direction vector, sample composition, and outlier influence stress-tested?"
    live_lookup_required: ["current solver and package behavior"]

    check: "Generated-score inference"
    ask: "Are bootstrap or other valid methods used for uncertainty in DEA scores and second-stage regressions?"
    live_lookup_required: ["current bootstrap implementation"]

    check: "Second-stage causality"
    ask: "Does the second-stage design avoid naive OLS/Tobit causal claims and separate policy variation from frontier construction variables?"
    live_lookup_required: []

    check: "Productivity indices"
    ask: "Are Malmquist or Malmquist-Luenberger decompositions described as relative frontier movements unless paired with causal identification?"
    live_lookup_required: ["current package definitions"]

    check: "Raw outcomes"
    ask: "Are raw emissions, inputs, outputs, and intensity outcomes shown alongside constructed efficiency scores?"
    live_lookup_required: ["current underlying data vintage"]
```

## Forbidden claims

- Do not treat a DEA score as an observed causal primitive.
- Do not claim policy treatment effects from DEA score differences without a credible causal design.
- Do not model undesirable outputs by arbitrary sign reversal without explaining the production technology.
- Do not use CRS, VRS, orientation, or direction vectors without robustness and economic justification.
- Do not run naive second-stage OLS/Tobit on DEA scores and present the coefficients as causal.
- Do not interpret Malmquist or Malmquist-Luenberger productivity changes as treatment effects without identifying variation.
- Do not make current claims about DEA package defaults, bootstrap implementations, undesirable-output support, or solver behavior without live lookup.

## Domain reasoning steps

* Define the target object first: static relative efficiency, dynamic productivity change, decomposition component, ranking, or second-stage association.
* State the estimand as sample-relative unless a broader population and support argument are supplied.
* Do not call an efficiency score a causal outcome effect; do not call a Malmquist index a treatment effect by itself.
* Identify the DMU population and the production technology assumed comparable across those DMUs.
* Check whether firms, public regions, regulated utilities, banks, and industries are being mixed in a way that breaks comparability.
* Check whether the frontier support is credible given the number of DMUs, inputs, desirable outputs, and undesirable outputs.
* Flag small samples with many variables, extreme DMUs, singletons, boundary changes, mergers, and influential frontier observations.
* Treat frontier membership as sample-relative best practice, not proof of absolute global efficiency.
* Define inputs as resources consumed, not policy labels unless a production interpretation is explicit.
* Define desirable outputs as valued production or service output.
* Define undesirable outputs as harms whose direction must be explicit and checked.
* Block green-efficiency claims if higher pollution can mechanically improve the score by coding accident.
* If bad outputs are transformed, state the transformation and require sensitivity to alternatives.
* If emissions intensity replaces emissions levels, state the denominator risk and implied production model.
* If green patents are outputs, say whether they represent innovation output, policy response, or both.
* Choose orientation according to the economic question: reduce inputs, expand good outputs, contract bad outputs, or treat all slacks jointly.
* Distinguish radial contraction or expansion from non-radial slack treatment.
* For SBM, explain that slacks are measurement components of inefficiency, not causal mechanisms.
* Require a rule for zero, negative, missing, and winsorized values before accepting scores.
* Choose CRS only with a defensible constant-returns and optimal-scale argument.
* Choose VRS when size heterogeneity, institutional constraints, or scale inefficiency is central.
* If scale theory is not settled, require CRS and VRS sensitivity before ranking or scale claims.
* Interpret CRS/VRS differences as frontier-model sensitivity, not causal scale effects.
* For static DEA, state the period-specific or pooled frontier and avoid time-trend language.
* For window DEA, require stable sample composition, window length rationale, and identical variable definitions across windows.
* For Malmquist or green TFP, require consecutive-period coverage and state whether the estimand is productivity change, catch-up, or frontier shift.
* Treat Malmquist decomposition as descriptive unless a separate design and claim_gate.json allow stronger language.
* Do not equate DEA-based green TFP with a structural production-function TFP parameter.
* Treat bootstrap as uncertainty support only; it does not solve omitted variables, simultaneity, bad measurement, or policy endogeneity.
* If bootstrap is requested, specify the resampling unit, panel structure, dependence assumptions, repetitions, and recorded seed policy.
* Do not describe bootstrap intervals as identification proof.
* For second-stage requests, set `second_stage_allowed_claim` to `none_by_default`.
* A regression of DEA scores on covariates is exploratory association unless a separate design supports causal interpretation.
* Do not fall back to unsupported OLS, Tobit, fractional, or panel regressions as if they solve generated-score and bounded-score problems.
* Check whether second-stage covariates duplicate or mechanically proxy DEA inputs or outputs.
* Check whether determinants are measured before the score and before any treatment response when causal language is requested.
* If the user has a policy treatment, route the causal question to a DID, event-study, IV, RDD, synthetic-control, or other causal-design skill.
* Even with a causal design, state that the DEA score is a constructed outcome requiring measurement and frontier sensitivity diagnostics.
* Block claims when DMU definition, input list, desirable-output list, undesirable-output direction, or returns-to-scale rationale is missing.
* Block rankings when frontier support, influential-DMU diagnostics, and CRS/VRS sensitivity are missing.
* Block green TFP claims when dynamic index requirements, panel coverage, or Malmquist decomposition details are missing.
* Block window trend claims when window comparability and sample-stability checks are missing.
* Block causal determinant claims when identification artifacts and claim_gate.json do not allow them.
* Anticipate referee objections about frontier support, too many variables, mixed technology sets, bad-output coding, CRS/VRS sensitivity, constructed outcomes, endogenous second-stage covariates, and bootstrap overinterpretation.
* Downgrade any result that is parser-only, interface-only, dry-run-only, missing-dependency, unsupported-backend, or not allowed by claim_gate.json.

## Candidate outputs

* `dea_environmental_efficiency_plan` YAML block.
* Research brief with unit, frequency, candidate outcomes, treatment or exposure, estimand candidates, and identification risks.
* Candidate workflows for static DEA, SBM, Malmquist, window DEA, and exploratory second-stage analysis.
* Candidate methods with explicit claim limits.
* Required diagnostics that must pass before descriptive, dynamic, ranking, or causal language is upgraded.
* Robustness checks ranked by measurement and identification risk.
* Referee objections, downgrade triggers, and forbidden claim language.
* Handoff instructions for code and for reading completed artifacts.

## Output schema

Return YAML or JSON. Do not omit the base fields. Use null or empty arrays when unknown; do not invent missing values.

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
dea_environmental_efficiency_plan:
  dmu_definition: null
  input_variables: []
  desirable_outputs: []
  undesirable_outputs: []
  returns_to_scale: CRS | VRS | unknown
  dynamic_index_needed: true | false | unknown
  second_stage_requested: true | false | unknown
  second_stage_allowed_claim: none_by_default
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

* DEA, SBM, Malmquist, and window DEA create sample-relative efficiency or productivity measures; they do not create causal evidence by default.
* Efficiency scores, productivity indexes, and causal outcomes are different objects and must be named separately.
* Undesirable outputs require explicit direction and transformation rules.
* CRS and VRS choices can change rankings and interpretations.
* Frontier support, variable count, and influential DMUs can determine results.
* Malmquist and green TFP decompositions are descriptive unless separate identification artifacts support stronger language.
* Window DEA needs stable sample and variable definitions across windows.
* Bootstrap supports uncertainty quantification only when artifacts support it; bootstrap is not identification.
* Second-stage analysis is exploratory association unless separate design artifacts and claim_gate.json allow stronger claims.
* A skill drafts reasoning and language; it does not validate specs, run backends, install packages, or certify artifacts.
* Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
* If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
* For volatile policy, regulation, standard, API, package, and data-source facts, check official/latest sources at use time.

## Forbidden claims

* Do not bypass claim_gate.json.
* Do not turn diagnostic success into paper-ready causal success.
* Do not turn parser-only, interface-only, missing-dependency, dry-run, or skipped-backend output into a live backend result.
* Do not present unsupported fallback estimators as equivalent substitutes.
* Do not claim DEA environmental efficiency has a causal effect by default.
* Do not treat DEA second-stage determinants as causal determinants by default.
* Do not use unsupported OLS, Tobit, fractional response, or panel regression as a default second stage and call it valid.
* Do not ignore undesirable-output direction.
* Do not call a score green efficiency when pollution was coded as desirable output by accident.
* Do not call a DEA-based green TFP index a structural productivity parameter.
* Do not claim Malmquist catch-up or frontier shift is caused by policy without an identification design.
* Do not rank DMUs as globally efficient when the frontier is sample-relative.
* Do not ignore CRS/VRS sensitivity when scale assumptions are unclear.
* Do not ignore measurement, timing, support, generated-score, and backend caveats.
* Do not certify code execution, backend availability, package behavior, or current data facts without artifacts or official/latest checks.

## Handoff to code

* Draft a spec with DMU, time, inputs, desirable outputs, undesirable outputs, orientation, returns to scale, and dynamic-index choice.
* Validate undesirable-output direction and variable transformations.
* Validate compatible units, missing-value rules, zero and negative handling, deflators, and sample boundaries.
* Check DMU comparability and the number of DMUs relative to the number of inputs and outputs.
* Check extreme observations, singletons, frontier influence, and support.
* Run CRS and VRS versions when theory does not settle the choice.
* Run radial and slack-aware variants when environmental slacks matter.
* For Malmquist or green TFP, validate consecutive-period coverage and decomposition reporting.
* For window DEA, validate window length, sample stability, and variable definitions across windows.
* For bootstrap, record resampling unit, panel structure, dependence assumptions, repetitions, and seed policy.
* For second stage, label default output exploratory and require separate identification artifacts for causal claims.
* Write status.json, backend_status.json, diagnostics.json, reviewer_risk.json, artifact_manifest.json, and claim_gate.json when a run exists.

## Handoff from code artifacts

* Read claim_gate.json first for allowed claim levels.
* Read status.json for run status and failure modes.
* Read backend_status.json for live backend evidence.
* Read artifact_manifest.json or manifest.json for provenance.
* Read diagnostics.json for variable, support, frontier, direction, and robustness checks.
* Read reviewer_risk.json for unresolved objections.
* Read model_table.csv for scores, indexes, decompositions, or second-stage estimates.
* Read logs for unsupported fallbacks, dry runs, skipped backends, and missing dependencies.
* Downgrade if claim_gate.json is absent or does not allow the claim.
* Downgrade if undesirable-output direction, CRS/VRS sensitivity, frontier support, dynamic comparability, or second-stage identification diagnostics are missing.
* Downgrade if any unsupported fallback is presented as equivalent.

## Minimal examples

### Example 1: good planning request

User: Can I use DEA efficiency as green TFP and regress determinants?

Expected skill output:

```yaml
skill_name: dea_environmental_efficiency
user_question_summary: "DEA environmental efficiency, green TFP, and possible second-stage determinants."
research_domain: environmental_efficiency
research_brief:
  unit: null
  time_frequency: year
  outcome_candidates: [efficiency_score, green_TFP_index]
  treatment_or_exposure: null
  estimand_candidates: [sample_relative_efficiency_score, Malmquist_productivity_change, exploratory_second_stage_association]
  identification_risks: [score_is_constructed_outcome, second_stage_endogeneity, generated_score_uncertainty]
dea_environmental_efficiency_plan:
  dmu_definition: city_or_firm_to_be_confirmed
  input_variables: [capital, labor, energy]
  desirable_outputs: [GDP_or_output]
  undesirable_outputs: [CO2, SO2]
  returns_to_scale: unknown
  dynamic_index_needed: true
  second_stage_requested: true
  second_stage_allowed_claim: none_by_default
  forbidden_claims: [do_not_treat_second_stage_as_causal, do_not_call_index_structural_TFP]
candidate_workflows: [static_environmental_DEA_plan, SBM_sensitivity_plan, Malmquist_or_window_plan, exploratory_second_stage_if_labeled]
candidate_methods: [DEA_CRS_VRS, undesirable_output_SBM, Malmquist_index, window_DEA_if_panel_supports_it]
required_diagnostics: [DMU_comparability_check, undesirable_output_direction_check, frontier_support_check, CRS_VRS_sensitivity, dynamic_panel_coverage_check, second_stage_design_gate]
recommended_robustness: [alternative_input_output_sets, CRS_vs_VRS, radial_vs_SBM, influential_DMU_exclusion, alternative_emissions_transformations]
forbidden_claims: [causal_determinants_from_default_second_stage, global_efficiency_ranking, policy_effect_from_Malmquist_decomposition]
claim_language:
  allowed: ["A DEA-based green efficiency or productivity index can be planned as a descriptive constructed measure."]
  disallowed: ["The determinants causally improve green TFP."]
uncertainty_notes: [Need confirmed DMU, variable definitions, panel balance, and claim_gate.json before strong claims.]
next_code_actions: [draft_DEA_SBM_Malmquist_spec, run_direction_and_support_diagnostics, prepare_claim_gate]
scholarly_depth:
  estimand_definition: "Sample-relative environmental efficiency and, if dynamic, DEA-based productivity change rather than a causal treatment effect."
  identification_assumptions: [comparable_DMU_technology_set, stable_measurement, no_as_if_random_policy_variation_established]
  measurement_model: [inputs_are_resources, desirable_outputs_are_good_outputs, undesirable_outputs_are_bads_with_explicit_direction]
  data_construction_risks: [emissions_transformations, missing_or_zero_values, boundary_changes, variable_count_relative_to_DMUs]
  method_decision_tree: [start_static_DEA, add_SBM_for_slacks, add_Malmquist_only_for_panel_productivity, keep_second_stage_exploratory]
  diagnostics_that_block_claims: [missing_direction_check, weak_frontier_support, missing_CRS_VRS_sensitivity, missing_second_stage_design]
  robustness_ranked_by_risk: [variable_set_sensitivity, CRS_VRS_sensitivity, influential_DMU_check, window_length_sensitivity]
  referee_objections: [constructed_score_used_as_outcome, endogenous_second_stage_covariates, frontier_driven_by_outliers]
  downgrade_triggers: [no_claim_gate, unsupported_backend, second_stage_called_causal, Malmquist_called_policy_effect]
not_recommended_methods: [default_OLS_second_stage_as_causal, default_Tobit_second_stage_as_causal, ignoring_undesirable_outputs, log_transforming_bad_outputs_without_direction_rule]
```

### Example 2: downgrade or refusal for unsupported claim

User: The DEA run produced city green efficiency scores. Please say digital finance caused the improvement because the Tobit second stage is significant.

Expected skill output:

```yaml
skill_name: dea_environmental_efficiency
user_question_summary: "Request to turn DEA scores and a significant Tobit second stage into a causal claim."
research_domain: environmental_efficiency
research_brief:
  unit: city
  time_frequency: null
  outcome_candidates: [DEA_green_efficiency_score]
  treatment_or_exposure: digital_finance
  estimand_candidates: [exploratory_association_only]
  identification_risks: [second_stage_endogeneity, generated_score_uncertainty, post_treatment_controls, unsupported_causal_language]
dea_environmental_efficiency_plan:
  dmu_definition: city
  input_variables: []
  desirable_outputs: []
  undesirable_outputs: []
  returns_to_scale: unknown
  dynamic_index_needed: unknown
  second_stage_requested: true
  second_stage_allowed_claim: none_by_default
  forbidden_claims: [do_not_claim_digital_finance_caused_efficiency, do_not_treat_Tobit_as_identification]
candidate_workflows: [artifact_reading_and_claim_gate_review, exploratory_second_stage_downgrade]
candidate_methods: [DEA_score_interpretation_with_caveats]
required_diagnostics: [claim_gate_check, undesirable_output_direction_check, CRS_VRS_sensitivity, frontier_support_check, second_stage_identification_artifact_check]
recommended_robustness: [alternative_score_construction, variable_set_sensitivity, influential_DMU_check, lagged_exposure_sensitivity_if_design_exists]
forbidden_claims: [causal_determinant_claim, paper_ready_policy_effect, backend_certified_result_without_artifacts]
claim_language:
  allowed: ["The second-stage result may be described only as an exploratory association with the constructed DEA score."]
  disallowed: ["Digital finance caused the improvement in city green efficiency."]
uncertainty_notes: [No causal design or claim_gate.json is described; causal language is blocked.]
next_code_actions: [inspect_claim_gate_and_artifacts, verify_backend_status, check_second_stage_design_or_downgrade]
scholarly_depth:
  estimand_definition: "At most an exploratory association between a constructed DEA score and digital finance."
  identification_assumptions: [no_causal_identification_established, timing_and_exogeneity_not_verified]
  measurement_model: [DEA_score_depends_on_inputs_outputs_bads_and_frontier_sample]
  data_construction_risks: [score_generated_from_same_economic_system, possible_covariate_overlap_with_inputs_outputs]
  method_decision_tree: [refuse_causal_language, report_association_only, require_separate_design_for_causality]
  diagnostics_that_block_claims: [missing_claim_gate, missing_identification_design, missing_generated_score_uncertainty, missing_frontier_sensitivity]
  robustness_ranked_by_risk: [DEA_variable_set_sensitivity, CRS_VRS_sensitivity, alternative_second_stage_timing, placebo_or_event_design_only_if_supported]
  referee_objections: [Tobit_significance_not_identification, constructed_dependent_variable, omitted_policy_confounders]
  downgrade_triggers: [significance_used_as_causality, unsupported_Tobit_fallback, missing_backend_artifact]
not_recommended_methods: [claiming_causality_from_Tobit, unsupported_OLS_second_stage, ignoring_score_uncertainty, hiding_failed_backend]
```

## Completion checklist

* First line is exactly `# Skill: dea_environmental_efficiency`.
* All required second-level headings are present in the required order.
* Required repo artifacts say to inspect workspace files first.
* Shared rules `01` through `07` are listed, especially `../_shared/07_scholarly_depth_rules.md`.
* Output schema includes all common base fields, `dea_environmental_efficiency_plan`, `scholarly_depth`, and `not_recommended_methods`.
* The skill distinguishes efficiency score, productivity index, and causal outcome.
* DMU comparability, frontier support, input/output/bad-output measurement, bad-output direction, radial versus slack treatment, CRS/VRS sensitivity, Malmquist, and window analysis are covered.
* Bootstrap is uncertainty support, not identification.
* Second-stage analysis is exploratory by default, and unsupported OLS/Tobit fallbacks are forbidden.
* Two examples are present: one good planning example and one downgrade/refusal example.
* claim_gate.json controls all strong claims.
* No package availability, backend completion, or current policy fact is asserted without an artifact or official/latest check.

`
