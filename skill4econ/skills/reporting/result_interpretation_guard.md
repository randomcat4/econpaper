# Skill: result_interpretation_guard
## Purpose
Turn skill4econ model tables, diagnostics, robustness artifacts, and backend statuses into cautious result interpretation for econometric research.
This skill is for environmental economics, policy evaluation, ESG, climate, pollution, energy, and applied micro reporting.
It separates numerical patterns from design validity, robustness, measurement validity, sample construction, and claim readiness.
It is a reporting and reviewer-risk skill, not an estimator, spec validator, backend runner, power calculator, or artifact certifier.
The skill must not let statistical significance substitute for identification, artifact completeness, backend execution, or measurement credibility.
The skill must not let statistical insignificance become a claim of no effect without power, confidence interval, effect-size, and sample-support evidence.
The main output is a safe interpretation that a strict econometric referee could recognize as appropriately bounded.

## Shared reporting contract

Shared reporting boilerplate lives in `./_reporting_shared_contract.md`; apply it before this file-specific logic and do not duplicate or weaken its artifact, claim-gate, parser-only, missing-dependency, forbidden-claims, or scholarly-depth rules.

## When to use
- Use when the user provides `model_table.csv` and asks what the results mean.
- Use when diagnostics, robustness tables, backend status, or reviewer-risk artifacts qualify the numerical estimates.
- Use when a coefficient is statistically significant but overlap, balance, pre-trends, placebo, measurement, W sensitivity, or backend status fails.
- Use when a coefficient is not statistically significant but power, sample size, missing backend, wide intervals, or noisy measurement may prevent a strong null conclusion.
- Use when point estimates change sign across W matrices, samples, outcomes, estimators, specifications, or time windows.
- Use when robustness results conflict with the preferred model.
- Use when backend artifacts are partial, parser-only, missing, or unavailable.
- Use when environmental or ESG outcomes rely on proxies, text measures, remote sensing, self-reports, monitors, firm disclosures, or administrative thresholds.
- Use when sample selection, reporting selection, monitor siting, treatment adoption, attrition, or disclosure participation may shape the table.
- Use when the user wants manuscript prose, table notes, figure notes, slide summaries, referee responses, or cautious abstract language.
## Do not use when
- Do not use to estimate a model, run a backend, validate a spec, install a dependency, or repair an artifact.
- Do not use to produce a p-value-only conclusion.
- Do not interpret a significant coefficient as causal when `claim_gate.json` blocks causal claims.
- Do not interpret an insignificant coefficient as evidence of no effect when confidence intervals are wide, power is weak, sample size is small, or measurement is noisy.
- Do not ignore sign flips across W matrices, specifications, samples, outcomes, estimators, or time windows.
- Do not hide robustness conflicts behind generic language such as `robust overall`.
- Do not claim the target backend ran if artifacts report parser-only, interface-only, missing dependency, failure, or partial availability.
- Do not report structural spatial direct, indirect, or total effects from reduced-form spatial exposure regressions.
- Do not write legal, fraud, intent, or regulatory-violation interpretations from ESG text metrics unless explicit legal authority is present and current official sources are checked at use time.
- Do not use model-table stars as the ordering principle for the result narrative.
## Inputs expected
- User question and intended audience for the interpretation.
- `model_table.csv` with estimates, standard errors, confidence intervals, p-values, units, denominators, sample sizes, model labels, backend labels, and specification labels.
- `diagnostics.json` with overlap, balance, pre-trend, placebo, support, leverage, W-matrix, measurement, and sample-selection diagnostics when available.
- `status.json` with agent status, workflow status, diagnostic-only flags, parser-only flags, warnings, errors, and partial-completion markers.
- `claim_gate.json` with allowed, downgraded, blocked, or forbidden claim levels.
- `manifest.json` and `artifact_manifest.json` when present, with provenance, timestamps, artifact completeness, and workflow links.
- `reviewer_risk.json` with objections, limitations, risk severity, and downgrade triggers.
- Robustness tables, W-sensitivity tables, placebo tables, event-study tables, balance tables, power notes, or supplementary outputs when present.
- `backend_discovery.json` or equivalent and `backend_status.json` when backend status matters.
- Data documentation for units, denominators, outcome construction, treatment coding, exposure windows, and sample restrictions when available.
- Any draft sentence that the user wants rewritten into cautious research prose.
## Required repo artifacts to inspect
Inspect repo capability before interpreting results:
- `README.md`
- `skill4econ/registry.yml`
- `skill4econ/cli.py`
- `skill4econ/core.py`
- `skill4econ/python_wrappers.py`
- `skill4econ/workflows.py`
- `skill4econ/diagnostics/`
- `skill4econ/tests/fixtures/`
- `skill4econ/tests/backends/`
Inspect shared reporting rules before output:
- `../_shared/00_skill_authoring_rules.md`
- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
Inspect run artifacts before writing interpretation:
- `status.json`
- `claim_gate.json`
- `manifest.json`
- `artifact_manifest.json` when present
- `diagnostics.json`
- `model_table.csv`
- `reviewer_risk.json`
- Robustness, event-study, placebo, balance, power, and W-sensitivity outputs when present
- `backend_discovery.json` or equivalent backend discovery artifact when present
- `backend_status.json` when present
If an artifact required for the user's intended interpretation is absent, name the absence in the interpretation and in `next_code_actions`.
## Domain reasoning steps
- Start by summarizing the research question, unit, frequency, outcome, treatment or exposure, sample, and candidate estimand.
- Identify whether the user wants descriptive, associational, diagnostic, causal, structural, policy-ready, legal, or backend-certified interpretation.
- Read `claim_gate.json` before using causal or strong language.
- Read `status.json` before assuming the run completed or the output is more than diagnostic.
- Read `manifest.json` and `artifact_manifest.json` before trusting artifact provenance.
- Read backend artifacts before naming a backend as executed.
- Read diagnostics before model-table stars.
- Read `model_table.csv` for sign, magnitude, confidence intervals, effect size, units, denominators, sample size, model labels, and specification labels.
- Translate coefficients into meaningful units only when the denominator, transformation, and outcome scale are documented.
- Report sign and magnitude together; do not report direction without scale.
- Report confidence intervals or uncertainty ranges when available; do not reduce uncertainty to stars.
- Compare effect size to baseline mean, policy-relevant threshold, or plausible measurement error only when those denominators are available.
- Treat p-values as one part of numerical uncertainty, not as claim authorization.
- For significant results, check overlap, balance, pre-trends, placebo, support, sample selection, measurement, and backend status before interpretation.
- For significant but design-failed results, state that precision does not rescue identification.
- For insignificant results, inspect confidence intervals, sample size, power notes, minimum detectable effects, measurement noise, and missing backends before saying `no effect`.
- For wide confidence intervals, say the estimate is imprecise and compatible with economically meaningful effects if the interval permits them.
- For sign flips across W matrices, specifications, samples, time windows, or outcomes, downgrade direction claims and describe instability.
- For robustness conflicts, identify which specification fails and whether it is a core identification check or a secondary sensitivity check.
- For backend partial or missing status, interpret only outputs that artifacts show actually ran.
- For parser-only status, do not say the model ran; say the parser or interface was exercised if supported by artifacts.
- For missing dependency status, do not say the backend passed; request backend completion before backend-certified interpretation.
- For reduced-form spatial models, interpret coefficients as conditional associations with spatial exposure unless structural spatial claims are explicitly allowed.
- For W sensitivity, discuss distance bands, contiguity definitions, row normalization, islands, zero-neighbor units, and sign or magnitude instability when artifacts include them.
- For measurement error, identify whether attenuation, misclassification, proxy validity, monitor coverage, remote-sensing error, text-score validity, or carbon-accounting uncertainty may affect interpretation.
- For sample selection, identify whether reporting units, treated units, monitors, facilities, firms, municipalities, or matched samples differ from the target population.
- For event studies, inspect pre-trends and dynamic timing before saying effects emerge after treatment.
- For DID, synthetic control, matching, IV, RD, PPML, spatial, panel, or text-score workflows, use design-specific diagnostics and do not generalize from another method's checks.
- For ESG or legal-sensitive text, interpret elevated scores as disclosure risk, inconsistency, or greenwashing risk unless legal authority supports stronger claims.
- For volatile policy, regulation, ESG standard, carbon accounting, API, and official data-source facts, require latest official-source checks at use time.
- Rank limitations by whether they block the main claim, downgrade the claim, or merely qualify presentation.
- Produce a safe interpretation paragraph that combines numerical pattern, design validity, and robustness status.
- Produce unsafe interpretations to avoid as direct sentence-level examples.
- Produce next steps before paper use that are code-actionable and artifact-specific.
## Candidate outputs
- A YAML or JSON result interpretation report with base fields, scholarly-depth fields, and `result_interpretation`.
- A numerical summary with sign, magnitude, units, confidence intervals, denominator, and sample context.
- A design-validity summary covering overlap, balance, pre-trends, support, placebo, measurement, sample selection, and backend status.
- A robustness summary covering alternative specifications, W matrices, samples, time windows, outcomes, estimators, and placebo checks.
- A safe interpretation paragraph that does not exceed the claim gate.
- A list of unsafe interpretations to avoid.
- A list of next steps before paper, abstract, policy memo, or audit use.
- A list of not-recommended methods or interpretations given the artifacts.
- A scholarly-depth block with estimand, assumptions, measurement model, data risks, decision tree, blocking diagnostics, robustness ranking, referee objections, and downgrade triggers.
## Output schema
Return YAML or JSON. Do not omit base fields. Include the exact `result_interpretation` block.
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
  identifying_assumptions: []
  measurement_model: []
  data_construction_risks: []
  method_decision_tree: []
  diagnostics_that_block_claims: []
  robustness_ranked_by_risk: []
  referee_objections: []
  downgrade_triggers: []
