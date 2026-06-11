# Skill: policy_brief_translation_guard

## Purpose
- Translate academic empirical results into policy-brief language without overstating what the research design, artifacts, and reviewed claims support.
- Audience: econometricians and environmental, climate, and finance economists writing for policy readers.
- This skill is a prompt/rubric skill, not estimator code, a backend runner, validator, legal certifier, or policy authority.
- Preserve academic uncertainty even when the requested output is short, direct, or advocacy-facing.
- Distinguish evidence levels before writing: causal claim; reduced-form evidence; correlation; diagnostic-only result; scenario or stress-test result; unknown.
- Keep visible: uncertainty, scope, units, geography, sample, period, mechanism ambiguity, measurement error, external validity, and artifact provenance.
- Do not turn statistical significance into policy certainty.
- Do not generalize local sample conclusions to all regions, sectors, firms, households, assets, or policy regimes.
- Prefer policy-safe wording that states what was estimated, where, when, for whom, in what units, and under what assumptions.
- Treat clarity as a translation goal, not as permission to strengthen claims.
- Treat policy implications as implications, not mandates, unless the evidence and requested task explicitly support a recommendation with limits.

## Shared reporting contract

Shared reporting boilerplate lives in `./_reporting_shared_contract.md`; apply it before this file-specific logic and do not duplicate or weaken its artifact, claim-gate, parser-only, missing-dependency, forbidden-claims, or scholarly-depth rules.

## When to use
- Use when translating, revising, or auditing a policy brief based on empirical academic results.
- Use for environmental economics, climate economics, energy, sustainable finance, ESG, transition risk, physical risk, banking, insurance, carbon markets, disclosure, regulation, and related fields.
- Use when source material includes econometric estimates, event studies, DiD, IV, RDD, panel regressions, synthetic controls, structural estimates, forecasts, scenarios, stress tests, or diagnostics.
- Use when claim strength must be mapped to artifacts such as claim_gate.json, result_interpretation output, claim_guard output, reviewer_summary, reviewer_risk.json, or model_table.csv.
- Use when a draft risks saying proves, guarantees, certifies, universal, fraud, illegal, enforcement proof, all regions, all firms, or policy certainty.
- Use when diagnostics, parser status, interface status, scenario outputs, or fallback estimators are being used as if they were substantive evidence.
- Use when statistical significance, local evidence, or model output is being converted into policy language.
- Use when the brief mentions volatile laws, policies, standards, APIs, taxonomies, or data definitions that require official/latest sources.

## Do not use when
- Do not use as a substitute for running estimators, cleaning data, validating code, or generating required artifacts.
- Do not use as a substitute for claim_gate.json, reviewer review, artifact validation, or official policy/legal sources.
- Do not use to certify regulatory compliance, legal liability, fraud, misconduct, intent, enforcement probability, or safety.
- Do not use to upgrade correlation, diagnostics, scenarios, parser success, interface success, or missing-dependency outputs into causal evidence.
- Do not use to infer evidence strength from prose alone when artifacts are missing, stale, failed, or inconsistent.
- Do not use to fabricate citations, estimates, intervals, diagnostics, sample sizes, or provenance.
- Do not use to convert statistically significant results into certainty, welfare optimality, cost-effectiveness, or universal policy advice.
- Do not use unsupported fallback estimators as equivalent substitutes for the specified design.
- Do not use to erase uncertainty in order to satisfy a policy audience.

## Inputs expected
- User question or draft policy-brief text.
- Research domain and intended policy audience.
- Policy audience/scope: jurisdiction, geography, sector, unit, sample, period, institution type, and intended use.
- Academic abstract, conclusion, result paragraph, table note, reviewer note, or artifact summary to translate.
- claim_guard output, result_interpretation output, and reviewer_summary when available.
- claim_gate.json, status.json, manifest.json or artifact_manifest.json when available.
- diagnostics.json, model_table.csv, reviewer_risk.json, and backend_status.json when available.
- Estimator family, identification design, treatment definition, outcome definition, sample construction, and unit of observation.
- Point estimates, standard errors, confidence intervals, p-values, baseline means, units, transformations, and inference method.
- Robustness, placebo, pre-trend, balance, first-stage, weak-instrument, bandwidth, sensitivity, or stress-test artifacts.
- Known author caveats, reviewer objections, code warnings, unresolved TODOs, and previous skill outputs.
- Official/latest sources for volatile policy, regulatory, standard, API, or data facts.
- Explicit user constraints on length, tone, audience, jurisdiction, or document type.

