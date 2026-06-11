# Skill: reviewer_summary_template
## Purpose
This skill drafts a conservative reviewer-facing summary for environmental economics and applied econometrics projects.
It is a prompt and rubric skill, not an estimator, parser, backend runner, or claim validator.
It converts inspected repo artifacts into a paper-readiness, diagnostic-readiness, and claim-risk memo.
It must separate supported evidence from desired claims.
It must respect claim_gate.json and all stricter shared rules.
It is for econometric researchers who need referee-risk language, not engineering boilerplate.

## Shared reporting contract

Shared reporting boilerplate lives in `./_reporting_shared_contract.md`; apply it before this file-specific logic and do not duplicate or weaken its artifact, claim-gate, parser-only, missing-dependency, forbidden-claims, or scholarly-depth rules.

## When to use
Use when the user asks for a reviewer summary, referee risk memo, claim-readiness memo, or paper-readiness summary.
Use for climate, pollution, energy, natural resources, ESG, spatial exposure, and related environmental economics designs.
Use after model, diagnostic, robustness, backend, manifest, and claim-gate artifacts exist.
Use when a readiness label is needed: paper_ready, supplementary_only, diagnostic_only, blocked, or unknown.

## Do not use when
Do not use to estimate models, run diagnostics, scrape data, or create a backend.
Do not use to bypass claim_gate.json.
Do not use to convert diagnostic_success into paper-ready causal success.
Do not use to convert parser-only status into live backend execution.
Do not use to convert missing_dependency into a backend pass.
Do not use to convert spatial reduced-form exposure into structural spillover evidence.
Do not use to convert ESG text risk into fraud, illegal conduct, intent, deception, or enforcement findings.
Do not use to certify policy, regulatory, or data-source facts that were not checked from official/latest sources at use time.

## Inputs expected
User question or task statement.
Research setting: unit, geography, period, frequency, outcome, treatment or exposure, and population.
Candidate estimand or claim language, if provided.
Candidate workflows: DID, event study, panel FE, IV, RD, synthetic control, spatial exposure, text-risk design, prediction, or diagnostics-only.
Artifact bundle or repo root.
Volatile policy, regulatory, standard, or data-source facts, checked from official/latest sources at use time.

## Required repo artifacts to inspect
First inspect shared rules:
* ../_shared/00_skill_authoring_rules.md
* ../_shared/01_claim_language_rules.md
* ../_shared/02_evidence_lookup_rules.md
* ../_shared/03_artifact_reading_rules.md
* ../_shared/04_spec_drafting_rules.md
* ../_shared/05_forbidden_fallbacks.md
* ../_shared/06_reviewer_mode_rules.md
* ../_shared/07_scholarly_depth_rules.md

Then inspect repo and workflow evidence:
* README.md
* registry.yml
* cli/core/workflows/wrappers
* diagnostics/tests/backends
* status.json
* claim_gate.json
* manifest.json or artifact_manifest.json
* diagnostics.json
* model_table.csv
* reviewer_risk.json
* backend_status.json
* backend_discovery.json or equivalent
* logs
* specs
* robustness outputs

If an artifact is referenced but missing, treat it as missing evidence.
If claim_gate.json is missing, readiness cannot be paper_ready.
If backend_status.json says parser_only, missing_dependency, skipped, failed, unavailable, dry_run, or unknown, do not call the backend passed.
If backend_discovery.json exists without execution evidence, treat it as discovery only.
If model_table.csv exists without diagnostics.json and claim_gate.json, treat estimates as unvalidated descriptive or diagnostic evidence.
If volatile policy, regulatory, standard, or data-source facts matter, check official/latest sources at use time.

## Domain reasoning steps
Start from the research question and estimand, not from the estimator.
State unit, time frequency, geography, outcome, exposure, sample, and policy window.
Classify the strongest possible estimand as causal, reduced-form, descriptive, predictive, structural, or diagnostic.

Audit data construction before identification.
Check identifiers, dates, geocodes, firm links, facility links, text records, duplicates, missingness, attrition, interpolation, and sample restrictions.
For environmental exposure, check timing, assignment precision, spatial correlation, endogenous sorting, and measurement error.
For ESG text, distinguish risk language from verified fraud, illegality, intent, deception, or enforcement.
For spatial exposure, distinguish own exposure, neighbor exposure, W-matrix reduced form, market access, equilibrium channels, and structural spillovers.