not_recommended_methods: []
result_interpretation:
  numerical_result_summary: string
  design_validity_summary: string
  robustness_summary: string
  safe_interpretation: string
  unsafe_interpretations_to_avoid: []
  next_steps_before_paper: []
```
Use `numerical_result_summary` for what the table says, not what the study proves.
Use `design_validity_summary` for whether the design supports the intended estimand.
Use `robustness_summary` for stability across specifications, W matrices, samples, outcomes, time windows, and backends.
Use `safe_interpretation` for manuscript-ready cautious prose within the claim gate.
Use `unsafe_interpretations_to_avoid` for direct claims the user should not make.
Use `next_steps_before_paper` for artifact-producing work, not vague advice.
## Required caveats
- Do not write p-value-only conclusions.
- A statistically significant estimate is not a valid causal interpretation when design diagnostics fail.
- A non-significant estimate is not evidence of no effect unless the design is credible and power or confidence intervals rule out meaningful effects.
- Confidence intervals, effect sizes, denominators, and units matter for interpretation.
- If the outcome is logged, standardized, winsorized, indexed, rate-based, count-based, or denominator-normalized, state the transformation before interpreting magnitude.
- If the treatment is continuous, exposure-based, binned, staggered, spatially weighted, or text-scored, state the contrast being interpreted.
- If pre-trends fail or are missing for an event-study or DID interpretation, block clean dynamic causal language.
- If overlap or balance fails, downgrade main causal interpretation even when the coefficient is significant.
- If W sensitivity shows sign or magnitude instability, block stable spatial direction claims.
- If robustness conflicts involve core identifying assumptions, downgrade the main result, not merely the appendix.
- If backend status is partial, missing, parser-only, interface-only, failed, or `missing_dependency`, state which outputs are uncertified or unavailable.
- If measurement error is flagged, avoid strong magnitude, compliance, welfare, or mechanism claims that require precise measurement.
- If sample selection is flagged, avoid population-wide or external-validity claims unless the target population is restricted accordingly.
- If claim gate blocks a claim, interpretation must stay at the allowed claim level even if estimates look favorable.
- If legal, regulatory, ESG standard, carbon accounting, policy, API, or data-source facts are current-sensitive, check official latest sources at use time rather than hard-coding them.
- If artifacts conflict, use the stricter interpretation and disclose the conflict.
## Forbidden claims
- Do not conclude from p-values alone.
- Do not say `the policy worked` from a significant coefficient when overlap, balance, pre-trend, placebo, backend, or claim-gate diagnostics block causal language.
- Do not say `there is no effect` from a non-significant coefficient with wide intervals, weak power, small sample, noisy measurement, or missing backend evidence.
- Do not say `the sign is robust` when any core W matrix, specification, sample, or estimator flips the sign.
- Do not say `the result is robust` when robustness conflict concerns a core identifying assumption.
- Do not say `the backend estimate confirms the result` when backend artifacts are partial, parser-only, missing, failed, or `missing_dependency`.
- Do not say `structural spillovers`, `indirect effects`, or `total effects` for reduced-form spatial exposure results.
- Do not say `emissions fell by X percent` unless the outcome scale, transformation, denominator, and coefficient interpretation support that statement.
- Do not say `pollution exposure improved for residents` unless population exposure, monitor coverage, spatial aggregation, and sample representativeness support that claim.
- Do not say `firms complied`, `fraud occurred`, or `illegal greenwashing occurred` from ESG text or disclosure-risk scores alone.
- Do not omit measurement error, sample selection, attrition, reporting selection, or monitor coverage limitations when artifacts flag them.
- Do not present fallback estimators as equivalent to unavailable target estimators without claim-gate authorization.
- Do not allow abstract or conclusion language to be stronger than the results section.
## Handoff to code
- Request missing `claim_gate.json` before any strong interpretation.
- Request missing `status.json` before assuming completion, diagnostic-only status, or backend status.
- Request missing `manifest.json` or `artifact_manifest.json` before trusting artifact provenance.
- Request regenerated `model_table.csv` if units, denominators, confidence intervals, sample size, specification names, or backend labels are absent.
- Request `diagnostics.json` when overlap, balance, pre-trends, support, placebo, measurement, or sample-selection diagnostics are missing.
- Request power, minimum detectable effect, or interval-based summaries when interpreting insignificant estimates.
- Request W-matrix audit and W sensitivity when spatial direction, spatial exposure, or spillover language is requested.
- Request backend discovery and backend status artifacts when target backend execution is unclear.
- Request backend rerun or dependency installation through code when `missing_dependency`, parser-only, failed, or partial status appears.
- Request robustness tables for alternative specifications, samples, outcomes, time windows, clustering, transformations, W matrices, and placebo outcomes when they are absent.
- Request measurement validation for emissions data, pollution monitors, remote sensing, ESG text scores, carbon accounting, facility reporting, and proxy outcomes.
- Request sample-selection or attrition diagnostics when treated, control, reporting, monitored, or disclosed units may be selected.
- Request official-source checks when policy timing, regulatory thresholds, ESG standards, carbon-accounting rules, or legal claims enter the interpretation.
- Request a revised claim gate after code produces new diagnostics, robustness, backend, or artifact-manifest outputs.
## Handoff from code artifacts
- From `model_table.csv`, use coefficient sign, magnitude, standard errors, confidence intervals, p-values, units, denominators, model labels, sample sizes, and backend labels.
- From `diagnostics.json`, use overlap, balance, pre-trend, support, placebo, leverage, W-matrix, measurement, and sample-selection flags.
- From robustness artifacts, use sign stability, magnitude stability, interval overlap, sensitivity to samples, sensitivity to W matrices, and failure of core checks.
- From event-study artifacts, use pre-treatment coefficients, joint pre-trend tests, dynamic path stability, and anticipation windows.
- From power artifacts, use sample size, minimum detectable effect, standard error scale, and confidence interval width.
- From `status.json`, use diagnostic-only flags, warnings, errors, partial completion, and parser-only status.
- From `claim_gate.json`, use allowed claim levels, blocked claim levels, downgrade triggers, forbidden phrases, and paper-readiness status.
- From `manifest.json` and `artifact_manifest.json`, use provenance, artifact completeness, workflow links, and known omissions.
- From `reviewer_risk.json`, use the highest-severity objections as interpretation caveats.
- From `backend_discovery.json` or equivalent and `backend_status.json`, use installed, unavailable, failed, parser-only, interface-only, missing dependency, and partial backend states.
- If fields are missing, say what cannot be interpreted rather than filling gaps with assumptions.
- If artifacts conflict, use the more conservative interpretation and record the conflict.
## Minimal examples
### Example 1: significant coefficient but design fails
Input facts:
- User asks: `Can I say the plant standard reduced SO2 emissions?`
- `model_table.csv` reports a negative coefficient with p-value below 0.05.
- `diagnostics.json` reports failed overlap and failed pre-trends.
- `claim_gate.json` blocks main causal claims.
- `status.json` reports `agent_status: diagnostic_success`.
Expected output:
```yaml
skill_name: result_interpretation_guard
user_question_summary: "Interpret a significant SO2 estimate with failed design diagnostics."
research_domain: "environmental economics reporting"
research_brief:
  unit: "plant-year"
  time_frequency: "annual"
  outcome_candidates: ["SO2 emissions"]
  treatment_or_exposure: "plant emission standard"
  estimand_candidates: ["ATT for regulated plants"]
  identification_risks: ["overlap_fail", "pretrend_fail"]