## Required repo artifacts to inspect
- Inspect shared rules when present:
  - ../_shared/00_skill_authoring_rules.md
  - ../_shared/01_claim_language_rules.md
  - ../_shared/02_evidence_lookup_rules.md
  - ../_shared/03_artifact_reading_rules.md
  - ../_shared/04_spec_drafting_rules.md
  - ../_shared/05_forbidden_fallbacks.md
  - ../_shared/06_reviewer_mode_rules.md
  - ../_shared/07_scholarly_depth_rules.md
- Inspect claim_guard output when available.
- Inspect result_interpretation output when available.
- Inspect reviewer_summary when available.
- Inspect policy audience/scope when available.
- Inspect claim_gate.json before making or preserving any substantive claim.
- Do not bypass claim_gate.json.
- Inspect status.json for run state, warnings, failures, and completeness.
- Inspect manifest.json or artifact_manifest.json for provenance, freshness, and expected outputs.
- Inspect diagnostics.json for diagnostics, while keeping diagnostics separate from evidence.
- diagnostic_success is not paper-ready evidence.
- Inspect model_table.csv for estimates, units, sample size, fixed effects, controls, and inference.
- Inspect reviewer_risk.json for identification, measurement, inference, external-validity, and policy-overreach flags.
- Inspect backend_status.json for actual backend execution state.
- parser-only, interface-only, or missing_dependency is not a backend pass.
- Inspect official/latest sources for volatile policy, regulatory, standard, API, or data facts.
- If required artifacts are absent, stale, failed, inconsistent, or omitted from the manifest, classify readiness as unknown or blocked for the affected claim.
- Do not infer artifact status from narrative descriptions.
- Do not infer model success from file existence alone.
- Do not infer causality from table titles, variable names, or policy motivation.
- Unsupported fallback estimators are not equivalent substitutes.
- Prefer the most conservative evidence classification when artifacts conflict.

## Domain reasoning steps
- First identify policy audience and intended use: regulator, agency staff, legislator, central bank, supervisor, firm risk team, investor, NGO, local government, or public reader.
- Do not let audience needs change evidence strength.
- Identify the domain: environmental, climate, energy, sustainable finance, ESG, disclosure, asset pricing, banking, insurance, public finance, macro-finance, or another field.
- Note domain pitfalls: spatial spillovers, adaptation, anticipation, sorting, policy endogeneity, leakage, reporting incentives, omitted physical risk, transition channels, equilibrium effects, and incidence.
- Read artifact provenance before translating.
- Start with claim_gate.json; if it is missing or blocks the claim, classify the affected claim as unknown or blocked.
- Check backend_status.json; parser-only, interface-only, or missing_dependency is not a backend pass.
- Check diagnostics.json; diagnostic_success is not paper-ready evidence.
- Check model_table.csv for the actual coefficient, uncertainty, unit, sample, and model label.
- Check reviewer_risk.json and reviewer_summary for unresolved objections.
- Classify evidence level before writing:
  - causal_claim: supported causal design, passed or qualified artifacts, explicit scope, and claim gate permission.
  - reduced_form_evidence: policy-relevant estimate or intent-to-treat evidence, but mechanism, channel, or full structural interpretation is not isolated.
  - correlation: descriptive, associational, cross-sectional, uncontrolled, or not credibly identified.
  - diagnostic_only: code health, parser status, model fit, convergence, missingness, balance, pre-trend, placebo, or other checks without direct policy-effect evidence.
  - scenario_or_stress_test: simulation, forecast, pathway, assumed shock, stress-test, counterfactual, or hypothetical policy result.
  - unknown: artifacts are missing, failed, stale, inconsistent, blocked, or insufficient to classify.