Audit identification.
For DID and event studies, check timing, comparison sets, no anticipation, pretrends, overlap, balance, and staggered adoption handling.
For panel FE, check remaining identifying variation and time-varying confounding.
For IV, check relevance, weak instruments, exclusion, monotonicity, and possible direct effects.
For spatial designs, check W construction, reflection, correlated shocks, endogenous exposure, row-standardization, and alternative W definitions.

Audit estimator and backend evidence.
Confirm whether a backend actually ran, not merely parsed or was discovered.
Confirm dependency status before treating model outputs as executable.
Treat diagnostic_success as evidence that a diagnostic ran, not as evidence that the paper claim is valid.

Audit diagnostics that block claims.
Failed pretrends, severe imbalance, no overlap, or unstable weights block main DID claims.
Weak first stage or credible direct effects block IV causal claims.
Unstable W, endogenous exposure, reflection, or correlated shocks block structural spillover claims.
Low text precision, weak labels, leakage, or ambiguous language block ESG legal and intent claims.
Severe measurement error blocks precise magnitude claims.
Thin, selected, or nonrepresentative samples block broad external-validity claims.

Assign readiness after reading claim_gate.json and stricter artifacts.
Use the strictest applicable artifact when evidence conflicts.
Do not average away a blocking failure.
Reviewer objections must be tied to artifacts, assumptions, or missing evidence.
A favorable model table cannot overcome failed diagnostics.

## Candidate outputs
Return a YAML readiness summary plus a markdown referee report.
The final markdown referee report must use exactly this top-level structure:

```md
# Referee report

## Recommendation
Reject / Major revision / Minor revision / Accept / Not enough evidence

## Summary

## Major comments

## Minor comments

## Required evidence before revision

## Claims that must be removed or downgraded
```

Use the readiness audit internally to choose the recommendation and comments.
Do not expose the old ten-section readiness memo as the final report template
unless the user explicitly asks for an engineering evidence inventory.

## Output schema
Use this base schema:
```yaml
skill_name: string
user_question_summary: string
research_domain: string
research_brief:
  unit: string
  time_frequency: string
  outcome_candidates: []
  treatment_or_exposure: string
  estimand_candidates: []
  identification_risks: []
candidate_workflows: []
candidate_methods: []
not_recommended_methods: []
required_diagnostics: []
recommended_robustness: []
forbidden_claims: []
claim_language:
  allowed: []
  disallowed: []
uncertainty_notes: []
next_code_actions: []
reviewer_summary:
  readiness: paper_ready | supplementary_only | diagnostic_only | blocked | unknown
  strongest_supported_claim: string
  top_reviewer_objections: []
  must_fix_before_submission: []
  optional_improvements: []
referee_report:
  recommendation: Reject | Major revision | Minor revision | Accept | Not enough evidence
  summary: string
  major_comments: []
  minor_comments: []
  required_evidence_before_revision: []
  claims_that_must_be_removed_or_downgraded: []
scholarly_depth:
  estimand_definition: string
  identifying_assumptions: []
  measurement_model: string
  data_construction_risks: []
  method_decision_tree: []
  diagnostics_that_block_claims: []
  robustness_ranked_by_risk: []
  referee_objections: []
  downgrade_triggers: []
```

Readiness rules:

* paper_ready only if claim_gate.json permits the claim, all stricter artifacts permit it, backend execution passed, required diagnostics passed, and robustness does not materially conflict.
* supplementary_only for useful but non-main evidence, including descriptive patterns, appendix checks, or secondary designs.
* diagnostic_only for design checks, backend checks, parser checks, feasibility results, or robustness triage that cannot support paper claims.
* blocked for artifact, design, backend, dependency, diagnostic, robustness, or claim-gate failures that prevent the stated use.
* unknown for missing, unreadable, inconsistent, or uninspected essential artifacts, especially missing claim_gate.json.

Precedence rules:

* blocked overrides all other labels when a blocking failure is observed.
* unknown overrides paper_ready when claim_gate.json or essential artifacts are missing.
* diagnostic_only overrides supplementary_only when evidence is only diagnostics, parser checks, or feasibility evidence.
* supplementary_only applies when real evidence exists but main causal or structural claims are not supported.
* paper_ready is the rarest label and requires affirmative support from claim_gate.json and stricter artifacts.

## Required caveats
Diagnostic_success is not paper-ready causal success.
Missing diagnostics require unknown, diagnostic_only, or blocked readiness depending on the claim.
Parser-only status is not a live backend.
Missing_dependency is not a backend pass.
Favorable signs or statistical significance do not repair failed identification.
Reduced-form W or spatial exposure is not structural spillover unless the design identifies spillover channels.
ESG text risk is not fraud, illegality, intent, deception, or enforcement evidence.
Measurement error can block precise magnitude claims.
Sample limitations can block broad external validity claims.
Robustness conflict requires downgrade unless resolved by pre-specified logic.
Missing claim_gate.json makes paper_ready unavailable.
Volatile policy, regulatory, standard, and data-source facts must be checked from official/latest sources at use time.

## Forbidden claims
Do not claim causal effects from descriptive, predictive, parser, or diagnostic evidence alone.
Do not claim paper_ready when claim_gate.json is missing, failed, or stricter than the summary.
Do not claim backend pass when backend_status.json says parser_only, missing_dependency, skipped, unavailable, dry_run, failed, or unknown.
Do not claim robustness when core robustness outputs conflict with the main estimate.
Do not claim parallel trends hold when pretrend diagnostics fail, are missing, or are too weak without caveat.
Do not claim balanced comparison groups when overlap or balance diagnostics fail.
Do not claim structural spillovers from spatial reduced-form exposure or W coefficients alone.
Do not claim fraud, illegal conduct, intent, deception, enforcement, or compliance from ESG text risk alone.
Do not claim representative national effects from selected, local, thin, or non-random samples.
Do not claim measurement validation when proxy validation is absent.
Do not claim current official policy facts without official/latest checks at use time.

## Handoff to code
Request concrete next artifacts, not vague improvements.
Ask code to produce claim_gate.json when missing.
Ask code to produce artifact_manifest.json when provenance is unclear.
Ask code to validate backend_status.json and backend_discovery.json separately.
Ask code to resolve missing_dependency and rerun live backend execution tests.
Ask code to distinguish parser tests from backend execution tests.
Ask code to run DID pretrend, overlap, balance, timing, and event-support diagnostics.
Ask code to run IV first-stage, weak-instrument, exclusion-sensitivity, and direct-effect checks.
Ask code to run RD density, sorting, covariate-continuity, and bandwidth checks.
Ask code to run synthetic-control donor-pool, pre-fit, and placebo checks.
Ask code to run spatial alternative W, exposure-window, sorting, reflection, and correlated-shock checks.
Ask code to run ESG text label quality, leakage, calibration, external validation, and lag checks.
Ask code to produce robustness outputs tied to the highest-ranked identification risks.
State exact missing artifacts, blocking status values, diagnostics needed, claim language to test, downgraded readiness label, and expected outputs.

## Handoff from code artifacts
Treat code artifacts as evidence, not conclusions.
Read manifest.json or artifact_manifest.json before downstream outputs.
Check that diagnostics.json and model_table.csv use the same sample, dates, units, and specification family.
Check that reviewer_risk.json aligns with diagnostics.json and claim_gate.json.
Check that backend_status.json reports execution, not just discovery.
Check that backend_discovery.json or equivalent is not used as proof of model execution.
Check logs for skipped stages, dry runs, parser-only tests, missing files, and dependency errors.
Check robustness outputs for contradiction, not just presence.
When artifacts disagree, use the most conservative interpretation and record the disagreement in uncertainty_notes.

## Minimal examples
Example A: diagnostic-only DID reviewer summary.