candidate_workflows: []
candidate_methods: []
required_diagnostics: ["overlap", "pre-trends", "claim_gate"]
recommended_robustness: ["support-restricted design", "alternative control group", "event-study redesign"]
forbidden_claims:
  - "The plant standard reduced SO2 emissions."
  - "The significant coefficient proves the policy worked."
claim_language:
  allowed:
    - "The reported coefficient is negative and statistically precise in the fitted table."
    - "Design diagnostics block a main causal interpretation."
  disallowed:
    - "caused"
    - "worked"
    - "paper-ready causal evidence"
uncertainty_notes:
  - "Failed overlap and pre-trends prevent treating the estimate as main causal evidence."
next_code_actions:
  - "Redesign the comparison group and regenerate overlap diagnostics."
  - "Rerun event-study diagnostics after redesign."
scholarly_depth:
  estimand_definition: "The intended ATT requires comparable regulated and unregulated plants with credible pre-treatment trends."
  identifying_assumptions: ["common support", "parallel trends", "stable reporting"]
  measurement_model: ["SO2 emissions reporting may require facility reporting validation"]
  data_construction_risks: ["regulated plants outside support", "differential pre-trends"]
  method_decision_tree: ["treat the significant estimate as diagnostic until design failures are repaired"]
  diagnostics_that_block_claims: ["overlap_fail", "pretrend_fail"]
  robustness_ranked_by_risk: ["support restriction", "matched controls", "pre-trend recheck"]
  referee_objections: ["The identifying assumptions fail before the table is interpreted causally."]
  downgrade_triggers: ["significant_but_design_fail"]