- Apply downgrade rules:
  - Downgrade causal_claim to reduced_form_evidence if treatment effects are estimated but mechanism, exclusion, interference, compliance, or channel remains ambiguous.
  - Downgrade causal_claim to correlation if identification assumptions are unsupported, pre-trends fail, instruments are weak, timing is endogenous, or omitted variables dominate.
  - Downgrade reduced_form_evidence to correlation if the design is only associational or if key design artifacts are missing.
  - Downgrade correlation to unknown if the table, sample, outcome, or provenance cannot be verified.
  - Downgrade any level to diagnostic_only when only diagnostics, parser success, interface success, fit metrics, or backend status support the claim.
  - Downgrade any level to scenario_or_stress_test when the result is driven by assumed shocks, climate pathways, transition scenarios, simulations, or hypothetical regimes.
  - Downgrade any level to unknown when claim_gate.json is absent, failed, or blocking and no lower artifact-backed claim remains.
  - Downgrade broad statements when evidence is local, sector-specific, short-period, selected, or based only on observed adopters.
- Reduced-form evidence is not automatically causal.
- ESG text risk is not fraud, illegality, intent, or enforcement proof.
- Statistical significance is not policy certainty.
- Local sample evidence is not universal evidence.
- Preserve scope: geography, jurisdiction, sector, market, sample frame, unit of observation, inclusion rules, treatment, outcome, and period.
- Preserve units: percentage points, log points, elasticity, dollars, emissions units, risk metrics, probabilities, or index points.
- Preserve uncertainty: confidence intervals, standard errors, p-values, credible intervals, sensitivity ranges, or qualitative uncertainty.
- Preserve mechanism ambiguity: do not assign channels unless separately identified.
- Preserve measurement limits: proxies, missingness, reporting incentives, data linkage, classification error, and definitional changes.
- Preserve external validity: do not extrapolate beyond the studied sample unless directly supported.
- uncertainty, scope, units, geography, sample, period, mechanism ambiguity, measurement error, and external validity must be preserved.
- Translate with cautious verbs: estimates, finds evidence consistent with, is associated with, suggests within this sample, indicates under these assumptions.
- Avoid strong verbs: proves, guarantees, certifies, establishes everywhere, eliminates uncertainty, detects fraud, or shows that policy must.
- Separate statistical significance from practical significance, welfare effects, cost-effectiveness, incidence, and distributional impacts.
- Separate realized historical estimates from scenarios, stress tests, forecasts, and simulations.
- Safe wording for causal_claim: "Within the studied setting and maintained design assumptions, the estimates support a causal interpretation of X on Y."
- Unsupported wording for causal_claim: "This proves the policy will work everywhere."
- Safe wording for reduced_form_evidence: "The estimates show policy-relevant reduced-form evidence in the observed sample."
- Unsupported wording for reduced_form_evidence: "The coefficient identifies the complete causal mechanism."
- Safe wording for correlation: "The variables are associated in the analyzed data."
- Unsupported wording for correlation: "The association shows that X caused Y."
- Safe wording for diagnostic_only: "The diagnostic result supports pipeline or model-check readiness only."
- Unsupported wording for diagnostic_only: "Diagnostic success is substantive policy evidence."
- Safe wording for scenario_or_stress_test: "Under the stated scenario assumptions, the model implies exposure of this size."
- Unsupported wording for scenario_or_stress_test: "The scenario predicts realized losses."
- Safe wording for unknown: "Available artifacts do not support a classified policy claim yet."
- Unsupported wording for unknown: "The narrative is enough to support the policy conclusion."
- Produce allowed and disallowed language, forbidden claims, uncertainty notes, reviewer questions, not recommended methods, and next code actions.