```yaml
skill_name: reviewer_summary_template
user_question_summary: "Assess DID readiness for a pollution rule and county infant health."
research_domain: "environmental economics"
research_brief:
  unit: "county"
  time_frequency: "annual"
  outcome_candidates: ["infant mortality rate"]
  treatment_or_exposure: "post-rule treated-county exposure"
  estimand_candidates: ["ATT under parallel trends"]
  identification_risks: ["pretrend failure", "exposure measurement error", "composition changes"]
candidate_workflows: ["DID event study"]
candidate_methods: ["event-study DID"]
not_recommended_methods: ["structural spillover model without spillover design"]
required_diagnostics: ["pretrend", "overlap", "balance", "event-time support"]
recommended_robustness: ["placebo dates", "alternative exposure windows", "county trends sensitivity"]
forbidden_claims: ["paper-ready causal effect", "parallel trends hold"]
claim_language:
  allowed: ["Current artifacts support DID design diagnostics."]
  disallowed: ["The rule causally reduced infant mortality."]
uncertainty_notes: ["Claim gate permits diagnostic language only."]
next_code_actions: ["Resolve pretrend failure and rerun claim_gate.json."]
reviewer_summary:
  readiness: diagnostic_only
  strongest_supported_claim: "The workflow can diagnose whether the DID design is credible for this county panel."
  top_reviewer_objections: ["Pretrends are not yet credible.", "Exposure assignment may be noisy."]
  must_fix_before_submission: ["Pass or address pretrends.", "Document exposure construction."]
  optional_improvements: ["Add placebo dates and alternative exposure windows."]
scholarly_depth:
  estimand_definition: "ATT for treated counties under a parallel-trends counterfactual."
  identifying_assumptions: ["parallel trends", "no anticipation", "stable exposure mapping"]
  measurement_model: "County-year exposure proxy linked to rule timing."
  data_construction_risks: ["aggregation hides within-county exposure heterogeneity"]
  method_decision_tree: ["Use DID only if timing, overlap, balance, and pretrends pass."]
  diagnostics_that_block_claims: ["failed pretrend diagnostic"]
  robustness_ranked_by_risk: ["placebo dates", "alternative exposure windows", "county trends sensitivity"]
  referee_objections: ["Treated counties may have been trending differently before the rule."]
  downgrade_triggers: ["failed pretrend", "failed overlap", "failed balance"]
```

```md
## 1. Research question
The study asks whether a pollution rule changed county infant health outcomes.
## 2. Data construction
The county-year panel is usable for design diagnostics, but exposure construction and sample restrictions need audit.
## 3. Treatment / exposure design
Treatment is a post-rule county exposure indicator, with possible measurement error.
## 4. Identification strategy
The DID estimand requires parallel trends and no anticipation; current artifacts do not yet support that claim.
## 5. Estimator and backend
Estimator artifacts support diagnostic execution only, not paper readiness.
## 6. Diagnostics
Pretrend evidence blocks the main causal claim unless resolved or directly modeled.
## 7. Robustness and sensitivity
Highest-value checks are placebo dates, alternative windows, and event-time support.
## 8. Claim gate
Claim language should stay at diagnostic readiness and design risk.
## 9. Main limitations
Main limitations are pretrend risk, exposure measurement error, and sample construction uncertainty.
## 10. Required fixes before paper use
Resolve pretrends, document exposure construction, and rerun claim_gate.json before causal language.
```

Example B: blocked or unknown summary from missing claim gate plus parser-only or missing-dependency backend.