not_recommended_methods: ["claiming policy success from p-value stars"]
result_interpretation:
  numerical_result_summary: "The fitted table reports a negative SO2 coefficient that is statistically significant, but the table alone does not establish causal validity."
  design_validity_summary: "Overlap and pre-trend diagnostics fail, so the intended ATT lacks credible support in the current design."
  robustness_summary: "Robustness cannot rescue the main claim until the core support and pre-trend failures are addressed."
  safe_interpretation: "The current artifacts show a negative and statistically precise diagnostic association, but failed overlap and pre-trends block the claim that the standard caused SO2 emissions to fall."
  unsafe_interpretations_to_avoid:
    - "The plant standard reduced SO2 emissions."
    - "The significant estimate proves the regulation worked."
  next_steps_before_paper:
    - "Repair support or redefine the target estimand."
    - "Regenerate overlap and event-study diagnostics."
    - "Update the claim gate after the new diagnostics."
```
### Example 2: non-significant estimate, missing backend, and sign flip across W
Input facts:
- User asks: `Does the clean heating subsidy have no effect on PM2.5?`
- `model_table.csv` reports a non-significant preferred coefficient with a wide confidence interval.
- W-sensitivity output reports negative estimates for distance W and positive estimates for contiguity W.
- `backend_status.json` reports `missing_dependency` for the target spatial backend.
- `claim_gate.json` allows only exploratory interpretation.
Expected output:
```yaml
skill_name: result_interpretation_guard
user_question_summary: "Interpret a non-significant PM2.5 estimate with W sign flips and missing backend."
research_domain: "spatial environmental policy reporting"
research_brief:
  unit: "county-month"
  time_frequency: "monthly"
  outcome_candidates: ["PM2.5 concentration"]
  treatment_or_exposure: "clean heating subsidy exposure"
  estimand_candidates: ["reduced-form association with subsidy exposure"]
  identification_risks: ["wide_interval", "w_sign_flip", "missing_dependency"]