## Candidate outputs
- Policy-safe paragraph, caveat block, or full brief revision preserving scope, units, uncertainty, mechanisms, measurement, and external validity.
- Evidence-level classification with rationale and downgrade explanation.
- Allowed and disallowed claim-language lists with unsupported claims to remove.
- Reviewer questions before publication and a blocked-readiness response when artifacts are absent or failed.
- Handoff to code for missing or failed artifacts, and handoff from code explaining what can and cannot be said.
- YAML output conforming to the schema, or reviewer-mode prose focused on preventing overstatement.

## Output schema
- Base fields: skill_name, user_question_summary, research_domain, policy_brief_translation, claim_language, forbidden_claims, uncertainty_notes, scholarly_depth, not_recommended_methods, next_code_actions.
- Use the exact schema below when structured output is requested or repo automation expects machine-readable output.
```yaml
skill_name: string
user_question_summary: string
research_domain: string
policy_brief_translation:
  evidence_level: causal_claim | reduced_form_evidence | correlation | diagnostic_only | scenario_or_stress_test | unknown
  policy_safe_summary: string
  uncertainty_to_keep: []
  scope_limits: []
  unsupported_wording_to_avoid: []
claim_language:
  allowed: []
  disallowed: []
forbidden_claims: []
uncertainty_notes: []
scholarly_depth:
  missing_context: []
  assumptions: []
  identification_or_design_limits: []
  measurement_limits: []
  external_validity_limits: []
  reviewer_questions: []
not_recommended_methods: []
next_code_actions: []
```
- evidence_level must contain exactly one enumerated value.
- policy_safe_summary must not exceed claim_gate.json.
- uncertainty_to_keep must include uncertainty that materially affects interpretation.
- scope_limits must include geography, sector, sample, period, and units when known.
- unsupported_wording_to_avoid must identify phrases that overstate evidence.
- allowed language must be paste-ready for a policy brief.
- disallowed language must be concrete enough to remove mechanically.
- forbidden_claims must include blocked or unsupported claims.
- scholarly_depth fields must preserve missing context, assumptions, identification limits, measurement limits, external validity limits, and reviewer questions.
- not_recommended_methods must include unsupported fallbacks or unjustified substitutes.
- next_code_actions must list concrete artifact tasks needed to unblock stronger claims.

## Required caveats
- Always preserve whether the claim is causal, reduced-form, correlational, diagnostic, scenario-based, or unknown.
- Always preserve uncertainty, scope, units, geography, sample, period, mechanism ambiguity, measurement error, and external validity.
- Always preserve artifact provenance and claim-gate status.
- Always state when claim_gate.json is missing, unavailable, failed, or blocking.
- Always state when backend_status.json is parser-only, interface-only, missing_dependency, failed, partial, or otherwise not a backend pass.
- Always state that diagnostic_success is not paper-ready evidence when diagnostics are the only support.
- Always state that reduced-form evidence is not automatically causal.
- Always state that statistical significance is not policy certainty.
- Always state that local sample evidence is not universal evidence.
- Always state that ESG text risk is not fraud, illegality, intent, or enforcement proof when ESG text-risk claims are present.
- Always state that unsupported fallback estimators are not equivalent substitutes when fallbacks appear.
- Caveat magnitude separately from statistical significance.
- Caveat projections, climate pathways, transition scenarios, and stress tests separately from observed historical estimates.
- Caveat market-price reactions separately from welfare impacts.
- Caveat disclosure changes separately from real emissions, real abatement, or real risk changes.
- Caveat transition-risk exposure separately from actual losses, defaults, insolvency, or systemic risk.
- Caveat physical-risk exposure separately from realized damages.
- Caveat sample-average effects separately from distributional or incidence claims.
- Caveat local average treatment effects separately from population average effects.
- Caveat official policy facts using official/latest sources when facts are volatile.
- Required caveats must be plain enough for policy readers and precise enough for academic reviewers.