```yaml
skill_name: reviewer_summary_template
user_question_summary: "Assess an ESG text-risk workflow for emissions outcomes."
research_domain: "environmental economics and ESG text analysis"
research_brief:
  unit: "firm"
  time_frequency: "quarterly"
  outcome_candidates: ["emissions intensity"]
  treatment_or_exposure: "ESG text-risk score"
  estimand_candidates: ["association between text-risk score and emissions reporting outcomes"]
  identification_risks: ["text measurement error", "reverse causality", "legal overclaim"]
candidate_workflows: ["panel association with text-risk exposure"]
candidate_methods: ["firm and time fixed effects after backend execution exists"]
not_recommended_methods: ["fraud detection claim from text risk", "causal misconduct model without enforcement labels"]
required_diagnostics: ["claim_gate.json", "backend execution status", "text label validation"]
recommended_robustness: ["alternative dictionaries", "holdout validation", "lag sensitivity"]
forbidden_claims: ["fraud", "illegal conduct", "intent", "paper-ready causal ESG effect"]
claim_language:
  allowed: ["The current repo is not sufficient to support paper claims."]
  disallowed: ["The backend ran successfully.", "The text score identifies illegal conduct."]
uncertainty_notes: ["claim_gate.json is missing.", "backend_status.json reports parser_only or missing_dependency."]
next_code_actions: ["Create claim_gate.json.", "Resolve backend dependency.", "Run live backend tests."]
reviewer_summary:
  readiness: unknown
  strongest_supported_claim: "The repo contains a proposed ESG text-risk workflow, but claim readiness is not established."
  top_reviewer_objections: ["Missing claim gate.", "Backend is parser-only or dependency-blocked.", "Text risk is overread as legal wrongdoing."]
  must_fix_before_submission: ["Add claim_gate.json.", "Resolve backend dependency.", "Validate text labels."]
  optional_improvements: ["Add external validation and lag sensitivity."]
scholarly_depth:
  estimand_definition: "At most an association between firm-quarter text-risk scores and emissions reporting outcomes."
  identifying_assumptions: ["No causal assumptions are supported until claim gate, backend, and diagnostics pass."]
  measurement_model: "Text-risk proxy requiring label validation and leakage checks."
  data_construction_risks: ["text reflects disclosure choices as well as underlying behavior"]
  method_decision_tree: ["Do not estimate paper models until live backend execution and claim gate exist."]
  diagnostics_that_block_claims: ["missing claim_gate.json", "parser_only or missing_dependency backend status"]
  robustness_ranked_by_risk: ["text label validation", "lag sensitivity", "alternative dictionaries"]
  referee_objections: ["A referee may object that ESG risk text is being treated as evidence of wrongdoing."]
  downgrade_triggers: ["missing claim gate", "backend non-execution", "unvalidated labels"]
```

```md
## 1. Research question
The workflow asks whether firm-quarter ESG text-risk scores relate to emissions reporting outcomes.
## 2. Data construction
The panel may be constructible, but linkage and labels are not validated.
## 3. Treatment / exposure design
The exposure is a text-risk score and must be treated as a noisy proxy.
## 4. Identification strategy
No causal identification strategy is established because claim gate and diagnostics are missing.
## 5. Estimator and backend
Parser-only or missing-dependency status is not evidence that the estimator ran.
## 6. Diagnostics
Claim, backend, and text-validation diagnostics are missing or blocked.
## 7. Robustness and sensitivity
Useful future checks include alternative text measures, holdout validation, and lag sensitivity.
## 8. Claim gate
Because claim_gate.json is missing, paper_ready is unavailable and causal or legal claims are disallowed.
## 9. Main limitations
Main limitations are missing claim gate, backend non-execution, text measurement risk, and legal overclaim risk.
## 10. Required fixes before paper use
Create claim_gate.json, resolve backend dependencies, run live backend tests, and restrict ESG language.
```

## Completion checklist
Confirm the file starts with exactly "# Skill: reviewer_summary_template."
Confirm there is no YAML frontmatter.
Confirm fixed headings appear in the required order.
Confirm all shared rule paths and required artifacts are listed literally.
Confirm volatile policy, regulatory, standard, and data-source facts require official/latest checks at use time.
Confirm the schema includes all base fields, reviewer_summary, scholarly_depth, and not_recommended_methods.
Confirm reviewer_summary has readiness choices: paper_ready, supplementary_only, diagnostic_only, blocked, unknown.
Confirm output guidance requires YAML readiness summary plus a markdown referee report with Recommendation, Summary, Major comments, Minor comments, Required evidence before revision, and Claims that must be removed or downgraded.
Confirm readiness rules cover all five labels and strict precedence.
Confirm missing claim_gate.json blocks paper_ready.
Confirm diagnostic_success, parser-only, and missing_dependency caveats are explicit.
Confirm overlap, balance, pretrend, W/spatial, ESG legal, measurement error, sample limitation, and robustness conflict risks are covered.
Confirm examples include one diagnostic-only DID summary.
Confirm examples include one blocked or unknown missing-claim-gate and parser-only or missing-dependency summary.
Confirm ASCII-only content.