candidate_workflows: []
candidate_methods: []
required_diagnostics: ["confidence interval", "W sensitivity", "backend status", "claim_gate"]
recommended_robustness: ["W audit", "power summary", "backend rerun", "alternative exposure windows"]
forbidden_claims:
  - "The subsidy had no effect on PM2.5."
  - "The spatial backend confirms no spillover."
claim_language:
  allowed:
    - "The preferred estimate is statistically imprecise."
    - "Direction is unstable across W choices."
    - "Backend-certified spatial interpretation is unavailable."
  disallowed:
    - "no effect"
    - "robust null"
    - "confirmed spillover"
uncertainty_notes:
  - "The interval is wide enough that meaningful effects are not ruled out."
  - "The target spatial backend did not pass because a dependency is missing."
next_code_actions:
  - "Produce a power or minimum-detectable-effect summary."
  - "Resolve the missing backend dependency and rerun spatial specifications."
  - "Audit W matrices and report sign stability."
scholarly_depth:
  estimand_definition: "The current estimand is a reduced-form association under alternative W definitions, not a structural spillover effect."
  identifying_assumptions: ["valid exposure mapping", "stable W definition", "sufficient power"]
  measurement_model: ["PM2.5 monitors or gridded data may introduce exposure measurement error"]
  data_construction_risks: ["W choice changes exposure contrast", "backend unavailable"]
  method_decision_tree: ["block no-effect and stable-direction claims until power, W, and backend issues are resolved"]
  diagnostics_that_block_claims: ["w_sign_flip", "missing_dependency", "wide_interval"]
  robustness_ranked_by_risk: ["W audit", "backend rerun", "power summary", "exposure-window sensitivity"]
  referee_objections: ["The non-significant preferred estimate does not rule out meaningful effects and the direction changes across W definitions."]
  downgrade_triggers: ["non_significant_underpowered", "w_sign_flip", "backend_missing"]