## Forbidden claims
- Do not bypass claim_gate.json.
- Do not claim paper-ready evidence from diagnostic_success.
- diagnostic_success is not paper-ready evidence.
- Do not claim backend pass from parser-only, interface-only, or missing_dependency status.
- parser-only, interface-only, or missing_dependency is not a backend pass.
- Do not claim causality from reduced-form evidence unless artifacts and design support it.
- reduced-form evidence is not automatically causal.
- Do not claim fraud, illegality, intent, enforcement proof, or misconduct from ESG text risk.
- ESG text risk is not fraud, illegality, intent, or enforcement proof.
- Do not claim policy certainty from statistical significance.
- statistical significance is not policy certainty.
- Do not claim universal validity from local sample evidence.
- local sample evidence is not universal evidence.
- Do not delete academic uncertainty.
- Do not omit scope, units, geography, sample, period, mechanism ambiguity, measurement error, or external validity.
- Do not imply that a significant coefficient is economically large, stable, cost-effective, or welfare-improving without support.
- Do not imply that a null result proves no effect unless power and precision support that interpretation.
- Do not imply that robustness checks, pre-trend balance, first-stage strength, placebo success, or model fit alone prove identification.
- Do not imply that stress-test losses are predicted realized losses.
- Do not imply that climate scenarios are forecasts unless the scenario source defines them as forecasts.
- Do not imply that disclosure text measures real emissions, real abatement, or real climate risk unless validated.
- Do not imply that asset-price reactions are welfare effects.
- Do not imply that transition-risk exposure is default, insolvency, systemic risk, or enforcement proof without support.
- Do not imply that current regulatory text, standards, APIs, or data definitions are verified without official/latest sources.
- Do not imply that unsupported fallback estimators are equivalent substitutes.
- Unsupported fallback estimators are not equivalent substitutes.
- Do not fabricate citations, estimates, intervals, diagnostics, sample sizes, artifacts, or provenance.
- Do not hide blocked, failed, missing, stale, partial, or inconsistent artifacts.
- Do not upgrade claims because a policy audience wants simpler language.

## Handoff to code
- Request claim_gate.json generation or inspection before substantive claims.
- Request backend_status.json inspection when execution status is unclear.
- Request manifest.json or artifact_manifest.json updates when provenance is unclear.
- Request model_table.csv with estimates, units, sample size, controls, fixed effects, intervals, and inference method.
- Request diagnostics.json only as diagnostics, not as policy-effect evidence.
- Request reviewer_risk.json when reviewer concerns are absent but claim stakes are high.
- Request sample metadata: geography, sector, unit, period, inclusion rules, missingness, treatment timing, and outcome definition.
- Request robustness and sensitivity artifacts when policy language depends on robustness.
- Request official/latest-source checks for volatile policy, regulatory, standard, API, taxonomy, or data facts.
- Request a code-side block if claim_gate.json is missing, stale, inconsistent, or blocking.
- Request a code-side block if backend_status.json shows parser-only, interface-only, missing_dependency, failed, or partial execution.
- Request that unsupported fallback estimators be removed, labeled exploratory, or separately justified.
- Request that scenario outputs include assumptions, pathway labels, horizons, shock sizes, and non-forecast caveats.
- Request that ESG text-risk outputs include measurement definitions and disclaimers about fraud, illegality, intent, and enforcement proof.
- Handoff must be concrete, artifact-named, and testable.

## Handoff from code artifacts
- Start from claim_gate.json, not from the draft prose.
- If claim_gate.json permits a claim, still preserve scope and uncertainty.
- If claim_gate.json downgrades a claim, use the downgraded evidence level.
- If claim_gate.json blocks a claim, do not make the claim.
- If claim_gate.json is absent, classify readiness as unknown or blocked for substantive claims.
- If status.json indicates failure, partial execution, stale artifacts, or warnings, do not present results as final.
- If manifest.json or artifact_manifest.json omits an artifact, treat it as unverified.
- If diagnostics.json reports only diagnostic_success, classify as diagnostic_only.
- If backend_status.json is parser-only, interface-only, or missing_dependency, do not report backend pass.
- If model_table.csv contains only descriptive statistics or associations, classify as correlation unless design artifacts support more.
- If model_table.csv contains reduced-form estimates, do not call them causal unless identification support is explicit.
- If reviewer_risk.json flags high risk, include the issue in uncertainty_notes or scholarly_depth.
- If reviewer_summary conflicts with result_interpretation, prefer the more conservative claim.
- If claim_guard output identifies forbidden language, include it in unsupported_wording_to_avoid.
- If official/latest sources conflict with stale policy text, treat the stale text as unverified.
- If artifacts include fallback estimators, verify authorization and substantive equivalence.
- If the fallback is unsupported, list it in not_recommended_methods and avoid treating it as equivalent.
- If artifacts are absent, do not infer from narrative.
- Use the most conservative evidence classification consistent with inspected artifacts.

## Minimal examples
- Example 1: reduced-form evidence with scope limits.
```yaml
skill_name: policy_brief_translation_guard
user_question_summary: Translate a county-level climate adaptation estimate for a state policy brief.
research_domain: climate_economics
policy_brief_translation:
  evidence_level: reduced_form_evidence
  policy_safe_summary: "In the studied coastal counties from 2005 to 2020, the estimates are consistent with lower flood-insurance take-up after repeated premium increases, conditional on the reported controls and fixed effects. The result can inform affordability and coverage-gap discussions, but it does not identify all mechanisms or establish effects for inland counties."
  uncertainty_to_keep:
    - "Reduced-form evidence is not automatically causal."
    - "Mechanisms such as liquidity constraints, risk beliefs, and migration are not separately identified."
  scope_limits:
    - "Geography: studied coastal counties."
    - "Period: 2005 to 2020."
    - "Unit: county-year insurance take-up."
  unsupported_wording_to_avoid:
    - "Premium increases caused all households to drop coverage."
    - "The result proves subsidies are required nationwide."
claim_language:
  allowed:
    - "The estimates suggest a coverage response in the studied coastal counties."
  disallowed:
    - "This proves premium increases cause households everywhere to abandon coverage."
forbidden_claims:
  - "Universal national effect."
  - "Policy certainty from statistical significance."
uncertainty_notes:
  - "local sample evidence is not universal evidence."
scholarly_depth:
  missing_context: ["Exact estimate, interval, baseline mean, and clustering choice."]
  assumptions: ["Premium changes are interpreted through the reported reduced-form design."]
  identification_or_design_limits: ["Policy endogeneity and unobserved county trends must remain visible."]
  measurement_limits: ["Insurance take-up may not measure actual flood-risk protection."]
  external_validity_limits: ["Coastal county results do not automatically extend to inland counties."]
  reviewer_questions: ["Are results robust to county-specific trends and storm exposure controls?"]
not_recommended_methods: ["Unsupported fallback estimator as an equivalent substitute."]
next_code_actions: ["Inspect claim_gate.json and model_table.csv before final wording."]
```
- Example 2: diagnostic downgrade and ESG overclaim guard.
```yaml
skill_name: policy_brief_translation_guard
user_question_summary: Audit a draft saying an ESG text-risk model proves greenwashing.
research_domain: sustainable_finance
policy_brief_translation:
  evidence_level: diagnostic_only
  policy_safe_summary: "The available artifacts support only that the ESG text-risk pipeline completed diagnostic checks for the analyzed disclosures. They do not establish fraud, illegality, intent, enforcement risk, or actual emissions misreporting. A policy brief should describe the output as a measured text-risk signal, not proof of misconduct."
  uncertainty_to_keep:
    - "diagnostic_success is not paper-ready evidence."
    - "Text-risk scores are proxies and may reflect language, disclosure style, or sector composition."
  scope_limits:
    - "Sample: analyzed disclosures only."
    - "Outcome: text-risk signal, not legally adjudicated conduct."
  unsupported_wording_to_avoid:
    - "The model proves fraud."
    - "High ESG text risk shows illegal greenwashing."
claim_language:
  allowed:
    - "The diagnostic output flags disclosures with higher measured ESG text-risk scores."
  disallowed:
    - "The model detects fraud."
    - "The score is enforcement proof."
forbidden_claims:
  - "Text score proves intent."
  - "Diagnostic success is substantive evidence."
uncertainty_notes:
  - "ESG text risk is not fraud, illegality, intent, or enforcement proof."
  - "parser-only, interface-only, or missing_dependency is not a backend pass."
scholarly_depth:
  missing_context: ["claim_gate.json, validation outcomes, sample construction, and false-positive rates."]
  assumptions: ["Text-risk score is treated as a screening proxy only."]
  identification_or_design_limits: ["No causal or legal identification is established by diagnostics."]
  measurement_limits: ["Disclosure language may reflect boilerplate, regulation, industry norms, and counsel."]
  external_validity_limits: ["Analyzed public disclosures do not represent all firms or jurisdictions."]
  reviewer_questions: ["Was the score validated against independent outcomes without treating them as proof of intent?"]
not_recommended_methods: ["Treating parser success as backend pass.", "Using unsupported fallback text classifier as an equivalent substitute."]
next_code_actions: ["Inspect backend_status.json, diagnostics.json, claim_gate.json, and artifact_manifest.json."]
```