not_recommended_methods: ["calling the preferred non-significant row a robust null"]
result_interpretation:
  numerical_result_summary: "The preferred PM2.5 coefficient is not statistically significant, but the confidence interval is wide."
  design_validity_summary: "The current artifacts do not support a no-effect claim because power is unclear and the target spatial backend is unavailable."
  robustness_summary: "Direction flips across W definitions, so the sign and spatial interpretation are unstable."
  safe_interpretation: "The evidence is inconclusive: the preferred estimate is imprecise, meaningful effects are not ruled out, W sensitivity changes the sign, and backend-certified spatial results are unavailable."
  unsafe_interpretations_to_avoid:
    - "The subsidy had no effect on PM2.5."
    - "The null is robust across spatial specifications."
    - "The spatial backend confirms no spillover."
  next_steps_before_paper:
    - "Add power or minimum-detectable-effect diagnostics."
    - "Resolve the missing dependency and rerun the target spatial backend."
    - "Justify W construction and report W sensitivity after backend completion."
```
## Completion checklist
- The first line is exactly `# Skill: result_interpretation_guard`.
- All required second-level headings are present and in the required order.
- No YAML frontmatter, installation notes, changelog, or README content is included.
- All required shared rule paths are listed exactly.
- The output schema includes all base fields.
- The output schema includes `scholarly_depth` and `not_recommended_methods`.
- The output schema includes the exact `result_interpretation` block.
- The skill explicitly forbids p-value-only conclusions.
- The skill handles significant but design-failed results.
- The skill handles insignificant but underpowered, small-sample, wide-interval, or missing-backend results.
- The skill handles sign flips across W matrices and specifications.
- The skill handles robustness conflict, backend partial availability, measurement error, and sample selection.
- The skill includes rules for sign, magnitude, stability, confidence intervals, effect sizes, denominators, and units.
- The skill includes rules for pre-trends, overlap, balance, W sensitivity, backend missingness, measurement, and sample selection.
- Handoff to code is explicit and artifact-producing.
- Handoff from code artifacts is explicit and artifact-grounded.
- Minimal examples include significant but design-failed evidence.
- Minimal examples include non-significant, missing-backend, and W sign-flip evidence.
- Volatile policy, regulation, standard, API, and data-source facts are routed to current official-source checks at use time.