## Completion checklist
- First line is exactly "# Skill: policy_brief_translation_guard"; no YAML frontmatter is present; file is ASCII only; level-2 headings are required headings in required order.
- Purpose says the skill translates academic results into policy-brief language without overstating and is not estimator code, backend runner, validator, legal certifier, or policy authority.
- Evidence levels are named: causal claim; reduced-form evidence; correlation; diagnostic-only result; scenario or stress-test result; unknown.
- Schema evidence enum is exactly: causal_claim, reduced_form_evidence, correlation, diagnostic_only, scenario_or_stress_test, unknown.
- All required shared rule paths are named literally.
- Required artifacts are named: claim_guard output, result_interpretation output, reviewer_summary, policy audience/scope, claim_gate.json, status.json, manifest.json or artifact_manifest.json, diagnostics.json, model_table.csv, reviewer_risk.json, backend_status.json; official/latest sources are required for volatile policy, regulatory, standard, API, or data facts.
- Red lines appear exactly or substantively: Do not bypass claim_gate.json; diagnostic_success is not paper-ready evidence; parser-only, interface-only, or missing_dependency is not a backend pass.
- Red lines appear exactly or substantively: reduced-form evidence is not automatically causal; ESG text risk is not fraud, illegality, intent, or enforcement proof.
- Red lines appear exactly or substantively: statistical significance is not policy certainty; local sample evidence is not universal evidence.
- Red lines appear exactly or substantively: uncertainty, scope, units, geography, sample, period, mechanism ambiguity, measurement error, and external validity must be preserved.
- Red line appears exactly or substantively: Unsupported fallback estimators are not equivalent substitutes.
- Downgrade rules cover causal_claim, reduced_form_evidence, correlation, diagnostic_only, scenario_or_stress_test, and unknown.
- Safe and unsupported wording examples are provided for each evidence level.
- Missing, stale, failed, inconsistent, or absent artifacts imply unknown or blocked readiness for affected claims.
- The file says not to infer from narrative when artifacts are absent.
- Output schema contains the required YAML block and all required fields.
- Caveats preserve uncertainty, scope, units, geography, sample, time, mechanism, measurement error, and external validity.
- Forbidden claims prohibit policy certainty from statistical significance, universal conclusions from local samples, and fraud or enforcement proof from ESG text risk.
- Handoff to code gives concrete artifact-generation or inspection actions.
- Handoff from code explains how to use claim_gate.json, backend_status.json, diagnostics.json, model_table.csv, reviewer_risk.json, and manifests.
- Minimal examples include one reduced-form or causal example with scope limits and one diagnostic, scenario, unknown, or overgeneralization downgrade example.
- Minimal examples use YAML and include policy_brief_translation blocks.
- Completion checklist is mechanical enough for Codex validation.
